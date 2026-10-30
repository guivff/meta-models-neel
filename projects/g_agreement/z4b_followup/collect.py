"""Z4b ownership follow-up + NLA reproduction gate (GPU; BRIEF_Z deviations 2026-10-09 "Z4b ownership follow-up" and
"NLA reproduction gate", both PRE-REGISTERED).

Phase A (target + J-lens + Oracle lens), the 32 ownership X2 pairs × both sources (64 items), interpolation α 1
(h' = h_A + α(h_B − h_A) at the arm's positions; the mirror from B), one decode per (item, arm, layer):
  layer 38 (cached X2 captures, cache/g_agreement/x/full):
    question_only          user-text tokens after the last statement's final period through the end of the user text
    template_only          the tokens after the user text (<|im_end|> … the final token)
    last3                  the final three positions
    question_first_half    the question span's first floor(n/2) tokens
    question_second_half   the rest of the question span
  layers 20 and 28 (new full captures, cache/g_agreement/z/z4b_full/<item>.pt, bf16):
    names_objects_only     the positions where the two renders differ (core.edit.differing_positions)
  7 arm × layer cells × 64 items = 448 decodes (printed; the run refuses above --cap 600).
Spans are found from the tokenizer (offset mapping of the chat-template string, ids asserted equal to the render; fallback:
subsequence match of the user-text ids with cumulative-decode offsets) and written to results/g_agreement/z4b/spans.json.
"Last statement's final period" = the last '.' before the question's '?' (see the module note SPAN RULE).

    python -m projects.g_agreement.z4b_followup.collect --phase A
    python -m projects.g_agreement.z4b_followup.collect --phase B --nla-x1-check

Phase B (NLA only; the NLA is NOT run on the Z4b edits): the NLA reproduction gate. The 280 X1 TEST states
(cache/g_agreement/states/<item>.pt; items_x.json split test, all four families) are written as Z4-style read-vector inputs
(bf16 by default, the dtype Z4 stores its read vectors in) and scored by ``z4_positions.collect.collect_lo`` — the function the Z4
phase-B collector calls, which calls ``core.scoring_lo.score_lo`` — with candidates (own answer, other) and the family passed through.
Rows → cache/g_agreement/z/z4b_nla_x1.jsonl. The X1 E1 within-pair win (x1_bank.analyze.e1_reader_family: win = lo_A + lo_B > 0,
lo = lp(own) − lp(other)) per family; GATE: ownership and mapping each within 0.72 ± 0.05 → PASS (else the Z4 NLA numbers are void);
row-by-row comparison with the original X1 NLA rows (cache/g_agreement/x/x1_lo.jsonl): median |Δlo|, sign agreement.
Verdict → results/g_agreement/z4b/nla_gate.json.

SPAN RULE (resolved ambiguity): the deviation text says "the second '.'" because ownership prompts carry two statements, but 3 of the 5
ownership templates join both statements in ONE sentence (own-t2 ", and", own-t4 ";", own-t5 " and"), where the second '.' ends the
instruction after the question. The binding definition is "the last statement's final period", implemented as the last '.' before
the '?' (regex ``^(?P<statements>[^?]*\\.)(?P<question>\\s+[^.?]*\\?.*)$``), asserted to be the 1st or 2nd '.' of the user text, with
both candidate names inside the statements part and exactly one '?' in the user text.

Outputs (resumable by key): cache/g_agreement/z/{z4b_behaviour.jsonl, z4b_readvecs/, z4b_lo.jsonl, z4b_full/, z4b_nla_x1.jsonl,
z4b_nla_x1_inputs.jsonl, z4b_nla_x1_vecs/}; results/g_agreement/z4b/{log.md, spans.json, nla_gate.json}. Ledger steps z4b_*.
Sign conventions as X2/Z4: cand_A = own answer, cand_B = the other candidate; lo_model = lp(first B) − lp(first A);
lo_toward_other = reader score(B) − score(A); positive = toward the other candidate.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import edit as E
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core import states as S
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, read_jsonl, timed_call
from projects.g_agreement.x1_bank import collect as XC
from projects.g_agreement.x2_causal import collect as X
from projects.g_agreement.z4_positions import collect as Z

MODULE = "z4b"
SITE = "Z4b"
FAMILY = "ownership"
Z4B_L38 = 38
Z4B_EARLY_LAYERS: tuple[int, ...] = (20, 28)
Z4B_ALPHA = 1.0
L38_ARMS: tuple[str, ...] = ("question_only", "template_only", "last3", "question_first_half", "question_second_half")
NAMES_ARM = "names_objects_only"
ARMS: tuple[str, ...] = L38_ARMS + (NAMES_ARM,)
DECODE_CAP = 600
EXPECTED_DECODES = 448

Z_DIR = C.CACHE_DIR / "z"
FULL_DIR = Z_DIR / "z4b_full"
BEH_PATH = Z_DIR / "z4b_behaviour.jsonl"
LO_PATH = Z_DIR / "z4b_lo.jsonl"
READVEC_DIR = Z_DIR / "z4b_readvecs"
GATE_INPUTS = Z_DIR / "z4b_nla_x1_inputs.jsonl"
GATE_VEC_DIR = Z_DIR / "z4b_nla_x1_vecs"
GATE_LO_PATH = Z_DIR / "z4b_nla_x1.jsonl"
X1_LO_PATH = XC.LO_PATH
RESULTS = C.RESULTS_DIR / "z4b"
LOG = RESULTS / "log.md"
SPANS_JSON = RESULTS / "spans.json"
GATE_JSON = RESULTS / "nla_gate.json"
SAVE_DTYPE = X.SAVE_DTYPE
GATE_FAMILIES: tuple[str, ...] = ("ownership", "mapping")
GATE_TARGET, GATE_TOL = 0.72, 0.05
GATE_KEY_PREFIX = "x1gate"
STATEMENT_RE = re.compile(r"^(?P<statements>[^?]*\.)(?P<question>\s+[^.?]*\?.*)$", re.S)


# ------------------------------------------------------------------ pairs
def z4b_pairs(items: list[dict[str, Any]], x2_beh_path: Path = X.BEH_PATH, *, n_pairs: int = X.N_PAIRS_PER_FAMILY, limit: int = 0) -> list[dict[str, Any]]:
    """The ownership X2 pairs: pair ids read from the X2 behaviour file (family ownership), asserted to be exactly the first
    ``n_pairs`` test ownership pairs by pair index (X2's selection); returned in X2 order, ``limit`` = first N (debug)."""
    ids = {r["pair_id"] for r in read_jsonl(Path(x2_beh_path)) if r.get("family") == FAMILY}
    if not ids:
        raise SystemExit(f"no {FAMILY} rows in {x2_beh_path}")
    ref = X.x2_pairs(items, n_pairs=n_pairs, families=(FAMILY,))
    if {p["pair_id"] for p in ref} != ids:
        raise SystemExit(f"{x2_beh_path}: ownership pair ids {sorted(ids)[:4]}… ({len(ids)}) are not the first {n_pairs} test ownership pairs")
    return ref[: limit or None]


# ------------------------------------------------------------------ spans
def statement_end_char(user_text: str, candidates: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
    """Char index (within the user text) of the last statement's final period = the last '.' before the question's '?'."""
    if user_text.count("?") != 1:
        raise ValueError(f"expected exactly one '?' in the ownership prompt: {user_text!r}")
    m = STATEMENT_RE.match(user_text)
    if m is None:
        raise ValueError(f"ownership prompt does not match statements + question: {user_text!r}")
    p = len(m.group("statements")) - 1
    n_before = m.group("statements").count(".")
    if n_before not in (1, 2):
        raise ValueError(f"statement-end period is the {n_before}th '.' (expected the 1st or 2nd): {user_text!r}")
    for c in candidates:
        if c not in m.group("statements"):
            raise ValueError(f"candidate {c!r} not inside the statements part: {user_text!r}")
    assert user_text[p] == "."
    return {"period_char": p, "period_ordinal": n_before, "statements_text": m.group("statements"), "question_text": m.group("question")}


def render_string(tokenizer: Any, prompt_text: str, system: str | None = None) -> str:
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt_text}]
    s = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=C.ENABLE_THINKING)
    return s if isinstance(s, str) else str(s)


def _user_token_offsets(tokenizer: Any, ids: list[int], prompt_text: str, system: str | None) -> tuple[int, int, list[tuple[int, int]], str]:
    """(u0, u1, offsets, method): the user text occupies ids[u0:u1]; offsets[k] = (start, end) chars WITHIN the user text of
    token u0 + k. Primary: offset mapping of the chat-template string (its ids must equal the render). Fallback: subsequence
    match of the user-text ids, offsets by cumulative decode."""
    try:
        s = render_string(tokenizer, prompt_text, system)
        enc = tokenizer(s, return_offsets_mapping=True, add_special_tokens=False)
        offs = enc.get("offset_mapping") if hasattr(enc, "get") else None
        if offs is not None and list(enc["input_ids"]) == list(ids) and s.count(prompt_text) == 1:
            c0 = s.index(prompt_text)
            c1 = c0 + len(prompt_text)
            inside = [k for k, (a, b) in enumerate(offs) if b > c0 and a < c1]
            if inside and offs[inside[0]][0] == c0 and offs[inside[-1]][1] == c1 and inside == list(range(inside[0], inside[-1] + 1)):
                return inside[0], inside[-1] + 1, [(int(offs[k][0]) - c0, int(offs[k][1]) - c0) for k in inside], "offsets"
    except (TypeError, ValueError, NotImplementedError, KeyError):
        pass
    uids = LO.encode(tokenizer, prompt_text)
    n = len(uids)
    hits = [i for i in range(len(ids) - n + 1) if list(ids[i: i + n]) == uids]
    if len(hits) != 1:
        raise ValueError(f"user text ids found {len(hits)} times in the render (need exactly one)")
    if tokenizer.decode(uids) != prompt_text:
        raise ValueError("user-text ids do not decode back to the user text")
    cum = [len(tokenizer.decode(uids[:k])) for k in range(n + 1)]
    return hits[0], hits[0] + n, [(cum[k], cum[k + 1]) for k in range(n)], "subsequence"


def item_spans(tokenizer: Any, item: dict[str, Any], ids: list[int]) -> dict[str, Any]:
    """Role spans of one ownership item (absolute token indices into ``ids``)."""
    ids = [int(t) for t in ids]
    T = len(ids)
    u0, u1, offs, method = _user_token_offsets(tokenizer, ids, item["prompt_text"], item.get("system"))
    st = statement_end_char(item["prompt_text"], item.get("primary", {}).get("candidates", ()))
    pc = st["period_char"]
    ks = [k for k, (a, b) in enumerate(offs) if a <= pc < b]
    if len(ks) != 1:
        raise ValueError(f"{item.get('item_id')}: no unique token covers the statement-end period")
    period = u0 + ks[0]
    if "." not in tokenizer.decode([ids[period]]):
        raise ValueError(f"{item.get('item_id')}: token {period} ({tokenizer.decode([ids[period]])!r}) is not the period")
    question = list(range(period + 1, u1))
    template = list(range(u1, T))
    if not question or not template or T < 3:
        raise ValueError(f"{item.get('item_id')}: empty question or template span")
    if not any("?" in tokenizer.decode([ids[k]]) for k in question):
        raise ValueError(f"{item.get('item_id')}: question span carries no '?'")
    h = len(question) // 2
    return {"item_id": item.get("item_id"), "template_id": item.get("template_id"), "n_tokens": T, "method": method, "user_span": [u0, u1],
            "period_pos": period, "period_ordinal": st["period_ordinal"], "question_only": question, "template_only": template,
            "last3": [T - 3, T - 2, T - 1], "question_first_half": question[:h], "question_second_half": question[h:],
            "question_text": tokenizer.decode(ids[period + 1: u1]), "template_text": tokenizer.decode(ids[u1:])}


def pair_spans(tokenizer: Any, pair: dict[str, Any], ids_A: list[int], ids_B: list[int]) -> dict[str, Any]:
    """Spans of both items, the arm → positions table (L38 arms must coincide across A and B; names_objects_only = differing
    positions, all inside the statements part)."""
    sA, sB = item_spans(tokenizer, pair["A"], ids_A), item_spans(tokenizer, pair["B"], ids_B)
    for arm in L38_ARMS:
        if sA[arm] != sB[arm]:
            raise ValueError(f"{pair['pair_id']}: {arm} differs between A {sA[arm]} and B {sB[arm]}")
    diff = E.differing_positions(ids_A, ids_B)
    if not diff:
        raise ValueError(f"{pair['pair_id']}: identical renders")
    if max(diff) >= min(sA["period_pos"], sB["period_pos"]) or min(diff) < max(sA["user_span"][0], sB["user_span"][0]):
        raise ValueError(f"{pair['pair_id']}: differing positions {diff} not inside the statements part")
    arms = {arm: list(sA[arm]) for arm in L38_ARMS}
    arms[NAMES_ARM] = diff
    return {"pair_id": pair["pair_id"], "family": pair["family"], "n_tokens": len(ids_A), "arms": arms, "A": sA, "B": sB,
            "names_objects_tokens": [tokenizer.decode([int(ids_A[k])]) + "/" + tokenizer.decode([int(ids_B[k])]) for k in diff]}


def build_spans(tokenizer: Any, pairs: list[dict[str, Any]], x_full_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Spans of every pair from the CACHED X2 renders (ids asserted equal to a fresh render)."""
    import torch

    out = {}
    for p in pairs:
        ids = {}
        for v in ("A", "B"):
            d = torch.load(X.full_path(p[v]["item_id"], x_full_dir), map_location="cpu")
            ids[v] = [int(t) for t in d["ids"]]
            if M.render_item(tokenizer, p[v]["prompt_text"], p[v].get("system")) != ids[v]:
                raise RuntimeError(f"{p[v]['item_id']}: cached X2 ids differ from the render")
        out[p["pair_id"]] = pair_spans(tokenizer, p, ids["A"], ids["B"])
    return out


def spans_summary(spans: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"pairs": len(spans), "methods": sorted({s[v]["method"] for s in spans.values() for v in "AB"}),
                           "period_ordinal": {str(k): sum(1 for s in spans.values() for v in "AB" if s[v]["period_ordinal"] == k) for k in (1, 2)}}
    for arm in ARMS:
        n = [len(s["arms"][arm]) for s in spans.values()]
        out[arm] = {"min": min(n) if n else 0, "max": max(n) if n else 0, "mean": (sum(n) / len(n)) if n else 0.0}
    return out


# ------------------------------------------------------------------ table / plan
def arm_layers(arm: str, l38: int | None = None, early: tuple[int, ...] | None = None) -> tuple[int, ...]:
    l38 = Z4B_L38 if l38 is None else l38
    early = Z4B_EARLY_LAYERS if early is None else early
    return tuple(early) if arm == NAMES_ARM else (int(l38),)


def entry_key(pair_id: str, source: str, arm: str, layer: int, alpha: float = Z4B_ALPHA) -> str:
    """``pair|source|Z4b|arm|alpha|L<layer>``."""
    return f"{pair_id}|{source}|{SITE}|{arm}|{float(alpha)}|L{int(layer)}"


def build_table(spans: dict[str, dict[str, Any]], *, arms: tuple[str, ...] = ARMS, alpha: float = Z4B_ALPHA) -> list[dict[str, Any]]:
    out = []
    for pid, sp in spans.items():
        for src in ("A", "B"):
            for arm in arms:
                for layer in arm_layers(arm):
                    pos = list(sp["arms"][arm])
                    out.append({"key": entry_key(pid, src, arm, layer, alpha), "pair_id": pid, "family": sp["family"], "source": src, "arm": arm,
                                "condition": arm, "edit_layer": int(layer), "alpha": float(alpha), "positions": pos, "n_positions": len(pos),
                                "n_tokens": sp["n_tokens"], "site": SITE})
    return out


def planned_decodes(table: list[dict[str, Any]]) -> dict[str, Any]:
    cells: dict[str, int] = {}
    for e in table:
        k = f"{e['arm']}@L{e['edit_layer']}"
        cells[k] = cells.get(k, 0) + 1
    return {"cells": cells, "n_cells": len(cells), "total_planned": len(table)}


def format_plan(plan: dict[str, Any]) -> str:
    lines = [f"  {k:34s} {v:5d}" for k, v in plan["cells"].items()]
    lines.append(f"  {'total':34s} {plan['total_planned']:5d}   ({plan['n_cells']} arm × layer cells)")
    return "\n".join(lines)


def check_cap(plan: dict[str, Any], cap: int = DECODE_CAP) -> None:
    if plan["total_planned"] > cap:
        raise SystemExit(f"refusing to run: {plan['total_planned']} planned decodes exceed the cap {cap}")


# ------------------------------------------------------------------ L20/L28 captures
def early_path(item_id: str, full_dir: Path | None = None) -> Path:
    return (full_dir or FULL_DIR) / f"{item_id}.pt"


def load_early(item_id: str, full_dir: Path | None = None) -> dict[str, Any]:
    import torch

    d = torch.load(early_path(item_id, full_dir), map_location="cpu")
    d["layers"] = {int(k): v.float() for k, v in d["layers"].items()}
    return d


def capture_early(target: M.Target, pairs: list[dict[str, Any]], *, layers: tuple[int, ...] | None = None, full_dir: Path | None = None,
                  x_full_dir: Path | None = None, check_layer: int | None = None, ledger_path: Path | None = None,
                  log_path: Path | None = LOG) -> list[dict[str, Any]]:
    """Full block outputs at ``layers`` (default 20, 28) for both items of every pair → ``z4b_full/<item>.pt`` (bf16), from the
    cached X2 ids. The cached-layer ``check_layer`` (38) is captured in the same forward and compared with the X2 capture
    (max |Δ|, relative Frobenius) as a consistency check; it is not saved. Resumable (sha + layer set checked)."""
    import torch

    layers = tuple(int(x) for x in (layers or Z4B_EARLY_LAYERS))
    check_layer = Z4B_L38 if check_layer is None else int(check_layer)
    full_dir = full_dir or FULL_DIR
    full_dir.mkdir(parents=True, exist_ok=True)
    ledger = StepLedger(step="z4b_capture_full", module=MODULE, extra={"layers": list(layers), "dtype_saved": SAVE_DTYPE})
    checks = []
    for pair in pairs:
        for v in ("A", "B"):
            it = pair[v]
            cached = X.load_full(it["item_id"], x_full_dir)
            ids = [int(t) for t in cached["ids"]]
            sha = C.sha256_ids(ids)
            if cached.get("prompt_ids_sha256") not in (None, sha):
                raise RuntimeError(f"{it['item_id']}: X2 cache sha mismatch")
            p = early_path(it["item_id"], full_dir)
            if p.exists():
                prev = torch.load(p, map_location="cpu")
                if prev.get("prompt_ids_sha256") != sha or set(int(k) for k in prev["layers"]) != set(layers):
                    raise RuntimeError(f"{p}: cached capture is from a different render/layer set; delete it to recapture")
                checks.append(prev.get("check"))
                continue
            cap = sorted(set(layers) | ({check_layer} if check_layer in cached["layers"] else set()))
            with timed_call() as st:
                acts = E.capture_full(target, ids, cap)
            chk = None
            if check_layer in cached["layers"]:
                ref = cached["layers"][check_layer]
                d = (acts[check_layer] - ref).abs()
                chk = {"layer": check_layer, "max_abs": float(d.max()), "rel_fro": float((acts[check_layer] - ref).norm() / ref.norm().clamp_min(1e-9))}
            checks.append(chk)
            dt = getattr(torch, SAVE_DTYPE)
            torch.save({"item_id": it["item_id"], "pair_id": pair["pair_id"], "family": pair["family"], "version": v, "ids": ids, "n_tokens": len(ids),
                        "prompt_ids_sha256": sha, "layers": {int(L): acts[L].to(dt) for L in layers}, "dtype_saved": SAVE_DTYPE,
                        "model_id": target.model_id, "model_sha": target.revision, "hook": C.HOOK, "check": chk, "captured_at": now_iso()}, p)
            ledger.add(len(ids), 0, st.wall_s, st.peak_mem_gb)
    r = ledger.flush(ledger_path)
    ok = [c for c in checks if c]
    if log_path:
        if r:
            log_line(log_path, f"capture_full L{list(layers)}: {r}")
        if ok:
            log_line(log_path, f"L{check_layer} consistency vs the X2 capture: max rel_fro {max(c['rel_fro'] for c in ok):.2e}, "
                               f"max |Δ| {max(c['max_abs'] for c in ok):.3g} over {len(ok)} items")
    return checks


# ------------------------------------------------------------------ entry vectors
def z4b_entry_vectors(e: dict[str, Any], hA: Any, hB: Any) -> dict[str, Any]:
    """Edited rows of one entry at its edit layer (``hA``/``hB`` = that layer's [T, d] captures): P = the arm's positions,
    base = this state's rows, delta = toward·(h_B − h_A)(P) (toward +1 from A, −1 from B); vector = base + α·delta."""
    hA, hB = hA.float(), hB.float()
    if hA.shape != hB.shape:
        raise ValueError(f"{e['pair_id']}: A and B captures differ in shape {tuple(hA.shape)} vs {tuple(hB.shape)}")
    T = int(hA.shape[0])
    pos = [int(p) for p in e["positions"]]
    if not pos or pos != sorted(set(pos)) or pos[0] < 0 or pos[-1] >= T:
        raise ValueError(f"{e['key']}: positions {pos} must be sorted, unique and inside the render (T={T})")
    toward = 1.0 if e["source"] == "A" else -1.0
    h = hA if e["source"] == "A" else hB
    D = hB - hA
    base = h[pos].clone()
    delta = toward * D[pos]
    alpha = float(e["alpha"])
    vec = base + alpha * delta
    last_edited = pos[-1] == T - 1
    return {"positions": pos, "n_positions": len(pos), "base": base, "delta": delta, "vector": vec, "dose_abs": alpha * float(delta.norm()),
            "delta_edited": float(delta.norm()), "delta_total": float(D.norm()), "delta_last": float(D[T - 1].norm()),
            "input_norm_last": float(vec[-1].norm()) if last_edited else float(h[T - 1].norm()), "input_norm_natural_last": float(h[T - 1].norm()),
            "last_edited": last_edited}


def _layer_captures(pair: dict[str, Any], arm: str, layer: int, x_full_dir: Path | None, full_dir: Path | None) -> tuple[Any, Any]:
    if arm in L38_ARMS:
        H = {v: X.load_full(pair[v]["item_id"], x_full_dir) for v in ("A", "B")}
    else:
        H = {v: load_early(pair[v]["item_id"], full_dir) for v in ("A", "B")}
    if layer not in H["A"]["layers"] or layer not in H["B"]["layers"]:
        raise RuntimeError(f"{pair['pair_id']}: layer {layer} not in the captures for arm {arm}")
    return H["A"]["layers"][layer], H["B"]["layers"][layer]


# ------------------------------------------------------------------ behaviour
def collect_behaviour(target: M.Target, pairs: list[dict[str, Any]], table: list[dict[str, Any]], *, beh_path: Path = BEH_PATH,
                      readvec_dir: Path | None = None, x_full_dir: Path | None = None, full_dir: Path | None = None, ledger_path: Path | None = None,
                      log_path: Path | None = LOG, max_new_tokens: int = X.BEHAVIOUR_TOKENS, batch: int = X.DEFAULT_BATCH, items_file: Path | None = None,
                      read_layer: int | None = None) -> int:
    """Decode every entry not yet done, batched over entries sharing (pair, source, edit layer) (row-wise position sets via
    ``z4_positions.collect.generate_with_rowwise_positions``); read back the block-42 last-token vector. Resumable."""
    import torch

    from projects.g_agreement.core import scoring as SC

    readvec_dir = readvec_dir or READVEC_DIR
    read_layer = E.X2_READ_LAYER if read_layer is None else read_layer
    readvec_dir.mkdir(parents=True, exist_ok=True)
    done = {k for k in done_ids(beh_path, key="key") if X.readvec_path(k, readvec_dir).exists()}
    ledgers: dict[str, StepLedger] = {}
    extra = X._row_extra(items_file)
    dt = getattr(torch, SAVE_DTYPE)
    by_pair = {p["pair_id"]: p for p in pairs}
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for e in table:
        if e["key"] not in done:
            groups.setdefault((e["pair_id"], e["source"], int(e["edit_layer"])), []).append(e)
    n = 0
    for (pid, src, layer), ents in groups.items():
        pair = by_pair[pid]
        it = pair[src]
        cached = X.load_full(it["item_id"], x_full_dir)
        ids = [int(t) for t in cached["ids"]]
        cand_A, cand_B = it["primary"]["answer"], X.other_candidate(it)
        ft = E.first_token_candidates(target.tokenizer, cand_A, cand_B)
        cft = None if ft["unscorable"] else (ft["first_A"], ft["first_B"])
        caps: dict[str, tuple[Any, Any]] = {}
        for s in range(0, len(ents), batch):
            chunk = ents[s: s + batch]
            vecs = []
            for e in chunk:
                kind = "x2" if e["arm"] in L38_ARMS else "early"
                if kind not in caps:
                    caps[kind] = _layer_captures(pair, e["arm"], layer, x_full_dir, full_dir)
                hA, hB = caps[kind]
                if int(hA.shape[0]) != len(ids):
                    raise RuntimeError(f"{e['key']}: capture length {hA.shape[0]} != render {len(ids)}")
                vecs.append(z4b_entry_vectors(e, hA, hB))
            rows = Z.generate_with_rowwise_positions(target, ids, layer, [v["positions"] for v in vecs], [v["vector"] for v in vecs],
                                                     read_layer=read_layer, max_new_tokens=max_new_tokens, cand_first_tokens=cft)
            for e, v, r in zip(chunk, vecs, rows):
                parsed, evidence = SC.extract_target_answer(r["answer_text"], it)
                torch.save(r["read_vec"].to(dt), X.readvec_path(e["key"], readvec_dir))
                row = {"key": e["key"], "pair_id": pid, "family": pair["family"], "source": src, "state_item_id": it["item_id"], "site": SITE,
                       "arm": e["arm"], "condition": e["arm"], "edit_layer": layer, "positions_kind": e["arm"], "positions": v["positions"],
                       "n_positions": v["n_positions"], "n_tokens": r["n_tokens"], "alpha": e["alpha"], "null_k": None, "sign": 1 if src == "A" else -1,
                       "cand_A": cand_A, "cand_B": cand_B, "answer_text": r["answer_text"], "parsed": parsed, "parse_evidence": evidence,
                       "flipped_to_other": parsed == cand_B, "kept_original": parsed == cand_A, "coherent": parsed in (cand_A, cand_B),
                       "lo_model": r["lo_model"], "lp_first_A": r["lp_first_A"], "lp_first_B": r["lp_first_B"], "lo_model_unscorable": ft["unscorable"],
                       "lo_model_form": ft["form"], "first_A": ft["first_A"], "first_B": ft["first_B"], "first_token_id": r["first_token_id"],
                       "top1_id": r["top1_id"], "dose_abs": v["dose_abs"], "delta_edited": v["delta_edited"], "delta_total": v["delta_total"],
                       "delta_last": v["delta_last"], "input_norm_last": v["input_norm_last"], "input_norm_natural_last": v["input_norm_natural_last"],
                       "last_edited": v["last_edited"], "n_new_tokens": r["n_new_tokens"], "finish_reason": r["finish_reason"], "read_layer": read_layer,
                       "n_hook_edits": r["n_hook_edits"], "batch_size": r["batch_size"], "wall_s": r["wall_s"] / max(1, r["batch_size"]),
                       "wall_s_batch": r["wall_s_batch"], "peak_mem_gb": r["peak_mem_gb"], "prompt_ids_sha256": C.sha256_ids(ids),
                       "readvec_dtype": SAVE_DTYPE, "created_at": now_iso(), **extra}
                append_jsonl(beh_path, row)
                n += 1
            for arm in {e["arm"] for e in chunk}:
                sub = [r for e, r in zip(chunk, rows) if e["arm"] == arm]
                ld = ledgers.setdefault(f"{arm}_L{layer}", StepLedger(step=f"z4b_behaviour_{arm}_L{layer}", module=MODULE,
                                                                       extra={"max_new_tokens": max_new_tokens, "batch": batch}))
                ld.add(len(ids) * len(sub), sum(r["n_new_tokens"] for r in sub), rows[0]["wall_s_batch"] * len(sub) / len(chunk), rows[0]["peak_mem_gb"])
        print(f"[z4b/behaviour] {pid}|{src}|L{layer}: {len(ents)} entries decoded", flush=True)
    for ld in ledgers.values():
        r = ld.flush(ledger_path)
        if log_path and r:
            log_line(log_path, f"behaviour {ld.step}: {r}")
    if log_path:
        log_line(log_path, f"behaviour: {n} new entries")
    return n


# ------------------------------------------------------------------ reader LO (J-lens / Oracle) on the read vectors
LO_COPY_KEYS = ("pair_id", "family", "source", "state_item_id", "site", "arm", "condition", "edit_layer", "n_positions", "n_tokens", "alpha",
                "cand_A", "cand_B", "dose_abs", "lo_model", "flipped_to_other", "coherent")


def collect_lo(reader: Any, *, beh_path: Path = BEH_PATH, lo_path: Path = LO_PATH, readvec_dir: Path | None = None, ledger_path: Path | None = None,
               log_path: Path | None = LOG, batch: int = 32, items_file: Path | None = None) -> int:
    """Native LO of ``reader`` on every Z4b read vector via ``core.scoring_lo.score_lo`` (the Z4/X2 scoring call, chunked by family as
    in Z4); ``lo_toward_other = score(B) − score(A)``. Resumable by ``reader|entry key``."""
    import torch

    readvec_dir = readvec_dir or READVEC_DIR
    done = done_ids(lo_path, key="key")
    todo = [r for r in read_jsonl(beh_path) if f"{reader.name}|{r['key']}" not in done and X.readvec_path(r["key"], readvec_dir).exists()]
    ledger = StepLedger(step=f"z4b_lo_{reader.name}", module=MODULE, extra={"batch": batch})
    extra = X._row_extra(items_file)
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for r in todo:
        by_fam.setdefault(r["family"], []).append(r)
    n = 0
    for fam, rows_f in by_fam.items():
        for s in range(0, len(rows_f), batch):
            chunk = rows_f[s: s + batch]
            Hm = torch.stack([X.load_readvec(r["key"], readvec_dir) for r in chunk])
            with timed_call() as st:
                res = LO.score_lo(reader, Hm, [(r["cand_A"], r["cand_B"]) for r in chunk], fam, batch=batch)
            for b, q in zip(chunk, res):
                row = {"key": f"{reader.name}|{b['key']}", "entry_key": b["key"], "reader": reader.name, **{k: b.get(k) for k in LO_COPY_KEYS},
                       "lo_own": q["lo"], "lo_toward_other": (None if q["lo"] is None else -q["lo"]), "lp_A": q["lp_A"], "lp_B": q["lp_B"],
                       "templates": q["templates"], "unscorable": q["unscorable"], "wall_s_chunk": st.wall_s, "chunk_size": len(chunk),
                       "created_at": now_iso(), **extra}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason"):
                    if k in q:
                        row[k] = q[k]
                append_jsonl(lo_path, row)
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[z4b/lo/{reader.name}] {fam}: {len(rows_f)} vectors scored", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"lo {reader.name}: {r}")
    return n


# ------------------------------------------------------------------ NLA reproduction gate (phase B)
def gate_key(item_id: str) -> str:
    return f"{GATE_KEY_PREFIX}|{item_id}"


def gate_pairs(items_path: Path = XC.ITEMS_X, limit_pairs: int = 0, items: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """The X1 test bank (all four families, X1's pair order); ``limit_pairs`` per family (debug)."""
    return XC.load_pairs(items_path, "test", limit_pairs, items=items)


def write_gate_inputs(pairs: list[dict[str, Any]], *, inputs_path: Path = GATE_INPUTS, vec_dir: Path = GATE_VEC_DIR, states_dir: Path | None = None,
                      dtype: str = SAVE_DTYPE) -> int:
    """One Z4-style input row per X1 state (X1 pair order, A then B; key ``x1gate|<item>``; cand_A = own answer, cand_B = other) and
    its read vector = the cached X1 block-42 state stored in ``dtype`` (bf16 = the Z4 read-vector format). Resumable; a dtype change
    for existing rows is refused."""
    import torch

    vec_dir.mkdir(parents=True, exist_ok=True)
    prev = {r["key"]: r for r in read_jsonl(inputs_path)} if Path(inputs_path).exists() else {}
    if any(r.get("input_dtype") != dtype for r in prev.values()):
        raise SystemExit(f"{inputs_path}: existing gate inputs were written in another dtype; delete them (and the gate rows) to switch to {dtype}")
    n = 0
    for p in pairs:
        for v in ("A", "B"):
            it = p[v]
            key = gate_key(it["item_id"])
            vp = X.readvec_path(key, vec_dir)
            if key in prev and vp.exists():
                continue
            h = S.load_state(it["item_id"], states_dir)
            torch.save(h.to(getattr(torch, dtype)), vp)
            if key not in prev:
                append_jsonl(inputs_path, {"key": key, "pair_id": p["pair_id"], "family": p["family"], "source": v, "state_item_id": it["item_id"],
                                           "split": it.get("split"), "cand_A": it["primary"]["answer"], "cand_B": XC.other_candidate(it),
                                           "input_dtype": dtype, "state_source": "x1_states_block42_last", "created_at": now_iso()})
            n += 1
    return n


def score_gate(nla: Any, *, inputs_path: Path = GATE_INPUTS, lo_path: Path = GATE_LO_PATH, vec_dir: Path = GATE_VEC_DIR, ledger_path: Path | None = None,
               log_path: Path | None = LOG, batch: int = 32, items_file: Path | None = None) -> int:
    """Score the gate inputs through ``z4_positions.collect.collect_lo`` (the Z4 phase-B collector → core.scoring_lo.score_lo). Its
    ledger row (step z4_lo_nla) goes to a temporary file and is re-emitted as step ``z4b_nla_x1_gate`` / module z4b, so the Z4
    compute accounting is not polluted."""
    tmp = Path(lo_path).with_name(Path(lo_path).stem + ".ledger.tmp.jsonl")
    tmp.unlink(missing_ok=True)
    try:
        n = Z.collect_lo(nla, beh_path=inputs_path, lo_path=lo_path, readvec_dir=vec_dir, ledger_path=tmp, log_path=log_path, batch=batch, items_file=items_file)
        for row in (read_jsonl(tmp) if tmp.exists() else []):
            row.update(step="z4b_nla_x1_gate", module=MODULE, extra={**row.get("extra", {}), "code_path": "z4_positions.collect.collect_lo -> core.scoring_lo.score_lo"})
            append_jsonl(ledger_path or C.COMPUTE_LEDGER, row)
    finally:
        tmp.unlink(missing_ok=True)
    return n


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def gate_summary(pairs: list[dict[str, Any]], *, gate_lo_path: Path = GATE_LO_PATH, x1_lo_path: Path = X1_LO_PATH, n_boot: int | None = None,
                 seed: int = 0, families: tuple[str, ...] = GATE_FAMILIES, target: float = GATE_TARGET, tol: float = GATE_TOL) -> dict[str, Any]:
    """X1 E1 within-pair win per family on the gate rows (x1_bank.analyze.e1_reader_family, X1's n_boot 2000 / seed 0), the gate
    verdict, and the row-by-row comparison with the original X1 NLA rows."""
    from projects.g_agreement.core import analysis_utils as U
    from projects.g_agreement.x1_bank import analyze as XA

    nb = U.N_BOOT if n_boot is None else n_boot
    g = [r for r in read_jsonl(gate_lo_path) if r.get("reader") == "nla"] if Path(gate_lo_path).exists() else []
    rows_g = [{"item_id": r["state_item_id"], "lo": r["lo_own"], "unscorable": r["unscorable"]} for r in g]
    x1 = [r for r in read_jsonl(x1_lo_path) if r.get("reader") == "nla" and r.get("condition", "natural") == "natural" and "item_id" in r] \
        if Path(x1_lo_path).exists() else []
    lo_g = {r["item_id"]: r["lo"] for r in rows_g if not r["unscorable"] and r["lo"] is not None}
    lo_x = {r["item_id"]: r["lo"] for r in x1 if not r.get("unscorable") and r.get("lo") is not None}
    out: dict[str, Any] = {"module": MODULE, "written": now_iso(), "gate": {"families": list(families), "target": target, "tol": tol,
                           "rule": f"within-pair win (X1 E1: lo_A + lo_B > 0) within {target} ± {tol} on each of {list(families)} → PASS"},
                           "n_gate_rows": len(g), "n_x1_rows": len(x1), "families": {}}
    fams = sorted({p["family"] for p in pairs}, key=lambda f: (f not in families, families.index(f) if f in families else 0, f))
    for fam in fams:
        fp = [p for p in pairs if p["family"] == fam]
        eg = XA.e1_reader_family(rows_g, fp, nb, seed)
        ex = XA.e1_reader_family(x1, fp, nb, seed) if x1 else None
        ids = [p[v]["item_id"] for p in fp for v in "AB"]
        both = [i for i in ids if i in lo_g and i in lo_x]
        d = [abs(lo_g[i] - lo_x[i]) for i in both]
        win_agree = [eg["per_pair"][pid]["win"] == ex["per_pair"][pid]["win"] for pid in eg["per_pair"] if ex and pid in ex["per_pair"]]
        out["families"][fam] = {
            "gate_win": {k: eg[k] for k in ("k", "n", "p", "lo", "hi", "wilson_lo", "wilson_hi", "n_pairs_total", "n_pairs_scored", "n_unscorable_rows", "n_missing_rows", "mean_margin_nats")},
            "x1_win": None if ex is None else {k: ex[k] for k in ("k", "n", "p", "lo", "hi", "n_pairs_scored")},
            "compare": {"n_matched": len(both), "median_abs_dlo": statistics.median(d) if d else None, "max_abs_dlo": max(d) if d else None,
                        "mean_abs_dlo": (sum(d) / len(d)) if d else None,
                        "sign_agreement": (sum(_sign(lo_g[i]) == _sign(lo_x[i]) for i in both) / len(both)) if both else None,
                        "pair_win_agreement": (sum(win_agree) / len(win_agree)) if win_agree else None,
                        "worst": sorted(({"item_id": i, "lo_gate": lo_g[i], "lo_x1": lo_x[i]} for i in both), key=lambda q: -abs(q["lo_gate"] - q["lo_x1"]))[:5]},
            "in_gate": fam in families,
            "within_tolerance": (bool(eg["n"]) and abs(eg["p"] - target) <= tol + 1e-12) if fam in families else None}
    allb = [i for i in lo_g if i in lo_x]
    dd = [abs(lo_g[i] - lo_x[i]) for i in allb]
    out["compare_all"] = {"n_matched": len(allb), "median_abs_dlo": statistics.median(dd) if dd else None, "max_abs_dlo": max(dd) if dd else None,
                          "sign_agreement": (sum(_sign(lo_g[i]) == _sign(lo_x[i]) for i in allb) / len(allb)) if allb else None}
    gf = [out["families"].get(f) for f in families]
    if any(x is None or not x["gate_win"]["n"] for x in gf):
        verdict = "INCOMPLETE"
    else:
        verdict = "PASS" if all(x["within_tolerance"] for x in gf) else "FAIL"
    out["verdict"] = verdict
    out["consequence"] = {"PASS": "Z4 NLA numbers may be reported", "FAIL": "Z4 NLA numbers are VOID until the Z4 NLA path is debugged",
                          "INCOMPLETE": "gate rows missing for a gated family; no verdict"}[verdict]
    return out


def format_gate(s: dict[str, Any]) -> str:
    lines = [f"NLA reproduction gate: {s['verdict']} — {s['consequence']}", f"  rule: {s['gate']['rule']}",
             f"  {'family':10s} {'gate win':>14s} {'X1 win':>14s} {'med|Δlo|':>9s} {'sign agr':>9s} {'win agr':>8s}  in gate"]
    for fam, f in s["families"].items():
        gw, xw, c = f["gate_win"], f["x1_win"], f["compare"]
        fmt = lambda w: "n/a" if not w or not w["n"] else f"{w['k']}/{w['n']}={w['p']:.3f}"  # noqa: E731
        num = lambda x: "n/a" if x is None else f"{x:.3f}"  # noqa: E731
        lines.append(f"  {fam:10s} {fmt(gw):>14s} {fmt(xw):>14s} {num(c['median_abs_dlo']):>9s} {num(c['sign_agreement']):>9s} "
                     f"{num(c['pair_win_agreement']):>8s}  {'no' if not f['in_gate'] else 'yes, no rows' if not gw['n'] else 'yes, within' if f['within_tolerance'] else 'yes, OUTSIDE'}")
    return "\n".join(lines)


def run_gate(*, items_path: Path, limit_pairs: int = 0, states_dir: Path | None = None, inputs_path: Path = GATE_INPUTS, vec_dir: Path = GATE_VEC_DIR,
             lo_path: Path = GATE_LO_PATH, x1_lo_path: Path = X1_LO_PATH, gate_json: Path | None = GATE_JSON, nla: Any = None, dtype: str = SAVE_DTYPE,
             batch: int = 32, ledger_path: Path | None = None, log_path: Path | None = LOG, n_boot: int | None = None, score: bool = True,
             items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Inputs → (``nla`` bound: scoring) → summary + verdict (printed; written to ``gate_json``)."""
    pairs = gate_pairs(items_path, limit_pairs, items=items)
    if not pairs:
        raise SystemExit("no X1 test pairs")
    if score:
        missing = [p[v]["item_id"] for p in pairs for v in "AB" if not S.state_path(p[v]["item_id"], states_dir).exists()]
        if missing:
            raise SystemExit(f"missing X1 states {missing[:4]} ({len(missing)})")
        nw = write_gate_inputs(pairs, inputs_path=inputs_path, vec_dir=vec_dir, states_dir=states_dir, dtype=dtype)
        if log_path:
            log_line(log_path, f"gate inputs: {nw} new ({2 * len(pairs)} X1 test states, dtype {dtype})")
        if nla is not None:
            ns = score_gate(nla, inputs_path=inputs_path, lo_path=lo_path, vec_dir=vec_dir, ledger_path=ledger_path, log_path=log_path, batch=batch,
                            items_file=items_path)
            if log_path:
                log_line(log_path, f"gate: {ns} NLA rows scored via z4_positions.collect.collect_lo")
    s = gate_summary(pairs, gate_lo_path=lo_path, x1_lo_path=x1_lo_path, n_boot=n_boot)
    s.update(n_states=2 * len(pairs), n_pairs=len(pairs), input_dtype=dtype, items_file=str(items_path), items_file_sha256=C.sha256_file(items_path),
             code_path="z4_positions.collect.collect_lo -> core.scoring_lo.score_lo")
    print(format_gate(s), flush=True)
    if gate_json is not None:
        Path(gate_json).parent.mkdir(parents=True, exist_ok=True)
        Path(gate_json).write_text(json.dumps(s, indent=1, default=str))
    if log_path:
        log_line(log_path, f"NLA gate verdict {s['verdict']}: " + json.dumps({f: (v["gate_win"]["k"], v["gate_win"]["n"]) for f, v in s["families"].items()}))
    return s


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--nla-x1-check", action="store_true", help="phase B: the NLA reproduction gate on the X1 test bank (the only phase-B job)")
    ap.add_argument("--summary-only", action="store_true", help="phase B: recompute the gate summary from existing rows (no NLA load)")
    ap.add_argument("--gate-dtype", choices=["bfloat16", "float32"], default=SAVE_DTYPE, help="dtype the X1 states are stored in as gate inputs")
    ap.add_argument("--items-file", default=str(X.ITEMS_X))
    ap.add_argument("--split", default="test")
    ap.add_argument("--n-pairs", type=int, default=X.N_PAIRS_PER_FAMILY, help="ownership pairs (X2: 32)")
    ap.add_argument("--limit-pairs", type=int, default=0, help="debug: phase A first N pairs; phase B first N pairs per family")
    ap.add_argument("--cap", type=int, default=DECODE_CAP)
    ap.add_argument("--batch", type=int, default=X.DEFAULT_BATCH)
    ap.add_argument("--lo-batch", type=int, default=32)
    ap.add_argument("--max-new-tokens", type=int, default=X.BEHAVIOUR_TOKENS)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--skip-lo", action="store_true")
    ap.add_argument("--skip-behaviour", action="store_true")
    a = ap.parse_args(argv)
    items_file = Path(a.items_file)
    if a.phase == "B" and not a.nla_x1_check:
        raise SystemExit("phase B runs only the NLA reproduction gate (--nla-x1-check); the NLA is not run on the Z4b edits (BRIEF_Z)")
    fz = X.require_frozen_x(items_file, a.allow_unfrozen or a.split == "dev")
    Z_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    if a.phase == "B":
        log_line(LOG, f"phase B (NLA gate): items={items_file.name} sha={fz['items_file_sha256'][:12]} frozen={fz['frozen']} dtype={a.gate_dtype}")
        if a.summary_only:
            run_gate(items_path=items_file, limit_pairs=a.limit_pairs, dtype=a.gate_dtype, score=False)
            return 0
        ledger = StepLedger(step="z4b_load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader().bind()  # exactly as the Z4 phase-B path
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        log_line(LOG, f"phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}")
        run_gate(items_path=items_file, limit_pairs=a.limit_pairs, nla=nla, dtype=a.gate_dtype, batch=a.lo_batch)
        nla.unload()
        return 0
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    items = C.load_items(a.split, 0, path=items_file)
    pairs = z4b_pairs(items, n_pairs=a.n_pairs, limit=a.limit_pairs)
    missing = [p[v]["item_id"] for p in pairs for v in "AB" if not X.full_path(p[v]["item_id"]).exists()]
    if missing:
        raise SystemExit(f"missing X2 full captures {missing[:4]} ({len(missing)}): Z4b reuses cache/g_agreement/x/full")
    print(f"Z4b phase A: {len(pairs)} ownership pairs, α {Z4B_ALPHA}, L38 arms {list(L38_ARMS)}, {NAMES_ARM} at L{list(Z4B_EARLY_LAYERS)}, freeze={fz}", flush=True)
    log_line(LOG, f"phase A: {len(pairs)} pairs; items={items_file.name} sha={fz['items_file_sha256'][:12]} frozen={fz['frozen']}; cap {a.cap}")
    target = load_target_timed(MODULE)
    spans = build_spans(target.tokenizer, pairs)
    SPANS_JSON.write_text(json.dumps({"rule": "question = user-text tokens after the last '.' before the '?' through the end of the user text; "
                                               "template = tokens after the user text; last3 = final 3; halves by count (first = floor(n/2)); "
                                               "names_objects_only = differing positions", "summary": spans_summary(spans), "pairs": spans}, indent=1))
    log_line(LOG, f"spans: {spans_summary(spans)}")
    table = build_table(spans)
    plan = planned_decodes(table)
    print("[z4b] planned decodes:\n" + format_plan(plan) + f"\n  cap {a.cap} (pre-registered ≈ {EXPECTED_DECODES})", flush=True)
    log_line(LOG, f"planned decodes {plan}; cap {a.cap}")
    check_cap(plan, a.cap)
    capture_early(target, pairs)
    if not a.skip_behaviour:
        collect_behaviour(target, pairs, table, max_new_tokens=a.max_new_tokens, batch=a.batch, items_file=items_file)
    if not a.skip_lo:
        jl = R.JLensReader().bind(target)
        collect_lo(jl, batch=a.lo_batch, items_file=items_file)
        del jl
        ol = R.OLensReader().bind(target)
        log_line(LOG, f"olens adapter={ol.adapter_dir} liveness={ol.liveness}")
        collect_lo(ol, batch=a.lo_batch, items_file=items_file)
    M.unload(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
