"""SWAP — workspace swaps at scale (BRIEF_R Deviations "WS4 / SWAP", pre-registered 2026-10-19 03:40Z before any swap
compute). R5 edits a direction chosen from LABELS and asks whether readers follow it. SWAP edits a concept the model
COMPUTED and was never told — the 2-hop bridge entity, the planned rhyme word — along the J-lens readout difference
(distractor − true), and asks (i) whether the model's own answer follows and (ii) which readers notice.

**STATUS 2026-10-19 17:45Z — CODE COMPLETE, NOT YET TESTED, NOT YET RUN.** Every phase now exists
(`precheck`, `A`, `score`, `B`) and the CLI is wired. Nothing here has touched the model: the only evidence so far is
that the pure functions behave (rhyme rule, tag parsing, file naming) and that the module imports. **Do not point it at
a pod until `tests/test_r_swap.py` passes AND `--phase precheck` passes on the real bank**, which is the gate recorded
in `results/g_agreement/r/HANDOFF.md`. An earlier draft of the generation and scoring code was deleted rather than kept
because it was written badly enough to be a hazard; what replaced it has not yet earned trust either.
Phases: `A` is the GPU work (edits, read-backs, poetry completions); `score` scores the saved read-back `.npy` files
with the lens readers; `B` is the NLA with its own model. `score` and `B` both need a model and so run on the pod:
`score` loads the target because the Oracle and skip-lens arms score by forward passes through it, and because binding
even the analytic J-lens needs the target's tokenizer and unembedding. Only the arithmetic over the `.npy` files is
CPU-bound; there is no off-pod path for the scoring itself without a loader for the unembedding alone.

One edited position per item (the hop-1 span end the collector resolved, or the line break for poetry), layers 24-44
step 4, one dose, every arm at a layer sharing the same norm so the random control is exact.
Outputs under `cache/g_agreement/r/swap/`; the shared files take the SWAP suffix, set by the caller.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import (StepLedger, append_jsonl, done_ids, log_line, now_iso,
                                                  read_jsonl, timed_call)
from projects.g_agreement.r_bench import bank as B
from projects.g_agreement.r_bench import collect as RC
from projects.g_agreement.r_bench import steer as ST

MODULE = "swap"
SWAP_DIR = RC.R_DIR / "swap"
ROWS_PATH = SWAP_DIR / "swap.jsonl"
READERS_PATH = SWAP_DIR / "swap_readers.jsonl"
POETRY_PATH = SWAP_DIR / "swap_poetry.jsonl"
POETRY_POOL = "poetry_pool"                               # BRIEF_R §28 (SWAP-P): the 50 POOL couplets, never edited
POETRY_POOL_PATH = SWAP_DIR / "swap_poetry_pool.jsonl"    # its greedy completions; its forced-choice rows go to ROWS_PATH

# EVERY path this module writes, by name. The test fixture redirects all of these and the isolation guard asserts the
# list is complete, because a hand-written guard list is how mock rows reached the real cache on 2026-10-20: I added
# POETRY_POOL_PATH without adding it to the guard's dict, so the guard passed while a test wrote 12 mock rows into
# cache/g_agreement/r/swap/swap_poetry_pool.jsonl. Add a path here when you add one, or the guard fails.
PATH_NAMES = ("SWAP_DIR", "ROWS_PATH", "READERS_PATH", "POETRY_PATH", "POETRY_POOL_PATH", "RB_DIR", "DIR_DIR",
              "PRECHECK_PATH")


def output_paths() -> dict[str, Path]:
    """The current value of every output path, by name — for the fixture to redirect and the guard to check."""
    return {n: Path(globals()[n]) for n in PATH_NAMES}
RB_DIR = SWAP_DIR / "readback"
DIR_DIR = SWAP_DIR / "directions"
PRECHECK_PATH = RC.RESULTS / "swap_prechecks.json"
LAYERS = (24, 28, 32, 36, 40, 44)
ALPHA = 1.0
N_RANDOM = 3
READ_LAYER = ST.L_READ
RANDOM_SEED = 20261019
GEN_TOKENS = 6
KHOP_BRIDGE, KHOP_ANSWER, POETRY = "re_khop2_bridge", "re_khop2_answer", "x27_wsb_poetry"
NAMED_ARMS = ("d_swap", "d_answer", "d_cm", "d_logit")
NATURAL = "natural"


# ------------------------------------------------------------------ states at the collector's read position
def rp_state_file(dataset: str, render: str, layer: int) -> Any:
    p = RC.state_file(dataset, render, layer)
    return p.with_name(f"{p.stem}_rp{p.suffix}")


def load_rp_states(dataset: str, render: str, layer: int) -> tuple[np.ndarray, list[str]]:
    """fp32 [N, d] states at the READ POSITION (hop-1 span end) and the item ids in row order."""
    f = rp_state_file(dataset, render, layer)
    if not f.exists():
        raise FileNotFoundError(f)
    idx = json.loads(RC.index_file(dataset).read_text())["item_ids"]
    X = np.load(f).astype(np.float32)
    if X.shape[0] != len(idx):
        raise RuntimeError(f"{f.name}: {X.shape[0]} rows for {len(idx)} items")
    return X, idx


def read_positions(dataset: str, render: str = "chat") -> dict[str, int]:
    """The collector's resolved read position per item id (only items whose status is 'span')."""
    idx = json.loads(RC.index_file(dataset).read_text())
    if not idx.get("has_read_position"):
        raise SystemExit(f"{dataset}: index.json carries no read positions")
    toks = idx["read_position_token"][render]
    stat = (idx.get("read_position_status") or {}).get(render) or ["span"] * len(toks)
    return {iid: int(t) for iid, t, st in zip(idx["item_ids"], toks, stat) if st == "span"}


# ------------------------------------------------------------------ items and the single-token gate
def paired_khop(items_file: Any = None, split: str = "test") -> list[dict[str, Any]]:
    """khop2 prompts present in BOTH candidate sets, joined on prompt_text."""
    path = items_file or (C.DATASET_DIR / "items_re.json")
    items = B.load_items(path, split, [KHOP_BRIDGE, KHOP_ANSWER])
    br = {it["prompt_text"]: it for it in items if it["dataset"] == KHOP_BRIDGE}
    an = {it["prompt_text"]: it for it in items if it["dataset"] == KHOP_ANSWER}
    out = []
    for text in sorted(set(br) & set(an)):
        b, a = br[text], an[text]
        con = b.get("construction") or {}
        out.append({"key": b["item_id"], "prompt_text": text, "bridge_item": b, "answer_item": a,
                    "bridge": con.get("bridge"), "distractor": con.get("distractor"),
                    "answer": con.get("answer"), "distractor_answer": con.get("distractor_answer"),
                    "bridge_jlens": con.get("bridge_jlens") or con.get("bridge"),
                    "distractor_jlens": con.get("distractor_jlens") or con.get("distractor"),
                    "template": con.get("template"), "read_position": b.get("read_position")})
    return out


def poetry_items(items_file: Any = None, split: str = "test") -> list[dict[str, Any]]:
    path = items_file or (C.DATASET_DIR / "items_rx.json")
    out = []
    for it in B.load_items(path, split, [POETRY]):
        cands = it["primary"]["candidates"]
        true = it["primary"]["answer"]
        dist = next(c for c in cands if c != true)
        jl = it["primary"].get("jlens") or cands
        jl_true = jl[cands.index(true)] if len(jl) == len(cands) else true
        jl_dist = jl[cands.index(dist)] if len(jl) == len(cands) else dist
        out.append({"key": it["item_id"], "prompt_text": it["prompt_text"], "item": it,
                    "answer": true, "distractor_answer": dist,
                    "answer_jlens": jl_true, "distractor_jlens": jl_dist})
    return out


def single_token(tok: Any, *words: str) -> bool:
    return all(bool(w) and bool(LO.token_variants(tok, w)) for w in words)


# ------------------------------------------------------------------ positions in a render
def char_span_tokens(tok: Any, ids: list[int], prompt_text: str, c0: int, c1: int, anchor: str | None) -> tuple[int, int] | None:
    """Token range covering prompt characters [c0, c1) inside a render, via the fast tokenizer's offsets."""
    rendered = tok.decode(ids, skip_special_tokens=False)
    start = 0
    if anchor:
        k = rendered.find(anchor)
        start = k + len(anchor) if k >= 0 else 0
    base = rendered.find(prompt_text.strip()[:200], start)
    if base < 0:
        return None
    try:
        enc = tok(rendered, add_special_tokens=False, return_offsets_mapping=True)
        offs = enc["offset_mapping"]
    except (TypeError, KeyError, NotImplementedError):
        return None
    if list(enc["input_ids"]) != list(ids):
        return None
    a, b = base + c0, base + c1
    pos = [i for i, (s, e) in enumerate(offs) if e > a and s < b]
    return (pos[0], pos[-1] + 1) if pos else None


def line_break_position(tok: Any, ids: list[int], prompt_text: str, anchor: str | None) -> int | None:
    """Poetry: the newline ENDING line 1 of the couplet, as a token index in the render."""
    nl = [i for i, ch in enumerate(prompt_text) if ch == "\n"]
    if len(nl) < 2:
        return None
    rng = char_span_tokens(tok, ids, prompt_text, nl[1], nl[1] + 1, anchor)
    return None if rng is None else rng[1] - 1


# ------------------------------------------------------------------ directions
def swap_direction(jl: R.JLensReader, tok: Any, true: str, distractor: str, layer: int) -> np.ndarray | None:
    """∇_h [s_jlens(distractor) − s_jlens(true)]: the analytic J-lens readout difference, bare-spelling variants."""
    if layer not in jl.J:
        return None
    G = ST.jlens_grads(jl, tok, distractor, true, layer)
    return None if G is None else ST._unit(G.mean(0))


def require_consistent_scale(part: str, layer: int, arm: str, scale: float, rows: list[dict[str, Any]]) -> None:
    """BRIEF_R §28: s(L) is fixed ONCE over the full gated set, so every arm of an item shares it.

    `run_part` already computes the scale over the whole gated set rather than the subset being measured, so a plain
    resume is consistent. What this refuses is the case §28 names explicitly: a cell that already holds rows written
    at a DIFFERENT scale, which is what a `--limit` smoke sharing the real files produced on 2026-10-19 (L24 carried
    76.07, 83.53 and 86.22 at once, leaving two items' arms unmatched against their own random controls). Rows are
    append-only, so the repair is the operator's: delete that cell's rows and re-run it whole.
    """
    seen = {round(float(r["scale"]), 4) for r in rows
            if r.get("part") == part and r.get("layer") == layer and r.get("arm") == arm and r.get("scale")}
    if seen and seen != {round(float(scale), 4)}:
        raise SystemExit(
            f"swap {part} L{layer} {arm}: existing rows were written at scale {sorted(seen)} but this pass computed "
            f"{round(float(scale), 4)}. §28 requires one s(L) over the full gated set, so extending this cell would "
            f"leave its arms unmatched. Delete this cell's rows and re-run it whole, or run the full part in one pass.")


def require_primary_arm(part: str, layer: int, per_item: dict[str, np.ndarray], n_items: int) -> None:
    """Abort the layer's work if `d_swap` — the PRE-REGISTERED PRIMARY arm — has no direction for any item.

    This is the guard for the failure that cost a pod run on 2026-10-19: `ST.bind_readers` kept the J-lens only at
    [38, 42], so at the SWAP layers `swap_direction` returned None for every item and the primary arm produced zero
    rows while the random and class-mean controls ran to completion. Both paths previously recorded that as a quiet
    `n: 0` cell, so the run looked successful. A swap effect is defined as (primary flip rate − control flip rate),
    so a layer without the primary arm cannot answer the question and must not be paid for in GPU time.
    """
    if per_item:
        return
    raise SystemExit(f"swap {part} L{layer}: the primary arm d_swap has no direction for any of {n_items} items "
                     f"(J-lens layers bound: check bind_readers_for covers L{layer}). Refusing to run the controls "
                     f"alone: the pre-registered effect is primary minus control.")


def expected_arms(part: str, keep: list[dict[str, Any]], k_random: int = N_RANDOM) -> list[str]:
    """Every arm that MUST have rows for this part. `d_answer` is conditional (only khop items whose answer pair is
    single-token have one) and `d_cm` is khop-only, so neither is required when the item set cannot supply it."""
    arms = ["d_swap", "d_logit"] + [f"d_rand{k}" for k in range(k_random)]
    if part == "khop":
        if cm_eligible(keep):
            arms.append("d_cm")
        if any(r.get("answer_gated") for r in keep):
            arms.append("d_answer")
    return arms


def arm_coverage(part: str, layers: tuple[int, ...], arms: list[str]) -> dict[str, int]:
    """Rows ON DISK per (layer, arm) — not summary cells, which a resumed run legitimately leaves empty."""
    path = {"poetry": POETRY_PATH, POETRY_POOL: POETRY_POOL_PATH}.get(part, ROWS_PATH)
    rows = [r for r in read_jsonl(path) if r.get("part") == part]   # read_jsonl returns [] for a missing file
    counts: dict[str, int] = {}
    for L in layers:
        for arm in arms:
            counts[f"L{L}|{arm}"] = sum(1 for r in rows if r.get("layer") == L and r.get("arm") == arm)
    counts[NATURAL] = sum(1 for r in rows if r.get("arm") == NATURAL)
    return counts


def require_arm_coverage(part: str, layers: tuple[int, ...], keep: list[dict[str, Any]], k_random: int = N_RANDOM) -> list[str]:
    """PODS.md rule 5's arm × condition assertion, in code rather than in my reading of the console: every required
    (layer, arm) cell must hold at least one row. The binding bug produced two J-lens arms with zero rows while the
    controls ran normally, and only the foreground smoke caught it; this makes `--limit` smokes and full runs alike
    exit non-zero instead. Returns the empty cells (also the list the caller logs)."""
    counts = arm_coverage(part, layers, expected_arms(part, keep, k_random))
    return [cell for cell, n in counts.items() if n == 0]


def smoke_paths(limit: int) -> dict[str, Path]:
    """Point every output at a per-limit smoke directory, so a `--limit` run cannot touch real rows or read-backs."""
    g = globals()
    root = RC.R_DIR / "swap" / f"smoke_limit{int(limit)}"
    g["SWAP_DIR"], g["RB_DIR"], g["DIR_DIR"] = root, root / "readback", root / "directions"
    g["ROWS_PATH"], g["READERS_PATH"] = root / "swap.jsonl", root / "swap_readers.jsonl"
    g["POETRY_PATH"], g["PRECHECK_PATH"] = root / "swap_poetry.jsonl", root / "swap_prechecks.json"
    return {k: g[k] for k in ("SWAP_DIR", "ROWS_PATH", "READERS_PATH", "POETRY_PATH", "RB_DIR", "DIR_DIR")}


def cell_tag(row: dict[str, Any]) -> str:
    """The read-back file stem a steer row belongs to: `natural`, or `L24_d_swap`."""
    return NATURAL if row.get("arm") == NATURAL else f"L{row['layer']}_{row['arm']}"


def audit_cells(part: str) -> tuple[list[str], dict[str, Any]]:
    """PODS.md rule 5 for SWAP, as Guiv specified it on 2026-10-19: per cell (part × layer × arm), every steer row's
    item must have **exactly one** saved read-back state, no state may exist without a row, and each `.npy`/`.json`
    pair must be internally consistent. Reads files only — no model, no GPU.

    It exists because the arm-coverage guard counts ROWS and so could not see the `_save_reads` overwrite bug that
    lost 22 states on 2026-10-19. Returns (failure lines, summary).
    """
    # Always ROWS_PATH: those are the rows `run_part` writes, and they are the rows a read-back state belongs to.
    # `swap_poetry.jsonl` holds generated completions, which have no state by design and are not audited here.
    rows = [r for r in read_jsonl(ROWS_PATH) if r.get("part") == part]
    want: dict[str, set[str]] = collections.defaultdict(set)
    for r in rows:
        want[cell_tag(r)].add(r["item"])
    d = RB_DIR / part
    fails: list[str] = []
    summary: dict[str, Any] = {"part": part, "rows": len(rows), "cells_with_rows": len(want), "cells_checked": 0,
                               "states": 0, "missing": 0, "orphans": 0, "notes": []}
    if not rows:
        # No read-back-producing phase has run for this part yet. That is a state of the pipeline, not a fault, so it
        # is a NOTE — but it is said out loud, because silence here would read as success.
        summary["notes"].append(f"NOTE: {part} has no rows in {ROWS_PATH.name}, so there is nothing to audit yet. "
                                f"For poetry this means the read-back pass has not run and no reader can be scored.")
        return fails, summary
    if not d.exists():
        # Rows exist, so states should too. Since 2026-10-20 this is a FAILURE for EVERY part including poetry, whose
        # phase A now runs `run_part`; the old poetry exemption is gone with the gap that justified it.
        return [f"SMOKE FAILED: {part} wrote {len(rows)} rows but has no read-back directory at all"], summary
    seen = set()
    for f in sorted(d.glob("*.npy")):
        tag, keys_file = f.stem, d / f"{f.stem}.json"
        seen.add(tag)
        summary["cells_checked"] += 1
        if not keys_file.exists():
            fails.append(f"SMOKE FAILED: {part}/{tag} torn pair: {f.name} has no companion {keys_file.name}")
            continue
        keys = json.loads(keys_file.read_text())
        n_states = int(np.load(f, mmap_mode="r").shape[0])
        summary["states"] += n_states
        if n_states != len(keys):
            fails.append(f"SMOKE FAILED: {part}/{tag} torn pair: {n_states} states for {len(keys)} keys")
            continue
        if len(set(keys)) != len(keys):
            dup = sorted({k for k in keys if keys.count(k) > 1})
            fails.append(f"SMOKE FAILED: {part}/{tag} has {len(keys) - len(set(keys))} duplicate keys ({dup[:6]})")
            continue
        missing = sorted(want.get(tag, set()) - set(keys))
        extra = sorted(set(keys) - want.get(tag, set()))
        if missing:
            summary["missing"] += len(missing)
            fails.append(f"SMOKE FAILED: {part}/{tag} missing {len(missing)} states ({missing[:6]})")
        if extra:
            summary["orphans"] += len(extra)
            fails.append(f"SMOKE FAILED: {part}/{tag} has {len(extra)} states with no row ({extra[:6]})")
    # Provenance per cell: which processes wrote it. Multiple run ids are legitimate (a resumed or segmented run), so
    # this is REPORTED, not failed — but a cell written by two processes is exactly the shape of both contamination
    # incidents on 2026-10-19/20 (a `--limit` smoke sharing the real file, and a test writing to an unredirected
    # path), and `code_sha256` cannot distinguish those because the code is the same.
    runs = collections.Counter(r.get("run_id") for r in rows if r.get("run_id"))
    summary["run_ids"] = len(runs)
    if len(runs) > 1:
        per_cell = collections.defaultdict(set)
        for r in rows:
            if r.get("run_id"):
                per_cell[cell_tag(r)].add(r["run_id"])
        mixed = sorted(c for c, v in per_cell.items() if len(v) > 1)
        summary.setdefault("notes", []).append(
            f"NOTE: {part} rows come from {len(runs)} runs; {len(mixed)} cell(s) mix runs"
            + (f" (e.g. {mixed[:4]})" if mixed else " — each cell is from one run"))
    rows_no_id = sum(1 for r in rows if not r.get("run_id"))
    if rows_no_id:
        summary.setdefault("notes", []).append(
            f"NOTE: {rows_no_id} row(s) predate run_id stamping; their writing process is not recorded")

    # BRIEF_R: every arm at a layer shares the same edit norm, so the random control is exact. One scale per layer.
    by_layer: dict[Any, set[float]] = collections.defaultdict(set)
    for r in rows:
        if r.get("arm") != NATURAL and r.get("scale"):
            by_layer[r["layer"]].add(round(float(r["scale"]), 4))
    for L, scales in sorted(by_layer.items(), key=lambda kv: str(kv[0])):
        if len(scales) > 1:
            n = {sc: sum(1 for r in rows if r.get("layer") == L and r.get("scale")
                         and round(float(r["scale"]), 4) == sc) for sc in sorted(scales)}
            fails.append(f"SMOKE FAILED: {part}/L{L} has {len(scales)} different edit scales {n} — the arms at a "
                         f"layer are not norm-matched, so real minus random is not a matched comparison")
    for tag in sorted(set(want) - seen):
        summary["missing"] += len(want[tag])
        fails.append(f"SMOKE FAILED: {part}/{tag} missing {len(want[tag])} states (no read-back file for the cell)")
    return fails, summary


def logit_direction(target: M.Target, h: Any, true: str, distractor: str, tok: Any) -> np.ndarray | None:
    """∇_h [logit(distractor) − logit(true)] through the frozen final norm and unembedding (RMSNorm Jacobian at h)."""
    import torch

    ids = {}
    for name, w in (("t", true), ("d", distractor)):
        v = LO.token_variants(tok, w)
        if not v:
            return None
        ids[name] = list(v.values())[0]
    if ids["t"] == ids["d"]:
        return None
    nrm, W = M.final_norm(target.model), M.unembed_weight(target.model)
    dev = next(target.model.parameters()).device
    hh = torch.as_tensor(h).float().to(dev).clone().requires_grad_(True)
    with torch.enable_grad():
        out = nrm(hh.to(W.dtype)).float()
        lo = (W[ids["d"]].float() * out).sum() - (W[ids["t"]].float() * out).sum()
        (g,) = torch.autograd.grad(lo, hh)
    return ST._unit(g.detach().float().cpu().numpy())


def _code_sha() -> str:
    """sha256 of THIS file, stamped into every row this module writes.

    Asked for by Guiv on 2026-10-20 after WS3 could not tell which code produced the rows that queue row 5 added:
    the pod's git tree said ed1f6c3 while `swap.py` had been rsynced to a newer sha, so the tree was not the answer
    and the file that wrote the rows had already been overwritten by the time anyone asked. A row that carries its own
    writer's hash cannot have that problem.
    """
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except OSError:
        return "unknown"


CODE_SHA = _code_sha()


def stamp() -> dict[str, Any]:
    """GUARDS.md rule 3, via WS2's shared `collect.row_meta()` (scaffold f4ea50b) rather than a parallel copy.

    row_meta carries run_id, run_started_at, run_kind, pod, shard and git_sha, maintained in one place; this module
    overrides `code_sha256` with ITS OWN file's hash, because row_meta's is collect.py's. Evaluated at call time, so a
    later `--run-kind` declaration is reflected — a stamp frozen at import was the decoy finding GUARDS.md cites.
    `gpu` comes from `steer.gpu_tag()`, defined once there: which accelerator computed the row (Guiv, 2026-10-20).
    """
    return {**RC.row_meta(), "code_sha256": CODE_SHA, "gpu": ST.gpu_tag()}

# One id per PROCESS. `code_sha256` says which code wrote a row; it cannot say whether the writer was a real run or a
# test, because a mock run executes the same code and so carries the same hash — WS3 pointed this out on 2026-10-20
# after my own test leaked 12 mock rows into the real cache and their `code_sha256` check could not have caught the
# three natural rows among them. A run id can: rows from different processes differ, so a file that mixes a test with
# a pod run, or a `--limit` smoke with a real pass, is visible. Multiple run ids in a FILE are legitimate (a resumed
# or segmented run), so the audit reports them per cell rather than failing on them.
RUN_ID = RC.RUN_ID            # one id per process, from collect.py

# GUARDS.md rule 3 also asks for the run KIND on every row, so a row says what produced it and not only which code
# and which process. "real" by default; `--limit` sets "smoke" (it is a smoke by definition); the test fixture sets
# WS4_RUN_KIND=test. With this, the 2026-10-20 leak would have been self-evident in the rows themselves.
# run kind, id and git sha come from RC.row_meta(); nothing here defaults to "real"

CM_MIN_PER_SIDE = 4       # BRIEF_R: d_cm needs >= 4 items on each side; pre-registered, not to be lowered


def cm_eligible(recs: list[dict[str, Any]], min_per_side: int = CM_MIN_PER_SIDE) -> list[str]:
    """The items that CAN have a class-mean direction, from the bridge/distractor labels alone (the same combinatorial
    condition `class_mean_directions` applies). The coverage check needs this because an empty `d_cm` is a documented
    property of the bank, not a bug: BRIEF_R records 70 of 200 khop2 items eligible at the threshold of 4, while a
    small mock bank has none. Requiring the arm unconditionally would fail honest runs; never requiring it would hide
    the arm disappearing for the reason that cost a pod run."""
    n = collections.Counter(r["bridge"] for r in recs if r.get("bridge"))
    big = {k for k, c in n.items() if c >= min_per_side}
    return [r["key"] for r in recs if r.get("bridge") in big and r.get("distractor") in big]


def class_mean_directions(recs: list[dict[str, Any]], H: dict[str, np.ndarray], min_per_side: int = CM_MIN_PER_SIDE) -> dict[str, np.ndarray]:
    """d_cm per item: mean state of items whose bridge IS the distractor − mean over items whose bridge is the true one."""
    by: dict[str, list[np.ndarray]] = {}
    for r in recs:
        if r["key"] in H and r.get("bridge"):
            by.setdefault(r["bridge"], []).append(H[r["key"]])
    means = {k: np.mean(v, axis=0) for k, v in by.items() if len(v) >= min_per_side}
    out = {}
    for r in recs:
        a, b = means.get(r.get("distractor")), means.get(r.get("bridge"))
        if a is not None and b is not None:
            out[r["key"]] = ST._unit(a - b)
    return out


def random_direction(key: str, k: int, d: int, n: int = N_RANDOM, seed: int = RANDOM_SEED) -> np.ndarray:
    rng = np.random.default_rng(seed + RC.stable_offset(key))
    return [ST._unit(rng.standard_normal(d).astype(np.float32)) for _ in range(n)][k]


# ------------------------------------------------------------------ the pre-registered rhyme rule
VOWELS = "aeiouy"


def rhyme_key(word: str) -> str | None:
    w = "".join(ch for ch in word.lower() if ch.isalpha())
    for i, ch in enumerate(w):
        if ch in VOWELS and len(w) - i >= 2:
            return w[i:]
    return None


def rhymes(a: str, b: str) -> bool:
    ka, kb = rhyme_key(a), rhyme_key(b)
    if not ka or not kb or ka != kb:
        return False
    wa = "".join(c for c in a.lower() if c.isalpha())
    wb = "".join(c for c in b.lower() if c.isalpha())
    return wa != wb


def last_word(text: str) -> str:
    line = text.strip().split("\n")[0]
    words = "".join(ch if ch.isalpha() or ch.isspace() else " " for ch in line).split()
    return words[-1] if words else ""


# ------------------------------------------------------------------ one batched edited measurement
def _measure(target: M.Target, part: str, chunk: list[dict[str, Any]], layer: int, arm: str,
             deltas: dict[str, np.ndarray] | None, read_layer: int, scale: float | None, alpha: float) -> tuple[list[dict], list[tuple[str, np.ndarray]]]:
    """For one batch of items: the model's forced-choice log-probs on the item's pair(s) and the read-back state, with
    the item's own delta added at its own position (``deltas`` None = the natural, un-hooked pass)."""
    import torch

    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    pairs = (("bridge", "ids_po_bridge", "pos_po_bridge", "bridge_item"),
             ("answer", "ids_po_answer", "pos_po_answer", "answer_item")) if part == "khop" else \
            (("rhyme", "ids_po", "pos_po", "item"),)
    rows, spans, heads, owner, which = [], [], [], [], []
    for r in chunk:
        for name, ids_k, pos_k, item_k in pairs:
            ids_po, p = r[ids_k], r[pos_k]
            for c in r[item_k]["primary"]["candidates"]:
                rows.append(ids_po + LO.encode(tok, c))
                spans.append((p, p + 1))
                heads.append(len(ids_po))
                owner.append(r["key"])
                which.append(name)
    n_per = len(pairs) * 2
    if deltas is None:
        lps, _ = ST.edited_forward_batch(target.model, rows, spans, layer, None, pad, head_lens=heads)
        _, Hb = ST.edited_forward_batch(target.model, [r["ids_chat"] for r in chunk],
                                        [(r["pos_chat"], r["pos_chat"] + 1) for r in chunk], layer, None, pad,
                                        read_layer=read_layer)
    else:
        d_rows = np.stack([(alpha * scale * deltas[r["key"]]).astype(np.float32) for r in chunk for _ in range(n_per)])
        lps, _ = ST.edited_forward_batch(target.model, rows, spans, layer, torch.from_numpy(d_rows), pad, head_lens=heads)
        d_ch = np.stack([(alpha * scale * deltas[r["key"]]).astype(np.float32) for r in chunk])
        _, Hb = ST.edited_forward_batch(target.model, [r["ids_chat"] for r in chunk],
                                        [(r["pos_chat"], r["pos_chat"] + 1) for r in chunk], layer,
                                        torch.from_numpy(d_ch), pad, read_layer=read_layer)
    out, reads = [], []
    for j, r in enumerate(chunk):
        row: dict[str, Any] = {"key": f"{part}|{r['key']}|{layer}|{arm}", "module": MODULE, "experiment": "swap",
                               "part": part, "item": r["key"], "layer": layer, "arm": arm, "alpha": alpha,
                               "scale": scale, "position_chat": r["pos_chat"], "created_at": now_iso(),
                               **stamp()}
        for pi, (name, _ik, _pk, item_k) in enumerate(pairs):
            cands = r[item_k]["primary"]["candidates"]
            true = r[item_k]["primary"]["answer"]
            a, b = lps[j * n_per + 2 * pi], lps[j * n_per + 2 * pi + 1]
            lp_true, lp_dist = (a, b) if cands[0] == true else (b, a)
            row[f"lp_{name}_true"], row[f"lp_{name}_dist"] = lp_true, lp_dist
            row[f"lo_{name}"] = lp_true - lp_dist
            row[f"prefers_{name}_true"] = bool(lp_true > lp_dist)
        if part == "khop":
            row.update(template=r.get("template"), bridge=r.get("bridge"), distractor=r.get("distractor"),
                       answer=r.get("answer"), distractor_answer=r.get("distractor_answer"), answer_gated=r.get("answer_gated"))
        else:
            row.update(answer=r.get("answer"), distractor_answer=r.get("distractor_answer"))
        out.append(row)
        reads.append((r["key"], Hb[j].numpy().astype(np.float16)))
    return out, reads


def _save_reads(part: str, layer: Any, arm: str, reads: list[tuple[str, np.ndarray]]) -> None:
    """MERGE the cell's read-back states by item key, never overwrite.

    This overwrote the file with only the states just measured, which silently destroyed data on resume: `run_part`
    measures only the items whose ROWS are missing (`todo`), so a cell completed across two attempts kept the read-backs
    of the second attempt alone. Realised damage on the 2026-10-19 khop run, which was itself a resume: 22 of 7,192
    states lost, all at L24 (every L24 cell short by 4, d_answer by 2), which shrank R-S2's denominator from 136
    answer-flipped items to the 132 that happened to be measured in the surviving attempt. The rows were never
    affected, only the states, so nothing flagged it.
    """
    d = RB_DIR / part
    d.mkdir(parents=True, exist_ok=True)
    tag = f"L{layer}_{arm}" if layer is not None else "natural"
    f_npy, f_json = d / f"{tag}.npy", d / f"{tag}.json"
    merged: dict[str, np.ndarray] = {}
    if f_npy.exists() and f_json.exists():
        old_keys = json.loads(f_json.read_text())
        old_X = np.load(f_npy)
        if old_X.shape[0] == len(old_keys):          # a torn pair is discarded rather than mis-attributed
            merged = {k: old_X[i] for i, k in enumerate(old_keys)}
        else:
            log_line(ST.LOG, f"swap {part} {tag}: {old_X.shape[0]} states for {len(old_keys)} keys, rebuilding the cell")
    for k, v in reads:
        merged[k] = v                                # a re-measured item replaces its own state
    keys = list(merged)
    np.save(f_npy, np.stack([merged[k] for k in keys]))
    f_json.write_text(json.dumps(keys))


# ------------------------------------------------------------------ khop part
def prepare_khop(target: M.Target, recs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """Renders, edit positions (chat from the collector's index, prompt-only computed from the character span) and the
    single-token gate. Returns (items kept, [(item, reason) dropped])."""
    tok = target.tokenizer
    pos_chat = read_positions(KHOP_BRIDGE, "chat")
    keep, dropped = [], []
    for r in recs:
        bid = r["bridge_item"]["item_id"]
        if bid not in pos_chat:
            dropped.append((r["key"], "no resolved read position")); continue
        if not single_token(tok, r["bridge_jlens"], r["distractor_jlens"]):
            dropped.append((r["key"], "bridge pair not single-token")); continue
        rp = r.get("read_position") or {}
        c0, c1 = int(rp.get("char_start", -1)), int(rp.get("char_end", -1))
        if c0 < 0 or c1 <= c0:
            dropped.append((r["key"], "no character span")); continue
        ids_chat = RC.render_ids(tok, r["prompt_text"], "chat")
        if not 0 <= pos_chat[bid] < len(ids_chat):
            dropped.append((r["key"], "position outside the render")); continue
        out = dict(r, ids_chat=ids_chat, pos_chat=pos_chat[bid])
        ok = True
        for name, item_k in (("bridge", "bridge_item"), ("answer", "answer_item")):
            ids_po = RC.prompt_only_ids(tok, r[item_k])
            rng = char_span_tokens(tok, ids_po, r["prompt_text"], c0, c1, ST.ANCHOR_PO)
            if rng is None:
                dropped.append((r["key"], f"span not found in the {name} prompt-only render")); ok = False; break
            out[f"ids_po_{name}"], out[f"pos_po_{name}"] = ids_po, rng[1] - 1
        if not ok:
            continue
        out["answer_gated"] = single_token(tok, r["answer"], r["distractor_answer"])
        keep.append(out)
    return keep, dropped


def run_part(target: M.Target, readers: list[Any], part: str, keep: list[dict[str, Any]], layers: tuple[int, ...],
             alpha: float = ALPHA, k_random: int = N_RANDOM, batch: int = 8, read_layer: int = READ_LAYER,
             force_items: set[str] | None = None) -> dict[str, Any]:
    """The natural pass, then every (layer, arm) with the item's own direction; rows and read-backs are written as the
    run goes so a stop loses only the condition in flight.

    `force_items` re-measures those items even though their rows exist, to repair read-back states without duplicating
    rows — the recovery path for the 22 states the pre-merge `_save_reads` lost on 2026-10-19. Row appends are guarded
    by `done` everywhere, so a forced pass adds states and no rows.
    """
    force = set(force_items or ())
    tok = target.tokenizer
    jl = next((r for r in readers if isinstance(r, R.JLensReader)), None)
    if jl is None:
        raise SystemExit("the J-lens must be bound: it supplies the swap directions")
    SWAP_DIR.mkdir(parents=True, exist_ok=True)
    DIR_DIR.mkdir(parents=True, exist_ok=True)
    done = done_ids(ROWS_PATH, key="key")
    existing_rows = [r for r in read_jsonl(ROWS_PATH) if r.get("part") == part]   # for the §28 scale check
    ledger = StepLedger(step=f"swap_{part}", module=MODULE)
    summary: dict[str, Any] = {"part": part, "n_items": len(keep), "layers": list(layers), "alpha": alpha,
                               "k_random": k_random, "cells": {}}
    # natural pass (layer-independent; the hook is not installed at all)
    if force or not all(f"{part}|{r['key']}|None|{NATURAL}" in done for r in keep):
        nat_todo = [r for r in keep if f"{part}|{r['key']}|None|{NATURAL}" not in done or r["key"] in force]
        rows_all, reads_all = [], []
        with timed_call() as st:
            for s in range(0, len(nat_todo), batch):
                rows, reads = _measure(target, part, nat_todo[s: s + batch], layers[0], NATURAL, None, read_layer, None, 0.0)
                for row in rows:
                    row["key"] = f"{part}|{row['item']}|None|{NATURAL}"
                    row["layer"] = None
                rows_all += rows; reads_all += reads
        for row in rows_all:
            if row["key"] not in done:
                append_jsonl(ROWS_PATH, row)
        _save_reads(part, None, NATURAL, reads_all)
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        summary["cells"]["natural"] = {"n": len(rows_all), "wall_s": round(st.wall_s, 1)}
        print(f"[swap {part}] natural: {len(rows_all)} items in {st.wall_s:.0f}s", flush=True)
    for L in layers:
        try:
            X, idx = load_rp_states(KHOP_BRIDGE if part == "khop" else POETRY, "chat", L)
            by_id = {iid: X[i] for i, iid in enumerate(idx)}
            H = {r["key"]: by_id[r["bridge_item"]["item_id"]] for r in keep if part == "khop" and r["bridge_item"]["item_id"] in by_id}
        except FileNotFoundError:
            H = {}
        if not H:
            # Poetry legitimately has no cached read-position states, so it captures them directly. For khop the
            # cached states are the ones the EXISTING rows were measured from, so falling back here would mix two
            # code paths in one cell — which is how a 4-item repair could silently disagree with its 192 neighbours.
            if part == "khop":
                raise SystemExit(
                    f"swap khop L{L}: no cached read-position states for {KHOP_BRIDGE} at block {L}. The existing "
                    f"rows were measured from those states, so capturing fresh ones here would make this cell "
                    f"inconsistent. Rsync cache/g_agreement/r/states/{KHOP_BRIDGE}/chat_L{L}_rp.npy (+ index.json) "
                    f"and re-run; do not let it fall back.")
            H = capture_site_states(target, keep, L)
        scale = float(np.mean([np.linalg.norm(v) for v in H.values()])) if H else None
        if not scale:
            log_line(ST.LOG, f"swap {part} L{L}: no site states, layer skipped")
            continue
        dirs: dict[str, dict[str, np.ndarray]] = {a: {} for a in NAMED_ARMS}
        for r in keep:
            if part == "khop":
                g = swap_direction(jl, tok, r["bridge_jlens"], r["distractor_jlens"], L)
                ga = swap_direction(jl, tok, r["answer"], r["distractor_answer"], L) if r["answer_gated"] else None
            else:
                # the J-lens short forms, matching `poetry_completions`; they are byte-identical to the plain
                # candidates on the frozen bank (48/48 checked), so this changes no number — it removes a trap
                g = swap_direction(jl, tok, r["answer_jlens"], r["distractor_jlens"], L)
                ga = None
            if g is not None:
                dirs["d_swap"][r["key"]] = g
            if ga is not None:
                dirs["d_answer"][r["key"]] = ga
            h = H.get(r["key"])
            if h is not None:
                true, dist = ((r["bridge_jlens"], r["distractor_jlens"]) if part == "khop"
                              else (r["answer_jlens"], r["distractor_jlens"]))
                dl = logit_direction(target, h, true, dist, tok)
                if dl is not None:
                    dirs["d_logit"][r["key"]] = dl
        if part == "khop":
            dirs["d_cm"] = class_mean_directions(keep, H)
        require_primary_arm(part, L, dirs["d_swap"], len(keep))
        d_model = len(next(iter(H.values())))
        for k in range(k_random):
            dirs[f"d_rand{k}"] = {r["key"]: random_direction(r["key"], k, d_model, k_random) for r in keep}
        np.savez(DIR_DIR / f"{part}_L{L}.npz", **{f"{a}|{key}": v for a, m in dirs.items() for key, v in m.items()})
        for arm, per_item in dirs.items():
            if not per_item:
                summary["cells"][f"L{L}|{arm}"] = {"n": 0, "note": "no item had this direction"}
                continue
            todo = [r for r in keep if r["key"] in per_item
                    and (f"{part}|{r['key']}|{L}|{arm}" not in done or r["key"] in force)]
            if not todo:
                continue
            require_consistent_scale(part, L, arm, scale, existing_rows)
            rows_all, reads_all = [], []
            with timed_call() as st:
                for s in range(0, len(todo), batch):
                    rows, reads = _measure(target, part, todo[s: s + batch], L, arm, per_item, read_layer, scale, alpha)
                    rows_all += rows; reads_all += reads
            for row in rows_all:
                if row["key"] not in done:          # a forced re-measure repairs states, it never duplicates a row
                    append_jsonl(ROWS_PATH, row)
            _save_reads(part, L, arm, reads_all)
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
            summary["cells"][f"L{L}|{arm}"] = {"n": len(rows_all), "scale": scale, "wall_s": round(st.wall_s, 1)}
            print(f"[swap {part}] L{L} {arm}: {len(rows_all)} items in {st.wall_s:.0f}s", flush=True)
    r = ledger.flush()
    log_line(ST.LOG, f"swap {part}: {len(keep)} items × {len(layers)} layers; cells {len(summary['cells'])} {r}")
    return summary


def capture_site_states(target: M.Target, keep: list[dict[str, Any]], layer: int) -> dict[str, np.ndarray]:
    """The natural state at each item's own edit position (used where the collector cached none, i.e. poetry)."""
    out = {}
    for r in keep:
        acts = M.capture(target.model, r["ids_chat"], [layer], [r["pos_chat"]])
        out[r["key"]] = acts[layer][0].numpy().astype(np.float32)
    return out


# ------------------------------------------------------------------ poetry part
def prepare_poetry(target: M.Target, recs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """Renders and the line-break edit position for the couplets, plus the single-token gate on the rhyme pair."""
    tok = target.tokenizer
    keep, dropped = [], []
    for r in recs:
        # BOTH spellings are gated: the rhyme verdict compares the plain names, while the swap and logit directions are
        # built from the J-lens short forms (`poetry_completions`), so gating only one lets the primary arm silently
        # produce no direction for an item that passed. They coincide on the current bank (48/48 items, both forms
        # single-token) — the gate is here so a later bank cannot reintroduce the empty-arm failure.
        if not single_token(tok, r["answer"], r["distractor_answer"]):
            dropped.append((r["key"], "rhyme pair not single-token")); continue
        if not single_token(tok, r["answer_jlens"], r["distractor_jlens"]):
            dropped.append((r["key"], "rhyme pair's J-lens short forms not single-token")); continue
        ids_chat = RC.render_ids(tok, r["prompt_text"], "chat")
        p_ch = line_break_position(tok, ids_chat, r["prompt_text"], ST.ANCHOR_CHAT)
        ids_po = RC.prompt_only_ids(tok, r["item"])
        p_po = line_break_position(tok, ids_po, r["prompt_text"], ST.ANCHOR_PO)
        if p_ch is None or p_po is None:
            dropped.append((r["key"], "line break not located")); continue
        keep.append(dict(r, ids_chat=ids_chat, pos_chat=p_ch, ids_po=ids_po, pos_po=p_po))
    return keep, dropped


# ------------------------------------------------------------------ reader scoring (needs a bound reader: on the pod)
def reader_pair(reader_name: str, part: str, pair: str, r: dict[str, Any]) -> tuple[str, str] | None:
    """(true, distractor) for one reader and one pair: the J-lens scores its single-token short forms, every other
    reader the plain names. None when the item has no scorable pair (the answer pair of an ungated khop item)."""
    jlensy = reader_name in ("jlens", "rlens")
    if part == "khop" and pair == "bridge":
        return (r["bridge_jlens"], r["distractor_jlens"]) if jlensy else (r["bridge"], r["distractor"])
    if part == "khop":
        return (r["answer"], r["distractor_answer"]) if r.get("answer_gated") else None
    return (r["answer_jlens"], r["distractor_jlens"]) if jlensy else (r["answer"], r["distractor_answer"])


def parse_tag(tag: str) -> tuple[int | None, str]:
    """`natural` -> (None, 'natural'); `L32_d_swap` -> (32, 'd_swap')."""
    if tag == NATURAL:
        return None, NATURAL
    layer, arm = tag.split("_", 1)
    return int(layer[1:]), arm


def score_readbacks(reader: Any, part: str, by_key: dict[str, dict[str, Any]], read_layer: int = READ_LAYER,
                    batch: int = 32) -> int:
    """Every reader's native score on every saved read-back state, per pair the part defines. Reads only the `.npy`
    files and the items, but the reader passed in must already be bound, which needs the target model (and the Oracle
    and skip-lens arms score by forward passes), so this runs on the pod, not on the Mac. Resumable."""
    import torch

    d = RB_DIR / part
    if not d.exists():
        return 0
    done = done_ids(READERS_PATH, key="key")
    ledger = StepLedger(step=f"swap_lo_{reader.name}", module=MODULE, extra={"part": part})
    pairs = ("bridge", "answer") if part == "khop" else ("rhyme",)
    n = 0
    for f in sorted(d.glob("*.npy")):
        keys_file = d / f"{f.stem}.json"
        if not keys_file.exists():
            raise RuntimeError(f"{f.name} has no companion {keys_file.name}: cannot attribute rows to items")
        keys = json.loads(keys_file.read_text())
        X = np.load(f).astype(np.float32)
        if X.shape[0] != len(keys):
            raise RuntimeError(f"{f.name}: {X.shape[0]} states for {len(keys)} keys")
        layer, arm = parse_tag(f.stem)
        for pair in pairs:
            rows_k, cps, idxs = [], [], []
            for i, k in enumerate(keys):
                r = by_key.get(k)
                if r is None:
                    continue
                cp = reader_pair(reader.name, part, pair, r)
                if cp is None:
                    continue
                key = f"{reader.name}|{part}|{k}|{layer}|{arm}|{pair}"
                if key in done:
                    continue
                rows_k.append(key); cps.append(cp); idxs.append(i)
            if not cps:
                continue
            first = by_key[keys[idxs[0]]]
            fam = RC.register_templates(first["bridge_item" if part == "khop" else "item"]["primary"])
            with timed_call() as st:
                res = LO.score_lo(reader, torch.from_numpy(X[idxs]), cps, fam, layer=read_layer, batch=batch)
            for key, i, rr in zip(rows_k, idxs, res):
                append_jsonl(READERS_PATH, {"key": key, "module": MODULE, "experiment": "swap", "reader": reader.name,
                                            **stamp(),
                                            "part": part, "item": keys[i], "layer": layer, "arm": arm, "pair": pair,
                                            "cand_true": rr["cand_A"], "cand_dist": rr["cand_B"],
                                            "lp_true": rr["lp_A"], "lp_dist": rr["lp_B"], "lo": rr["lo"],
                                            "unscorable": rr["unscorable"], "created_at": now_iso()})
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush()
    return n


# ------------------------------------------------------------------ poetry: greedy completion under the edit
def completions_path(part: str) -> Path:
    return POETRY_POOL_PATH if part == POETRY_POOL else POETRY_PATH


def poetry_completions(target: M.Target, jl: R.JLensReader, keep: list[dict[str, Any]], layers: tuple[int, ...],
                       alpha: float = ALPHA, k_random: int = N_RANDOM, gen_tokens: int = GEN_TOKENS,
                       part: str = "poetry") -> dict[str, Any]:
    """One greedy continuation per (item, layer, arm) with the item's own delta replacing the state at the line break,
    plus one natural continuation per item; the rhyme verdict is the pre-registered rule."""
    from projects.g_agreement.core import edit as E

    tok = target.tokenizer
    out_path = completions_path(part)
    done = done_ids(out_path, key="key")
    ledger = StepLedger(step=f"swap_{part}_gen", module=MODULE)
    out: dict[str, Any] = {"part": part, "n_items": len(keep), "cells": {}}
    sites = {L: capture_site_states(target, keep, L) for L in layers}

    def row(r, layer, arm, res, extra=None):
        w = last_word(res["answer_text"])
        d = {"key": f"{part}|{r['key']}|{layer}|{arm}", "module": MODULE, "experiment": "swap", "part": part,
             **stamp(),
             "item": r["key"], "layer": layer, "arm": arm, "completion": res["answer_text"], "last_word": w,
             "rhymes_true": rhymes(w, r["answer"]), "rhymes_planted": rhymes(w, r["distractor_answer"]),
             "true": r["answer"], "planted": r["distractor_answer"], "position_chat": r["pos_chat"],
             "n_new_tokens": res.get("n_new_tokens"), "created_at": now_iso()}
        d.update(extra or {})
        return d

    with timed_call() as st:
        for r in keep:
            if f"{part}|{r['key']}|None|{NATURAL}" in done:
                continue
            res = E.generate_with_edited_state(target, r["ids_chat"], sites[layers[0]][r["key"]], layer=layers[0],
                                               pos=r["pos_chat"], max_new_tokens=gen_tokens)
            append_jsonl(out_path, row(r, None, NATURAL, res, {"alpha": 0.0}))
    ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    out["cells"][NATURAL] = {"n": len(keep), "wall_s": round(st.wall_s, 1)}
    print(f"[swap poetry] natural: {len(keep)} completions in {st.wall_s:.0f}s", flush=True)
    for L in layers:
        H = sites[L]
        scale = float(np.mean([np.linalg.norm(v) for v in H.values()]))
        arms: dict[str, dict[str, np.ndarray]] = {"d_swap": {}, "d_logit": {}}
        for r in keep:
            g = swap_direction(jl, tok, r["answer_jlens"], r["distractor_jlens"], L)
            if g is not None:
                arms["d_swap"][r["key"]] = g
            dl = logit_direction(target, H[r["key"]], r["answer_jlens"], r["distractor_jlens"], tok)
            if dl is not None:
                arms["d_logit"][r["key"]] = dl
        require_primary_arm(part, L, arms["d_swap"], len(keep))
        d_model = len(H[keep[0]["key"]])
        for k in range(k_random):
            arms[f"d_rand{k}"] = {r["key"]: random_direction(r["key"], k, d_model, k_random) for r in keep}
        for arm, per_item in arms.items():
            n = 0
            with timed_call() as st:
                for r in keep:
                    if r["key"] not in per_item or f"{part}|{r['key']}|{L}|{arm}" in done:
                        continue
                    v = H[r["key"]] + alpha * scale * per_item[r["key"]]
                    res = E.generate_with_edited_state(target, r["ids_chat"], v, layer=L, pos=r["pos_chat"],
                                                       max_new_tokens=gen_tokens)
                    append_jsonl(out_path, row(r, L, arm, res, {"alpha": alpha, "scale": scale,
                                                                   "norm_ratio": float(np.linalg.norm(v) / np.linalg.norm(H[r["key"]]))}))
                    n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
            out["cells"][f"L{L}|{arm}"] = {"n": n, "wall_s": round(st.wall_s, 1)}
            print(f"[swap poetry] L{L} {arm}: {n} completions in {st.wall_s:.0f}s", flush=True)
    ledger.flush()
    return out


# ------------------------------------------------------------------ pre-checks (the gate before any GPU run)
POS_COS_MIN = 0.999       # my computed position must reproduce the collector's cached read-position state
ZERO_TOL = 1e-3           # hooked zero delta vs the un-hooked forward
FD_BAND = ST.FD_BAND      # the §4.5 band, reused


def precheck(target: M.Target, jl: R.JLensReader, part: str, keep: list[dict[str, Any]], layer: int = 32,
             n_zero: int = 4, n_fd: int = 2, read_layer: int = READ_LAYER) -> dict[str, Any]:
    """The three gating checks of the WS4 / SWAP hand-off note. (1) position: a capture at the position this module
    computes must match the collector's cached `_rp` state (khop only — poetry has no cached position, so the check is
    the decoded token instead). (2) zero delta: the hooked forward with a zero delta equals the un-hooked one at the
    single edit position. (3) the J-lens swap direction passes a central finite difference."""
    import torch

    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    out: dict[str, Any] = {"part": part, "layer": layer, "n_items": len(keep), "created_at": now_iso(), "checks": {}}
    # 1. position
    if part == "khop":
        X, idx = load_rp_states(KHOP_BRIDGE, "chat", layer)
        cached = {iid: X[i] for i, iid in enumerate(idx)}
        cos, missing = [], 0
        for r in keep:
            ref = cached.get(r["bridge_item"]["item_id"])
            if ref is None:
                missing += 1
                continue
            mine = M.capture(target.model, r["ids_chat"], [layer], [r["pos_chat"]])[layer][0].numpy()
            a, b = mine / (np.linalg.norm(mine) + 1e-9), ref / (np.linalg.norm(ref) + 1e-9)
            cos.append(float(a @ b))
        rec = {"n": len(cos), "missing_cached": missing, "min_cos": (min(cos) if cos else None),
               "mean_cos": (float(np.mean(cos)) if cos else None), "n_below_threshold": sum(c < POS_COS_MIN for c in cos),
               "threshold": POS_COS_MIN}
        rec["pass"] = bool(cos) and missing == 0 and rec["n_below_threshold"] == 0
    else:
        toks = [tok.decode([r["ids_chat"][r["pos_chat"]]]) for r in keep]
        rec = {"n": len(toks), "distinct_tokens": sorted(set(toks))[:6],
               "all_newline": all("\n" in t for t in toks)}
        rec["pass"] = bool(toks) and rec["all_newline"]
    out["checks"]["position"] = rec
    # 2. zero delta at the single edit position
    sub = keep[:n_zero]
    ids_list = [r["ids_chat"] for r in sub]
    spans = [(r["pos_chat"], r["pos_chat"] + 1) for r in sub]
    d_model = int(target.model.get_input_embeddings().weight.shape[1])
    _, H0 = ST.edited_forward_batch(target.model, ids_list, spans, layer, None, pad, read_layer=read_layer)
    _, Hz = ST.edited_forward_batch(target.model, ids_list, spans, layer, torch.zeros(len(sub), d_model), pad,
                                    read_layer=read_layer)
    rec = {"n": len(sub), "max_abs_dstate": float((H0 - Hz).abs().max())}
    rec["pass"] = rec["max_abs_dstate"] < ZERO_TOL
    out["checks"]["zero_delta"] = rec
    # 3. the J-lens swap direction against a central finite difference
    first = keep[0]
    fam = RC.register_templates(first["bridge_item" if part == "khop" else "item"]["primary"])
    rec = {"n": 0, "items": [], "band": list(FD_BAND)}
    if part == "khop":
        X, idx = load_rp_states(KHOP_BRIDGE, "chat", read_layer)
        states = {iid: X[i] for i, iid in enumerate(idx)}
        pick = [(r, states.get(r["bridge_item"]["item_id"])) for r in keep[:n_fd]]
    else:
        H = capture_site_states(target, keep[:n_fd], read_layer)
        pick = [(r, H.get(r["key"])) for r in keep[:n_fd]]
    for r, h in pick:
        if h is None:
            continue
        true, dist = (r["bridge_jlens"], r["distractor_jlens"]) if part == "khop" else (r["answer_jlens"], r["distractor_jlens"])
        G = ST.jlens_grads(jl, tok, dist, true, read_layer)       # RAW gradient: finite_difference's pred is eps*||g||,
        if G is None:                                              # so handing it a unit vector would measure ||g||
            continue
        # the gradient points distractor-minus-true, so the LO of (distractor, true) must RISE along it
        fd = ST.finite_difference(jl, torch.from_numpy(np.asarray(h)), G[0], dist, true, fam, read_layer, eps_rel=1e-2)
        rec["items"].append(fd); rec["n"] += 1
    rec["ratio_central"] = [x["ratio_central"] for x in rec["items"]]
    rec["pass"] = bool(rec["items"]) and all(x["delta_plus"] > 0 and x["ratio_central"] is not None
                                             and FD_BAND[0] <= x["ratio_central"] <= FD_BAND[1] for x in rec["items"])
    out["checks"]["jlens_direction_fd"] = rec
    out["all_pass"] = all(v.get("pass") is True for v in out["checks"].values())
    return out


# ------------------------------------------------------------------ main
def bind_readers_for(target: M.Target, names: list[str], layers: tuple[int, ...], read_layer: int = READ_LAYER) -> list[Any]:
    """Like `steer.bind_readers`, except the J-lens keeps **every layer this experiment edits** plus the read layer.
    `steer.bind_readers` keeps only [L_EDIT, L_READ] = [38, 42], which is right for R5 (it edits at 38) and wrong here:
    SWAP edits 24-44 step 4, none of which is 38 or 42, so `swap_direction` returned None at every layer and the
    PRIMARY arm (d_swap, and d_answer) silently produced no rows while the control arms looked healthy. Caught by the
    foreground smoke on the pod, not by the tests, because the mock fixture binds the lens at every mock layer."""
    readers: list[Any] = []
    if "jlens" in names:
        keep = sorted(set(int(L) for L in layers) | {int(read_layer)})
        readers.append(R.JLensReader().bind(target, layers_keep=keep))
    if "olens" in names:
        readers.append(R.OLensReader().bind(target))
    for arm in ("skip_a", "skip_d"):
        if arm in names:
            readers.append(R.SKIPLENS_READERS[arm]().bind(target))
    return readers


def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--part", choices=["khop", "poetry", POETRY_POOL], required=True,
                    help=f"{POETRY_POOL} = BRIEF_R §28 (SWAP-P): the 50 POOL couplets, never edited or read")
    ap.add_argument("--phase", choices=["precheck", "A", "score", "B", "audit"], required=True,
                    help="A = GPU edits/read-backs (+ poetry completions); score = readers on the saved read-backs (loads the target); B = the NLA; audit = rule 5, states vs rows per cell (files only, no model)")
    ap.add_argument("--layers", nargs="*", type=int, default=list(LAYERS))
    ap.add_argument("--alpha", type=float, default=ALPHA)
    ap.add_argument("--k-random", type=int, default=N_RANDOM)
    ap.add_argument("--readers", nargs="*", default=["jlens", "olens", "skip_a"])
    ap.add_argument("--limit", type=int, default=0, help="first N items (smoke runs only)")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--run-kind", choices=list(RC.RUN_KINDS), default=None,
                    help="GUARDS.md rule 3: a real run says --run-kind real. The default is \"unknown\", never "
                         "\"real\" by omission; --limit forces \"smoke\". --datasets never implies smoke")
    ap.add_argument("--remeasure-items", nargs="*", default=None,
                    help="item keys to re-measure even though their rows exist, to repair lost read-back states; "
                         "rows are never duplicated (the 2026-10-19 L24 recovery)")
    a = ap.parse_args(argv)
    if a.run_kind:
        RC.set_run_kind(a.run_kind)
    RC.require_frozen_r(a.allow_unfrozen)
    # §28's items are the POOL split; the 48 test couplets are excluded by construction, not by a filter.
    recs = (paired_khop() if a.part == "khop"
            else poetry_items(split="pool") if a.part == POETRY_POOL else poetry_items())
    if a.limit:
        recs = recs[: a.limit]
        # A smoke run writes to its OWN directory. It used to share the real files, and that is the root cause of
        # two defects found on 2026-10-19/20: the `--limit 2` and `--limit 4` smokes at 18:29 and 18:36 wrote L24 rows
        # for four items, so the full pass at 18:40 skipped those rows (`done`) and overwrote the read-back cell with
        # its own 192 states (the 22 "lost" states); and those rows carry the smoke's edit scale, averaged over 2 or 4
        # items (86.22 / 83.53) instead of s(24) = 76.07 over all 196, so within two items the arms are not
        # norm-matched — which BRIEF_R requires ("every arm at a layer sharing the same norm so the random control is
        # exact"). WS3 found the scale half; the audit now catches it, and this stops it at the source.
        RC.set_run_kind("smoke")                 # a --limit run is a smoke, whatever was declared
        smoke_paths(a.limit)
        print(f"[swap] --limit {a.limit}: SMOKE outputs -> {SWAP_DIR} (the real files are untouched)", flush=True)
    SWAP_DIR.mkdir(parents=True, exist_ok=True)
    layers = tuple(a.layers)
    if a.phase == "audit":                       # files only: no model, no GPU, runs on the Mac
        fails, summary = audit_cells(a.part)
        for n in summary["notes"]:
            print(f"[swap audit {a.part}] {n}", flush=True)
        for line in fails:
            print(line, flush=True)
        print(f"[swap audit {a.part}] {summary['rows']} rows over {summary['cells_with_rows']} cells; "
              f"{summary['cells_checked']} read-back cells, {summary['states']} states; "
              f"missing {summary['missing']}, orphans {summary['orphans']}", flush=True)
        log_line(ST.LOG, f"swap audit {a.part}: {len(fails)} failures, missing {summary['missing']}, "
                         f"orphans {summary['orphans']} over {summary['cells_checked']} cells")
        return 1 if fails else 0
    if a.phase == "score":                       # CPU: no target model, no pod needed
        nla = "nla" in a.readers
        if nla:
            raise SystemExit("the NLA is phase B (it loads its own model), not --phase score")
        target = load_target_timed(MODULE)
        readers = bind_readers_for(target, a.readers, layers)
        prep = prepare_khop(target, recs)[0] if a.part == "khop" else prepare_poetry(target, recs)[0]
        by_key = {r["key"]: r for r in prep}
        total = sum(score_readbacks(rd, a.part, by_key) for rd in readers)
        log_line(ST.LOG, f"swap {a.part} score: {total} reader rows over {len(by_key)} items")
        M.unload(target)
        return 0
    if a.phase == "B":
        nla = R.NLAReader().bind()
        target_tok = nla.tokenizer
        prep = recs                               # the NLA only needs the items' candidate names and the saved states
        by_key = {r["key"]: r for r in prep}
        n = score_readbacks(nla, a.part, by_key)
        log_line(ST.LOG, f"swap {a.part} phase B: {n} NLA rows")
        nla.unload()
        return 0
    target = load_target_timed(MODULE)
    readers = bind_readers_for(target, a.readers, layers)
    jl = next((r for r in readers if isinstance(r, R.JLensReader)), None)
    if jl is None:
        raise SystemExit("the J-lens must be bound: it supplies the swap directions")
    keep, dropped = (prepare_khop(target, recs) if a.part == "khop" else prepare_poetry(target, recs))
    if a.part == POETRY_POOL:        # §28 asks for the gate's coverage to be reported, not just applied
        print(f"[swap {a.part}] gate coverage: {len(keep)}/{len(recs)} couplets kept, {len(dropped)} dropped "
              f"({dict(collections.Counter(d[1] for d in dropped))})", flush=True)
    log_line(ST.LOG, f"swap {a.part}: {len(keep)} items kept, {len(dropped)} dropped "
                     f"({dict(collections.Counter(d[1] for d in dropped))})")
    if not keep:
        raise SystemExit(f"no {a.part} item survived the gate; see the log line above")
    if a.phase == "precheck":
        rec = precheck(target, jl, a.part, keep, layer=layers[0])
        rec["dropped"] = dropped[:40]
        PRECHECK_PATH.parent.mkdir(parents=True, exist_ok=True)
        old = json.loads(PRECHECK_PATH.read_text()) if PRECHECK_PATH.exists() else []
        PRECHECK_PATH.write_text(json.dumps(old + [rec], indent=1))
        print(f"[swap precheck {a.part}] " + ", ".join(f"{k}={v.get('pass')}" for k, v in rec["checks"].items()), flush=True)
        log_line(ST.LOG, f"swap precheck {a.part}: " + " ".join(f"{k}={v.get('pass')}" for k, v in rec["checks"].items()))
        M.unload(target)
        return 0 if rec["all_pass"] else 1
    force = set(a.remeasure_items or ())
    if a.part == "khop":
        summary = run_part(target, readers, a.part, keep, layers, a.alpha, a.k_random, a.batch, force_items=force)
    else:
        # Poetry needs BOTH passes. `run_part` writes the forced-choice rhyme readout and, crucially, the read-back
        # states at the read layer, which `poetry_completions` never saved — so until 2026-10-20 no reader could be
        # scored on poetry at all and the pre-registered measurement (ii) did not exist. It runs FIRST because it is
        # cheap (batched forwards) and it is what the readers need; the generation pass is the expensive one and is
        # resumable, so an interrupted re-run still leaves the states behind.
        summary = {"part": a.part,
                   "readback": run_part(target, readers, a.part, keep, layers, a.alpha, a.k_random, a.batch,
                                        force_items=force),
                   "completions": poetry_completions(target, jl, keep, layers, a.alpha, a.k_random, part=a.part)}
    (RC.RESULTS / f"swap_{a.part}_summary.json").write_text(json.dumps(summary, indent=1))
    M.unload(target)
    empty = require_arm_coverage(a.part, layers, keep, a.k_random)
    if empty:
        msg = f"swap {a.part}: {len(empty)} required arm cells have NO rows: {', '.join(empty[:12])}"
        print("[swap] " + msg, flush=True)
        log_line(ST.LOG, msg)
        return 1
    log_line(ST.LOG, f"swap {a.part}: arm coverage complete over {len(layers)} layers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
