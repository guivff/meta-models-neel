"""F2-2 analysis (Mac): model flip and reader follow per arm x dose; pre-registered rule (BRIEF_Z.md, 2026-10-14).

    python -m projects.g_agreement.f2.t2_analyze [--root .]
-> results/g_agreement/f2/t2/{t2.md, t2.csv, t2_summary.json, fig_t2.png}
Flip = parsed answer is the other candidate (Wilson over 64 states; pair bootstrap as secondary). Follow = reader's log-odds toward the
other candidate rises vs the same state's natural row (pair bootstrap over 32 pairs, 1,000, seed 0).
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ARMS = ("full", "J_scaled", "perp_scaled", "rand_scaled", "J_only")
ALPHAS = (0.25, 0.5, 1.0, 1.5, 2.0)
READERS = (("olens", 44), ("olens", 42), ("jlens", 42), ("jlens", 44), ("nla", 42))
LABEL = {"full": "full swap Δ", "J_scaled": "J-space part, rescaled to ‖Δ‖", "perp_scaled": "non-J part, rescaled to ‖Δ‖",
         "rand_scaled": "random direction at ‖Δ‖ (K = 2)", "J_only": "J-space part, unscaled (Y2)"}


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def boot(by_pair, nb=1000, seed=0):
    pids = [p for p in by_pair if by_pair[p]]
    if not pids:
        return float("nan"), float("nan"), float("nan")
    est = float(np.mean([x for p in pids for x in by_pair[p]]))
    rng = np.random.default_rng(seed)
    bs = [np.mean([x for i in rng.choice(len(pids), len(pids)) for x in by_pair[pids[i]]]) for _ in range(nb)]
    return est, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    a = ap.parse_args()
    C, OUT = a.root / "cache/g_agreement/f2/t2", a.root / "results/g_agreement/f2/t2"
    OUT.mkdir(parents=True, exist_ok=True)
    beh = [json.loads(x) for x in (C / "behaviour.jsonl").read_text().splitlines() if x.strip()]
    lo = {}
    for x in (C / "lo.jsonl").read_text().splitlines():
        if x.strip():
            r = json.loads(x)
            lo[(r["reader"], r["layer"], r["entry"])] = r["lo_own"]
    nat = {(r["pair_id"], r["source"]): r for r in beh if r["arm"] == "natural"}
    S = {"flip": {}, "follow": {}, "lo_model": {}, "checks": {}}
    S["checks"]["natural_kept"] = sum(r["kept"] for r in nat.values()), len(nat)
    rows = []
    for arm in ARMS:
        for al in ALPHAS:
            es = [r for r in beh if (r["arm"] == arm or (arm == "rand_scaled" and r["arm"].startswith("rand_scaled"))) and float(r["alpha"]) == al]
            k = sum(bool(r["flipped"]) for r in es)
            p, lo_, hi = wilson(k, len(es))
            S["flip"][f"{arm}|{al}"] = {"k": k, "n": len(es), "p": p, "lo": lo_, "hi": hi}
            dl = defaultdict(list)
            for r in es:
                n0 = nat[(r["pair_id"], r["source"])]
                if r["lo_model"] is not None and n0["lo_model"] is not None:
                    dl[r["pair_id"]].append(r["lo_model"] - n0["lo_model"])
            S["lo_model"][f"{arm}|{al}"] = boot(dl)
            row = {"arm": arm, "alpha": al, "n": len(es), "flip": p, "flip_lo": lo_, "flip_hi": hi, "dlo_model": S["lo_model"][f"{arm}|{al}"][0]}
            for rd, L in READERS:
                fp = defaultdict(list)
                for r in es:
                    n0 = nat[(r["pair_id"], r["source"])]
                    e, z = lo.get((rd, L, r["key"])), lo.get((rd, L, n0["key"]))
                    if e is not None and z is not None:
                        fp[r["pair_id"]].append(float((-e) - (-z) > 0))
                f = boot(fp)
                S["follow"][f"{rd}@{L}|{arm}|{al}"] = f
                row[f"follow_{rd}{L}"], row[f"follow_{rd}{L}_lo"], row[f"follow_{rd}{L}_hi"] = f
            rows.append(row)
    fj, ff = S["flip"]["J_scaled|1.0"], S["flip"]["full|1.0"]
    reduces = fj["p"] >= ff["p"] - 0.10
    first50 = next((al for al in ALPHAS if S["flip"][f"J_scaled|{al}"]["p"] >= 0.5), None)
    S["decision"] = {"J_scaled_flip_a1": fj, "full_flip_a1": ff, "reduces_to_sensitivity": reduces, "J_scaled_first_alpha_ge_50pct": first50}
    (OUT / "t2_summary.json").write_text(json.dumps(S, indent=1, default=float))
    with (OUT / "t2.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    pc = lambda t: f"{100*t[0]:.0f}% [{100*t[1]:.0f}, {100*t[2]:.0f}]"  # noqa: E731
    dec = (f"REDUCES TO SENSITIVITY: the norm-matched J-space part flips the model {100*fj['p']:.0f}% at α 1, within 10 points of the full edit "
           f"({100*ff['p']:.0f}%)" if reduces else
           f"DOES NOT reduce to sensitivity: the norm-matched J-space part flips the model {100*fj['p']:.0f}% [{100*fj['lo']:.0f}, {100*fj['hi']:.0f}] at α 1 "
           f"vs {100*ff['p']:.0f}% for the full edit; first dose with ≥ 50% flips: {first50 if first50 else 'none up to α 2'}")
    L = ["# F2-2 — norm-matched split edit (ownership, 32 pairs × 2 sources = 64 states)", "",
         "Pre-registered in BRIEF_Z.md (2026-10-14). Edit at block 38, all positions, h + α·δ. Every arm except J_only has the full edit's norm at every position. "
         "Flip: Wilson 95% CI over 64 states. Follow: reader log-odds toward the other candidate rises vs the natural state; pair bootstrap over 32 pairs.", "",
         f"**Decision: {dec}.**", "", f"Natural states answered correctly: {S['checks']['natural_kept'][0]}/{S['checks']['natural_kept'][1]}.", "",
         "## Model flip rate by dose", "", "| arm | " + " | ".join(f"α {al}" for al in ALPHAS) + " |", "|---|" + "---|" * len(ALPHAS)]
    for arm in ARMS:
        L.append(f"| {LABEL[arm]} | " + " | ".join(f"{S['flip'][f'{arm}|{al}']['k']}/{S['flip'][f'{arm}|{al}']['n']} = {100*S['flip'][f'{arm}|{al}']['p']:.0f}% [{100*S['flip'][f'{arm}|{al}']['lo']:.0f}, {100*S['flip'][f'{arm}|{al}']['hi']:.0f}]" for al in ALPHAS) + " |")
    L += ["", "## Reader follow at α 1 (and α 0.5)", "", "| arm | model flip α 1 | " + " | ".join(f"{rd}@{Ly}" for rd, Ly in READERS) + " |", "|---|---|" + "---|" * len(READERS)]
    for arm in ARMS:
        L.append(f"| {LABEL[arm]} | {100*S['flip'][f'{arm}|1.0']['p']:.0f}% | " + " | ".join(pc(S['follow'][f'{rd}@{Ly}|{arm}|1.0']) for rd, Ly in READERS) + " |")
    L += ["", "| arm (α 0.5) | model flip | " + " | ".join(f"{rd}@{Ly}" for rd, Ly in READERS) + " |", "|---|---|" + "---|" * len(READERS)]
    for arm in ARMS:
        L.append(f"| {LABEL[arm]} | {100*S['flip'][f'{arm}|0.5']['p']:.0f}% | " + " | ".join(pc(S['follow'][f'{rd}@{Ly}|{arm}|0.5']) for rd, Ly in READERS) + " |")
    L += ["", "## Mean change in the model's first-token log-odds toward the other candidate (pair bootstrap)", "", "| arm | " + " | ".join(f"α {al}" for al in ALPHAS) + " |", "|---|" + "---|" * len(ALPHAS)]
    for arm in ARMS:
        L.append(f"| {LABEL[arm]} | " + " | ".join(f"{S['lo_model'][f'{arm}|{al}'][0]:+.1f} [{S['lo_model'][f'{arm}|{al}'][1]:+.1f}, {S['lo_model'][f'{arm}|{al}'][2]:+.1f}]" for al in ALPHAS) + " |")
    (OUT / "t2.md").write_text("\n".join(L) + "\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        cols = {"full": "#1d1d1f", "J_scaled": "#2a5bd7", "perp_scaled": "#d9822b", "rand_scaled": "#999999", "J_only": "#7ea2ff"}
        panels = [("model", None)] + [(rd, Ly) for rd, Ly in (("olens", 44), ("jlens", 42), ("nla", 42))]
        fig, axes = plt.subplots(1, 4, figsize=(15, 3.8), sharey=True)
        for ax, (rd, Ly) in zip(axes, panels):
            for arm in ARMS:
                if rd == "model":
                    ys = [S["flip"][f"{arm}|{al}"] for al in ALPHAS]
                    p = [y["p"] for y in ys]; lo_ = [y["p"] - y["lo"] for y in ys]; hi = [y["hi"] - y["p"] for y in ys]
                else:
                    ys = [S["follow"][f"{rd}@{Ly}|{arm}|{al}"] for al in ALPHAS]
                    p = [y[0] for y in ys]; lo_ = [y[0] - y[1] for y in ys]; hi = [y[2] - y[0] for y in ys]
                ax.errorbar(ALPHAS, p, yerr=[lo_, hi], marker="o", ms=4, capsize=2, color=cols[arm], label=LABEL[arm] if rd == "model" else None)
            ax.set_title("model flip rate" if rd == "model" else f"{rd} @ block {Ly}: follow rate", fontsize=9)
            ax.set_xlabel("dose α"); ax.set_ylim(0, 1.02); ax.axhline(0.5 if rd != "model" else 0, color="#cccccc", lw=0.8, ls=":")
        axes[0].set_ylabel("share of states (95% CI)"); axes[0].legend(fontsize=7, loc="upper left")
        fig.suptitle("F2-2: does the J-space part flip the model once it has the full edit's norm? (ownership, 64 states)", fontsize=10)
        fig.tight_layout(); fig.savefig(OUT / "fig_t2.png", dpi=150); plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        print(f"[t2] figure skipped: {exc}")
    print("\n".join(L[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
