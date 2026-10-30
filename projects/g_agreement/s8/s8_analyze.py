"""S8 analysis (CPU): combine cpu.jsonl (J-lens, probe) with the pod's native.jsonl / freetext.jsonl (Oracle, NLA).

S8b: share of the 297 X3 ERROR items whose argmax over {m, c, d} is each candidate, Wilson 95%, chance 1/3, per reader x block;
     free text scored with rule-v1 primitives into m / c / d / none / multiple; verdict per BRIEF_S S8 amendment.
S8a: pick = argmax over the 29 F2-2 names; follow = pick == planted; two-candidate = score(planted) > score(own); rule at alpha 1, block 42.
Writes results/g_agreement/s8/{s8.csv, s8b_table.md, s8a_table.md, s8_summary.json}.

    .venv/bin/python projects/g_agreement/s8/s8_analyze.py --data-root /path/to/mats-minis [--parts s8b,s8a]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
from common.stats import wilson  # noqa: E402
from projects.g_agreement.core.scoring import _answer_patterns, _token_matches  # noqa: E402
from projects.g_agreement.s8 import s8_common as S  # noqa: E402

READERS_B = ("jlens", "olens", "nla", "probe")
LABEL = {"jlens": "J-lens", "olens": "Oracle", "nla": "NLA", "probe": "probe (ref.)"}
ROLES = ("m", "c", "d")


def W(k, n):
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "p": p, "lo": lo, "hi": hi}


def load(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def ft_label(row):
    if row["reader"] == "jlens":
        toks = row["tokens"]
        hit = {r: any(_token_matches(t, [row[r]], [row[o] for o in ROLES if o != r], t) for t in toks) for r in ROLES}
    else:
        hit = {r: bool(_answer_patterns(row["text"] or "", row[r])) for r in ROLES}
    h = [r for r in ROLES if hit[r]]
    return h[0] if len(h) == 1 else ("none" if not h else "multiple")


def above(a, b):
    return a["lo"] > b["hi"]


def s8b(cpu, native, ft):
    picks = defaultdict(list)
    for r in cpu + native:
        if r.get("part") != "s8b":
            continue
        sc = r["score"] if "score" in r else {x: r["lp"][r[x]] for x in ROLES}
        if any(sc[x] is None for x in ROLES):
            picks[(r["reader"], r["layer"])].append(None)
            continue
        picks[(r["reader"], r["layer"])].append(max(ROLES, key=lambda x: sc[x]))
    fts = defaultdict(list)
    for r in [x for x in cpu if x.get("part") == "s8b_ft"] + ft:
        fts[(r["reader"], r["layer"])].append(ft_label(r))
    out = []
    for (rd, L), ps in sorted(picks.items(), key=lambda kv: (READERS_B.index(kv[0][0]), kv[0][1])):
        ok = [p for p in ps if p is not None]
        sh = {x: W(sum(p == x for p in ok), len(ok)) for x in ROLES}
        f = fts.get((rd, L))
        fsh = {x: W(sum(v == x for v in f), len(f)) for x in ROLES + ("none", "multiple")} if f else None
        mostly_none = bool(f) and (fsh["none"]["k"] + fsh["multiple"]["k"]) / len(f) > 0.5
        if above(sh["m"], sh["c"]) and above(sh["m"], sh["d"]):
            v = "tracks the model"
        elif above(sh["c"], sh["m"]) and above(sh["c"], sh["d"]):
            v = "tracks the prompt"
        else:
            v = "neither"
        if mostly_none and v != "neither":
            v = "neither (free text mostly none)"
        out.append({"reader": rd, "layer": L, "n_dropped": len(ps) - len(ok), "native": sh, "freetext": fsh, "mostly_none": mostly_none, "verdict": v})
    return out


def s8a(cpu, native, beh, names):
    by = defaultdict(list)
    for r in cpu + native:
        if r.get("part") != "s8a":
            continue
        sc = r["score"] if "score" in r else r["lp"]
        ok = {n: v for n, v in sc.items() if v is not None}
        if r["planted"] not in ok or r["own"] not in ok:
            by[(r["reader"], r["layer"], "random" if r["arm"].startswith("rand") else r["arm"], r["alpha"])].append(None)
            continue
        pick = max(ok, key=ok.get)
        by[(r["reader"], r["layer"], "random" if r["arm"].startswith("rand") else r["arm"], r["alpha"])].append(
            (pick == r["planted"], ok[r["planted"]] > ok[r["own"]], pick == r["own"]))
    flips = defaultdict(list)
    for b in beh:
        if b["arm"] in S.S8A_ARMS:
            flips[("random" if b["arm"].startswith("rand") else b["arm"], b["alpha"])].append(bool(b["flipped"]))
    rows = []
    for (rd, L, arm, al), v in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], kv[0][3])):
        ok = [x for x in v if x is not None]
        n = len(ok)
        fl = flips[(arm, al)]
        rows.append({"reader": rd, "layer": L, "arm": arm, "alpha": al, "n": n, "n_dropped": len(v) - n,
                     "follow_k": W(sum(x[0] for x in ok), n), "follow_2": W(sum(x[1] for x in ok), n), "pick_own": W(sum(x[2] for x in ok), n),
                     "model_flip": W(sum(fl), len(fl))})
    k = len(names)
    verdict = {}
    for rd in ("jlens", "olens", "nla"):
        j = next((r for r in rows if (r["reader"], r["layer"], r["arm"], r["alpha"]) == (rd, 42, "J_scaled", 1.0)), None)
        rnd = next((r for r in rows if (r["reader"], r["layer"], r["arm"], r["alpha"]) == (rd, 42, "random", 1.0)), None)
        if j and rnd:
            c1 = j["follow_k"]["p"] >= 2 / k
            c2 = j["follow_k"]["lo"] > rnd["follow_k"]["p"]
            verdict[rd] = {"J_scaled": j["follow_k"], "random": rnd["follow_k"], "ge_2x_chance": c1, "lo_above_random": c2, "survives": c1 and c2}
    if len(verdict) == 3:
        verdict["headline_survives"] = all(verdict[r]["survives"] for r in ("jlens", "olens", "nla"))
    return rows, verdict, k


def pct(d):
    return f"{100 * d['p']:.0f} [{100 * d['lo']:.0f}, {100 * d['hi']:.0f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, default=HERE)
    ap.add_argument("--native", type=Path, default=None)
    ap.add_argument("--freetext", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=HERE / "results/g_agreement/s8")
    a = ap.parse_args()
    D = a.data_root / "cache/g_agreement/s8x"
    cpu = load(D / "cpu.jsonl")
    native = load(a.native or D / "native.jsonl")
    ft = load(a.freetext or D / "freetext.jsonl")
    names = json.loads((D / "cpu_meta.json").read_text())["names"]
    beh = load(a.data_root / "cache/g_agreement/f2/t2/behaviour.jsonl")
    a.out.mkdir(parents=True, exist_ok=True)
    B = s8b(cpu, native, ft)
    A, AV, k = s8a(cpu, native, beh, names)
    # CSV
    with open(a.out / "s8.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["part", "reader", "layer", "arm", "alpha", "mode", "label", "k", "n", "share", "lo", "hi", "chance", "verdict"])
        for r in B:
            for x in ROLES:
                d = r["native"][x]
                w.writerow(["s8b", r["reader"], r["layer"], "", "", "native", x, d["k"], d["n"], d["p"], d["lo"], d["hi"], 1 / 3, r["verdict"]])
            if r["freetext"]:
                for x, d in r["freetext"].items():
                    w.writerow(["s8b", r["reader"], r["layer"], "", "", "freetext", x, d["k"], d["n"], d["p"], d["lo"], d["hi"], "", r["verdict"]])
        for r in A:
            for lab, key, ch in (("follow_k", "follow_k", 1 / k), ("follow_2cand", "follow_2", 0.5), ("pick_own_k", "pick_own", 1 / k), ("model_flip", "model_flip", "")):
                d = r[key]
                w.writerow(["s8a", r["reader"], r["layer"], r["arm"], r["alpha"], "native" if lab != "model_flip" else "model", lab, d["k"], d["n"], d["p"], d["lo"], d["hi"], ch,
                            AV.get(r["reader"], {}).get("survives", "") if (r["layer"], r["arm"], r["alpha"]) == (42, "J_scaled", 1.0) else ""])
    # tables
    L = ["| reader | block | n | m: model's answer | c: correct | d: distractor | free text m / c / d / none / multiple | verdict |", "|---|---|---|---|---|---|---|---|"]
    for r in B:
        ftx = " / ".join(f"{100 * r['freetext'][x]['p']:.0f}" for x in ROLES + ("none", "multiple")) if r["freetext"] else "—"
        L.append(f"| {LABEL[r['reader']]} | {r['layer']} | {r['native']['m']['n']} | {pct(r['native']['m'])} | {pct(r['native']['c'])} | {pct(r['native']['d'])} | {ftx} | **{r['verdict']}** |")
    (a.out / "s8b_table.md").write_text("\n".join(L) + "\n")
    L = [f"k = {k} names, chance {100 / k:.1f}% (2x chance {200 / k:.1f}%). Pick rate = argmax over the k names is the planted name; 2-cand = score(planted) > score(own).", "",
         "| reader | block | arm | α | n | pick planted (k) | 2-cand | pick own (k) | model flip |", "|---|---|---|---|---|---|---|---|---|"]
    for r in A:
        L.append(f"| {LABEL.get(r['reader'], r['reader'])} | {r['layer']} | {r['arm']} | {r['alpha']} | {r['n']} | {pct(r['follow_k'])} | {pct(r['follow_2'])} | {pct(r['pick_own'])} | {pct(r['model_flip'])} |")
    (a.out / "s8a_table.md").write_text("\n".join(L) + "\n")
    (a.out / "s8_summary.json").write_text(json.dumps({"s8b": B, "s8a_verdict": AV, "k": k, "names": names}, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print((a.out / "s8b_table.md").read_text())
    print(json.dumps(AV, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
