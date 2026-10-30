#!/usr/bin/env python
"""G3 donor assignment (INTERFACES.md §2): for every TEST item, a donor test item from the same
family whose cached readouts will be re-assigned to the recipient ("shuffled" arm).

Constraints (all checked, script fails loudly if any cannot be met):
  1. same family;
  2. donor pair_id != recipient pair_id (so both versions of the recipient pair are excluded);
  3. the assignment within a family is a permutation (every item donates exactly once);
  4. label balance WITHOUT forcing donor label != recipient label: within a family, among the 4
     recipients whose answer is the first-listed candidate, exactly 2 donors carry a first-listed
     answer and 2 a second-listed answer; same for the 4 second-listed recipients. Hence donor
     label == recipient label for exactly half of the recipients.
The permutation is decided by the seed only (seeded shuffles, first one satisfying the
constraints is kept; the number of attempts is recorded). No readout is consulted.

Usage: .venv/bin/python projects/g_agreement/dataset/donors.py [--seed 20261007] [--items items.json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import random
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ITEMS = os.path.join(HERE, "items.json")
DEFAULT_OUT = os.path.join(HERE, "donors.json")
DEFAULT_SEED = 20261007
MAX_ATTEMPTS = 100_000


class DonorConstraintError(RuntimeError):
    pass


def _label(item: dict) -> int:
    return item["primary"]["candidates"].index(item["primary"]["answer"])


def _family_ok(recips: List[dict], donors: List[dict]) -> bool:
    if any(r["pair_id"] == d["pair_id"] for r, d in zip(recips, donors)):
        return False
    for rl in (0, 1):
        dl = [_label(d) for r, d in zip(recips, donors) if _label(r) == rl]
        if len(dl) == 0:
            continue
        if dl.count(0) != dl.count(1):
            return False
    return True


def build_assignments(items: List[dict], seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    rng = random.Random(seed)
    families = sorted({it["family"] for it in items}, key=lambda f: [it["family"] for it in items].index(f))
    assignments: Dict[str, str] = {}
    attempts: Dict[str, int] = {}
    for fam in families:
        recips = sorted([it for it in items if it["family"] == fam and it["split"] == "test"], key=lambda x: x["item_id"])
        if len(recips) % 4:
            raise DonorConstraintError(f"{fam}: {len(recips)} test items; label balance needs a multiple of 4")
        donors = list(recips)
        for n in range(1, MAX_ATTEMPTS + 1):
            rng.shuffle(donors)
            if _family_ok(recips, donors):
                attempts[fam] = n
                break
        else:
            raise DonorConstraintError(f"{fam}: no permutation satisfied the constraints in {MAX_ATTEMPTS} attempts")
        for r, d in zip(recips, donors):
            assignments[r["item_id"]] = d["item_id"]
    checks = run_checks(items, assignments)
    dev = build_dev_assignments(items, seed)
    checks["dev_assignments_cross_family"] = all(
        idx_fam(items, r) != idx_fam(items, d) for r, d in dev["assignments"].items())
    return {"seed": seed, "assignments": assignments, "checks": checks, "attempts_per_family": attempts,
            "dev_assignments": dev,
            "created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "decided_by": "seed only; no readout or target output consulted"}


def idx_fam(items: List[dict], item_id: str) -> str:
    return next(it["family"] for it in items if it["item_id"] == item_id)


def build_dev_assignments(items: List[dict], seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    """Development-only plumbing (coordinator decision 2026-10-07): the 8 dev items get donors too,
    so the G3 shuffled-arm code path can be exercised on dev. With one dev pair per family the
    'other pair, same family' rule is unsatisfiable, so dev donors are drawn ACROSS families
    (seeded permutation with donor family != recipient family). Never scored, never reported."""
    rng = random.Random(seed + 1)
    dev = sorted([it for it in items if it["split"] == "dev"], key=lambda x: x["item_id"])
    donors = list(dev)
    for n in range(1, MAX_ATTEMPTS + 1):
        rng.shuffle(donors)
        if all(r["family"] != d["family"] for r, d in zip(dev, donors)):
            break
    else:
        raise DonorConstraintError("dev: no cross-family permutation found")
    return {"dev_cross_family": True, "scored": False, "attempts": n,
            "note": "development-only plumbing; donors come from a different family and a different pair",
            "assignments": {r["item_id"]: d["item_id"] for r, d in zip(dev, donors)}}


def run_checks(items: List[dict], assignments: Dict[str, str]) -> Dict[str, Any]:
    idx = {it["item_id"]: it for it in items}
    test_ids = sorted(it["item_id"] for it in items if it["split"] == "test")
    checks: Dict[str, Any] = {
        "only_test_items": sorted(assignments) == test_ids and all(idx[d]["split"] == "test" for d in assignments.values()),
        "same_family": all(idx[r]["family"] == idx[d]["family"] for r, d in assignments.items()),
        "excludes_recipient_pair": all(idx[r]["pair_id"] != idx[d]["pair_id"] for r, d in assignments.items()),
        "no_self": all(r != d for r, d in assignments.items()),
        "is_permutation_within_family": True,
        "label_balance": {},
        "donor_label_equals_recipient_label_fraction": None,
    }
    same = 0
    for fam in sorted({it["family"] for it in items}):
        recips = [r for r in assignments if idx[r]["family"] == fam]
        donors = [assignments[r] for r in recips]
        if sorted(donors) != sorted(recips):
            checks["is_permutation_within_family"] = False
        fam_entry: Dict[str, Any] = {}
        ok = True
        for rl in (0, 1):
            dl = [_label(idx[assignments[r]]) for r in recips if _label(idx[r]) == rl]
            fam_entry[f"recipient_label_{rl}"] = {"donor_label_0": dl.count(0), "donor_label_1": dl.count(1)}
            ok = ok and dl.count(0) == dl.count(1)
        fam_entry["balanced"] = ok
        checks["label_balance"][fam] = fam_entry
        same += sum(_label(idx[r]) == _label(idx[assignments[r]]) for r in recips)
    checks["donor_label_equals_recipient_label_fraction"] = same / max(1, len(assignments))
    checks["all_passed"] = bool(checks["only_test_items"] and checks["same_family"] and checks["excludes_recipient_pair"]
                                and checks["no_self"] and checks["is_permutation_within_family"]
                                and all(v["balanced"] for v in checks["label_balance"].values())
                                and abs(checks["donor_label_equals_recipient_label_fraction"] - 0.5) < 1e-9)
    if not checks["all_passed"]:
        raise DonorConstraintError(json.dumps(checks, indent=1))
    return checks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--items", default=DEFAULT_ITEMS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    with open(args.items, encoding="utf-8") as f:
        data = json.load(f)
    out = build_assignments(data["items"], args.seed)
    out["items_sha256"] = data["meta"]["sha256_items"]
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {args.out}: {len(out['assignments'])} assignments, attempts {out['attempts_per_family']}")
    print(json.dumps(out["checks"], indent=1))


if __name__ == "__main__":
    main()
