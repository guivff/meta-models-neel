"""Apply BRIEF_BLINDSPOT's 2026-10-23 08:50 W4 rule to per-row results.

No scoring or eligibility is recomputed. prepare_swaps selects the tested rows;
its count-like/state-like rows are the blind-spot group. Each row has one vote.
Site and inference scope (including OFF-NATIVE/EXPLORATORY) remain unchanged.

Usage from the repository root:
    python -m projects.g_agreement.blindspot.w4_aggregate \
        --input ANALYSIS/metrics.swap.json --out NEW_AGGREGATE_DIRECTORY
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time


RULE = (
    "BRIEF_BLINDSPOT 2026-10-23 08:50 §73: per-row rule holds on >=70% "
    "of tested blind-spot rows AND >=70% of tested semantic rows."
)


def aggregate_swap_scores(per_row: dict) -> dict:
    """Aggregate frozen rule_met booleans; preserve every per-row result.

    Empty groups cannot satisfy the rule and yield NOT MET. Malformed input is
    rejected rather than silently excluding rows from either denominator.
    """
    if not isinstance(per_row, dict) or not isinstance(per_row.get("rows"), list):
        raise ValueError("expected analyse_swap_scores output with a rows list")
    groups = {"blindspot": [], "semantic": []}
    seen = set()
    for row in per_row["rows"]:
        if not isinstance(row, dict):
            raise ValueError("each tested row must be an object")
        feature = row.get("feature")
        if not isinstance(feature, str) or not feature.strip() or feature in seen:
            raise ValueError("tested row features must be nonempty and unique")
        seen.add(feature)
        row_class = row.get("row_class")
        if row_class not in ("count-like", "state-like", "semantic"):
            raise ValueError("unknown tested row_class")
        if type(row.get("rule_met")) is not bool:
            raise ValueError("each tested row needs a boolean rule_met")
        group = "semantic" if row_class == "semantic" else "blindspot"
        groups[group].append(row["rule_met"])

    summary = {}
    for group, flags in groups.items():
        n, n_met = len(flags), sum(flags)
        summary[group] = {
            "n": n,
            "n_met": n_met,
            "fraction": n_met / n if n else None,
            # Exact inclusive threshold; no rounding or pooling across groups.
            "rule_met": bool(n and 10 * n_met >= 7 * n),
        }
    return {
        **deepcopy(per_row),
        "per_row_status": per_row.get("status"),
        "status": "CONFIRMED" if all(g["rule_met"] for g in summary.values()) else "NOT MET",
        "aggregation_note": RULE,
        "aggregation": summary,
    }


def main(argv=None):
    from . import protocol as P

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="per-row metrics.swap.json")
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    raw = args.input.read_bytes()
    input_sha = hashlib.sha256(raw).hexdigest()
    seal = args.input.parent / "SCORE_SEAL.json"
    if not seal.is_file():
        raise ValueError("upstream analysis SCORE_SEAL.json is required")
    verified = P.verify(args.input.parent, seal.name)
    if verified.get("status") != "SCORES_SEALED_ANALYSIS_SWAP":
        raise ValueError("upstream seal must have status SCORES_SEALED_ANALYSIS_SWAP")
    if verified["files"].get(args.input.name) != input_sha:
        raise ValueError("input is not covered by its analysis score seal")
    result = aggregate_swap_scores(json.loads(raw))
    args.out.mkdir(parents=True, exist_ok=False)
    P.dump(args.out / "metrics.swap_aggregate.json", result)
    P.dump(args.out / "provenance.json", {
        "input_file": str(args.input), "input_sha256": input_sha,
        "input_score_seal_sha256": P.sha(seal),
        "script_sha256": P.sha(__file__), "brief_sha256": P.sha(P.ROOT / P.BRIEF),
        "rule": RULE,
    })
    # Keep this CPU postprocessing receipt with its own sealed outputs.
    P.dump(args.out / "run.json", {
        "step": "w4_aggregate", "status": "COMPLETE", "started": started,
        "wall_s": time.perf_counter() - start, "seed": P.SEED,
        "command": sys.argv if argv is None else [__name__, *map(str, argv)],
        "gpu_hours": 0, "model_forwards": 0,
    })
    P.seal(args.out, ["metrics.swap_aggregate.json", "provenance.json", "run.json"],
           "SCORES_SEALED_W4_AGGREGATE")


if __name__ == "__main__":
    main()
