"""F2-1 analysis (Mac): score the prefill-vs-template readouts and apply the pre-registered rule (BRIEF_Z.md, 2026-10-14).

    python -m projects.g_agreement.f2.t1_analyze [--root .] [--no-judge] [--workers 8]

Scorers: rule-v1 (core/scoring.py; hit = 'supports', wrong = 'contradicts'); LLM answer judge (gemini-3.8-flash via
w_claims/judge.py; sees the item's question, the two candidates in alphabetical order and the readout, never the prompt;
hit = asserts the key, wrong = asserts the other); native log-odds (win = lo_A + lo_B > 0 per pair).
Per state, a free-text rate is the share of its 4 samples. CIs: pair bootstrap over the 16 pairs (1,000, seed 0); Wilson on
the pooled sample counts as a secondary. Contrasts (b)-(a) and (c)-(a) are paired over pairs.
-> results/g_agreement/f2/t1/{t1.md, t1.csv, t1_summary.json, fig_t1.png}
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from projects.g_agreement.core import scoring as SC
from projects.g_agreement.w_claims import judge as JD

FORMATS = ("a", "b", "c")
POS = ("last", "last-1", "last-2")
CELLS = [("olens", 44), ("olens", 42), ("nla", 42), ("jlens", 42), ("jlens", 44)]
FMT_LABEL = {"a": "chat template", "b": "template + answer prefill", "c": "plain text + stem"}
NB, SEED, THRESH = 1000, 0, 0.20
SCHEMA = {"name": "answer", "strict": True, "schema": {"type": "object", "additionalProperties": False, "required": ["answer", "evidence"],
          "properties": {"answer": {"type": "string"}, "evidence": {"type": "string"}}}}
SYSTEM = ("You read a description produced by an interpretability tool. The tool looked at a language model's internal state while the "
          "model was processing a prompt, and wrote what it thinks that state contains. You do NOT see the prompt. Decide which of the "
          "two candidate answers to the QUESTION the description asserts. Reply with JSON: {\"answer\": one of the two candidates exactly "
          "as written, or \"both\" if it asserts both, or \"neither\" if it asserts neither or is unclear; \"evidence\": a short quote}. "
          "Only count an explicit assertion or an unambiguous implication (e.g. a Spanish word as the reply implies Spanish).")


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def boot_mean(by_pair: dict, nb=NB, seed=SEED):
    """by_pair: pair -> list of per-state values (None dropped). Mean over states, CI by resampling pairs."""
    pids = [p for p, v in by_pair.items() if any(x is not None for x in v)]
    vals = {p: [x for x in by_pair[p] if x is not None] for p in pids}
    if not pids:
        return {"p": float("nan"), "lo": float("nan"), "hi": float("nan"), "n_states": 0}
    est = float(np.mean([x for p in pids for x in vals[p]]))
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(nb):
        pick = rng.choice(len(pids), len(pids), replace=True)
        xs = [x for i in pick for x in vals[pids[i]]]
        bs.append(np.mean(xs))
    return {"p": est, "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)), "n_states": sum(len(v) for v in vals.values())}


def boot_diff(a: dict, b: dict, nb=NB, seed=SEED):
    """paired: mean over pairs of (mean_state(b) - mean_state(a)); pairs with both present."""
    pids = [p for p in a if p in b and any(x is not None for x in a[p]) and any(x is not None for x in b[p])]
    if not pids:
        return {"d": float("nan"), "lo": float("nan"), "hi": float("nan"), "n_pairs": 0}
    da = {p: np.mean([x for x in b[p] if x is not None]) - np.mean([x for x in a[p] if x is not None]) for p in pids}
    est = float(np.mean(list(da.values())))
    rng = np.random.default_rng(seed)
    bs = [np.mean([da[pids[i]] for i in rng.choice(len(pids), len(pids), replace=True)]) for _ in range(nb)]
    return {"d": est, "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)), "n_pairs": len(pids)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    C, OUT = a.root / "cache/g_agreement/f2/t1", a.root / "results/g_agreement/f2/t1"
    OUT.mkdir(parents=True, exist_ok=True)
    ctxs = {c["ctx"]: c for c in json.loads((C / "contexts.json").read_text())}
    items = {it["item_id"]: it for it in json.loads((a.root / "projects/g_agreement/dataset/items.json").read_text())["items"]}
    reads = [json.loads(x) for x in (C / "readouts.jsonl").read_text().splitlines() if x.strip()]
    los = [json.loads(x) for x in (C / "lo.jsonl").read_text().splitlines() if x.strip()]
    # ---- rule-v1
    for r in reads:
        c = ctxs[r["ctx"]]
        it = items[c["item_id"]]
        if r["reader"] == "jlens":
            if r["layer"] not in (42, 44):
                continue
            body = SC.extract_claims(r["tokens_decoded"], it, "jlens")
        else:
            body = SC.extract_claims(r["text"], it, r["reader"], r.get("finish_reason"))
        st = body["primary"]["status"]
        r["rule"] = st
        r["rule_hit"], r["rule_wrong"] = st == "supports", st == "contradicts"
    # ---- LLM judge (Oracle, NLA)
    usage = JD.Usage(C / "judge_usage.json")
    cache = JD.Cache(C / "judge_cache.jsonl")
    todo = [r for r in reads if r["reader"] in ("olens", "nla")]

    def judge(r):
        c = ctxs[r["ctx"]]
        it = items[c["item_id"]]
        cands = sorted([c["key"], c["other"]])
        key = f"t1|{r['k']}"
        got = cache.get(JD.JUDGE_MODEL, key)
        if got is None:
            user = (f"QUESTION: {it['primary']['question']}\nCANDIDATES: {cands[0]} | {cands[1]}\n\nDESCRIPTION:\n{JD.clean_readout(r['text'])}")
            import time as _t
            for attempt in range(8):
                try:
                    got = JD.call_judge(SYSTEM, user, SCHEMA, JD.JUDGE_MODEL, usage)
                    break
                except RuntimeError as exc:
                    if "429" not in str(exc) or attempt == 7:
                        raise
                    _t.sleep(15 * (attempt + 1))
            cache.put(JD.JUDGE_MODEL, key, got)
        ans = str((got or {}).get("answer", "")).strip()
        return r["k"], ans, (got or {}).get("evidence")

    if not a.no_judge:
        with cf.ThreadPoolExecutor(a.workers) as ex:
            res = {k: (ans, ev) for k, ans, ev in ex.map(judge, todo)}
        (C / "judge_usage.json").write_text(json.dumps(usage.data, indent=1))
        for r in todo:
            ans, ev = res[r["k"]]
            c = ctxs[r["ctx"]]
            r["judge"], r["judge_evidence"] = ans, ev
            r["judge_hit"] = ans.lower() == c["key"].lower()
            r["judge_wrong"] = ans.lower() == c["other"].lower()
    # ---- per-state values
    per = defaultdict(lambda: defaultdict(list))  # (metric, reader, layer, fmt, pos) -> pair -> [state values]
    acc = defaultdict(list)
    for r in reads:
        if r["reader"] == "jlens" and r["layer"] not in (42, 44):
            continue
        c = ctxs[r["ctx"]]
        acc[(r["reader"], r["layer"], c["format"], r["pos"], c["item_id"])].append(r)
    for (rd, L, f, p, iid), rs in acc.items():
        pid = ctxs[f"{iid}|fmt_{f}"]["pair_id"]
        for m in ("rule_hit", "rule_wrong", "judge_hit", "judge_wrong"):
            vals = [r.get(m) for r in rs if r.get(m) is not None]
            per[(m, rd, L, f, p)][pid].append(float(np.mean(vals)) if vals else None)
    lo = {(r["reader"], r["layer"], r["ctx"], r["pos"]): r.get("lo") for r in los}
    for (rd, L, cx, p), v in list(lo.items()):
        pass
    lo_win = defaultdict(lambda: defaultdict(list))
    pairs = defaultdict(dict)
    for c in ctxs.values():
        pairs[(c["pair_id"], c["format"])][c["version"]] = c["ctx"]
    for (pid, f), vv in pairs.items():
        if "A" not in vv or "B" not in vv:
            continue
        for rd, L in CELLS:
            for p in POS:
                la, lb = lo.get((rd, L, vv["A"], p)), lo.get((rd, L, vv["B"], p))
                lo_win[(rd, L, f, p)][pid].append(None if la is None or lb is None else float((la + lb) > 0))
    # ---- tables
    S = {"rates": {}, "contrasts": {}, "lo": {}, "decision": {}}
    rows = []
    for rd, L in CELLS:
        for f in FORMATS:
            for p in POS:
                cell = {}
                for m in ("rule_hit", "rule_wrong", "judge_hit", "judge_wrong"):
                    d = per.get((m, rd, L, f, p))
                    if d:
                        cell[m] = boot_mean(d)
                        k = sum(r.get(m, False) for key, rs in acc.items() if key[:4] == (rd, L, f, p) for r in rs if r.get(m) is not None)
                        n = sum(1 for key, rs in acc.items() if key[:4] == (rd, L, f, p) for r in rs if r.get(m) is not None)
                        cell[m]["wilson"] = wilson(k, n)
                        cell[m]["k"], cell[m]["n"] = k, n
                lw = lo_win.get((rd, L, f, p))
                if lw:
                    vals = [x for v in lw.values() for x in v if x is not None]
                    cell["lo_win"] = {**boot_mean(lw), "wilson": wilson(int(sum(vals)), len(vals)), "k": int(sum(vals)), "n": len(vals)}
                S["rates"][f"{rd}@{L}|{f}|{p}"] = cell
                rows.append({"reader": rd, "layer": L, "format": f, "pos": p, **{f"{m}_{x}": cell.get(m, {}).get(x) for m in ("rule_hit", "judge_hit", "rule_wrong", "judge_wrong", "lo_win") for x in ("p", "lo", "hi")}})
            for f in ("b", "c"):
                for p in POS:
                    for m in ("rule_hit", "judge_hit", "lo_win"):
                        src = lo_win if m == "lo_win" else None
                        A_ = (lo_win.get((rd, L, "a", p)) if m == "lo_win" else per.get((m, rd, L, "a", p)))
                        B_ = (lo_win.get((rd, L, f, p)) if m == "lo_win" else per.get((m, rd, L, f, p)))
                        if A_ and B_:
                            d = boot_diff(A_, B_)
                            d["flag"] = bool(m != "lo_win" and p == "last" and d["d"] >= THRESH and d["lo"] > 0)
                            S["contrasts"][f"{rd}@{L}|{f}-a|{p}|{m}"] = d
    flags = [k for k, v in S["contrasts"].items() if v.get("flag")]
    S["decision"] = {"flags": flags, "triggered": bool(flags),
                     "text": ("TRIGGERED: the G1 free-text misses are largely a read-position artefact for " + ", ".join(flags)) if flags else
                             "NOT TRIGGERED: no primary contrast raises a reader's free-text hit rate by >= 20 points with the CI excluding 0"}
    # by family, primary position, judge hit
    fam_of = {c["item_id"]: c["family"] for c in ctxs.values()}
    S["by_family"] = {}
    for rd, L in CELLS:
        for f in FORMATS:
            for fam in ("language", "tense", "ownership", "mapping"):
                for m in ("rule_hit", "judge_hit"):
                    d = per.get((m, rd, L, f, "last"))
                    if not d:
                        continue
                    sub = {pid: v for pid, v in d.items() if fam_of.get(pid + "A", fam_of.get(pid + "B")) == fam}
                    if sub:
                        S["by_family"][f"{rd}@{L}|{f}|{fam}|{m}"] = boot_mean(sub)
                lw = lo_win.get((rd, L, f, "last"))
                if lw:
                    sub = {pid: v for pid, v in lw.items() if fam_of.get(pid + "A") == fam}
                    if sub:
                        S["by_family"][f"{rd}@{L}|{f}|{fam}|lo_win"] = boot_mean(sub)
    S["answers"] = {c["ctx"]: c.get("model_answer") for c in ctxs.values()}
    (OUT / "t1_summary.json").write_text(json.dumps(S, indent=1, default=float))
    with (OUT / "t1.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with (C / "readouts_scored.jsonl").open("w") as fh:
        for r in reads:
            if r["reader"] != "jlens" or r["layer"] in (42, 44):
                fh.write(json.dumps({k: v for k, v in r.items() if k not in ("tokens",)}, ensure_ascii=False) + "\n")
    pct = lambda c: "n/a" if not c or c.get("p") != c.get("p") else f"{100*c['p']:.0f}% [{100*c['lo']:.0f}, {100*c['hi']:.0f}]"  # noqa: E731
    dif = lambda d: "n/a" if not d else f"{100*d['d']:+.0f} [{100*d['lo']:+.0f}, {100*d['hi']:+.0f}]{' **flag**' if d.get('flag') else ''}"  # noqa: E731
    L_ = ["# F2-1 — prefill vs chat template (32 G1 test states, 16 pairs)", "",
          "Pre-registered in BRIEF_Z.md (2026-10-14). Formats: a = chat template (as G1); b = chat template + assistant prefill stem; "
          "c = plain text `<prompt> <stem>`. Stems never contain either candidate. Free-text hit = share of 4 samples asserting the key; "
          "wrong = asserting the other candidate (control: a reader echoing a default scores equally on both). Native LO win = within-pair win. "
          "CIs: pair bootstrap over 16 pairs (1,000, seed 0).", "",
          f"**Decision: {S['decision']['text']}.**", "", "## Primary cells (position last)", "",
          "| reader | format | rule-v1 hit | judge hit | judge wrong (control) | native LO win |", "|---|---|---|---|---|---|"]
    for rd, L in CELLS:
        for f in FORMATS:
            c = S["rates"][f"{rd}@{L}|{f}|last"]
            L_.append(f"| {rd}@{L} | {f}: {FMT_LABEL[f]} | {pct(c.get('rule_hit'))} | {pct(c.get('judge_hit'))} | {pct(c.get('judge_wrong'))} | {pct(c.get('lo_win'))} |")
    L_ += ["", "## Paired contrasts vs (a), position last (points)", "", "| reader | contrast | rule-v1 hit | judge hit | native LO win |", "|---|---|---|---|---|"]
    for rd, L in CELLS:
        for f in ("b", "c"):
            g = lambda m: S["contrasts"].get(f"{rd}@{L}|{f}-a|last|{m}")  # noqa: E731
            L_.append(f"| {rd}@{L} | ({f}) − (a) | {dif(g('rule_hit'))} | {dif(g('judge_hit'))} | {dif(g('lo_win'))} |")
    L_ += ["", "## Secondary positions (judge hit for Oracle/NLA, rule-v1 hit for J-lens)", "", "| reader | format | last | last-1 | last-2 |", "|---|---|---|---|---|"]
    for rd, L in CELLS:
        m = "rule_hit" if rd == "jlens" else "judge_hit"
        for f in FORMATS:
            L_.append(f"| {rd}@{L} | {f} | " + " | ".join(pct(S["rates"][f"{rd}@{L}|{f}|{p}"].get(m)) for p in POS) + " |")
    L_ += ["", "## By family (position last; judge hit for Oracle/NLA, rule-v1 for J-lens; 4 pairs per family)", "",
           "| reader | format | language | tense | ownership | mapping |", "|---|---|---|---|---|---|"]
    for rd, L in CELLS:
        m = "rule_hit" if rd == "jlens" else "judge_hit"
        for f in FORMATS:
            L_.append(f"| {rd}@{L} | {f} | " + " | ".join(pct(S["by_family"].get(f"{rd}@{L}|{f}|{fam}|{m}")) for fam in ("language", "tense", "ownership", "mapping")) + " |")
    u = json.loads((C / "judge_usage.json").read_text()) if (C / "judge_usage.json").exists() else {}
    L_ += ["", f"Judge: {JD.JUDGE_MODEL}, temperature 0; usage {json.dumps(u)}.", "",
           "Caveat: language and tense prompts state the key in the user text, so any format can be passed by copying the prompt (as in G1)."]
    (OUT / "t1.md").write_text("\n".join(L_) + "\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
        cols = {"a": "#888888", "b": "#2a5bd7", "c": "#d9822b"}
        for ax, (m, title) in zip(axes, (("free", "Free-text hit (judge for Oracle/NLA, rule-v1 for J-lens)"), ("lo_win", "Native log-odds within-pair win"))):
            for i, (rd, L) in enumerate(CELLS):
                for j, f in enumerate(FORMATS):
                    mm = m if m == "lo_win" else ("rule_hit" if rd == "jlens" else "judge_hit")
                    c = S["rates"][f"{rd}@{L}|{f}|last"].get(mm)
                    if not c or c["p"] != c["p"]:
                        continue
                    x = i + (j - 1) * 0.22
                    ax.errorbar(x, c["p"], yerr=[[c["p"] - c["lo"]], [c["hi"] - c["p"]]], fmt="o", color=cols[f], capsize=3, ms=5, label=FMT_LABEL[f] if i == 0 else None)
            ax.set_xticks(range(len(CELLS))); ax.set_xticklabels([f"{rd}@{L}" for rd, L in CELLS], fontsize=8)
            ax.set_ylim(0, 1.02); ax.set_title(title, fontsize=9); ax.axhline(0.5 if m == "lo_win" else 0, color="#bbbbbb", lw=0.8, ls=":")
        axes[0].set_ylabel("rate at position last (pair-bootstrap 95% CI)"); axes[0].legend(fontsize=8, loc="upper left")
        fig.suptitle("F2-1: does an answer-stem read position change what the readers report? (32 G1 states)", fontsize=10)
        fig.tight_layout(); fig.savefig(OUT / "fig_t1.png", dpi=150); plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        print(f"[t1] figure skipped: {exc}")
    print("\n".join(L_[:7]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
