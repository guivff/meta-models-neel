"""F2-6 analysis (Mac): do readers track `col` at the new read sites? Pre-registered rule in BRIEF_Z.md (follow-ups 3).

    python -m projects.g_agreement.f2.t6_analyze [--root .]
-> results/g_agreement/f2/t6/{t6.md, t6.csv, t6_summary.json, fig_t6.png}
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

SITES = ("s0_raw", "s1_im_end", "s2_count", "s3_count_im_end")
SITE_LABEL = {"s0_raw": "raw text", "s1_im_end": "+ <|im_end|>", "s2_count": "count instruction", "s3_count_im_end": "count instruction + <|im_end|>"}
CELLS = [("olens", 42), ("olens", 44), ("nla", 42), ("jlens", 42), ("jlens", 44)]
FAMS = ("count_qual", "count_num", "decision", "placebo")
MENTION_RE_STRICT = (r"(\b\d+\s*(-\s*)?(characters?|chars)\b|\bcharacters? (count|long|per line|wide)\b|"
                     r"\b(number of|count of|many|few) characters\b|\bchars\b|\bline[- ]length|\bline[- ]width|"
                     r"\bcolumn (position|width|\d)|\b(line|word|text)[- ]wrap\w*|\bwrap(ped|s)? (at|to) \d|\bline[- ]?breaks?|\bnewlines?\b|\blong line|\bshort line|"
                     r"\bend of (the |a )?line|\bstart of (the |a )?line|\bline is (long|short|full)|"
                     r"\bhard[- ]wrapped|\bfixed[- ]width)")  # Suraj 08_col_pilot/templates.py MENTION_RE_STRICT


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def ridge_lopo(X, y, groups, lam=1e2):
    """Leave-one-passage-out ridge (dual form, standardised features). Returns out-of-fold predictions."""
    pred = np.zeros_like(y, dtype=float)
    for g in sorted(set(groups)):
        tr, te = groups != g, groups == g
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-6
        A, B = (X[tr] - mu) / sd, (X[te] - mu) / sd
        ym = y[tr].mean()
        K = A @ A.T
        alpha = np.linalg.solve(K + lam * len(A) * np.eye(len(A)), y[tr] - ym)
        pred[te] = B @ (A.T @ alpha) + ym
    return pred


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    a = ap.parse_args()
    C, OUT = a.root / "cache/g_agreement/f2/t6", a.root / "results/g_agreement/f2/t6"
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {m["key"]: m for m in json.loads((C / "states_meta.json").read_text())}
    lo = defaultdict(list)
    for x in (C / "lo.jsonl").read_text().splitlines():
        if x.strip():
            r = json.loads(x)
            if r["lo"] is not None:
                lo[(r["reader"], r["layer"], r["family"], r["key"])].append(r["lo"])
    items = sorted({m["item"] for m in meta.values()})
    S = {"cells": {}, "decision": {}, "probe": {}, "mentions": {}}
    rows = []
    for site in SITES:
        for rd, L in CELLS:
            for fam in FAMS:
                ws = []
                for it in items:
                    h, l = lo.get((rd, L, fam, f"{it}|high|{site}")), lo.get((rd, L, fam, f"{it}|low|{site}"))
                    if h and l:
                        ws.append(np.mean(h) > np.mean(l))
                if not ws:
                    continue
                p, lo_, hi = wilson(sum(ws), len(ws))
                S["cells"][f"{rd}@{L}|{site}|{fam}"] = {"win": p, "lo": lo_, "hi": hi, "n": len(ws)}
                rows.append({"site": site, "reader": rd, "layer": L, "family": fam, "win": p, "lo": lo_, "hi": hi, "n": len(ws)})
            c, pl = S["cells"].get(f"{rd}@{L}|{site}|count_qual"), S["cells"].get(f"{rd}@{L}|{site}|placebo")
            if c and pl:
                S["decision"][f"{rd}@{L}|{site}"] = bool(c["win"] >= 0.70 and c["lo"] > 0.5 and abs(pl["win"] - 0.5) <= 0.15)
    # probe positive control on block 42
    try:
        import torch
        H = torch.load(C / "states_L42.pt", map_location="cpu")
        for site in SITES:
            keys = [k for k in meta if meta[k]["site"] == site and k in H]
            X = np.stack([H[k].float().numpy() for k in keys]).astype(np.float64)
            y = np.array([meta[k]["col"] for k in keys], dtype=float)
            g = np.array([meta[k]["item"] for k in keys])
            pr = ridge_lopo(X, y, g)
            from scipy.stats import spearmanr
            rho = float(spearmanr(pr, y).correlation)
            pk = {k: v for k, v in zip(keys, pr)}
            ws = [pk[f"{it}|high|{site}"] > pk[f"{it}|low|{site}"] for it in items if f"{it}|high|{site}" in pk and f"{it}|low|{site}" in pk]
            p, lo_, hi = wilson(sum(ws), len(ws))
            S["probe"][site] = {"spearman": rho, "win": p, "lo": lo_, "hi": hi, "n": len(ws)}
    except Exception as exc:  # noqa: BLE001
        S["probe"]["error"] = str(exc)
    # free-text mentions
    rx = re.compile(MENTION_RE_STRICT, re.I)
    mt = defaultdict(list)
    for x in (C / "ol_text.jsonl").read_text().splitlines():
        if x.strip():
            r = json.loads(x)
            m = meta[r["key"]]
            mt[(m["site"], m["read"])].append(bool(rx.search(r["text"] or "")))
    for (site, rd), v in mt.items():
        S["mentions"][f"{site}|{rd}"] = {"k": sum(v), "n": len(v), "rate": sum(v) / len(v)}
    (OUT / "t6_summary.json").write_text(json.dumps(S, indent=1, default=float))
    with (OUT / "t6.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    pc = lambda c: "–" if not c else f"{100*c['win']:.0f}% [{100*c['lo']:.0f}, {100*c['hi']:.0f}]"  # noqa: E731
    tracks = [k for k, v in S["decision"].items() if v]
    Ls = ["# F2-6 — does any reader track the newline feature at new read sites?", "",
          "Pre-registered in BRIEF_Z.md (follow-ups 3). 60 hard-wrapped wikitext-103 test passages (widths 30–70); per passage a 'high' read "
          "(≥ 75% of the line width) and a 'low' read (≤ 25%). Win = the reader's log-odds for 'long line' is higher at the high read than at the "
          "low read (Suraj's fixed templates; count_qual primary, mean over its two templates). Wilson 95% CI over passages. Placebo = an "
          "unrelated contrast that should stay at 50%.", "",
          f"**Decision: {'tracks col at ' + ', '.join(tracks) if tracks else 'no reader tracks col at any site (count_qual win ≥ 70% with CI > 50% and placebo within 50 ± 15%)'}.**", "",
          "## Primary: 'long line' vs 'short line' (count_qual)", "", "| reader | " + " | ".join(SITE_LABEL[s] for s in SITES) + " |", "|---|" + "---|" * len(SITES)]
    for rd, L in CELLS:
        Ls.append(f"| {rd}@{L} | " + " | ".join(pc(S["cells"].get(f"{rd}@{L}|{s}|count_qual")) for s in SITES) + " |")
    Ls += ["", "## Other contrasts (same layout)", ""]
    for fam in ("count_num", "decision", "placebo"):
        Ls += [f"**{fam}**", "", "| reader | " + " | ".join(SITE_LABEL[s] for s in SITES) + " |", "|---|" + "---|" * len(SITES)]
        for rd, L in CELLS:
            if any(S["cells"].get(f"{rd}@{L}|{s}|{fam}") for s in SITES):
                Ls.append(f"| {rd}@{L} | " + " | ".join(pc(S["cells"].get(f"{rd}@{L}|{s}|{fam}")) for s in SITES) + " |")
        Ls.append("")
    Ls += ["## Positive control: a ridge probe for the character count (block 42, leave-one-passage-out)", "",
           "| site | Spearman (predicted vs true count) | high > low |", "|---|---|---|"]
    for s in SITES:
        p = S["probe"].get(s)
        if p:
            Ls.append(f"| {SITE_LABEL[s]} | {p['spearman']:.2f} | {pc(p)} |")
    Ls += ["", "## Oracle free text (2 samples at block 44): share of readouts mentioning line length (Suraj's strict regex)", "",
           "| site | high reads | low reads |", "|---|---|---|"]
    for s in SITES:
        h, l = S["mentions"].get(f"{s}|high"), S["mentions"].get(f"{s}|low")
        Ls.append(f"| {SITE_LABEL[s]} | {h['k']}/{h['n']} | {l['k']}/{l['n']} |" if h and l else f"| {SITE_LABEL[s]} | – | – |")
    (OUT / "t6.md").write_text("\n".join(Ls) + "\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 4))
        cols = ["#2a5bd7", "#7ea2ff", "#d9822b", "#1f7a3a", "#6fd38f"]
        for i, (rd, L) in enumerate(CELLS):
            for j, s in enumerate(SITES):
                c = S["cells"].get(f"{rd}@{L}|{s}|count_qual")
                if c:
                    x = j + (i - 2) * 0.13
                    ax.errorbar(x, c["win"], yerr=[[c["win"] - c["lo"]], [c["hi"] - c["win"]]], fmt="o", color=cols[i], capsize=2, ms=4, label=f"{rd}@{L}" if j == 0 else None)
                    pl = S["cells"].get(f"{rd}@{L}|{s}|placebo")
                    if pl:
                        ax.plot(x, pl["win"], marker="x", color=cols[i], ms=4, alpha=0.6)
        for j, s in enumerate(SITES):
            p = S["probe"].get(s)
            if p:
                ax.plot([j - 0.35, j + 0.35], [p["win"], p["win"]], color="#111111", lw=1.5, label="ridge probe (block 42)" if j == 0 else None)
        ax.axhline(0.5, color="#999999", lw=0.8, ls=":"); ax.axhline(0.7, color="#bbbbbb", lw=0.8, ls="--")
        ax.set_xticks(range(len(SITES))); ax.set_xticklabels([SITE_LABEL[s] for s in SITES], fontsize=8)
        ax.set_ylim(0, 1.02); ax.set_ylabel("high > low read, share of 60 passages (95% CI)")
        ax.set_title("F2-6: do readers track 'characters since the last newline'? (dots: 'long line' contrast; x: placebo)", fontsize=9)
        ax.legend(fontsize=7, loc="lower right", ncol=3)
        fig.tight_layout(); fig.savefig(OUT / "fig_t6.png", dpi=150); plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        print(f"[t6] figure skipped: {exc}")
    print("\n".join(Ls[:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
