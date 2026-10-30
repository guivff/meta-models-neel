"""F2-4 analysis (Mac): (a) NLA FVE and Oracle log-prob as signals of a correct readout; (b) Oracle confusion on Y1 errors.

    python -m projects.g_agreement.f2.t4_analyze [--root .] [--workers 4]
-> results/g_agreement/f2/t4/{t4.md, t4_fve.csv, t4_confusion.csv, t4_summary.json, fig_t4.png}
(a) FVE = 1 - MSE(normalize(pred), normalize(gold)) / predict-the-mean variance of the normalised gold states in this set.
    Labels: F2-1 judge (asserts key / other / neither) and, for G1 sample-0 readouts, rule-v1. AUROC with an item (state) bootstrap.
    Oracle analogue: log p("- X") for the candidate X its readout asserts (and the margin over the other candidate).
(b) gemini-3.8-flash lists the symbols (A-H) each Y1 Oracle readout gives as the final answer; distinct count per readout;
    error vs control difference with an item bootstrap (1,000, seed 0).
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

from projects.g_agreement.w_claims import judge as JD

NB, SEED = 1000, 0
SCHEMA = {"name": "symbols", "strict": True, "schema": {"type": "object", "additionalProperties": False, "required": ["symbols", "evidence"],
          "properties": {"symbols": {"type": "array", "items": {"type": "string"}}, "evidence": {"type": "string"}}}}
SYSTEM = ("You read a description produced by an interpretability tool about a language model's internal state while it solves an arrow-following "
          "puzzle over the symbols A-H. List every symbol that the description gives as the puzzle's final answer (where you end up). Do not list "
          "symbols that only appear as steps, starting points or in rules. JSON: {\"symbols\": [...], \"evidence\": short quote}. Empty list if none.")


def auroc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    from scipy.stats import rankdata
    r = rankdata(np.concatenate([pos, neg]))
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def auroc_boot(rows, score, label, item, nb=NB, seed=SEED):
    """rows with score, label (bool), item; AUROC(label True vs False) with item bootstrap."""
    rows = [r for r in rows if r[score] is not None and r[label] is not None]
    est = auroc([r[score] for r in rows if r[label]], [r[score] for r in rows if not r[label]])
    by = defaultdict(list)
    for r in rows:
        by[r[item]].append(r)
    ids = list(by)
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(nb):
        rr = [x for i in rng.choice(len(ids), len(ids)) for x in by[ids[i]]]
        v = auroc([x[score] for x in rr if x[label]], [x[score] for x in rr if not x[label]])
        if v == v:
            bs.append(v)
    return {"auroc": est, "lo": float(np.percentile(bs, 2.5)) if bs else float("nan"), "hi": float(np.percentile(bs, 97.5)) if bs else float("nan"),
            "n_pos": sum(1 for r in rows if r[label]), "n_neg": sum(1 for r in rows if not r[label]), "n_items": len(ids)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    C, T1, OUT = a.root / "cache/g_agreement/f2/t4", a.root / "cache/g_agreement/f2/t1", a.root / "results/g_agreement/f2/t4"
    OUT.mkdir(parents=True, exist_ok=True)
    jl = lambda p: [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]  # noqa: E731
    S: dict = {}
    # ---------------- (a) FVE
    fve = jl(C / "fve.jsonl")
    pc = json.loads((C / "phaseC_done.json").read_text())
    base = pc["baseline_rawvar_our_states"]
    scored = {r["k"]: r for r in jl(T1 / "readouts_scored.jsonl")}
    g1lab = {r["gen_id"]: r["primary"]["status"] for r in jl(a.root / "results/g_agreement/claims/g1.jsonl")}
    rows = []
    for r in fve:
        rr = {"src": r["src"], "k": r["k"], "item": r["ctx"].split("|")[0], "ctx": r["ctx"], "pos": r["pos"], "extracted": r["extracted"],
              "fve": None if r["mse"] is None else 1 - r["mse"] / base, "cos": r.get("cos")}
        if r["src"] == "f2t1":
            s = scored.get(r["k"], {})
            rr["hit"] = s.get("judge_hit")
            rr["wrong"] = s.get("judge_wrong")
            rr["fmt"] = r["ctx"].split("fmt_")[-1]
        else:
            st = g1lab.get(r["k"])
            rr["hit"] = None if st is None else st == "supports"
            rr["wrong"] = None if st is None else st == "contradicts"
            rr["fmt"] = "g1"
        rows.append(rr)
    ex = [r for r in rows if r["extracted"]]
    S["fve"] = {"baseline": base, "n": len(rows), "n_extracted": len(ex), "mean_fve": float(np.mean([r["fve"] for r in ex])),
                "mean_fve_hit": float(np.mean([r["fve"] for r in ex if r["hit"]])) if any(r["hit"] for r in ex) else None,
                "mean_fve_nohit": float(np.mean([r["fve"] for r in ex if r["hit"] is False])),
                "auroc_hit_vs_rest": auroc_boot(ex, "fve", "hit", "item"),
                "auroc_hit_vs_rest_fmt_a_and_g1": auroc_boot([r for r in ex if r["fmt"] in ("a", "g1")], "fve", "hit", "item")}
    hw = [dict(r, hw=(True if r["hit"] else (False if r["wrong"] else None))) for r in ex]
    S["fve"]["auroc_hit_vs_wrong"] = auroc_boot(hw, "fve", "hw", "item")
    ctxfam = {c["ctx"]: c["family"] for c in json.loads((T1 / "contexts.json").read_text())}
    S["fve"]["by_family"] = {}
    for fam in ("language", "tense", "ownership", "mapping"):
        sub = [r for r in ex if ctxfam.get(r["ctx"], r["item"].split("-")[0]) == fam or (r["src"] == "g1" and r["item"].startswith({"language": "lang", "tense": "tense", "ownership": "own", "mapping": "map"}[fam]))]
        S["fve"]["by_family"][fam] = {"mean_fve": float(np.mean([r["fve"] for r in sub])) if sub else None, "hit_rate": float(np.mean([bool(r["hit"]) for r in sub if r["hit"] is not None])) if sub else None, "n": len(sub)}
    with (OUT / "t4_fve.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["src", "k", "item", "ctx", "pos", "fmt", "extracted", "fve", "cos", "hit", "wrong"]); w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in w.fieldnames})
    # Oracle analogue
    lp = {(r["ctx"], r["layer"], r["pos"]): r for r in jl(C / "olens_lp.jsonl")}
    orow = []
    for k, s in scored.items():
        if s["reader"] != "olens" or not (s.get("judge_hit") or s.get("judge_wrong")):
            continue
        q = lp.get((s["ctx"], s["layer"], s["pos"]))
        if not q:
            continue
        hit = bool(s["judge_hit"])
        orow.append({"item": s["ctx"].split("|")[0], "hit": hit, "lp_asserted": q["lp_key"] if hit else q["lp_other"],
                     "margin_asserted": (q["lp_key"] - q["lp_other"]) * (1 if hit else -1)})
    S["oracle_lp"] = {"n_assertions": len(orow), "n_wrong": sum(not r["hit"] for r in orow),
                      "auroc_lp_asserted": auroc_boot(orow, "lp_asserted", "hit", "item"), "auroc_margin_asserted": auroc_boot(orow, "margin_asserted", "hit", "item")}
    # ---------------- (b) Y1 confusion
    y = jl(C / "y1_oracle.jsonl")
    usage, cache = JD.Usage(C / "judge_usage.json"), JD.Cache(C / "judge_cache.jsonl")

    def judge(r):
        key = f"y1|{r['item_id']}|{r['layer']}"
        got = cache.get(JD.JUDGE_MODEL, key)
        if got is None:
            user = f"DESCRIPTION:\n{JD.clean_readout(r['text'])}"
            for att in range(8):
                try:
                    got = JD.call_judge(SYSTEM, user, SCHEMA, JD.JUDGE_MODEL, usage)
                    break
                except RuntimeError as exc:
                    if "429" not in str(exc) or att == 7:
                        raise
                    time.sleep(15 * (att + 1))
            cache.put(JD.JUDGE_MODEL, key, got)
        syms = sorted({str(x).strip().upper() for x in (got or {}).get("symbols", []) if str(x).strip().upper() in list("ABCDEFGH")})
        return key, syms, (got or {}).get("evidence")

    with cf.ThreadPoolExecutor(a.workers) as exr:
        res = {k: (s, e) for k, s, e in exr.map(judge, y)}
    (C / "judge_usage.json").write_text(json.dumps(usage.data, indent=1))
    for r in y:
        r["symbols"], r["evidence"] = res[f"y1|{r['item_id']}|{r['layer']}"]
        r["n_distinct"] = len(r["symbols"])
        r["names_actual"], r["names_correct"] = r["actual"] in r["symbols"], r["correct"] in r["symbols"]
    with (OUT / "t4_confusion.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["item_id", "set", "layer", "actual", "correct", "symbols", "n_distinct", "names_actual", "names_correct"]); w.writeheader()
        for r in y:
            w.writerow({k: (" ".join(r[k]) if k == "symbols" else r[k]) for k in w.fieldnames})

    def item_mean(rs, f):
        by = defaultdict(list)
        for r in rs:
            by[r["item_id"]].append(f(r))
        return {i: float(np.mean(v)) for i, v in by.items()}

    def diff_boot(e, c, nb=NB, seed=SEED):
        ev, cv = list(e.values()), list(c.values())
        rng = np.random.default_rng(seed)
        bs = [np.mean(rng.choice(ev, len(ev))) - np.mean(rng.choice(cv, len(cv))) for _ in range(nb)]
        return {"error": float(np.mean(ev)), "control": float(np.mean(cv)), "diff": float(np.mean(ev) - np.mean(cv)),
                "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)), "n_error": len(ev), "n_control": len(cv)}

    S["confusion"] = {}
    for L in (None, 44, 48, 52, 56):
        rs = [r for r in y if L is None or r["layer"] == L]
        tag = "all" if L is None else str(L)
        S["confusion"][tag] = {m: diff_boot(item_mean([r for r in rs if r["set"] == "error"], f), item_mean([r for r in rs if r["set"] == "error_control"], f))
                               for m, f in (("n_distinct", lambda r: r["n_distinct"]), ("multi", lambda r: float(r["n_distinct"] >= 2)),
                                            ("names_actual", lambda r: float(r["names_actual"])), ("names_correct", lambda r: float(r["names_correct"])))}
    ex5 = sorted([r for r in y if r["set"] == "error" and r["n_distinct"] >= 3], key=lambda r: (-r["n_distinct"], r["layer"], r["item_id"]))[:5]
    S["examples"] = [{"item_id": r["item_id"], "layer": r["layer"], "actual": r["actual"], "correct": r["correct"], "symbols": r["symbols"],
                      "text": r["text"][:500]} for r in ex5]
    (OUT / "t4_summary.json").write_text(json.dumps(S, indent=1, default=float))
    A = lambda d: f"{d['auroc']:.2f} [{d['lo']:.2f}, {d['hi']:.2f}] (n+ {d['n_pos']}, n− {d['n_neg']})"  # noqa: E731
    D = lambda d, pct=False: (f"{100*d['error']:.0f}% vs {100*d['control']:.0f}%, Δ {100*d['diff']:+.0f} [{100*d['lo']:+.0f}, {100*d['hi']:+.0f}] pts" if pct else  # noqa: E731
                              f"{d['error']:.2f} vs {d['control']:.2f}, Δ {d['diff']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}]")
    f = S["fve"]
    L_ = ["# F2-4 — diagnostics: NLA reconstruction (FVE), Oracle confidence, Oracle confusion", "",
          "Pre-registered in BRIEF_Z.md (2026-10-14).", "", "## (a) Does the NLA's reconstruction quality flag its correct readouts?", "",
          f"Reconstructor: ceselder/qwen3.6-27b-nla-rl `ar_reconstructor` (43-block backbone + value head), EasyNLA recipe. FVE baseline = predict-the-mean "
          f"variance of the {len(rows) and pc['n_rows']} gold states in this set ({base:.3f}); FVE values are comparable only within this set.", "",
          (lambda cb: f"- Mean FVE against the NLA corpus baseline (64 shipped activations, `data/example_activations.parquet`, baseline {cb:.3f}): "
                      f"{1 - float(np.mean([r['mse'] for r in fve if r['mse'] is not None])) / cb:.2f}. Both baselines give FVE near zero: on these end-of-prompt "
                      "states the reconstruction does no better than predicting the mean. The pipeline was not checked on in-distribution corpus explanations, "
                      "so this is inconclusive about the NLA in general.")(json.loads((C / "corpus_baseline.json").read_text())["baseline_rawvar_corpus64"]),
          f"- Readouts with a closed `<explanation>`: {f['n_extracted']}/{f['n']}. Mean FVE {f['mean_fve']:.2f}; hit {f['mean_fve_hit']:.2f} vs no hit {f['mean_fve_nohit']:.2f}.",
          f"- AUROC of FVE, readout asserts the key vs not: {A(f['auroc_hit_vs_rest'])}; chat-template states only: {A(f['auroc_hit_vs_rest_fmt_a_and_g1'])}.",
          f"- AUROC of FVE, asserts the key vs asserts the other candidate: {A(f['auroc_hit_vs_wrong'])}.",
          "- By family (mean FVE / NLA hit rate): " + "; ".join(f"{k} {v['mean_fve']:.2f} / {100*v['hit_rate']:.0f}%" for k, v in f["by_family"].items() if v["mean_fve"] is not None) + ".",
          "", f"Oracle analogue (F2-1 Oracle readouts that assert a candidate, n = {S['oracle_lp']['n_assertions']}, of which {S['oracle_lp']['n_wrong']} assert the wrong one):",
          f"- AUROC of log p(\"- X\") for the asserted X, correct vs wrong: {A(S['oracle_lp']['auroc_lp_asserted'])}.",
          f"- AUROC of the margin log p(asserted) − log p(other): {A(S['oracle_lp']['auroc_margin_asserted'])}.", "",
          "## (b) Oracle confusion on the Y1 puzzles (297 errors, 103 controls; last token; 1 sample per layer)", "",
          "| block | distinct answers per readout (error vs control) | ≥ 2 answers | names the model's answer | names the correct answer |", "|---|---|---|---|---|"]
    for tag in ("44", "48", "52", "56", "all"):
        c = S["confusion"][tag]
        L_.append(f"| {tag} | {D(c['n_distinct'])} | {D(c['multi'], True)} | {D(c['names_actual'], True)} | {D(c['names_correct'], True)} |")
    L_ += ["", "On control items the model's answer is the correct answer, so 'names the model's answer' and 'names the correct answer' coincide there.", "",
           "### Five error readouts with ≥ 3 answers", ""]
    for e in S["examples"]:
        L_.append(f"- **{e['item_id']}, block {e['layer']}** (model answered {e['actual']}, correct {e['correct']}; judge: {', '.join(e['symbols'])}): "
                  f"“{e['text'][:300].replace(chr(10), ' ⏎ ')}…”")
    u = json.loads((C / "judge_usage.json").read_text())
    L_ += ["", f"Judge usage: {json.dumps(u)}."]
    (OUT / "t4.md").write_text("\n".join(L_) + "\n")
    print("\n".join(L_))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
