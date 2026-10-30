"""Re-score the V7 PILOT probe cell at block 42 on the Mac with the fixed orientation rule (mention order read from preamble + prompt;
PREREG_WV.md 2026-10-12 10:40 UTC). Writes results/g_agreement/v/v7_pilot_probe_rescore.json and prints old vs new.

    python -m projects.g_agreement.v67_analysis.pilot_probe_rescore
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from projects.g_agreement.w_pod import common as W  # noqa: E402
from projects.g_agreement.v67_analysis import common as K  # noqa: E402


def main() -> int:
    import torch
    idx = json.loads((W.W_CACHE / "directions" / "index.json").read_text())["families"]["ownership"]
    probe = W.load_probe_shared(W.W_CACHE / "directions" / idx["shared"], layer=idx["layer"], site=idx["site"])
    items = {it["item_id"]: it for it in W.load_v7(W.ITEMS_V7)}
    old_rows = {r["item_id"]: r for r in K.read_jsonl(W.S3_LO) if r.get("reader") == "probe" and r.get("unit") == "S1" and r.get("family") == "v7"}
    out = {}
    for iid, it in items.items():
        p = W.W_CACHE / "states_L42" / f"{iid}.pt"
        if not p.exists():
            continue
        h = torch.load(p, map_location="cpu").float()
        h = h[-1] if h.dim() == 2 else h
        cands = [it["primary"]["candidates"][0], it["primary"]["candidates"][1]]
        own = it["primary"]["answer"]; other = cands[1 - cands.index(own)]
        text_new = f"{it['preamble']}\n\n{it['prompt_text']}"
        q_new = W.probe_candidate_scores(probe, h, [own, other], pair_id=it["pair_id"], prompt_text=text_new)
        q_old = W.probe_candidate_scores(probe, h, [own, other], pair_id=it["pair_id"], prompt_text=it["prompt_text"])
        lo_new = q_new["scores"][0] - q_new["scores"][1]; lo_old = q_old["scores"][0] - q_old["scores"][1]
        out[iid] = {"pair_id": it["pair_id"], "version": it["version"], "lo_own_new": lo_new, "lo_own_old": lo_old, "lo_own_old_file": (old_rows.get(iid) or {}).get("lo_own"),
                    "order_new": W.mention_order(text_new, cands), "fold": q_new["fold"]}
    by = {}
    for iid, r in out.items():
        by.setdefault(r["pair_id"], {})[r["version"]] = r
    flags_new = [(p, (d["A"]["lo_own_new"] + d["B"]["lo_own_new"]) > 0) for p, d in sorted(by.items()) if "A" in d and "B" in d]
    flags_old = [(p, (d["A"]["lo_own_old"] + d["B"]["lo_own_old"]) > 0) for p, d in sorted(by.items()) if "A" in d and "B" in d]
    rn, ro = K.rate(flags_new), K.rate(flags_old)
    agree_file = sum(1 for r in out.values() if r["lo_own_old_file"] is not None and abs(r["lo_own_old_file"] - r["lo_own_old"]) < 1e-3)
    res = {"n_items": len(out), "old_rule": ro, "new_rule": rn, "old_rule_matches_s3_file": f"{agree_file}/{sum(1 for r in out.values() if r['lo_own_old_file'] is not None)}", "per_item": out}
    (K.RESULTS_V / "v7_pilot_probe_rescore.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"[pilot probe L42] old rule {ro['k']}/{ro['n']} (file match {res['old_rule_matches_s3_file']}); new rule {rn['k']}/{rn['n']} = {100*rn['p']:.1f}% boot[{100*rn['boot_lo']:.1f}, {100*rn['boot_hi']:.1f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
