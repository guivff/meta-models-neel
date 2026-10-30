"""F2-5 analysis (Mac): Agam's exact stems with a copy control. Rules in BRIEF_Z.md (follow-ups 3).

    python -m projects.g_agreement.f2.t5_analyze [--root .] [--workers 4]
-> results/g_agreement/f2/t5/{t5.md, t5.csv, t5_summary.json}
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from projects.g_agreement.core import scoring as SC
from projects.g_agreement.f2.t1_analyze import SCHEMA, SYSTEM, boot_diff, boot_mean
from projects.g_agreement.w_claims import judge as JD

CELLS = [("olens", 44), ("olens", 56), ("nla", 42)]
JL_LAYERS = list(range(36, 61, 4))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--rule-only", action="store_true", help="score free text with rule-v1 instead of the LLM judge (OpenRouter credits exhausted 2026-10-14)")
    a = ap.parse_args()
    C, OUT = a.root / "cache/g_agreement/f2/t5", a.root / "results/g_agreement/f2/t5"
    OUT.mkdir(parents=True, exist_ok=True)
    ctxs = {c["ctx"]: c for c in json.loads((C / "contexts.json").read_text())}
    items = {it["item_id"]: it for it in json.loads((a.root / "projects/g_agreement/dataset/items.json").read_text())["items"]}
    reads = [json.loads(x) for x in (C / "readouts.jsonl").read_text().splitlines() if x.strip()]
    usage, cache = JD.Usage(C / "judge_usage.json"), JD.Cache(C / "judge_cache.jsonl")

    def judge(r):
        c = ctxs[r["ctx"]]; it = items[c["item_id"]]
        cands = sorted([c["key"], c["other"]]); key = f"t5|{r['k']}"
        got = cache.get(JD.JUDGE_MODEL, key)
        if got is None:
            user = f"QUESTION: {it['primary']['question']}\nCANDIDATES: {cands[0]} | {cands[1]}\n\nDESCRIPTION:\n{JD.clean_readout(r['text'])}"
            for att in range(8):
                try:
                    got = JD.call_judge(SYSTEM, user, SCHEMA, JD.JUDGE_MODEL, usage); break
                except RuntimeError as exc:
                    if "429" not in str(exc) or att == 7:
                        raise
                    time.sleep(15 * (att + 1))
            cache.put(JD.JUDGE_MODEL, key, got)
        return r["k"], str((got or {}).get("answer", "")).strip()

    todo = [r for r in reads if r["reader"] in ("olens", "nla")]
    if a.rule_only:
        ans = {}
        for r in todo:
            c = ctxs[r["ctx"]]
            st = SC.extract_claims(r["text"], items[c["item_id"]], r["reader"], r.get("finish_reason"))["primary"]
            ans[r["k"]] = c["key"] if st["status"] == "supports" else (c["other"] if st["status"] == "contradicts" else "neither")
    else:
        with cf.ThreadPoolExecutor(a.workers) as ex:
            ans = dict(ex.map(judge, todo))
        (C / "judge_usage.json").write_text(json.dumps(usage.data, indent=1))
    per = defaultdict(lambda: defaultdict(list))
    jl = defaultdict(lambda: defaultdict(list))
    for r in reads:
        c = ctxs[r["ctx"]]
        tag = (c["variant"], c["format"])
        if r["reader"] == "jlens":
            st = SC.extract_claims(r["tokens_decoded"], items[c["item_id"]], "jlens")["primary"]["status"]
            jl[(r["layer"], r["pos"], c["family"]) + tag][c["pair_id"]].append(float(st == "supports"))
            continue
        aw = ans[r["k"]].lower()
        per[("hit", r["reader"], r["layer"], r["pos"], c["family"]) + tag][c["item_id"]].append(float(aw == c["key"].lower()))
        per[("other", r["reader"], r["layer"], r["pos"], c["family"]) + tag][c["item_id"]].append(float(aw == c["other"].lower()))

    def agg(metric, rd, L, pos, fams, tag):
        """pair -> [per-state mean] for the given families."""
        out = defaultdict(list)
        for fam in fams:
            for iid, v in per.get((metric, rd, L, pos, fam) + tag, {}).items():
                out[iid[:-1]].append(float(np.mean(v)))
        return out

    S = {"rescue": {}, "copy": {}, "keystem": {}, "jlens": {}}
    rows = []
    OM, LT = ("ownership", "mapping"), ("language", "tense")
    for rd, L in CELLS:
        base = agg("hit", rd, L, "last", OM, ("a", "chat"))
        for fmt in ("chat", "plain"):
            g = agg("hit", rd, L, "last", OM, ("generic", fmt))
            d = boot_diff(base, g)
            S["rescue"][f"{rd}@{L}|{fmt}"] = {"a": boot_mean(base), "generic": boot_mean(g), "diff": d, "flag": bool(d["d"] >= 0.20 and d["lo"] > 0)}
            o_other = boot_mean(agg("other", rd, L, "last", LT, ("otherstem", fmt)))
            o_key = boot_mean(agg("hit", rd, L, "last", LT, ("otherstem", fmt)))
            k_key = boot_mean(agg("hit", rd, L, "last", LT, ("keystem", fmt)))
            S["copy"][f"{rd}@{L}|{fmt}"] = {"names_stem_word_under_otherstem": o_other, "names_key_under_otherstem": o_key,
                                           "names_key_under_keystem": k_key, "flag": bool(o_other["p"] >= 0.5 and o_key["p"] <= 0.25)}
            rows.append({"reader": f"{rd}@{L}", "format": fmt, "own_map_a": base and boot_mean(base)["p"], "own_map_generic": boot_mean(g)["p"],
                         "rescue_diff": d["d"], "lt_keystem_key": k_key["p"], "lt_otherstem_key": o_key["p"], "lt_otherstem_stemword": o_other["p"]})
    for L in JL_LAYERS:
        for fam in ("ownership", "mapping", "language", "tense"):
            for tag in (("a", "chat"), ("generic", "chat"), ("generic", "plain"), ("keystem", "chat"), ("keystem", "plain"), ("otherstem", "chat"), ("otherstem", "plain")):
                d = jl.get((L, "last", fam) + tag)
                if d:
                    S["jlens"][f"{L}|{fam}|{tag[0]}|{tag[1]}"] = float(np.mean([x for v in d.values() for x in v]))
    rescue = [k for k, v in S["rescue"].items() if v["flag"]]
    copy = [k for k, v in S["copy"].items() if v["flag"]]
    S["decision"] = {"rescue_flags": rescue, "copy_flags": copy}
    (OUT / "t5_summary.json").write_text(json.dumps(S, indent=1, default=float))
    with (OUT / "t5.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    pc = lambda c: "–" if not c or c.get("p") != c.get("p") else f"{100*c['p']:.0f}% [{100*c['lo']:.0f}, {100*c['hi']:.0f}]"  # noqa: E731
    Ls = ["# F2-5 — Agam's exact stems, with a copy control (32 G1 states)", "",
          "Pre-registered in BRIEF_Z.md (follow-ups 3). Free-text hits at position last (scorer below); pair-bootstrap 95% CIs.", "",
          f"**Rescue (ownership + mapping, \"The answer is\" vs chat template, +20 points with CI > 0): {'yes for ' + ', '.join(rescue) if rescue else 'no reader-layer'}.**",
          f"**Copying (language + tense, stem names the wrong candidate: reader names it ≥ 50% and the key ≤ 25%): {'yes for ' + ', '.join(copy) if copy else 'no reader-layer'}.**", "",
          "## Ownership + mapping: does \"The answer is\" rescue the free-text hits?", "", "| reader | format | chat template (no stem) | \"The answer is\" | Δ [CI] |", "|---|---|---|---|---|"]
    for k, v in S["rescue"].items():
        rd, fmt = k.split("|")
        d = v["diff"]
        Ls.append(f"| {rd} | {fmt} | {pc(v['a'])} | {pc(v['generic'])} | {100*d['d']:+.0f} [{100*d['lo']:+.0f}, {100*d['hi']:+.0f}] |")
    Ls += ["", "## Language + tense: does the reader copy the stem's word?", "",
           "| reader | format | names key, stem names key | names key, stem names the other | names the stem's (wrong) word, stem names the other |", "|---|---|---|---|---|"]
    for k, v in S["copy"].items():
        rd, fmt = k.split("|")
        Ls.append(f"| {rd} | {fmt} | {pc(v['names_key_under_keystem'])} | {pc(v['names_key_under_otherstem'])} | {pc(v['names_stem_word_under_otherstem'])} |")
    Ls += ["", "## J-lens names the answer (rule-v1, top-10, last position), by block", ""]
    for fam in ("ownership", "mapping", "language", "tense"):
        tags = [("a", "chat"), ("generic", "chat"), ("generic", "plain")] if fam in OM else [("a", "chat"), ("keystem", "chat"), ("otherstem", "chat"), ("keystem", "plain"), ("otherstem", "plain")]
        Ls += [f"**{fam}**", "", "| variant | " + " | ".join(f"L{L}" for L in JL_LAYERS) + " |", "|---|" + "---|" * len(JL_LAYERS)]
        for t in tags:
            Ls.append(f"| {t[0]} / {t[1]} | " + " | ".join(("–" if f"{L}|{fam}|{t[0]}|{t[1]}" not in S["jlens"] else f"{100*S['jlens'][f'{L}|{fam}|{t[0]}|{t[1]}']:.0f}%") for L in JL_LAYERS) + " |")
        Ls.append("")
    Ls += [("Scorer: rule-v1 (core/scoring.py), because the OpenRouter credits ran out after 78 judge calls; in F2-1 rule-v1 and the "
            "judge agreed on 92% of readouts." if a.rule_only else f"Judge: {JD.JUDGE_MODEL}."), "", "For language and tense the stem places a candidate word right before the read position, so naming it can be copying, not reading."]
    (OUT / "t5.md").write_text("\n".join(Ls) + "\n")
    print("\n".join(Ls[:30]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
