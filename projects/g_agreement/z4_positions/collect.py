"""Z4 matched-layer position dissection at L38 (GPU; BRIEF_Z §Z4). On the 64 X2 pairs (full L38/L42 captures in
cache/g_agreement/x/full) the planted swap h' = h_A + α(h_B − h_A) (and the mirror from B) is applied at ONE position
at a time, then at every position but one, then as a full swap with one position restored; the model's greedy decode,
its first-token answer log-odds, the read-back block-42 last-token vector and the readers' native LO are recorded as in
X2/Y2. Position subsample (seed 0, drawn BEFORE any decode): at most Z4_MAX_POSITIONS per prompt, always including every
differing (name/object/symbol) position, the question's first token (the first equal position after the last differing
one) and the last token; the rest uniform.

Arms (condition, key = pair|source|Z4|condition|alpha|position):
  single        one position i, α ∈ Z4_SINGLE_ALPHAS                                      [--stage single]
  rand_single   control: Z4_N_RAND (pair, source, position) triples drawn by seed 0, a seeded random unit direction
                scaled to ‖Δ(i)‖, α 1                                                      [--stage single]
  name_only / name_removed   REUSED from Y2 at the same α (rows carry reused_key; no decode)
  all_except    every position but i, α 1, for the top-K single positions per family (highest flip rate at α 1 over
                the family's single entries with n ≥ Z4_TOP_MIN_N, ties by position index)  [--stage dependent]
  pair2         (BRIEF_Z deviation 2026-10-09 (2)) interpolation at the two positions {i, j} only, for every one of the
                C(K, 2) pairs of the same top-K, α ∈ Z4_PAIR2_ALPHAS, on Z4_PAIR2_N_ITEMS (pair, source) items per
                family and position pair (seed C.stable_seed("z4", "pair2", family, 0): one permutation of the family's
                pairs; the first eligible pairs, i.e. with both positions inside the render, are taken in that order,
                the first half from source A and the second from B). Key position = "i-j" (i < j)  [--stage dependent]
  restore       (deviation (1): a DETERMINISM CHECK only) all positions set to the other state, position i restored
                to this state, α 1 — at α 1 the same block-38 state as all_except:i. Z4_N_RESTORE_PER_FAMILY
                (pair, source, position) triples per family drawn by seed 0 (C.stable_seed("z4", "restore", family, 0))
                from the family's all_except table; each is compared with its all_except twin  [--stage dependent]

    python -m projects.g_agreement.z4_positions.collect --phase A --stage single
    python -m projects.g_agreement.z4_positions.collect --phase A --stage dependent
    python -m projects.g_agreement.z4_positions.collect --phase B            # NLA LO on every read vector
  (--stage all runs single then dependent in one model load.)

Cap: the total planned decodes are printed at run start; the run refuses if they exceed Z4_DECODE_CAP (6,500). The single
stage prints the pre-deviation plan (single + rand_single + the all_except/restore upper bound 2·2·K per pair, unchanged
so that the running single stage is reproducible); the dependent stage prints and caps the FULL-run table
(single + rand_single + all_except + pair2 + restore; ≈ 3,840 + 64 + 640 + 600 + 32 = 5,176 on the 64 X2 pairs).
Outputs (resumable by key):
  cache/g_agreement/z/z4_behaviour.jsonl, cache/g_agreement/z/z4_readvecs/{key}.pt, cache/g_agreement/z/z4_lo.jsonl,
  results/g_agreement/z4/{log.md, skipped.json, positions.json}
Sign conventions as X2: cand_A = own answer, cand_B = planted (other) candidate; lo_model = lp(first B) − lp(first A);
lo_toward_other = reader score(B) − score(A). Positive = toward the planted candidate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import edit as E
from projects.g_agreement.core import generate as G
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, read_jsonl, timed_call
from projects.g_agreement.x2_causal import collect as X

MODULE = "z4"
Z4_SITE = "Z4"
Z4_EDIT_LAYER = 38
Z4_MAX_POSITIONS = 15
Z4_SINGLE_ALPHAS: tuple[float, ...] = (0.75, 1.0)
Z4_DEPENDENT_ALPHA = 1.0
Z4_REUSE_ALPHAS: tuple[float, ...] = (0.75, 1.0)
Z4_REUSED_CONDITIONS: tuple[str, ...] = ("name_only", "name_removed")
Z4_TOP_K = 5
Z4_TOP_MIN_N = 8  # a position needs this many single entries at α 1 in the family to be ranked (fallback: all)
Z4_N_RAND = 64
Z4_DECODE_CAP = 6500
Z4_SEED = 0
Z4_PAIR2_ALPHAS: tuple[float, ...] = (0.5, 0.75, 1.0)
Z4_PAIR2_N_ITEMS = 10  # (pair, source) items per family and position pair
Z4_N_RESTORE_PER_FAMILY = 16  # restore = determinism check only (deviation 2026-10-09 (1))
Z4_CONDITIONS: tuple[str, ...] = ("single", "rand_single", "all_except", "restore", "pair2", "name_only", "name_removed")
# the single-stage plan printout lists exactly these (kept as it was when the single stage was launched)
Z4_NEW_CONDITIONS: tuple[str, ...] = ("single", "rand_single", "all_except", "restore")
# every decoded condition (ledgers, the dependent stage's full-run plan)
Z4_DECODED_CONDITIONS: tuple[str, ...] = ("single", "rand_single", "all_except", "pair2", "restore")
Z4_STAGE_OF = {"single": "single", "rand_single": "single", "all_except": "dependent", "restore": "dependent", "pair2": "dependent"}
Z4_POSITIONS_KIND = {"single": "single", "rand_single": "single", "all_except": "all_except_one", "restore": "all_restore_one",
                     "pair2": "pair", "name_only": "differing", "name_removed": "equal"}
ROLES = ("diff", "question_first", "last", "uniform")

Z_DIR = C.CACHE_DIR / "z"
BEH_PATH = Z_DIR / "z4_behaviour.jsonl"
LO_PATH = Z_DIR / "z4_lo.jsonl"
READVEC_DIR = Z_DIR / "z4_readvecs"
RESULTS = C.RESULTS_DIR / "z4"
LOG = RESULTS / "log.md"
SKIPPED = RESULTS / "skipped.json"
POSITIONS_JSON = RESULTS / "positions.json"
Y2_BEH_PATH = C.CACHE_DIR / "y" / "y2_behaviour.jsonl"
SAVE_DTYPE = X.SAVE_DTYPE
BEHAVIOUR_TOKENS = X.BEHAVIOUR_TOKENS
DEFAULT_BATCH = X.DEFAULT_BATCH


# ------------------------------------------------------------------ keys
def z4_entry_key(e: dict[str, Any]) -> str:
    """``pair|source|Z4|condition|alpha|position`` (position None for the reused Y2 arms)."""
    return f"{e['pair_id']}|{e['source']}|{Z4_SITE}|{e['condition']}|{float(e['alpha'])}|{e['position']}"


def positions_seed(pair_id: str, seed: int = Z4_SEED) -> int:
    return C.stable_seed(MODULE, "positions", pair_id, seed)


def rand_dir_seed(pair_id: str, source: str, position: int) -> int:
    return C.stable_seed(MODULE, "rand_dir", f"{pair_id}|{source}", position)


def rand_triples_seed(seed: int = Z4_SEED) -> int:
    return C.stable_seed(MODULE, "rand_single", "all", seed)


def pair2_seed(family: str, seed: int = Z4_SEED) -> int:
    return C.stable_seed(MODULE, "pair2", family, seed)


def restore_seed(family: str, seed: int = Z4_SEED) -> int:
    return C.stable_seed(MODULE, "restore", family, seed)


def pair_label(i: int, j: int) -> str:
    """Key position of a pair2 entry: ``"i-j"`` with i < j."""
    i, j = sorted((int(i), int(j)))
    return f"{i}-{j}"


def parse_pair_label(label: str) -> tuple[int, int]:
    i, j = (int(x) for x in str(label).split("-"))
    return i, j


# ------------------------------------------------------------------ position subsample
RULE_PLAIN = "first equal token after the last differing one"
RULE_ALNUM = "first equal token after the last differing one with an alphanumeric character"


def question_first_position(ids_A: list[int], ids_B: list[int], tokenizer: Any = None) -> int:
    """The brief's 'question's first token': the first position after the last differing one where the two renders
    agree. With a ``tokenizer`` (the pod run) punctuation-only tokens are skipped (the period closing the last
    statement sits right after the last name/object token), falling back to the plain rule if none qualifies.
    Raises if the renders do not differ."""
    diff = E.differing_positions(ids_A, ids_B)
    if not diff:
        raise ValueError("identical renders: no differing positions")
    T = len(ids_A)
    equal = [i for i in range(diff[-1] + 1, T) if int(ids_A[i]) == int(ids_B[i])]
    if not equal:
        raise ValueError("no equal position after the last differing one")
    if tokenizer is not None:
        for i in equal:
            if any(ch.isalnum() for ch in str(tokenizer.decode([int(ids_A[i])], skip_special_tokens=True))):
                return i
    return equal[0]


def z4_positions(pair_id: str, ids_A: list[int], ids_B: list[int], *, max_positions: int = Z4_MAX_POSITIONS, seed: int = Z4_SEED,
                 tokenizer: Any = None) -> dict[str, Any]:
    """The pair's position subsample: every differing position, the question's first token and the last token always;
    the rest uniform without replacement (seeded per pair from ``seed``) up to ``max_positions`` in total. Returns
    ``{positions (sorted), roles {pos: role}, n_tokens, n_differing, question_first, fixed, seed, rule}``."""
    import numpy as np

    T = len(ids_A)
    diff = E.differing_positions(ids_A, ids_B)
    q = question_first_position(ids_A, ids_B, tokenizer)
    roles: dict[int, str] = {}
    for i in diff:
        roles[i] = "diff"
    roles.setdefault(q, "question_first")
    roles.setdefault(T - 1, "last")
    fixed = sorted(roles)
    rest = [i for i in range(T) if i not in roles]
    n_extra = max(0, int(max_positions) - len(fixed))
    if n_extra >= len(rest):
        chosen = rest
    else:
        rng = np.random.default_rng(positions_seed(pair_id, seed))
        chosen = sorted(int(i) for i in rng.choice(len(rest), size=n_extra, replace=False))
        chosen = [rest[i] for i in chosen]
    for i in chosen:
        roles[i] = "uniform"
    pos = sorted(roles)
    return {"positions": pos, "roles": {int(i): roles[i] for i in pos}, "n_tokens": T, "n_differing": len(diff), "question_first": q,
            "fixed": fixed, "seed": int(seed), "max_positions": int(max_positions), "rule": RULE_ALNUM if tokenizer is not None else RULE_PLAIN}


def build_positions(pairs: list[dict[str, Any]], full_dir: Path | None = None, *, max_positions: int = Z4_MAX_POSITIONS, seed: int = Z4_SEED,
                    tokenizer: Any = None) -> dict[str, dict[str, Any]]:
    """Position subsample of every pair from the cached renders (``{pair_id: z4_positions(...)}``)."""
    import torch

    out = {}
    for p in pairs:
        ids = {v: list(torch.load(X.full_path(p[v]["item_id"], full_dir), map_location="cpu")["ids"]) for v in ("A", "B")}
        out[p["pair_id"]] = z4_positions(p["pair_id"], ids["A"], ids["B"], max_positions=max_positions, seed=seed, tokenizer=tokenizer)
    return out


def rand_triples(positions: dict[str, dict[str, Any]], n: int = Z4_N_RAND, seed: int = Z4_SEED) -> list[tuple[str, str, int]]:
    """``n`` (pair, source, position) triples drawn by seed without replacement from every pair's selected positions."""
    import numpy as np

    allt = sorted((pid, src, int(i)) for pid, P in positions.items() for src in ("A", "B") for i in P["positions"])
    if n >= len(allt):
        return allt
    rng = np.random.default_rng(rand_triples_seed(seed))
    idx = rng.choice(len(allt), size=n, replace=False)
    return [allt[int(i)] for i in sorted(idx)]


# ------------------------------------------------------------------ dependent-stage draws (deviation 2026-10-09)
def restore_draw(pairs: list[dict[str, Any]], positions: dict[str, dict[str, Any]], top: dict[str, list[int]], *,
                 n_per_family: int = Z4_N_RESTORE_PER_FAMILY, seed: int = Z4_SEED) -> list[tuple[str, str, int]]:
    """The restore determinism check: per family ``n_per_family`` (pair, source, position) triples drawn without
    replacement by ``restore_seed(family, seed)`` from the family's all_except table (every pair × source × top
    position inside the render). Sorted; fewer if the table is smaller."""
    import numpy as np

    out: list[tuple[str, str, int]] = []
    for fam in sorted({p["family"] for p in pairs}):
        tab = sorted((p["pair_id"], src, int(i)) for p in pairs if p["family"] == fam for src in ("A", "B")
                     for i in (top.get(fam) or []) if int(i) < int(positions[p["pair_id"]]["n_tokens"]))
        if n_per_family >= len(tab):
            out += tab
            continue
        rng = np.random.default_rng(restore_seed(fam, seed))
        idx = rng.choice(len(tab), size=n_per_family, replace=False)
        out += [tab[int(k)] for k in sorted(idx)]
    return sorted(out)


def pair2_draw(pairs: list[dict[str, Any]], positions: dict[str, dict[str, Any]], top: dict[str, list[int]], *,
               n_items: int = Z4_PAIR2_N_ITEMS, seed: int = Z4_SEED) -> list[tuple[str, str, int, int]]:
    """The two-position arm's (pair, source, i, j) items. Per family: every C(K, 2) pair (i < j) of the family's top-K
    positions; ONE permutation of the family's pairs by ``pair2_seed(family, seed)``; for each position pair the first
    ``n_items`` eligible pairs in that order (eligible = both positions inside the render), the first n//2 from source A,
    the rest from source B (balanced 5/5 at n 10). With fewer than ``n_items`` eligible pairs
    both sources of each eligible pair are used (A, B alternating, truncated to ``n_items``). Because the permutation is
    shared, position pairs that every pair can host get the same items (paired across position pairs)."""
    import itertools

    import numpy as np

    out: list[tuple[str, str, int, int]] = []
    for fam in sorted({p["family"] for p in pairs}):
        tp = sorted({int(i) for i in (top.get(fam) or [])})
        if len(tp) < 2:
            continue
        fam_pairs = sorted(p["pair_id"] for p in pairs if p["family"] == fam)
        rng = np.random.default_rng(pair2_seed(fam, seed))
        order = [fam_pairs[int(k)] for k in rng.permutation(len(fam_pairs))]
        for i, j in itertools.combinations(tp, 2):
            elig = [pid for pid in order if j < int(positions[pid]["n_tokens"])]
            if len(elig) >= n_items:
                chosen = [(pid, "A" if k < n_items // 2 else "B") for k, pid in enumerate(elig[:n_items])]
            else:
                chosen = [(pid, src) for pid in elig for src in ("A", "B")][:n_items]
            out += [(pid, src, i, j) for pid, src in chosen]
    return out


def dependent_draws(pairs: list[dict[str, Any]], positions: dict[str, dict[str, Any]], top: dict[str, list[int]], *, seed: int = Z4_SEED,
                    n_restore: int = Z4_N_RESTORE_PER_FAMILY, n_pair2: int = Z4_PAIR2_N_ITEMS) -> dict[str, Any]:
    return {"restore": restore_draw(pairs, positions, top, n_per_family=n_restore, seed=seed),
            "pair2": pair2_draw(pairs, positions, top, n_items=n_pair2, seed=seed)}


# ------------------------------------------------------------------ condition table
def z4_condition_table(pair_id: str, family: str, P: dict[str, Any], *, alphas: tuple[float, ...] = Z4_SINGLE_ALPHAS,
                       reuse_alphas: tuple[float, ...] = Z4_REUSE_ALPHAS, top_positions: list[int] | tuple[int, ...] | None = None,
                       rand: list[tuple[str, str, int]] | tuple[tuple[str, str, int], ...] = (), stage: str = "all",
                       restore: list[tuple[str, str, int]] | tuple[tuple[str, str, int], ...] | set | None = None,
                       pair2: list[tuple[str, str, int, int]] | tuple[tuple[str, str, int, int], ...] = (),
                       pair2_alphas: tuple[float, ...] = Z4_PAIR2_ALPHAS) -> list[dict[str, Any]]:
    """The tensor-free table of one pair (both sources). ``stage`` single | dependent | all selects the arms; reused
    Y2 rows are listed in every stage (never decoded). ``top_positions`` are the family's top-K positions (those
    ≥ n_tokens are dropped for this pair); ``rand`` the global rand_single triples; ``restore`` the drawn
    (pair, source, position) restore triples (None or empty: no restore entries — deviation 2026-10-09 (1));
    ``pair2`` the drawn (pair, source, i, j) two-position items, each decoded at every α in ``pair2_alphas``."""
    T = int(P["n_tokens"])
    restore_set = {(str(a), str(b), int(c)) for a, b, c in (restore or ())}
    out: list[dict[str, Any]] = []

    def add(**e: Any) -> None:
        e.setdefault("position", None)
        e.setdefault("reused", False)
        e.setdefault("reused_key", None)
        if "role" not in e:  # (lazy: pair2 entries pass their combined role; their position "i-j" is not an int)
            e["role"] = None if e["position"] is None else P["roles"].get(int(e["position"]), "unsampled")
        e["site"] = Z4_SITE
        e["edit_layer"] = Z4_EDIT_LAYER
        e["family"] = family
        e["pair_id"] = pair_id
        e["n_tokens"] = T
        e["positions_kind"] = Z4_POSITIONS_KIND[e["condition"]]
        e["stage"] = Z4_STAGE_OF.get(e["condition"], "reused")
        e["key"] = z4_entry_key(e)
        out.append(e)

    for src in ("A", "B"):
        if stage in ("single", "all"):
            for i in P["positions"]:
                for a in alphas:
                    add(source=src, condition="single", alpha=float(a), position=int(i))
            for pid, s, i in rand:
                if pid == pair_id and s == src:
                    add(source=src, condition="rand_single", alpha=1.0, position=int(i))
        for a in reuse_alphas:
            for cond in Z4_REUSED_CONDITIONS:
                add(source=src, condition=cond, alpha=float(a), reused=True, reused_key=f"{pair_id}|{src}|{E.Y2_SITE}|{cond}|{float(a)}|None")
        if stage in ("dependent", "all") and top_positions:
            for i in top_positions:
                if int(i) < T:
                    add(source=src, condition="all_except", alpha=Z4_DEPENDENT_ALPHA, position=int(i))
                    if (pair_id, src, int(i)) in restore_set:
                        add(source=src, condition="restore", alpha=Z4_DEPENDENT_ALPHA, position=int(i))
        if stage in ("dependent", "all"):
            for pid, s, i, j in pair2:
                if pid == pair_id and s == src and max(int(i), int(j)) < T:
                    i, j = sorted((int(i), int(j)))
                    role = "+".join(P["roles"].get(k, "unsampled") for k in (i, j))
                    for a in pair2_alphas:
                        add(source=src, condition="pair2", alpha=float(a), position=pair_label(i, j), pair_positions=[i, j], role=role)
    return out


def build_tables(pairs: list[dict[str, Any]], positions: dict[str, dict[str, Any]], *, stage: str = "all", top: dict[str, list[int]] | None = None,
                 rand: list[tuple[str, str, int]] | None = None, alphas: tuple[float, ...] = Z4_SINGLE_ALPHAS,
                 restore: list[tuple[str, str, int]] | None = None, pair2: list[tuple[str, str, int, int]] | None = None) -> dict[str, list[dict[str, Any]]]:
    rand = rand if rand is not None else []
    top = top or {}
    return {p["pair_id"]: z4_condition_table(p["pair_id"], p["family"], positions[p["pair_id"]], alphas=alphas, top_positions=top.get(p["family"]),
                                             rand=rand, stage=stage, restore=restore, pair2=pair2 or ()) for p in pairs}


def planned_decodes(tables: dict[str, list[dict[str, Any]]], *, dependent_upper: int | None = None,
                    conditions: tuple[str, ...] = Z4_NEW_CONDITIONS) -> dict[str, int]:
    """Decode counts implied by the tables (reused rows excluded). ``dependent_upper`` adds an upper bound for the
    dependent arms when they are not in the tables yet (top-K unknown before the single decodes). ``conditions``
    defaults to the single-stage printout's list; the dependent stage passes Z4_DECODED_CONDITIONS (adds pair2)."""
    ents = [e for t in tables.values() for e in t]
    out = {c: sum(1 for e in ents if e["condition"] == c and not e["reused"]) for c in conditions}
    out["reused"] = sum(1 for e in ents if e["reused"])
    out["in_tables"] = sum(out[c] for c in conditions)
    out["dependent_upper_bound"] = int(dependent_upper or 0)
    out["total_planned"] = out["in_tables"] + out["dependent_upper_bound"]
    return out


def dependent_upper_bound(pairs: list[dict[str, Any]], k: int = Z4_TOP_K) -> int:
    """all_except + restore for K positions × 2 sources per pair — the PRE-deviation bound, used only by the single-stage
    printout (kept so that printout is unchanged); the dependent stage reports the exact full-run table instead."""
    return 2 * 2 * k * len(pairs)


def full_run_plan(pairs: list[dict[str, Any]], positions: dict[str, dict[str, Any]], *, top: dict[str, list[int]], rand: list[tuple[str, str, int]],
                  draws: dict[str, Any], alphas: tuple[float, ...] = Z4_SINGLE_ALPHAS) -> dict[str, int]:
    """Exact decode table of the whole Z4 run (single + rand_single + all_except + pair2 + restore), from tensor-free tables."""
    tabs = build_tables(pairs, positions, stage="all", top=top, rand=rand, alphas=alphas, restore=draws["restore"], pair2=draws["pair2"])
    return planned_decodes(tabs, conditions=Z4_DECODED_CONDITIONS)


def check_cap(plan: dict[str, int], cap: int = Z4_DECODE_CAP) -> None:
    if plan["total_planned"] > cap:
        raise SystemExit(f"refusing to run: {plan['total_planned']} planned decodes exceed the cap {cap} ({plan})")


# ------------------------------------------------------------------ top-K per family from the single rows
def top_positions_by_family(rows: list[dict[str, Any]], *, k: int = Z4_TOP_K, alpha: float = Z4_DEPENDENT_ALPHA, min_n: int = Z4_TOP_MIN_N) -> dict[str, Any]:
    """Seed-free rule: per family, rank the single positions at ``alpha`` by flip rate (flipped_to_other ∧ coherent),
    ties by position index; positions with fewer than ``min_n`` entries are not ranked unless fewer than ``k`` qualify.
    Returns ``{family: {"top": [...], "table": [{position, k, n, rate}], "min_n_applied": bool}}``."""
    acc: dict[str, dict[int, list[int]]] = {}
    for r in rows:
        if r.get("condition") != "single" or float(r["alpha"]) != float(alpha):
            continue
        acc.setdefault(r["family"], {}).setdefault(int(r["position"]), []).append(int(bool(r["flipped_to_other"]) and bool(r.get("coherent", True))))
    out: dict[str, Any] = {}
    for fam, byp in acc.items():
        tab = [{"position": p, "k": sum(v), "n": len(v), "rate": sum(v) / len(v)} for p, v in sorted(byp.items())]
        ok = [t for t in tab if t["n"] >= min_n]
        applied = len(ok) >= k
        ranked = sorted(ok if applied else tab, key=lambda t: (-t["rate"], t["position"]))
        out[fam] = {"top": [t["position"] for t in ranked[:k]], "table": tab, "min_n_applied": applied, "min_n": min_n, "alpha": alpha, "k": k}
    return out


# ------------------------------------------------------------------ entry vectors
def z4_entry_vectors(e: dict[str, Any], HA: dict[int, Any], HB: dict[int, Any], *, layer: int | None = None) -> dict[str, Any]:
    """``positions`` and ``base``/``delta`` (fp32 ``[P, d]``; edited state = base + alpha * delta) of one Z4 entry from the
    full captures ``HA/HB = {layer: [T, d]}``. In the A→B frame (toward = +1 from A, −1 from B):
    single      P = {i}, delta = toward·Δ(i)
    all_except  P = all \\ {i}, delta = toward·Δ(P)
    restore     P = all, base = the OTHER state, delta = 0 except delta(i) = −toward·Δ(i)  (α 1: full swap with i restored)
    rand_single P = {i}, delta = ‖Δ(i)‖ · r, r a seeded random unit direction.
    pair2       P = {i, j} (position "i-j"), delta = toward·Δ(P)  (see ``pair2_entry_vectors``)."""
    import torch

    if e["condition"] == "pair2":
        return pair2_entry_vectors(e, HA, HB, layer=layer)
    layer = Z4_EDIT_LAYER if layer is None else layer
    hA, hB = HA[layer].float(), HB[layer].float()
    if hA.shape != hB.shape:
        raise ValueError(f"{e['pair_id']}: A and B captures differ in shape {tuple(hA.shape)} vs {tuple(hB.shape)}")
    T, d = int(hA.shape[0]), int(hA.shape[1])
    toward = 1.0 if e["source"] == "A" else -1.0
    h = hA if e["source"] == "A" else hB
    other = hB if e["source"] == "A" else hA
    Dfull = hB - hA
    norms = Dfull.norm(dim=1)
    i = int(e["position"])
    if not 0 <= i < T:
        raise ValueError(f"{e['pair_id']}: position {i} outside the render (T={T})")
    cond = e["condition"]
    cos = 1.0
    rseed = None
    if cond == "single":
        pos = [i]
        base = h[pos].clone()
        delta = toward * Dfull[pos]
    elif cond == "all_except":
        pos = [j for j in range(T) if j != i]
        base = h[pos].clone()
        delta = toward * Dfull[pos]
    elif cond == "restore":
        pos = list(range(T))
        base = other.clone()
        delta = torch.zeros_like(base)
        delta[i] = -toward * Dfull[i]
    elif cond == "rand_single":
        pos = [i]
        base = h[pos].clone()
        rseed = rand_dir_seed(e["pair_id"], e["source"], i)
        g = torch.Generator().manual_seed(rseed)
        r = torch.randn(d, generator=g)
        r = r / r.norm().clamp_min(1e-9)
        delta = (norms[i] * r)[None, :]
        cos = float(r @ (Dfull[i] / norms[i].clamp_min(1e-9)))
    else:
        raise ValueError(f"unknown condition {cond}")
    alpha = float(e["alpha"])
    v = base + alpha * delta
    last_edited = pos[-1] == T - 1
    return {"positions": pos, "n_positions": len(pos), "base": base, "delta": delta, "dose_abs": alpha * float(delta.norm()),
            "delta_pos": float(norms[i]), "delta_last": float(norms[T - 1]), "delta_total": float(norms.norm()), "delta_edited": float(delta.norm()),
            "input_norm_last": float(v[-1].norm()) if last_edited else float(h[T - 1].norm()), "input_norm_natural_last": float(h[T - 1].norm()),
            "input_norm_pos": float(v[pos.index(i)].norm()) if i in pos else float(h[i].norm()), "last_edited": last_edited, "cos_to_u_pos": cos, "rand_seed": rseed}


def pair2_entry_vectors(e: dict[str, Any], HA: dict[int, Any], HB: dict[int, Any], *, layer: int | None = None) -> dict[str, Any]:
    """The two-position arm: P = {i, j}, base = this state's rows, delta = toward·Δ(P) (α 1 from A lands on B at both
    positions). ``delta_pos`` / ``input_norm_pos`` are Frobenius norms over the two rows."""
    layer = Z4_EDIT_LAYER if layer is None else layer
    hA, hB = HA[layer].float(), HB[layer].float()
    if hA.shape != hB.shape:
        raise ValueError(f"{e['pair_id']}: A and B captures differ in shape {tuple(hA.shape)} vs {tuple(hB.shape)}")
    T = int(hA.shape[0])
    i, j = parse_pair_label(e["position"])
    if not (0 <= i < j < T):
        raise ValueError(f"{e['pair_id']}: pair2 positions {e['position']} invalid for the render (T={T}; need 0 ≤ i < j < T)")
    toward = 1.0 if e["source"] == "A" else -1.0
    h = hA if e["source"] == "A" else hB
    Dfull = hB - hA
    norms = Dfull.norm(dim=1)
    pos = [i, j]
    base = h[pos].clone()
    delta = toward * Dfull[pos]
    alpha = float(e["alpha"])
    v = base + alpha * delta
    last_edited = j == T - 1
    return {"positions": pos, "n_positions": 2, "base": base, "delta": delta, "dose_abs": alpha * float(delta.norm()),
            "delta_pos": float(Dfull[pos].norm()), "delta_last": float(norms[T - 1]), "delta_total": float(norms.norm()), "delta_edited": float(delta.norm()),
            "input_norm_last": float(v[-1].norm()) if last_edited else float(h[T - 1].norm()), "input_norm_natural_last": float(h[T - 1].norm()),
            "input_norm_pos": float(v.norm()), "last_edited": last_edited, "cos_to_u_pos": 1.0, "rand_seed": None}


# ------------------------------------------------------------------ row-wise batched decode (per-row position sets)
def generate_with_rowwise_positions(target: M.Target, ids: list[int], layer: int, row_positions: list[list[int]], row_vectors: list[Any], *,
                                    read_layer: int | None = None, max_new_tokens: int = 8, cand_first_tokens: tuple[int, int] | None = None) -> list[dict[str, Any]]:
    """``E.generate_with_interpolated_batch`` generalised to a DIFFERENT position set per row: row b has ``blocks[layer]``'s
    output at ``row_positions[b]`` replaced by ``row_vectors[b]`` (fp32 ``[P_b, d]``) during the prefill only. Same read
    hook (block ``read_layer`` output at the last prefill position) and the same first-step ``lo_model``."""
    import torch

    read_layer = E.X2_READ_LAYER if read_layer is None else read_layer
    model, tok = target.model, target.tokenizer
    dev = next(model.parameters()).device
    blks = M.blocks(model)
    T = len(ids)
    B = len(row_positions)
    if B == 0 or len(row_vectors) != B:
        raise ValueError("row_positions and row_vectors must be non-empty and of equal length")
    P = [torch.tensor([int(p) % T for p in ps], dtype=torch.long) for ps in row_positions]
    V = [torch.as_tensor(v).float() for v in row_vectors]
    for b in range(B):
        if V[b].ndim == 1:
            V[b] = V[b][None]
        if V[b].shape[0] != len(P[b]):
            raise ValueError(f"row {b}: {V[b].shape[0]} vectors for {len(P[b])} positions")
    pmax = max(int(p.max()) for p in P)
    state: dict[str, Any] = {"n_edits": 0, "n_reads": 0, "read": None}

    def edit_hook(_mod, _inp, out):
        h = out[0] if isinstance(out, tuple) else out
        if h.shape[1] <= 1 or h.shape[1] <= pmax:
            return out
        state["n_edits"] += 1
        for b in range(B):
            h[b, P[b].to(h.device), :] = V[b].to(h.device, h.dtype)
        return out

    def read_hook(_mod, _inp, out):
        h = out[0] if isinstance(out, tuple) else out
        if h.shape[1] < T:
            return out
        state["n_reads"] += 1
        state["read"] = h[:, T - 1, :].detach().float().cpu().clone()
        return out

    handles = [blks[layer].register_forward_hook(edit_hook), blks[read_layer].register_forward_hook(read_hook)]
    kw = G._gen_kwargs(None, max_new_tokens)
    kw.update(pad_token_id=G.pad_id(tok), num_return_sequences=1, return_dict_in_generate=True)
    eos = G.eos_ids(tok, model)
    x = torch.tensor([list(ids)] * B, device=dev)
    try:
        with timed_call() as st, torch.no_grad(), M.disable_adapter_ctx(model):
            try:
                out = model.generate(x, attention_mask=torch.ones_like(x), output_logits=True, **kw)
                first = out.logits[0]
            except TypeError:
                out = model.generate(x, attention_mask=torch.ones_like(x), output_scores=True, **kw)
                first = out.scores[0]
    finally:
        for hd in handles:
            hd.remove()
    if state["n_edits"] < 1:
        raise RuntimeError("edit hook did not fire during the prefill")
    if state["n_reads"] != 1 or state["read"] is None or state["read"].shape[0] != B:
        raise RuntimeError(f"read hook fired {state['n_reads']} times (expected once, batch {B})")
    lp = torch.log_softmax(first.float(), dim=-1).cpu()
    seqs = out.sequences
    rows: list[dict[str, Any]] = []
    for b in range(B):
        new = seqs[b, T:].tolist()
        cut, reason = G._finish(new, max_new_tokens, eos)
        row: dict[str, Any] = {"answer_text": tok.decode(cut, skip_special_tokens=True), "n_new_tokens": len(cut), "finish_reason": reason, "new_ids": cut,
                               "read_vec": state["read"][b].clone(), "lo_model": None, "lp_first_A": None, "lp_first_B": None,
                               "first_token_id": (cut[0] if cut else None), "top1_id": int(lp[b].argmax()), "n_tokens": T, "layer": layer, "read_layer": read_layer,
                               "positions": [int(p) for p in P[b].tolist()], "n_hook_edits": state["n_edits"], "n_read_hits": state["n_reads"], "batch_size": B,
                               "wall_s": st.wall_s, "wall_s_batch": st.wall_s, "peak_mem_gb": st.peak_mem_gb}
        if cand_first_tokens is not None:
            ia, ib = int(cand_first_tokens[0]), int(cand_first_tokens[1])
            row["lp_first_A"], row["lp_first_B"] = float(lp[b, ia]), float(lp[b, ib])
            row["lo_model"] = row["lp_first_B"] - row["lp_first_A"]
        rows.append(row)
    return rows


# ------------------------------------------------------------------ behaviour (+ read vectors)
def collect_behaviour(target: M.Target, pairs: list[dict[str, Any]], tables: dict[str, list[dict[str, Any]]], *, beh_path: Path = BEH_PATH,
                      readvec_dir: Path | None = None, full_dir: Path | None = None, ledger_path: Path | None = None, log_path: Path | None = LOG,
                      max_new_tokens: int = BEHAVIOUR_TOKENS, batch: int = DEFAULT_BATCH, items_file: Path | None = None, read_layer: int | None = None,
                      edit_layer: int | None = None, y2_beh_path: Path | None = Y2_BEH_PATH) -> int:
    """Every NEW entry of every pair, batched row-wise over entries sharing (pair, source) (each row its own position
    set). Reused Y2 entries are skipped (counted; checked to exist in the Y2 file when present). Resumable."""
    import torch

    from projects.g_agreement.core import scoring as SC

    readvec_dir = readvec_dir or READVEC_DIR
    read_layer = E.X2_READ_LAYER if read_layer is None else read_layer
    edit_layer = Z4_EDIT_LAYER if edit_layer is None else edit_layer
    readvec_dir.mkdir(parents=True, exist_ok=True)
    done = {k for k in done_ids(beh_path, key="key") if X.readvec_path(k, readvec_dir).exists()}
    y2_keys = done_ids(y2_beh_path, key="key") if y2_beh_path is not None and Path(y2_beh_path).exists() else None
    ledgers = {c: StepLedger(step=f"z4_behaviour_{c}", module=MODULE, extra={"max_new_tokens": max_new_tokens, "batch": batch}) for c in Z4_DECODED_CONDITIONS}
    extra = X._row_extra(items_file)
    dt = getattr(torch, SAVE_DTYPE)
    n, n_reused, n_reused_missing = 0, 0, 0
    for pair in pairs:
        table = tables[pair["pair_id"]]
        reused = [e for e in table if e["reused"]]
        n_reused += len(reused)
        if y2_keys is not None:
            n_reused_missing += sum(1 for e in reused if e["reused_key"] not in y2_keys)
        todo = [e for e in table if not e["reused"] and e["key"] not in done]
        if not todo:
            continue
        H = {v: X.load_full(pair[v]["item_id"], full_dir) for v in ("A", "B")}
        HA, HB = H["A"]["layers"], H["B"]["layers"]
        if H["A"]["n_tokens"] != H["B"]["n_tokens"]:
            raise RuntimeError(f"{pair['pair_id']}: unequal cached lengths")
        for src in ("A", "B"):
            ents = [e for e in todo if e["source"] == src]
            if not ents:
                continue
            it = pair[src]
            ids = H[src]["ids"]
            cand_A, cand_B = it["primary"]["answer"], X.other_candidate(it)
            ft = E.first_token_candidates(target.tokenizer, cand_A, cand_B)
            cft = None if ft["unscorable"] else (ft["first_A"], ft["first_B"])
            for s in range(0, len(ents), batch):
                chunk = ents[s: s + batch]
                vecs = [z4_entry_vectors(e, HA, HB, layer=edit_layer) for e in chunk]
                rows = generate_with_rowwise_positions(target, ids, edit_layer, [v["positions"] for v in vecs],
                                                       [v["base"] + float(e["alpha"]) * v["delta"] for e, v in zip(chunk, vecs)],
                                                       read_layer=read_layer, max_new_tokens=max_new_tokens, cand_first_tokens=cft)
                for e, v, r in zip(chunk, vecs, rows):
                    parsed, evidence = SC.extract_target_answer(r["answer_text"], it)
                    torch.save(r["read_vec"].to(dt), X.readvec_path(e["key"], readvec_dir))
                    row = {"key": e["key"], "pair_id": pair["pair_id"], "family": pair["family"], "source": src, "state_item_id": it["item_id"],
                           "site": e["site"], "edit_layer": edit_layer, "stage": e["stage"], "condition": e["condition"], "position": e["position"],
                           "role": e["role"], "rel_position": (None if e["condition"] == "pair2" else int(e["position"]) - r["n_tokens"]), "positions_kind": e["positions_kind"],
                           "n_positions": v["n_positions"], "positions": v["positions"] if v["n_positions"] <= 2 else None, "n_tokens": r["n_tokens"],
                           "alpha": e["alpha"], "reused": False, "rand_seed": v["rand_seed"], "cos_to_u_pos": v["cos_to_u_pos"],
                           "cand_A": cand_A, "cand_B": cand_B, "answer_text": r["answer_text"], "parsed": parsed, "parse_evidence": evidence,
                           "flipped_to_other": parsed == cand_B, "kept_original": parsed == cand_A, "coherent": parsed in (cand_A, cand_B),
                           "lo_model": r["lo_model"], "lp_first_A": r["lp_first_A"], "lp_first_B": r["lp_first_B"], "lo_model_unscorable": ft["unscorable"],
                           "lo_model_form": ft["form"], "first_A": ft["first_A"], "first_B": ft["first_B"], "first_token_id": r["first_token_id"], "top1_id": r["top1_id"],
                           "dose_abs": v["dose_abs"], "delta_pos": v["delta_pos"], "delta_last": v["delta_last"], "delta_total": v["delta_total"],
                           "delta_edited": v["delta_edited"], "input_norm_last": v["input_norm_last"], "input_norm_pos": v["input_norm_pos"], "last_edited": v["last_edited"],
                           "n_new_tokens": r["n_new_tokens"], "finish_reason": r["finish_reason"], "read_layer": read_layer, "n_hook_edits": r["n_hook_edits"],
                           "batch_size": r["batch_size"], "wall_s": r["wall_s"] / max(1, r["batch_size"]), "wall_s_batch": r["wall_s_batch"],
                           "peak_mem_gb": r["peak_mem_gb"], "prompt_ids_sha256": H[src]["prompt_ids_sha256"], "readvec_dtype": SAVE_DTYPE,
                           "created_at": now_iso(), **extra}
                    if e["condition"] == "pair2":  # pair2-only field (single/rand/all_except/restore rows keep their schema)
                        row["pair_positions"] = list(e["pair_positions"])
                    append_jsonl(beh_path, row)
                    n += 1
                for c in {e["condition"] for e in chunk}:
                    sub = [r for e, r in zip(chunk, rows) if e["condition"] == c]
                    ledgers[c].add(len(ids) * len(sub), sum(r["n_new_tokens"] for r in sub), rows[0]["wall_s_batch"] * len(sub) / len(chunk), rows[0]["peak_mem_gb"])
        print(f"[z4/behaviour] {pair['pair_id']}: {len(todo)} entries decoded ({len(reused)} Y2 rows reused)", flush=True)
    for c, ld in ledgers.items():
        r = ld.flush(ledger_path)
        if log_path and r:
            log_line(log_path, f"behaviour {c}: {r}")
    if log_path:
        log_line(log_path, f"behaviour: {n} new entries; {n_reused} name_only/name_removed entries reused from Y2"
                 + (f" ({n_reused_missing} MISSING in {y2_beh_path})" if y2_keys is not None else " (Y2 behaviour file not checked)"))
    return n


# ------------------------------------------------------------------ reader LO on the read vectors
LO_COPY_KEYS = ("pair_id", "family", "source", "state_item_id", "site", "edit_layer", "stage", "condition", "position", "role", "rel_position",
                "positions_kind", "n_positions", "n_tokens", "alpha", "cand_A", "cand_B", "dose_abs", "delta_pos", "lo_model", "flipped_to_other", "coherent")


def collect_lo(reader: Any, *, beh_path: Path = BEH_PATH, lo_path: Path = LO_PATH, readvec_dir: Path | None = None, ledger_path: Path | None = None,
               log_path: Path | None = LOG, batch: int = 32, items_file: Path | None = None, pair_ids: set[str] | None = None) -> int:
    """Native LO of ``reader`` on every Z4 behaviour row's read vector (block 42); ``lo_toward_other = score(B) − score(A)``."""
    import torch

    readvec_dir = readvec_dir or READVEC_DIR
    done = done_ids(lo_path, key="key")
    beh = [r for r in read_jsonl(beh_path) if pair_ids is None or r["pair_id"] in pair_ids]
    todo = [r for r in beh if f"{reader.name}|{r['key']}" not in done and X.readvec_path(r["key"], readvec_dir).exists()]
    ledger = StepLedger(step=f"z4_lo_{reader.name}", module=MODULE, extra={"batch": batch})
    extra = X._row_extra(items_file)
    n = 0
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for r in todo:
        by_fam.setdefault(r["family"], []).append(r)
    for fam, rows_f in by_fam.items():
        for s in range(0, len(rows_f), batch):
            chunk = rows_f[s: s + batch]
            Hm = torch.stack([X.load_readvec(r["key"], readvec_dir) for r in chunk])
            with timed_call() as st:
                res = LO.score_lo(reader, Hm, [(r["cand_A"], r["cand_B"]) for r in chunk], fam, batch=batch)
            for b, q in zip(chunk, res):
                row = {"key": f"{reader.name}|{b['key']}", "entry_key": b["key"], "reader": reader.name, **{k: b.get(k) for k in LO_COPY_KEYS},
                       "lo_own": q["lo"], "lo_toward_other": (None if q["lo"] is None else -q["lo"]), "lp_A": q["lp_A"], "lp_B": q["lp_B"],
                       "templates": q["templates"], "unscorable": q["unscorable"], "wall_s_chunk": st.wall_s, "chunk_size": len(chunk), "created_at": now_iso(), **extra}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason"):
                    if k in q:
                        row[k] = q[k]
                append_jsonl(lo_path, row)
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[z4/lo/{reader.name}] {fam}: {len(rows_f)} vectors scored", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"lo {reader.name}: {r}")
    return n


# ------------------------------------------------------------------ main
def positions_summary(positions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    n = [len(P["positions"]) for P in positions.values()]
    return {"pairs": len(positions), "positions_total": sum(n), "positions_min": min(n) if n else 0, "positions_max": max(n) if n else 0,
            "n_tokens_min": min(P["n_tokens"] for P in positions.values()) if positions else 0, "n_tokens_max": max(P["n_tokens"] for P in positions.values()) if positions else 0,
            "roles": {r: sum(1 for P in positions.values() for v in P["roles"].values() if v == r) for r in ROLES}}


def run_stage(target: M.Target, stage: str, usable: list[dict[str, Any]], positions: dict[str, dict[str, Any]], a: argparse.Namespace, items_file: Path) -> dict[str, Any]:
    """One collection stage (single | dependent) on a loaded target: tables, plan + cap, decodes."""
    if stage == "dependent":
        return run_dependent_stage(target, usable, positions, a, items_file)
    rand = rand_triples(positions, a.n_rand) if stage == "single" else []
    top = None
    tables = build_tables(usable, positions, stage=stage, top=top, rand=rand, alphas=tuple(a.alphas))
    plan = planned_decodes(tables, dependent_upper=dependent_upper_bound(usable, a.top_k) if stage == "single" else 0)
    print(f"[z4] stage {stage}: planned decodes {plan} (cap {a.cap})", flush=True)
    log_line(LOG, f"stage {stage}: planned decodes {plan}; cap {a.cap}")
    check_cap(plan, a.cap)
    if stage == "single":
        log_line(LOG, f"rand_single triples (seed {Z4_SEED}): {len(rand)}")
    if not a.skip_behaviour:
        n = collect_behaviour(target, usable, tables, max_new_tokens=a.max_new_tokens, batch=a.batch, items_file=items_file)
        log_line(LOG, f"stage {stage}: {n} new entries")
    return {"plan": plan, "top": top, "rand": rand}


def plan_dependent(usable: list[dict[str, Any]], positions: dict[str, dict[str, Any]], single_rows: list[dict[str, Any]], *, top_k: int = Z4_TOP_K,
                   n_rand: int = Z4_N_RAND, alphas: tuple[float, ...] = Z4_SINGLE_ALPHAS) -> dict[str, Any]:
    """Tensor-free plan of the dependent stage (deviation 2026-10-09): top-K per family from the single rows, the restore
    and pair2 draws, the dependent tables and the exact FULL-run decode table (single + rand_single re-derived from the
    same seeds). Raises SystemExit if there are no single rows."""
    topinfo = top_positions_by_family(single_rows, k=top_k)
    if not topinfo:
        raise SystemExit("no single-position rows yet: run --stage single first")
    top = {f: v["top"] for f, v in topinfo.items()}
    draws = dependent_draws(usable, positions, top)
    tables = build_tables(usable, positions, stage="dependent", top=top, alphas=alphas, restore=draws["restore"], pair2=draws["pair2"])
    stage_plan = planned_decodes(tables, conditions=Z4_DECODED_CONDITIONS)
    full = full_run_plan(usable, positions, top=top, rand=rand_triples(positions, n_rand), draws=draws, alphas=alphas)
    return {"topinfo": topinfo, "top": top, "draws": draws, "tables": tables, "stage_plan": stage_plan, "full_plan": full}


def run_dependent_stage(target: M.Target, usable: list[dict[str, Any]], positions: dict[str, dict[str, Any]], a: argparse.Namespace,
                        items_file: Path) -> dict[str, Any]:
    """all_except (top-K, α 1) + pair2 (C(K,2) pairs × Z4_PAIR2_ALPHAS × Z4_PAIR2_N_ITEMS items per family) + restore (determinism
    check, Z4_N_RESTORE_PER_FAMILY per family). The cap is checked on the FULL-run table."""
    rows = [r for r in read_jsonl(BEH_PATH) if r["pair_id"] in {p["pair_id"] for p in usable}]
    pl = plan_dependent(usable, positions, rows, top_k=a.top_k, n_rand=a.n_rand, alphas=tuple(a.alphas))
    topinfo, top, draws, tables = pl["topinfo"], pl["top"], pl["draws"], pl["tables"]
    log_line(LOG, f"top-{a.top_k} single positions per family (α {Z4_DEPENDENT_ALPHA}, min_n {Z4_TOP_MIN_N}): "
                  + json.dumps({f: {"top": v["top"], "rates": [(t['position'], t['k'], t['n']) for t in sorted(v['table'], key=lambda t: (-t['rate'], t['position']))[:a.top_k]], "min_n_applied": v["min_n_applied"]} for f, v in topinfo.items()}))
    print(f"[z4] top positions: {top}", flush=True)
    log_line(LOG, f"restore determinism draw (seed {Z4_SEED}, {Z4_N_RESTORE_PER_FAMILY}/family): {json.dumps(draws['restore'])}")
    log_line(LOG, f"pair2 draw (seed {Z4_SEED}, {Z4_PAIR2_N_ITEMS} items per family × position pair, α {list(Z4_PAIR2_ALPHAS)}): {json.dumps(draws['pair2'])}")
    full = pl["full_plan"]
    print(f"[z4] stage dependent: planned decodes this stage {pl['stage_plan']}", flush=True)
    print("[z4] FULL Z4 run planned decodes (deviation 2026-10-09):\n" + format_plan_table(full) + f"\n  cap {a.cap}", flush=True)
    log_line(LOG, f"stage dependent: planned decodes this stage {pl['stage_plan']}; FULL run {full}; cap {a.cap}")
    check_cap(full, a.cap)
    if not a.skip_behaviour:
        n = collect_behaviour(target, usable, tables, max_new_tokens=a.max_new_tokens, batch=a.batch, items_file=items_file)
        log_line(LOG, f"stage dependent: {n} new entries")
    return {"plan": full, "stage_plan": pl["stage_plan"], "top": top, "draws": draws, "rand": []}


def format_plan_table(plan: dict[str, int]) -> str:
    lines = [f"  {c:12s} {plan.get(c, 0):6d}" for c in Z4_DECODED_CONDITIONS]
    lines.append(f"  {'total':12s} {plan['total_planned']:6d}   (reused Y2 rows, not decoded: {plan.get('reused', 0)})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--stage", choices=["single", "dependent", "all"], default="all", help="phase A: which arms to decode")
    ap.add_argument("--items-file", default=str(X.ITEMS_X))
    ap.add_argument("--split", default="test")
    ap.add_argument("--n-pairs", type=int, default=X.N_PAIRS_PER_FAMILY, help="pairs per family (X2: 32)")
    ap.add_argument("--limit-pairs", type=int, default=0, help="debug: first N pairs overall")
    ap.add_argument("--alphas", default=",".join(str(x) for x in Z4_SINGLE_ALPHAS), help="single-position doses")
    ap.add_argument("--max-positions", type=int, default=Z4_MAX_POSITIONS)
    ap.add_argument("--top-k", type=int, default=Z4_TOP_K)
    ap.add_argument("--n-rand", type=int, default=Z4_N_RAND)
    ap.add_argument("--cap", type=int, default=Z4_DECODE_CAP)
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="entries per decode batch (same pair/source; row-wise positions)")
    ap.add_argument("--lo-batch", type=int, default=32)
    ap.add_argument("--max-new-tokens", type=int, default=BEHAVIOUR_TOKENS)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--skip-lo", action="store_true")
    ap.add_argument("--skip-behaviour", action="store_true")
    a = ap.parse_args(argv)
    a.alphas = tuple(float(x) for x in a.alphas.split(",") if x.strip())
    items_file = Path(a.items_file)
    fz = X.require_frozen_x(items_file, a.allow_unfrozen or a.split == "dev")
    items = C.load_items(a.split, 0, path=items_file)
    pairs = X.x2_pairs(items, split=a.split, n_pairs=a.n_pairs, limit=a.limit_pairs)
    if not pairs:
        raise SystemExit(f"no {X.FAMILIES} {a.split} pairs in {items_file}")
    Z_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"Z4 phase {a.phase} stage {a.stage}: {len(pairs)} pairs, alphas={a.alphas}, max_positions={a.max_positions}, top_k={a.top_k}, n_rand={a.n_rand}, freeze={fz}", flush=True)
    log_line(LOG, f"phase {a.phase} stage {a.stage}: {len(pairs)} pairs, alphas={a.alphas}, max_positions={a.max_positions}, top_k={a.top_k}, n_rand={a.n_rand}, "
                  f"cap={a.cap}, split={a.split}, items={items_file.name} sha={fz['items_file_sha256'][:12]} frozen={fz['frozen']}")
    if a.phase == "A":
        from projects.g_agreement.g1_agreement.collect import load_target_timed

        target = load_target_timed(MODULE)
        usable, skipped = X.ensure_full_states(target, pairs, log_path=LOG, skipped_path=SKIPPED)  # reuses cache/x/full
        log_line(LOG, f"full captures: {len(usable)} usable pairs, {len(skipped)} skipped (unequal length)")
        positions = build_positions(usable, max_positions=a.max_positions, tokenizer=target.tokenizer)
        POSITIONS_JSON.write_text(json.dumps({"seed": Z4_SEED, "max_positions": a.max_positions, "summary": positions_summary(positions), "pairs": positions}, indent=1))
        log_line(LOG, f"positions (seed {Z4_SEED}, ≤ {a.max_positions}/prompt): {positions_summary(positions)}")
        stages = ["single", "dependent"] if a.stage == "all" else [a.stage]
        for st in stages:
            run_stage(target, st, usable, positions, a, items_file)
        if not a.skip_lo:
            pid = {p["pair_id"] for p in usable}
            jl = R.JLensReader().bind(target)
            collect_lo(jl, batch=a.lo_batch, items_file=items_file, pair_ids=pid)
            del jl
            ol = R.OLensReader().bind(target)
            log_line(LOG, f"olens adapter={ol.adapter_dir} liveness={ol.liveness}")
            collect_lo(ol, batch=a.lo_batch, items_file=items_file, pair_ids=pid)
        M.unload(target)
    else:
        ledger = StepLedger(step="load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader().bind()
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        log_line(LOG, f"phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}")
        if not a.skip_lo:
            collect_lo(nla, batch=a.lo_batch, items_file=items_file, pair_ids={p["pair_id"] for p in pairs})
        nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
