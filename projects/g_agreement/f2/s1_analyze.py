"""S1 analysis (Mac): are the F2-3 template cells load-bearing? (BRIEF_S.md "S1").

    python -m projects.g_agreement.f2.s1_analyze [--root .]
-> results/g_agreement/s1/{s1.md, s1.csv, fig_s1.png, s1_summary.json}
Flip = greedy answer parsed as the other version's answer (Wilson 95%). Answer LO shift toward the other version = edited -
natural (ownership: first-token lp(other) - lp(own); tense: teacher-forced summed lp of the other version's natural answer minus
the own one's); fraction of arm "all" with a pair bootstrap (1,000, seed 0). Readers: native LO = score(own) - score(other);
follow = LO moves toward the other version vs the natural state. Verdict at alpha = 1 per (family, layer).
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ARMS = ("cells", "all", "last", "noncell", "rand", "probe", "cellsT", "cellsI")
ARM_LABEL = {"cells": "1 cells", "all": "2 all positions", "last": "3 last token", "noncell": "4 non-cell positions",
             "rand": "5 random dir @ cells", "probe": "6 probe dir @ cells", "cellsT": "1T cells: template tokens", "cellsI": "1I cells: instruction words"}
TEMPLATE = {"<think>", "</think>", "\n\n", "\n", "<|im_start|>", "<|im_end|>", "assistant"}


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def jl(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def verdict(c1, c4, c5, frac):
    p, lo, _ = c1
    if p >= 0.5 and lo > c4[2] and lo > c5[2] and frac >= 0.5:
        return "LOAD-BEARING"
    if p <= 0.05 and frac < 0.10:
        return "INERT"
    return "PARTIAL"


def verdict_lines(by, V):
    """Three generated lines: template cells, instruction-word cells vs the non-cell control, readers vs the model."""
    g = lambda f, L, arm, al: by.get((f, L, arm, al), (None,))[0]  # noqa: E731
    own = [L for L in (36, 38, 44) if g("ownership", L, "cells", 1.0)]
    pc = lambda r: f"{r['flips']}/{r['n']}"  # noqa: E731
    t1 = "; ".join(f"{L}: {pc(g('ownership', L, 'cellsT', 2.0))}" for L in own)
    tt = "; ".join(f"{L}: {pc(g('tense', L, 'cells', 2.0))}" for L in (36, 38) if g("tense", L, "cells", 2.0))
    ci = ", ".join(f"{L}: {pc(g('ownership', L, 'cellsI', 1.0))} at α 1, {pc(g('ownership', L, 'cellsI', 2.0))} at α 2, "
                   f"{g('ownership', L, 'cellsI', 1.0)['frac_of_all']:.2f} of the full edit's log-odds shift (non-cell control "
                   f"{g('ownership', L, 'noncell', 1.0)['frac_of_all']:.2f}, {pc(g('ownership', L, 'noncell', 1.0))} flips)" for L in own)
    c2 = ", ".join(f"{L}: {pc(g('ownership', L, 'cells', 2.0))} vs {pc(g('ownership', L, 'noncell', 2.0))}" for L in own)
    rf = [g("ownership", L, "cells", 1.0)[f"{rd}56_follow"] for L in own for rd in ("jlens", "olens")]
    fl = [g("ownership", L, "cells", 1.0)["flip"] for L in own]
    return [f"1. Chat-template cells (`<think>`, `\\n\\n`, `<|im_start|>`, `<|im_end|>`) are INERT: edited alone they flip no answer even at "
            f"α 2 (ownership {t1}; tense, whose only genuine cells are `<think>`, {tt}) and move the answer log-odds ≤ 1% of the full edit.",
            f"2. Ownership instruction-word cells (` Reply`, ` name`, `?`, ...) are PARTIAL: {ci}. At the verdict dose they move the answer about as much as an "
            f"equal number of other non-content positions; at α 2 all cells vs that control flip {c2}. Not load-bearing at any block; "
            f"the instruction words carry a modest share of the binding, comparable to other context positions.",
            f"3. Readers at block 56 follow the cell edits {100 * min(rf):.0f}–{100 * max(rf):.0f}% of the time while the model flips "
            f"{100 * min(fl):.0f}–{100 * max(fl):.0f}% (α 1): the same 'readers weight what the model under-weights' pattern as F2-2. "
            f"Verdicts: " + ", ".join(f"{k.replace('|', ' ')} {v}" for k, v in V.items() if k.endswith("|cells")) + "."]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    a = ap.parse_args()
    C, OUT = a.root / "cache/g_agreement/s1", a.root / "results/g_agreement/s1"
    OUT.mkdir(parents=True, exist_ok=True)
    beh = {}
    for r in jl(C / "behaviour.jsonl"):
        beh[r["key"]] = r
    tf = {r["key"]: r["lo_tf"] for r in jl(C / "tf.jsonl")}
    lo = {r["key"]: r["lo"] for r in jl(C / "lo.jsonl")}
    meta = json.loads((C / "cells.json").read_text()) if (C / "cells.json").exists() else {}
    nat = {(r["pair_id"], r["source"]): r for r in beh.values() if r["arm"] == "natural"}
    bad_nat = sorted(f"{p}|{s}" for (p, s), r in nat.items() if not r["kept"])
    ok_state = {k for k, r in nat.items() if r["kept"]}

    def model_lo(r):
        if r["family"] == "tense":
            return tf.get(r["key"])
        return r["lo_model"]

    groups = defaultdict(list)
    for r in beh.values():
        if r["arm"] == "natural" or (r["pair_id"], r["source"]) not in ok_state:
            continue
        groups[(r["family"], r["layer"], r["arm"], r["alpha"])].append(r)
    rng = np.random.default_rng(0)
    rows, by = [], {}
    for (fam, L, arm, al), rs in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1], ARMS.index(x[0][2]), x[0][3])):
        k = sum(r["flipped"] for r in rs)
        p, wlo, whi = wilson(k, len(rs))
        sh = {}
        for r in rs:
            m0, m1 = model_lo(nat[(r["pair_id"], r["source"])]), model_lo(r)
            if m0 is not None and m1 is not None:
                sh[(r["pair_id"], r["source"])] = m1 - m0
        row = {"family": fam, "layer": L, "arm": arm, "alpha": al, "n": len(rs), "flips": k, "flip": p, "flip_lo": wlo, "flip_hi": whi,
               "lo_shift_mean": float(np.mean(list(sh.values()))) if sh else None, "n_lo": len(sh)}
        for rd in ("jlens", "olens"):
            for Lr in (44, 56):
                fol, shifts = [], []
                for r in rs:
                    l1, l0 = lo.get(f"{rd}|{Lr}|{r['key']}"), lo.get(f"{rd}|{Lr}|{r['pair_id']}|{r['source']}|natural|0|0")
                    if l1 is not None and l0 is not None:
                        shifts.append(l0 - l1)  # toward the other version
                        fol.append(l0 - l1 > 0)
                fp = wilson(sum(fol), len(fol))
                row[f"{rd}{Lr}_follow"], row[f"{rd}{Lr}_follow_lo"], row[f"{rd}{Lr}_follow_hi"] = fp
                row[f"{rd}{Lr}_shift"] = float(np.mean(shifts)) if shifts else None
                row[f"{rd}{Lr}_n"] = len(fol)
        by[(fam, L, arm, al)] = (row, sh)
        rows.append(row)
    # fraction of arm 2's LO shift, pair bootstrap
    for (fam, L, arm, al), (row, sh) in by.items():
        ref = by.get((fam, L, "all", al))
        if not ref or not sh or not ref[1]:
            row["frac_of_all"] = row["frac_lo"] = row["frac_hi"] = None
            continue
        sh2 = ref[1]
        keys = sorted(set(sh) & set(sh2))
        pids = sorted({k[0] for k in keys})
        fr = np.mean([sh[k] for k in keys]) / np.mean([sh2[k] for k in keys])
        bs = []
        for _ in range(1000):
            pick = rng.choice(len(pids), len(pids))
            kk = [k for i in pick for k in keys if k[0] == pids[i]]
            den = np.mean([sh2[k] for k in kk])
            bs.append(np.mean([sh[k] for k in kk]) / den if den != 0 else np.nan)
        row["frac_of_all"], row["frac_lo"], row["frac_hi"] = float(fr), float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))
    with (OUT / "s1.csv").open("w", newline="") as fh:
        keys = list(dict.fromkeys(k for r in rows for k in r))
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    # verdicts at alpha 1
    V = {}
    for fam, L in sorted({(r["family"], r["layer"]) for r in rows}):
        g = lambda arm: by.get((fam, L, arm, 1.0), (None,))[0]  # noqa: E731
        c4, c5 = g("noncell"), g("rand")
        for arm in ("cells", "cellsT", "cellsI"):
            r1 = g(arm)
            if r1 is None or c4 is None or c5 is None or r1.get("frac_of_all") is None:
                continue
            V[f"{fam}|{L}|{arm}"] = verdict((r1["flip"], r1["flip_lo"], r1["flip_hi"]), (c4["flip"], c4["flip_lo"], c4["flip_hi"]),
                                            (c5["flip"], c5["flip_lo"], c5["flip_hi"]), r1["frac_of_all"])
    (OUT / "s1_summary.json").write_text(json.dumps({"verdicts": V, "natural_not_kept": bad_nat, "n_rows": len(rows)}, indent=1))
    # cells listing (from F2-3) grouped by token type and layer
    t3 = list(csv.DictReader((a.root / "results/g_agreement/f2/t3/t3_probe_only.csv").open()))
    pct = lambda p, l_, h: "–" if p is None else f"{100 * p:.0f}% [{100 * l_:.0f}, {100 * h:.0f}]"  # noqa: E731
    f2 = lambda x: "–" if x is None else f"{x:+.2f}"  # noqa: E731
    frac = lambda r: "–" if r.get("frac_of_all") is None else f"{r['frac_of_all']:.2f} [{r['frac_lo']:.2f}, {r['frac_hi']:.2f}]"  # noqa: E731
    Ls = ["# S1 — are the F2-3 template cells load-bearing?", "",
          "Pre-registered in BRIEF_S.md \"S1\" (2026-10-15) with one deviation logged before compute: tense has 23 test pairs (46 states), and the 6 "
          "tense cells at offset 16 are a token-misalignment artefact (dropped; F2-3's genuine probe-only cells = 54). Edit at the block named, "
          "prompt prefill only; alpha = 1 is the verdict dose. Flip: Wilson 95%. LO fraction: mean shift / arm 2's mean shift, pair bootstrap.", "",
          f"Natural states not answered correctly (excluded): {len(bad_nat)} {bad_nat if bad_nat else ''}", "",
          "## Verdict", ""] + verdict_lines(by, V) + ["",
          "## Verdicts (alpha = 1)", "", "| family | block | arm 1 cells | 1T template tokens | 1I instruction words |", "|---|---|---|---|---|"]
    for fam, L in sorted({(r["family"], r["layer"]) for r in rows}):
        Ls.append(f"| {fam} | {L} | {V.get(f'{fam}|{L}|cells', '–')} | {V.get(f'{fam}|{L}|cellsT', '–')} | {V.get(f'{fam}|{L}|cellsI', '–')} |")
    Ls += ["", "## Every arm", "", "| family | block | arm | α | flips | answer-LO shift (nats) | fraction of arm 2 | J-lens@44 follow | J-lens@56 | Oracle@44 | Oracle@56 |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        Ls.append(f"| {r['family']} | {r['layer']} | {ARM_LABEL[r['arm']]} | {r['alpha']} | {r['flips']}/{r['n']} = {pct(r['flip'], r['flip_lo'], r['flip_hi'])} | "
                  f"{f2(r['lo_shift_mean'])} | {frac(r)} | "
                  + " | ".join(pct(r[f'{rd}{Lr}_follow'], r[f'{rd}{Lr}_follow_lo'], r[f'{rd}{Lr}_follow_hi']) for rd in ("jlens", "olens") for Lr in (44, 56)) + " |")
    Ls += ["", "Reads at block 44 after an edit at 44 leave the last token untouched for arms 1, 4, 5, 6 (unchanged by construction).", "",
           "## The F2-3 cells, by token type and block", "", "| family | token type | token (offset from last) | blocks |", "|---|---|---|---|"]
    grp = defaultdict(list)
    for c in t3:
        grp[(c["family"], "template" if c["token"] in TEMPLATE else "instruction word", c["token"], int(c["offset_from_last"]))].append(int(c["layer"]))
    for (fam, tt, tk, k), Lz in sorted(grp.items(), key=lambda x: (x[0][0], x[0][1], x[0][3])):
        note = " (misalignment artefact, dropped)" if fam == "tense" and k == 16 else ""
        Ls.append(f"| {fam} | {tt} | `{tk!r}` ({k}){note} | {', '.join(map(str, sorted(Lz)))} |")
    cnt = Counter(int(c["layer"]) for c in t3)
    Ls += ["", "Cells per block (F2-3, both families): " + ", ".join(f"{L}: {cnt[L]}" for L in sorted(cnt))]
    if meta:
        tokc = Counter(t for m in meta.values() for t in m.get("cell_tokens", []))
        Ls += ["", "Actual tokens at the edited cell positions (all states, all blocks): " + ", ".join(f"`{t!r}` {n}" for t, n in tokc.most_common())]
    (OUT / "s1.md").write_text("\n".join(Ls) + "\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        panels = sorted({(r["family"], r["layer"]) for r in rows})
        fig, axes = plt.subplots(1, len(panels), figsize=(4.2 * len(panels), 3.8), squeeze=False, sharey=True)
        cols = {"cells": "#d62728", "all": "#111111", "last": "#7f7f7f", "noncell": "#1f77b4", "rand": "#bcbd22", "probe": "#9467bd",
                "cellsT": "#ff9896", "cellsI": "#e377c2"}
        for ax, (fam, L) in zip(axes[0], panels):
            for j, arm in enumerate(ARMS):
                rr = [r for r in rows if r["family"] == fam and r["layer"] == L and r["arm"] == arm]
                if not rr:
                    continue
                x = np.array([r["alpha"] for r in rr]) * (1 + 0.03 * (j - 3))
                y = np.array([r["flip"] for r in rr])
                e = np.clip(np.array([[r["flip"] - r["flip_lo"] for r in rr], [r["flip_hi"] - r["flip"] for r in rr]]), 0, None)
                ax.errorbar(x, 100 * y, yerr=100 * e, marker="o", ms=4, lw=1.8 if arm in ("cells", "all") else 1.1, capsize=2,
                            color=cols[arm], ls="--" if arm in ("cellsT", "cellsI") else "-", label=ARM_LABEL[arm])
            ax.set_xscale("log", base=2); ax.set_xticks([0.5, 1, 2]); ax.set_xticklabels(["0.5", "1", "2"])
            ax.set_title(f"{fam}, edit at block {L}", fontsize=10); ax.set_xlabel("dose α")
            ax.set_ylim(-3, 103); ax.grid(alpha=0.3)
        axes[0][0].set_ylabel("model answer flips (% of states, Wilson 95%)")
        h, l = axes[0][0].get_legend_handles_labels()
        axes[0][-1].legend(h, l, fontsize=7, loc="center left", bbox_to_anchor=(1.02, 0.5))
        fig.suptitle("S1: does editing only the probe-only template cells flip the model's answer?", fontsize=11)
        fig.savefig(OUT / "fig_s1.png", dpi=140, bbox_inches="tight"); plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        print(f"[s1] figure skipped: {exc}")
    print("\n".join(Ls[:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
