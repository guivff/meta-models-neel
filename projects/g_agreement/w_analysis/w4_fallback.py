"""W4 fallback (deviation 2026-10-12): S4 samples were never produced, so the consistency filter is applied to the
G4 repeat claims (8 items x 2 readers x 2 samples, judged in Track C) with the W4 matcher. 'Kept' = the claim recurs
in the other sample of the same reader/item (agreement 2 of 2). Michael Kenney's own 8-sample data is analysed in V3.

    python -m projects.g_agreement.w_analysis.w4_fallback [--claims results/g_agreement/w/claims/claims_g4.jsonl] [--out results/g_agreement/w/w4]
"""
from __future__ import annotations
import argparse, csv, json
from collections import defaultdict
from pathlib import Path
from projects.g_agreement.w_analysis import w4_consistency as W4
from projects.g_agreement.w_claims.stats import precision_item_bootstrap, wilson

ROOT = Path(__file__).resolve().parents[3]
CLAIMS = ROOT / "results/g_agreement/w/claims/claims_g4.jsonl"
OUT = ROOT / "results/g_agreement/w/w4"


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--claims", type=Path, default=CLAIMS)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--n-boot", type=int, default=1000)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args(argv)
    raw = [json.loads(l) for l in a.claims.read_text().splitlines() if l.strip()]
    for c in raw:
        c["condition"] = "natural"                       # G4 rows are tagged 'repeat'; they are natural states sampled twice
    ns = {}
    for c in raw:
        ns.setdefault((c["reader"], c["item_id"]), set()).add(int(c["sample_idx"]))
    ns = {k: len(v) for k, v in ns.items()}
    results, rows = {}, []
    for mode in ("primary", "strict", "lenient"):
        ann = W4.annotate_claims(raw)
        W4.agreement_counts(ann, mode, ns)
        results[mode] = {}
        for rd in sorted({c["reader"] for c in ann}):
            results[mode][rd] = {}
            for t in ("input", "computation"):
                cs = [c for c in ann if c["reader"] == rd and c.get("claim_type") == t]
                kept = [c for c in cs if c["kept"]]
                allp = precision_item_bootstrap([c["item_id"] for c in cs], [c.get("truth") for c in cs], a.n_boot, a.seed)
                kp = precision_item_bootstrap([c["item_id"] for c in kept], [c.get("truth") for c in kept], a.n_boot, a.seed)
                auc = W4.auroc_item_bootstrap([c["item_id"] for c in cs], [c["agreement"] for c in cs], [c.get("truth") for c in cs], a.n_boot, a.seed) if cs else None
                share = wilson(len(kept), len(cs))
                d = {"n_claims": len(cs), "n_kept": len(kept), "kept_share": share[0], "all": allp, "kept": kp, "auroc": auc}
                results[mode][rd][t] = d
                rows.append({"matcher": mode, "reader": rd, "claim_type": t, "n_claims": len(cs), "n_kept": len(kept), "kept_share": round(share[0], 3) if cs else None,
                             "precision_all": allp["precision"], "precision_all_lo": allp["lo"], "precision_all_hi": allp["hi"],
                             "precision_kept": kp["precision"], "precision_kept_lo": kp["lo"], "precision_kept_hi": kp["hi"],
                             "auroc_agreement": (auc or {}).get("auroc"), "auroc_lo": (auc or {}).get("lo"), "auroc_hi": (auc or {}).get("hi")})
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "w4.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    (a.out / "w4_summary.json").write_text(json.dumps({"inputs": str(a.claims), "n_samples": {f"{k[0]}|{k[1]}": v for k, v in ns.items()}, "results": results}, indent=1, default=str))

    def f(x):
        return "n/a" if x is None or x.get("precision") is None else f"{100*x['precision']:.0f}% [{100*x['lo']:.0f}, {100*x['hi']:.0f}] (n={x['n_claims']})"
    L = ["# W4 (fallback) — consistency filter on the G4 repeat claims", "",
         "**Deviation (2026-10-12).** The pre-registered W4 runs Michael Kenney's >= 2-of-8 consistency filter on the S4 free-text samples. "
         "S4 was never produced: the pod's prioritized resume chain reached the 150-min budget guard after S3 and S3v1 and went straight to S5. "
         "This fallback applies the same matcher (`w4_consistency.claims_match`, primary mode; strict/lenient as sensitivity) to the Track C "
         "G4 repeat claims: 8 test items x 2 readers (Oracle lens, NLA) x 2 samples, judged by gemini-3.8-flash (κ 0.86 vs human on G1). "
         "With 2 samples per readout, 'kept' means the claim recurs in the other sample (agreement 2/2); the >= 7/8 statistics are undefined. "
         "Michael's own 8-sample data (500 NLA states) is analysed in `results/g_agreement/v/v3.md`.", "",
         "| matcher | reader | claim type | claims | kept share | precision all [CI] | precision kept [CI] | AUROC agreement vs correct [CI] |", "|---|---|---|---|---|---|---|---|"]
    for mode in ("primary", "strict", "lenient"):
        for rd, R in results[mode].items():
            for t, d in R.items():
                auc = d["auroc"]
                aucs = "n/a" if not auc or auc.get("auroc") is None else f"{auc['auroc']:.2f} [{auc['lo']:.2f}, {auc['hi']:.2f}]"
                L.append(f"| {mode} | {rd} | {t} | {d['n_claims']} | {100*d['kept_share']:.0f}% ({d['n_kept']}) | {f(d['all'])} | {f(d['kept'])} | {aucs} |")
    L += ["", "CI: item-level bootstrap (1000 resamples, seed 0); unverifiable claims excluded from precision. AUROC uses the W4 tie-aware formula on the agreement count (1 or 2).", "",
          "Reading: with 8 items per reader this is a pilot. Compare with Michael's numbers on his data: input-claim AUROC 0.90, internal 0.75; "
          "input false share 38% (all) vs 13% (kept)."]
    (a.out / "w4.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[8:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
