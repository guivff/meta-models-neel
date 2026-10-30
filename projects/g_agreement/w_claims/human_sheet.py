"""V4: build `results/g_agreement/v/human_labels.csv` — up to N claims stratified by reader (Oracle, NLA) x claim
type (input, computation) x judge truth (true, false); columns claim_id, reader, item_id, prompt_text,
model_answer_or_key, claim_text, claim_type, judge_label, human_label (blank), notes (blank).

    .venv/bin/python -m projects.g_agreement.w_claims.human_sheet --claims results/g_agreement/w/claims/claims_g1.jsonl \
        --out results/g_agreement/v/human_labels.csv --n 300 --seed 0
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

COLUMNS = ["claim_id", "reader", "item_id", "prompt_text", "model_answer_or_key", "claim_text", "claim_type",
           "judge_label", "human_label", "notes"]
STRATA = [(r, t, v) for r in ("Oracle", "NLA") for t in ("input", "computation") for v in (True, False)]


def allocate(avail: Dict[Tuple, int], n: int) -> Dict[Tuple, int]:
    """Equal quotas per stratum; strata short of their quota give the slack to the others (water-filling)."""
    quota = {k: 0 for k in avail}
    remaining, open_ = n, [k for k in avail if avail[k] > 0]
    while remaining > 0 and open_:
        share = max(remaining // len(open_), 1)
        progressed = False
        for k in list(open_):
            take = min(share, avail[k] - quota[k], remaining)
            if take > 0:
                quota[k] += take
                remaining -= take
                progressed = True
            if quota[k] >= avail[k]:
                open_.remove(k)
            if remaining == 0:
                break
        if not progressed:
            break
    return quota


def build_rows(claims: List[dict], n: int = 300, seed: int = 0) -> Tuple[List[dict], Dict[str, int]]:
    rng = random.Random(seed)
    pools: Dict[Tuple, List[dict]] = {k: [] for k in STRATA}
    for c in claims:
        if not c.get("claim_text") or c.get("truth") is None:
            continue
        k = (c["reader"], c["claim_type"], bool(c["truth"]))
        if k in pools:
            pools[k].append(c)
    for v in pools.values():
        v.sort(key=lambda c: c["claim_id"])
        rng.shuffle(v)
    quota = allocate({k: len(v) for k, v in pools.items()}, n)
    chosen = [c for k in STRATA for c in pools[k][:quota[k]]]
    rng.shuffle(chosen)
    rows = []
    for c in chosen:
        ans = c.get("actual_answer")
        key = c.get("answer")
        mak = (f"model answer: {ans!r}; key: {key!r}" if ans is not None else f"key: {key!r}")
        if c.get("candidates"):
            mak += f"; candidates: {c['candidates']}"
        rows.append({"claim_id": c["claim_id"], "reader": c["reader"], "item_id": c["item_id"],
                     "prompt_text": c.get("prompt_text", ""), "model_answer_or_key": mak,
                     "claim_text": c["claim_text"], "claim_type": c["claim_type"], "judge_label": c["judge_label"],
                     "human_label": "", "notes": ""})
    counts = {f"{k[0]}/{k[1]}/{'true' if k[2] else 'false'}": f"{quota[k]}/{len(pools[k])}" for k in STRATA}
    return rows, counts


def write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    claims = [json.loads(l) for p in a.claims for l in Path(p).read_text().splitlines() if l.strip()]
    rows, counts = build_rows(claims, a.n, a.seed)
    write_csv(a.out, rows)
    print(json.dumps({"written": len(rows), "requested": a.n, "per_stratum (taken/available)": counts}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
