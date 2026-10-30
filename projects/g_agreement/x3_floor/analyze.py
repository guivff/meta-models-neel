"""X3 analysis (CPU; BRIEF_X.md endpoints E8, E9, kill K6).

Inputs: dataset/items_x3_selected.json (sets error / error_control / disagree / agree_control, candidates
(actual, other), text_key), cache/g_agreement/x/x3_lo.jsonl (one row per reader x item, lo_actual =
lp(actual) − lp(other)), cache/g_agreement/x/x3_target.jsonl (the selection decodes; the prompt-only
rate is recomputed from them), cache/g_agreement/states/<item_id>.pt (fp32 block-42 states, for E9).

  E8  per reader x set: P(lo_actual > 0) with an item bootstrap CI (n_boot 2000, seed 0) and a Wilson CI.
      A reader READS THE MODEL, NOT THE TEXT if on ERROR and on DISAGREE the rate is >= 0.75 with the
      bootstrap CI excluding 0.5. Unscorable rows (J-lens without a single-token variant) are excluded and
      counted; ties (lo == 0) count as not favouring.
  E9  column (a) on ERROR ∪ ERROR_CONTROL and DISAGREE ∪ AGREE_CONTROL: leave-one-out diff-in-means probe
      predicting the actual answer (binary label: puzzles 'actual == correct', choice 'actual == first-listed
      option'); held-out AUROC and win (accuracy at the LOO midpoint threshold) with item bootstrap CI;
      two-half ceiling (direction from half 1 evaluated on half 2 and vice versa, halves by seed).
      PRESENT if held-out win >= 0.9 (the E2 rule).
  prompt-only rate per set = fraction of items whose text-implied answer equals the actual answer, from the
      recorded decodes (0 on ERROR/DISAGREE, 1 on the controls by construction; computed, not assumed).
  K6  a set with < 24 items is reported descriptively only (no verdict).

Outputs results/g_agreement/x3[/dev]/{summary.json, e8.csv, e9.csv, fig_main.png}.

    .venv/bin/python projects/g_agreement/x3_floor/analyze.py [--allow-unfrozen] [--selected ...] [--lo ...]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402

MODULE = "x3"
READERS = ("jlens", "olens", "nla")
SETS = ("error", "error_control", "disagree", "agree_control")
UNIONS = {"puzzle": ("error", "error_control"), "choice": ("disagree", "agree_control")}
DECISION_SETS = ("error", "disagree")
E8_MIN_RATE = 0.75
E9_PRESENT_WIN = 0.9
MIN_SET = 24
FROZEN_CONFIG_X = getattr(C, "FROZEN_CONFIG_X", C.MANIFEST_DIR / "frozen_config_x.json")
X_DIR = C.CACHE_DIR / "x"
SET_LABELS = {"error": "ERROR\n(puzzle, model wrong)", "error_control": "ERROR control\n(puzzle, model right)",
              "disagree": "DISAGREE\n(self-guess ≠ choice)", "agree_control": "AGREE control\n(self-guess = choice)"}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selected", default=str(C.DATASET_DIR / "items_x3_selected.json"))
    ap.add_argument("--lo", default=str(X_DIR / "x3_lo.jsonl"))
    ap.add_argument("--target", default=str(X_DIR / "x3_target.jsonl"))
    ap.add_argument("--states-dir", default=str(C.STATES_DIR))
    ap.add_argument("--frozen-config", default=str(FROZEN_CONFIG_X))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    ap.add_argument("--skip-e9", action="store_true", help="skip the probe (no states available)")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ stats
def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float, float]:
    try:
        from common.stats import wilson as _w  # shared repo helper

        p, lo, hi = (float(x) for x in _w(k, n, z))
        return p, (lo if math.isnan(lo) else max(0.0, lo)), (hi if math.isnan(hi) else min(1.0, hi))
    except Exception:  # pragma: no cover - fallback when common/ is not importable
        if n == 0:
            return float("nan"), float("nan"), float("nan")
        p = k / n
        den = 1 + z * z / n
        c = (p + z * z / (2 * n)) / den
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        return p, max(0.0, c - h), min(1.0, c + h)


def item_bootstrap_rate(flags: Sequence[bool], n_boot: int, seed: int, alpha: float = 0.05) -> Tuple[float, float, float]:
    """(p, lo, hi): the mean of the flags and a percentile item-bootstrap CI."""
    x = np.asarray([bool(f) for f in flags], dtype=float)
    if x.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    vals = x[idx].mean(axis=1)
    return float(x.mean()), float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based AUROC with ties at 0.5; nan if one class is empty."""
    from scipy.stats import rankdata

    pos, neg = labels == 1, labels == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    r = rankdata(scores)
    return float((r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def dim_direction(X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, float]:
    """Diff-in-means direction (unit) and the midpoint threshold of the class means along it."""
    mu1, mu0 = X[y == 1].mean(0), X[y == 0].mean(0)
    d = mu1 - mu0
    nrm = float(np.linalg.norm(d))
    d = d / nrm if nrm > 0 else d
    return d, float(((mu1 + mu0) / 2) @ d)


def loo_dim_scores(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Leave-one-out diff-in-means score per item: (h_i · d_{-i}) − threshold_{-i}; > 0 predicts label 1."""
    n = X.shape[0]
    out = np.full(n, np.nan)
    for i in range(n):
        m = np.ones(n, dtype=bool)
        m[i] = False
        yi = y[m]
        if (yi == 1).sum() < 1 or (yi == 0).sum() < 1:
            continue
        d, thr = dim_direction(X[m], yi)
        out[i] = float(X[i] @ d) - thr
    return out


def two_half_ceiling(X: np.ndarray, y: np.ndarray, seed: int) -> Dict[str, Any]:
    """Halves by seed (stratified by label); direction from one half evaluated on the other, both ways."""
    rng = np.random.default_rng(seed)
    halves: List[np.ndarray] = [np.array([], dtype=int), np.array([], dtype=int)]
    for lab in (0, 1):
        idx = np.where(y == lab)[0]
        rng.shuffle(idx)
        halves[0] = np.concatenate([halves[0], idx[0::2]])
        halves[1] = np.concatenate([halves[1], idx[1::2]])
    res = []
    dirs = []
    for a, b in ((0, 1), (1, 0)):
        ia, ib = halves[a], halves[b]
        if (y[ia] == 1).sum() == 0 or (y[ia] == 0).sum() == 0 or ib.size == 0:
            res.append({"auroc": float("nan"), "win": float("nan"), "n_fit": int(ia.size), "n_eval": int(ib.size)})
            continue
        d, thr = dim_direction(X[ia], y[ia])
        dirs.append(d)
        sc = X[ib] @ d - thr
        res.append({"auroc": auroc(sc, y[ib]), "win": float(((sc > 0).astype(int) == y[ib]).mean()),
                    "n_fit": int(ia.size), "n_eval": int(ib.size)})
    cos = float(dirs[0] @ dirs[1]) if len(dirs) == 2 else float("nan")
    return {"halves": res, "auroc": float(np.nanmean([r["auroc"] for r in res])),
            "win": float(np.nanmean([r["win"] for r in res])), "cos_directions": cos}


# ------------------------------------------------------------------ loading
def load_selected(path: str) -> Tuple[dict, Dict[str, dict]]:
    d = U.load_json(path)
    items = {it["item_id"]: it for it in d["items"]}
    for it in items.values():
        if it.get("set") not in SETS:
            raise U.AnalysisError(f"{it['item_id']}: unknown set {it.get('set')!r}")
        if len(it["primary"]["candidates"]) != 2 or it["primary"]["answer"] != it["primary"]["candidates"][0]:
            raise U.AnalysisError(f"{it['item_id']}: candidates must be (actual, other) with answer = actual")
    return d.get("meta", {}), items


def e9_label(item: dict) -> Optional[int]:
    """Binary label of the actual answer: puzzles 'actual == correct'; choice 'actual == first-listed option'."""
    actual = item["primary"]["answer"]
    src = item.get("source") or {}
    if item["family"] == "puzzle":
        ref = src.get("correct")
        if ref is None:
            ref = item.get("text_key")
    else:
        ref = src.get("first_listed")
        if ref is None:
            return None
    return int(U.normalise_answer(actual) == U.normalise_answer(ref))


def text_implied_equals_actual(item: dict, trow: Optional[dict]) -> Optional[bool]:
    """From the recorded decode: puzzle parsed == correct; choice self_guess == actual. Falls back to the
    selected item's text_key when the decode row is missing (flagged in the summary)."""
    if trow is not None:
        if item["family"] == "puzzle":
            if trow.get("parsed") is None:
                return None
            return trow["parsed"] == trow.get("correct")
        if trow.get("self_guess") is None or trow.get("actual") is None:
            return None
        return trow["self_guess"] == trow["actual"]
    tk = item.get("text_key")
    return None if tk is None else (U.normalise_answer(tk) == U.normalise_answer(item["primary"]["answer"]))


# ------------------------------------------------------------------ endpoints
def e8_table(items: Dict[str, dict], lo_rows: List[dict], counts: Dict[str, int], nb: int, sd: int) -> Dict[str, Dict[str, dict]]:
    by: Dict[str, Dict[str, dict]] = {r: {} for r in READERS}
    for r in lo_rows:
        if r.get("reader") in by and r.get("item_id") in items:
            if r["item_id"] in by[r["reader"]]:
                raise U.AnalysisError(f"duplicate LO row {r['reader']}|{r['item_id']}")
            by[r["reader"]][r["item_id"]] = r
    out: Dict[str, Dict[str, dict]] = {}
    for reader in READERS:
        out[reader] = {}
        for s in SETS:
            ids = sorted(i for i, it in items.items() if it["set"] == s)
            rows = [by[reader].get(i) for i in ids]
            scored = [r for r in rows if r is not None and r.get("lo_actual") is not None]
            flags = [float(r["lo_actual"]) > 0 for r in scored]
            k, n = sum(flags), len(flags)
            p, blo, bhi = item_bootstrap_rate(flags, nb, sd)
            _, wlo, whi = wilson(k, n)
            passes = (n > 0) and (p >= E8_MIN_RATE) and (not np.isnan(blo)) and (blo > 0.5)
            out[reader][s] = {"n_items": len(ids), "n_rows": sum(r is not None for r in rows), "n_scored": n,
                              "n_unscorable": sum(1 for r in rows if r is not None and r.get("lo_actual") is None),
                              "n_missing": sum(r is None for r in rows), "k_favours_actual": int(k), "p": p,
                              "boot_lo": blo, "boot_hi": bhi, "wilson_lo": wlo, "wilson_hi": whi,
                              "mean_lo_actual": float(np.mean([r["lo_actual"] for r in scored])) if scored else float("nan"),
                              "passes_rule": bool(passes), "underpowered": counts.get(s, len(ids)) < MIN_SET}
    return out


def e9_probe(items: Dict[str, dict], states_dir: Path, nb: int, sd: int) -> Dict[str, dict]:
    from projects.g_agreement.core import states as S

    out: Dict[str, dict] = {}
    for union, sets in UNIONS.items():
        ids = sorted(i for i, it in items.items() if it["set"] in sets)
        labels = {i: e9_label(items[i]) for i in ids}
        usable = [i for i in ids if labels[i] is not None and S.state_path(i, states_dir).exists()]
        missing_states = [i for i in ids if labels[i] is not None and not S.state_path(i, states_dir).exists()]
        rec: Dict[str, Any] = {"sets": list(sets), "n_items": len(ids), "n_used": len(usable), "n_missing_states": len(missing_states),
                               "n_no_label": sum(labels[i] is None for i in ids),
                               "label": "actual == correct" if union == "puzzle" else "actual == first-listed option"}
        if len(usable) < 4:
            rec.update(status="skipped (fewer than 4 usable items)", present=None)
            out[union] = rec
            continue
        X = np.stack([S.load_state(i, states_dir).numpy().astype(np.float64) for i in usable])
        y = np.asarray([labels[i] for i in usable], dtype=int)
        rec.update(n_pos=int(y.sum()), n_neg=int((1 - y).sum()), majority_rate=float(max(y.mean(), 1 - y.mean())))
        if y.sum() < 2 or (1 - y).sum() < 2:
            rec.update(status="skipped (a class has fewer than 2 items)", present=None)
            out[union] = rec
            continue
        sc = loo_dim_scores(X, y)
        ok = ~np.isnan(sc)
        correct = ((sc[ok] > 0).astype(int) == y[ok])
        win, wlo, whi = item_bootstrap_rate(correct.tolist(), nb, sd)
        rec.update(status="ok", loo_auroc=auroc(sc[ok], y[ok]), loo_win=win, loo_win_boot_lo=wlo, loo_win_boot_hi=whi,
                   loo_k=int(correct.sum()), loo_n=int(ok.sum()), ceiling=two_half_ceiling(X, y, sd),
                   present=bool(win >= E9_PRESENT_WIN), per_item={i: {"score": float(s), "label": int(l)} for i, s, l in zip(usable, sc, y)})
        out[union] = rec
    return out


# ------------------------------------------------------------------ run
def run(args: argparse.Namespace) -> dict:
    frozen, cfg = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if frozen else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    meta, items = load_selected(args.selected)
    sel_sha = U.canonical_items_sha([items[i] for i in sorted(items)])
    lo_rows = U.load_jsonl(args.lo) if Path(args.lo).exists() else []
    trows = {r["item_id"]: r for r in (U.load_jsonl(args.target) if Path(args.target).exists() else [])}
    counts = {s: sum(it["set"] == s for it in items.values()) for s in SETS}
    nb, sd = args.n_boot, args.seed
    U.log(f"[x3] frozen={frozen} {len(items)} selected items {counts}; {len(lo_rows)} LO rows; {len(trows)} decode rows; "
          f"selected sha {sel_sha[:12]}; out={out}")
    underpowered = {s: counts[s] < MIN_SET for s in DECISION_SETS}
    for s, u in underpowered.items():
        if u:
            U.log(f"[x3] K6: {s} has {counts[s]} < {MIN_SET} items -> descriptive only")

    # prompt-only rate per set, from the recorded decodes
    prompt_only: Dict[str, dict] = {}
    for s in SETS:
        ids = sorted(i for i, it in items.items() if it["set"] == s)
        flags = [text_implied_equals_actual(items[i], trows.get(i)) for i in ids]
        known = [f for f in flags if f is not None]
        p, lo, hi = item_bootstrap_rate(known, nb, sd)
        _, wlo, whi = wilson(sum(known), len(known))
        prompt_only[s] = {"k": int(sum(known)), "n": len(known), "p": p, "boot_lo": lo, "boot_hi": hi, "wilson_lo": wlo, "wilson_hi": whi,
                          "n_from_decode_rows": sum(i in trows for i in ids), "n_from_text_key_fallback": sum(i not in trows for i in ids)}
    U.log("[x3] prompt-only (text-implied == actual): " + ", ".join(f"{s} {prompt_only[s]['k']}/{prompt_only[s]['n']}" for s in SETS))

    # E8
    e8 = e8_table(items, lo_rows, counts, nb, sd)
    e8_rows: List[dict] = []
    verdicts: Dict[str, dict] = {}
    for reader in READERS:
        both = all(e8[reader][s]["passes_rule"] for s in DECISION_SETS)
        any_under = any(underpowered.values())
        any_missing = any(e8[reader][s]["n_scored"] == 0 for s in DECISION_SETS)
        if any_missing:
            verdict = "no_data"
        elif any_under:
            verdict = "descriptive_only (K6)"
        else:
            verdict = "reads_the_model" if both else "no_evidence"
        verdicts[reader] = {"verdict": verdict, "per_set": {s: e8[reader][s]["passes_rule"] for s in DECISION_SETS},
                            "rule": f"on ERROR and on DISAGREE: P(lo_actual > 0) >= {E8_MIN_RATE} with item-bootstrap CI excluding 0.5"}
        for s in SETS:
            d = e8[reader][s]
            U.log(f"[x3] E8 {U.METHOD_LABELS[reader]:12s} {s:14s} favours actual {d['k_favours_actual']}/{d['n_scored']} = "
                  f"{100 * d['p']:.1f}% boot [{100 * d['boot_lo']:.0f}, {100 * d['boot_hi']:.0f}] wilson [{100 * d['wilson_lo']:.0f}, {100 * d['wilson_hi']:.0f}]"
                  f"; unscorable {d['n_unscorable']}, missing {d['n_missing']}")
            e8_rows.append({"reader": reader, "set": s, **{k: v for k, v in d.items()}, "prompt_only_p": prompt_only[s]["p"]})
        U.log(f"[x3] E8 {U.METHOD_LABELS[reader]:12s} -> {verdict}")
    U.write_csv(out / "e8.csv", e8_rows)

    # E9
    e9: Dict[str, dict] = {}
    if not args.skip_e9:
        e9 = e9_probe(items, Path(args.states_dir), nb, sd)
        e9_rows = []
        for union, d in e9.items():
            c = d.get("ceiling") or {}
            e9_rows.append({"union": union, "sets": "+".join(d["sets"]), "label": d["label"], "status": d.get("status"), "n_items": d["n_items"],
                            "n_used": d["n_used"], "n_pos": d.get("n_pos"), "n_neg": d.get("n_neg"), "majority_rate": d.get("majority_rate"),
                            "loo_auroc": d.get("loo_auroc"), "loo_win": d.get("loo_win"), "loo_win_boot_lo": d.get("loo_win_boot_lo"),
                            "loo_win_boot_hi": d.get("loo_win_boot_hi"), "ceiling_auroc": c.get("auroc"), "ceiling_win": c.get("win"),
                            "ceiling_cos_directions": c.get("cos_directions"), "present": d.get("present"), "n_missing_states": d["n_missing_states"]})
            if d.get("status") == "ok":
                U.log(f"[x3] E9 {union}: LOO AUROC {d['loo_auroc']:.2f}, win {d['loo_k']}/{d['loo_n']} = {100 * d['loo_win']:.1f}% "
                      f"[{100 * d['loo_win_boot_lo']:.0f}, {100 * d['loo_win_boot_hi']:.0f}]; ceiling AUROC {c['auroc']:.2f} win {100 * c['win']:.1f}% "
                      f"cos {c['cos_directions']:.2f}; majority {100 * d['majority_rate']:.0f}% -> PRESENT={d['present']}")
            else:
                U.log(f"[x3] E9 {union}: {d.get('status')}")
        U.write_csv(out / "e9.csv", e9_rows)

    summary = {"module": MODULE, "frozen": frozen, "selected_sha256": sel_sha, "selected_meta": {k: v for k, v in meta.items() if k != "rule"},
               "counts": counts, "underpowered": underpowered, "min_set": MIN_SET, "n_boot": nb, "seed": sd, "n_lo_rows": len(lo_rows),
               "prompt_only": prompt_only, "E8": e8, "E8_verdicts": verdicts,
               "E9": {u: {k: v for k, v in d.items() if k != "per_item"} for u, d in e9.items()},
               "E9_per_item": {u: d.get("per_item", {}) for u, d in e9.items()},
               "decision_rule": (f"E8: reads the model, not the text if on ERROR and on DISAGREE P(lo_actual > 0) >= {E8_MIN_RATE} with the "
                                 f"item-bootstrap CI excluding 0.5; E9: PRESENT if LOO diff-in-means held-out win >= {E9_PRESENT_WIN}; "
                                 f"K6: a set < {MIN_SET} items is descriptive only")}
    U.write_json(out / "summary.json", summary)
    if not args.no_fig:
        make_figure(out / "fig_main.png", summary, frozen)
    U.log(f"[x3] wrote {out}")
    return summary


def make_figure(path: Path, s: dict, frozen: bool) -> None:
    plt = U.mpl()
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.6), sharey=True)
    e8, po, e9 = s["E8"], s["prompt_only"], s.get("E9", {})
    for ax, set_ in zip(axes, SETS):
        union = "puzzle" if set_ in UNIONS["puzzle"] else "choice"
        xs = []
        for j, reader in enumerate(READERS):
            d = e8[reader][set_]
            rate = U.Rate(d["k_favours_actual"], d["n_scored"], d["p"], d["boot_lo"], d["boot_hi"], d["n_scored"], ci="item-bootstrap")
            U.bar_ci(ax, j, rate, U.METHOD_COLORS[reader], width=0.62)
            xs.append(j)
        pop = po[set_]["p"]
        if not np.isnan(pop):
            ax.axhline(pop, color=U.METHOD_COLORS["prompt_only"], lw=1.4, ls=":", zorder=2, label=f"prompt-only {po[set_]['k']}/{po[set_]['n']}")
        pr = e9.get(union) or {}
        if pr.get("status") == "ok":
            ax.axhline(pr["loo_win"], color=U.INK, lw=1.2, ls="--", zorder=2, label=f"probe LOO win {100 * pr['loo_win']:.0f}% (ceiling {100 * pr['ceiling']['win']:.0f}%)")
        ax.axhline(0.5, color=U.GRID, lw=1.0, zorder=1)
        ax.axhline(E8_MIN_RATE, color=U.INK2, lw=0.8, ls=(0, (1, 3)), zorder=1)
        ax.set_xticks(xs)
        ax.set_xticklabels([U.METHOD_LABELS[r] for r in READERS], fontsize=8.5)
        n = s["counts"][set_]
        under = " — UNDERPOWERED (K6)" if (set_ in s["underpowered"] and s["underpowered"][set_]) else ""
        ax.set_title(f"{SET_LABELS[set_]}\nn = {n}{under}", fontsize=9.5)
        ax.legend(fontsize=7.5, loc="lower left")
        U.style_ax(ax, "% items: reader LO favours ACTUAL answer" if set_ == SETS[0] else None, (0, 1.18))
    verdict_txt = "; ".join(f"{U.METHOD_LABELS[r]}: {s['E8_verdicts'][r]['verdict'].replace('_', ' ')}" for r in READERS)
    fig.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + f"X3 floor sets — E8 reader LO vs the model's actual answer (bars = 95% item-bootstrap CI; "
                 f"dotted = prompt-only rate; dashed = E9 probe)\n{verdict_txt}", y=1.04, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
