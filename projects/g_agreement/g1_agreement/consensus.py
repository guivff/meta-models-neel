"""G1 consensus view (B1-style buckets) on the 32 test states (or the 8 dev states, unfrozen).

One vote per method (NLA, Oracle lens, J-lens): the asserted candidate, or an abstention when the
claim is `unclear` or `self_contradictory`. States are bucketed by the number of agreeing votes
(1 / 2 / 3). Ties (1–1 with the third abstaining) and all-abstain states are *unresolved* and kept
out of every bucket; they are reported, not dropped. Accuracy per bucket is vs the answer key.
"Shared wrong answers" = states where ≥2 methods assert the same wrong candidate, by family.

Leave-one-out consistency (kept separate from accuracy): for method m, the consensus of the OTHER
two methods is formed without m's vote; m's vote is compared to it. Others tying or both abstaining
is unresolved; m abstaining is `own_abstain`. The consistency rate is agree / (agree + disagree).

Outputs: results/g_agreement/g1[/dev]/consensus.csv (one row per state) and consensus.json.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.g1_agreement.analyze import collect_claims_by_method  # noqa: E402

MODULE = "g1"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(U.DEFAULTS["items"]))
    ap.add_argument("--gens", default=str(U.DEFAULTS["gens_dir"] / "g1.jsonl"))
    ap.add_argument("--claims", default=str(U.DEFAULTS["claims_dir"] / "g1.jsonl"))
    ap.add_argument("--states-meta", default=str(U.DEFAULTS["states_meta"]))
    ap.add_argument("--frozen-config", default=str(U.DEFAULTS["frozen_config"]))
    ap.add_argument("--out", default=None)
    ap.add_argument("--split", choices=U.SPLITS, default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    return ap.parse_args(argv)


def bucket_table(items, item_ids, cbm, pid, nb, sd) -> dict:
    """Pure function of the votes so tests can call it directly. Returns the per-state rows and the summary."""
    rows: List[dict] = []
    for i in item_ids:
        votes = {m: U.vote(cbm[m][i]) for m in U.METHODS}
        c = U.consensus(votes)
        key = items[i]["primary"]["answer"]
        correct = None if not c.resolved else U.normalise_answer(c.value) == U.normalise_answer(key)
        rows.append({
            "item_id": i, "pair_id": pid(i), "family": items[i]["family"], "answer": key,
            **{f"vote_{m}": votes[m] for m in U.METHODS},
            **{f"status_{m}": U.claim_status(cbm[m][i]) for m in U.METHODS},
            "consensus": c.value, "n_agree": c.n_agree, "n_cast": c.n_cast, "bucket": c.bucket, "resolved": c.resolved,
            "unresolved_reason": "" if c.resolved else c.reason, "dissent": c.dissent, "voters": "+".join(c.voters),
            "consensus_correct": correct,
            **{f"loo_{m}": U.loo_consistency(votes, m) for m in U.METHODS},
        })
    buckets = {}
    for b in (1, 2, 3):
        rb = [r for r in rows if r["bucket"] == b]
        buckets[str(b)] = {
            "n_states": len(rb),
            "accuracy": U.pair_rate([(r["pair_id"], bool(r["consensus_correct"])) for r in rb], nb, sd).as_dict(),
            "with_dissent": sum(bool(r["dissent"]) for r in rb),
            "voter_sets": dict(Counter(r["voters"] for r in rb)),
        }
    # bucket "≥2" for a monotonicity read-out
    r2 = [r for r in rows if r["bucket"] in (2, 3)]
    buckets["2_or_3"] = {"n_states": len(r2), "accuracy": U.pair_rate([(r["pair_id"], bool(r["consensus_correct"])) for r in r2], nb, sd).as_dict()}
    unresolved = Counter(r["unresolved_reason"] for r in rows if not r["resolved"])
    shared_wrong = defaultdict(lambda: {"n_states": 0, "n_shared_wrong": 0, "n_all3_wrong": 0, "items": []})
    for r in rows:
        f = shared_wrong[r["family"]]
        f["n_states"] += 1
        if r["bucket"] in (2, 3) and r["consensus_correct"] is False:
            f["n_shared_wrong"] += 1
            f["items"].append(r["item_id"])
            if r["bucket"] == 3:
                f["n_all3_wrong"] += 1
    loo = {}
    for m in U.METHODS:
        cnt = Counter(r[f"loo_{m}"] for r in rows)
        scored = [r for r in rows if r[f"loo_{m}"] in ("agree", "disagree")]
        loo[m] = {"counts": dict(cnt), "consistency": U.pair_rate([(r["pair_id"], r[f"loo_{m}"] == "agree") for r in scored], nb, sd).as_dict(),
                  "note": "agree/(agree+disagree); own vote excluded from the others' consensus; others' ties/all-abstain unresolved"}
    return {"rows": rows, "buckets": buckets, "unresolved": dict(unresolved), "n_unresolved": sum(unresolved.values()),
            "shared_wrong_by_family": dict(shared_wrong), "leave_one_out": loo}


def run(args: argparse.Namespace) -> dict:
    frozen, cfg = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    split, out = U.resolve_split_and_out(MODULE, args.split, frozen, args.out)
    out.mkdir(parents=True, exist_ok=True)
    meta, items = U.load_items(args.items)
    U.check_dataset_sha(meta, items, cfg)
    gens = U.load_gens(args.gens)
    claims = U.load_claims(args.claims)
    states_meta = U.load_states_meta(args.states_meta)
    item_ids = U.split_item_ids(items, split)
    U.assert_split(items, item_ids, split)
    gens_split = [g for g in gens if g.get("item_id") in set(item_ids)]
    U.validate_gens_against_states(gens_split, states_meta)
    cbm, _, absent = collect_claims_by_method(items, gens_split, claims, set(item_ids))
    pid = lambda i: items[i]["pair_id"]  # noqa: E731
    res = bucket_table(items, item_ids, cbm, pid, args.n_boot, args.seed)
    primary = {f"k{k}": U.consensus_vs_best_single(cbm, items, k, item_ids, n_boot=args.n_boot, seed=args.seed) for k in (2, 3)}
    for kk, d in primary.items():
        b = d["best_single_reader"]
        U.log(f"[consensus] PRIMARY consensus-{kk[1]}: covered {d['n_covered']}/{d['n_states']}; consensus {d['consensus_accuracy']['k']}/{d['n_covered']} "
              f"vs best single {U.METHOD_LABELS[b]} {d['single_reader_accuracy_on_covered'][b]['k']}/{d['n_covered']} on the same states; "
              f"diff {100 * d['difference_reselected_best']['est']:+.1f} pp [{100 * d['difference_reselected_best']['lo']:.0f}, {100 * d['difference_reselected_best']['hi']:.0f}] "
              f"(best re-selected per resample; fixed-best CI [{100 * d['difference_fixed_best']['lo']:.0f}, {100 * d['difference_fixed_best']['hi']:.0f}])")

    U.log(f"[consensus] SECONDARY buckets/LOO: split={split} n_states={len(item_ids)} unresolved={res['n_unresolved']} {res['unresolved']}")
    for b, d in res["buckets"].items():
        a = d["accuracy"]
        U.log(f"[consensus] bucket {b}: {d['n_states']} states, consensus correct {U.fmt_count(a['k'], a['n'])} [{100 * a['lo']:.0f}, {100 * a['hi']:.0f}]")
    for f, d in res["shared_wrong_by_family"].items():
        U.log(f"[consensus] shared wrong ({f}): {d['n_shared_wrong']}/{d['n_states']} (all-three wrong: {d['n_all3_wrong']}) {d['items']}")
    for m, d in res["leave_one_out"].items():
        c = d["consistency"]
        U.log(f"[consensus] LOO {U.METHOD_LABELS[m]}: {d['counts']} -> consistency {U.fmt_count(c['k'], c['n'])} [{100 * c['lo']:.0f}, {100 * c['hi']:.0f}]")

    U.write_csv(out / "consensus.csv", res["rows"])
    summary = {"primary_endpoint_consensus_vs_best_single": primary, "secondary": "buckets, shared_wrong_by_family and leave_one_out below are secondary analyses"}
    summary.update({k: v for k, v in res.items() if k != "rows"})
    summary.update({"module": MODULE, "split": split, "frozen": frozen, "n_states": len(item_ids), "n_pairs": len(U.pairs_of(items, item_ids)),
                    "n_boot": args.n_boot, "seed": args.seed, "absent_rows": absent,
                    "rules": "vote = asserted candidate; unclear/self_contradictory abstain; ties and all-abstain unresolved; "
                             "accuracy vs answer key; LOO consistency excludes own vote and is not an accuracy"})
    U.write_json(out / "consensus.json", summary)
    U.log(f"[consensus] wrote {out / 'consensus.csv'} and consensus.json")
    return summary


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
