#!/usr/bin/env python
"""G4 pre-selection (INTERFACES.md §3): one TEST pair per family, chosen by seed before any test
output exists. Writes dataset/g4_pairs.json with `chosen_before_test_outputs: true` and a timestamp.

The script refuses to (re)write the selection if a G1 generation file already exists in the cache
(cache/g_agreement/gens/g1.jsonl), unless --force is given; a forced rewrite is recorded as such.

Usage: .venv/bin/python projects/g_agreement/dataset/g4_selection.py [--seed 20261007]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import random
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_ITEMS = os.path.join(HERE, "items.json")
DEFAULT_OUT = os.path.join(HERE, "g4_pairs.json")
G1_GENS = os.path.join(REPO, "cache", "g_agreement", "gens", "g1.jsonl")
DEFAULT_SEED = 20261007


def select_pairs(items: List[dict], seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    rng = random.Random(seed)
    families: List[str] = []
    for it in items:
        if it["family"] not in families:
            families.append(it["family"])
    pairs, item_ids = [], []
    for fam in families:
        test_pairs = sorted({it["pair_id"] for it in items if it["family"] == fam and it["split"] == "test"})
        if len(test_pairs) != 4:
            raise RuntimeError(f"{fam}: expected 4 test pairs, found {len(test_pairs)}")
        chosen = rng.choice(test_pairs)
        pairs.append(chosen)
        item_ids += sorted(it["item_id"] for it in items if it["pair_id"] == chosen)
    assert len(pairs) == 4 and len(item_ids) == 8
    return {"seed": seed, "pairs": pairs, "item_ids": item_ids,
            "chosen_before_test_outputs": not os.path.exists(G1_GENS),
            "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "decided_by": "seed only (random.Random(seed).choice over the sorted test pair ids of each family)"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--items", default=DEFAULT_ITEMS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true", help="rewrite even if G1 test outputs already exist")
    args = ap.parse_args()
    if os.path.exists(G1_GENS) and not args.force:
        raise SystemExit(f"refusing: test outputs already exist at {G1_GENS}; selection must precede them (--force to override)")
    with open(args.items, encoding="utf-8") as f:
        data = json.load(f)
    out = select_pairs(data["items"], args.seed)
    out["items_sha256"] = data["meta"]["sha256_items"]
    if args.force and os.path.exists(G1_GENS):
        out["chosen_before_test_outputs"] = False
        out["forced_rewrite"] = True
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {args.out}: {out['pairs']} (chosen_before_test_outputs={out['chosen_before_test_outputs']})")


if __name__ == "__main__":
    main()
