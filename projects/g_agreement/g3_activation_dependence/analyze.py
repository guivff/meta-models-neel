"""G3 — does the readout depend on the activation? genuine vs shuffled (cached reassignment) vs prompt-only.

CPU only. Arms, on the 32 test states (8 dev states when unfrozen):
  genuine             G1 first-sample readout of state i, scored against item i            (claims/g1.jsonl)
  shuffled_cached     the cached G1 readout of DONOR d(i) (donors.json) re-scored against item i's facts.
                      This is a reassignment of cached text, NOT a fresh intervention: the reader never saw
                      state i. It is valid only because NLA/OLens receive (activation, fixed instruction,
                      fixed layer integer) and J-lens is a function of the activation alone.
                        recipient-scored accuracy  = shuffled readout asserts item i's answer        (claims/g3_shuffled.jsonl)
                        donor tracking             = shuffled readout asserts donor d(i)'s answer     (= donor's own genuine claim)
  prompt_only         the same base model answering the frozen question prompt from the text alone,
                      no activation (gens/g3.jsonl, method prompt_only; claims/g3.jsonl).

Expected format of claims/g3_shuffled.jsonl: one row per (recipient item, method) with
  gen_id   = the DONOR's cached G1 gen_id (the text that was scored)
  item_id  = the RECIPIENT item whose answer key the status refers to
  condition = "shuffled_cached"
The script verifies every such row against donors.json and the G1 gens.

Outputs results/g_agreement/g3[/dev]/{fig_main.png, g3.csv, summary.json}. Pair bootstrap (16 pairs), n_boot 2000, seed 0.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.g1_agreement.analyze import collect_claims_by_method  # noqa: E402

MODULE = "g3"
ARMS = ("genuine", "shuffled_recipient", "shuffled_donor", "prompt_only")
ARM_LABELS = {"genuine": "genuine\n(reader saw state i)", "shuffled_recipient": "shuffled (cached)\nscored vs recipient i",
              "shuffled_donor": "shuffled (cached)\nscored vs donor d(i)\n= donor tracking", "prompt_only": "prompt-only\n(no activation)"}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(U.DEFAULTS["items"]))
    ap.add_argument("--gens", default=str(U.DEFAULTS["gens_dir"] / "g1.jsonl"), help="G1 generations (genuine readouts)")
    ap.add_argument("--claims", default=str(U.DEFAULTS["claims_dir"] / "g1.jsonl"), help="G1 claims (genuine, scored vs own item)")
    ap.add_argument("--gens-prompt-only", default=str(U.DEFAULTS["gens_dir"] / "g3.jsonl"))
    ap.add_argument("--claims-prompt-only", default=str(U.DEFAULTS["claims_dir"] / "g3.jsonl"))
    ap.add_argument("--claims-shuffled", default=str(U.DEFAULTS["claims_dir"] / "g3_shuffled.jsonl"),
                    help="donor readouts re-scored against recipient facts (see module docstring)")
    ap.add_argument("--donors", default=str(U.DEFAULTS["donors"]))
    ap.add_argument("--states-meta", default=str(U.DEFAULTS["states_meta"]))
    ap.add_argument("--frozen-config", default=str(U.DEFAULTS["frozen_config"]))
    ap.add_argument("--out", default=None)
    ap.add_argument("--split", choices=U.SPLITS, default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


def load_shuffled_claims(path: str, items, assignments: Dict[str, str], gens_by_id: Dict[str, dict], item_ids) -> Dict[str, Dict[str, Optional[dict]]]:
    """{method: {recipient_item: claim}} after verifying each row is the donor's cached text scored vs the recipient."""
    out: Dict[str, Dict[str, Optional[dict]]] = {m: {} for m in U.METHODS}
    rows = U.load_jsonl(path) if Path(path).exists() else []
    for r in rows:
        rec, m = r["item_id"], r["method"]
        if rec not in item_ids or m not in U.METHODS:
            continue
        if r.get("condition", "shuffled_cached") != "shuffled_cached":
            raise U.AnalysisError(f"shuffled claim {r['gen_id']}->{rec}: condition {r.get('condition')!r} != shuffled_cached")
        g = gens_by_id.get(r["gen_id"])
        if g is None:
            raise U.DonorAssignmentError(f"shuffled claim for {rec}: gen_id {r['gen_id']} not among G1 gens")
        if g["item_id"] != assignments.get(rec):
            raise U.DonorAssignmentError(f"shuffled claim for {rec}: text comes from {g['item_id']} but donors.json says {assignments.get(rec)}")
        if g["method"] != m or g.get("sample_idx", 0) != 0 or g.get("condition", "genuine") != "genuine":
            raise U.DonorAssignmentError(f"shuffled claim for {rec}: {r['gen_id']} is not the donor's first genuine {m} sample")
        st = r["primary"]["status"]
        if st not in U.ALL_STATUSES:
            raise U.AnalysisError(f"shuffled claim {r['gen_id']}->{rec}: unknown status {st}")
        if rec in out[m]:
            raise U.AnalysisError(f"duplicate shuffled claim for {rec}/{m}")
        out[m][rec] = r
    for m in U.METHODS:
        for i in item_ids:
            out[m].setdefault(i, None)
    return out


def run(args: argparse.Namespace) -> dict:
    frozen, cfg = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    split, out = U.resolve_split_and_out(MODULE, args.split, frozen, args.out)
    out.mkdir(parents=True, exist_ok=True)
    meta, items = U.load_items(args.items)
    U.check_dataset_sha(meta, items, cfg)
    gens = U.load_gens(args.gens)
    gens_by_id = U.index_by(gens, "gen_id")
    claims = U.load_claims(args.claims)
    states_meta = U.load_states_meta(args.states_meta)
    item_ids = U.split_item_ids(items, split)
    U.assert_split(items, item_ids, split)
    id_set = set(item_ids)
    pair_ids = U.pairs_of(items, item_ids)
    pid = lambda i: items[i]["pair_id"]  # noqa: E731
    nb, sd = args.n_boot, args.seed
    U.log(f"[g3] split={split} {len(item_ids)} states / {len(pair_ids)} pairs; out={out}")

    gens_split = [g for g in gens if g.get("item_id") in id_set]
    U.validate_gens_against_states(gens_split, states_meta)
    genuine, gbm, absent = collect_claims_by_method(items, gens_split, claims, id_set)

    # donors: only defined for the test split; dev runs use a dev-internal assignment if donors.json has one
    donors = U.load_json(args.donors)
    if split == "test":
        assignments = U.validate_donors(items, donors)
        mode = "test"
    else:
        assignments = U.validate_dev_donors(items, donors)
        mode = "DEV PLUMBING CHECK (cross-family dev donors; numbers are not interpretable)"
        U.log(f"[g3] {mode}")
    shuffled = load_shuffled_claims(args.claims_shuffled, items, assignments, gens_by_id, id_set)
    n_shuf = sum(v is not None for m in U.METHODS for v in shuffled[m].values())
    U.log(f"[g3] shuffled arm: {len(assignments)} donor assignments; {n_shuf} re-scored cached readouts (expected {3 * len(assignments)})")
    # label structure of the assignment: how often the donor's answer equals the recipient's answer (chance level for a donor-tracking reader)
    same_label = U.pair_rate([(pid(r), U.normalise_answer(items[d]["primary"]["answer"]) == U.normalise_answer(items[r]["primary"]["answer"]))
                              for r, d in assignments.items() if r in id_set], nb, sd)
    same_cands = sum(items[d]["primary"]["candidates"] == items[r]["primary"]["candidates"] for r, d in assignments.items() if r in id_set)
    U.log(f"[g3] donor answer == recipient answer in {same_label}; identical candidate sets in {same_cands}/{len(assignments)}")

    # prompt-only + state-free reader-prior control share the G3 gens/claims files
    g3_rows = U.load_gens(args.gens_prompt_only)
    po_gens = [g for g in g3_rows if g.get("method") == "prompt_only" and g.get("item_id") in id_set]
    po_claims = U.load_claims(args.claims_prompt_only) if Path(args.claims_prompt_only).exists() else {}
    sf_rows = [g for g in g3_rows if g.get("condition") == "state_free" and g.get("item_id") in id_set]
    U.validate_gens_against_states(sf_rows, states_meta)
    state_free: Dict[str, Dict[str, Dict[str, Optional[dict]]]] = {}
    for g in sf_rows:
        src = (g.get("input") or {}).get("injection_source")
        state_free.setdefault(g["method"], {}).setdefault(src, {})
        if g["item_id"] in state_free[g["method"]][src]:
            raise U.AnalysisError(f"two state_free rows for {g['item_id']}/{g['method']}/{src}")
        state_free[g["method"]][src][g["item_id"]] = po_claims.get(g["gen_id"])
    U.log(f"[g3] state-free arm (reader prior, no state): {len(sf_rows)} rows; methods {sorted(state_free)}")
    po: Dict[str, Optional[dict]] = {i: None for i in item_ids}
    po_gen: Dict[str, dict] = {}
    for g in po_gens:
        inp = g.get("input") or {}
        if inp.get("injection", "none") != "none":
            raise U.AnalysisError(f"prompt-only row {g['gen_id']} carries an injection {inp.get('injection')!r}")
        vp = inp.get("visible_prompt")
        if not vp:
            raise U.AnalysisError(f"prompt-only row {g['gen_id']} has no visible_prompt")
        if items[g["item_id"]]["prompt_text"] not in vp:
            U.log(f"[g3] WARNING prompt-only {g['gen_id']}: visible_prompt does not contain the item prompt text verbatim")
        if g["item_id"] in po_gen:
            raise U.AnalysisError(f"two prompt-only rows for {g['item_id']}")
        po_gen[g["item_id"]] = g
        po[g["item_id"]] = po_claims.get(g["gen_id"])
    U.log(f"[g3] prompt-only arm: {len(po_gen)} generations, {sum(v is not None for v in po.values())} claims")

    # ---------------- per-method arms ----------------
    csv_rows: List[dict] = []
    per_method: Dict[str, dict] = {}
    for m in U.METHODS:
        gen_flags, gen_cov, rec_flags, rec_cov, don_flags, don_cov = [], [], [], [], [], []
        for i in item_ids:
            d = assignments.get(i)
            cg, cs = genuine[m][i], shuffled[m][i]
            cd = genuine[m].get(d) if d in genuine[m] else (claims.get(f"g1|{m}|{d}|s0") if d else None)
            g_ok = U.claim_correct(cg, items[i])
            r_ok = U.claim_correct(cs, items[i])
            d_ok = U.claim_correct(cd, items[d]) if d else None
            gen_flags.append((pid(i), bool(g_ok))); gen_cov.append((pid(i), U.vote(cg) is not None))
            rec_flags.append((pid(i), bool(r_ok))); rec_cov.append((pid(i), U.vote(cs) is not None))
            don_flags.append((pid(i), bool(d_ok))); don_cov.append((pid(i), U.vote(cd) is not None))
            csv_rows.append({"split": split, "mode": mode, "item_id": i, "pair_id": pid(i), "family": items[i]["family"], "method": m, "donor_item_id": d,
                             "genuine_status": U.claim_status(cg), "genuine_value": U.vote(cg), "genuine_correct": g_ok,
                             "shuffled_status_vs_recipient": U.claim_status(cs), "shuffled_value": U.vote(cs), "shuffled_correct_vs_recipient": r_ok,
                             "donor_status_vs_donor": U.claim_status(cd), "donor_value": U.vote(cd), "shuffled_tracks_donor": d_ok,
                             "donor_answer_equals_recipient_answer": None if not d else U.normalise_answer(items[d]["primary"]["answer"]) == U.normalise_answer(items[i]["primary"]["answer"]),
                             "condition_note": "shuffled = cached-readout reassignment, not a fresh intervention"})
        arms = {
            "genuine": {"accuracy_all": U.pair_rate(gen_flags, nb, sd).as_dict(), "coverage": U.pair_rate(gen_cov, nb, sd).as_dict()},
            "shuffled_recipient": {"accuracy_all": U.pair_rate(rec_flags, nb, sd).as_dict(), "coverage": U.pair_rate(rec_cov, nb, sd).as_dict()},
            "shuffled_donor": {"accuracy_all": U.pair_rate(don_flags, nb, sd).as_dict(), "coverage": U.pair_rate(don_cov, nb, sd).as_dict()},
        }
        for src, cl in state_free.get(m, {}).items():
            sf_flags = [(pid(i), bool(U.claim_correct(cl.get(i), items[i]))) for i in item_ids]
            sf_cov = [(pid(i), U.vote(cl.get(i)) is not None) for i in item_ids]
            arms[f"state_free:{src}"] = {"accuracy_all": U.pair_rate(sf_flags, nb, sd).as_dict(), "coverage": U.pair_rate(sf_cov, nb, sd).as_dict(),
                                         "note": "reader run with a state-free input (reader-prior control); scored against the item key like genuine"}
            for i in item_ids:
                csv_rows.append({"split": split, "mode": mode, "item_id": i, "pair_id": pid(i), "family": items[i]["family"], "method": m, "donor_item_id": None,
                                 "genuine_status": U.claim_status(cl.get(i)), "genuine_value": U.vote(cl.get(i)), "genuine_correct": U.claim_correct(cl.get(i), items[i]),
                                 "condition_note": f"state_free:{src} (reader prior, no activation)"})
        diff = U.pair_rate_diff(gen_flags, rec_flags, nb, sd)
        per_method[m] = {"arms": arms, "genuine_minus_shuffled_recipient": {"est": diff[0], "lo": diff[1], "hi": diff[2]}}
        for src in state_free.get(m, {}):
            dsf = U.pair_rate_diff(gen_flags, [(pid(i), bool(U.claim_correct(state_free[m][src].get(i), items[i]))) for i in item_ids], nb, sd)
            per_method[m][f"genuine_minus_state_free:{src}"] = {"est": dsf[0], "lo": dsf[1], "hi": dsf[2]}
            U.log(f"[g3] {'':12s} genuine − state_free[{src}] = {100 * dsf[0]:+.1f} pp [{100 * dsf[1]:.0f}, {100 * dsf[2]:.0f}]")
        for a, d in arms.items():
            U.log(f"[g3] {U.METHOD_LABELS[m]:12s} {a:20s} acc {U.fmt_count(d['accuracy_all']['k'], d['accuracy_all']['n'])} "
                  f"[{100 * d['accuracy_all']['lo']:.0f},{100 * d['accuracy_all']['hi']:.0f}]  coverage {U.fmt_count(d['coverage']['k'], d['coverage']['n'])}")
        U.log(f"[g3] {'':12s} genuine − shuffled(recipient) = {100 * diff[0]:+.1f} pp [{100 * diff[1]:.0f}, {100 * diff[2]:.0f}]")

    po_acc = U.pair_rate([(pid(i), bool(U.claim_correct(po[i], items[i]))) for i in item_ids], nb, sd)
    po_cov = U.pair_rate([(pid(i), U.vote(po[i]) is not None) for i in item_ids], nb, sd)
    U.log(f"[g3] prompt-only: acc {po_acc}; coverage {po_cov}")
    for i in item_ids:
        csv_rows.append({"split": split, "mode": mode, "item_id": i, "pair_id": pid(i), "family": items[i]["family"], "method": "prompt_only", "donor_item_id": None,
                         "genuine_status": U.claim_status(po[i]), "genuine_value": U.vote(po[i]), "genuine_correct": U.claim_correct(po[i], items[i]),
                         "condition_note": "prompt-only: frozen question prompt, no activation"})
    U.write_csv(out / "g3.csv", csv_rows)

    summary = {"module": MODULE, "split": split, "mode": mode, "frozen": frozen, "n_states": len(item_ids), "n_pairs": len(pair_ids), "n_boot": nb, "seed": sd,
               "state_free_arm_note": "reader-prior control: reader run on a state-free input (mean dev activation / zeros), scored against the item key",
               "shuffled_arm_note": "cached-readout reassignment via donors.json; NOT a fresh intervention; reader never saw the recipient state",
               "donor_assignment": {"n": len(assignments), "donor_answer_equals_recipient_answer": same_label.as_dict(), "identical_candidate_sets": same_cands,
                                    "checks": donors.get("checks"), "seed": donors.get("seed")},
               "per_method": per_method, "prompt_only": {"accuracy_all": po_acc.as_dict(), "coverage": po_cov.as_dict(), "n_gens": len(po_gen)},
               "absent_rows": absent, "status_counts": {m: {"genuine": dict(Counter(U.claim_status(genuine[m][i]) for i in item_ids)),
                                                             "shuffled": dict(Counter(U.claim_status(shuffled[m][i]) for i in item_ids))} for m in U.METHODS}}
    U.write_json(out / "summary.json", summary)
    if not args.no_fig:
        make_figure(out / "fig_main.png", per_method, po_acc, po_cov, split, len(item_ids), same_label, mode)
    U.log(f"[g3] wrote {out}")
    return summary


def make_figure(path: Path, per_method, po_acc, po_cov, split, n_states, same_label, mode="test") -> None:
    plt = U.mpl()
    fig, ax = plt.subplots(figsize=(12, 4.6))
    x = 0.0
    ticks, labels = [], []
    has_sf = False
    for m in U.METHODS:
        xs = []
        arm_names = ["genuine", "shuffled_recipient", "shuffled_donor"] + sorted(a for a in per_method[m]["arms"] if a.startswith("state_free:"))
        for a in arm_names:
            d = per_method[m]["arms"][a]
            col = U.ARM_COLORS.get(a, U.ARM_COLORS["state_free"])
            U.bar_ci(ax, x, U.Rate(**{k: v for k, v in d["accuracy_all"].items() if k != "ci"}), col, width=0.7)
            ax.plot([x - 0.35, x + 0.35], [d["coverage"]["p"]] * 2, color=U.INK, lw=1.2, ls=(0, (2, 2)), zorder=6)
            xs.append(x)
            x += 0.85
            has_sf = has_sf or a.startswith("state_free:")
        ticks.append(sum(xs) / len(xs))
        labels.append(U.METHOD_LABELS[m])
        x += 0.7
    U.bar_ci(ax, x, po_acc, U.ARM_COLORS["prompt_only"], width=0.7)
    ax.plot([x - 0.35, x + 0.35], [po_cov.p] * 2, color=U.INK, lw=1.2, ls=(0, (2, 2)), zorder=6)
    ticks.append(x)
    labels.append("prompt-only\n(no activation)")
    ax.axhline(same_label.p, color=U.INK2, lw=0.9, ls=":", zorder=1)
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    U.style_ax(ax, f"accuracy vs answer key (% of {n_states} states)", (0, 1.18))
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    handles = [Patch(fc=U.ARM_COLORS["genuine"], label="genuine (reader saw state i)"),
               Patch(fc=U.ARM_COLORS["shuffled_recipient"], label="shuffled, cached donor text scored vs recipient i"),
               Patch(fc=U.ARM_COLORS["shuffled_donor"], label="shuffled, same text scored vs donor d(i) = donor tracking"),
               Patch(fc=U.ARM_COLORS["prompt_only"], label="prompt-only"),
               *([Patch(fc=U.ARM_COLORS["state_free"], label="state-free input (reader prior: mean dev activation / zeros)")] if has_sf else []),
               Line2D([], [], color=U.INK, ls=(0, (2, 2)), label="coverage (% with a vote)"),
               Line2D([], [], color=U.INK2, ls=":", label=f"donor answer = recipient answer ({same_label.k}/{same_label.n}):\nexpected recipient-scored accuracy of a pure donor-tracker")]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8)
    ax.set_title(("DEV PLUMBING CHECK — " if mode != "test" else "") + f"G3 activation dependence — {split} split. Shuffled arm = cached-readout reassignment (not a fresh intervention). "
                 f"Bars: 95% CI, bootstrap over base pairs; k/n printed", fontsize=9.5, loc="left")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
