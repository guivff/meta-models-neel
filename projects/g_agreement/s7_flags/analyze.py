"""S7 — can anything flag a shared reader error? (BRIEF_S.md S7, pre-registered 2026-10-16; CPU only, no forward passes)

Items: X3 ERROR (297 puzzle items, model's greedy answer task-wrong). KEY = the model's actual answer (X6 convention).
SHARED-WRONG = J-lens, Oracle lens and NLA all favour the non-key candidate (raw native LO < 0); ALL-RIGHT = all three
favour the key. Flags (higher = suspect a shared error):
  (a)  oracle_conf         -|LO_Oracle|
  (b') oracle_ft_distinct  distinct symbols across the four F2-4 Oracle free-text readouts (blocks 44/48/52/56)
  (c)  probe_disagree      -(X6 5-fold multinomial probe score toward the readers' common answer)
  (d)  reader_spread       SD over the three readers of their z-scored LO
  (d') weakest_margin      -min_r |z_r|            (descriptive)
  (m)  model_margin        -|model answer margin at block 63| (reference, descriptive)
AUROC shared-wrong vs all-right, stratified item bootstrap (2,000, seed 0). Decision: works iff CI lower bound > 0.7.
Permutation null: shuffle each reader's favours-key sign within difficulty bins (model margin at block 63, 5 quantile
bins primary; 3 and 10 sensitivity), 10,000 permutations, seed 0.

The X6 loaders/probe are imported from --data-root (the checkout that holds x6_majority and the cache):
    .venv/bin/python projects/g_agreement/s7_flags/analyze.py --data-root /path/to/mats-minis [--out results/g_agreement/s7]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE_ROOT = Path(__file__).resolve().parents[3]
SEED = 0
N_BOOT = 2000
N_PERM = 10000
BINS_PRIMARY = 5
BINS_SENS = (3, 10)
READERS = ("jlens", "olens", "nla")
FLAGS = ("oracle_conf", "oracle_ft_distinct", "probe_disagree", "reader_spread")
FLAGS_DESC = ("weakest_margin", "model_margin")
FLAG_LABELS = {"oracle_conf": "(a) Oracle confidence  −|LO|", "oracle_ft_distinct": "(b′) Oracle free-text: distinct answers (4 blocks)",
               "probe_disagree": "(c) probe disagrees with readers", "reader_spread": "(d) reader–reader spread (SD of z-LO)",
               "weakest_margin": "(d′) weakest reader margin  −min|z|", "model_margin": "(m) model margin  −|LO@63| (reference)"}


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, default=HERE_ROOT)
    ap.add_argument("--out", type=Path, default=HERE_ROOT / "results" / "g_agreement" / "s7")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ stats
def auroc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    allv = np.concatenate([pos, neg])
    ranks = _rankdata(allv)
    return (ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def _rankdata(x):
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), float)
    xs = x[order]
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and xs[j + 1] == xs[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def auroc_boot(pos, neg, nb=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    bs = [auroc(pos[rng.integers(0, len(pos), len(pos))], neg[rng.integers(0, len(neg), len(neg))]) for _ in range(nb)]
    return float(auroc(pos, neg)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def roc_curve(pos, neg):
    s = np.concatenate([pos, neg]); y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    th = np.unique(s)[::-1]
    tpr = [0.0] + [float((np.asarray(pos) >= t).mean()) for t in th]
    fpr = [0.0] + [float((np.asarray(neg) >= t).mean()) for t in th]
    return np.array(fpr), np.array(tpr)


def boot_rate(x, nb=N_BOOT, seed=SEED):
    x = np.asarray(x, float); rng = np.random.default_rng(seed)
    bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(nb)]
    return float(x.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def quantile_bins(v, k):
    edges = np.quantile(v, np.linspace(0, 1, k + 1))
    b = np.searchsorted(edges[1:-1], v, side="right")
    return b


def perm_null(S, bins, n_perm=N_PERM, seed=SEED):
    """S: (n, 3) bool favours-key. Shuffle each reader's column within bins; statistic = share all three non-key."""
    rng = np.random.default_rng(seed)
    n = S.shape[0]
    wrong = ~S
    counts = np.zeros(n_perm)
    for b in np.unique(bins):
        idx = np.where(bins == b)[0]
        prod = np.ones((n_perm, len(idx)), bool)
        for r in range(S.shape[1]):
            perm = np.argsort(rng.random((n_perm, len(idx))), axis=1)
            prod &= wrong[idx][:, r][perm]
        counts += prod.sum(1)
    return counts / n


# ------------------------------------------------------------------ data
def load(data_root: Path):
    sys.path.insert(0, str(data_root))
    x6 = importlib.import_module("projects.g_agreement.x6_majority.analyze")
    U = x6.U
    sel = {it["item_id"]: it for it in U.load_json(data_root / "projects/g_agreement/dataset/items_x3_selected.json")["items"]}
    x3 = U.load_jsonl(data_root / "cache/g_agreement/x/x3_lo.jsonl")
    tabs, info = x6.build_d3(sel, x3, data_root / "cache/g_agreement/states", True, U.SEED)
    rows = tabs["D3_error"]
    ll = {r["item_id"]: r for r in U.load_jsonl(data_root / "cache/g_agreement/y/y1_logitlens.jsonl")}
    ft = defaultdict(dict)
    with open(data_root / "results/g_agreement/f2/t4/t4_confusion.csv") as f:
        for r in csv.DictReader(f):
            if r["set"] == "error":
                ft[r["item_id"]][int(r["layer"])] = set(r["symbols"].split()) if r["symbols"] else set()
    return rows, sel, ll, ft, info


def build(rows, sel, ll, ft, field):
    out = []
    for r in rows:
        lo = r[field]
        if any(lo[k] is None for k in READERS):
            continue
        fav = {k: lo[k] > 0 for k in READERS}
        if all(fav.values()):
            cls = "all_right"
        elif not any(fav.values()):
            cls = "shared_wrong"
        else:
            cls = "mixed"
        it = sel[r["state"]]
        m = ll.get(r["state"], {})
        marg = None if m.get("unscorable") else (m.get("margins") or {}).get("63")
        f4 = ft.get(r["state"], {})
        out.append({"item_id": r["state"], "class": cls, "key_model_answer": it["primary"]["answer"], "other_candidate": it["primary"]["candidates"][1],
                    "correct_answer": it["source"]["correct"], "lo_jlens": lo["jlens"], "lo_olens": lo["olens"], "lo_nla": lo["nla"],
                    "probe_toward_key": lo.get("probe") if field == "lo" else r["lo"].get("probe"), "model_margin63": marg,
                    "ft_distinct": len(set().union(*f4.values())) if len(f4) == 4 else None})
    # z-score each reader over all scored ERROR items
    for k in READERS:
        v = np.array([o[f"lo_{k}"] for o in out]); mu, sd = v.mean(), v.std()
        for o in out:
            o[f"z_{k}"] = (o[f"lo_{k}"] - mu) / sd
    for o in out:
        z = np.array([o[f"z_{k}"] for k in READERS])
        sgn = 1.0 if o["class"] == "all_right" else -1.0  # orient toward the readers' common answer
        o["oracle_conf"] = -abs(o["lo_olens"])
        o["oracle_ft_distinct"] = o["ft_distinct"]
        o["probe_disagree"] = None if o["probe_toward_key"] is None or o["class"] == "mixed" else -sgn * o["probe_toward_key"]
        o["reader_spread"] = float(z.std(ddof=1))
        o["weakest_margin"] = -float(np.abs(z).min())
        o["model_margin"] = None if o["model_margin63"] is None else -abs(o["model_margin63"])
    return out


def flag_stats(items, flags):
    res = {}
    for f in flags:
        pos = [o[f] for o in items if o["class"] == "shared_wrong" and o[f] is not None]
        neg = [o[f] for o in items if o["class"] == "all_right" and o[f] is not None]
        a, lo, hi = auroc_boot(pos, neg)
        res[f] = {"auroc": a, "lo": lo, "hi": hi, "n_pos": len(pos), "n_neg": len(neg), "works": lo > 0.7,
                  "n_dropped": sum(1 for o in items if o["class"] != "mixed" and o[f] is None), "roc": roc_curve(pos, neg)}
    return res


def null_stats(items):
    it = [o for o in items if o["model_margin63"] is not None]
    S = np.array([[o[f"lo_{k}"] > 0 for k in READERS] for o in it])
    marg = np.array([o["model_margin63"] for o in it])
    obs = float((~S).all(1).mean())
    indep = float(np.prod((~S).mean(0)))
    out = {"n": len(it), "n_no_margin": len(items) - len(it), "observed": obs, "indep_plain": indep, "bins": {}}
    for k in (BINS_PRIMARY,) + BINS_SENS:
        null = perm_null(S, quantile_bins(marg, k))
        out["bins"][k] = {"null_mean": float(null.mean()), "null_lo": float(np.percentile(null, 2.5)), "null_hi": float(np.percentile(null, 97.5)),
                          "ratio": obs / null.mean(), "p": float((null >= obs - 1e-12).mean()),
                          "frac_excess_explained": (null.mean() - indep) / (obs - indep) if obs > indep else float("nan")}
    # per-bin rates (primary)
    b = quantile_bins(marg, BINS_PRIMARY)
    out["per_bin"] = [{"bin": int(j), "n": int((b == j).sum()), "margin_lo": float(marg[b == j].min()), "margin_hi": float(marg[b == j].max()),
                       "shared_wrong": float((~S[b == j]).all(1).mean()),
                       "P_wrong": {k: float((~S[b == j][:, i]).mean()) for i, k in enumerate(READERS)}} for j in np.unique(b)]
    return out


# ------------------------------------------------------------------ outputs
def fig(path, st):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = {"oracle_conf": "#c0504d", "oracle_ft_distinct": "#e8a33d", "probe_disagree": "#7d5ba6", "reader_spread": "#2f7ebc", "model_margin": "#888888"}
    figr, ax = plt.subplots(figsize=(6.4, 7.6))
    ax.plot([0, 1], [0, 1], color="#bbbbbb", lw=1, ls=":")
    for f in FLAGS + ("model_margin",):
        d = st[f]; fpr, tpr = d["roc"]
        ax.step(fpr, tpr, where="post", color=cols[f], lw=1.2 if f == "model_margin" else 2, ls="--" if f == "model_margin" else "-",
                label=f"{FLAG_LABELS[f]}\nAUROC {d['auroc']:.2f} [{d['lo']:.2f}, {d['hi']:.2f}]  (n {d['n_pos']}/{d['n_neg']})")
    ax.set_xlabel("false-positive rate (all-right items flagged)")
    ax.set_ylabel("true-positive rate (shared-wrong items flagged)")
    ax.set_title("S7: flagging shared J-lens/Oracle/NLA errors (X3 ERROR, raw LO)\nworks iff AUROC CI lower bound > 0.7", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2, frameon=False)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.0)
    figr.tight_layout(); figr.savefig(path, dpi=150); plt.close(figr)


def main(argv=None):
    a = parse_args(argv)
    t0 = time.time()
    a.out.mkdir(parents=True, exist_ok=True)
    rows, sel, ll, ft, info = load(a.data_root)
    res = {}
    for variant, field in (("raw", "lo"), ("centred", "lo_centred")):
        items = build(rows, sel, ll, ft, field)
        res[variant] = {"items": items, "flags": flag_stats(items, FLAGS + FLAGS_DESC), "null": null_stats(items)}
    raw = res["raw"]
    # item lists
    keep = ["item_id", "class", "key_model_answer", "other_candidate", "correct_answer", "lo_jlens", "lo_olens", "lo_nla", "probe_toward_key",
            "model_margin63", "ft_distinct", "oracle_conf", "probe_disagree", "reader_spread", "weakest_margin"]
    with open(a.out / "shared_wrong_items.csv", "w", newline="") as f:
        w = csv.DictWriter(f, keep, extrasaction="ignore"); w.writeheader()
        for o in sorted(raw["items"], key=lambda o: (o["class"], o["item_id"])):
            if o["class"] != "mixed":
                w.writerow(o)
    # s7.csv
    with open(a.out / "s7.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scoring", "kind", "name", "value", "lo", "hi", "n_pos", "n_neg", "works", "in_verdict"])
        for v in ("raw", "centred"):
            for fl, d in res[v]["flags"].items():
                w.writerow([v, "auroc", fl, d["auroc"], d["lo"], d["hi"], d["n_pos"], d["n_neg"], d["works"], v == "raw" and fl in FLAGS])
            nl = res[v]["null"]
            w.writerow([v, "shared_wrong_rate", "observed", nl["observed"], "", "", nl["n"], "", "", False])
            w.writerow([v, "shared_wrong_rate", "independence_plain", nl["indep_plain"], "", "", nl["n"], "", "", False])
            for k, d in nl["bins"].items():
                w.writerow([v, "shared_wrong_rate", f"perm_null_{k}bins", d["null_mean"], d["null_lo"], d["null_hi"], nl["n"], "", "", False])
                w.writerow([v, "ratio_obs_over_null", f"perm_null_{k}bins", d["ratio"], "", "", nl["n"], "", "", False])
                w.writerow([v, "perm_p", f"perm_null_{k}bins", d["p"], "", "", nl["n"], "", "", False])
    fig(a.out / "fig_s7.png", raw["flags"])
    summ = {v: {"n_items": len(res[v]["items"]), "classes": {c: sum(o["class"] == c for o in res[v]["items"]) for c in ("shared_wrong", "all_right", "mixed")},
                "flags": {f: {k: d[k] for k in ("auroc", "lo", "hi", "n_pos", "n_neg", "works", "n_dropped")} for f, d in res[v]["flags"].items()},
                "null": res[v]["null"]} for v in res}
    summ["probe_info"] = info.get("puzzle")
    summ["created_at"] = dt.datetime.now(dt.timezone.utc).isoformat(); summ["wall_s"] = time.time() - t0
    (a.out / "summary.json").write_text(json.dumps(summ, indent=1, default=float))
    print(json.dumps({v: {"classes": summ[v]["classes"], "flags": {f: [round(d["auroc"], 3), round(d["lo"], 3), round(d["hi"], 3), d["n_pos"], d["n_neg"]] for f, d in summ[v]["flags"].items()},
                          "obs": summ[v]["null"]["observed"], "indep": summ[v]["null"]["indep_plain"],
                          "null": {k: [round(d["null_mean"], 4), round(d["null_lo"], 4), round(d["null_hi"], 4), round(d["ratio"], 2), d["p"], round(d["frac_excess_explained"], 2)] for k, d in summ[v]["null"]["bins"].items()}}
                      for v in ("raw", "centred")}, indent=1))
    print(json.dumps(summ["raw"]["null"]["per_bin"], indent=1))
    return summ


if __name__ == "__main__":
    main()
