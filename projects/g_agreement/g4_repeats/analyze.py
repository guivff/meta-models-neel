"""G4 — is cross-method agreement worth more than re-sampling one reader? (feasibility pilot, 8 states)

CPU only. On the 8 preselected test states (dataset/g4_pairs.json, chosen before any test output
existed) we have 3 NLA samples, 3 Oracle-lens samples (first samples reused from G1, two more from
g4/collect) and one deterministic J-lens readout. Repeating J-lens is not an extra vote: it enters
each cross-method rule exactly once.

Rules (a verdict is a candidate or an abstention; abstentions are retained, never dropped):
  individual        nla_s0 nla_s1 nla_s2 olens_s0 olens_s1 olens_s2 jlens
  cross_2of3        majority of {nla_s0, olens_s0, jlens}; ties / all-abstain = no verdict
  cross_3of3        all three assert the same candidate
  nla_2of3/3of3     the same rules over the three NLA samples
  olens_2of3/3of3   the same rules over the three Oracle-lens samples
Per rule: coverage (states with a verdict / 8), accuracy given a verdict, accuracy over all 8 (abstain
≠ correct), accuracy on the *matched* set (states where every rule in the comparison set has a
verdict), and compute (sum of wall-clock seconds and new tokens of the calls the rule consumes).

Reuse validity: G1 first samples are reused only if their sampling dict equals the frozen sampling
setting and the G4 samples' dict; otherwise this script raises SamplingMismatchError.

Outputs results/g_agreement/g4[/dev]/{fig_main.png, g4.csv, summary.json}. Uncertainty: bootstrap over the
4 base pairs (n_boot 2000, seed 0) — the intervals are very wide by construction; this is a pilot.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402

MODULE = "g4"
N_SAMPLES = 3
READERS = tuple([f"nla_s{k}" for k in range(N_SAMPLES)] + [f"olens_s{k}" for k in range(N_SAMPLES)] + ["jlens"])
RULES: Dict[str, dict] = {
    "cross_2of3": {"voters": ("nla_s0", "olens_s0", "jlens"), "k": 2, "group": "cross-method"},
    "cross_3of3": {"voters": ("nla_s0", "olens_s0", "jlens"), "k": 3, "group": "cross-method"},
    "nla_2of3": {"voters": ("nla_s0", "nla_s1", "nla_s2"), "k": 2, "group": "within-NLA"},
    "nla_3of3": {"voters": ("nla_s0", "nla_s1", "nla_s2"), "k": 3, "group": "within-NLA"},
    "olens_2of3": {"voters": ("olens_s0", "olens_s1", "olens_s2"), "k": 2, "group": "within-OLens"},
    "olens_3of3": {"voters": ("olens_s0", "olens_s1", "olens_s2"), "k": 3, "group": "within-OLens"},
    **{r: {"voters": (r,), "k": 1, "group": "individual"} for r in READERS},
}
MATCHED_SETS = {"2of3": ("cross_2of3", "nla_2of3", "olens_2of3"), "3of3": ("cross_3of3", "nla_3of3", "olens_3of3"),
                "individual": READERS, "all_rules": tuple(RULES)}
GROUP_COLORS = {"cross-method": "#2a78d6", "within-NLA": "#eb6834", "within-OLens": "#1baf7a", "individual": "#52514e"}


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(U.DEFAULTS["items"]))
    ap.add_argument("--gens", default=str(U.DEFAULTS["gens_dir"] / "g1.jsonl"), help="G1 generations (first samples + J-lens)")
    ap.add_argument("--gens-g4", default=str(U.DEFAULTS["gens_dir"] / "g4.jsonl"), help="extra NLA/OLens samples")
    ap.add_argument("--claims", default=str(U.DEFAULTS["claims_dir"] / "g1.jsonl"))
    ap.add_argument("--claims-g4", default=str(U.DEFAULTS["claims_dir"] / "g4.jsonl"))
    ap.add_argument("--g4-pairs", default=str(U.DEFAULTS["g4_pairs"]))
    ap.add_argument("--states-meta", default=str(U.DEFAULTS["states_meta"]))
    ap.add_argument("--frozen-config", default=str(U.DEFAULTS["frozen_config"]))
    ap.add_argument("--out", default=None)
    ap.add_argument("--split", choices=U.SPLITS, default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


def rule_verdict(votes: Sequence[Optional[str]], k: int) -> Optional[str]:
    """Majority with at least k agreeing votes; ties and all-abstain give no verdict. k == len(votes) requires unanimity."""
    c = U.consensus({str(i): v for i, v in enumerate(votes)})
    if not c.resolved or c.n_agree < k:
        return None
    if k == len(votes) and c.n_cast != len(votes):
        return None
    return c.value


def collect_samples(items, item_ids, gens_g1, gens_g4, claims_g1, claims_g4, frozen_samp: Optional[dict]):
    """{reader: {item: claim|None}}, {reader: {item: gen}}; enforces the sampling-reuse rule."""
    readers: Dict[str, Dict[str, Optional[dict]]] = {r: {i: None for i in item_ids} for r in READERS}
    rgens: Dict[str, Dict[str, dict]] = {r: {} for r in READERS}
    reference: Optional[dict] = None
    for src, rows, claims in (("g1", gens_g1, claims_g1), ("g4", gens_g4, claims_g4)):
        for g in rows:
            if g.get("item_id") not in item_ids or g.get("method") not in U.METHODS:
                continue
            if g["item_id"] != g.get("state_item_id"):
                raise U.SiteMismatchError(f"gen {g['gen_id']}: reads state {g.get('state_item_id')} for item {g['item_id']}")
            m, s = g["method"], int(g.get("sample_idx", 0))
            if m == "jlens":
                if s != 0 or src != "g1":
                    continue  # repeated J-lens is identical and is not an extra vote
                r = "jlens"
            else:
                if src == "g1" and s != 0:
                    continue
                if src == "g4" and s == 0:
                    raise U.AnalysisError(f"g4 row {g['gen_id']} has sample_idx 0; first samples come from G1 only")
                if s >= N_SAMPLES:
                    continue
                r = f"{m}_s{s}"
                samp = g.get("sampling") or {}
                if frozen_samp is not None:
                    U.check_sampling_matches(samp, frozen_samp, where=f"({g['gen_id']} vs frozen config)")
                if reference is None:
                    reference = dict(samp)
                else:
                    U.check_sampling_matches(samp, reference, where=f"({g['gen_id']} vs other G4 samples)")
            if g["item_id"] in rgens[r]:
                raise U.AnalysisError(f"duplicate reader row {r} for {g['item_id']}")
            rgens[r][g["item_id"]] = g
            readers[r][g["item_id"]] = claims.get(g["gen_id"])
    missing = [(r, i) for r in READERS for i in item_ids if i not in rgens[r]]
    if missing:
        U.log(f"[g4] WARNING {len(missing)} reader×state cells have no generation (treated as abstention): {missing[:6]}")
    return readers, rgens


def run(args: argparse.Namespace) -> dict:
    frozen, cfg = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    split, out = U.resolve_split_and_out(MODULE, args.split, frozen, args.out)
    out.mkdir(parents=True, exist_ok=True)
    meta, items = U.load_items(args.items)
    U.check_dataset_sha(meta, items, cfg)
    sel = U.load_json(args.g4_pairs)
    if sel.get("chosen_before_test_outputs") is not True:
        raise U.AnalysisError("g4_pairs.json: chosen_before_test_outputs must be true")
    item_ids = list(sel["item_ids"])
    if sorted({items[i]["pair_id"] for i in item_ids}) != sorted(sel["pairs"]) or len(item_ids) != 2 * len(sel["pairs"]):
        raise U.AnalysisError("g4_pairs.json: item_ids are not exactly the two versions of each listed pair")
    if split == "dev":
        # development plumbing: the preselected G4 pairs are TEST pairs and never enter a dev run;
        # the dev run uses the 8 dev states (one pair per family) instead.
        item_ids = sorted(i for i, it in items.items() if it["split"] == "dev")
        U.log("[g4] DEV PLUMBING CHECK: using the 8 dev states, not the preselected test pairs")
    U.assert_split(items, item_ids, split)
    fams = Counter(items[i]["family"] for i in item_ids)
    if split == "test" and any(fams[f] != 2 for f in U.FAMILIES):
        raise U.AnalysisError(f"g4_pairs.json: expected one pair per family, got {dict(fams)}")
    pair_ids = U.pairs_of(items, item_ids)
    pid = lambda i: items[i]["pair_id"]  # noqa: E731
    nb, sd = args.n_boot, args.seed
    U.log(f"[g4] split={split} {len(item_ids)} states / {len(pair_ids)} pairs (feasibility pilot); out={out}")

    gens_g1 = [g for g in U.load_gens(args.gens) if g.get("item_id") in set(item_ids)]
    gens_g4 = [g for g in U.load_gens(args.gens_g4) if g.get("item_id") in set(item_ids)]
    states_meta = U.load_states_meta(args.states_meta)
    U.validate_gens_against_states(gens_g1 + gens_g4, states_meta)
    claims_g1 = U.load_claims(args.claims)
    claims_g4 = U.load_claims(args.claims_g4)
    fs = U.frozen_sampling(cfg)
    if frozen and fs is None:
        raise U.FrozenConfigError("frozen_config.json has no 'sampling' block; cannot validate G1-sample reuse")
    readers, rgens = collect_samples(items, item_ids, gens_g1, gens_g4, claims_g1, claims_g4, fs)
    U.log(f"[g4] sampling-reuse check passed ({'frozen config' if fs else 'mutual consistency only, unfrozen dev run'})")

    votes = {r: {i: U.vote(readers[r][i]) for i in item_ids} for r in READERS}
    verdicts: Dict[str, Dict[str, Optional[str]]] = {}
    compute: Dict[str, Dict[str, dict]] = {}
    for name, spec in RULES.items():
        verdicts[name] = {i: rule_verdict([votes[v][i] for v in spec["voters"]], spec["k"]) for i in item_ids}
        compute[name] = {}
        for i in item_ids:
            gs = [rgens[v].get(i) for v in spec["voters"]]
            compute[name][i] = {"n_calls": sum(g is not None for g in gs), "wall_s": sum(float(g.get("wall_s") or 0) for g in gs if g),
                                "new_tokens": sum(int(g.get("n_new_tokens") or 0) for g in gs if g)}

    def correct(name, i):
        v = verdicts[name][i]
        return None if v is None else U.normalise_answer(v) == U.normalise_answer(items[i]["primary"]["answer"])

    rules_out: Dict[str, dict] = {}
    csv_rows: List[dict] = []
    for name, spec in RULES.items():
        cov = U.pair_rate([(pid(i), verdicts[name][i] is not None) for i in item_ids], nb, sd)
        acc_v = U.pair_rate([(pid(i), correct(name, i)) for i in item_ids], nb, sd)
        acc_all = U.pair_rate([(pid(i), bool(correct(name, i))) for i in item_ids], nb, sd)
        wall = sum(compute[name][i]["wall_s"] for i in item_ids)
        toks = sum(compute[name][i]["new_tokens"] for i in item_ids)
        rules_out[name] = {"group": spec["group"], "voters": list(spec["voters"]), "k": spec["k"], "coverage": cov.as_dict(),
                           "accuracy_given_verdict": acc_v.as_dict(), "accuracy_all": acc_all.as_dict(),
                           "compute": {"wall_s_total": wall, "wall_s_per_state": wall / len(item_ids), "new_tokens_total": toks,
                                       "calls_per_state": spec["voters"].__len__()}}
        U.log(f"[g4] {name:12s} coverage {U.fmt_count(cov.k, cov.n):16s} acc|verdict {U.fmt_count(acc_v.k, acc_v.n):16s} "
              f"acc(all) {U.fmt_count(acc_all.k, acc_all.n):16s} compute {wall / len(item_ids):.1f} s/state, {toks} new tok")
        for i in item_ids:
            csv_rows.append({"split": split, "rule": name, "group": spec["group"], "item_id": i, "pair_id": pid(i), "family": items[i]["family"],
                             "verdict": verdicts[name][i], "abstained": verdicts[name][i] is None, "correct": correct(name, i),
                             "answer": items[i]["primary"]["answer"], **compute[name][i],
                             "votes": "|".join(str(votes[v][i]) for v in spec["voters"])})
    U.write_csv(out / "g4.csv", csv_rows)

    matched: Dict[str, dict] = {}
    for set_name, rule_names in MATCHED_SETS.items():
        ids_m = U.matched_coverage({r: verdicts[r] for r in rule_names}, item_ids)
        matched[set_name] = {"n_matched_states": len(ids_m), "states": ids_m,
                             "accuracy": {r: U.pair_rate([(pid(i), correct(r, i)) for i in ids_m], nb, sd).as_dict() for r in rule_names}}
        U.log(f"[g4] matched coverage [{set_name}]: {len(ids_m)}/{len(item_ids)} states; " +
              ", ".join(f"{r} {U.fmt_count(matched[set_name]['accuracy'][r]['k'], matched[set_name]['accuracy'][r]['n'])}" for r in rule_names))

    within = {}
    for m in ("nla", "olens"):
        trip = [[votes[f"{m}_s{k}"][i] for k in range(N_SAMPLES)] for i in item_ids]
        within[m] = {"all_three_same": U.pair_rate([(pid(i), all(v is not None for v in t) and len({U.normalise_answer(v) for v in t}) == 1) for i, t in zip(item_ids, trip)], nb, sd).as_dict(),
                     "n_abstentions": sum(v is None for t in trip for v in t), "n_votes": 3 * len(item_ids)}
    summary = {"module": MODULE, "split": split, "frozen": frozen, "n_states": len(item_ids), "n_pairs": len(pair_ids), "n_boot": nb, "seed": sd,
               "pilot_note": "8 states / 4 pairs: feasibility pilot; intervals are too wide to rank rules", "selection": sel,
               "sampling_checked_against": "frozen_config.sampling" if fs else "mutual consistency only", "rules": rules_out, "matched": matched,
               "within_reader": within, "reader_status_counts": {r: dict(Counter(U.claim_status(readers[r][i]) for i in item_ids)) for r in READERS},
               "votes": {r: votes[r] for r in READERS}}
    U.write_json(out / "summary.json", summary)
    if not args.no_fig:
        make_figure(out / "fig_main.png", rules_out, split, len(item_ids))
    U.log(f"[g4] wrote {out}")
    return summary


def make_figure(path: Path, rules_out, split, n_states) -> None:
    """Dot plot, one row per rule (no two rules can collide): accuracy given a verdict | coverage | compute."""
    plt = U.mpl()
    names = list(rules_out)
    n = len(names)
    fig, (ax_acc, ax_cov) = plt.subplots(1, 2, figsize=(11, 0.42 * n + 2.2), sharey=True, gridspec_kw={"width_ratios": [1, 1], "wspace": 0.08})
    ys = list(range(n))[::-1]
    for y, name in zip(ys, names):
        d = rules_out[name]
        col = GROUP_COLORS[d["group"]]
        mk = "o" if d["group"] != "individual" else "s"
        for ax, key, label_k in ((ax_acc, "accuracy_given_verdict", True), (ax_cov, "coverage", True)):
            r = d[key]
            if r["n"] == 0:
                ax.text(0.01, y, "no verdicts", va="center", fontsize=7.5, color=U.INK2)
                continue
            ax.errorbar(r["p"], y, xerr=[[max(r["p"] - r["lo"], 0)], [max(r["hi"] - r["p"], 0)]], fmt=mk, ms=7 if mk == "o" else 5.5,
                        color=col, ecolor=col, elinewidth=1.2, capsize=2.5, zorder=4)
            ax.text(1.03, y, f"{r['k']}/{r['n']}", va="center", fontsize=7.5, color=U.INK2)
        ax_cov.text(1.17, y, f"{d['compute']['wall_s_per_state']:.1f} s · {d['compute']['new_tokens_total'] / max(n_states, 1):.0f} tok /state",
                    va="center", fontsize=7.5, color=U.INK2)
    # group separators
    prev = None
    for y, name in zip(ys, names):
        g = rules_out[name]["group"]
        if prev is not None and g != prev:
            for ax in (ax_acc, ax_cov):
                ax.axhline(y + 0.5, color=U.GRID, lw=0.8, zorder=0)
        prev = g
    for ax, xl in ((ax_acc, f"accuracy given a verdict (%)"), (ax_cov, f"coverage (% of {n_states} states with a verdict)")):
        ax.set_xlim(-0.02, 1.02)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(["0", "25", "50", "75", "100"])
        ax.set_xlabel(xl)
        ax.grid(axis="x", color=U.GRID, lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.set_ylim(-0.7, n - 0.3)
        ax.tick_params(axis="y", length=0)
    ax_acc.set_yticks(ys)
    ax_acc.set_yticklabels(names, fontsize=8.5)
    for lbl, name in zip(ax_acc.get_yticklabels(), names):
        lbl.set_color(GROUP_COLORS[rules_out[name]["group"]])
    ax_cov.text(1.17, n - 0.2, "compute", fontsize=7.5, color=U.INK2, va="center")
    from matplotlib.lines import Line2D

    fig.legend(handles=[Line2D([], [], marker="o" if g != "individual" else "s", ls="", color=c, label=g) for g, c in GROUP_COLORS.items()],
               loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(f"G4 repeats — {split} split, {n_states} states (FEASIBILITY PILOT). Bars: 95% bootstrap CI over 4 base pairs; k/n printed.\n"
                 "cross-method = first NLA + first OLens + J-lens (J-lens enters once); within = 3 samples of one reader", fontsize=9.5, x=0.02, ha="left", y=1.0)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
