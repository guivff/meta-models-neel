"""W3 report: per-reader claim counts, input/computation shares, precision with item-level bootstrap CI,
cross-tab with rule-v1 correctness (results/g_agreement/claims/g1.jsonl), second-judge kappa.

    .venv/bin/python -m projects.g_agreement.w_claims.w3 --claims results/g_agreement/w/claims/claims_g1.jsonl \
        --relabel results/g_agreement/w/claims/relabel_g1.jsonl --rule results/g_agreement/claims/g1.jsonl \
        --usage results/g_agreement/w/claims/judge_usage.json --out results/g_agreement/w/claims/W3_g1
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from .stats import cohen_kappa, kappa_bootstrap, precision_item_bootstrap, wilson

N_BOOT, SEED = 1000, 0


def _read_jsonl(p: Path) -> List[dict]:
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def rule_correctness(rule_rows: List[dict]) -> Dict[str, Optional[bool]]:
    """gen_id -> rule-v1 primary status == 'supports' (None if the row is missing)."""
    return {r["gen_id"]: (r.get("primary") or {}).get("status") == "supports" for r in rule_rows}


def summarise(claims: List[dict], rule: Dict[str, Optional[bool]], n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    real = [c for c in claims if c.get("claim_text")]
    readouts = {}
    for c in claims:
        readouts.setdefault(c["gen_id"], {"reader": c["reader"], "item_id": c["item_id"], "claims": []})
        if c.get("claim_text"):
            readouts[c["gen_id"]]["claims"].append(c)
    out = {"n_boot": n_boot, "seed": seed, "readers": {}}
    for reader in sorted({c["reader"] for c in claims}):
        rs = {g: v for g, v in readouts.items() if v["reader"] == reader}
        cs = [c for c in real if c["reader"] == reader]
        types = Counter(c["claim_type"] for c in cs)
        labels = Counter(c["judge_label"] for c in cs)
        d = {"n_readouts": len(rs), "n_items": len({v["item_id"] for v in rs.values()}), "n_claims": len(cs),
             "claims_per_readout": len(cs) / max(len(rs), 1),
             "share": {t: types[t] / max(len(cs), 1) for t in ("input", "computation", "unverifiable")},
             "label_counts": dict(labels), "precision": {}, "readout_level": {}, "by_family": {}}
        for t in ("input", "computation", "all"):
            sub = [c for c in cs if t == "all" or c["claim_type"] == t]
            d["precision"][t] = precision_item_bootstrap([c["item_id"] for c in sub], [c["truth"] for c in sub],
                                                         n_boot, seed)
        # readout-level rates (Wilson)
        for name, fn in (("any_false", lambda v: any(c["truth"] is False for c in v["claims"])),
                         ("any_computation_false", lambda v: any(c["judge_label"] == "computation_false" for c in v["claims"])),
                         ("any_computation_true", lambda v: any(c["judge_label"] == "computation_true" for c in v["claims"])),
                         ("no_claims", lambda v: len(v["claims"]) == 0)):
            k = sum(fn(v) for v in rs.values())
            p, lo, hi = wilson(k, len(rs))
            d["readout_level"][name] = {"k": k, "n": len(rs), "rate": p, "lo": lo, "hi": hi}
        # per-family precision (point estimates only; 8 items each)
        for fam in sorted({c.get("family") for c in cs if c.get("family")}):
            fc = [c for c in cs if c.get("family") == fam]
            d["by_family"][fam] = {t: precision_item_bootstrap([c["item_id"] for c in fc if c["claim_type"] == t],
                                                               [c["truth"] for c in fc if c["claim_type"] == t],
                                                               n_boot, seed) for t in ("input", "computation")}
        # cross-tab with rule-v1 correctness of the same readout
        xt = {}
        for rule_ok in (True, False):
            sel = [v for g, v in rs.items() if rule.get(g) is rule_ok]
            cc = [c for v in sel for c in v["claims"] if c["claim_type"] == "computation"]
            xt["rule_supports" if rule_ok else "rule_other"] = {
                "n_readouts": len(sel),
                "computation_precision": precision_item_bootstrap([c["item_id"] for c in cc], [c["truth"] for c in cc],
                                                                  n_boot, seed),
                "readouts_with_computation_true_and_no_false": sum(
                    any(c["judge_label"] == "computation_true" for c in v["claims"])
                    and not any(c["judge_label"] == "computation_false" for c in v["claims"]) for v in sel),
                "readouts_with_any_computation_false": sum(
                    any(c["judge_label"] == "computation_false" for c in v["claims"]) for v in sel)}
        d["crosstab_rule_v1"] = xt
        out["readers"][reader] = d
    return out


def kappa_section(relabel: List[dict], n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    a = [r["judge1_label"] for r in relabel]
    b = [r["judge2_label"] for r in relabel]
    five = cohen_kappa(a, b)
    lo, hi = kappa_bootstrap(a, b, n_boot, seed)
    five.update({"lo": lo, "hi": hi})
    both = [(x.endswith("_true"), y.endswith("_true")) for x, y in zip(a, b)
            if x and y and x.startswith("computation") and y.startswith("computation")]
    binary = cohen_kappa([p[0] for p in both], [p[1] for p in both])
    blo, bhi = kappa_bootstrap([p[0] for p in both], [p[1] for p in both], n_boot, seed)
    binary.update({"lo": blo, "hi": bhi})
    type_agree = sum(bool(y) and y.startswith("computation") for y in b) / max(len(b), 1)
    conf = Counter((x, y) for x, y in zip(a, b))
    per_reader = {}
    for reader in sorted({r["reader"] for r in relabel}):
        rr = [r for r in relabel if r["reader"] == reader]
        per_reader[reader] = cohen_kappa([r["judge1_label"] for r in rr], [r["judge2_label"] for r in rr])
    return {"n_claims": len(relabel), "judge1": relabel[0]["judge1_model"] if relabel else None,
            "judge2": relabel[0]["judge2_model"] if relabel else None,
            "kappa_5way": five, "kappa_truth_both_computation": binary, "n_both_computation": len(both),
            "judge2_keeps_computation_type": type_agree, "per_reader_5way": per_reader,
            "confusion": {f"{k[0]}->{k[1]}": v for k, v in sorted(conf.items(), key=lambda kv: -kv[1])}}


def _f2(x) -> str:
    return "n/a" if x is None else f"{x:.2f}"


def fmt_p(d: dict) -> str:
    if d["precision"] is None:
        return "n/a"
    return f"{100 * d['precision']:.0f}% [{100 * d['lo']:.0f}, {100 * d['hi']:.0f}] (n={d['n_claims']})"


def render_md(summary: dict, kap: Optional[dict], usage: Optional[dict], title: str, notes: List[str]) -> str:
    L = [f"# {title}", "",
         "Judge: `google/gemini-3.8-flash` (OpenRouter, temperature 0, strict JSON schema), adapted from Michael "
         "Kenney's `nla-consistency/scripts/claim_judge.py` (see `projects/g_agreement/w_claims/judge.py`). "
         "Precision = true / (true + false) pooled over claims; CI = item-level bootstrap "
         f"({summary['n_boot']} resamples, seed {summary['seed']}); unverifiable claims excluded from precision.", ""]
    L += ["## Precision table", "",
          "| reader | readouts | items | claims | claims/readout | input share | computation share | unverifiable | "
          "input precision [95% CI] | computation precision [95% CI] | all | readouts with >=1 false claim |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r, d in summary["readers"].items():
        af = d["readout_level"]["any_false"]
        L.append(f"| {r} | {d['n_readouts']} | {d['n_items']} | {d['n_claims']} | {d['claims_per_readout']:.1f} | "
                 f"{100 * d['share']['input']:.0f}% | {100 * d['share']['computation']:.0f}% | "
                 f"{100 * d['share']['unverifiable']:.0f}% | {fmt_p(d['precision']['input'])} | "
                 f"{fmt_p(d['precision']['computation'])} | {fmt_p(d['precision']['all'])} | "
                 f"{100 * af['rate']:.0f}% [{100 * af['lo']:.0f}, {100 * af['hi']:.0f}] |")
    L += ["", "## Per family (point estimates, 8 test items per family)", "",
          "| reader | family | input precision | computation precision |", "|---|---|---|---|"]
    for r, d in summary["readers"].items():
        for fam, v in d["by_family"].items():
            L.append(f"| {r} | {fam} | {fmt_p(v['input'])} | {fmt_p(v['computation'])} |")
    L += ["", "## Cross-tab with rule-v1 correctness of the same readout", "",
          "No native log-odds exist for the G1 states (`cache/g_agreement/x/x1_lo.jsonl` covers the X bank), so the "
          "cross-tab uses the rule-v1 extractor's primary status on the same readout "
          "(`results/g_agreement/claims/g1.jsonl`; `supports` = the rule read the correct candidate).", "",
          "| reader | rule-v1 | readouts | computation precision [CI] | readouts: comp_true & no comp_false | "
          "readouts: any comp_false |", "|---|---|---|---|---|---|"]
    for r, d in summary["readers"].items():
        for k, v in d["crosstab_rule_v1"].items():
            L.append(f"| {r} | {k} | {v['n_readouts']} | {fmt_p(v['computation_precision'])} | "
                     f"{v['readouts_with_computation_true_and_no_false']} | {v['readouts_with_any_computation_false']} |")
    if kap:
        k5, kb = kap["kappa_5way"], kap["kappa_truth_both_computation"]
        L += ["", "## Second judge (computation-claim subsample)", "",
              f"Second judge: `{kap['judge2']}` re-labelled {kap['n_claims']} computation claims (claims fixed, "
              f"labels re-assigned, same context). 5-way label kappa = {k5['kappa']:.2f} "
              f"[{k5['lo']:.2f}, {k5['hi']:.2f}], raw agreement {100 * k5['agreement']:.0f}%. "
              f"Among the {kap['n_both_computation']} claims both judges call computation, true/false kappa = "
              f"{_f2(kb['kappa'])} [{_f2(kb['lo'])}, {_f2(kb['hi'])}]. "
              f"Judge 2 kept the computation type on "
              f"{100 * kap['judge2_keeps_computation_type']:.0f}% of claims.", "",
              "Per reader (5-way): " + ", ".join(f"{r}: kappa={v['kappa']:.2f} (n={v['n']})"
                                                 for r, v in kap["per_reader_5way"].items()), "",
              "Confusion (judge1 -> judge2, count): " + ", ".join(f"{k}: {v}" for k, v in kap["confusion"].items())]
    if usage:
        L += ["", "## API usage", ""]
        for m, u in usage.items():
            if isinstance(u, dict):
                L.append(f"- `{m}`: {u['calls']} calls, {u['prompt_tokens']} prompt + {u['completion_tokens']} "
                         f"completion tokens, ${u['cost_usd']:.3f}")
    if notes:
        L += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", type=Path, required=True)
    ap.add_argument("--relabel", type=Path, default=None)
    ap.add_argument("--rule", type=Path, default=None)
    ap.add_argument("--usage", type=Path, default=None)
    ap.add_argument("--out", type=Path, required=True, help="path stem; writes <stem>.md and <stem>.json")
    ap.add_argument("--module", default="g1", help="restrict to this module (g1 primary; 'all' for everything)")
    ap.add_argument("--title", default="W3 — claim-level precision on the G1 test readouts")
    ap.add_argument("--note", action="append", default=[])
    a = ap.parse_args(argv)
    claims = _read_jsonl(a.claims)
    if a.module != "all":
        claims = [c for c in claims if c.get("module") == a.module]
    rule = rule_correctness(_read_jsonl(a.rule)) if a.rule else {}
    summary = summarise(claims, rule)
    kap = kappa_section(_read_jsonl(a.relabel)) if a.relabel and Path(a.relabel).exists() else None
    usage = json.loads(Path(a.usage).read_text()) if a.usage and Path(a.usage).exists() else None
    payload = {"summary": summary, "kappa": kap, "usage": usage, "claims_file": str(a.claims), "module": a.module}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    Path(str(a.out) + ".json").write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    Path(str(a.out) + ".md").write_text(render_md(summary, kap, usage, a.title, a.note))
    print(render_md(summary, kap, usage, a.title, a.note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
