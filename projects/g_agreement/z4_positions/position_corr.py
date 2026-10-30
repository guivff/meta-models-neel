"""Z4 per-position correlation (BRIEF_Z deviation 2026-10-09 "Z1 reporting"): does a reader's per-position shift track the per-position
flip rate? Reported as its own result with a pair-bootstrap CI. CPU only; zero forward passes; reads the frozen Z4 / X2 artefacts.

Entries: the Z4 single-position arm (condition 'single'), α 0.75 and α 1 analysed SEPARATELY. Per entry (the Z1 definitions, via
z1_intervention.analyze in its Z4 mode): f_r = (lo_r(entry) − lo_r(natural)) / sep_r with the X2 natural row of the same state and the X2
separation (|sep_r| < 1e-4 excluded — the Z1 tie tolerance; per_position.csv used sep_r == 0 only, so its Oracle-lens mapping means carry the
xmap-16 tie at sep 4e-7), Δ_model = lo_model(entry) − lo_model(natural), flip = flipped_to_other ∧ coherent.

Per family (ownership, mapping, pooled) × α × keying × scorer: per position key, the mean score and the flip rate over the same entries (for a
reader: the entries where its f_r is defined; for the model reference row: every entry, score Δ_model); keys with n ≥ MIN_N entries enter;
Spearman and Pearson across keys; 95% CI by pair bootstrap (1,000 resamples, seed 0: pairs resampled with replacement, both per-key
aggregates and the correlation recomputed on each resample, the n ≥ MIN_N filter re-applied).
Keyings:
  absolute    the absolute token index (as results/g_agreement/z4/per_position.csv);
  role        (role, rank within role) from the pair's two renders, so the same key is the same kind of token in every prompt:
              chat_prefix (before the user text; rank = index), diff (the tokens where the A/B renders differ, ranked by order in the
              prompt), statement (other user-text tokens before the question; rank = order), question (from the question's first token
              — positions.json question_first — to the end of the user text; rank = offset from question_first), template (from
              <|im_end|> to the token before the last; rank = offset from <|im_end|>), last (the final token).
Outputs: results/g_agreement/z4/per_position_corr.{csv,md}; one line appended to results/g_agreement/z4/log.md.
Run: PYTHONPATH=. .venv/bin/python projects/g_agreement/z4_positions/position_corr.py --n-boot 1000 --seed 0
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy import stats as sps

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.z1_intervention import analyze as Z  # noqa: E402

CACHE = ROOT / "cache" / "g_agreement"
OUT = ROOT / "results" / "g_agreement" / "z4"
IM_END = 248046          # <|im_end|> in the target's (Qwen3.6) vocabulary
NEWLINE = 198            # "\n": the chat prefix is <|im_start|> user \n
MIN_N = 8                # as z4_positions.analyze (a position enters with n ≥ 8 entries)
ALPHAS = (0.75, 1.0)
FAMILIES = ("ownership", "mapping", "pooled")
KEYINGS = ("absolute", "role")
MODEL = "model"
SCORERS = Z.READERS + (MODEL,)
LABELS = {"olens": "Oracle lens", "nla": "NLA", "jlens": "J-lens", MODEL: "model Δ_model (reference)"}
ROLE_ORDER = ("chat_prefix", "diff", "statement", "question", "template", "last")


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--behaviour", default=str(CACHE / "z" / "z4_behaviour.jsonl"))
    ap.add_argument("--lo", default=str(CACHE / "z" / "z4_lo.jsonl"))
    ap.add_argument("--natural-behaviour", default=str(CACHE / "x" / "x2_behaviour.jsonl"))
    ap.add_argument("--natural-lo", default=str(CACHE / "x" / "x2_lo.jsonl"))
    ap.add_argument("--positions", default=str(OUT / "positions.json"))
    ap.add_argument("--full-dir", default=str(CACHE / "x" / "full"), help="cached renders {item_id}.pt with 'ids' (template boundary)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--min-n", type=int, default=MIN_N)
    ap.add_argument("--no-log", action="store_true", help="do not append to <out>/log.md")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ role-aligned keys
def role_keys(n_tokens: int, diff: Sequence[int], question_first: int, template_start: int, user_start: int) -> Dict[int, Tuple[str, int]]:
    """(role, rank within role) for every position 0..n_tokens−1 of a pair's prompt (see the module docstring). Raises on an inconsistent
    layout (differing tokens outside the user text before the question, question after the template, ...)."""
    diff = sorted(int(i) for i in diff)
    T = int(n_tokens)
    if not diff:
        raise ValueError("no differing positions")
    if not (0 < user_start <= diff[0] and diff[-1] < question_first < template_start < T - 1):
        raise ValueError(f"inconsistent layout: user_start {user_start}, diff {diff}, question_first {question_first}, template_start {template_start}, T {T}")
    out: Dict[int, Tuple[str, int]] = {}
    drank = {p: k for k, p in enumerate(diff)}
    n_stmt = 0
    for i in range(T):
        if i < user_start:
            out[i] = ("chat_prefix", i)
        elif i in drank:
            out[i] = ("diff", drank[i])
        elif i < question_first:
            out[i] = ("statement", n_stmt)
            n_stmt += 1
        elif i < template_start:
            out[i] = ("question", i - question_first)
        elif i < T - 1:
            out[i] = ("template", i - template_start)
        else:
            out[i] = ("last", 0)
    return out


def key_label(k: Tuple[str, int]) -> str:
    return f"{k[0]}:{k[1]}"


def layout_from_ids(ids_a: Sequence[int], ids_b: Sequence[int]) -> Tuple[List[int], int, int]:
    """differing positions, user-text start (after the chat prefix's first newline) and template start (<|im_end|>) of a pair's renders."""
    a, b = [int(x) for x in ids_a], [int(x) for x in ids_b]
    if len(a) != len(b):
        raise ValueError("renders of different length")
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    ie = [i for i, x in enumerate(a) if x == IM_END]
    if len(ie) != 1 or [i for i, x in enumerate(b) if x == IM_END] != ie:
        raise ValueError(f"expected exactly one <|im_end|> at the same index in both renders, got {ie}")
    return diff, a.index(NEWLINE) + 1, ie[0]


def pair_role_maps(positions_json: Mapping[str, dict], full_dir: Path) -> Dict[str, Dict[int, Tuple[str, int]]]:
    import torch

    out = {}
    for pid, v in sorted(positions_json.items()):
        ids = {s: list(torch.load(Path(full_dir) / f"{pid}{s}.pt", map_location="cpu")["ids"]) for s in ("A", "B")}
        diff, user_start, tmpl = layout_from_ids(ids["A"], ids["B"])
        sampled_diff = sorted(int(p) for p, r in v["roles"].items() if r == "diff")
        if sampled_diff != diff or len(ids["A"]) != int(v["n_tokens"]):
            raise U.AnalysisError(f"{pid}: positions.json disagrees with the cached renders (diff {sampled_diff} vs {diff})")
        out[pid] = role_keys(len(ids["A"]), diff, int(v["question_first"]), tmpl, user_start)
    return out


# ------------------------------------------------------------------ per-key aggregates and the bootstrap
def _corr(x: np.ndarray, y: np.ndarray, method: str) -> float:
    if x.size < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return float((sps.spearmanr if method == "spearman" else sps.pearsonr)(x, y).statistic)


def key_matrices(pair: np.ndarray, key: np.ndarray, score: np.ndarray, flip: np.ndarray) -> Tuple[List[str], List[str], np.ndarray, np.ndarray, np.ndarray]:
    """per (pair, key): entry count, score sum, flip sum (entries with a nan score are dropped)."""
    ok = ~np.isnan(score)
    pair, key, score, flip = pair[ok], key[ok], score[ok], flip[ok].astype(float)
    pids, keys = sorted(set(pair.tolist())), sorted(set(key.tolist()))
    pi = {p: i for i, p in enumerate(pids)}
    ki = {k: i for i, k in enumerate(keys)}
    n = np.zeros((len(pids), len(keys)))
    s = np.zeros_like(n)
    f = np.zeros_like(n)
    for p, k, x, y in zip(pair, key, score, flip):
        n[pi[p], ki[k]] += 1
        s[pi[p], ki[k]] += x
        f[pi[p], ki[k]] += y
    return pids, keys, n, s, f


def corr_from_weights(w: np.ndarray, n: np.ndarray, s: np.ndarray, f: np.ndarray, min_n: int) -> Tuple[float, float, int]:
    """pair weights (bootstrap multiplicities) → per-key mean score / flip rate over keys with n ≥ min_n → (Spearman, Pearson, n keys)."""
    N, S, F = w @ n, w @ s, w @ f
    m = N >= min_n
    if m.sum() < 3:
        return float("nan"), float("nan"), int(m.sum())
    x, y = S[m] / N[m], F[m] / N[m]
    return _corr(x, y, "spearman"), _corr(x, y, "pearson"), int(m.sum())


def position_corr(pair: np.ndarray, key: np.ndarray, score: np.ndarray, flip: np.ndarray, n_boot: int, seed: int, min_n: int = MIN_N) -> dict:
    """Spearman / Pearson of per-key mean score vs per-key flip rate with a pair-bootstrap 95% CI (pairs resampled with replacement)."""
    pids, keys, n, s, f = key_matrices(np.asarray(pair), np.asarray(key), np.asarray(score, dtype=float), np.asarray(flip, dtype=bool))
    w0 = np.ones(len(pids))
    rho, r, nk = corr_from_weights(w0, n, s, f, min_n)
    rng = np.random.default_rng(seed)
    vals = np.full((n_boot, 2), np.nan)
    for b in range(n_boot):
        w = np.bincount(rng.integers(0, len(pids), len(pids)), minlength=len(pids)).astype(float)
        vals[b, 0], vals[b, 1], _ = corr_from_weights(w, n, s, f, min_n)

    def ci(v: np.ndarray) -> Tuple[float, float]:
        v = v[~np.isnan(v)]
        return (float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))) if v.size else (float("nan"), float("nan"))

    (slo, shi), (plo, phi) = ci(vals[:, 0]), ci(vals[:, 1])
    N = n.sum(0)
    m = N >= min_n
    flips = f.sum(0)[m] / N[m] if m.any() else np.array([])
    return {"spearman": rho, "spearman_lo95": slo, "spearman_hi95": shi, "pearson": r, "pearson_lo95": plo, "pearson_hi95": phi,
            "spearman_ci_excludes_0": bool(not np.isnan(slo) and (slo > 0 or shi < 0)), "pearson_ci_excludes_0": bool(not np.isnan(plo) and (plo > 0 or phi < 0)),
            "n_keys": nk, "n_keys_with_any_flip": int((flips > 0).sum()), "n_entries": int(N[m].sum()), "n_pairs": len(pids),
            "n_boot": n_boot, "n_boot_undefined_spearman": int(np.isnan(vals[:, 0]).sum()),
            "_keys": [k for k, mm in zip(keys, m) if mm], "_mean_score": (s.sum(0)[m] / N[m]).tolist() if m.any() else [], "_flip": flips.tolist(), "_n": N[m].tolist()}


# ------------------------------------------------------------------ main
def run(args: argparse.Namespace) -> List[dict]:
    t0 = time.time()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    w, _ = Z.load_z4_world(args.behaviour, args.lo, args.natural_behaviour, args.natural_lo, ("single",))
    readers = [rd for rd in Z.READERS if rd in w.readers]
    t = Z.build_table(w, readers, sites=("single",), dose_of=Z.z4_dose_level)
    pos = np.array([int(w.by_key[k]["position"]) for k in t.key])
    roles_json = json.load(open(args.positions))["pairs"]
    rmap = pair_role_maps(roles_json, Path(args.full_dir))
    rkey = np.array([key_label(rmap[p][int(i)]) for p, i in zip(t.pair, pos)])
    # the sampled role labels of positions.json must agree with the role keying (diff ↔ diff, question_first ↔ question:0, last ↔ last:0)
    expect = {"diff": "diff", "question_first": "question", "last": "last"}
    for p, i, k in zip(t.pair, pos, rkey):
        r0 = roles_json[p]["roles"][str(int(i))]
        if r0 in expect and k.split(":")[0] != expect[r0] or (r0 == "question_first" and k != "question:0"):
            raise U.AnalysisError(f"{p} position {i}: positions.json role {r0} vs role key {k}")
    keys = {"absolute": pos.astype(str), "role": rkey}
    rows: List[dict] = []
    for fam in FAMILIES:
        for al in ALPHAS:
            m = (t.alpha == al) & ((t.family == fam) | (fam == "pooled"))
            for keying in KEYINGS:
                for sc in readers + [MODEL]:
                    score = t.dm[m] if sc == MODEL else t.f[sc][m]
                    rec = position_corr(t.pair[m], keys[keying][m], score, t.flip[m], args.n_boot, args.seed, args.min_n)
                    rows.append({"keying": keying, "family": fam, "alpha": al, "scorer": sc, "score": "Δ_model (nats)" if sc == MODEL else "f_r",
                                 **{k: v for k, v in rec.items() if not k.startswith("_")},
                                 "_cells": list(zip(rec["_keys"], rec["_mean_score"], rec["_flip"], rec["_n"]))})
    csv_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    U.write_csv(out / "per_position_corr.csv", csv_rows)
    wall = round(time.time() - t0, 1)
    write_md(out / "per_position_corr.md", rows, t, readers, args, wall)
    if not args.no_log:
        with open(out / "log.md", "a", encoding="utf-8") as fh:
            fh.write(f"- {dt.datetime.now(dt.timezone.utc).isoformat()}  `PYTHONPATH=. .venv/bin/python projects/g_agreement/z4_positions/position_corr.py "
                     f"--n-boot {args.n_boot} --seed {args.seed} --min-n {args.min_n} --out {args.out}`  CPU only, 0 forward passes, wall {wall} s; "
                     f"wrote per_position_corr.csv / per_position_corr.md (BRIEF_Z deviation 2026-10-09 'Z1 reporting')\n")
    U.log(f"[z4 position corr] wrote {out / 'per_position_corr.csv'} ({len(csv_rows)} rows), wall {wall} s")
    return rows


def _c(r: dict, m: str) -> str:
    if np.isnan(r[m]):
        return "n/a"
    star = "*" if r[f"{m}_ci_excludes_0"] else ""
    return f"{r[m]:+.2f} [{r[f'{m}_lo95']:+.2f}, {r[f'{m}_hi95']:+.2f}]{star}"


def write_md(path: Path, rows: Sequence[dict], t: Z.Table, readers: Sequence[str], args: argparse.Namespace, wall: float) -> None:
    L = [f"# Z4 per-position correlation: reader shift vs flip rate ({dt.datetime.now(dt.timezone.utc).date().isoformat()}; CPU only, 0 forward passes)", "",
         "BRIEF_Z deviation 2026-10-09 \"Z1 reporting\": per position, the mean reader shift f_r (fraction of the reader's own natural separation) "
         "against the flip rate on the same entries, Z4 single-position arm, α 0.75 and α 1 separately. Spearman and Pearson across positions; "
         f"95% CI by pair bootstrap ({args.n_boot} resamples, seed {args.seed}; per-position aggregates recomputed on each resample); positions with "
         f"n ≥ {args.min_n} entries enter; * = CI excludes 0. Reference row: the model's own Δ_model (nats) in place of f_r.",
         "Keyings: **absolute** token index (as per_position.csv); **role** = (role, rank within role): chat_prefix, diff (differing tokens in prompt "
         "order), statement, question (offset from the question's first token), template (offset from <|im_end|>), last — the same key is the same kind "
         "of token in every prompt. f_r uses the Z1 tie tolerance (|sep_r| < 1e-4 excluded: Oracle lens xmap-16/26, xown-09/20); per_position.csv's "
         "Oracle-lens means do not apply it (xmap-16, sep 4e-7, inflates its mapping means), so its f_olens columns are not the ones correlated here.", ""]
    for keying in KEYINGS:
        L.append(f"## {keying} keying")
        L.append("| family | α | scorer | n positions (with ≥1 flip) | n entries | Spearman [95% CI] | Pearson [95% CI] |")
        L.append("|---|---|---|---|---|---|---|")
        for r in rows:
            if r["keying"] != keying:
                continue
            L.append(f"| {r['family']} | {r['alpha']:g} | {LABELS[r['scorer']]} | {r['n_keys']} ({r['n_keys_with_any_flip']}) | {r['n_entries']} | "
                     f"{_c(r, 'spearman')} | {_c(r, 'pearson')} |")
        L.append("")
    L.append("## Role-aligned positions at α 1 that flip (model reference cells: flip rate, mean Δ_model, n)")
    for fam in FAMILIES:
        r = next(x for x in rows if x["keying"] == "role" and x["family"] == fam and x["alpha"] == 1.0 and x["scorer"] == MODEL)
        cells = sorted((c for c in r["_cells"] if c[2] > 0), key=lambda c: -c[2])
        L.append(f"- {fam}: " + ("; ".join(f"{k} {100 * fl:.0f}% (Δ_model {ms:+.1f}, n {int(n)})" for k, ms, fl, n in cells[:10]) or "no position flips") +
                 f" — {r['n_keys']} keys ranked, {r['n_keys_with_any_flip']} with any flip.")
    L.append("")
    L.append("Caveats: no single ownership position flips at either dose (correlation undefined); in mapping only a handful of positions flip "
             "(column 'with ≥1 flip'), so the flip rate is 0 at almost every key and the Spearman is mostly a test of whether those few keys get the "
             "highest reader shift (heavy ties; bootstrap CIs can be narrow or one-sided for that reason — the Pearson is the less tie-bound "
             "companion); the role keying pools prompts by role, so a key with few prompts (long statements, long questions) is dropped by the n filter. "
             "Uniform positions were sampled per pair (seed 0), so most role keys outside diff / question:0 / last carry fewer entries than those three.")
    L.append(f"Command: `PYTHONPATH=. .venv/bin/python projects/g_agreement/z4_positions/position_corr.py --n-boot {args.n_boot} --seed {args.seed} "
             f"--min-n {args.min_n}` (wall {wall} s; {t.key.size} single-position entries, readers {', '.join(readers)}).")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv=None) -> List[dict]:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
