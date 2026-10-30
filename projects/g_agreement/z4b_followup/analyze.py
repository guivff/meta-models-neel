"""Z4b — where in the ownership prompt does the L38 swap act, and did the binding sit on the names/objects earlier?
(BRIEF_Z deviation 2026-10-09 "Z4b ownership follow-up", PRE-REGISTERED; plus the "NLA reproduction gate" summary.)

CPU only. Inputs:
  cache/g_agreement/z/z4b_behaviour.jsonl  one row per (item, arm, layer) at α 1 {key = pair|source|Z4b|arm|1.0|L<layer>; arm, edit_layer,
                                           positions, flipped_to_other, kept_original, coherent, lo_model}
  cache/g_agreement/z/z4b_lo.jsonl         J-lens / Oracle-lens LO on the read-back block-42 vectors {entry_key, reader, lo_toward_other}
  cache/g_agreement/x/x2_behaviour.jsonl   natural rows (Δ_model baseline) and the X2 S2 planted α 1 rows (all positions at L38 = R_all, measured);
                                           x2_lo.jsonl the readers' natural LO (separation sep_r of each pair)
  cache/g_agreement/y/y2_behaviour.jsonl   L38 references: name_only and name_removed at α 1 (Y2; pre-registered 0/64 and 64/64 if absent)
  results/g_agreement/z4b/nla_gate.json    the NLA reproduction gate (reported if present)
Per arm × layer: flip = flipped_to_other ∧ coherent (Wilson 95% CI; pair bootstrap alongside), coherence, mean Δ_model = lo_model(entry) −
lo_model(X2 natural, same state) (pair bootstrap 1,000, seed 0), and per reader the mean fraction of its own separation
f_r = (lo_r(entry) − lo_r(natural)) / sep_r (Z1/Z4 definition, pair bootstrap).
DECISION (pre-registered): an L38 arm reaching ≥ 0.8·R_all (R_all = 1.00, ownership, all positions at L38) LOCATES the answer;
"the binding moved" if names_objects_only flips ≥ 0.5 at layer 20 or 28 while it flips 0 at layer 38 (Y2 name_only α 1: 0/64).
Outputs results/g_agreement/z4b/{z4b.md, z4b.csv, z4b_summary.json, fig_main.png}. Nothing is written to writeup.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.z4_positions import analyze as ZA  # noqa: E402

MODULE = "z4b"
FAMILY = "ownership"
L38 = 38
EARLY_LAYERS = (20, 28)
L38_ARMS = ("question_only", "template_only", "last3", "question_first_half", "question_second_half")
NAMES_ARM = "names_objects_only"
ARM_LABELS = {"question_only": "question only", "template_only": "template only", "last3": "last 3", "question_first_half": "question 1st half",
              "question_second_half": "question 2nd half", NAMES_ARM: "names/objects only", "name_only": "names/objects only", "name_removed": "all but names/objects"}
R_ALL_PREREG = 1.00
LOCATE_FRAC = 0.8
MOVED_FLIP = 0.5
EPS = 1e-12
Y2_PREREG = {"name_only": (0, 64), "name_removed": (64, 64)}
REF_ALPHA = 1.0
TICK_LABELS = {"question_only": "question\nonly", "template_only": "template\nonly", "last3": "last 3\ntokens", "question_first_half": "question\n1st half",
               "question_second_half": "question\n2nd half"}
CACHE = ROOT / "cache" / "g_agreement"
C_L38, C_EARLY, C_REF = "#2a78d6", "#eb6834", "#52514e"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--behaviour", default=str(CACHE / "z" / "z4b_behaviour.jsonl"))
    ap.add_argument("--lo", default=str(CACHE / "z" / "z4b_lo.jsonl"))
    ap.add_argument("--x2-behaviour", default=str(CACHE / "x" / "x2_behaviour.jsonl"))
    ap.add_argument("--x2-lo", default=str(CACHE / "x" / "x2_lo.jsonl"))
    ap.add_argument("--y2-behaviour", default=str(CACHE / "y" / "y2_behaviour.jsonl"))
    ap.add_argument("--y2-lo", default=str(CACHE / "y" / "y2_lo.jsonl"))
    ap.add_argument("--gate", default=str(U.DEFAULTS["results_dir"] / MODULE / "nla_gate.json"))
    ap.add_argument("--spans", default=str(U.DEFAULTS["results_dir"] / MODULE / "spans.json"))
    ap.add_argument("--frozen-config", default=str(U.G_DIR / "manifest" / "frozen_config_z.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ cells
def cell(w: dict, rs: List[dict], nb: int, sd: int, readers: List[str]) -> dict:
    """ZA.cell_stats (Wilson + pair-bootstrap flip, coherence, Δ_model, reader f_r) + the mean number of edited positions."""
    if not rs:
        return {"n": 0, "missing": True}
    c = ZA.cell_stats(w, rs, nb, sd, readers)
    npos = [r.get("n_positions") for r in rs if r.get("n_positions") is not None]
    c["mean_n_positions"] = float(np.mean(npos)) if npos else None
    c["missing"] = False
    return c


def flip_p(c: Optional[dict]) -> float:
    return float("nan") if not c or not c.get("n") else float(c["flip"]["p"])


def decide(cells: Dict[str, dict], refs: Dict[str, dict], r_all: float = R_ALL_PREREG) -> dict:
    """The pre-registered decision on the L38 arms and on names_objects_only at L20/L28."""
    bar = LOCATE_FRAC * r_all
    arms = {}
    for arm in L38_ARMS:
        c = cells.get(f"{arm}@L{L38}")
        p = flip_p(c)
        arms[arm] = {"flip": p, "k": (c or {}).get("flip", {}).get("k"), "n": (c or {}).get("n", 0),
                     "locates": None if np.isnan(p) else bool(p >= bar - EPS)}
    locating = [a for a in L38_ARMS if arms[a]["locates"]]
    early = {L: flip_p(cells.get(f"{NAMES_ARM}@L{L}")) for L in EARLY_LAYERS}
    l38 = refs.get("name_only")
    l38_k, l38_n = (l38["flip"]["k"], l38["n"]) if l38 and l38.get("n") else Y2_PREREG["name_only"]
    l38_src = "Y2 data" if l38 and l38.get("n") else "pre-registered (Y2 not loaded)"
    have_early = [L for L, p in early.items() if not np.isnan(p)]
    moved_layers = [L for L in have_early if early[L] >= MOVED_FLIP - EPS]
    moved = bool(moved_layers) and l38_k == 0
    lines = [f"Bar: 0.8·R_all = {bar:.2f} (R_all = {r_all:.2f}, ownership, all positions at L38, pre-registered)."]
    for a in L38_ARMS:
        x = arms[a]
        if x["locates"] is None:
            lines.append(f"- {a}: no rows.")
        else:
            lines.append(f"- {a}: {x['k']}/{x['n']} = {x['flip']:.2f} → " + ("reaches the bar: LOCATES the answer." if x["locates"] else "below the bar."))
    if locating:
        lines.append(f"L38 verdict: the answer is located by {', '.join(locating)}.")
    elif any(arms[a]["locates"] is not None for a in L38_ARMS):
        lines.append("L38 verdict: no role-defined span alone reaches 0.8·R_all.")
    if not have_early:
        lines.append("Binding verdict: no names_objects_only rows at L20/L28.")
    elif moved:
        lines.append(f"Binding verdict: THE BINDING MOVED — names_objects_only flips ≥ {MOVED_FLIP} at L{', L'.join(str(L) for L in moved_layers)} "
                     f"({', '.join(f'L{L} {early[L]:.2f}' for L in have_early)}) while it flips {l38_k}/{l38_n} at L38 ({l38_src}).")
    else:
        why = (f"names_objects_only flips {', '.join(f'L{L} {early[L]:.2f}' for L in have_early)} (< {MOVED_FLIP})" if not moved_layers
               else f"L38 names-only is {l38_k}/{l38_n}, not 0")
        lines.append(f"Binding verdict: the binding did NOT move by the pre-registered rule — {why}.")
    return {"bar": bar, "r_all_prereg": r_all, "arms": arms, "locating_arms": locating, "names_flip_early": {str(L): early[L] for L in EARLY_LAYERS},
            "names_l38": {"k": l38_k, "n": l38_n, "source": l38_src}, "binding_moved": moved if have_early else None, "moved_layers": moved_layers, "text": lines}


def csv_row(label: str, arm: str, layer, source: str, c: dict, readers: List[str], locates=None) -> dict:
    row: Dict[str, Any] = {"cell": label, "arm": arm, "layer": layer, "alpha": REF_ALPHA, "source": source, "n": c.get("n", 0)}
    if not c.get("n"):
        return row
    row.update(n_pairs=c["n_pairs"], mean_n_positions=c.get("mean_n_positions"), k_flip=c["flip"]["k"], flip=c["flip"]["p"], flip_wilson_lo=c["flip"]["lo"],
               flip_wilson_hi=c["flip"]["hi"], flip_boot_lo=c["flip_boot"]["lo"], flip_boot_hi=c["flip_boot"]["hi"], coherence=c["coherence"]["p"],
               dmodel_mean=c["d_model"]["mean"], dmodel_lo=c["d_model"]["lo"], dmodel_hi=c["d_model"]["hi"], n_dmodel=c["d_model"]["n"], locates=locates)
    for rd in readers:
        q = c["readers"].get(rd, {})
        row[f"f_{rd}_mean"], row[f"f_{rd}_lo"], row[f"f_{rd}_hi"], row[f"f_{rd}_n"] = q.get("mean"), q.get("lo"), q.get("hi"), q.get("n")
    return row


# ------------------------------------------------------------------ run
def run(args: argparse.Namespace) -> dict:
    frozen, _ = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if frozen else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    nb, sd = args.n_boot, args.seed
    w = ZA.load_world(args)
    z_lo_readers = {r["reader"] for r in U.load_jsonl(args.lo)} if Path(args.lo).exists() else set()
    readers = [rd for rd in ZA.READERS if rd in w["readers"] and rd in z_lo_readers]
    zrows = [r for r in w["rows"] if not r["reused"]]
    fams = sorted({r["family"] for r in zrows})
    if fams != [FAMILY]:
        raise U.AnalysisError(f"Z4b rows must be ownership only, got {fams}")
    reused = [r for r in w["rows"] if r["reused"] and float(r["alpha"]) == REF_ALPHA and r["family"] == FAMILY]
    U.log(f"[z4b] frozen={frozen} {len(zrows)} Z4b entries / {len(w['items'])} items; readers {readers}; {len(reused)} Y2 reference rows at α 1; "
          f"{len(w['ref'])} X2 all-position rows; {w['n_missing_nat']} items without a natural row; out={out}")
    cells: Dict[str, dict] = {}
    for arm in L38_ARMS:
        cells[f"{arm}@L{L38}"] = cell(w, [r for r in zrows if r["arm"] == arm and int(r["edit_layer"]) == L38], nb, sd, readers)
    for L in EARLY_LAYERS:
        cells[f"{NAMES_ARM}@L{L}"] = cell(w, [r for r in zrows if r["arm"] == NAMES_ARM and int(r["edit_layer"]) == L], nb, sd, readers)
    other = sorted({f"{r['arm']}@L{r['edit_layer']}" for r in zrows} - set(cells))
    if other:
        raise U.AnalysisError(f"unexpected arm × layer cells {other}")
    refs = {cond: cell(w, [r for r in reused if r["condition"] == cond], nb, sd, readers) for cond in ("name_only", "name_removed")}
    refs["all_positions"] = cell(w, [r for r in w["ref"] if r["family"] == FAMILY], nb, sd, readers)
    r_all_measured = flip_p(refs["all_positions"])
    dec = decide(cells, refs)
    gate = U.load_json(args.gate) if args.gate and Path(args.gate).exists() else None
    spans = U.load_json(args.spans) if args.spans and Path(args.spans).exists() else None
    summary = {"module": MODULE, "frozen": frozen, "n_entries": len(zrows), "n_items": len({(r["pair_id"], r["source"]) for r in zrows}),
               "n_pairs": len({r["pair_id"] for r in zrows}), "n_boot": nb, "seed": sd, "readers": readers, "alpha": REF_ALPHA,
               "orientation": "positive = toward the other candidate; Δ_model = lo_model(entry) − lo_model(X2 natural); f_r = (lo_r(entry) − lo_r(natural)) / sep_r",
               "r_all_prereg": R_ALL_PREREG, "r_all_measured_x2_s2": r_all_measured, "cells": cells, "references": refs, "decision": dec,
               "nla_gate": None if gate is None else {"verdict": gate.get("verdict"), "consequence": gate.get("consequence"),
                                                       "families": {f: {"gate_win": v["gate_win"], "x1_win": v.get("x1_win"),
                                                                        "median_abs_dlo": v["compare"]["median_abs_dlo"], "sign_agreement": v["compare"]["sign_agreement"]}
                                                                    for f, v in gate.get("families", {}).items()}},
               "spans_summary": None if spans is None else spans.get("summary")}
    rows = [csv_row(k, k.split("@")[0], int(k.split("@L")[1]), "z4b", c, readers, locates=dec["arms"].get(k.split("@")[0], {}).get("locates") if k.endswith(f"@L{L38}") else None)
            for k, c in cells.items()]
    rows += [csv_row(f"{cond}@L{L38}", cond, L38, "y2_reference", refs[cond], readers) for cond in ("name_only", "name_removed")]
    rows.append(csv_row(f"all_positions@L{L38}", "all_positions", L38, "x2_s2_reference", refs["all_positions"], readers))
    cols = ["cell", "arm", "layer", "alpha", "source", "n", "n_pairs", "mean_n_positions", "k_flip", "flip", "flip_wilson_lo", "flip_wilson_hi", "flip_boot_lo",
            "flip_boot_hi", "coherence", "dmodel_mean", "dmodel_lo", "dmodel_hi", "n_dmodel", "locates"]
    for rd in readers:
        cols += [f"f_{rd}_mean", f"f_{rd}_lo", f"f_{rd}_hi", f"f_{rd}_n"]
    U.write_csv(out / "z4b.csv", rows, cols)
    U.write_json(out / "z4b_summary.json", summary)
    write_md(out / "z4b.md", summary)
    if not args.no_fig:
        make_fig(out / "fig_main.png", summary, frozen)
    for line in dec["text"]:
        U.log("[z4b] " + line)
    if gate:
        U.log(f"[z4b] NLA gate: {gate.get('verdict')}")
    return summary


# ------------------------------------------------------------------ outputs
def _ci(c: dict) -> str:
    if not c or not c.get("n"):
        return "–"
    f = c["flip"]
    return f"{f['k']}/{f['n']} = {f['p']:.2f} [{f['lo']:.2f}, {f['hi']:.2f}]"


def _m(d: Optional[dict]) -> str:
    if not d or d.get("n", 0) == 0 or d.get("mean") is None or np.isnan(d["mean"]):
        return "–"
    return f"{d['mean']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}]"


def write_md(path: Path, s: dict) -> None:
    rd = s["readers"]
    L: List[str] = [f"# Z4b — ownership follow-up{'' if s['frozen'] else ' (UNFROZEN DEV RUN)'}", "",
                    "Pre-registered in BRIEF_Z (deviation 2026-10-09, before collection). 32 ownership pairs × both sources, α 1 "
                    "(h' = h_A + (h_B − h_A) at the arm's positions). Flip = parsed answer is the other candidate and coherent. "
                    "Δ_model = lo_model − X2 natural lo_model of the same state (nats, toward the other candidate). "
                    "f_r = reader r's LO shift as a fraction of its own natural separation of the pair.", "",
                    f"R_all (pre-registered) = {s['r_all_prereg']:.2f}; measured X2 S2 α 1 all positions = {s['r_all_measured_x2_s2']:.2f}.", "",
                    "| cell | n | mean #pos | flip (Wilson 95%) | coherence | mean Δ_model [pair boot] | " + " | ".join(f"f {ZA.READER_LABELS.get(r, r)}" for r in rd) + " |",
                    "|---|---|---|---|---|---|" + "---|" * len(rd)]

    def line(name: str, c: dict) -> str:
        if not c or not c.get("n"):
            return f"| {name} | 0 | – | – | – | – |" + " – |" * len(rd)
        mp = c.get("mean_n_positions")
        return (f"| {name} | {c['n']} | {'–' if mp is None else f'{mp:.1f}'} | {_ci(c)} | {c['coherence']['p']:.2f} | {_m(c['d_model'])} | "
                + " | ".join(_m(c["readers"].get(r)) for r in rd) + " |")

    for k, c in s["cells"].items():
        L.append(line(k, c))
    for k, lab in (("name_only", "names/objects only @L38 (Y2)"), ("name_removed", "all but names/objects @L38 (Y2)"), ("all_positions", "all positions @L38 (X2 S2)")):
        L.append(line(lab, s["references"][k]))
    L += ["", "## Decision (pre-registered)", ""] + s["decision"]["text"]
    L += ["", "## NLA reproduction gate", ""]
    g = s.get("nla_gate")
    if not g:
        L.append("Not run yet (phase B `--nla-x1-check`). Until it passes, no Z4 NLA number is reported.")
    else:
        L.append(f"Verdict: **{g['verdict']}** — {g['consequence']}. Gate: within-pair win (X1 E1) within 0.72 ± 0.05 on ownership and on mapping.")
        L.append("")
        L.append("| family | gate win | X1 win | median abs Δlo vs X1 | sign agreement |")
        L.append("|---|---|---|---|---|")
        for f, v in g["families"].items():
            gw, xw = v["gate_win"], v.get("x1_win")
            fx = lambda q: "–" if not q or not q.get("n") else f"{q['k']}/{q['n']} = {q['p']:.3f}"  # noqa: E731
            num = lambda x: "–" if x is None else f"{x:.3f}"  # noqa: E731
            L.append(f"| {f} | {fx(gw)} | {fx(xw)} | {num(v['median_abs_dlo'])} | {num(v['sign_agreement'])} |")
    if s.get("spans_summary"):
        L += ["", "## Spans", "", "```", json.dumps(s["spans_summary"], indent=1), "```"]
    L += ["", "Nothing from Z4b is written into writeup.md by this script."]
    path.write_text("\n".join(L) + "\n")


def _rate(c: dict) -> U.Rate:
    if not c or not c.get("n"):
        return U.Rate(0, 0, float("nan"), float("nan"), float("nan"), 0, "wilson")
    f = c["flip"]
    return U.Rate(f["k"], f["n"], f["p"], f["lo"], f["hi"], c.get("n_pairs", 0), "wilson")


def make_fig(path: Path, s: dict, frozen: bool) -> None:
    """One panel: flip rate (Wilson 95% CI, k/n printed) per arm. L38 arms grouped; names/objects-only at L20 / L28 next to the
    L38 references from Y2 (names/objects only, all but names/objects; hollow) and the X2 all-position reference (hollow)."""
    from matplotlib.patches import Patch

    plt = U.mpl()
    fig, ax = plt.subplots(figsize=(12, 4.8))
    bars = [(TICK_LABELS[a], s["cells"][f"{a}@L{L38}"], C_L38, False) for a in L38_ARMS]
    x = list(range(len(bars)))
    gap = len(bars) + 0.8
    right = [(f"names/objects\nonly, L{L}", s["cells"][f"{NAMES_ARM}@L{L}"], C_EARLY, False) for L in EARLY_LAYERS]
    right += [("names/objects\nonly, L38\n(Y2)", s["references"]["name_only"], C_REF, True),
              ("all but\nnames/objects,\nL38 (Y2)", s["references"]["name_removed"], C_REF, True),
              ("all positions,\nL38 (X2)", s["references"]["all_positions"], C_REF, True)]
    x += [gap + i for i in range(len(right))]
    for xi, (lab, c, col, hollow) in zip(x, bars + right):
        if c and c.get("n"):
            U.bar_ci(ax, xi, _rate(c), col, width=0.62, hollow=hollow)
        else:
            ax.text(xi, 0.02, "n/a", ha="center", va="bottom", fontsize=7.5, color=U.INK2)
    bar = s["decision"]["bar"]
    import matplotlib.transforms as mtransforms

    right_edge = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
    ax.plot([-0.5, len(bars) - 0.5], [bar, bar], color=U.INK2, lw=1, ls="--", zorder=2)
    ax.text(1.005, bar, f"0.8·R_all = {bar:.2f}\n(L38 span locates)", ha="left", va="center", fontsize=7.5, color=U.INK2, transform=right_edge)
    ax.plot([gap - 0.5, gap + len(EARLY_LAYERS) - 0.5], [MOVED_FLIP, MOVED_FLIP], color=U.INK2, lw=1, ls=":", zorder=2)
    ax.text(1.005, MOVED_FLIP, f"{MOVED_FLIP:.1f}\n(binding moved\nat L20/L28)", ha="left", va="center", fontsize=7.5, color=U.INK2, transform=right_edge)
    ax.set_xticks(x)
    ax.set_xticklabels([b[0] for b in bars + right], fontsize=7.5)
    ax.set_xlim(-0.6, x[-1] + 0.6)
    U.style_ax(ax, ylabel="flip to the other candidate (%)", ylim=(0, 1.12))
    ax.text((len(bars) - 1) / 2, -0.25, "layer 38 spans (α 1)", ha="center", va="top", fontsize=8.5, transform=ax.get_xaxis_transform())
    ax.text(gap + (len(right) - 1) / 2, -0.25, "names/objects at L20 / L28, next to the L38 references", ha="center", va="top", fontsize=8.5,
            transform=ax.get_xaxis_transform())
    ax.legend(handles=[Patch(color=C_L38, label="L38 span edit (Z4b)"), Patch(color=C_EARLY, label="names/objects edit at L20 / L28 (Z4b)"),
                       Patch(facecolor="none", edgecolor=C_REF, label="reference from earlier runs (Y2 / X2)")], fontsize=7.5, loc="lower center",
              bbox_to_anchor=(0.5, 1.0), ncol=3)
    ttl = ("UNFROZEN DEV RUN — " if not frozen else "") + f"Z4b ownership follow-up: flip rate per arm, {s['n_pairs']} pairs × 2 sources, Wilson 95% CI"
    ax.set_title(ttl, fontsize=9.5, pad=24)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
