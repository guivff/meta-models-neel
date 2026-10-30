"""V1 — reader layer sweep on the ERROR (297) and DISAGREE (165) sets at the last token (PREREG_WV.md Part V, V1).

The brief wants J-lens, Oracle Lens and the transferred NLA scored at every captured layer 42..62. On the Mac only two
layers exist per reader: 42 (block-42 last-token X3 states, cache/g_agreement/x/x3_lo.jsonl; DISAGREE only on the
33-item X3 subset) and 48 (Y1 re-read at site 48:0, cache/g_agreement/y/y1_lo.jsonl). The remaining layers need the
pod (results/g_agreement/v/v12_pod_requests.json); their rows are ingested with ``--extra-lo <file>`` (y1_lo schema,
site "<L>:0") or by rsyncing them into y1_lo.jsonl.

Pre-registered outcome: (a) a reader crosses P(favours actual) >= 0.75 at some layer <= 62 -> first such layer and
the lag behind the E10 probe's first >= 0.75 layer; (b) none crosses by 62 -> the strong claim stands. A verdict is
only "final" when all 11 layers are scored; otherwise the output says which layers are pending.

Run: .venv/bin/python -m projects.g_agreement.v12_readers.v1_sweep [--extra-lo FILE ...] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.v12_readers import common as K  # noqa: E402

PLOT_READERS = ("jlens", "olens", "nla")
COLORS = {"jlens": "#1baf7a", "olens": "#eb6834", "olens_trueL": "#f4a582", "nla": "#2a78d6", "probe": "#52514e", "logit_lens": "#9a9890"}
MARKERS = {"jlens": "o", "olens": "s", "olens_trueL": "s", "nla": "D"}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(K.DEFAULTS["items"]))
    ap.add_argument("--x3-lo", default=str(K.DEFAULTS["x3_lo"]))
    ap.add_argument("--y1-lo", default=str(K.DEFAULTS["y1_lo"]))
    ap.add_argument("--extra-lo", action="append", default=[], help="pod rows (y1_lo schema, site '<L>:0'); repeatable")
    ap.add_argument("--sweep-dir", default=str(K.DEFAULTS["sweep_dir"]), help="dir with sweep_<set>.csv and logitlens.csv (Y1)")
    ap.add_argument("--out-dir", default=str(K.DEFAULTS["out_dir"]))
    ap.add_argument("--n-boot", type=int, default=K.N_BOOT)
    ap.add_argument("--seed", type=int, default=K.SEED)
    ap.add_argument("--thresh", type=float, default=K.PRESENT_WIN)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


# ------------------------------------------------------------------ analysis
def reader_curve(rows: Sequence[dict], reader: str, set_: str, n_boot: int, seed: int) -> Dict[int, dict]:
    """{layer: rate dict + n_unscorable, n_ties, layer_used, source}} at the last token."""
    out: Dict[int, dict] = {}
    sel = K.select_rows(rows, reader=reader, set_=set_, position="0")
    for L in sorted({r["layer"] for r in sel}):
        rl = [r for r in sel if r["layer"] == L]
        sc = [r for r in rl if not r["unscorable"]]
        flags = [r["lo_actual"] > 0 for r in sc]
        d = K.rate(flags, n_boot=n_boot, seed=seed)
        d.update({"n_unscorable": len(rl) - len(sc), "n_ties": sum(1 for r in sc if r["lo_actual"] == 0),
                  "layer_used": next((r["layer_used"] for r in rl if r["layer_used"] is not None), None),
                  "source": ",".join(sorted({r["source"] for r in rl}))})
        out[L] = d
    return out


def verdict_for(curve: Mapping[int, dict], probe: Mapping[int, dict], layers: Sequence[int], thresh: float) -> dict:
    scored = sorted(L for L in curve if curve[L]["n"] > 0)
    pending = [L for L in layers if L not in scored]
    first = K.first_crossing(curve, thresh)
    first_ci = next((L for L in scored if curve[L]["boot_lo"] >= thresh), None)
    probe_first = K.first_crossing(probe, thresh)
    max_L = max(scored, key=lambda L: curve[L]["p"]) if scored else None
    if first is not None:
        status = "crossed"
    elif pending:
        status = "not crossed at scored layers; pending"
    else:
        status = "no crossing through 62"
    return {"first_layer_ge_thresh": first, "first_layer_ci_lo_ge_thresh": first_ci, "probe_first_layer_ge_thresh": probe_first,
            "lag_layers": (None if first is None or probe_first is None else first - probe_first),
            "layers_scored": scored, "layers_pending": pending, "complete": not pending, "status": status,
            "max_p": (curve[max_L]["p"] if max_L is not None else None), "max_p_layer": max_L}


def analyse(items: Mapping[str, dict], rows: Sequence[dict], sweep_dir: Path, *, n_boot: int, seed: int, thresh: float,
            readers: Sequence[str] = ("jlens", "olens", "olens_trueL", "nla"), layers: Sequence[int] = K.LAYERS) -> dict:
    res: Dict[str, Any] = {"thresh": thresh, "n_boot": n_boot, "seed": seed, "layers": list(layers), "sets": {}}
    for set_ in list(K.MAIN_SETS) + [K.CONTROL_OF[s] for s in K.MAIN_SETS]:
        probe = K.probe_curve(sweep_dir / f"sweep_{set_}.csv") if set_ in K.MAIN_SETS else {}
        if set_ not in K.MAIN_SETS:  # the control's probe rate is carried on the main set's sweep rows
            main = next(m for m, c in K.CONTROL_OF.items() if c == set_)
            pm = K.probe_curve(sweep_dir / f"sweep_{main}.csv")
            probe = {L: {"p": d["control_rate"], "boot_lo": float("nan"), "boot_hi": float("nan"), "n": None, "k": None} for L, d in pm.items()}
        ll = K.logitlens_curve(sweep_dir / "logitlens.csv", set_)
        n_items = sum(1 for it in items.values() if it.get("set") == set_)
        ent: Dict[str, Any] = {"n_items": n_items, "probe": probe, "logit_lens": ll, "readers": {}, "verdict": {}}
        for rd in readers:
            cv = reader_curve(rows, rd, set_, n_boot, seed)
            if not cv:
                continue
            ent["readers"][rd] = cv
            if set_ in K.MAIN_SETS:
                ent["verdict"][rd] = verdict_for(cv, probe, layers, thresh)
        if set_ in K.MAIN_SETS:
            ent["probe_first_layer_ge_thresh"] = K.first_crossing(probe, thresh)
            ent["logit_lens_first_layer_ge_thresh"] = K.first_crossing({L: d for L, d in ll.items() if not d["is_final"]}, thresh)
        res["sets"][set_] = ent
    return res


def csv_rows(res: Mapping[str, Any]) -> List[dict]:
    out = []
    for set_, ent in res["sets"].items():
        for rd, cv in ent["readers"].items():
            for L, d in sorted(cv.items()):
                out.append({"set": set_, "reader": rd, "layer": L, "layer_used": d.get("layer_used"), "source": d.get("source"), "position": "0",
                            "n": d["n"], "k": d["k"], "p_favours_actual": d["p"], "boot_lo": d["boot_lo"], "boot_hi": d["boot_hi"],
                            "wilson_lo": d["wilson_lo"], "wilson_hi": d["wilson_hi"], "n_unscorable": d["n_unscorable"], "n_ties": d["n_ties"]})
        for L, d in sorted(ent["probe"].items()):
            out.append({"set": set_, "reader": "probe_E10", "layer": L, "layer_used": L, "source": "results/g_agreement/y1/sweep_*.csv", "position": "0",
                        "n": d.get("n"), "k": d.get("k"), "p_favours_actual": d["p"], "boot_lo": d["boot_lo"], "boot_hi": d["boot_hi"]})
        for L, d in sorted(ent["logit_lens"].items()):
            out.append({"set": set_, "reader": "logit_lens" + ("_final" if d["is_final"] else ""), "layer": L, "layer_used": L,
                        "source": "results/g_agreement/y1/logitlens.csv", "position": "0", "n": d["n"], "p_favours_actual": d["p"],
                        "boot_lo": d["boot_lo"], "boot_hi": d["boot_hi"]})
    return out


# ------------------------------------------------------------------ figure
def make_figure(path: Path, res: Mapping[str, Any]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb", "font.size": 9.5,
                         "axes.titlesize": 10.5, "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False,
                         "legend.frameon": False})
    layers = res["layers"]
    fig, axes = plt.subplots(1, len(K.MAIN_SETS), figsize=(11.5, 4.4), sharey=True)
    for ax, set_ in zip(np.atleast_1d(axes), K.MAIN_SETS):
        ent = res["sets"][set_]
        ax.grid(axis="y", color="#e4e3df", lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.axhline(res["thresh"], color="#0b0b0b", lw=0.9, ls=":", zorder=1)
        ax.text(layers[-1] + 0.3, res["thresh"] + 0.012, f"{res['thresh']:.2f}", fontsize=7.5, ha="right", color="#0b0b0b")
        ax.axhline(0.5, color="#e4e3df", lw=0.8, zorder=0)
        pr = ent["probe"]
        if pr:
            Ls = sorted(pr)
            ax.fill_between(Ls, [pr[L]["boot_lo"] for L in Ls], [pr[L]["boot_hi"] for L in Ls], color=COLORS["probe"], alpha=0.12, lw=0)
            ax.plot(Ls, [pr[L]["p"] for L in Ls], color=COLORS["probe"], lw=2, label="E10 held-out probe (last token)", zorder=3)
        ll = ent["logit_lens"]
        if ll:
            Ls = sorted(L for L in ll if not ll[L]["is_final"])
            ax.plot(Ls, [ll[L]["p"] for L in Ls], color=COLORS["logit_lens"], lw=1.4, ls="--", label="logit lens (margin > 0)", zorder=2)
            fin = [L for L in ll if ll[L]["is_final"]]
            if fin:
                ax.plot([layers[-1] + 0.6], [ll[fin[0]]["p"]], color=COLORS["logit_lens"], marker="s", ms=5, ls="none", zorder=2,
                        label=f"logit lens, final block L{fin[0]}")
        offs = {"jlens": -0.35, "olens": 0.0, "nla": 0.35}
        for rd in PLOT_READERS:
            cv = ent["readers"].get(rd)
            if not cv:
                continue
            Ls = sorted(L for L in cv if cv[L]["n"] > 0)
            x = [L + offs[rd] for L in Ls]
            y = [cv[L]["p"] for L in Ls]
            yerr = [[max(cv[L]["p"] - cv[L]["boot_lo"], 0) for L in Ls], [max(cv[L]["boot_hi"] - cv[L]["p"], 0) for L in Ls]]
            # connect only consecutive scored grid layers (no interpolation across pending layers)
            for a, b in zip(Ls, Ls[1:]):
                if b - a == 2:
                    ax.plot([a + offs[rd], b + offs[rd]], [cv[a]["p"], cv[b]["p"]], color=COLORS[rd], lw=1.4, zorder=3)
            ns = sorted({cv[L]["n"] for L in Ls})
            n_txt = f"n={ns[0]}" if len(ns) == 1 else f"n={ns[0]}–{ns[-1]}"
            ax.errorbar(x, y, yerr=yerr, color=COLORS[rd], marker=MARKERS[rd], ms=6, ls="none", lw=1.1, capsize=3, zorder=4,
                        label=f"{K.READER_LABELS[rd]}, {n_txt}" + ("" if len(Ls) == len(layers) else f" [L{', '.join(map(str, Ls))} scored]"))
        pend = sorted({L for v in ent["verdict"].values() for L in v["layers_pending"]})
        for L in pend:
            ax.axvspan(L - 0.9, L + 0.9, color="#e4e3df", alpha=0.35, lw=0, zorder=0)
        ax.set_xticks(list(layers))
        ax.set_xlim(layers[0] - 1.2, layers[-1] + 1.4)
        ax.set_ylim(0, 1.08)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0", "25", "50", "75", "100"])
        ax.set_xlabel("decoder block (output captured), last prompt token")
        ax.set_title(f"{set_.upper()} set (n = {ent['n_items']})")
        ax.legend(loc="lower right", fontsize=7)
    np.atleast_1d(axes)[0].set_ylabel("% items: reader favours the model's ACTUAL answer\n(two-candidate native log-odds > 0; 95% item bootstrap)")
    fig.suptitle("V1 — reader layer sweep at the last token. Grey bands: layers no reader has scored yet (pod arm pending).", fontsize=10)
    fig.tight_layout(rect=(0.01, 0, 1, 0.96))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ------------------------------------------------------------------ write-up
def write_md(path: Path, res: Mapping[str, Any], info: Mapping[str, Any], args: argparse.Namespace) -> None:
    L = []
    L.append("# V1 — reader layer sweep at the last token (PREREG_WV.md Part V)\n")
    L.append(f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `projects/g_agreement/v12_readers/v1_sweep.py`; "
             f"item bootstrap {res['n_boot']} resamples, seed {res['seed']}; threshold {res['thresh']:.2f}._\n")
    L.append("**Question.** Does any reader (J-lens native, Oracle Lens at the nearest grid layer, NLA transferred from L42) read the "
             "model's actual answer at some layer 42–62, and if so how many layers after the E10 probe first does?\n")
    L.append("**What exists on the Mac (no model calls possible here).** Reader rows at two layers only: L42 = the X3 block-42 last-token "
             "states (`cache/g_agreement/x/x3_lo.jsonl`; the Oracle Lens there used its layer-42 carrier, off-grid, not the Y1 nearest-grid "
             "rule; DISAGREE exists only for the 33-item X3 subset of the 165 Y1 disagreements) and L48 = the Y1 re-read at site 48:0 "
             "(`cache/g_agreement/y/y1_lo.jsonl`). Layers 44, 46, 50–62 need the pod: J-lens needs the 3.3 GB lens file, the Oracle Lens and "
             "NLA need the 27B models and adapters (see `v12_pod_requests.json`). The E10 probe curve and the logit-lens curve come from "
             "the Y1 analysis (`results/g_agreement/y1/sweep_<set>.csv` position 0, `logitlens.csv`).\n")
    srcs = "; ".join(f"{s['source']}: {s['n_rows']} rows" for s in info["sources"])
    L.append(f"Row sources: {srcs}. Overrides on (reader, site, item): {info['overrides']} "
             f"(sign agreement {info['override_sign_agree']}).\n")
    for set_ in K.MAIN_SETS:
        ent = res["sets"][set_]
        ctl = res["sets"].get(K.CONTROL_OF[set_], {})
        L.append(f"\n## {set_.upper()} (n = {ent['n_items']}; control = {K.CONTROL_OF[set_]}, n = {ctl.get('n_items')})\n")
        L.append("| reader | layer | layer used | P(favours actual) [95% CI] | unscorable | control set P(favours actual) | probe at layer | logit lens at layer |")
        L.append("|---|---|---|---|---|---|---|---|")
        for rd, cv in ent["readers"].items():
            for Ly, d in sorted(cv.items()):
                c = (ctl.get("readers", {}).get(rd) or {}).get(Ly)
                pr = ent["probe"].get(Ly)
                ll = ent["logit_lens"].get(Ly)
                L.append(f"| {rd} | {Ly} | {d.get('layer_used')} | {K.fmt_rate(d)} | {d['n_unscorable']} | {K.fmt_rate(c) if c else 'n/a'} | "
                         f"{100 * pr['p']:.1f}% | {100 * ll['p']:.1f}% |" if pr and ll else
                         f"| {rd} | {Ly} | {d.get('layer_used')} | {K.fmt_rate(d)} | {d['n_unscorable']} | {K.fmt_rate(c) if c else 'n/a'} | n/a | n/a |")
        pr = ent["probe"]
        if pr:
            L.append("\nE10 probe (last token) by layer: " + ", ".join(f"L{Ly} {100 * pr[Ly]['p']:.0f}%" for Ly in sorted(pr)) +
                     f". First layer >= {res['thresh']:.2f}: {ent.get('probe_first_layer_ge_thresh')}.")
        ll = ent["logit_lens"]
        if ll:
            L.append("Logit lens (margin > 0) by layer: " + ", ".join(f"L{Ly} {100 * ll[Ly]['p']:.0f}%{'*' if ll[Ly]['is_final'] else ''}" for Ly in sorted(ll)) +
                     " (* = final block).")
        L.append("\n**Pre-registered rule, per reader:**\n")
        for rd, v in ent["verdict"].items():
            if v["status"] == "crossed":
                lag = v["lag_layers"]
                L.append(f"- {rd}: crosses {res['thresh']:.2f} first at L{v['first_layer_ge_thresh']} (CI lower bound >= threshold first at "
                         f"{v['first_layer_ci_lo_ge_thresh']}); probe first at L{v['probe_first_layer_ge_thresh']}; lag {lag} layers"
                         + ("" if v["complete"] else f" — scored layers {v['layers_scored']} only, pending {v['layers_pending']}; an earlier crossing is still possible") + ".")
            elif v["complete"]:
                L.append(f"- {rd}: no layer reaches {res['thresh']:.2f} through 62 (max {100 * v['max_p']:.1f}% at L{v['max_p_layer']}) -> outcome (b), the strong claim stands.")
            else:
                L.append(f"- {rd}: below {res['thresh']:.2f} at every scored layer {v['layers_scored']} (max {100 * v['max_p']:.1f}% at L{v['max_p_layer']}); "
                         f"layers {v['layers_pending']} pending on the pod -> verdict provisional.")
    L.append("\n## Verdict (as of this run)\n")
    for set_ in K.MAIN_SETS:
        ent = res["sets"][set_]
        done = all(v["complete"] for v in ent["verdict"].values()) and ent["verdict"]
        crossed = {rd: v["first_layer_ge_thresh"] for rd, v in ent["verdict"].items() if v["first_layer_ge_thresh"] is not None}
        if crossed:
            L.append(f"- {set_.upper()}: outcome (a) for {crossed}; probe first >= threshold at L{ent.get('probe_first_layer_ge_thresh')}.")
        elif done:
            L.append(f"- {set_.upper()}: outcome (b) — no reader crosses by L62; the strong claim stands.")
        else:
            pf = ent.get("probe_first_layer_ge_thresh")
            L.append(f"- {set_.upper()}: no reader crosses at the scored layers (outcome (b) so far); FINAL only after the pod scores "
                     f"the pending layers. The probe first crosses at " + (f"L{pf}." if pf is not None else "no layer (never, on this set)."))
    L.append("\nCaveats: the L42 point uses the X3 capture of the same prompts (block-42 last token, same render), not the Y1 capture file; "
             "the pod arm re-scores 42:0 from `y1_caps` so the two captures can be cross-checked. NLA at any layer other than 42 is a transfer "
             "test (adapter trained at L42). The Oracle Lens is read at the nearest grid layer {44, 48, 52, 56, 60}; `olens_trueL` is the "
             "true-layer sensitivity arm. DISAGREE at L42 has n = 33 (X3 subset), so its CI is wide.\n")
    L.append("Figure: `fig_v1.png`; table: `v1.csv`.\n")
    path.write_text("\n".join(L))


def run(args: argparse.Namespace) -> dict:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _, items = K.load_items(args.items)
    K.check_item_roles(items)
    rows, info = K.load_lo_rows(args.x3_lo, args.y1_lo, args.extra_lo, items=items)
    res = analyse(items, rows, Path(args.sweep_dir), n_boot=args.n_boot, seed=args.seed, thresh=args.thresh)
    res["row_sources"] = info
    K.write_csv(out / "v1.csv", csv_rows(res))
    if not args.no_fig:
        make_figure(out / "fig_v1.png", res)
    write_md(out / "v1.md", res, info, args)
    (out / "v1_summary.json").write_text(json.dumps(res, indent=1, default=_json_default))
    for set_ in K.MAIN_SETS:
        for rd, v in res["sets"][set_]["verdict"].items():
            print(f"[v1] {set_:9s} {rd:12s} {v['status']}: scored {v['layers_scored']} max {v['max_p']:.3f}@L{v['max_p_layer']} "
                  f"first>= {v['first_layer_ge_thresh']} probe first {v['probe_first_layer_ge_thresh']}")
    return res


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
