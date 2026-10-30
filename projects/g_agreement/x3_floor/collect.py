"""X3 floor item sets (GPU; BRIEF_X.md "X3 design and endpoints"). Selection uses the target model
and the prompt-only arm only, never a reader.

    python -m projects.g_agreement.x3_floor.collect --phase A [--candidates dataset/items_x3_candidates.json]
                                                     [--limit N] [--allow-unfrozen] [--skip-lo]
    python -m projects.g_agreement.x3_floor.collect --phase B

Phase A
  step 1  selection decodes (target only):
          puzzles  greedy answer (16 new tokens) on every candidate puzzle -> one symbol A–H (or None)
          choice   greedy answer (16 new tokens; the ACTUAL choice) AND the prompt-only self-guess from the
                   item's ``prompt_only_text`` (64 new tokens); both parsed with the choice rule
          rows -> cache/g_agreement/x/x3_target.jsonl (key = item_id; resumable)
  step 2  deterministic selection (seed 0):
          ERROR         puzzles with a parsed symbol != correct; candidates (model's answer, correct)
          ERROR_CONTROL size-matched correct puzzles; candidates (correct, most frequent wrong symbol among the
                        ERROR items with the same k, else the symbol visited one step before the end)
          DISAGREE      choice items whose self-guess != actual (both parsed); candidates (actual, self-guess)
          AGREE_CONTROL size-matched agree items; candidates (actual, the other option)
          -> dataset/items_x3_selected.json (items.json-like; ``set``, ``text_key`` = the text-implied answer)
          K6: a set with < 24 items is marked ``underpowered`` in meta (descriptive only) but still runs.
  step 3  block-42 last-token states (shared cache keyed by item_id) + J-lens / OLens native LO with
          candidates (actual, other) -> cache/g_agreement/x/x3_lo.jsonl (key = reader|item_id;
          ``lo_actual`` = lp(actual) − lp(other), positive = the reader favours the model's own answer)
Phase B  NLA LO on the same selected items.

Ledger steps: x3_target_puzzle, x3_target_choice, x3_self_guess, capture (module x3), x3_lo_{jlens,olens,nla}.
Log: results/g_agreement/x3/log.md.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import generate as G
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring as SC
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core import states as S
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, read_jsonl, timed_call

MODULE = "x3"
X_DIR = C.CACHE_DIR / "x"
TARGET_PATH = X_DIR / "x3_target.jsonl"
LO_PATH = X_DIR / "x3_lo.jsonl"
CANDIDATES_JSON = C.DATASET_DIR / "items_x3_candidates.json"
SELECTED_JSON = C.DATASET_DIR / "items_x3_selected.json"
LOG = C.RESULTS_DIR / "x3" / "log.md"
FROZEN_CONFIG_X = getattr(C, "FROZEN_CONFIG_X", C.MANIFEST_DIR / "frozen_config_x.json")

PUZZLE_CAP = 16  # brief: target greedy, 16 tokens
CHOICE_CAP = 16  # one-word answers (G6 used 32; 16 is enough and halves the decode cost)
SELF_GUESS_CAP = 64
SYMBOLS = "ABCDEFGH"
SELECTION_SEED = 0
MIN_SET = 24  # K6
SETS = ("error", "error_control", "disagree", "agree_control")
FAMILIES = ("puzzle", "choice")
# mapping-style NLA templates for the puzzle family; the dataset agent adds the same entry to
# scoring_lo.NLA_TEMPLATES, setdefault keeps theirs when present.
PUZZLE_NLA_TEMPLATES = ['The answer must be the symbol "{X}".', 'The single-word answer "{X}".']
LO.NLA_TEMPLATES.setdefault("puzzle", list(PUZZLE_NLA_TEMPLATES))


# ------------------------------------------------------------------ parsing
_SYM = re.compile(r"(?<![A-Za-z])([A-H])(?![A-Za-z])")
_CUE = re.compile(
    r"(?:\b(?:answer|result|final|end(?:s|ing)?(?:\s+up)?|land(?:s|ing)?|arrive(?:s)?|is|at|reach(?:es)?)\b|=|:|->|→|⟶)"
    r"\s*(?:at|on|is|:)?\s*[\*\"'`\(\[]*([A-H])(?![A-Za-z])",
    re.I,
)


def parse_symbol(text: str | None, symbols: str = SYMBOLS) -> tuple[str | None, str]:
    """One puzzle symbol from a greedy answer. Rules in order: (1) exactly one distinct symbol is
    mentioned (evidence 'first word' when it is the first word); (2) several symbols: the last
    'answer cue' (``answer is X``, ``-> X``, ``= X``, ``: X`` ...) names the symbol; (3) else the first
    word if it is a symbol; else None (ambiguous or absent). Symbols are matched case-sensitively and
    as standalone letters, so the article 'a' never counts."""
    text = "" if text is None else str(text)
    allowed = set(symbols)
    words = re.sub(r"^\W+", "", text.strip()).split()
    head = re.sub(r"\W+$", "", words[0]) if words else ""
    found = [m.group(1) for m in _SYM.finditer(text) if m.group(1) in allowed]
    distinct = sorted(set(found))
    if len(distinct) == 1:
        return distinct[0], ("first word" if head in allowed else "only symbol mentioned")
    if not distinct:
        return None, "no symbol"
    cues = [m.group(1) for m in _CUE.finditer(text) if m.group(1) in allowed]
    if cues:
        return cues[-1], "answer cue (last)"
    if head in allowed:
        return head, "first word (others mentioned)"
    return None, f"ambiguous: {distinct}"


def parse_choice(text: str | None, candidates: list[str]) -> tuple[str | None, str]:
    """The G6 choice rule (scoring.extract_target_answer, family 'choice')."""
    return SC.extract_target_answer(text, {"family": "choice", "primary": {"candidates": list(candidates)}})


# ------------------------------------------------------------------ candidates
def load_candidates(path: Path | str = CANDIDATES_JSON, limit: int = 0) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """items_x3_candidates.json -> (meta, items). ``limit`` keeps the first N puzzles AND the first
    N choice items (smoke runs). Schema checked; anything else raises."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run dataset/build_x3.py first")
    d = json.loads(p.read_text(encoding="utf-8"))
    items = d["items"]
    seen: set[str] = set()
    for it in items:
        iid = it["item_id"]
        if iid in seen:
            raise ValueError(f"duplicate item_id {iid}")
        seen.add(iid)
        if it.get("family") not in FAMILIES:
            raise ValueError(f"{iid}: family must be one of {FAMILIES}, got {it.get('family')!r}")
        if not isinstance(it.get("prompt_text"), str) or not it["prompt_text"]:
            raise ValueError(f"{iid}: prompt_text missing")
        pr = it.get("primary") or {}
        if it["family"] == "puzzle":
            if pr.get("correct") not in set(SYMBOLS):
                raise ValueError(f"{iid}: primary.correct must be a symbol in {SYMBOLS}")
            if not isinstance(pr.get("k"), int):
                raise ValueError(f"{iid}: primary.k must be an int")
        else:
            cands = pr.get("candidates")
            if not (isinstance(cands, list) and len(cands) == 2 and len(set(cands)) == 2):
                raise ValueError(f"{iid}: primary.candidates must be two distinct options")
            if not isinstance(it.get("prompt_only_text"), str) or not it["prompt_only_text"]:
                raise ValueError(f"{iid}: prompt_only_text missing")
    if limit:
        out: list[dict[str, Any]] = []
        for fam in FAMILIES:
            out += [it for it in items if it["family"] == fam][:limit]
        items = out
    return d.get("meta", {}), items


def _distractors(item: dict[str, Any]) -> list[str]:
    d = item.get("distractors")
    if d is None:
        d = (item.get("primary") or {}).get("distractors")
    return list(d or [])


def pre_final_symbol(item: dict[str, Any]) -> str | None:
    """The symbol visited one step before the end (the (k-1)-trace symbol)."""
    pr = item.get("primary") or {}
    trace = list(pr.get("trace") or [])
    correct = pr.get("correct")
    if trace:
        if trace[-1] == correct and len(trace) >= 2:
            return trace[-2]
        if trace[-1] != correct:
            return trace[-1]
    ds = _distractors(item)
    return ds[-1] if ds else None


# ------------------------------------------------------------------ step 1: decodes
def self_guess_answer(target: M.Target, item: dict[str, Any], max_new_tokens: int = SELF_GUESS_CAP) -> tuple[Any, list[int], str]:
    """The prompt-only self-guess: the item's ``prompt_only_text`` (built by the dataset from the
    frozen G6 prompt-only template), chat render, greedy. Never sees a readout or a target answer."""
    visible = item["prompt_only_text"]
    for forbidden in ("<explanation>", "<activation>"):
        assert forbidden not in visible, "prompt-only prompt must not contain reader material"
    ids = M.render_item(target.tokenizer, visible, None)
    res = G.generate_ids(target.model, target.tokenizer, ids, max_new_tokens=max_new_tokens,
                         sampling=None, seed=None, adapter_enabled=False)
    return res, ids, visible


def collect_target(target: M.Target, items: list[dict[str, Any]], *, target_path: Path = TARGET_PATH,
                   ledger_path: Path | None = None, log_path: Path | None = LOG, puzzle_cap: int = PUZZLE_CAP,
                   choice_cap: int = CHOICE_CAP, self_guess_cap: int = SELF_GUESS_CAP,
                   extra: dict[str, Any] | None = None) -> int:
    """Step 1. One row per candidate item (key = item_id); resumable."""
    done = done_ids(target_path, key="key")
    led_p = StepLedger(step="x3_target_puzzle", module=MODULE, extra={"max_new_tokens": puzzle_cap})
    led_c = StepLedger(step="x3_target_choice", module=MODULE, extra={"max_new_tokens": choice_cap})
    led_s = StepLedger(step="x3_self_guess", module=MODULE, extra={"max_new_tokens": self_guess_cap})
    extra = dict(extra or {})
    n = 0
    for it in items:
        iid = it["item_id"]
        if iid in done:
            continue
        row: dict[str, Any] = {"key": iid, "item_id": iid, "family": it["family"], "created_at": now_iso(), **extra}
        if it["family"] == "puzzle":
            res, ids = G.target_answer(target, it, max_new_tokens=puzzle_cap)
            parsed, ev = parse_symbol(res.raw_output)
            correct = it["primary"]["correct"]
            rx = it.get("target_answer_regex")
            row.update({
                "answer_text": res.raw_output, "parsed": parsed, "parse_evidence": ev, "correct": correct,
                "k": it["primary"].get("k"), "is_coherent": parsed is not None,
                "is_error": parsed is not None and parsed != correct,
                "regex_match": bool(re.search(rx, res.raw_output)) if rx else None,
                "n_prompt_tokens": res.n_prompt_tokens, "n_new_tokens": res.n_new_tokens, "finish_reason": res.finish_reason,
                "prompt_ids_sha256": C.sha256_ids(ids), "wall_s": res.wall_s, "peak_mem_gb": res.peak_mem_gb,
                "sampling": res.sampling, "model_sha": C.TARGET_MODEL_SHA, "adapter": "none",
            })
            led_p.add(res.n_prompt_tokens, res.n_new_tokens, res.wall_s, res.peak_mem_gb)
            shown = f"{parsed} (correct {correct})"
        else:
            cands = list(it["primary"]["candidates"])
            res, ids = G.target_answer(target, it, max_new_tokens=choice_cap)
            actual, ev_a = parse_choice(res.raw_output, cands)
            res2, ids2, visible = self_guess_answer(target, it, self_guess_cap)
            guess, ev_g = parse_choice(res2.raw_output, cands)
            both = actual is not None and guess is not None
            row.update({
                "answer_text": res.raw_output, "actual": actual, "actual_evidence": ev_a,
                "self_guess_text": res2.raw_output, "self_guess": guess, "self_guess_evidence": ev_g,
                "candidates": cands, "first_listed": cands[0], "both_parsed": both,
                "disagree": bool(both and actual != guess),
                "n_prompt_tokens": res.n_prompt_tokens, "n_new_tokens": res.n_new_tokens, "finish_reason": res.finish_reason,
                "prompt_ids_sha256": C.sha256_ids(ids), "wall_s": res.wall_s, "peak_mem_gb": res.peak_mem_gb,
                "self_guess_n_prompt_tokens": res2.n_prompt_tokens, "self_guess_n_new_tokens": res2.n_new_tokens,
                "self_guess_finish_reason": res2.finish_reason, "self_guess_prompt_ids_sha256": C.sha256_ids(ids2),
                "self_guess_prompt_sha256": C.sha256_bytes(visible.encode("utf-8")), "self_guess_wall_s": res2.wall_s,
                "sampling": res.sampling, "model_sha": C.TARGET_MODEL_SHA, "adapter": "none",
            })
            led_c.add(res.n_prompt_tokens, res.n_new_tokens, res.wall_s, res.peak_mem_gb)
            led_s.add(res2.n_prompt_tokens, res2.n_new_tokens, res2.wall_s, res2.peak_mem_gb)
            shown = f"actual {actual} / self-guess {guess}"
        append_jsonl(target_path, row)
        n += 1
        print(f"[x3/target] {iid} -> {shown}", flush=True)
    for led in (led_p, led_c, led_s):
        r = led.flush(ledger_path)
        if log_path and r:
            log_line(log_path, f"{led.step}: {r}")
    return n


# ------------------------------------------------------------------ step 2: selection
def make_selected(item: dict[str, Any], set_: str, actual: str, other: str, text_key: str) -> dict[str, Any]:
    if actual is None or other is None or actual == other:
        raise ValueError(f"{item['item_id']}: candidates must be two distinct answers, got ({actual!r}, {other!r})")
    pr = item["primary"]
    src: dict[str, Any] = {}
    if item["family"] == "puzzle":
        src = {"correct": pr.get("correct"), "k": pr.get("k"), "start": pr.get("start"), "trace": pr.get("trace"),
               "distractors": _distractors(item)}
    else:
        src = {"options_listed": list(pr["candidates"]), "first_listed": pr["candidates"][0]}
    return {
        "item_id": item["item_id"], "pair_id": item["item_id"], "version": "A", "family": item["family"],
        "set": set_, "split": "test", "template_id": item.get("template_id"),
        "prompt_text": item["prompt_text"], "render": item.get("render", C.RENDER), "system": item.get("system"),
        "primary": {"name": "model_actual_answer", "question": pr.get("question"), "candidates": [actual, other],
                    "answer": actual, "answer_aliases": [actual.lower()], "answer_source": "target_greedy"},
        "text_key": text_key, "target_answer_regex": item.get("target_answer_regex"), "source": src,
    }


def control_other(item: dict[str, Any], correct: str, wrong_by_k: dict[Any, Counter], k: Any) -> tuple[str, str]:
    """The 'other' candidate of an ERROR_CONTROL puzzle: the most frequent wrong symbol among the
    ERROR items with the same k (ties by symbol order; never the item's own correct symbol),
    else the symbol visited one step before the end, else the first distractor / symbol != correct."""
    cnt = wrong_by_k.get(k) or Counter()
    for sym, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0])):
        if sym != correct:
            return sym, f"most frequent wrong symbol at k={k}"
    pre = pre_final_symbol(item)
    if pre and pre != correct:
        return pre, "(k-1)-trace symbol"
    for d in _distractors(item):
        if d != correct:
            return d, "first distractor"
    for s in SYMBOLS:
        if s != correct:
            return s, "first symbol != correct"
    raise ValueError("no other symbol")


def select(rows: list[dict[str, Any]], items: list[dict[str, Any]], seed: int = SELECTION_SEED,
           min_set: int = MIN_SET) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Step 2 (deterministic). Returns (selected items, selection meta)."""
    by_id = {it["item_id"]: it for it in items}
    rows = sorted((r for r in rows if r["item_id"] in by_id), key=lambda r: r["item_id"])
    puz = [r for r in rows if r["family"] == "puzzle"]
    cho = [r for r in rows if r["family"] == "choice"]
    # puzzles
    error = [r for r in puz if r.get("is_coherent") and r["parsed"] != r["correct"]]
    correct_pool = [r for r in puz if r.get("is_coherent") and r["parsed"] == r["correct"]]
    n_ctrl = min(len(error), len(correct_pool))
    ctrl = sorted(random.Random(seed).sample(correct_pool, n_ctrl), key=lambda r: r["item_id"]) if n_ctrl else []
    wrong_by_k: dict[Any, Counter] = {}
    for r in error:
        wrong_by_k.setdefault(r.get("k"), Counter())[r["parsed"]] += 1
    selected: list[dict[str, Any]] = []
    for r in error:
        selected.append(make_selected(by_id[r["item_id"]], "error", actual=r["parsed"], other=r["correct"], text_key=r["correct"]))
    ctrl_rules: Counter = Counter()
    for r in ctrl:
        other, rule = control_other(by_id[r["item_id"]], r["correct"], wrong_by_k, r.get("k"))
        ctrl_rules[rule] += 1
        sel = make_selected(by_id[r["item_id"]], "error_control", actual=r["correct"], other=other, text_key=r["correct"])
        sel["source"]["other_rule"] = rule
        selected.append(sel)
    # choice
    disagree = [r for r in cho if r.get("both_parsed") and r["actual"] != r["self_guess"]]
    agree_pool = [r for r in cho if r.get("both_parsed") and r["actual"] == r["self_guess"]]
    n_actrl = min(len(disagree), len(agree_pool))
    actrl = sorted(random.Random(seed).sample(agree_pool, n_actrl), key=lambda r: r["item_id"]) if n_actrl else []
    for r in disagree:
        sel = make_selected(by_id[r["item_id"]], "disagree", actual=r["actual"], other=r["self_guess"], text_key=r["self_guess"])
        sel["source"]["self_guess"] = r["self_guess"]
        selected.append(sel)
    for r in actrl:
        (other,) = [c for c in r["candidates"] if c != r["actual"]]
        sel = make_selected(by_id[r["item_id"]], "agree_control", actual=r["actual"], other=other, text_key=r["self_guess"])
        sel["source"]["self_guess"] = r["self_guess"]
        selected.append(sel)
    counts = {s: sum(x["set"] == s for x in selected) for s in SETS}
    meta = {
        "created": now_iso(), "seed": seed, "min_set": min_set, "counts": counts,
        "underpowered": {"error": counts["error"] < min_set, "disagree": counts["disagree"] < min_set},
        "puzzle": {"n_rows": len(puz), "n_coherent": sum(bool(r.get("is_coherent")) for r in puz), "n_error": len(error),
                   "n_correct": len(correct_pool), "n_incoherent": sum(not r.get("is_coherent") for r in puz),
                   "wrong_symbol_by_k": {str(k): dict(c) for k, c in sorted(wrong_by_k.items(), key=lambda kv: str(kv[0]))},
                   "control_other_rules": dict(ctrl_rules)},
        "choice": {"n_rows": len(cho), "n_both_parsed": sum(bool(r.get("both_parsed")) for r in cho), "n_disagree": len(disagree),
                   "n_agree": len(agree_pool), "n_unparsed": sum(not r.get("both_parsed") for r in cho)},
        "rule": ("ERROR = coherent puzzles with parsed != correct, candidates (actual, correct); ERROR_CONTROL = size-matched "
                 "correct puzzles sampled by seed, candidates (correct, most frequent wrong symbol at the same k else the "
                 "(k-1)-trace symbol); DISAGREE = choice items with self-guess != actual (both parsed), candidates "
                 "(actual, self-guess); AGREE_CONTROL = size-matched agree items sampled by seed, candidates (actual, other). "
                 f"K6: a set < {min_set} is underpowered (descriptive only)."),
    }
    return selected, meta


def write_selected(path: Path, selected: list[dict[str, Any]], meta: dict[str, Any]) -> Path:
    from projects.g_agreement.core.analysis_utils import canonical_items_sha

    out = {"meta": {**meta, "sha256_items": canonical_items_sha(selected), "n_items": len(selected), "frozen": False},
           "items": selected}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_selected(path: Path | str = SELECTED_JSON) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run phase A first")
    d = json.loads(p.read_text(encoding="utf-8"))
    for it in d["items"]:
        if it.get("set") not in SETS or it.get("family") not in FAMILIES or len(it["primary"]["candidates"]) != 2:
            raise ValueError(f"{it.get('item_id')}: malformed selected item")
    return d.get("meta", {}), d["items"]


# ------------------------------------------------------------------ step 3: LO
def lo_key(reader_name: str, item_id: str) -> str:
    return f"{reader_name}|{item_id}"


def collect_lo(reader: Any, selected: list[dict[str, Any]], *, lo_path: Path = LO_PATH, ledger_path: Path | None = None,
               log_path: Path | None = LOG, states_dir: Path | None = None, batch: int = 32,
               extra: dict[str, Any] | None = None) -> int:
    """Native LO of one reader on every selected item's cached state; candidates (actual, other).
    One row per (reader, item), key = reader|item_id; resumable."""
    import torch

    done = done_ids(lo_path, key="key")
    ledger = StepLedger(step=f"x3_lo_{reader.name}", module=MODULE, extra={"batch": batch})
    extra = dict(extra or {})
    n = 0
    for fam in FAMILIES:
        todo = [it for it in selected if it["family"] == fam and lo_key(reader.name, it["item_id"]) not in done]
        for s in range(0, len(todo), batch):
            chunk = todo[s: s + batch]
            H = torch.stack([S.load_state(it["item_id"], states_dir) for it in chunk])
            pairs = [(it["primary"]["candidates"][0], it["primary"]["candidates"][1]) for it in chunk]
            with timed_call() as st:
                rows = LO.score_lo(reader, H, pairs, fam, batch=batch)
            for it, r in zip(chunk, rows):
                row = {"key": lo_key(reader.name, it["item_id"]), "reader": reader.name, "item_id": it["item_id"],
                       "family": fam, "set": it["set"], "cand_actual": r["cand_A"], "cand_other": r["cand_B"],
                       "text_key": it.get("text_key"), "lo_actual": r["lo"], "lp_actual": r["lp_A"], "lp_other": r["lp_B"],
                       "favours_actual": (r["lo"] > 0) if r["lo"] is not None else None,
                       "templates": r["templates"], "unscorable": r["unscorable"], "layer": C.LAYER,
                       "wall_s_chunk": st.wall_s, "chunk_size": len(chunk), "created_at": now_iso(), **C.frozen_shas(), **extra}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason", "n_tokens_A", "n_tokens_B", "format"):
                    if k in r:
                        row[k] = r[k]
                append_jsonl(lo_path, row)
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
            print(f"[x3/lo/{reader.name}] {fam}: {len(chunk)} states scored ({s + len(chunk)}/{len(todo)})", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"lo {reader.name}: {r}")
    return n


# ------------------------------------------------------------------ freeze (X manifest)
def _flatten(d: Any, prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(d, dict):
        for k, v in d.items():
            out += _flatten(v, f"{prefix}.{k}" if prefix else str(k))
    else:
        out.append((prefix, d))
    return out


def frozen_x_status(candidates_path: Path | str, manifest: Path = FROZEN_CONFIG_X) -> tuple[bool, str]:
    """(ok, note). ok iff the X manifest exists, is frozen, and every recorded x3 candidates sha
    (any key mentioning 'x3') matches the file on disk."""
    sha = C.sha256_file(candidates_path)
    if not Path(manifest).exists():
        return False, f"{Path(manifest).name} missing (freeze X before test collection)"
    fz = json.loads(Path(manifest).read_text(encoding="utf-8"))
    if not fz.get("frozen"):
        return False, f"{Path(manifest).name}: frozen is false"
    recorded = [(k, v) for k, v in _flatten(fz) if "x3" in k.lower() and isinstance(v, str) and len(v) == 64]
    if not recorded:
        return True, f"{Path(manifest).name}: no x3 candidates sha recorded (accepted; sha {str(sha)[:12]} written per row)"
    if any(v == sha for _, v in recorded):
        return True, "candidates sha matches the X manifest"
    return False, f"candidates sha {str(sha)[:12]} differs from the X manifest ({recorded[0][0]}={recorded[0][1][:12]})"


def selected_path_for(limit: int) -> Path:
    return SELECTED_JSON if not limit else SELECTED_JSON.with_name(f"items_x3_selected_limit{limit}.json")


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--candidates", default=str(CANDIDATES_JSON))
    ap.add_argument("--limit", type=int, default=0, help="first N puzzles and first N choice items (smoke run)")
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--skip-lo", action="store_true")
    ap.add_argument("--batch", type=int, default=32)
    a = ap.parse_args(argv)
    ok, note = frozen_x_status(a.candidates)
    if not ok and not a.allow_unfrozen:
        raise SystemExit(f"refusing to collect X3: {note} (pass --allow-unfrozen for a smoke run)")
    meta, items = load_candidates(a.candidates, a.limit)
    X_DIR.mkdir(parents=True, exist_ok=True)
    extra = {"candidates_file": str(a.candidates), "candidates_sha256": C.sha256_file(a.candidates),
             "manifest_x": Path(FROZEN_CONFIG_X).name if ok else None, "frozen_x": ok}
    sel_path = selected_path_for(a.limit)
    n_puz = sum(it["family"] == "puzzle" for it in items)
    n_cho = len(items) - n_puz
    print(f"X3 phase {a.phase}: {n_puz} puzzles + {n_cho} choice candidates; freeze: {note}; shas={C.frozen_shas()}", flush=True)
    if a.phase == "A":
        target = load_target_timed(MODULE)
        log_line(LOG, f"phase A: {n_puz} puzzles + {n_cho} choice candidates (limit={a.limit}); freeze: {note}; "
                      f"caps puzzle={PUZZLE_CAP} choice={CHOICE_CAP} self_guess={SELF_GUESS_CAP}")
        n_new = collect_target(target, items, extra=extra)
        rows = read_jsonl(TARGET_PATH)
        selected, smeta = select(rows, items)
        smeta.update(candidates_file=str(a.candidates), candidates_sha256=extra["candidates_sha256"], limit=a.limit)
        write_selected(sel_path, selected, smeta)
        msg = (f"selection ({n_new} new decodes): counts {smeta['counts']}; underpowered {smeta['underpowered']}; "
               f"puzzle {smeta['puzzle']['n_error']} error / {smeta['puzzle']['n_correct']} correct / "
               f"{smeta['puzzle']['n_incoherent']} incoherent of {smeta['puzzle']['n_rows']}; "
               f"choice {smeta['choice']['n_disagree']} disagree / {smeta['choice']['n_agree']} agree / "
               f"{smeta['choice']['n_unparsed']} unparsed of {smeta['choice']['n_rows']} -> {sel_path.name}")
        print(f"[x3] {msg}", flush=True)
        log_line(LOG, msg)
        for s, under in smeta["underpowered"].items():
            if under:
                log_line(LOG, f"K6: {s} set has {smeta['counts'][s]} < {MIN_SET} items: reported descriptively only")
        if not selected:
            log_line(LOG, "no items selected; nothing to capture")
            M.unload(target)
            return 0
        S.ensure_states(target, selected, module=MODULE)
        log_line(LOG, f"states cached for {len(selected)} selected items")
        if not a.skip_lo:
            jl = R.JLensReader().bind(target)
            collect_lo(jl, selected, batch=a.batch, extra=extra)
            del jl
            ol = R.OLensReader().bind(target)
            log_line(LOG, f"olens adapter={ol.adapter_dir} liveness={ol.liveness}")
            collect_lo(ol, selected, batch=a.batch, extra=extra)
        M.unload(target)
    else:
        smeta, selected = load_selected(sel_path)
        missing = [it["item_id"] for it in selected if not S.state_path(it["item_id"]).exists()]
        if missing:
            raise SystemExit(f"missing cached states {missing[:4]} (+{max(0, len(missing) - 4)}); run phase A first")
        ledger = StepLedger(step="load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader().bind()
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        log_line(LOG, f"phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}; {len(selected)} selected items; "
                      f"puzzle templates {LO.templates_for('puzzle')}")
        if not a.skip_lo:
            collect_lo(nla, selected, batch=a.batch, extra=extra)
        nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
