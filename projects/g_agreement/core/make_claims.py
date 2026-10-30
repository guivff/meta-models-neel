"""Generations -> claims (rule-v1), the G3 shuffled-claims table, and the blind annotation sheet.

CPU only; the one step between collection and analysis that every module shares.

    python -m projects.g_agreement.core.make_claims --module g1 [--sheet]
    python -m projects.g_agreement.core.make_claims --module g3 --shuffled [--split test|dev]
    python -m projects.g_agreement.core.make_claims --module g4

Inputs:  cache/g_agreement/gens/<module>.jsonl (INTERFACES §5), dataset/items.json, dataset/donors.json.
Outputs: results/g_agreement/claims/<module>.jsonl (INTERFACES §6; one row per gen_id),
         results/g_agreement/claims/g3_shuffled.jsonl (--shuffled; one row per (recipient, method):
             gen_id = the DONOR's cached G1 first-sample gen_id, item_id = the RECIPIENT, condition
             "shuffled_cached" — a re-scoring of cached text, never a new model call),
         results/g_agreement/claims/<module>_sheet.jsonl (--sheet; sheet_id, method, text only;
             the sheet_id -> gen_id map goes to cache/g_agreement/sheet_map_<module>.json).

The extractor never sees answer keys: `extract_claims` reads only the item's candidate strings,
entities and symbols (the rubric needs them to detect mentions); `status` is derived afterwards
by comparing the asserted value with the key. Rows whose method has no rubric (none today) are
skipped and listed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import config as C
from . import scoring as SC
from .accounting import read_jsonl

CLAIMS_DIR = C.RESULTS_DIR / "claims"
READER_METHODS = ("nla", "olens", "jlens")
CLAIMABLE = READER_METHODS + ("target", "prompt_only", "jlens_null")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def claims_for_gens(gens: list[dict[str, Any]], items: dict[str, dict[str, Any]]) -> tuple[list[dict], list[str]]:
    out, skipped = [], []
    for g in gens:
        m = g.get("method")
        if m not in CLAIMABLE:
            skipped.append(g["gen_id"])
            continue
        iid = g.get("item_id")
        if iid not in items:
            raise SystemExit(f"{g['gen_id']}: item_id {iid!r} not in items.json (null/state-free rows must "
                             f"carry the item whose candidates they are scored against)")
        it = items[iid]
        rule_method = "jlens" if m == "jlens_null" else m
        c = SC.extract_claims(SC.gen_text(g), it, rule_method, g.get("finish_reason"))
        out.append({
            "gen_id": g["gen_id"], "method": m, "item_id": iid, "condition": g.get("condition", "genuine"),
            "sample_idx": g.get("sample_idx", 0), "extractor": SC.EXTRACTOR_ID,
            "primary": c["primary"], "entities_mentioned": c["entities_mentioned"],
            "objects_mentioned": c["objects_mentioned"], "relation": c["relation"],
            "truncated": c["truncated"], "blind": True,
        })
    return out, skipped


def shuffled_claims(g1_gens: list[dict[str, Any]], items: dict[str, dict[str, Any]], donors: dict[str, Any],
                    split: str) -> list[dict[str, Any]]:
    if split == "test":
        assign = donors["assignments"]
    else:
        blk = donors.get("dev_assignments") or {}
        assign = blk.get("assignments", blk if isinstance(blk, dict) and "assignments" not in blk else {})
    first = {}
    for g in g1_gens:
        if g.get("method") in READER_METHODS and g.get("sample_idx", 0) == 0 and g.get("condition", "genuine") == "genuine":
            first[(g["item_id"], g["method"])] = g
    rows, missing = [], []
    for rec, don in sorted(assign.items()):
        if items[rec]["split"] != split:
            raise SystemExit(f"donor block for split={split} contains {rec} ({items[rec]['split']})")
        for m in READER_METHODS:
            g = first.get((don, m))
            if g is None:
                missing.append((rec, m, don))
                continue
            c = SC.extract_claims(SC.gen_text(g), items[rec], m, g.get("finish_reason"))
            rows.append({
                "gen_id": g["gen_id"], "method": m, "item_id": rec, "donor_item_id": don,
                "condition": "shuffled_cached", "extractor": SC.EXTRACTOR_ID,
                "primary": c["primary"], "entities_mentioned": c["entities_mentioned"],
                "objects_mentioned": c["objects_mentioned"], "relation": c["relation"],
                "truncated": c["truncated"], "blind": True,
                "note": "cached donor readout re-scored against the recipient key; not a new model call",
            })
    if missing:
        print(f"[shuffled] {len(missing)} (recipient, method) cells have no donor G1 first sample yet, e.g. {missing[:3]}")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", required=True, choices=["g1", "g3", "g4", "g5", "g6"])
    ap.add_argument("--gens", default=None, help="default cache/g_agreement/gens/<module>.jsonl")
    ap.add_argument("--g1-gens", default=None, help="G1 gens (for --shuffled); default cache/.../gens/g1.jsonl")
    ap.add_argument("--items", default=str(C.ITEMS_JSON))
    ap.add_argument("--donors", default=str(C.DONORS_JSON))
    ap.add_argument("--out-dir", default=str(CLAIMS_DIR))
    ap.add_argument("--sheet-cache", default=None, help="where sheet_salt/sheet_map live (default cache/g_agreement)")
    ap.add_argument("--split", choices=["test", "dev"], default="test", help="for --shuffled: which donor block")
    ap.add_argument("--shuffled", action="store_true", help="also write g3_shuffled.jsonl from G1 gens + donors")
    ap.add_argument("--sheet", action="store_true", help="also write the blind annotation sheet")
    a = ap.parse_args(argv)

    items_path = Path(a.items)
    if a.module == "g6" and a.items == str(C.ITEMS_JSON):
        items_path = C.DATASET_DIR / "items_g6.json"  # the choice family lives in its own file
    items = {it["item_id"]: it for it in json.loads(items_path.read_text(encoding="utf-8"))["items"]}
    out_dir = Path(a.out_dir)
    gens_path = Path(a.gens) if a.gens else C.GENS_DIR / f"{a.module}.jsonl"
    gens = read_jsonl(gens_path) if gens_path.exists() else []
    if a.module == "g6":  # prompt-only rows were written to a sibling file by the G3 collector
        extra = C.GENS_DIR / "g6_prompt_only.jsonl"
        if extra.exists():
            seen = {g["gen_id"] for g in gens}
            gens += [g for g in read_jsonl(extra) if g["gen_id"] not in seen]
    if gens:
        claims, skipped = claims_for_gens(gens, items)
        _write_jsonl(out_dir / f"{a.module}.jsonl", claims)
        from collections import Counter
        cnt = Counter((c["method"], c["primary"]["status"]) for c in claims)
        print(f"[{a.module}] {len(claims)} claims from {len(gens)} gens -> {out_dir / (a.module + '.jsonl')}")
        for (m, st), n in sorted(cnt.items()):
            print(f"   {m:12} {st:18} {n}")
        if skipped:
            print(f"   skipped (no rubric): {len(skipped)}")
        if a.sheet:
            rows = SC.make_blind_sheet([g for g in gens if g.get("method") in READER_METHODS], module=a.module,
                                       cache_dir=a.sheet_cache)
            _write_jsonl(out_dir / f"{a.module}_sheet.jsonl", rows)
            print(f"   blind sheet: {len(rows)} rows -> {out_dir / (a.module + '_sheet.jsonl')}")
    else:
        print(f"[{a.module}] no gens at {gens_path}")
    if a.shuffled:
        g1_path = Path(a.g1_gens) if a.g1_gens else C.GENS_DIR / "g1.jsonl"
        g1 = read_jsonl(g1_path) if g1_path.exists() else []
        donors = json.loads(Path(a.donors).read_text(encoding="utf-8"))
        rows = shuffled_claims(g1, items, donors, a.split)
        _write_jsonl(out_dir / "g3_shuffled.jsonl", rows)
        print(f"[g3] shuffled (cached reassignment, split={a.split}): {len(rows)} rows -> {out_dir / 'g3_shuffled.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
