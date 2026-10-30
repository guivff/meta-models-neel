"""G2 — entity recognition vs relation correctness vs complete-pair tracking (ownership + mapping).

CPU only; a pure re-analysis of G1's first-sample readouts and claims on the relation families.
Per method and state:
  entity_all   every entity in secondary.entities appears in claim.entities_mentioned
  entity_any   at least one does
  relation     claim.relation.status: correct | wrong | unbound | absent  (unbound = both entities/objects
               named without a binding = unclear; it is neither correct nor wrong)
Per method and base pair:
  complete-pair tracking = relation correct in BOTH versions AND the asserted primary value changes
               between A and B (the readout tracks the swapped binding, not a template default)
Source-model errors (the target model's own answer != key, or unparseable) are kept and shown
separately: every metric is reported on all test states and on the target-correct subset.

Outputs results/g_agreement/g2[/dev]/{fig_main.png, relations.csv, summary.json, examples.md}.
Uncertainty: bootstrap over base pairs (8 test pairs), n_boot 2000, seed 0.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.g1_agreement.analyze import collect_claims_by_method  # noqa: E402

MODULE = "g2"
RELATION_STATUSES = ("correct", "wrong", "unbound", "absent")


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(U.DEFAULTS["items"]))
    ap.add_argument("--gens", default=str(U.DEFAULTS["gens_dir"] / "g1.jsonl"), help="G1 generations (G2 runs no model)")
    ap.add_argument("--claims", default=str(U.DEFAULTS["claims_dir"] / "g1.jsonl"))
    ap.add_argument("--states-meta", default=str(U.DEFAULTS["states_meta"]))
    ap.add_argument("--frozen-config", default=str(U.DEFAULTS["frozen_config"]))
    ap.add_argument("--out", default=None)
    ap.add_argument("--split", choices=U.SPLITS, default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


def _norm_set(xs) -> set:
    return {U.normalise_answer(x) for x in (xs or [])}


def relation_status(claim) -> str:
    if claim is None:
        return "absent"
    st = (claim.get("relation") or {}).get("status", "absent")
    if st not in RELATION_STATUSES:
        raise U.AnalysisError(f"claim {claim.get('gen_id')}: unknown relation status {st!r}")
    return st


def state_rows(items, item_ids, cbm, tgt) -> List[dict]:
    rows = []
    for i in item_ids:
        it = items[i]
        ents = _norm_set(it["secondary"]["entities"])
        t = tgt.get(i)
        t_ok = None if t is None else U.normalise_answer(t) == U.normalise_answer(it["primary"]["answer"])
        for m in U.METHODS:
            c = cbm[m][i]
            ment = _norm_set(c.get("entities_mentioned") if c else [])
            rows.append({
                "item_id": i, "pair_id": it["pair_id"], "version": it["version"], "family": it["family"], "method": m,
                "n_entities": len(ents), "n_entities_mentioned": len(ents & ment),
                "entity_all": ents <= ment and len(ents) > 0, "entity_any": len(ents & ment) > 0,
                "relation_status": relation_status(c), "relation_correct": relation_status(c) == "correct",
                "primary_status": U.claim_status(c), "primary_value": U.vote(c), "primary_correct": U.claim_correct(c, it),
                "target_answer": t, "target_correct": t_ok, "source_model_error": (t_ok is not True),
            })
    return rows


def pair_tracking(rows: List[dict]) -> List[dict]:
    """One row per (pair, method): complete-pair tracking and its two components."""
    out = []
    by = {}
    for r in rows:
        by.setdefault((r["pair_id"], r["method"]), {})[r["version"]] = r
    for (p, m), d in sorted(by.items()):
        a, b = d.get("A"), d.get("B")
        if a is None or b is None:
            continue
        rel_both = a["relation_correct"] and b["relation_correct"]
        va, vb = a["primary_value"], b["primary_value"]
        changes = va is not None and vb is not None and U.normalise_answer(va) != U.normalise_answer(vb)
        both_asserted = va is not None and vb is not None
        out.append({"pair_id": p, "family": a["family"], "method": m, "relation_correct_both": rel_both,
                    "primary_both_asserted": both_asserted, "primary_changes": changes,
                    "primary_both_correct": bool(a["primary_correct"]) and bool(b["primary_correct"]),
                    "complete_pair_tracking": rel_both and changes,
                    "target_correct_both": (a["target_correct"] is True) and (b["target_correct"] is True)})
    return out


def summarise(rows, prow, nb, sd, subset_name: str, keep_state, keep_pair) -> Dict[str, dict]:
    res: Dict[str, dict] = {}
    for m in U.METHODS:
        rs = [r for r in rows if r["method"] == m and keep_state(r)]
        ps = [r for r in prow if r["method"] == m and keep_pair(r)]
        res[m] = {
            "n_states": len(rs), "n_pairs": len(ps),
            "entity_all": U.pair_rate([(r["pair_id"], r["entity_all"]) for r in rs], nb, sd).as_dict(),
            "entity_any": U.pair_rate([(r["pair_id"], r["entity_any"]) for r in rs], nb, sd).as_dict(),
            "entity_micro": U.pair_rate([(r["pair_id"], k < r["n_entities_mentioned"]) for r in rs for k in range(r["n_entities"])], nb, sd).as_dict(),
            "relation_correct": U.pair_rate([(r["pair_id"], r["relation_correct"]) for r in rs], nb, sd).as_dict(),
            "relation_correct_given_bound": U.pair_rate([(r["pair_id"], None if r["relation_status"] in ("unbound", "absent") else r["relation_correct"]) for r in rs], nb, sd).as_dict(),
            "relation_status_counts": dict(Counter(r["relation_status"] for r in rs)),
            "primary_correct_all": U.pair_rate([(r["pair_id"], bool(r["primary_correct"])) for r in rs], nb, sd).as_dict(),
            "complete_pair_tracking": U.pair_rate([(r["pair_id"], r["complete_pair_tracking"]) for r in ps], nb, sd).as_dict(),
            "relation_correct_both": U.pair_rate([(r["pair_id"], r["relation_correct_both"]) for r in ps], nb, sd).as_dict(),
            "primary_changes": U.pair_rate([(r["pair_id"], r["primary_changes"]) for r in ps], nb, sd).as_dict(),
            "by_family": {f: {
                "entity_all": U.pair_rate([(r["pair_id"], r["entity_all"]) for r in rs if r["family"] == f], nb, sd).as_dict(),
                "relation_correct": U.pair_rate([(r["pair_id"], r["relation_correct"]) for r in rs if r["family"] == f], nb, sd).as_dict(),
                "complete_pair_tracking": U.pair_rate([(r["pair_id"], r["complete_pair_tracking"]) for r in ps if r["family"] == f], nb, sd).as_dict(),
            } for f in U.RELATION_FAMILIES},
        }
        d = res[m]
        U.log(f"[g2:{subset_name}] {U.METHOD_LABELS[m]:12s} entity(all) {U.fmt_count(d['entity_all']['k'], d['entity_all']['n'])}; "
              f"relation correct {U.fmt_count(d['relation_correct']['k'], d['relation_correct']['n'])} {d['relation_status_counts']}; "
              f"complete-pair {U.fmt_count(d['complete_pair_tracking']['k'], d['complete_pair_tracking']['n'])} "
              f"(rel both {d['relation_correct_both']['k']}, answer changes {d['primary_changes']['k']})")
    return res


def run(args: argparse.Namespace) -> dict:
    frozen, cfg = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    split, out = U.resolve_split_and_out(MODULE, args.split, frozen, args.out)
    out.mkdir(parents=True, exist_ok=True)
    meta, items = U.load_items(args.items)
    U.check_dataset_sha(meta, items, cfg)
    gens = U.load_gens(args.gens)
    claims = U.load_claims(args.claims)
    states_meta = U.load_states_meta(args.states_meta)

    item_ids = U.split_item_ids(items, split, U.RELATION_FAMILIES)
    U.assert_split(items, item_ids, split)
    pair_ids = U.pairs_of(items, item_ids)
    U.log(f"[g2] split={split} families={U.RELATION_FAMILIES} {len(item_ids)} states / {len(pair_ids)} pairs; out={out}")
    gens_split = [g for g in gens if g.get("item_id") in set(item_ids)]
    U.validate_gens_against_states(gens_split, states_meta)
    cbm, gbm, absent = collect_claims_by_method(items, gens_split, claims, set(item_ids))
    tgt = U.target_answers(items, gens_split, claims)

    rows = state_rows(items, item_ids, cbm, tgt)
    prow = pair_tracking(rows)
    nb, sd = args.n_boot, args.seed
    res_all = summarise(rows, prow, nb, sd, "all", lambda r: True, lambda r: True)
    res_tc = summarise(rows, prow, nb, sd, "target-correct", lambda r: r["target_correct"] is True, lambda r: r["target_correct_both"])
    src_err = sorted({r["item_id"] for r in rows if r["source_model_error"]})
    U.log(f"[g2] source-model errors (target wrong or unparseable): {len(src_err)}/{len(item_ids)} states {src_err}")

    for r in prow:
        r["level"] = "pair"
    for r in rows:
        r["level"] = "state"
    U.write_csv(out / "relations.csv", rows + prow)
    summary = {"module": MODULE, "split": split, "frozen": frozen, "n_states": len(item_ids), "n_pairs": len(pair_ids), "n_boot": nb, "seed": sd,
               "families": list(U.RELATION_FAMILIES), "absent_rows": absent, "source_model_error_items": src_err,
               "all_states": res_all, "target_correct_subset": res_tc,
               "definitions": {"entity_all": "all secondary.entities in entities_mentioned", "relation_correct": "relation.status == correct; unbound counts as unclear",
                               "complete_pair_tracking": "relation correct in both versions AND asserted primary value differs between A and B"}}
    U.write_json(out / "summary.json", summary)
    write_examples(out / "examples.md", items, item_ids, cbm, gbm, tgt, rows, split)
    if not args.no_fig:
        make_figure(out / "fig_main.png", res_all, res_tc, split, len(item_ids), len(pair_ids))
    U.log(f"[g2] wrote {out}")
    return summary


def write_examples(path: Path, items, item_ids, cbm, gbm, tgt, rows, split) -> None:
    lines = [f"# G2 examples ({split} split; ownership + mapping)", ""]
    lines.append("## Source-model errors (target's own answer wrong or unparseable; kept in the 'all states' numbers, excluded from the target-correct subset)")
    any_err = False
    for i in item_ids:
        t = tgt.get(i)
        if t is not None and U.normalise_answer(t) == U.normalise_answer(items[i]["primary"]["answer"]):
            continue
        any_err = True
        lines += [f"- **{i}** ({items[i]['family']}): key={items[i]['primary']['answer']!r}, target answered {t!r}; prompt: {items[i]['prompt_text']}"]
    if not any_err:
        lines.append("- none")
    lines.append("")
    for m in U.METHODS:
        lines.append(f"## {U.METHOD_LABELS[m]}")
        shown = Counter()
        for r in rows:
            if r["method"] != m or shown[r["relation_status"]] >= 2:
                continue
            shown[r["relation_status"]] += 1
            i = r["item_id"]
            it, c = items[i], cbm[m][i]
            lines += [f"### {i} ({it['family']}) — relation `{r['relation_status']}`, primary `{r['primary_status']}`", "",
                      f"- prompt: {it['prompt_text']}",
                      f"- relation key: {it['secondary']['relation']}; entities: {it['secondary']['entities']}",
                      f"- readout: {U.readout_text(gbm[m].get(i))}",
                      f"- entities mentioned: {c.get('entities_mentioned') if c else None}; relation evidence: {(c.get('relation') or {}).get('evidence') if c else None!r}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def make_figure(path: Path, res_all, res_tc, split, n_states, n_pairs) -> None:
    plt = U.mpl()
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    panels = [("entity_all", f"Entity recognition\n(all entities named; % of {n_states} states)"),
              ("relation_correct", f"Relation correct\n(unbound = unclear; % of {n_states} states)"),
              ("complete_pair_tracking", f"Complete-pair tracking\n(relation correct in A and B, answer changes; % of {n_pairs} pairs)")]
    for ax, (key, ttl) in zip(axes, panels):
        for k, m in enumerate(U.METHODS):
            U.bar_ci(ax, k - 0.18, U.Rate(**{a: b for a, b in res_all[m][key].items() if a != "ci"}), U.METHOD_COLORS[m], width=0.34)
            U.bar_ci(ax, k + 0.18, U.Rate(**{a: b for a, b in res_tc[m][key].items() if a != "ci"}), U.METHOD_COLORS[m], width=0.34, hollow=True)
        ax.set_xticks(range(len(U.METHODS)))
        ax.set_xticklabels([U.METHOD_LABELS[m] for m in U.METHODS])
        U.style_ax(ax, "%", (0, 1.15))
        ax.set_title(ttl)
    from matplotlib.patches import Patch

    fig.legend(handles=[Patch(fc=U.INK2, label="all states (source-model errors kept)"), Patch(fc="none", ec=U.INK2, label="target-correct subset")],
               loc="lower center", ncol=2, fontsize=8.5, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle(f"G2 relations — {split} split; bars = 95% CI from bootstrap over base pairs; k/n printed", y=1.02)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
