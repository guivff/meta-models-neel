"""Headline figure for the Friday summary: model flip rate vs reader follow rate per edit condition, layer 38, α 1.
Sources: Y2 per-family recomputation (cache/g_agreement/y/y2_*.jsonl, X2 S2 for the full swap) and Z4b
(cache/g_agreement/z/z4b_*.jsonl). Reader follow = share of states whose native log-odds moved toward the planted
candidate; 50% is chance. Numbers are hard-coded from those computations (2026-10-09) and written to the CSV."""
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROWS = {  # condition: (model flip %, Oracle %, J-lens %, NLA % or None)
    "mapping": [
        ("Full swap, all positions", 97, 84, 89, 73),
        ("Differing symbol tokens only", 95, 95, 98, 89),
        ("All other positions only", 0, 67, 56, 67),
        ("J-space component only", 8, 83, 78, 83),
        ("J-space remainder only", 84, 83, 72, 73),
        ("Another pair's direction", 3, 50, 56, 53),
    ],
    "ownership": [
        ("Full swap, all positions", 100, 86, 94, 70),
        ("Name and object tokens only", 0, 42, 42, 50),
        ("All other positions only", 100, 89, 94, 70),
        ("Chat-template tokens only", 11, 91, 95, None),
        ("Last 3 tokens only", 0, 89, 92, None),
        ("Question tokens only", 9, 75, 69, None),
        ("J-space component only", 0, 92, 86, 80),
        ("J-space remainder only", 100, 86, 84, 66),
        ("Another pair's direction", 39, 58, 61, 57),
    ],
}
READERS = [("Oracle lens", "#eb6834", 0.16), ("J-lens", "#1baf7a", 0.0), ("NLA", "#2a78d6", -0.16)]
INK, INK2, GRID, BASE, SURF, BAR = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb", "#c3c2b7"

with open("results/g_agreement/z/fig_headline_readers_vs_model.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["family", "condition", "model_flip_pct", "oracle_follow_pct", "jlens_follow_pct", "nla_follow_pct"])
    for fam, rows in ROWS.items():
        for r in rows: w.writerow([fam, *r])

fig, axes = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={"width_ratios": [6, 9]}, facecolor=SURF)
for ax, (fam, rows) in zip(axes, ROWS.items()):
    ax.set_facecolor(SURF)
    n = len(rows); ys = list(range(n))[::-1]
    for y, (cond, flip, *rd) in zip(ys, rows):
        ignored = flip <= 15 and max(v for v in rd if v is not None) >= 75
        if ignored:
            ax.axhspan(y - 0.45, y + 0.45, color="#f5ecd9", zorder=0, lw=0)
        ax.barh(y, flip, height=0.62, color=BAR, zorder=1)
        for (name, col, dy), v in zip(READERS, rd):
            if v is not None:
                ax.scatter(v, y + dy, s=60, color=col, edgecolor=SURF, linewidth=1.5, zorder=3)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], color=INK, fontsize=10)
    ax.set_xlim(0, 104); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0", "25", "50", "75", "100%"], color=INK2, fontsize=9)
    ax.axvline(50, color=BASE, lw=1, ls=(0, (3, 3)), zorder=0)
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0); ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE); ax.tick_params(length=0)
    ax.set_title(f"{fam.capitalize()} (n = 64 states per row)", loc="left", color=INK, fontsize=11, fontweight="bold")

handles = [plt.Rectangle((0, 0), 1, 1, color=BAR, label="Model answer flips")] + \
          [plt.Line2D([], [], marker="o", ls="", markersize=8, color=c, markeredgecolor=SURF, label=n) for n, c, _ in READERS] + \
          [plt.Rectangle((0, 0), 1, 1, color="#f5ecd9", label="Readers follow, model ignores")]
fig.legend(handles=handles, loc="upper left", ncol=5, frameon=False, fontsize=9.5, labelcolor=INK, bbox_to_anchor=(0.005, 0.885))
fig.text(0.5, 0.012, "Gray bar: share of states whose answer flips to the other candidate.  Dots: share of states whose reader score moves toward the edit (dashed line = chance).",
         ha="center", fontsize=9, color=INK2)
fig.suptitle("Readers follow edits the model ignores", x=0.01, y=0.985, ha="left", fontsize=15, fontweight="bold", color=INK)
fig.text(0.01, 0.925, "Qwen3.6-27B, edits interpolated to the other state at layer 38 (α = 1), read at block 42, last token. NLA not run on the three Z4b span rows.",
         ha="left", fontsize=9, color=INK2)
fig.tight_layout(rect=(0, 0.035, 1, 0.83))
fig.savefig("results/g_agreement/z/fig_headline_readers_vs_model.png", dpi=170, facecolor=SURF)
print("ok")
