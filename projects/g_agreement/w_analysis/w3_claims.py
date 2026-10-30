"""W3 — claim-level precision on the S4 samples (PREREG_WV.md Track C / "Analysis", brief_wv.md "W3").

Two sub-commands:

    # 1. before judging: pick the S4 samples to judge, merge the prompt text in, estimate the OpenRouter cost
    python -m projects.g_agreement.w_analysis.w3_claims prepare [--s4 cache/g_agreement/w/s4_samples.jsonl]
        [--items-y1 projects/g_agreement/dataset/items_y1_selected.json] [--items-w projects/g_agreement/banks/w/items_w.json]
        [--out results/g_agreement/w/w3] [--cap-usd 8] [--cost-per-call 0.17/96] [--subset 60,30] [--seed 0]
      -> <out>/s4_judge_input.jsonl (the rows for projects.g_agreement.w_claims.judge, prompt_text/question merged in),
         <out>/s4_judge_plan.json (n_calls, estimate, decision), and the exact judge command on stdout.
    # 2. after judging: the W3 report
    python -m projects.g_agreement.w_analysis.w3_claims report [--claims results/g_agreement/w/w3/claims_s4.jsonl]
        [--s3 cache/g_agreement/w/s3_lo.jsonl] [--x3-lo cache/g_agreement/x/x3_lo.jsonl] [--g1 results/g_agreement/w/claims/W3_g1.json]
        [--out results/g_agreement/w/w3] [--n-boot 1000 --seed 0]
      -> <out>/{w3.md, w3.csv, w3_summary.json}

Budget rule (fixed before the pod files arrived): judge only the 8 natural samples of every S4 state plus the random-vector samples
(1 per reader per random vector); cost estimate = n_calls x (Track C's $0.167368 / 96 calls = $0.00174 per call); if the estimate
exceeds the cap ($8) judge a seeded subset of 60 error + 30 counts states (numpy default_rng(seed) over the sorted ids, the recipe of
w_pod.common.seeded_subset) and say so in the plan. 150 states x 8 x 2 readers + 100 random = 2,500 calls = $4.36 -> full set.

What W3 reports (per reader Oracle / NLA, item = S4 state, 8 samples pooled per state, CI = item-level bootstrap, 1,000 resamples):
- Error states (the model's greedy answer is WRONG; answer = the puzzle's correct symbol, actual_answer = the model's symbol):
  input-claim precision (judge label); computation-claim precision AGAINST THE ACTUAL answer = the judge's computation_true /
  computation_false (the judge saw the actual answer and labels computation claims against it); computation-claim precision
  AGAINST THE CORRECT answer = judge-anchored relabel: a computation claim is true-vs-correct iff the judge called it
  computation_false (it does not name the actual) AND its text names the correct symbol and not the actual one; otherwise false.
  Both are reported because "true about what the model computes" != "true about the puzzle". A text-only check (which candidate
  the claim names, by regex) is reported next to the judge for both references, with its agreement with the judge.
- Counts states (value 1-99; the model is correct, so actual = value): input precision; computation precision = the judge's label
  (vs the value) and, as the text check, the first integer stated in the claim (digits or number words) == value.
- Cross-tab with the native log-odds of the SAME reader on the SAME state: errors -> favours_actual (S3 rows: unit S2, condition
  natural, family errors, read layer 42, lo toward the actual candidate > 0; states not covered by S3 fall back to the X3 layer-42
  rows cache/g_agreement/x/x3_lo.jsonl, source recorded per state); counts -> argmax of the S3 S1 score vector over '1'..'99' ==
  value. Cells: within states where the native LO favours the actual (resp. is exact) and where it does not, the computation
  precision and the share of states whose free text names the actual / the value; plus the state-level agreement between the two
  readings (Wilson CI).
- The G1 numbers (results/g_agreement/w/claims/W3_g1.json; binding facts where actual = key) are copied into the same table.
Nothing here is a raw-rate headline: every number sits next to the other reader, the other reference and the native reading.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

from projects.g_agreement.w_claims.stats import precision_item_bootstrap, wilson

REPO = Path(__file__).resolve().parents[3]
PROJECT_DIR = REPO / "projects" / "g_agreement"
CACHE_W = REPO / "cache" / "g_agreement" / "w"
RESULTS_W = REPO / "results" / "g_agreement" / "w"
S4_SAMPLES = CACHE_W / "s4_samples.jsonl"
S3_LO = CACHE_W / "s3_lo.jsonl"
X3_LO = REPO / "cache" / "g_agreement" / "x" / "x3_lo.jsonl"
ITEMS_Y1 = PROJECT_DIR / "dataset" / "items_y1_selected.json"
ITEMS_W = PROJECT_DIR / "banks" / "w" / "items_w.json"
G1_W3 = RESULTS_W / "claims" / "W3_g1.json"
OUT_W3 = RESULTS_W / "w3"
CLAIMS_S4 = OUT_W3 / "claims_s4.jsonl"

TRACK_C_COST_USD, TRACK_C_CALLS = 0.167368, 96          # results/g_agreement/w/claims/judge_usage.json (gemini-3.8-flash)
COST_PER_CALL = TRACK_C_COST_USD / TRACK_C_CALLS
CAP_USD = 8.0
SUBSET_ERRORS, SUBSET_COUNTS = 60, 30
N_SAMPLES = 8
N_BOOT, SEED = 1000, 0
READER_NAMES = {"olens": "Oracle", "oracle": "Oracle", "Oracle": "Oracle", "nla": "NLA", "NLA": "NLA"}
READERS: Tuple[str, ...] = ("Oracle", "NLA")
FAMILIES: Tuple[str, ...] = ("errors", "counts")

_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
          "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
          "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_NUMWORD_RE = re.compile(r"\b(" + "|".join(sorted(_TENS, key=len, reverse=True)) + r")(?:[-\s](" + "|".join(_UNITS) + r"))?\b|\b("
                         + "|".join(sorted(_UNITS, key=len, reverse=True)) + r")\b", re.I)


# ----------------------------------------------------------------------------------------------- small helpers
def read_jsonl(path: Path) -> List[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def reader_name(r: Any) -> str:
    return READER_NAMES.get(str(r), str(r))


def seeded_subset(ids: Sequence[str], n: int, seed: int = 0) -> List[str]:
    """``n`` ids drawn without replacement from the SORTED list by numpy default_rng(seed) (w_pod.common.seeded_subset)."""
    ids = sorted(ids)
    if n >= len(ids):
        return list(ids)
    rng = np.random.default_rng(int(seed))
    idx = rng.choice(len(ids), size=int(n), replace=False)
    return [ids[int(i)] for i in sorted(idx)]


def words_to_digits(text: str) -> str:
    """Replace English number words 0-99 ("twenty-seven", "seven") by digits; everything else untouched."""
    def rep(m: "re.Match[str]") -> str:
        if m.group(3):
            return str(_UNITS[m.group(3).lower()])
        v = _TENS[m.group(1).lower()] + (_UNITS[m.group(2).lower()] if m.group(2) else 0)
        return str(v)
    return _NUMWORD_RE.sub(rep, text or "")


def integers_in(text: str) -> List[int]:
    """Integers stated in a claim (digits after number-word conversion), in order; decimals/ids like 3.5 or 42:0 are skipped."""
    t = words_to_digits(text)
    return [int(m.group(0)) for m in re.finditer(r"(?<![\d.:])\d{1,3}(?![\d.:])", t)]


_SYMBOL_CUE = r"(?:symbol|letter|answer|is|at|to|from|reach|reaches|reached|output|outputs|end|ends|->|→|=|:)\s*"


def symbol_mentioned(text: str, letter: str) -> bool:
    """Is the single-letter puzzle symbol ``letter`` named in ``text``? Case-sensitive standalone capital, or quoted in either
    case. The capitals "A" and "I" double as English words, so they count only when quoted, preceded by a cue word/arrow
    ("symbol A", "is A", "-> A"), or followed by an arrow / punctuation / the end ("A -> B", "... reach A.")."""
    if not text or not letter:
        return False
    up = letter.upper()
    if re.search(rf"[\'\"`‘’“”]{re.escape(letter)}[\'\"`‘’“”]", text, re.I):
        return True
    if up not in ("A", "I"):
        return re.search(rf"(?<![A-Za-z]){up}(?![A-Za-z])", text) is not None
    if re.search(_SYMBOL_CUE + rf"{up}(?![A-Za-z])", text, re.I):
        return True
    return re.search(rf"(?<![A-Za-z]){up}\s*(?:->|→|[.,;:!?)]|$)", text) is not None


def mentions(text: str, candidate: Any) -> bool:
    """Does the claim text name ``candidate``? Single letters (puzzle symbols) via symbol_mentioned; numbers match as
    standalone integers (digits or number words); other strings match as whole words, case-insensitively."""
    if candidate is None or text is None:
        return False
    c = str(candidate).strip()
    if not c:
        return False
    if re.fullmatch(r"\d+", c):
        return int(c) in integers_in(text)
    if len(c) == 1 and c.isalpha():
        return symbol_mentioned(text, c)
    return re.search(rf"(?<![\w]){re.escape(c)}(?![\w])", text, re.I) is not None


def claim_names(text: str, candidates: Optional[Sequence[Any]]) -> Set[str]:
    return {str(c) for c in (candidates or []) if mentions(text, c)}


# ----------------------------------------------------------------------------------------------- items / samples
def load_item_prompts(items_y1: Optional[Path] = ITEMS_Y1, items_w: Optional[Path] = ITEMS_W) -> Dict[str, dict]:
    """item_id -> {prompt_text, question, value|correct} for the error items (Y1 selected) and the counts items (W bank)."""
    out: Dict[str, dict] = {}
    for p in (items_y1, items_w):
        if p is None or not Path(p).exists():
            continue
        raw = json.loads(Path(p).read_text(encoding="utf-8"))
        for it in (raw.get("items", raw) if isinstance(raw, dict) else raw):
            pr = it.get("primary") or {}
            out[it["item_id"]] = {"prompt_text": it.get("prompt_text") or "", "question": pr.get("question"), "family": it.get("family"),
                                  "correct": (it.get("source") or {}).get("correct"), "model_answer": pr.get("answer")}
    return out


def select_judge_rows(samples: List[dict], items: Dict[str, dict], *, cap_usd: float = CAP_USD, cost_per_call: float = COST_PER_CALL,
                      subset: Tuple[int, int] = (SUBSET_ERRORS, SUBSET_COUNTS), seed: int = SEED, n_samples: int = N_SAMPLES) -> Tuple[List[dict], dict]:
    """The S4 rows to judge: the first ``n_samples`` natural samples of every state for both readers + every random-vector sample.
    Merges prompt_text/question from the items and sets gen_id = Reader|state|s<k>. Applies the budget rule (docstring)."""
    nat = [r for r in samples if r.get("condition") == "natural" and int(r.get("sample_idx", 0)) < n_samples]
    rnd = [r for r in samples if r.get("condition") == "random"]
    states = {f: sorted({r["state_item_id"] for r in nat if r.get("family") == f}) for f in FAMILIES}
    n_full = len(nat) + len(rnd)
    est_full = n_full * cost_per_call
    chosen = {f: states[f] for f in FAMILIES}
    decision = "full"
    if est_full > cap_usd:
        chosen = {"errors": seeded_subset(states["errors"], subset[0], seed), "counts": seeded_subset(states["counts"], subset[1], seed)}
        decision = f"subset {subset[0]} errors + {subset[1]} counts (seed {seed})"
    keep_ids = {i for f in FAMILIES for i in chosen[f]}
    rows = []
    for r in nat + rnd:
        if r.get("condition") == "natural" and r["state_item_id"] not in keep_ids:
            continue
        it = items.get(r["state_item_id"], {})
        rd = reader_name(r["reader"])
        row = {"gen_id": f"{rd}|{r['state_item_id']}|s{int(r.get('sample_idx', 0))}", "state_item_id": r["state_item_id"], "reader": rd,
               "sample_idx": int(r.get("sample_idx", 0)), "text": r.get("text") or "", "candidates": r.get("candidates"), "answer": r.get("answer"),
               "actual_answer": r.get("actual_answer"), "condition": r.get("condition"), "family": r.get("family"), "layer": r.get("layer"),
               "module": "s4", "prompt_text": r.get("prompt_text") or it.get("prompt_text") or "", "question": r.get("question") or it.get("question")}
        rows.append(row)
    n_calls = len(rows)
    plan = {"n_samples_in_file": len(samples), "n_natural_candidates": len(nat), "n_random": len(rnd),
            "n_states": {f: len(states[f]) for f in FAMILIES}, "n_states_judged": {f: len(chosen[f]) for f in FAMILIES},
            "cost_per_call_usd": cost_per_call, "cost_formula": f"n_calls x ${cost_per_call:.5f} (Track C: ${TRACK_C_COST_USD} / {TRACK_C_CALLS} calls)",
            "cap_usd": cap_usd, "estimate_full_usd": round(est_full, 3), "n_calls_full": n_full, "decision": decision,
            "n_calls": n_calls, "estimate_usd": round(n_calls * cost_per_call, 3), "estimate_x1.5_usd": round(1.5 * n_calls * cost_per_call, 3),
            "missing_prompt_text": sum(1 for r in rows if r["condition"] == "natural" and not r["prompt_text"]), "seed": seed}
    return rows, plan


def judge_command(inp: Path, out: Path, out_dir: Path) -> str:
    return ("zsh -ic 'cd " + str(REPO) + " && PYTHONPATH=. .venv/bin/python -m projects.g_agreement.w_claims.judge "
            f"--readouts {inp} --items none --actual none --readers Oracle,NLA --out {out} "
            f"--usage {out_dir / 'judge_usage.json'} --cache {out_dir / 'cache' / 'judge_cache.jsonl'}'")


# ----------------------------------------------------------------------------------------------- claims
def load_claims(path: Path) -> List[dict]:
    """Judge output rows (incl. the '#none' rows for claim-less readouts) with reader names normalised and the text checks
    attached: names_actual, names_correct (errors), stated (counts: first integer in the claim)."""
    out = []
    for c in read_jsonl(path):
        c = dict(c)
        c["reader"] = reader_name(c.get("reader"))
        c["family"] = c.get("family") or ("random" if str(c.get("item_id", "")).startswith("random-") else None)
        if c.get("condition") is None:
            c["condition"] = "random" if c["family"] == "random" else "natural"
        t = c.get("claim_text")
        if t:
            cands = c.get("candidates") or []
            names = claim_names(t, cands)
            c["names_actual"] = (str(c.get("actual_answer")) in names) if c.get("actual_answer") is not None else None
            c["names_correct"] = (str(c.get("answer")) in names) if c.get("answer") is not None else None
            ints = integers_in(t)
            c["stated"] = ints[0] if ints else None
        out.append(c)
    return out


def computation_truths(c: dict) -> dict:
    """The truth of a computation claim under each reference. vs_actual_judge = the judge's label (seen with the actual answer).
    vs_correct_judge (errors) = judge-anchored: computation_false AND names the correct symbol and not the actual.
    vs_actual_text / vs_correct_text = text-only (None when the claim names both candidates or neither).
    vs_value (counts) = judge label; vs_value_text = first integer == value."""
    truth = c.get("truth")
    na, nc = c.get("names_actual"), c.get("names_correct")
    out = {"vs_actual_judge": truth}
    if c.get("family") == "counts":
        val = c.get("answer")
        out["vs_value_judge"] = truth
        out["vs_value_text"] = (None if c.get("stated") is None or val is None else int(c["stated"]) == int(str(val)))
        return out
    if truth is None:
        out["vs_correct_judge"] = None
    else:
        out["vs_correct_judge"] = bool((truth is False) and nc and not na)
    out["vs_actual_text"] = (None if (na and nc) or (not na and not nc) else bool(na))
    out["vs_correct_text"] = (None if (na and nc) or (not na and not nc) else bool(nc))
    return out


def precision_block(claims: List[dict], key: str, n_boot: int, seed: int) -> dict:
    pairs = [(c["item_id"], computation_truths(c).get(key)) for c in claims]
    return precision_item_bootstrap([i for i, _ in pairs], [t for _, t in pairs], n_boot, seed)


def state_table(claims: List[dict]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """(reader, state) -> {family, samples: {sample_idx: [claims]}} over natural claims (claim-less readouts give empty lists)."""
    st: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for c in claims:
        if c.get("condition") != "natural":
            continue
        k = (c["reader"], c["item_id"])
        d = st.setdefault(k, {"family": c.get("family"), "samples": {}, "answer": c.get("answer"), "actual_answer": c.get("actual_answer")})
        lst = d["samples"].setdefault(int(c.get("sample_idx", 0)), [])
        if c.get("claim_text"):
            lst.append(c)
    return st


# ----------------------------------------------------------------------------------------------- native LO
def native_lo(s3_rows: List[dict], x3_rows: List[dict], actual_of: Dict[str, Any]) -> Dict[Tuple[str, str], dict]:
    """(reader, state) -> {ok: bool, source, value}. Errors: favours_actual (S3 unit S2 natural rows at read layer 42; else the X3
    layer-42 rows). Counts: argmax of the S3 S1 score vector == the value."""
    out: Dict[Tuple[str, str], dict] = {}
    for r in s3_rows:
        rd = reader_name(r.get("reader"))
        if rd not in READERS:
            continue
        fam, unit = r.get("family"), str(r.get("unit") or "")
        if fam == "errors" and unit == "S2" and str(r.get("direction") or r.get("condition")) == "natural":
            lo = r.get("lo_own")
            if lo is None:
                continue
            sid = r.get("state_item_id") or r.get("item_id")
            act = str(actual_of.get(sid, r.get("cand_A")))
            if str(r.get("cand_A")) == act:
                fav = lo > 0
            elif str(r.get("cand_B")) == act:
                fav = lo < 0
            else:
                continue
            out[(rd, sid)] = {"ok": bool(fav), "source": "s3_lo:S2 natural L42", "value": float(lo)}
        elif fam == "counts" and unit == "S1":
            am, tv = r.get("argmax"), r.get("true_answer")
            if am is None or tv is None:
                continue
            out[(rd, r.get("item_id"))] = {"ok": str(am) == str(tv), "source": "s3_lo:S1 argmax", "value": str(am)}
    for r in x3_rows:
        rd = reader_name(r.get("reader"))
        if rd not in READERS or r.get("set") != "error" or r.get("favours_actual") is None:
            continue
        out.setdefault((rd, r["item_id"]), {"ok": bool(r["favours_actual"]), "source": "x3_lo:L42", "value": r.get("lo_actual")})
    return out


# ----------------------------------------------------------------------------------------------- W3 summary
def _rate(k: int, n: int) -> dict:
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (None if n == 0 else p), "lo": (None if n == 0 else lo), "hi": (None if n == 0 else hi)}


def _agreement(pairs: List[Tuple[Optional[bool], Optional[bool]]]) -> dict:
    ps = [(a, b) for a, b in pairs if a is not None and b is not None]
    return dict(_rate(sum(a == b for a, b in ps), len(ps)), n_pairs=len(ps))


def summarise(claims: List[dict], lo: Dict[Tuple[str, str], dict], g1: Optional[dict] = None, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    real = [c for c in claims if c.get("claim_text") and c.get("condition") == "natural"]
    states = state_table(claims)
    out: Dict[str, Any] = {"n_boot": n_boot, "seed": seed, "readers": {}, "text_check_agreement": {}, "g1": {}}
    for rd in READERS:
        R: Dict[str, Any] = {}
        for fam in FAMILIES:
            cs = [c for c in real if c["reader"] == rd and c.get("family") == fam]
            sts = {k: v for k, v in states.items() if k[0] == rd and v["family"] == fam}
            comp = [c for c in cs if c.get("claim_type") == "computation"]
            inp = [c for c in cs if c.get("claim_type") == "input"]
            d: Dict[str, Any] = {"n_states": len(sts), "n_readouts": sum(len(v["samples"]) for v in sts.values()), "n_claims": len(cs),
                                 "claims_per_readout": len(cs) / max(1, sum(len(v["samples"]) for v in sts.values())),
                                 "share": {t: sum(c.get("claim_type") == t for c in cs) / max(1, len(cs)) for t in ("input", "computation", "unverifiable")},
                                 "label_counts": dict(Counter(c.get("judge_label") for c in cs)), "precision": {}}
            d["precision"]["input"] = precision_item_bootstrap([c["item_id"] for c in inp], [c.get("truth") for c in inp], n_boot, seed)
            keys = ("vs_actual_judge", "vs_correct_judge", "vs_actual_text", "vs_correct_text") if fam == "errors" else ("vs_value_judge", "vs_value_text")
            for k in keys:
                d["precision"][f"computation_{k}"] = precision_block(comp, k, n_boot, seed)
            if fam == "errors":
                d["computation_names"] = {"actual_only": sum(1 for c in comp if c.get("names_actual") and not c.get("names_correct")),
                                          "correct_only": sum(1 for c in comp if c.get("names_correct") and not c.get("names_actual")),
                                          "both": sum(1 for c in comp if c.get("names_actual") and c.get("names_correct")),
                                          "neither": sum(1 for c in comp if not c.get("names_actual") and not c.get("names_correct"))}
                out["text_check_agreement"][f"{rd}/{fam}"] = _agreement([(computation_truths(c)["vs_actual_judge"], computation_truths(c)["vs_actual_text"]) for c in comp])
            else:
                d["computation_names"] = {"states_number": sum(1 for c in comp if c.get("stated") is not None), "no_number": sum(1 for c in comp if c.get("stated") is None)}
                out["text_check_agreement"][f"{rd}/{fam}"] = _agreement([(computation_truths(c)["vs_value_judge"], computation_truths(c)["vs_value_text"]) for c in comp])
            # state-level free-text reading: share of the state's samples with >= 1 computation claim naming the actual / value
            text_ok = {}
            for (r_, sid), v in sts.items():
                flags = [any(c.get("judge_label") == "computation_true" for c in cl) for cl in v["samples"].values()]
                text_ok[sid] = (sum(flags) / len(flags)) if flags else None
            d["state_text_names_actual"] = {"any_sample": _rate(sum(1 for v in text_ok.values() if v), len(text_ok)),
                                            "majority_of_samples": _rate(sum(1 for v in text_ok.values() if v is not None and v > 0.5), len(text_ok))}
            # cross-tab with the native LO of the same reader on the same state
            xt: Dict[str, Any] = {"n_states_with_lo": 0, "sources": {}, "cells": {}}
            lo_states = {sid: lo[(rd, sid)] for (_, sid) in sts if (rd, sid) in lo}
            xt["n_states_with_lo"] = len(lo_states)
            xt["sources"] = dict(Counter(v["source"] for v in lo_states.values()))
            for ok in (True, False):
                sids = {s for s, v in lo_states.items() if v["ok"] is ok}
                cc = [c for c in comp if c["item_id"] in sids]
                cell = {"n_states": len(sids), "computation_precision": {k: precision_block(cc, k, n_boot, seed) for k in keys},
                        "states_text_names_actual_any": _rate(sum(1 for s in sids if text_ok.get(s)), len(sids)),
                        "states_text_names_actual_majority": _rate(sum(1 for s in sids if (text_ok.get(s) or 0) > 0.5), len(sids))}
                name = (("lo_favours_actual" if ok else "lo_favours_correct") if fam == "errors" else ("lo_exact" if ok else "lo_not_exact"))
                xt["cells"][name] = cell
            xt["agreement_lo_vs_text_majority"] = _agreement([(lo_states[s]["ok"], (text_ok.get(s) or 0) > 0.5) for s in lo_states if text_ok.get(s) is not None])
            xt["lo_rate"] = _rate(sum(1 for v in lo_states.values() if v["ok"]), len(lo_states))
            d["crosstab_native_lo"] = xt
            R[fam] = d
        out["readers"][rd] = R
    if g1:
        for rd, d in (g1.get("summary") or {}).get("readers", {}).items():
            out["g1"][reader_name(rd)] = {"n_items": d.get("n_items"), "n_claims": d.get("n_claims"), "input": d["precision"].get("input"),
                                         "computation": d["precision"].get("computation")}
    return out


# ----------------------------------------------------------------------------------------------- rendering
def fmt_p(p: Optional[dict]) -> str:
    if not p or p.get("precision") is None:
        return "n/a"
    return f"{100 * p['precision']:.0f}% [{100 * p['lo']:.0f}, {100 * p['hi']:.0f}] (n={p['n_claims']})"


def fmt_r(r: Optional[dict]) -> str:
    if not r or r.get("rate") is None:
        return "n/a"
    return f"{100 * r['rate']:.0f}% [{100 * r['lo']:.0f}, {100 * r['hi']:.0f}] ({r['k']}/{r['n']})"


def csv_rows(s: dict) -> List[dict]:
    rows = []
    for rd, g in s.get("g1", {}).items():
        for t in ("input", "computation"):
            p = g.get(t) or {}
            rows.append({"source": "G1 test (binding facts, actual = key)", "reader": rd, "family": "g1", "claim_type": t, "reference": "key",
                         "n_items": p.get("n_items"), "n_claims": p.get("n_claims"), "n_true": p.get("n_true"), "precision": p.get("precision"), "lo": p.get("lo"), "hi": p.get("hi")})
    for rd, R in s["readers"].items():
        for fam, d in R.items():
            for k, p in d["precision"].items():
                t = "input" if k == "input" else "computation"
                ref = "key" if k == "input" else k.replace("computation_", "")
                rows.append({"source": f"S4 {fam}", "reader": rd, "family": fam, "claim_type": t, "reference": ref, "n_items": p.get("n_items"),
                             "n_claims": p.get("n_claims"), "n_true": p.get("n_true"), "precision": p.get("precision"), "lo": p.get("lo"), "hi": p.get("hi")})
    return rows


def render_md(s: dict, inputs: dict, notes: Sequence[str] = ()) -> str:
    L = ["# W3 — claim precision on the S4 samples (input vs computation claims), with the G1 numbers", "",
         "Judge: `google/gemini-3.8-flash` via `projects/g_agreement/w_claims/judge.py` (Track C; adapted from Michael Kenney's "
         "`nla-consistency/scripts/claim_judge.py`). Precision = true / (true + false) pooled over claims, 8 samples per state; CI = state-level "
         f"bootstrap ({s['n_boot']} resamples, seed {s['seed']}); unverifiable claims excluded. On the ERROR states the model's greedy answer is wrong: "
         "computation claims are scored against the model's ACTUAL answer (the judge's label) and separately against the puzzle's CORRECT answer "
         "(judge-anchored relabel: computation_false AND the text names the correct symbol, not the actual). Counts: the model is correct, "
         "so 'actual' = the value. A text-only check (which candidate the claim names) sits next to each judge number.", "",
         "Inputs: " + ", ".join(f"{k}={v}" for k, v in inputs.items() if v), "",
         "## Precision table (one row per source x reader)", "",
         "| source | reader | states | claims | input prec. [CI] | computation vs ACTUAL [CI] | computation vs CORRECT / VALUE [CI] | text check vs actual | text check vs correct/value |",
         "|---|---|---|---|---|---|---|---|---|"]
    for rd, g in s.get("g1", {}).items():
        L.append(f"| G1 test (binding facts; actual = key) | {rd} | {g.get('n_items')} | {g.get('n_claims')} | {fmt_p(g.get('input'))} | {fmt_p(g.get('computation'))} | "
                 f"(same: actual = key) | — | — |")
    for rd, R in s["readers"].items():
        for fam, d in R.items():
            P = d["precision"]
            if fam == "errors":
                L.append(f"| S4 errors | {rd} | {d['n_states']} | {d['n_claims']} | {fmt_p(P['input'])} | {fmt_p(P['computation_vs_actual_judge'])} | "
                         f"{fmt_p(P['computation_vs_correct_judge'])} | {fmt_p(P['computation_vs_actual_text'])} | {fmt_p(P['computation_vs_correct_text'])} |")
            else:
                L.append(f"| S4 counts | {rd} | {d['n_states']} | {d['n_claims']} | {fmt_p(P['input'])} | {fmt_p(P['computation_vs_value_judge'])} | "
                         f"(same: actual = value) | {fmt_p(P['computation_vs_value_text'])} | — |")
    L += ["", "## Claim mix and what the computation claims name", "",
          "| reader | family | readouts | claims/readout | input | computation | unverifiable | computation claims naming: | states: text names actual (any sample) | (majority of samples) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for rd, R in s["readers"].items():
        for fam, d in R.items():
            nm = ", ".join(f"{k} {v}" for k, v in d["computation_names"].items())
            st = d["state_text_names_actual"]
            L.append(f"| {rd} | {fam} | {d['n_readouts']} | {d['claims_per_readout']:.1f} | {100 * d['share']['input']:.0f}% | {100 * d['share']['computation']:.0f}% | "
                     f"{100 * d['share']['unverifiable']:.0f}% | {nm} | {fmt_r(st['any_sample'])} | {fmt_r(st['majority_of_samples'])} |")
    L += ["", "Text check vs judge (computation claims, agreement on truth where both decide): " +
          "; ".join(f"{k}: {fmt_r(v)}" for k, v in s["text_check_agreement"].items()), "",
          "## Cross-tab with the native log-odds of the same reader on the same state", "",
          "Errors: native LO favours the model's actual answer (S3 natural rows at the block-42 read-back; X3 layer-42 rows where S3 has none). "
          "Counts: argmax of the native score vector over 1..99 equals the value.", "",
          "| reader | family | LO cell | states | computation vs actual [CI] | vs correct [CI] | states whose text names the actual/value (any sample) | (majority) |",
          "|---|---|---|---|---|---|---|---|"]
    for rd, R in s["readers"].items():
        for fam, d in R.items():
            xt = d["crosstab_native_lo"]
            for cell, v in xt["cells"].items():
                P = v["computation_precision"]
                a = P.get("vs_actual_judge") or P.get("vs_value_judge")
                b = P.get("vs_correct_judge")
                L.append(f"| {rd} | {fam} | {cell} | {v['n_states']} | {fmt_p(a)} | {fmt_p(b) if b else '(= value)'} | "
                         f"{fmt_r(v['states_text_names_actual_any'])} | {fmt_r(v['states_text_names_actual_majority'])} |")
    L += [""]
    for rd, R in s["readers"].items():
        for fam, d in R.items():
            xt = d["crosstab_native_lo"]
            L.append(f"- {rd}/{fam}: native LO available for {xt['n_states_with_lo']} states ({', '.join(f'{k}: {v}' for k, v in xt['sources'].items()) or 'none'}); "
                     f"LO {'favours actual' if fam == 'errors' else 'exact'} on {fmt_r(xt['lo_rate'])}; agreement between the LO reading and the free text "
                     f"(majority of samples names the actual/value): {fmt_r(xt['agreement_lo_vs_text_majority'])}.")
    if notes:
        L += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    return "\n".join(L) + "\n"


def run_report(*, claims_path: Path = CLAIMS_S4, s3: Path = S3_LO, x3: Path = X3_LO, g1: Path = G1_W3, items_y1: Path = ITEMS_Y1, items_w: Path = ITEMS_W,
               out_dir: Path = OUT_W3, n_boot: int = N_BOOT, seed: int = SEED, notes: Sequence[str] = ()) -> dict:
    claims = load_claims(claims_path)
    if not claims:
        raise SystemExit(f"no judged claims at {claims_path}; run `prepare` and the judge first")
    actual_of = {c["item_id"]: c.get("actual_answer") for c in claims if c.get("actual_answer") is not None}
    lo = native_lo(read_jsonl(s3), read_jsonl(x3), actual_of)
    g1d = json.loads(Path(g1).read_text()) if g1 and Path(g1).exists() else None
    s = summarise(claims, lo, g1d, n_boot, seed)
    inputs = {"claims": str(claims_path), "s3_lo": str(s3) if Path(s3).exists() else None, "x3_lo": str(x3) if Path(x3).exists() else None, "g1": str(g1) if g1d else None}
    notes = list(notes)
    if not Path(s3).exists():
        notes.append(f"{s3} is absent: the error cross-tab uses the X3 layer-42 rows only and the counts cross-tab is empty.")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "w3_summary.json").write_text(json.dumps({"summary": s, "inputs": inputs, "notes": notes}, indent=1, ensure_ascii=False))
    rows = csv_rows(s)
    with (out_dir / "w3.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["source"])
        w.writeheader()
        w.writerows(rows)
    (out_dir / "w3.md").write_text(render_md(s, inputs, notes))
    return s


def run_prepare(*, s4: Path = S4_SAMPLES, items_y1: Path = ITEMS_Y1, items_w: Path = ITEMS_W, out_dir: Path = OUT_W3, cap_usd: float = CAP_USD,
                cost_per_call: float = COST_PER_CALL, subset: Tuple[int, int] = (SUBSET_ERRORS, SUBSET_COUNTS), seed: int = SEED) -> dict:
    samples = read_jsonl(s4)
    if not samples:
        raise SystemExit(f"no S4 samples at {s4}")
    rows, plan = select_judge_rows(samples, load_item_prompts(items_y1, items_w), cap_usd=cap_usd, cost_per_call=cost_per_call, subset=subset, seed=seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    inp, outp = out_dir / "s4_judge_input.jsonl", out_dir / "claims_s4.jsonl"
    write_jsonl(inp, rows)
    plan["judge_input"], plan["judge_output"], plan["judge_command"] = str(inp), str(outp), judge_command(inp, outp, out_dir)
    (out_dir / "s4_judge_plan.json").write_text(json.dumps(plan, indent=1))
    return plan


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--s4", type=Path, default=S4_SAMPLES)
    p.add_argument("--items-y1", type=Path, default=ITEMS_Y1)
    p.add_argument("--items-w", type=Path, default=ITEMS_W)
    p.add_argument("--out", type=Path, default=OUT_W3)
    p.add_argument("--cap-usd", type=float, default=CAP_USD)
    p.add_argument("--cost-per-call", type=float, default=COST_PER_CALL)
    p.add_argument("--subset", default=f"{SUBSET_ERRORS},{SUBSET_COUNTS}")
    p.add_argument("--seed", type=int, default=SEED)
    r = sub.add_parser("report")
    r.add_argument("--claims", type=Path, default=CLAIMS_S4)
    r.add_argument("--s3", type=Path, default=S3_LO)
    r.add_argument("--x3-lo", type=Path, default=X3_LO)
    r.add_argument("--g1", type=Path, default=G1_W3)
    r.add_argument("--items-y1", type=Path, default=ITEMS_Y1)
    r.add_argument("--items-w", type=Path, default=ITEMS_W)
    r.add_argument("--out", type=Path, default=OUT_W3)
    r.add_argument("--n-boot", type=int, default=N_BOOT)
    r.add_argument("--seed", type=int, default=SEED)
    r.add_argument("--note", action="append", default=[])
    a = ap.parse_args(argv)
    if a.cmd == "prepare":
        e, c = (int(x) for x in a.subset.split(","))
        plan = run_prepare(s4=a.s4, items_y1=a.items_y1, items_w=a.items_w, out_dir=a.out, cap_usd=a.cap_usd, cost_per_call=a.cost_per_call, subset=(e, c), seed=a.seed)
        print(json.dumps({k: v for k, v in plan.items() if k != "judge_command"}, indent=1))
        print("\nJudge command:\n" + plan["judge_command"])
    else:
        s = run_report(claims_path=a.claims, s3=a.s3, x3=a.x3_lo, g1=a.g1, items_y1=a.items_y1, items_w=a.items_w, out_dir=a.out, n_boot=a.n_boot, seed=a.seed, notes=a.note)
        print((Path(a.out) / "w3.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
