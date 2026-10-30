"""F2-3 analysis (Mac): probe vs J-lens vs Oracle within-pair win per (family, layer, offset from the last token).

    python -m projects.g_agreement.f2.t3_analyze [--root .]
-> results/g_agreement/f2/t3/{t3.md, t3_cells.csv, t3_probe_only.csv, t3_summary.json, fig_t3.png}
Win per pair: probe = held-out score of the positive state > the other's (X1 E2, leave-one-pair-out); readers = lo_A + lo_B > 0.
Wilson 95% CI over pairs. "Probe reads it, readers at chance": probe win >= 0.80 and every reader's CI includes 0.5.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

FAMS = ("ownership", "mapping", "language", "tense")
LAYERS = list(range(36, 61, 4))


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    a = ap.parse_args()
    C, OUT = a.root / "cache/g_agreement/f2/t3", a.root / "results/g_agreement/f2/t3"
    OUT.mkdir(parents=True, exist_ok=True)
    tk = json.loads((C / "tokens.json").read_text())
    K, toks = tk["K"], tk["tokens"]
    jl = lambda p: [json.loads(x) for x in p.read_text().splitlines() if x.strip()]  # noqa: E731
    probe = {(r["family"], r["layer"], r["k"]): r["wins"] for r in jl(C / "probe.jsonl")}
    lo = {(r["reader"], r["family"], r["layer"], r["k"]): r["lo"] for r in jl(C / "lo.jsonl")}
    fam_items = defaultdict(set)
    for (rd, f, L, k), d in lo.items():
        fam_items[f] |= set(d)

    def tied(pid, k):
        """True when the two prompts of the pair are token-identical up to and including this position (identical states)."""
        a, b = toks.get(pid + "A"), toks.get(pid + "B")
        if a is None or b is None or len(a) != len(b):
            return False
        d = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), len(a))
        return len(a) - 1 - k < d

    def pair_wins(d, k):
        by = defaultdict(dict)
        for iid, v in d.items():
            by[iid[:-1]][iid[-1]] = v
        return [None if (x.get("A") is None or x.get("B") is None or tied(pid, k)) else (x["A"] + x["B"]) > 0
                for pid, x in by.items() if "A" in x and "B" in x]

    def label(f, k):
        c = Counter(toks[i][-1 - k] for i in fam_items[f] if len(toks[i]) > k)
        t, n = c.most_common(1)[0]
        return t, n / max(1, sum(c.values()))

    cells, flagged = [], []
    for f in FAMS:
        for L in LAYERS:
            for k in range(K[f]):
                w = {pid: v for pid, v in probe.get((f, L, k), {}).items() if not tied(pid, k)}
                pr = wilson(sum(w.values()), len(w))
                row = {"family": f, "layer": L, "offset_from_last": k, "token": label(f, k)[0], "token_share": round(label(f, k)[1], 2),
                       "probe": (pr[0] if w else None), "probe_lo": pr[1], "probe_hi": pr[2], "n_pairs": len(w)}
                chance = []
                for rd in ("jlens", "olens"):
                    d = lo.get((rd, f, L, k))
                    if d is None:
                        row[rd] = row[f"{rd}_lo"] = row[f"{rd}_hi"] = None
                        continue
                    ws = [x for x in pair_wins(d, k) if x is not None]
                    r = wilson(sum(ws), len(ws))
                    row[rd], row[f"{rd}_lo"], row[f"{rd}_hi"] = r
                    chance.append(r[1] <= 0.5 <= r[2])
                row["readers_scored"] = "+".join(rd for rd in ("jlens", "olens") if row[rd] is not None)
                npairs_f = len({i[:-1] for i in fam_items[f]})
                row["n_pairs_family"] = npairs_f
                row["probe_reads_readers_chance"] = bool(w and len(w) >= 0.75 * npairs_f and pr[0] >= 0.80 and chance and all(chance))
                cells.append(row)
                if row["probe_reads_readers_chance"]:
                    flagged.append(row)
    with (OUT / "t3_cells.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cells[0].keys())); w.writeheader(); w.writerows(cells)
    with (OUT / "t3_probe_only.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cells[0].keys())); w.writeheader(); w.writerows(flagged)
    S = {"K": K, "n_cells": len(cells), "n_flagged": len(flagged), "by_family": {}}
    for f in FAMS:
        fc = [c for c in cells if c["family"] == f]
        S["by_family"][f] = {"cells": len(fc), "probe_ge_080": sum((c["probe"] or 0) >= 0.8 for c in fc),
                             "jlens_ge_080": sum((c["jlens"] or 0) >= 0.8 for c in fc), "olens_ge_080": sum((c["olens"] or 0) >= 0.8 for c in fc),
                             "olens_scored": sum(c["olens"] is not None for c in fc), "flagged": sum(c["probe_reads_readers_chance"] for c in fc)}
    (OUT / "t3_summary.json").write_text(json.dumps(S, indent=1))
    pct = lambda p, lo_, hi: "–" if p is None else f"{100*p:.0f}% [{100*lo_:.0f}, {100*hi:.0f}]"  # noqa: E731
    Ls = ["# F2-3 — probe vs readers at every position and blocks 36–60 (X1 test bank)", "",
          "Pre-registered in BRIEF_Z.md (2026-10-14). Positions are offsets from the last token (0 = last); each family runs to its shortest prompt. "
          "A cell is flagged only if at least 75% of the family's pairs are scorable there (analysis-time rule set 2026-10-14 after 3-pair cells were flagged). Positions where a pair's two prompts are still token-identical are ties and are excluded (blank in the figure). Win = within-pair win (probe: X1 E2 difference of means, leave-one-pair-out; readers: native log-odds). Wilson 95% CI over pairs.", "",
          f"**{len(flagged)} cells where the probe reads the answer (≥ 80%) and both J-lens and Oracle are at chance (CI includes 50%).**", "",
          "| family | cells | probe ≥ 80% | J-lens ≥ 80% | Oracle ≥ 80% (scored) | probe reads, readers at chance |", "|---|---|---|---|---|---|"]
    for f in FAMS:
        b = S["by_family"][f]
        Ls.append(f"| {f} | {b['cells']} | {b['probe_ge_080']} | {b['jlens_ge_080']} | {b['olens_ge_080']} ({b['olens_scored']}) | {b['flagged']} |")
    Ls += ["", "## Every flagged cell", "", "| family | block | offset | token there | probe | J-lens | Oracle |", "|---|---|---|---|---|---|---|"]
    for c in sorted(flagged, key=lambda c: (c["family"], c["offset_from_last"], c["layer"])):
        Ls.append(f"| {c['family']} | {c['layer']} | {c['offset_from_last']} | `{c['token']!r}` | {pct(c['probe'], c['probe_lo'], c['probe_hi'])} | "
                  f"{pct(c['jlens'], c['jlens_lo'], c['jlens_hi'])} | {pct(c['olens'], c['olens_lo'], c['olens_hi'])} |")
    (OUT / "t3.md").write_text("\n".join(Ls) + "\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        fig, axes = plt.subplots(len(FAMS), 3, figsize=(16, 3.6 * len(FAMS)), squeeze=False, gridspec_kw={"hspace": 0.75})
        for i, f in enumerate(FAMS):
            ks = list(range(K[f]))[::-1]
            labs = [repr(label(f, k)[0])[1:-1][:8] for k in ks]
            for j, (name, key) in enumerate((("probe (held-out)", "probe"), ("J-lens", "jlens"), ("Oracle lens", "olens"))):
                M_ = np.full((len(LAYERS), len(ks)), np.nan)
                for c in cells:
                    if c["family"] == f and c[key] is not None and not (c["n_pairs"] == 0):
                        M_[LAYERS.index(c["layer"]), ks.index(c["offset_from_last"])] = c[key]
                ax = axes[i, j]
                im = ax.imshow(M_, aspect="auto", cmap="RdBu_r", vmin=0, vmax=1, origin="lower")
                ax.set_yticks(range(len(LAYERS))); ax.set_yticklabels(LAYERS, fontsize=7)
                ax.set_xticks(range(len(ks))); ax.set_xticklabels(labs, rotation=90, fontsize=6)
                ax.set_title(f"{f} · {name}", fontsize=9)
                if j == 0:
                    ax.set_ylabel("block")
                if key == "probe":
                    for c in cells:
                        if c["family"] == f and c["probe_reads_readers_chance"]:
                            ax.plot(ks.index(c["offset_from_last"]), LAYERS.index(c["layer"]), marker="s", ms=5, mfc="none", mec="#111111", mew=1.2)
        fig.colorbar(im, ax=axes, fraction=0.015, pad=0.01, label="within-pair win (0.5 = chance)")
        fig.suptitle("F2-3: where a probe reads the answer and where the readers do (black squares: probe ≥ 80%, both readers at chance)", fontsize=11)
        fig.savefig(OUT / "fig_t3.png", dpi=140, bbox_inches="tight"); plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        print(f"[t3] figure skipped: {exc}")
    print("\n".join(Ls[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
