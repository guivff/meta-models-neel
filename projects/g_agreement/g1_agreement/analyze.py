"""G1 — agreement map between NLA, Oracle-lens and J-lens readouts of the same cached state.

CPU only. Consumes items.json (§1), gens/g1.jsonl (§5), claims/g1.jsonl (§6), states_meta (§4).
Writes to results/g_agreement/g1/ (test, frozen) or results/g_agreement/g1/dev/ (dev):
  fig_main.png     3×3 agree / contradict / missing matrices + accuracy, coverage, target consistency
  agreement.csv    one row per (pair, method pair): n_agree, n_contradict, n_missing
  summary.json     all numbers with raw numerators/denominators and pair-bootstrap CIs
  examples.md      a few readouts per method with their extracted claims

Definitions (rubric.md is authoritative for statuses):
  vote      = the single candidate a readout asserts; unclear / self_contradictory abstain
  agree     = both readouts assert the same candidate; contradict = both assert, different; missing = otherwise
  coverage  = fraction of states with a vote; accuracy = votes equal to the answer key (independently re-checked
              from the value, not the status) over ALL states; acc|covered over voting states
  target consistency = votes equal to the target model's own greedy answer (where that answer is parseable)
Uncertainty: bootstrap over base pairs (16 test pairs / 4 dev pairs), n_boot 2000, seed 0. No significance claims.
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

MODULE = "g1"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(U.DEFAULTS["items"]))
    ap.add_argument("--gens", default=str(U.DEFAULTS["gens_dir"] / "g1.jsonl"))
    ap.add_argument("--claims", default=str(U.DEFAULTS["claims_dir"] / "g1.jsonl"))
    ap.add_argument("--states-meta", default=str(U.DEFAULTS["states_meta"]))
    ap.add_argument("--frozen-config", default=str(U.DEFAULTS["frozen_config"]))
    ap.add_argument("--out", default=None, help="output dir (default results/g_agreement/g1[/dev])")
    ap.add_argument("--split", choices=U.SPLITS, default=None, help="default: test if frozen else dev")
    ap.add_argument("--allow-unfrozen", action="store_true", help="dev-only run without a frozen manifest")
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    return ap.parse_args(argv)


def collect_claims_by_method(items, gens, claims, item_ids, module: str = "g1", sample_idx: int = 0, condition: str = "genuine"):
    """{method: {item_id: claim|None}} and {method: {item_id: gen}} for the first genuine sample of each method."""
    by_method: Dict[str, Dict[str, Optional[dict]]] = {m: {} for m in U.METHODS}
    gens_by_method: Dict[str, Dict[str, dict]] = {m: {} for m in U.METHODS}
    absent: List[str] = []
    for g in gens:
        if g.get("module") != module or g.get("method") not in U.METHODS:
            continue
        if g.get("sample_idx", 0) != sample_idx or g.get("condition", "genuine") != condition:
            continue
        if g["item_id"] not in item_ids:
            continue
        if g["item_id"] != g.get("state_item_id"):
            raise U.SiteMismatchError(f"gen {g['gen_id']}: genuine row reads state of {g.get('state_item_id')}")
        m, iid = g["method"], g["item_id"]
        if iid in gens_by_method[m]:
            raise U.AnalysisError(f"two first-sample {m} rows for {iid}")
        gens_by_method[m][iid] = g
        by_method[m][iid] = claims.get(g["gen_id"])
        if by_method[m][iid] is None:
            absent.append(g["gen_id"])
    for m in U.METHODS:
        for iid in item_ids:
            if iid not in by_method[m]:
                by_method[m][iid] = None
                absent.append(f"{module}|{m}|{iid}|s{sample_idx}")
    return by_method, gens_by_method, absent


def run(args: argparse.Namespace) -> dict:
    frozen, cfg = U.require_frozen(args.frozen_config, args.allow_unfrozen)
    split, out = U.resolve_split_and_out(MODULE, args.split, frozen, args.out)
    out.mkdir(parents=True, exist_ok=True)
    U.log(f"[g1] split={split} frozen={frozen} out={out}")

    meta, items = U.load_items(args.items)
    U.check_dataset_sha(meta, items, cfg)
    gens = U.load_gens(args.gens)
    claims = U.load_claims(args.claims)
    states_meta = U.load_states_meta(args.states_meta)

    item_ids = U.split_item_ids(items, split)
    U.assert_split(items, item_ids, split)
    pair_ids = U.pairs_of(items, item_ids)
    U.log(f"[g1] {len(item_ids)} states in {len(pair_ids)} pairs")

    gens_split = [g for g in gens if g.get("item_id") in set(item_ids)]
    n_checked = U.validate_gens_against_states(gens_split, states_meta)
    U.log(f"[g1] activation-site/cache check passed for {n_checked} reader rows (layer {U.EXPECTED_LAYER}, {U.EXPECTED_HOOK})")

    cbm, gbm, absent = collect_claims_by_method(items, gens_split, claims, set(item_ids))
    if absent:
        U.log(f"[g1] WARNING {len(absent)} reader rows have no claim / no generation; counted as missing: {absent[:6]}")
    tgt = U.target_answers(items, gens_split, claims)
    missing_target = [i for i in item_ids if i not in tgt]
    if missing_target:
        U.log(f"[g1] WARNING {len(missing_target)} states have no target answer row: {missing_target[:6]}")

    pid = lambda i: items[i]["pair_id"]  # noqa: E731
    fam = lambda i: items[i]["family"]  # noqa: E731
    nb, sd = args.n_boot, args.seed

    # ---------------- per-method rates ----------------
    per_method: Dict[str, dict] = {}
    inconsistent: List[str] = []
    for m in U.METHODS:
        cl = cbm[m]
        for i in item_ids:
            if not U.status_value_consistent(cl[i], items[i]):
                inconsistent.append(f"{m}:{i}")
        cover = U.pair_rate([(pid(i), U.vote(cl[i]) is not None) for i in item_ids], nb, sd)
        acc_all = U.pair_rate([(pid(i), bool(U.claim_correct(cl[i], items[i]))) for i in item_ids], nb, sd)
        acc_cov = U.pair_rate([(pid(i), U.claim_correct(cl[i], items[i])) for i in item_ids], nb, sd)
        cons_flags = []
        for i in item_ids:
            v, t = U.vote(cl[i]), tgt.get(i)
            cons_flags.append((pid(i), None if (v is None or t is None) else U.normalise_answer(v) == U.normalise_answer(t)))
        cons = U.pair_rate(cons_flags, nb, sd)
        trunc = U.pair_rate([(pid(i), U.is_truncated(cl[i], gbm[m].get(i))) for i in item_ids], nb, sd)
        statuses = Counter(U.claim_status(cl[i]) for i in item_ids)
        by_family = {}
        for f in U.FAMILIES:
            ids_f = [i for i in item_ids if fam(i) == f]
            if not ids_f:
                continue
            by_family[f] = {
                "coverage": U.pair_rate([(pid(i), U.vote(cl[i]) is not None) for i in ids_f], nb, sd).as_dict(),
                "accuracy_all": U.pair_rate([(pid(i), bool(U.claim_correct(cl[i], items[i]))) for i in ids_f], nb, sd).as_dict(),
                "accuracy_given_covered": U.pair_rate([(pid(i), U.claim_correct(cl[i], items[i])) for i in ids_f], nb, sd).as_dict(),
            }
        per_method[m] = {
            "coverage": cover.as_dict(), "accuracy_all": acc_all.as_dict(), "accuracy_given_covered": acc_cov.as_dict(),
            "target_consistency_given_both": cons.as_dict(), "truncated": trunc.as_dict(),
            "status_counts": dict(statuses), "by_family": by_family,
        }
        U.log(f"[g1] {U.METHOD_LABELS[m]:12s} coverage {cover}")
        U.log(f"[g1] {'':12s} accuracy(all) {acc_all}")
        U.log(f"[g1] {'':12s} accuracy|covered {acc_cov}")
        U.log(f"[g1] {'':12s} target-consistency|both {cons}")
        U.log(f"[g1] {'':12s} truncated {trunc}   statuses {dict(statuses)}")
    if inconsistent:
        U.log(f"[g1] WARNING {len(inconsistent)} claims whose status disagrees with value-vs-key: {inconsistent[:8]} (accuracy uses the value)")

    # target model's own accuracy (source-model errors are kept, shown here)
    tgt_flags = [(pid(i), None if tgt.get(i) is None else U.normalise_answer(tgt[i]) == U.normalise_answer(items[i]["primary"]["answer"])) for i in item_ids]
    tgt_acc = U.pair_rate(tgt_flags, nb, sd)
    tgt_parse = U.pair_rate([(pid(i), tgt.get(i) is not None) for i in item_ids], nb, sd)
    U.log(f"[g1] target model: parseable {tgt_parse}; correct|parseable {tgt_acc}")

    # ---------------- agreement matrices ----------------
    counts, records = U.agreement_matrix(cbm, item_ids)
    pairwise: Dict[str, dict] = {}
    csv_rows: List[dict] = []
    for a_i, a in enumerate(U.METHODS):
        for b_i, b in enumerate(U.METHODS):
            if b_i <= a_i:
                continue
            recs = [r for r in records if r["method_a"] == a and r["method_b"] == b]
            d = {}
            for kind in U.KINDS:
                d[kind] = U.pair_rate([(pid(r["item_id"]), r["outcome"] == kind) for r in recs], nb, sd).as_dict()
            both = [r for r in recs if r["outcome"] != "missing"]
            d["agree_given_both_assert"] = U.pair_rate([(pid(r["item_id"]), r["outcome"] == "agree") for r in both], nb, sd).as_dict()
            # agreement on wrong answers: both assert the same wrong candidate
            d["agree_wrong"] = U.pair_rate([(pid(r["item_id"]), r["outcome"] == "agree" and not U.claim_correct(cbm[a][r["item_id"]], items[r["item_id"]])) for r in recs], nb, sd).as_dict()
            kap = U.pair_kappa(cbm[a], cbm[b], items, item_ids, nb, sd)
            d["kappa"] = {k: v for k, v in kap.items() if k != "per_pair"}
            pairwise[f"{a}|{b}"] = d
            U.log(f"[g1] {a} vs {b}: agree {U.fmt_count(d['agree']['k'], d['agree']['n'])}, contradict {U.fmt_count(d['contradict']['k'], d['contradict']['n'])}, "
                  f"missing {U.fmt_count(d['missing']['k'], d['missing']['n'])}; agree|both {U.fmt_count(d['agree_given_both_assert']['k'], d['agree_given_both_assert']['n'])}; "
                  f"agree-on-wrong {d['agree_wrong']['k']}; kappa {kap['kappa']:.2f} [{kap['lo']:.2f}, {kap['hi']:.2f}] on {kap['n_both']} both-assert states")
            for p in pair_ids:
                rp = [r for r in recs if pid(r["item_id"]) == p]
                kp = kap["per_pair"].get(p, {"n_both": 0, "agree": 0, "a_pos0": 0, "b_pos0": 0})
                csv_rows.append({"split": split, "pair_id": p, "family": items[rp[0]["item_id"]]["family"] if rp else "", "method_a": a, "method_b": b,
                                 "n_items": len(rp), "n_agree": sum(r["outcome"] == "agree" for r in rp),
                                 "n_contradict": sum(r["outcome"] == "contradict" for r in rp),
                                 "n_missing": sum(r["outcome"] == "missing" for r in rp),
                                 "n_agree_wrong": sum(r["outcome"] == "agree" and not U.claim_correct(cbm[a][r["item_id"]], items[r["item_id"]]) for r in rp),
                                 "n_both_assert": kp["n_both"], "n_a_pos0": kp["a_pos0"], "n_b_pos0": kp["b_pos0"],
                                 "kappa_overall": kap["kappa"], "kappa_lo": kap["lo"], "kappa_hi": kap["hi"]})
    U.write_csv(out / "agreement.csv", csv_rows)

    # primary contrast: consensus-k vs best single reader on the same covered states (buckets / LOO are secondary, see consensus.py)
    primary = {f"k{k}": U.consensus_vs_best_single(cbm, items, k, item_ids, n_boot=nb, seed=sd) for k in (2, 3)}
    for kk, d in primary.items():
        U.log(f"[g1] PRIMARY consensus-{kk[1]} vs best single ({d['best_single_reader']}) on {d['n_covered']}/{d['n_states']} covered states: "
              f"{d['consensus_accuracy']['k']}/{d['n_covered']} vs {d['single_reader_accuracy_on_covered'][d['best_single_reader']]['k']}/{d['n_covered']}; "
              f"diff {100 * d['difference_reselected_best']['est']:+.1f} pp [{100 * d['difference_reselected_best']['lo']:.0f}, {100 * d['difference_reselected_best']['hi']:.0f}]")

    # J-lens noise ceiling: candidate-in-top-10 rate on null inputs (method jlens_null, condition noise_ceiling)
    null_ceiling = {}
    for g in gens_split:
        if g.get("method") != "jlens_null":
            continue
        src = (g.get("input") or {}).get("injection_source")
        c = claims.get(g["gen_id"])
        null_ceiling.setdefault(src, []).append((pid(g["item_id"]), c is not None and U.claim_status(c) != "unclear"))
    null_ceiling = {src: U.pair_rate(fl, nb, sd) for src, fl in null_ceiling.items()}
    for src, r in null_ceiling.items():
        U.log(f"[g1] J-lens noise ceiling [{src}]: candidate in top-10 {r}   (compare J-lens coverage {per_method['jlens']['coverage']['k']}/{per_method['jlens']['coverage']['n']})")
    if not null_ceiling:
        U.log("[g1] WARNING no jlens_null rows: J-lens coverage has no noise ceiling")
    per_method["jlens"]["noise_ceiling_candidate_in_top10"] = {src: r.as_dict() for src, r in null_ceiling.items()}

    # all-three agreement
    all3 = []
    for i in item_ids:
        vs = [U.vote(cbm[m][i]) for m in U.METHODS]
        all3.append((pid(i), all(v is not None for v in vs) and len({U.normalise_answer(v) for v in vs}) == 1))
    all3_rate = U.pair_rate(all3, nb, sd)
    U.log(f"[g1] all three assert the same candidate: {all3_rate}")

    summary = {
        "module": MODULE, "split": split, "frozen": frozen, "n_states": len(item_ids), "n_pairs": len(pair_ids),
        "n_boot": nb, "seed": sd, "ci": "95% pair bootstrap", "absent_rows": absent, "status_value_inconsistent": inconsistent,
        "per_method": per_method, "target_model": {"parseable": tgt_parse.as_dict(), "accuracy_given_parseable": tgt_acc.as_dict()},
        "pairwise": pairwise, "all_three_agree": all3_rate.as_dict(), "primary_endpoint_consensus_vs_best_single": primary,
        "matrix_counts": {k: counts[k].tolist() for k in U.KINDS}, "matrix_methods": list(U.METHODS),
        "items": {i: {"family": fam(i), "pair_id": pid(i), "answer": items[i]["primary"]["answer"], "target_answer": tgt.get(i),
                      **{m: {"status": U.claim_status(cbm[m][i]), "value": U.vote(cbm[m][i]), "correct": U.claim_correct(cbm[m][i], items[i])} for m in U.METHODS}}
                  for i in item_ids},
    }
    U.write_json(out / "summary.json", summary)
    write_examples(out / "examples.md", items, item_ids, cbm, gbm, tgt, split)
    if not args.no_fig:
        make_figure(out / "fig_main.png", counts, per_method, len(item_ids), split, items, item_ids, cbm, pid, nb, sd, pairwise, null_ceiling)
    U.log(f"[g1] wrote {out / 'fig_main.png'}, agreement.csv, summary.json, examples.md")
    return summary


def write_examples(path: Path, items, item_ids, cbm, gbm, tgt, split: str, per_status: int = 2) -> None:
    lines = [f"# G1 examples ({split} split)", "", "Readouts are shown verbatim (first sample) with the extracted claim. "
             "`status` is the rubric label relative to the answer key; `value` is the asserted candidate.", ""]
    for m in U.METHODS:
        lines.append(f"## {U.METHOD_LABELS[m]}")
        shown = Counter()
        for i in item_ids:
            c = cbm[m][i]
            st = U.claim_status(c)
            if shown[st] >= per_status:
                continue
            shown[st] += 1
            it = items[i]
            lines += [f"### {i} ({it['family']}) — status `{st}`", "",
                      f"- prompt: {it['prompt_text']}", f"- answer key: **{it['primary']['answer']}**; target model answered: {tgt.get(i)!r}",
                      f"- readout: {U.readout_text(gbm[m].get(i))}"]
            if c is not None:
                lines.append(f"- claim: value={c['primary'].get('value')!r}; evidence: {c['primary'].get('evidence', '')!r}; extractor={c.get('extractor')}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def make_figure(path: Path, counts, per_method, n_items: int, split: str, items, item_ids, cbm, pid, nb, sd, pairwise=None, null_ceiling=None) -> None:
    plt = U.mpl()
    fig = plt.figure(figsize=(12.5, 7.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.05, 1], hspace=0.5, wspace=0.35)
    titles = {"agree": "Agree on asserted answer", "contradict": "Contradict (both assert, differ)", "missing": "Missing (≥1 abstains)"}
    kap_txt = {}
    for key, d in (pairwise or {}).items():
        a, b = key.split("|")
        i, j = U.METHODS.index(a), U.METHODS.index(b)
        kp = d.get("kappa", {})
        if kp and not (kp["kappa"] != kp["kappa"]):
            kap_txt[(i, j)] = kap_txt[(j, i)] = f"κ={kp['kappa']:.2f}\n[{kp['lo']:.2f}, {kp['hi']:.2f}]"
    for j, kind in enumerate(U.KINDS):
        ax = fig.add_subplot(gs[0, j])
        U.draw_matrix(ax, counts[kind], U.METHODS, f"{titles[kind]}\n(count / {n_items} states, %)" + ("; κ chance-corrected" if kind == "agree" else ""),
                      n_items, extra=kap_txt if kind == "agree" else None)
    panels = [("accuracy_all", "Accuracy vs answer key (% of all states)"), ("coverage", "Coverage (% of states with a vote)"),
              ("target_consistency_given_both", "Consistency with target's own answer\n(% of states where both answered)")]
    for j, (key, ttl) in enumerate(panels):
        ax = fig.add_subplot(gs[1, j])
        for k, m in enumerate(U.METHODS):
            r = U.Rate(**{kk: vv for kk, vv in per_method[m][key].items() if kk != "ci"})
            U.bar_ci(ax, k, r, U.METHOD_COLORS[m])
            if key in ("accuracy_all", "coverage"):
                for f, mk in U.FAMILY_MARKERS.items():
                    bf = per_method[m]["by_family"].get(f)
                    if bf:
                        ax.scatter(k + 0.28, bf[key]["p"], marker=mk, s=18, facecolor=SURFACE_, edgecolor=U.INK2, lw=0.8, zorder=6)
        if key == "coverage" and null_ceiling:
            kj = U.METHODS.index("jlens")
            for n_i, (src, r) in enumerate(sorted(null_ceiling.items())):
                ax.plot([kj - 0.42, kj + 0.42], [r.p] * 2, color=U.INK, lw=1.3, ls=(0, (3, 2)) if n_i == 0 else (0, (1, 1.5)), zorder=7)
        ax.set_xticks(range(len(U.METHODS)))
        ax.set_xticklabels([U.METHOD_LABELS[m] for m in U.METHODS])
        U.style_ax(ax, "%", (0, 1.15))
        ax.set_title(ttl)
    from matplotlib.lines import Line2D

    handles = [Line2D([], [], marker=mk, ls="", mfc=SURFACE_, mec=U.INK2, label=f"{f} (per-family point)") for f, mk in U.FAMILY_MARKERS.items()]
    for n_i, (src, r) in enumerate(sorted((null_ceiling or {}).items())):
        handles.append(Line2D([], [], color=U.INK, ls=(0, (3, 2)) if n_i == 0 else (0, (1, 1.5)),
                              label=f"J-lens noise ceiling, null input = {src}: candidate in top-10 {r.k}/{r.n}"))
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(f"G1 agreement map — {split} split, {n_items} states; bars = 95% CI from bootstrap over base pairs; k/n printed", y=0.995)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


SURFACE_ = U.SURFACE


def main(argv=None) -> dict:
    return run(parse_args(argv))


if __name__ == "__main__":
    main()
