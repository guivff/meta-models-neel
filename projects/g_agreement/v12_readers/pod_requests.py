"""Write results/g_agreement/v/v12_pod_requests.json — exactly what the pod must score to complete V1 and V2.

Everything here is derivable on the Mac (item ids, candidates, the k-1 symbol, the capture file/field/index); the pod only
runs the readers. Two requests:

  v1_layer_sweep   last-token vectors of the 297 ERROR + 165 DISAGREE items (and the two control sets, cheap) at every
                   captured layer 42..62 step 2, readers jlens (native L), olens (nearest grid layer, true layer recorded),
                   olens_trueL (true-layer carrier), nla (transfer from L42); candidates (actual, other) as in Y1;
                   output rows identical to cache/g_agreement/y/y1_lo.jsonl with site "<L>:0". The existing
                   y1_site.collect reread stage produces exactly this: one command per layer and phase.
  three_way        the 146 ERROR items whose k-1 symbol differs from the model's actual answer: score the three
                   candidates [correct, actual, km1] in ONE forward batch at sites 42:0 and 48:0 (jlens/olens/nla);
                   one row per (reader, site, item) with lp per candidate.

Run: .venv/bin/python -m projects.g_agreement.v12_readers.pod_requests [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.v12_readers import common as K  # noqa: E402

Y1_LO_FIELDS = ["key", "reader", "reader_class", "site", "layer", "position", "layer_used", "layer_role", "item_id", "family", "set",
                "cand_actual", "cand_other", "text_key", "lo_actual", "lp_actual", "lp_other", "favours_actual", "templates", "unscorable",
                "format", "variants_A", "variants_B", "best_A", "best_B", "created_at", "manifest", "frozen_code_sha256", "x3_candidates_sha256",
                "y1_choice_sha256", "frozen_x"]
# per-site wall-clock from results/g_agreement/y1/log.md (H100, 730 items, batch 32): jlens 2 s, olens 20 s, olens_trueL 18 s, nla 83 s,
# plus the E3 mean-state rows (olens 20 s, nla 74 s each)
PER_SITE_SECONDS = {"jlens": 2 + 2, "olens": 20 + 20, "olens_trueL": 18 + 18, "nla": 83 + 74}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(K.DEFAULTS["items"]))
    ap.add_argument("--x3-lo", default=str(K.DEFAULTS["x3_lo"]))
    ap.add_argument("--y1-lo", default=str(K.DEFAULTS["y1_lo"]))
    ap.add_argument("--out", default=str(K.DEFAULTS["out_dir"] / "v12_pod_requests.json"))
    return ap.parse_args(argv)


def build(items: Mapping[str, dict], rows: List[dict], *, layers=K.LAYERS, caps_dir: str = "cache/g_agreement/y/y1_caps") -> Dict[str, Any]:
    sets = {s: sorted(i for i, it in items.items() if it.get("set") == s) for s in ("error", "disagree", "error_control", "agree_control")}
    done: Dict[str, List[str]] = {}
    for r in rows:
        if r["position"] == "0" and r["set"] in ("error", "disagree"):
            done.setdefault(r["site"], [])
            if r["reader"] not in done[r["site"]]:
                done[r["site"]].append(r["reader"])
    done = {k: sorted(v) for k, v in sorted(done.items())}
    pending_sites = [f"{L}:0" for L in layers if f"{L}:0" not in done or not {"jlens", "olens", "nla"} <= set(done[f"{L}:0"])]
    # 42:0 exists from the X3 capture (x3_lo); re-scoring it from y1_caps is requested as a cross-check, flagged optional
    n_layers_new = sum(1 for L in layers if f"{L}:0" not in done)
    est_min = n_layers_new * sum(PER_SITE_SECONDS.values()) / 60
    cands_three = []
    for iid in sets["error"]:
        ro = items[iid]["roles"]
        if ro["km1"] != ro["actual"]:
            cands_three.append({"item_id": iid, "candidates": {"correct": ro["correct"], "actual": ro["actual"], "km1": ro["km1"]},
                                "family": "puzzle", "trace": (items[iid].get("source") or {}).get("trace")})
    first_err = sets["error"][0]
    labels = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "candA", "candB"]
    req: Dict[str, Any] = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prereg": "projects/g_agreement/PREREG_WV.md Part V (V1 reader layer sweep, V2 re-solving); brief projects/g_agreement/manifest/brief_wv.md",
        "why": "V1 needs every reader at every captured layer 42..62 at the last token; V2 needs a third candidate (the k-1 symbol) on 146 "
               "errors. Neither can run on the Mac: J-lens needs the 3.3 GB lens file, the Oracle Lens and NLA need the 27B models/adapters "
               "(all on the pod volume).",
        "inputs": {
            "items_file": "projects/g_agreement/dataset/items_y1_selected.json",
            "captures": {"dir": caps_dir, "file": f"{caps_dir}/<item_id>.pt", "field": "acts", "dtype": "bfloat16 -> cast .float()",
                         "shape": "[11 layers, 14 positions, 5120]", "layers": list(layers), "labels": labels,
                         "last_token_index": "acts[cap['layers'].index(L), cap['labels'].index('0'), :]  (label '0' = last prompt token, "
                                             "positions[0] == n_tokens - 1; hook block_output; render chat, enable_thinking False)",
                         "loader": "projects.g_agreement.y1_site.collect.load_cap / cell_vector(cap, L, '0')",
                         "example": f"{caps_dir}/{first_err}.pt"},
            "candidates": "item['primary']['candidates'] with cand_actual = item['primary']['answer'] (the model's greedy answer) and "
                          "cand_other = the other candidate (ERROR: the correct answer; ERROR_CONTROL: the most frequent wrong symbol; "
                          "DISAGREE: the self-guess; AGREE_CONTROL: the other option)",
        },
        "requests": [
            {
                "name": "v1_layer_sweep",
                "sets": {"error": {"n": len(sets["error"]), "item_ids": sets["error"]}, "disagree": {"n": len(sets["disagree"]), "item_ids": sets["disagree"]},
                         "controls_also_scored_by_the_reread_stage": {"error_control": len(sets["error_control"]), "agree_control": len(sets["agree_control"])}},
                "layers": list(layers), "position": "0 (last prompt token)",
                "already_scored_on_mac": {"sites": done,
                                          "note": "42:0 rows come from the X3 block-42 capture (x3_lo.jsonl), not from y1_caps; 48:0 from the Y1 reread. "
                                                  "Re-scoring 42:0 from y1_caps is optional and gives the capture cross-check."},
                "pending_sites": pending_sites,
                "readers": {
                    "jlens": {"layer_arg": "L (native: the lens Jacobian for source layer L; layers_keep=[L])", "layer_role": "native",
                              "if_layer_missing_from_lens": "write the rows with unscorable=true and a 'reason' field; do not substitute a layer"},
                    "olens": {"layer_arg": "nearest grid layer in {44, 48, 52, 56, 60} (ties -> lower)", "layer_role": "nearest_grid",
                              "map": {str(L): K.nearest_grid_layer(L) for L in layers}, "record": "layer_used = the grid layer, layer = the true L"},
                    "olens_trueL": {"layer_arg": "L (true-layer carrier, off-grid allowed)", "layer_role": "true_layer_sensitivity", "optional": False},
                    "nla": {"layer_arg": None, "layer_role": "transfer_from_L42", "note": "adapter trained at L42; norm-matched injection at block 1"},
                },
                "output": {"path": "append to cache/g_agreement/y/y1_lo.jsonl (resumable, key = reader|<L>:0|item_id) — the Mac analysis reads it by default; "
                                   "or a separate file passed as --extra-lo",
                           "schema": "identical to y1_lo.jsonl rows", "fields": Y1_LO_FIELDS, "site": "<L>:0",
                           "lo_actual": "lp(cand_actual) - lp(cand_other) in the reader's native format (jlens: max cosine over single-token variants; "
                                        "olens: summed bullet log-prob; nla: mean over the family's templates)",
                           "e3_mean_rows": "the reread stage also writes one mean-state row per set (key reader|site|mean|set); keep them"},
                "commands": (
                    [f"python -m projects.g_agreement.y1_site.collect --phase A --stage reread --site {L}:0 --readers jlens,olens" for L in layers if f"{L}:0" not in done]
                    + [f"python -m projects.g_agreement.y1_site.collect --phase B --stage reread --site {L}:0 --readers nla" for L in layers if f"{L}:0" not in done]
                    + ["# optional cross-check of the X3 capture: python -m projects.g_agreement.y1_site.collect --phase A --stage reread --site 42:0 --readers jlens,olens ; "
                       "--phase B --readers nla"]),
                "estimated_gpu_minutes": round(est_min, 1),
                "estimate_basis": "per-site wall-clock of the Y1 48:0 reread on an H100 (jlens 2 s, olens 20 s x2 arms, nla 83 s, plus the E3 mean rows), x "
                                  f"{n_layers_new} new layers; excludes model loading",
                "ingest_on_mac": ["python -m projects.g_agreement.v12_readers.v1_sweep  [--extra-lo <file>]",
                                  "python -m projects.g_agreement.v12_readers.v2_resolve [--extra-lo <file>] --layers 42,48"],
            },
            {
                "name": "three_way",
                "why": "V2 three-way preference correct / actual / k-1. On 151 errors actual == k-1 (two-way rows suffice); on these 146 the k-1 symbol "
                       "needs its own reader log-prob.",
                "n_items": len(cands_three), "items": cands_three,
                "sites": ["42:0", "48:0"], "vectors": "same y1_caps last-token vectors as above (layers 42 and 48, label '0')",
                "readers": {"jlens": "layer 42 / 48 native", "olens": "nearest grid layer (44 for L42, 48 for L48); record layer_used", "nla": "transfer"},
                "procedure": "score the THREE candidate strings for one state in the same forward batch (bf16 batch composition shifts scores by up to "
                             "0.26 nats — Suraj's rule, core/scoring_lo.py); jlens: max cosine over each candidate's single-token variants; olens: summed "
                             "log-prob of '- {X}'; nla: mean over the puzzle templates of the summed log-prob; a candidate with no single-token variant "
                             "makes the jlens row unscorable",
                "output": {"path": "cache/g_agreement/v/v2_three_way.jsonl",
                           "row": {"reader": "jlens|olens|nla", "site": "42:0|48:0", "layer": 42, "layer_used": "int or null", "item_id": "xpz-....",
                                   "set": "error", "family": "puzzle", "candidates": {"correct": "E", "actual": "C", "km1": "H"},
                                   "lp": {"correct": 0.0, "actual": 0.0, "km1": 0.0}, "unscorable": False, "format": "cosine|bullet|nla_templates",
                                   "created_at": "iso"},
                           "ingest": "python -m projects.g_agreement.v12_readers.v2_resolve --three-way cache/g_agreement/v/v2_three_way.jsonl"},
                "estimated_gpu_minutes": 4.0,
            },
        ],
        "frozen_inputs": {},
    }
    return req


def run(args: argparse.Namespace) -> Dict[str, Any]:
    _, items = K.load_items(args.items)
    K.check_item_roles(items)
    rows, _ = K.load_lo_rows(args.x3_lo, args.y1_lo, [], items=items)
    req = build(items, rows)
    fz = K.DEFAULTS["frozen_wv"]
    if fz.exists():
        f = json.loads(fz.read_text())
        req["frozen_inputs"] = {k: v for k, v in f.get("inputs", {}).items() if "items_y1_selected" in k or "y1_caps_meta" in k}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(req, indent=1))
    r0, r1 = req["requests"]
    print(f"[pod_requests] {out}: v1 pending sites {r0['pending_sites']} (~{r0['estimated_gpu_minutes']} GPU-min); three_way {r1['n_items']} items")
    return req


def main(argv=None) -> Dict[str, Any]:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
