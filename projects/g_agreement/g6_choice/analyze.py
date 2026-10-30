"""G6 — a property the prompt does not state: the model's own choice (BRIEF_G5G6.md, endpoints E5–E7)

CPU only. Inputs: dataset/items_g6.json (family "choice", primary.answer null, answer_source target_greedy),
cache/g_agreement/gens/g6.jsonl (module g6: target, jlens, olens, nla, jlens_null; prompt_only and state_free rows
may sit in the same file or in a second file passed with --gens-extra), results/g_agreement/claims/g6.jsonl,
cache/g_agreement/states_meta.jsonl.

Key filling: each item's answer key = the target's parsed greedy answer (scoring.extract_target_answer); states whose
target answer is unparseable are excluded and counted. Every consistency number is recomputed from the claim's
asserted VALUE against that key (not from the status label).
  E5 coverage and target-consistency per reader (J-lens, Oracle lens, NLA), over all parseable states and given a vote;
     J-lens noise ceiling (jlens_null) and state-free reader-prior consistency (condition state_free) reported beside them.
  E6 prompt-only consistency with the target = the floor.
  E7 NLA–OLens agreement (agree / contradict / missing) and Cohen's kappa.
Position dominance: if the target's greedy choice is the first-listed option in >= 14/16 states the family is
position-dominated and E7 is uninterpretable (reported, not concluded).
Decision per reader: "reads the choice" if consistency − prompt-only floor >= 25 pp with a paired pair-bootstrap CI
excluding 0; otherwise "no evidence" (n = 8 pairs).

Outputs results/g_agreement/g6[/dev]/{fig_main.png, g6.csv, summary.json}. The items_g6 sha is recorded in summary.json
(it is not part of the frozen manifest).
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402

MODULE = "g6"
READERS = ("jlens", "olens", "nla")
MIN_EFFECT = 0.25
DOMINANCE_K, DOMINANCE_N = 14, 16


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(U.G_DIR / "dataset" / "items_g6.json"))
    ap.add_argument("--gens", default=str(U.DEFAULTS["gens_dir"] / "g6.jsonl"))
    ap.add_argument("--gens-extra", default=None, help="optional second gens file (prompt_only / state_free rows)")
    ap.add_argument("--claims", default=str(U.DEFAULTS["claims_dir"] / "g6.jsonl"))
    ap.add_argument("--states-meta", default=str(U.DEFAULTS["states_meta"]))
    ap.add_argument("--frozen-config", default=str(U.DEFAULTS["frozen_config"]))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


def load_items_g6(path: str):
    """items_g6: family choice, answer null (filled from the target), A/B swap the option ORDER so candidates are a set."""
    d = U.load_json(path)
    meta, items = d.get("meta", {}), {it["item_id"]: it for it in d["items"]}
    by_pair: Dict[str, List[dict]] = {}
    for it in items.values():
        if it["family"] != "choice":
            raise U.AnalysisError(f"{it['item_id']}: items_g6 must be family 'choice', got {it['family']}")
        if it["primary"].get("answer") is not None:
            raise U.AnalysisError(f"{it['item_id']}: items_g6 answer must be null (filled from the target's greedy answer)")
        if it["primary"].get("answer_source", "target_greedy") != "target_greedy":
            raise U.AnalysisError(f"{it['item_id']}: answer_source must be target_greedy")
        if len(it["primary"]["candidates"]) != 2:
            raise U.AnalysisError(f"{it['item_id']}: exactly two options expected")
        by_pair.setdefault(it["pair_id"], []).append(it)
    for p, its in by_pair.items():
        if len(its) != 2 or set(its[0]["primary"]["candidates"]) != set(its[1]["primary"]["candidates"]):
            raise U.AnalysisError(f"pair {p}: two versions sharing one option set expected")
    return meta, items


def first_listed(item: dict) -> str:
    c = item.get("construction") or {}
    return c.get("first_mentioned_candidate") or c.get("first_listed") or item["primary"]["candidates"][0]


def run(args: argparse.Namespace) -> dict:
    frozen, cfg = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    out = Path(args.out) if args.out else (U.DEFAULTS["results_dir"] / MODULE / ("" if frozen else "dev"))
    out.mkdir(parents=True, exist_ok=True)
    meta, items = load_items_g6(args.items)
    items_sha = U.canonical_items_sha([items[i] for i in sorted(items)])
    gens = U.load_gens(args.gens)
    if args.gens_extra and Path(args.gens_extra).exists():
        extra = U.load_gens(args.gens_extra)
        seen = {g["gen_id"] for g in gens}
        gens += [g for g in extra if g["gen_id"] not in seen]
    claims = U.load_claims(args.claims)
    states_meta = U.load_states_meta(args.states_meta) if Path(args.states_meta).exists() else {}
    nb, sd = args.n_boot, args.seed
    pid = lambda i: items[i]["pair_id"]  # noqa: E731
    all_ids = sorted(items)
    if states_meta:
        U.validate_gens_against_states([g for g in gens if g.get("item_id") in items], states_meta)
    U.log(f"[g6] frozen={frozen} {len(all_ids)} states / {len(U.pairs_of(items, all_ids))} pairs; items_g6 sha {items_sha[:12]}; out={out}")

    # ---------------- key filling from the target ----------------
    from projects.g_agreement.core.scoring import extract_target_answer

    tgt: Dict[str, Optional[str]] = {}
    tgt_ev: Dict[str, str] = {}
    for g in gens:
        if g.get("method") != "target" or g.get("item_id") not in items:
            continue
        text = (g.get("native") or {}).get("text") or g.get("raw_output")
        v, ev = extract_target_answer(text, items[g["item_id"]])
        tgt[g["item_id"]], tgt_ev[g["item_id"]] = v, ev
    unparseable = [i for i in all_ids if tgt.get(i) is None]
    item_ids = [i for i in all_ids if tgt.get(i) is not None]
    for i in item_ids:
        items[i]["primary"]["answer"] = tgt[i]
        items[i]["primary"]["answer_aliases"] = [tgt[i].lower()]
    pair_ids = U.pairs_of(items, item_ids)
    U.log(f"[g6] target greedy answer parseable on {len(item_ids)}/{len(all_ids)} states; excluded (unparseable/no target row): {unparseable}")

    # position dominance
    first = sum(U.normalise_answer(tgt[i]) == U.normalise_answer(first_listed(items[i])) for i in item_ids)
    dominated = first >= DOMINANCE_K and len(item_ids) >= DOMINANCE_N - 2
    same_choice_both_versions = sum(1 for p in pair_ids if len({U.normalise_answer(tgt[i]) for i in item_ids if pid(i) == p}) == 1 and sum(pid(i) == p for i in item_ids) == 2)
    U.log(f"[g6] target chose the first-listed option in {first}/{len(item_ids)} states -> position-dominated={dominated} (rule >= {DOMINANCE_K}/{DOMINANCE_N}); "
          f"same option chosen in both versions of {same_choice_both_versions}/{len(pair_ids)} pairs")

    # ---------------- readers ----------------
    cbm: Dict[str, Dict[str, Optional[dict]]] = {r: {i: None for i in item_ids} for r in READERS}
    gbm: Dict[str, Dict[str, dict]] = {r: {} for r in READERS}
    po: Dict[str, Optional[dict]] = {i: None for i in item_ids}
    sf: Dict[str, Dict[str, Dict[str, Optional[dict]]]] = {}
    null_rows: Dict[str, List] = {}
    for g in gens:
        i, m = g.get("item_id"), g.get("method")
        if i not in items or i not in cbm["nla"]:
            continue
        if g.get("condition") == "state_free":
            src = (g.get("input") or {}).get("injection_source")
            sf.setdefault(m, {}).setdefault(src, {})[i] = claims.get(g["gen_id"])
        elif m == "jlens_null":
            src = (g.get("input") or {}).get("injection_source")
            c = claims.get(g["gen_id"])
            null_rows.setdefault(src, []).append((pid(i), c is not None and U.claim_status(c) != "unclear"))
        elif m == "prompt_only":
            po[i] = claims.get(g["gen_id"])
        elif m in READERS and int(g.get("sample_idx", 0)) == 0:
            if i in gbm[m]:
                raise U.AnalysisError(f"two first-sample {m} rows for {i}")
            gbm[m][i] = g
            cbm[m][i] = claims.get(g["gen_id"])

    def consistency(cl: Dict[str, Optional[dict]]):
        return {"consistent_all": U.pair_rate([(pid(i), bool(U.claim_correct(cl.get(i), items[i]))) for i in item_ids], nb, sd).as_dict(),
                "consistent_given_vote": U.pair_rate([(pid(i), U.claim_correct(cl.get(i), items[i])) for i in item_ids], nb, sd).as_dict(),
                "coverage": U.pair_rate([(pid(i), U.vote(cl.get(i)) is not None) for i in item_ids], nb, sd).as_dict(),
                "asserts_first_listed": U.pair_rate([(pid(i), None if U.vote(cl.get(i)) is None else U.normalise_answer(U.vote(cl.get(i))) == U.normalise_answer(first_listed(items[i]))) for i in item_ids], nb, sd).as_dict(),
                "status_counts": dict(Counter(U.claim_status(cl.get(i)) for i in item_ids))}

    e6 = consistency(po)
    e6["n_rows"] = sum(v is not None for v in po.values())
    U.log(f"[g6] E6 prompt-only floor: consistent {U.fmt_count(e6['consistent_all']['k'], e6['consistent_all']['n'])}; coverage {U.fmt_count(e6['coverage']['k'], e6['coverage']['n'])}")
    po_flags = [(pid(i), bool(U.claim_correct(po.get(i), items[i]))) for i in item_ids]
    e5: Dict[str, dict] = {}
    csv_rows: List[dict] = []
    for r in READERS:
        d = consistency(cbm[r])
        diff = U.pair_rate_diff([(pid(i), bool(U.claim_correct(cbm[r].get(i), items[i]))) for i in item_ids], po_flags, nb, sd)
        d["minus_prompt_only"] = {"est": diff[0], "lo": diff[1], "hi": diff[2]}
        d["state_free"] = {src: consistency(cl) for src, cl in sf.get(r, {}).items()}
        if r == "jlens":
            d["noise_ceiling_candidate_in_top10"] = {src: U.pair_rate(fl, nb, sd).as_dict() for src, fl in null_rows.items()}
        reads = (not np.isnan(diff[1])) and diff[0] >= MIN_EFFECT and diff[1] > 0
        d["decision"] = {"verdict": "reads_the_choice" if reads else "no_evidence",
                         "reason": f"consistency − prompt-only = {100 * diff[0]:+.1f} pp [{100 * diff[1]:.0f}, {100 * diff[2]:.0f}]; rule: >= 25 pp with CI excluding 0 (n = {len(pair_ids)} pairs)"
                                   + ("; family position-dominated — report only" if dominated else "")}
        e5[r] = d
        U.log(f"[g6] E5 {U.METHOD_LABELS[r]:12s} consistent {U.fmt_count(d['consistent_all']['k'], d['consistent_all']['n'])} "
              f"[{100 * d['consistent_all']['lo']:.0f}, {100 * d['consistent_all']['hi']:.0f}]; coverage {U.fmt_count(d['coverage']['k'], d['coverage']['n'])}; "
              f"− prompt-only {100 * diff[0]:+.1f} pp [{100 * diff[1]:.0f}, {100 * diff[2]:.0f}] -> {d['decision']['verdict']}")
        for i in item_ids:
            c = cbm[r].get(i)
            csv_rows.append({"item_id": i, "pair_id": pid(i), "version": items[i].get("version"), "reader": r, "target_answer": tgt[i], "first_listed": first_listed(items[i]),
                             "status": U.claim_status(c), "value": U.vote(c), "consistent_with_target": U.claim_correct(c, items[i]), "readout": U.readout_text(gbm[r].get(i), 300)})
    for i in item_ids:
        csv_rows.append({"item_id": i, "pair_id": pid(i), "version": items[i].get("version"), "reader": "prompt_only", "target_answer": tgt[i], "first_listed": first_listed(items[i]),
                         "status": U.claim_status(po.get(i)), "value": U.vote(po.get(i)), "consistent_with_target": U.claim_correct(po.get(i), items[i])})
    for i in unparseable:
        csv_rows.append({"item_id": i, "pair_id": pid(i), "version": items[i].get("version"), "reader": "target", "target_answer": None, "status": "unparseable_excluded",
                         "readout": tgt_ev.get(i, "no target row")})

    # ---------------- E7 ----------------
    counts, recs = U.agreement_matrix({"nla": cbm["nla"], "olens": cbm["olens"]}, item_ids, ("nla", "olens"))
    kap = U.pair_kappa(cbm["nla"], cbm["olens"], items, item_ids, nb, sd)
    e7 = {kind: U.pair_rate([(pid(x["item_id"]), x["outcome"] == kind) for x in recs], nb, sd).as_dict() for kind in U.KINDS}
    e7["agree_given_both"] = U.pair_rate([(pid(x["item_id"]), x["outcome"] == "agree") for x in recs if x["outcome"] != "missing"], nb, sd).as_dict()
    e7["kappa"] = {k: v for k, v in kap.items() if k != "per_pair"}
    e7["interpretable"] = not dominated
    U.log(f"[g6] E7 NLA–OLens: agree {U.fmt_count(e7['agree']['k'], e7['agree']['n'])}, contradict {e7['contradict']['k']}, missing {e7['missing']['k']}; "
          f"kappa {kap['kappa']:.2f} [{kap['lo']:.2f}, {kap['hi']:.2f}] on {kap['n_both']} both-assert states; interpretable={not dominated}")

    U.write_csv(out / "g6.csv", csv_rows)
    summary = {"module": MODULE, "frozen": frozen, "items_g6_sha256": items_sha, "items_g6_meta_sha": meta.get("sha256_items"), "n_states_total": len(all_ids),
               "n_states_parseable": len(item_ids), "n_pairs": len(pair_ids), "excluded_unparseable": unparseable, "n_boot": nb, "seed": sd,
               "target_answers": tgt, "position_dominance": {"first_listed_chosen": first, "n": len(item_ids), "dominated": dominated, "rule": f">= {DOMINANCE_K}/{DOMINANCE_N}",
                                                              "same_choice_in_both_versions_pairs": same_choice_both_versions},
               "E5_readers": e5, "E6_prompt_only_floor": e6, "E7_nla_olens": e7,
               "decision_rule": "reads the choice if consistency − prompt-only floor >= 25 pp with pair-bootstrap CI excluding 0; else no evidence; E7 uninterpretable if position-dominated"}
    U.write_json(out / "summary.json", summary)
    if not args.no_fig:
        make_figure(out / "fig_main.png", summary, frozen)
    U.log(f"[g6] wrote {out}")
    return summary


def make_figure(path: Path, s: dict, frozen: bool) -> None:
    plt = U.mpl()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1.5, 1]})
    e5, e6 = s["E5_readers"], s["E6_prompt_only_floor"]
    xs, labels = [], []
    x = 0.0
    for r in READERS:
        d = e5[r]
        U.bar_ci(ax1, x, U.Rate(**{k: v for k, v in d["consistent_all"].items() if k != "ci"}), U.METHOD_COLORS[r], width=0.6)
        ax1.plot([x - 0.3, x + 0.3], [d["coverage"]["p"]] * 2, color=U.INK, lw=1.2, ls=(0, (2, 2)), zorder=6)
        xs.append(x); labels.append(f"{U.METHOD_LABELS[r]}\n{d['decision']['verdict'].replace('_', ' ')}")
        x += 0.75
        for src, sd_ in sorted(d.get("state_free", {}).items()):
            U.bar_ci(ax1, x, U.Rate(**{k: v for k, v in sd_["consistent_all"].items() if k != "ci"}), U.ARM_COLORS["state_free"], width=0.6, hollow=True)
            xs.append(x); labels.append(f"{U.METHOD_LABELS[r]}\nstate-free")
            x += 0.75
        x += 0.3
    U.bar_ci(ax1, x, U.Rate(**{k: v for k, v in e6["consistent_all"].items() if k != "ci"}), U.METHOD_COLORS["prompt_only"], width=0.6)
    ax1.plot([x - 0.3, x + 0.3], [e6["coverage"]["p"]] * 2, color=U.INK, lw=1.2, ls=(0, (2, 2)), zorder=6)
    ax1.axhline(e6["consistent_all"]["p"], color=U.METHOD_COLORS["prompt_only"], lw=0.9, ls=":", zorder=1)
    xs.append(x); labels.append("prompt-only\n(floor)")
    ax1.set_xticks(xs); ax1.set_xticklabels(labels, fontsize=8)
    U.style_ax(ax1, f"consistent with target's choice (% of {s['n_states_parseable']} states)", (0, 1.18))
    ax1.set_title("E5/E6 target-consistency per reader\n(dashed = coverage; hollow = state-free reader prior; dotted = prompt-only floor)")
    e7 = s["E7_nla_olens"]
    vals = [("agree", "agree"), ("contradict", "contradict"), ("missing", "missing")]
    for i, (k, lbl) in enumerate(vals):
        U.bar_ci(ax2, i, U.Rate(**{kk: v for kk, v in e7[k].items() if kk != "ci"}), U.METHOD_COLORS["olens"] if k == "agree" else U.INK2, width=0.6)
    ax2.set_xticks(range(3)); ax2.set_xticklabels([l for _, l in vals])
    U.style_ax(ax2, "% of states", (0, 1.18))
    kp = e7["kappa"]
    ax2.set_title(f"E7 NLA–OLens agreement\nκ = {kp['kappa']:.2f} [{kp['lo']:.2f}, {kp['hi']:.2f}] (n both = {kp['n_both']})" + ("\nUNINTERPRETABLE: position-dominated" if not e7["interpretable"] else ""))
    pd_ = s["position_dominance"]
    fig.suptitle(("" if frozen else "UNFROZEN DEV RUN — ") + f"G6 self-choice — {s['n_states_parseable']}/{s['n_states_total']} states with a parseable target answer, {s['n_pairs']} pairs; "
                 f"target chose first-listed {pd_['first_listed_chosen']}/{pd_['n']} ({'position-dominated' if pd_['dominated'] else 'not dominated'}); bars = 95% pair-bootstrap CI", y=1.02, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
