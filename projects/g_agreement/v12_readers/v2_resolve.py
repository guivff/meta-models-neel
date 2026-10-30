"""V2 — re-solving test on the 297 puzzle ERRORS at layers 42 and 48 (PREREG_WV.md Part V, V2).

Two-candidate scoring on ERROR: the candidates are (actual = the model's wrong answer, other = the CORRECT answer), so
    P(favours correct) = P(lo_actual < 0),  P(favours actual) = P(lo_actual > 0),  P(correct) = 1 - P(actual) - P(tie).
(The identity P(correct) = 1 - P(actual) holds exactly when there are no ties; ties (lo == 0) are reported.)
Rule: a reader "re-solves" if P(correct) - P(actual) >= 0.15 with the paired item-bootstrap CI excluding 0.
Permutation null: shuffle the candidate labels within each item (= an independent sign flip of each item's log-odds),
200 permutations, two-sided p for the statistic P(correct) - P(actual).
Control: ERROR_CONTROL (103 correct puzzles; candidates (correct = the model's answer, most frequent wrong symbol)) — the
same reader's preference for the correct symbol when the model was right.
Third candidate (k-1 "stopped one step early" symbol): on 151/297 errors the model's actual answer IS the k-1 symbol, so the
three-way preference there collapses to the two-way one (segment "actual = k-1"). On the other 146 the k-1 symbol is a
third string that no cached reader call has scored: it is requested from the pod (v12_pod_requests.json, request
"three_way") and ingested with ``--three-way <file>`` (rows: reader, site, item_id, candidates{correct, actual, km1},
lp{correct, actual, km1}, unscorable).

Run: .venv/bin/python -m projects.g_agreement.v12_readers.v2_resolve [--extra-lo FILE] [--three-way FILE] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.v12_readers import common as K  # noqa: E402

V2_LAYERS = (42, 48)
SUBSETS = ("all", "km1_eq_actual", "km1_ne_actual")
SEG_COLORS = {"correct": "#1baf7a", "actual": "#d1495b", "km1": "#8d99ae", "tie": "#e4e3df", "pending": "#fcfcfb", "other_wrong": "#f6b99a"}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(K.DEFAULTS["items"]))
    ap.add_argument("--x3-lo", default=str(K.DEFAULTS["x3_lo"]))
    ap.add_argument("--y1-lo", default=str(K.DEFAULTS["y1_lo"]))
    ap.add_argument("--extra-lo", action="append", default=[], help="pod rows (y1_lo schema, site '<L>:0'); repeatable")
    ap.add_argument("--three-way", action="append", default=[], help="pod three-way rows (see module doc); repeatable")
    ap.add_argument("--layers", default=",".join(map(str, V2_LAYERS)))
    ap.add_argument("--readers", default="jlens,olens,nla")
    ap.add_argument("--out-dir", default=str(K.DEFAULTS["out_dir"]))
    ap.add_argument("--n-boot", type=int, default=K.N_BOOT)
    ap.add_argument("--n-perm", type=int, default=K.N_PERM)
    ap.add_argument("--seed", type=int, default=K.SEED)
    ap.add_argument("--gap", type=float, default=K.RESOLVE_GAP)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ two-way
def two_way(rows: Sequence[dict], *, n_boot: int, n_perm: int, seed: int, gap: float) -> dict:
    """rows: scorable error rows of one reader at one layer (any subset). P(correct)=lo<0, P(actual)=lo>0."""
    lo = np.asarray([r["lo_actual"] for r in rows], dtype=float)
    fc = lo < 0
    fa = lo > 0
    rc, ra = K.rate(fc, n_boot, seed), K.rate(fa, n_boot, seed)
    d = K.paired_diff(fc, fa, n_boot, seed)
    perm = K.permutation_null(lo, n_perm=n_perm, seed=seed)
    resolves = bool(lo.size and d["diff"] >= gap and d["diff_lo"] > 0)
    return {"n": int(lo.size), "n_ties": int((lo == 0).sum()), "correct": rc, "actual": ra, **d, "perm": perm, "resolves": resolves,
            "mean_lo_actual": (float(lo.mean()) if lo.size else float("nan"))}


def control_two_way(rows: Sequence[dict], *, n_boot: int, seed: int) -> dict:
    """ERROR_CONTROL rows: cand_actual == correct, so P(correct) = lo > 0 and the other candidate is a wrong symbol."""
    lo = np.asarray([r["lo_actual"] for r in rows], dtype=float)
    return {"n": int(lo.size), "n_ties": int((lo == 0).sum()), "correct": K.rate(lo > 0, n_boot, seed), "other_wrong": K.rate(lo < 0, n_boot, seed),
            "mean_lo_correct": (float(lo.mean()) if lo.size else float("nan"))}


# ------------------------------------------------------------------ three-way
def load_three_way(paths: Sequence[Path | str]) -> Dict[tuple, dict]:
    out: Dict[tuple, dict] = {}
    for p in paths:
        for r in K.read_jsonl(p):
            if r.get("unscorable") or not isinstance(r.get("lp"), Mapping):
                continue
            site = r.get("site") or f"{r.get('layer')}:0"
            out[(r["reader"], site, r["item_id"])] = r
    return out


def three_way_pref(lp: Mapping[str, float]) -> str:
    vals = {k: lp[k] for k in ("correct", "actual", "km1") if lp.get(k) is not None}
    if not vals:
        return "unscorable"
    best = max(vals.values())
    top = [k for k, v in vals.items() if v == best]
    return top[0] if len(top) == 1 else "tie"


def three_way(items: Mapping[str, dict], rows: Sequence[dict], tw: Mapping[tuple, dict], reader: str, layer: int) -> dict:
    """Per-item three-way preference over the 297 errors: derived from the two-way rows where actual == k-1, from the pod
    three-way rows elsewhere, else 'pending'."""
    counts = {"correct": 0, "actual": 0, "km1": 0, "actual_is_km1": 0, "tie": 0, "pending": 0}
    by = {r["item_id"]: r for r in rows}
    for iid, it in items.items():
        if it.get("set") != "error":
            continue
        ro = it["roles"]
        r = by.get(iid)
        if ro["km1"] == ro["actual"]:
            if r is None or r["unscorable"]:
                counts["pending"] += 1
            elif r["lo_actual"] > 0:
                counts["actual_is_km1"] += 1
            elif r["lo_actual"] < 0:
                counts["correct"] += 1
            else:
                counts["tie"] += 1
            continue
        t = tw.get((reader, f"{layer}:0", iid))
        if t is None:
            counts["pending"] += 1
        else:
            counts[three_way_pref(t["lp"])] = counts.get(three_way_pref(t["lp"]), 0) + 1
    n = sum(counts.values())
    return {"counts": counts, "n": n, "n_pending": counts["pending"], "complete": counts["pending"] == 0}


# ------------------------------------------------------------------ driver
def analyse(items: Mapping[str, dict], rows: Sequence[dict], tw: Mapping[tuple, dict], *, readers: Sequence[str], layers: Sequence[int],
            n_boot: int, n_perm: int, seed: int, gap: float) -> dict:
    res: Dict[str, Any] = {"layers": list(layers), "readers": list(readers), "gap": gap, "n_boot": n_boot, "n_perm": n_perm, "seed": seed,
                           "item_counts": K.check_item_roles(items), "cells": {}}
    for rd in readers:
        for L in layers:
            err = [r for r in K.select_rows(rows, reader=rd, set_="error", layer=L) if not r["unscorable"]]
            ctl = [r for r in K.select_rows(rows, reader=rd, set_="error_control", layer=L) if not r["unscorable"]]
            n_unsc = len(K.select_rows(rows, reader=rd, set_="error", layer=L)) - len(err)
            if not err:
                res["cells"][f"{rd}@{L}"] = {"reader": rd, "layer": L, "available": False}
                continue
            cell: Dict[str, Any] = {"reader": rd, "layer": L, "available": True, "n_unscorable": n_unsc,
                                    "source": ",".join(sorted({r["source"] for r in err})), "subsets": {}}
            for sub in SUBSETS:
                if sub == "all":
                    sel = err
                elif sub == "km1_eq_actual":
                    sel = [r for r in err if items[r["item_id"]]["roles"]["km1"] == r["cand_actual"]]
                else:
                    sel = [r for r in err if items[r["item_id"]]["roles"]["km1"] != r["cand_actual"]]
                cell["subsets"][sub] = two_way(sel, n_boot=n_boot, n_perm=n_perm, seed=seed, gap=gap)
            cell["control"] = control_two_way(ctl, n_boot=n_boot, seed=seed)
            cell["three_way"] = three_way(items, err, tw, rd, L)
            res["cells"][f"{rd}@{L}"] = cell
    return res


def csv_rows(res: Mapping[str, Any]) -> List[dict]:
    out = []
    for key, c in res["cells"].items():
        if not c.get("available"):
            out.append({"reader": c["reader"], "layer": c["layer"], "subset": "all", "available": False})
            continue
        for sub, d in c["subsets"].items():
            out.append({"reader": c["reader"], "layer": c["layer"], "subset": sub, "available": True, "source": c["source"], "n": d["n"], "n_ties": d["n_ties"],
                        "k_correct": d["correct"]["k"], "p_correct": d["correct"]["p"], "correct_lo": d["correct"]["boot_lo"], "correct_hi": d["correct"]["boot_hi"],
                        "k_actual": d["actual"]["k"], "p_actual": d["actual"]["p"], "actual_lo": d["actual"]["boot_lo"], "actual_hi": d["actual"]["boot_hi"],
                        "diff_correct_minus_actual": d["diff"], "diff_lo": d["diff_lo"], "diff_hi": d["diff_hi"],
                        "perm_p": d["perm"]["p_value"], "perm_null_abs_p95": d["perm"]["null_abs_p95"], "n_perm": d["perm"]["n_perm"],
                        "resolves": d["resolves"], "mean_lo_actual": d["mean_lo_actual"]})
        k = c["control"]
        out.append({"reader": c["reader"], "layer": c["layer"], "subset": "error_control", "available": True, "source": c["source"], "n": k["n"], "n_ties": k["n_ties"],
                    "k_correct": k["correct"]["k"], "p_correct": k["correct"]["p"], "correct_lo": k["correct"]["boot_lo"], "correct_hi": k["correct"]["boot_hi"],
                    "k_actual": None, "p_actual": None, "mean_lo_actual": k["mean_lo_correct"]})
        t = c["three_way"]
        out.append({"reader": c["reader"], "layer": c["layer"], "subset": "three_way_counts", "available": t["complete"], "n": t["n"],
                    **{f"tw_{kk}": v for kk, v in t["counts"].items()}})
    return out


# ------------------------------------------------------------------ figure
def make_figure(path: Path, res: Mapping[str, Any]) -> None:
    """Per reader: at each layer an ERROR bar (two-way stack over all 297 items, split by whether the actual answer is the k-1
    symbol), a 3-WAY bar once the pod's third-candidate rows exist (hatched 'pending' until then), and the CONTROL bar."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    plt.rcParams.update({"figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb", "font.size": 9.5,
                         "axes.titlesize": 10.5, "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False,
                         "legend.frameon": False})
    readers, layers = res["readers"], res["layers"]
    fig, axes = plt.subplots(1, len(readers), figsize=(4.3 * len(readers), 5.0), sharey=True)
    W = 0.72

    def stack(ax, x, segs, n):
        bottom = 0.0
        for cnt, col, hatch, txtcol in segs:
            h = cnt / n if n else 0
            if h <= 0:
                continue
            ax.bar(x, h, bottom=bottom, width=W, color=col, edgecolor="#fcfcfb" if hatch != "xx" else "#52514e", lw=0.8, hatch=hatch, zorder=3)
            if h > 0.07:
                ax.text(x, bottom + h / 2, f"{cnt}", ha="center", va="center", fontsize=7.5, color=txtcol)
            bottom += h

    def ci(ax, x, r):
        ax.errorbar([x], [r["p"]], yerr=[[max(r["p"] - r["boot_lo"], 0)], [max(r["boot_hi"] - r["p"], 0)]], color="#0b0b0b", marker="_", ms=9,
                    lw=1.1, capsize=3, zorder=5)

    for ax, rd in zip(np.atleast_1d(axes), readers):
        ax.grid(axis="y", color="#e4e3df", lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        xs, labels, lines, groups = [], [], [], []
        x = 0.0
        for L in layers:
            c = res["cells"].get(f"{rd}@{L}")
            if not c or not c.get("available"):
                xs.append(x); labels.append(f"L{L}\nno rows"); x += 3.2
                continue
            d_all, d_eq, d_ne = (c["subsets"][k] for k in ("all", "km1_eq_actual", "km1_ne_actual"))
            n = d_all["n"]
            stack(ax, x, [(d_ne["correct"]["k"], SEG_COLORS["correct"], None, "#fcfcfb"), (d_eq["correct"]["k"], SEG_COLORS["correct"], "//", "#fcfcfb"),
                          (d_ne["actual"]["k"], SEG_COLORS["actual"], None, "#fcfcfb"), (d_eq["actual"]["k"], SEG_COLORS["actual"], "//", "#fcfcfb"),
                          (d_all["n_ties"], SEG_COLORS["tie"], None, "#0b0b0b")], n)
            ci(ax, x + W / 2 + 0.12, d_all["correct"])
            xs.append(x); labels.append(f"2-way\nn={n}")
            gx0 = x
            x += 1.05
            t = c["three_way"]["counts"]
            tn = c["three_way"]["n"]
            stack(ax, x, [(t["correct"], SEG_COLORS["correct"], None, "#fcfcfb"), (t["actual"], SEG_COLORS["actual"], None, "#fcfcfb"),
                          (t["actual_is_km1"], SEG_COLORS["actual"], "//", "#fcfcfb"), (t["km1"], SEG_COLORS["km1"], None, "#fcfcfb"),
                          (t["tie"], SEG_COLORS["tie"], None, "#0b0b0b"), (t["pending"], SEG_COLORS["pending"], "xx", "#0b0b0b")], tn)
            xs.append(x); labels.append("3-way\n(k−1)")
            x += 1.05
            k = c["control"]
            if k["n"]:
                stack(ax, x, [(k["correct"]["k"], SEG_COLORS["correct"], None, "#fcfcfb"), (k["other_wrong"]["k"], SEG_COLORS["other_wrong"], None, "#0b0b0b"),
                              (k["n_ties"], SEG_COLORS["tie"], None, "#0b0b0b")], k["n"])
                ci(ax, x + W / 2 + 0.12, k["correct"])
                xs.append(x); labels.append(f"CONTROL\nn={k['n']}")
            groups.append(((gx0 + x) / 2, f"layer {L}"))
            x += 2.1
            lines.append(f"L{L}: Δ = {100 * d_all['diff']:+.0f} [{100 * d_all['diff_lo']:+.0f}, {100 * d_all['diff_hi']:+.0f}], perm p {d_all['perm']['p_value']:.3f}"
                         f" → {'RE-SOLVES' if d_all['resolves'] else 'no'}")
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontsize=7)
        for gx, gl in groups:
            ax.text(gx, -0.16, gl, transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=8, fontweight="bold")
        ax.set_xlim(-0.6, x - 1.5)
        ax.set_ylim(0, 1.3)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0", "25", "50", "75", "100"])
        ax.spines["left"].set_bounds(0, 1.0)
        ax.set_title(K.READER_LABELS[rd].split(" (")[0], pad=4)
        ax.text(0.5, 1.27, "\n".join(lines), transform=ax.get_yaxis_transform(), ha="center", va="top", fontsize=7.6, color="#0b0b0b")
    np.atleast_1d(axes)[0].set_ylabel("% of items the reader prefers\n(CI: 95% item bootstrap of P(correct))")
    handles = [Patch(color=SEG_COLORS["correct"], label="prefers the CORRECT answer"),
               Patch(color=SEG_COLORS["actual"], label="prefers the model's ACTUAL (wrong) answer"),
               Patch(facecolor="#ffffff", hatch="//", edgecolor="#52514e", label="hatched: items whose actual answer IS the k−1 symbol (151)"),
               Patch(color=SEG_COLORS["km1"], label="prefers the k−1 symbol as a third candidate"),
               Patch(facecolor=SEG_COLORS["pending"], hatch="xx", edgecolor="#52514e", label="146 items: third candidate not yet scored (pod)"),
               Patch(color=SEG_COLORS["other_wrong"], label="CONTROL (model correct): prefers the frequent wrong symbol"),
               Patch(color=SEG_COLORS["tie"], label="tie (log-odds = 0)")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=7.2, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(f"V2 — re-solving test on the 297 puzzle errors, Δ = P(correct) − P(actual); rule: Δ ≥ {int(100 * res['gap'])} points with the CI excluding 0",
                 fontsize=10, y=0.995)
    fig.tight_layout(rect=(0, 0.12, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ------------------------------------------------------------------ write-up
def write_md(path: Path, res: Mapping[str, Any], info: Mapping[str, Any]) -> None:
    ic = res["item_counts"]
    L = ["# V2 — re-solving test on the puzzle errors (PREREG_WV.md Part V)\n",
         f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `projects/g_agreement/v12_readers/v2_resolve.py`; "
         f"item bootstrap {res['n_boot']}, permutations {res['n_perm']}, seed {res['seed']}._\n",
         "**Question.** On the 297 puzzle errors, does a reader favour the CORRECT answer over the model's ACTUAL (wrong) answer — i.e. "
         "re-solve the puzzle from the vector rather than read the model's choice?\n",
         "**Identity used.** The ERROR candidates are (actual, other = correct), so in the two-candidate scoring "
         "P(favours correct) = P(lo_actual < 0) and P(favours actual) = P(lo_actual > 0); P(correct) = 1 − P(actual) − P(tie), with ties "
         "(lo = 0) listed. The statistic is Δ = P(correct) − P(actual) with a paired item bootstrap; the permutation null shuffles the two "
         "candidate labels within each item (a sign flip of each item's log-odds), 200 permutations, two-sided p.\n",
         f"**Rule.** A reader re-solves if Δ ≥ {res['gap']:.2f} with the CI excluding 0.\n",
         f"**Third candidate.** The k−1 symbol (one step short of the answer) equals the model's actual answer on {ic['km1_eq_actual']} of "
         f"{ic['error']} errors — there the actual answer IS the k−1 symbol and the three-way preference is the two-way one. On the other "
         f"{ic['km1_ne_actual']} items the k−1 symbol is a third string with no cached log-prob; it is requested from the pod "
         "(`v12_pod_requests.json`, `three_way`) and ingested with `--three-way`.\n",
         "Layer 42 rows are the X3 block-42 last-token states (`x3_lo.jsonl`); layer 48 rows the Y1 re-read at 48:0 (`y1_lo.jsonl`). "
         f"Sources: {'; '.join(f'{s[chr(115)+chr(111)+chr(117)+chr(114)+chr(99)+chr(101)]}: {s[chr(110)+chr(95)+chr(114)+chr(111)+chr(119)+chr(115)]} rows' for s in info['sources'])}.\n",
         "## Two-way preference on ERROR, with the correct-answer control\n",
         "| reader | layer | subset | n (ties) | P(correct) [CI] | P(actual) [CI] | Δ = correct − actual [CI] | perm p (null |Δ| p95) | re-solves? | CONTROL P(correct) [CI] |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for key, c in res["cells"].items():
        if not c.get("available"):
            L.append(f"| {c['reader']} | {c['layer']} | all | no rows | | | | | | |")
            continue
        for sub, d in c["subsets"].items():
            k = c["control"]
            L.append(f"| {c['reader']} | {c['layer']} | {sub} | {d['n']} ({d['n_ties']}) | {K.fmt_rate(d['correct'])} | {K.fmt_rate(d['actual'])} | "
                     f"{100 * d['diff']:+.1f} [{100 * d['diff_lo']:+.0f}, {100 * d['diff_hi']:+.0f}] | {d['perm']['p_value']:.3f} ({100 * d['perm']['null_abs_p95']:.0f}) | "
                     f"{'YES' if d['resolves'] else 'no'} | {K.fmt_rate(k['correct']) if sub == 'all' else ''} |")
    L.append("\n## Three-way preference (correct / actual / k−1)\n")
    L.append("| reader | layer | correct | actual (≠ k−1) | actual (= k−1) | k−1 as third | tie | pending (146-item third candidate) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for key, c in res["cells"].items():
        if not c.get("available"):
            continue
        t = c["three_way"]["counts"]
        L.append(f"| {c['reader']} | {c['layer']} | {t['correct']} | {t['actual']} | {t['actual_is_km1']} | {t['km1']} | {t['tie']} | {t['pending']} |")
    L.append("\nUntil the pod scores the third candidate, the 146 'pending' items are known only as a two-way split (correct vs actual): see the "
             "`km1_ne_actual` rows above.\n")
    L.append("## Verdict\n")
    for key, c in res["cells"].items():
        if not c.get("available"):
            L.append(f"- {c['reader']} @ L{c['layer']}: no rows on the Mac.")
            continue
        d = c["subsets"]["all"]
        k = c["control"]
        word = "RE-SOLVES" if d["resolves"] else ("favours the correct answer but below the 15-point rule" if d["diff"] > 0 and d["diff_lo"] > 0
                                                  else "does not re-solve")
        L.append(f"- {c['reader']} @ L{c['layer']}: P(correct) {100 * d['correct']['p']:.1f}% vs P(actual) {100 * d['actual']['p']:.1f}%, "
                 f"Δ = {100 * d['diff']:+.1f} [{100 * d['diff_lo']:+.0f}, {100 * d['diff_hi']:+.0f}], perm p = {d['perm']['p_value']:.3f} → {word}. "
                 f"Control (model correct): P(correct) {100 * k['correct']['p']:.1f}% [{100 * k['correct']['boot_lo']:.0f}, {100 * k['correct']['boot_hi']:.0f}].")
    # cross-layer consistency note for any reader that meets the rule
    for rd in res["readers"]:
        hits = [L_ for L_ in res["layers"] if (res["cells"].get(f"{rd}@{L_}") or {}).get("available") and res["cells"][f"{rd}@{L_}"]["subsets"]["all"]["resolves"]]
        if hits:
            others = [(L_, res["cells"][f"{rd}@{L_}"]["subsets"]["all"]["diff"]) for L_ in res["layers"]
                      if L_ not in hits and (res["cells"].get(f"{rd}@{L_}") or {}).get("available")]
            L.append(f"\nNote on {rd}: the rule is met at layer(s) {hits} only; at the other scored layer(s) Δ = "
                     + ", ".join(f"L{L_} {100 * d:+.1f}" for L_, d in others)
                     + ". The pre-registration set one rule per reader and layer with no correction over the 3 readers × 2 layers; a sign that "
                       "flips between L42 and L48 is a layer-specific effect, not a stable re-solving behaviour, and the hatched/solid split shows "
                       "where it comes from: " + "; ".join(
                           f"{rd}@L{L_}: Δ = {100 * res['cells'][f'{rd}@{L_}']['subsets']['km1_ne_actual']['diff']:+.1f} on the "
                           f"{res['cells'][f'{rd}@{L_}']['subsets']['km1_ne_actual']['n']} items whose actual answer is NOT the k−1 symbol, "
                           f"{100 * res['cells'][f'{rd}@{L_}']['subsets']['km1_eq_actual']['diff']:+.1f} on the "
                           f"{res['cells'][f'{rd}@{L_}']['subsets']['km1_eq_actual']['n']} where it is" for L_ in hits) + ".")
    L.append("\nReading: a reader whose P(correct) on ERROR is far below its P(correct) on the CONTROL is not solving the puzzle from the vector "
             "either — it tracks neither the model's answer nor the truth reliably on the states where the model errs. The three-way split "
             "is final only after the pod's `three_way` request (146 items × layers 42, 48 × 3 readers).\n")
    L.append("Figure: `fig_v2.png`; table: `v2.csv`.\n")
    path.write_text("\n".join(L))


def run(args: argparse.Namespace) -> dict:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _, items = K.load_items(args.items)
    rows, info = K.load_lo_rows(args.x3_lo, args.y1_lo, args.extra_lo, items=items)
    tw = load_three_way(args.three_way)
    layers = [int(x) for x in args.layers.split(",") if x]
    readers = [x for x in args.readers.split(",") if x]
    res = analyse(items, rows, tw, readers=readers, layers=layers, n_boot=args.n_boot, n_perm=args.n_perm, seed=args.seed, gap=args.gap)
    res["row_sources"] = info
    K.write_csv(out / "v2.csv", csv_rows(res))
    if not args.no_fig:
        make_figure(out / "fig_v2.png", res)
    write_md(out / "v2.md", res, info)
    (out / "v2_summary.json").write_text(json.dumps(res, indent=1, default=_json_default))
    for key, c in res["cells"].items():
        if c.get("available"):
            d = c["subsets"]["all"]
            print(f"[v2] {key:10s} P(correct) {d['correct']['p']:.3f} P(actual) {d['actual']['p']:.3f} diff {d['diff']:+.3f} "
                  f"[{d['diff_lo']:+.3f},{d['diff_hi']:+.3f}] perm p {d['perm']['p_value']:.3f} resolves={d['resolves']} "
                  f"control P(correct) {c['control']['correct']['p']:.3f} three-way pending {c['three_way']['n_pending']}")
    return res


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
