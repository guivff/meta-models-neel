"""X1 analysis (CPU; BRIEF_X.md §X1 endpoints E1-E3).

Inputs: dataset/items_x.json, cache/g_agreement/x/x1_lo.jsonl (x1_bank/collect.py), cache/g_agreement/states/<id>.pt (fp32).
  E1  per reader x family: paired win P(LO(h_A) > LO(h_B)) with LO = lp(answer_A) - lp(other), i.e. the stored
      per-state lo (own answer minus other) gives win = lo_A + lo_B > 0. 95% pair-bootstrap CI (n_boot 2000,
      seed 0) and Wilson CI. SEPARATES if win >= 0.75 and the bootstrap CI excludes 0.5. Unscorable rows
      (J-lens candidates without a single-token variant) are excluded and counted.
  E2  column (a) PRESENT: leave-one-pair-out diff-in-means probe on the fp32 states, per family:
        binary families   tense (past - future), ownership (owner is the first-mentioned name - second):
                          u = mean over the other pairs of (h_pos - h_neg); score = u . h
        identity families language, mapping (the fact is WHICH candidate; A/B of different pairs differ in
                          unrelated candidates): class-mean directions d_v = mean(h | answer v) - mean(h) over the
                          other pairs; for the held-out pair with candidates (a, b): u = d_a - d_b; pairs whose
                          candidate was never an answer in the training pairs are skipped (counted)
      Held-out paired win and AUROC; two-half ceiling = direction from half 1 evaluated on half 2 and vice versa
      (pairs split by seed 0). PRESENT if held-out win >= 0.9.
  E3  state-free prior: each reader's LO on the family mean state, must be inside [-1, 1] nats on average.
Outputs results/g_agreement/x1[/dev]/{summary.json, e1.csv, e2.csv, fig_main.png}. Works on the --split dev smoke
subset (one pair per family: E2 is reported as n/a, nothing crashes) and with readers whose rows are all unscorable.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.stats import wilson  # noqa: E402
from projects.g_agreement.core import analysis_utils as U  # noqa: E402

MODULE = "x1"
READERS = ("jlens", "olens", "nla")
FAMILIES = ("ownership", "mapping", "language", "tense")
PROBE_TYPE = {"tense": "binary", "ownership": "binary", "language": "identity", "mapping": "identity"}
SEPARATE_WIN, PRESENT_WIN, E3_BAND = 0.75, 0.9, 1.0
DEFAULT_ITEMS = ROOT / "projects" / "g_agreement" / "dataset" / "items_x.json"
DEFAULT_LO = ROOT / "cache" / "g_agreement" / "x" / "x1_lo.jsonl"
DEFAULT_STATES = ROOT / "cache" / "g_agreement" / "states"
DEFAULT_FROZEN = ROOT / "projects" / "g_agreement" / "manifest" / "frozen_config_x.json"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(DEFAULT_ITEMS))
    ap.add_argument("--lo", default=str(DEFAULT_LO))
    ap.add_argument("--states-dir", default=str(DEFAULT_STATES))
    ap.add_argument("--frozen-config", default=str(DEFAULT_FROZEN))
    ap.add_argument("--split", choices=["dev", "test"], default="test")
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ loading
def load_pairs(items: Dict[str, dict], split: str) -> Dict[str, List[dict]]:
    """{family: [pair dicts {pair_id, A, B}]} of the split, in item order."""
    by: Dict[str, Dict[str, dict]] = {}
    for it in items.values():
        if it["split"] == split and it["family"] in FAMILIES:
            by.setdefault(it["pair_id"], {"pair_id": it["pair_id"], "family": it["family"]})[it["version"]] = it
    out: Dict[str, List[dict]] = {f: [] for f in FAMILIES}
    for p in by.values():
        if "A" in p and "B" in p:
            out[p["family"]].append(p)
    return out


def load_states(pairs: List[dict], states_dir: Path) -> Tuple[Dict[str, np.ndarray], List[str]]:
    import torch

    H, missing = {}, []
    for p in pairs:
        for v in "AB":
            iid = p[v]["item_id"]
            f = states_dir / f"{iid}.pt"
            if f.exists():
                H[iid] = torch.load(f, map_location="cpu").float().numpy().astype(np.float64)
            else:
                missing.append(iid)
    return H, missing


# ------------------------------------------------------------------ E1
def e1_reader_family(rows: List[dict], pairs: List[dict], nb: int, sd: int) -> dict:
    """Paired win for one reader on one family. rows: this reader's E1 rows (any family)."""
    lo = {r["item_id"]: r for r in rows}
    n_unscorable = sum(1 for p in pairs for v in "AB" if lo.get(p[v]["item_id"], {}).get("unscorable"))
    n_missing = sum(1 for p in pairs for v in "AB" if p[v]["item_id"] not in lo)
    ok = [p for p in pairs if all(p[v]["item_id"] in lo and not lo[p[v]["item_id"]]["unscorable"] and lo[p[v]["item_id"]]["lo"] is not None for v in "AB")]
    win = {p["pair_id"]: lo[p["A"]["item_id"]]["lo"] + lo[p["B"]["item_id"]]["lo"] > 0 for p in ok}
    margin = {p["pair_id"]: lo[p["A"]["item_id"]]["lo"] + lo[p["B"]["item_id"]]["lo"] for p in ok}
    rate = U.pair_rate([(pid, w) for pid, w in win.items()], nb, sd)
    _, wlo, whi = wilson(rate.k, rate.n) if rate.n else (float("nan"),) * 3
    separates = bool(rate.n and rate.p >= SEPARATE_WIN and rate.lo > 0.5)
    return {"k": rate.k, "n": rate.n, "p": rate.p, "lo": rate.lo, "hi": rate.hi, "wilson_lo": wlo, "wilson_hi": whi,
            "n_pairs_total": len(pairs), "n_pairs_scored": len(ok), "n_unscorable_rows": n_unscorable, "n_missing_rows": n_missing,
            "mean_margin_nats": float(np.mean(list(margin.values()))) if margin else float("nan"), "separates": separates,
            "per_pair": {pid: {"win": bool(w), "margin": margin[pid]} for pid, w in win.items()}}


# ------------------------------------------------------------------ E2 probes
def pos_version(pair: dict) -> str:
    """Binary families: the version carrying the positive label (tense: past = A; ownership: owner first-mentioned)."""
    if pair["family"] == "tense":
        return "A" if pair["A"]["primary"]["answer"] == "past" else "B"
    return "A" if pair["A"]["construction"]["answer_is_first_mentioned"] else "B"


def _unit(u: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(u)
    return u / n if n > 0 else u


def direction_binary(train: List[dict], H: Dict[str, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    diffs, allh = [], []
    for p in train:
        pv = pos_version(p)
        nv = "B" if pv == "A" else "A"
        diffs.append(H[p[pv]["item_id"]] - H[p[nv]["item_id"]])
        allh += [H[p["A"]["item_id"]], H[p["B"]["item_id"]]]
    return _unit(np.mean(diffs, axis=0)), np.mean(allh, axis=0)


def direction_identity(train: List[dict], H: Dict[str, np.ndarray], cands: Tuple[str, str]) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    by_val: Dict[str, List[np.ndarray]] = defaultdict(list)
    allh = []
    for p in train:
        for v in "AB":
            by_val[p[v]["primary"]["answer"]].append(H[p[v]["item_id"]])
            allh.append(H[p[v]["item_id"]])
    a, b = cands
    if not by_val.get(a) or not by_val.get(b):
        return None
    m = np.mean(allh, axis=0)
    return _unit((np.mean(by_val[a], axis=0) - m) - (np.mean(by_val[b], axis=0) - m)), m


def score_pair(pair: dict, train: List[dict], H: Dict[str, np.ndarray]) -> Optional[Tuple[float, float]]:
    """(score of the positive-label state, score of the other) for a held-out pair, or None if skipped.
    Positive = pos_version (binary) or version A, whose answer is candidates[0] (identity)."""
    fam = pair["family"]
    if not train:
        return None
    if PROBE_TYPE[fam] == "binary":
        u, m = direction_binary(train, H)
        pv = pos_version(pair)
    else:
        d = direction_identity(train, H, tuple(pair["A"]["primary"]["candidates"]))
        if d is None:
            return None
        u, m = d
        pv = "A"
    nv = "B" if pv == "A" else "A"
    return float(u @ (H[pair[pv]["item_id"]] - m)), float(u @ (H[pair[nv]["item_id"]] - m))


def summarise_probe(scored: Dict[str, Tuple[float, float]], n_total: int, nb: int, sd: int) -> dict:
    win = {pid: s_pos > s_neg for pid, (s_pos, s_neg) in scored.items()}
    rate = U.pair_rate(list(win.items()), nb, sd) if win else U.Rate(0, 0, float("nan"), float("nan"), float("nan"), 0)
    _, wlo, whi = wilson(rate.k, rate.n) if rate.n else (float("nan"),) * 3
    sc = np.array([s for v in scored.values() for s in v]) if scored else np.array([])
    lb = np.array([l for _ in scored for l in (1, 0)]) if scored else np.array([])
    return {"k": rate.k, "n": rate.n, "p": rate.p, "lo": rate.lo, "hi": rate.hi, "wilson_lo": wlo, "wilson_hi": whi,
            "auroc": _auroc(sc, lb) if len(sc) else float("nan"), "n_pairs_total": n_total, "n_pairs_skipped": n_total - len(scored)}


def _auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    from scipy.stats import rankdata

    pos, neg = labels == 1, labels == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    r = rankdata(scores)
    return float((r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum()))


def e2_family(fam: str, pairs: List[dict], H: Dict[str, np.ndarray], nb: int, sd: int) -> dict:
    """E2 for one family: LOO probe and the two-half ceiling."""
    usable = [p for p in pairs if all(p[v]["item_id"] in H for v in "AB")]
    loo: Dict[str, Tuple[float, float]] = {}
    for p in usable:
        r = score_pair(p, [q for q in usable if q["pair_id"] != p["pair_id"]], H)
        if r is not None:
            loo[p["pair_id"]] = r
    rng = np.random.default_rng(sd)
    order = [usable[i] for i in rng.permutation(len(usable))]
    h1, h2 = order[: len(order) // 2], order[len(order) // 2:]
    halves: Dict[str, Tuple[float, float]] = {}
    per_half = {}
    for name, train, test in (("half1_to_half2", h1, h2), ("half2_to_half1", h2, h1)):
        sc = {}
        for p in test:
            r = score_pair(p, train, H)
            if r is not None:
                sc[p["pair_id"]] = r
        halves.update(sc)
        per_half[name] = summarise_probe(sc, len(test), nb, sd)
    out = {"probe_type": PROBE_TYPE[fam], "n_pairs_total": len(pairs), "n_pairs_with_states": len(usable),
           "n_states_missing": 2 * (len(pairs) - len(usable)), "loo": summarise_probe(loo, len(usable), nb, sd),
           "ceiling": {"pooled": summarise_probe(halves, len(usable), nb, sd), **per_half, "n_half1": len(h1), "n_half2": len(h2)}}
    out["present"] = bool(out["loo"]["n"] and out["loo"]["p"] >= PRESENT_WIN)
    out["loo_per_pair"] = {pid: {"win": bool(s[0] > s[1]), "score_pos": s[0], "score_neg": s[1]} for pid, s in loo.items()}
    return out


# ------------------------------------------------------------------ E3
def e3_reader(mean_rows: List[dict]) -> Dict[str, dict]:
    out = {}
    for r in mean_rows:
        out[r["family"]] = {"mean_lo": r.get("mean_lo"), "mean_abs_lo": r.get("mean_abs_lo"), "n_scorable": r.get("n_scorable"),
                            "n_states_in_mean": r.get("n_states_in_mean"),
                            "within_band": (abs(r["mean_lo"]) <= E3_BAND) if r.get("mean_lo") is not None else None}
    return out


# ------------------------------------------------------------------ run
def run(args: argparse.Namespace) -> dict:
    fz = U.load_frozen_config(args.frozen_config)
    frozen = bool(fz and fz.get("frozen") is True)
    if args.split == "test" and not frozen and not args.allow_unfrozen:
        raise U.FrozenConfigError(f"{args.frozen_config} missing or frozen!=true; pass --allow-unfrozen or --split dev")
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("dev" if args.split == "dev" else ""))
    out.mkdir(parents=True, exist_ok=True)
    meta, items = U.load_items(args.items)
    pairs = load_pairs(items, args.split)
    rows = U.load_jsonl(args.lo) if Path(args.lo).exists() else []
    e1_rows = [r for r in rows if r.get("condition", "natural") == "natural" and "item_id" in r]
    mean_rows = [r for r in rows if r.get("condition") == "mean_state"]
    for r in e1_rows:
        if r["item_id"] not in items:
            raise U.AnalysisError(f"x1_lo.jsonl references unknown item {r['item_id']}")
    nb, sd = args.n_boot, args.seed
    U.log(f"[x1] frozen={frozen} split={args.split} pairs={{{', '.join(f'{f}: {len(p)}' for f, p in pairs.items())}}} "
          f"E1 rows={len(e1_rows)} E3 rows={len(mean_rows)} out={out}")
    summary: dict = {"module": MODULE, "split": args.split, "frozen": frozen, "n_boot": nb, "seed": sd,
                     "dataset_sha256_items": meta.get("sha256_items"), "thresholds": {"separate_win": SEPARATE_WIN, "present_win": PRESENT_WIN, "e3_band": E3_BAND},
                     "orientation": "lo = lp(own answer) - lp(other); E1 win = lo_A + lo_B > 0", "E1": {}, "E2": {}, "E3": {}}
    e1_csv, e2_csv = [], []
    for rd in READERS:
        rrows = [r for r in e1_rows if r["reader"] == rd]
        if not rrows:
            U.log(f"[x1] WARNING no E1 rows for {rd}")
        summary["E1"][rd] = {}
        for fam in FAMILIES:
            if not pairs[fam]:
                continue
            e = e1_reader_family(rrows, pairs[fam], nb, sd)
            summary["E1"][rd][fam] = e
            e1_csv.append({"reader": rd, "family": fam, **{k: e[k] for k in e if k != "per_pair"}})
            U.log(f"[x1] E1 {rd:5} {fam:9}: win {U.fmt_count(e['k'], e['n'])} boot[{100 * e['lo']:.0f}, {100 * e['hi']:.0f}] "
                  f"wilson[{100 * e['wilson_lo']:.0f}, {100 * e['wilson_hi']:.0f}] unscorable={e['n_unscorable_rows']} missing={e['n_missing_rows']} separates={e['separates']}")
        summary["E3"][rd] = e3_reader([r for r in mean_rows if r["reader"] == rd])
        for fam, v in summary["E3"][rd].items():
            U.log(f"[x1] E3 {rd:5} {fam:9}: mean LO on the family mean state {v['mean_lo']} (|.|<=1: {v['within_band']})")
    states_dir = Path(args.states_dir)
    for fam in FAMILIES:
        if not pairs[fam]:
            continue
        H, missing = load_states(pairs[fam], states_dir)
        e = e2_family(fam, pairs[fam], H, nb, sd)
        summary["E2"][fam] = e
        l, c = e["loo"], e["ceiling"]["pooled"]
        e2_csv.append({"family": fam, "probe_type": e["probe_type"], "n_pairs_total": e["n_pairs_total"], "n_states_missing": e["n_states_missing"],
                       "loo_k": l["k"], "loo_n": l["n"], "loo_win": l["p"], "loo_lo": l["lo"], "loo_hi": l["hi"], "loo_wilson_lo": l["wilson_lo"],
                       "loo_wilson_hi": l["wilson_hi"], "loo_auroc": l["auroc"], "loo_skipped": l["n_pairs_skipped"],
                       "ceiling_k": c["k"], "ceiling_n": c["n"], "ceiling_win": c["p"], "ceiling_lo": c["lo"], "ceiling_hi": c["hi"], "ceiling_auroc": c["auroc"],
                       "ceiling_half1_to_half2_win": e["ceiling"]["half1_to_half2"]["p"], "ceiling_half2_to_half1_win": e["ceiling"]["half2_to_half1"]["p"],
                       "present": e["present"]})
        U.log(f"[x1] E2 {fam:9} ({e['probe_type']}): LOO win {U.fmt_count(l['k'], l['n'])} AUROC {l['auroc']:.2f} skipped={l['n_pairs_skipped']} "
              f"missing states={e['n_states_missing']}; ceiling win {U.fmt_count(c['k'], c['n'])} AUROC {c['auroc']:.2f}; present={e['present']}")
    U.write_csv(out / "e1.csv", e1_csv)
    U.write_csv(out / "e2.csv", e2_csv)
    U.write_json(out / "summary.json", summary)
    if not args.no_fig:
        make_figure(out / "fig_main.png", summary)
    U.log(f"[x1] wrote {out}")
    return summary


def _rate(d: dict) -> U.Rate:
    return U.Rate(d["k"], d["n"], d["p"], d["lo"], d["hi"], d["n"])


def make_figure(path: Path, summary: dict) -> None:
    """One panel per family: paired win per reader (E1), the LOO probe (E2) and its two-half ceiling (hollow), CI bars."""
    plt = U.mpl()
    fams = [f for f in FAMILIES if f in summary["E2"] or any(f in summary["E1"].get(r, {}) for r in READERS)]
    fig, axes = plt.subplots(1, max(len(fams), 1), figsize=(3.4 * max(len(fams), 1), 4.2), sharey=True)
    axes = np.atleast_1d(axes)
    labels = [U.METHOD_LABELS[r] for r in READERS] + ["probe\n(LOO)", "ceiling\n(two-half)"]
    for ax, fam in zip(axes, fams):
        for j, rd in enumerate(READERS):
            e = summary["E1"].get(rd, {}).get(fam)
            if e and e["n"]:
                U.bar_ci(ax, j, _rate(e), U.METHOD_COLORS[rd])
            else:
                ax.text(j, 0.02, "no\nrows", ha="center", va="bottom", fontsize=7, color=U.INK2)
        e2 = summary["E2"].get(fam)
        if e2:
            if e2["loo"]["n"]:
                U.bar_ci(ax, 3, _rate(e2["loo"]), U.METHOD_COLORS["target"])
            else:
                ax.text(3, 0.02, "n/a", ha="center", va="bottom", fontsize=7, color=U.INK2)
            if e2["ceiling"]["pooled"]["n"]:
                U.bar_ci(ax, 4, _rate(e2["ceiling"]["pooled"]), U.METHOD_COLORS["target"], hollow=True)
            else:
                ax.text(4, 0.02, "n/a", ha="center", va="bottom", fontsize=7, color=U.INK2)
        for y, ls in ((0.5, ":"), (SEPARATE_WIN, "--"), (PRESENT_WIN, "-")):
            ax.axhline(y, color=U.INK2, lw=0.7, ls=ls, zorder=1)
        ax.set_xticks(range(5))
        ax.set_xticklabels(labels, fontsize=7.5)
        U.style_ax(ax, "paired win (% of pairs)" if ax is axes[0] else None, (0, 1.15))
        n = summary["E2"].get(fam, {}).get("n_pairs_total", "?")
        ax.set_title(f"{fam} ({n} pairs)")
    fig.suptitle(("" if summary["frozen"] else "UNFROZEN ") + f"X1 — E1 reader paired win vs E2 probe (lines: 0.5 / 0.75 separate / 0.9 present); "
                 f"split={summary['split']}; bars = 95% pair-bootstrap CI, k/n printed", y=1.02, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
