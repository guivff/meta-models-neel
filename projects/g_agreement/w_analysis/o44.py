"""O44 analysis: Oracle (and J-lens) at block 44 vs block 42 on X1 and W1 (PREREG_WV.md 2026-10-13 entry). CPU.

    python -m projects.g_agreement.w_analysis.o44 [--root <repo with cache/>] [--n-boot 1000 --seed 0]
    -> results/g_agreement/w/o44/{o44.md, o44.csv, o44_summary.json, fig_o44.png}
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from projects.g_agreement.core import analysis_utils as U

FAMS_X1 = ("ownership", "mapping", "language", "tense")
FAMS_W = ("ownership", "mapping")
DIRS = ("d_cm", "d_pw", "d_J", "d_res", "full")
READERS = ("olens", "jlens")
THRESH = 0.10


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def x1_flags(rows: list[dict], pairs: dict[str, dict]) -> dict[str, list]:
    """family -> [(pair_id, win)] with win = lo_A + lo_B > 0."""
    lo = {r["item_id"]: r.get("lo") for r in rows}
    out = defaultdict(list)
    for pid, p in sorted(pairs.items()):
        a, b = lo.get(p["A"]), lo.get(p["B"])
        out[p["family"]].append((pid, None if a is None or b is None else (a + b) > 0))
    return out


def rate(flags, nb, sd):
    r = U.pair_rate(flags, nb, sd)
    return {"k": r.k, "n": r.n, "p": r.p, "lo": r.lo, "hi": r.hi}


def diff(fa, fb, nb, sd):
    d, lo, hi = U.pair_rate_diff(fa, fb, nb, sd)
    return {"d": d, "lo": lo, "hi": hi, "excl0": bool(lo > 0 or hi < 0), "flag": bool(abs(d) >= THRESH and (lo > 0 or hi < 0))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    R, nb, sd = a.root, a.n_boot, a.seed
    C, OUT = R / "cache/g_agreement", R / "results/g_agreement/w/o44"
    OUT.mkdir(parents=True, exist_ok=True)
    S: dict = {"x1": {}, "w1": {}, "checks": {}}
    rows_csv = []
    # ---------------- X1
    old = [r for r in jl(C / "x/x1_lo.jsonl") if "|mean|" not in r["key"]]
    new = jl(C / "w/o44/x1_lo44.jsonl")
    pairs = {}
    for r in new:
        pairs.setdefault(r["pair_id"], {"family": r["family"]})[r["version"]] = r["item_id"]
    for rd in READERS:
        f42o = x1_flags([r for r in old if r["reader"] == rd], pairs)
        f42n = x1_flags([r for r in new if r["reader"] == rd and r["layer"] == 42], pairs)
        f44 = x1_flags([r for r in new if r["reader"] == rd and r["layer"] == 44], pairs)
        lo_old = {r["item_id"]: r.get("lo") for r in old if r["reader"] == rd}
        lo_new = {r["item_id"]: r.get("lo") for r in new if r["reader"] == rd and r["layer"] == 42}
        dl = [abs(lo_old[i] - lo_new[i]) for i in lo_new if lo_old.get(i) is not None and lo_new[i] is not None]
        S["checks"][f"x1_{rd}_L42_rescore_max_abs_dlo"] = max(dl) if dl else None
        for fam in FAMS_X1:
            c = {"L42": rate(f42o[fam], nb, sd), "L42_rescore": rate(f42n[fam], nb, sd), "L44": rate(f44[fam], nb, sd), "diff_44_minus_42": diff(f44[fam], f42o[fam], nb, sd)}
            S["x1"][f"{rd}|{fam}"] = c
            rows_csv.append({"part": "X1 natural win", "reader": rd, "family": fam, "cell": "within-pair win", **{f"{k}_{x}": v[x] for k, v in (("L42", c["L42"]), ("L44", c["L44"])) for x in ("p", "lo", "hi")},
                             "n_pairs": c["L44"]["n"], "diff": c["diff_44_minus_42"]["d"], "diff_lo": c["diff_44_minus_42"]["lo"], "diff_hi": c["diff_44_minus_42"]["hi"], "flag": c["diff_44_minus_42"]["flag"]})
    # ---------------- W1
    beh = [r for r in jl(C / "w/s2_behaviour.jsonl") if r["family"] in FAMS_W]
    nat = {(r["pair_id"], r["source"]): r["key"] for r in beh if r["direction"] == "natural"}
    flips = defaultdict(list)
    lte: dict = {}
    for r in jl(C / "w/s3_lo.jsonl"):
        if r.get("reader") in READERS and r.get("unit") == "S2" and int(r.get("read_layer") or 42) == 42:
            lte[(r["reader"], 42, r["entry_key"])] = r.get("lo_toward_edit")
    for r in jl(C / "w/o44/s3_lo44.jsonl"):
        if r.get("reader") in READERS and str(r.get("unit", "")).startswith("S2"):
            lte[(r["reader"], int(r["read_layer"]), r["entry_key"])] = r.get("lo_toward_edit")

    def follow(rd, L, e):
        a_ = lte.get((rd, L, e["key"]))
        b_ = lte.get((rd, L, nat.get((e["pair_id"], e["source"]))))
        return None if a_ is None or b_ is None else (a_ - b_) > 0

    cells = []
    for fam in FAMS_W:
        for d in DIRS:
            cells.append((fam, d, [r for r in beh if r["family"] == fam and r["direction"] == d and float(r["alpha"]) == 1.0]))
        cells.append((fam, "random (pooled)", [r for r in beh if r["family"] == fam and r["direction"].startswith("rand")]))
    for fam, d, es in cells:
        S["w1"].setdefault(f"model|{fam}|{d}", {"flip": sum(bool(e.get("flipped_to_other")) and bool(e.get("coherent", True)) for e in es), "n": len(es)})
        for rd in READERS:
            f42 = [(e["pair_id"], follow(rd, 42, e)) for e in es]
            f44 = [(e["pair_id"], follow(rd, 44, e)) for e in es]
            c = {"L42": rate(f42, nb, sd), "L44": rate(f44, nb, sd), "diff_44_minus_42": diff(f44, f42, nb, sd)}
            S["w1"][f"{rd}|{fam}|{d}"] = c
            rows_csv.append({"part": "W1 follow (alpha 1)", "reader": rd, "family": fam, "cell": d, **{f"{k}_{x}": v[x] for k, v in (("L42", c["L42"]), ("L44", c["L44"])) for x in ("p", "lo", "hi")},
                             "n_pairs": c["L44"]["n"], "diff": c["diff_44_minus_42"]["d"], "diff_lo": c["diff_44_minus_42"]["lo"], "diff_hi": c["diff_44_minus_42"]["hi"], "flag": c["diff_44_minus_42"]["flag"]})
    ck = OUT / "checks.json"
    if (C / "w/o44/checks.json").exists():
        S["checks"]["pod"] = json.loads((C / "w/o44/checks.json").read_text())
    oflags = [r for r in rows_csv if r["reader"] == "olens" and r["flag"]]
    S["verdict"] = ("L42 Oracle conclusions STAND: no cell changes by >= 10 points with the paired CI excluding 0" if not oflags else
                    "CHANGED cells (L44 becomes the primary Oracle value): " + "; ".join(f"{r['part']} {r['family']} {r['cell']} {100*r['L42_p']:.0f}% -> {100*r['L44_p']:.0f}%" for r in oflags))
    (OUT / "o44_summary.json").write_text(json.dumps(S, indent=1, default=float))
    with (OUT / "o44.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_csv[0].keys())); w.writeheader(); w.writerows(rows_csv)
    pct = lambda c: f"{100*c['p']:.0f}% [{100*c['lo']:.0f}, {100*c['hi']:.0f}]"  # noqa: E731
    L = ["# O44 — Oracle lens at block 44 (on its training grid) vs block 42 (off-grid)", "",
         "Pre-registered in PREREG_WV.md (2026-10-13). Same states and scoring as X1 and W1; only the read layer (and the layer named in the Oracle's prompt) changes. "
         f"Pair bootstrap {nb} (seed {sd}); difference = L44 − L42 on the same pairs. Rule: a cell changes if |Δ| ≥ 10 points and the CI excludes 0.", "",
         f"**Verdict (Oracle): {S['verdict']}.**", "", "## X1 natural bindings (within-pair win)", "",
         "| reader | family | L42 (original) | L42 re-scored | L44 | Δ (44 − 42) [CI] |", "|---|---|---|---|---|---|"]
    for rd in READERS:
        for fam in FAMS_X1:
            c = S["x1"][f"{rd}|{fam}"]; dd = c["diff_44_minus_42"]
            L.append(f"| {rd} | {fam} | {pct(c['L42'])} | {pct(c['L42_rescore'])} | {pct(c['L44'])} | {100*dd['d']:+.0f} [{100*dd['lo']:+.0f}, {100*dd['hi']:+.0f}]{' **changed**' if dd['flag'] else ''} |")
    L += ["", "## W1 steering matrix, α 1 (follow = reader shift toward the edited-in candidate vs the natural state)", "",
          "| family | direction | model flips | reader | L42 | L44 | Δ (44 − 42) [CI] |", "|---|---|---|---|---|---|---|"]
    for fam, d, es in cells:
        m = S["w1"][f"model|{fam}|{d}"]
        for rd in READERS:
            c = S["w1"][f"{rd}|{fam}|{d}"]; dd = c["diff_44_minus_42"]
            L.append(f"| {fam} | {d} | {m['flip']}/{m['n']} | {rd} | {pct(c['L42'])} | {pct(c['L44'])} | {100*dd['d']:+.0f} [{100*dd['lo']:+.0f}, {100*dd['hi']:+.0f}]{' **changed**' if dd['flag'] else ''} |")
    L += ["", "## Checks", "", "```", json.dumps(S["checks"], indent=1, default=float), "```", "",
          "NLA is not part of this rerun: its injection is hard-wired to block 42."]
    (OUT / "o44.md").write_text("\n".join(L) + "\n")
    # figure: Oracle L42 vs L44 per cell
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        lab, a42, a44, e42, e44 = [], [], [], [], []
        for fam in FAMS_X1:
            c = S["x1"][f"olens|{fam}"]; lab.append(f"X1 win · {fam}"); a42.append(c["L42"]); a44.append(c["L44"])
        for fam, d, _ in cells:
            c = S["w1"][f"olens|{fam}|{d}"]; lab.append(f"W1 follow · {fam} · {d}"); a42.append(c["L42"]); a44.append(c["L44"])
        y = list(range(len(lab)))[::-1]
        fig, ax = plt.subplots(figsize=(8, 0.36 * len(lab) + 1.2))
        for yy, c42, c44 in zip(y, a42, a44):
            ax.plot([c42["p"], c44["p"]], [yy, yy], color="#bbbbbb", lw=1, zorder=1)
            ax.errorbar(c42["p"], yy + 0.12, xerr=[[c42["p"] - c42["lo"]], [c42["hi"] - c42["p"]]], fmt="o", color="#888888", ms=4, capsize=2, label="block 42 (off-grid)" if yy == y[0] else None)
            ax.errorbar(c44["p"], yy - 0.12, xerr=[[c44["p"] - c44["lo"]], [c44["hi"] - c44["p"]]], fmt="o", color="#2a5bd7", ms=4, capsize=2, label="block 44 (on-grid)" if yy == y[0] else None)
        ax.axvline(0.5, color="#999999", lw=0.8, ls=":")
        ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=8); ax.set_xlim(0, 1.02)
        ax.set_xlabel("Oracle lens: share of pairs (win) or states (follow), pair-bootstrap 95% CI")
        ax.set_title("Oracle lens at block 44 vs 42 (same states)", fontsize=10); ax.legend(fontsize=8, loc="lower right")
        fig.tight_layout(); fig.savefig(OUT / "fig_o44.png", dpi=150); plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        print(f"[o44] figure skipped: {exc}")
    print("\n".join(L[:6]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
