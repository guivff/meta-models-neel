"""S8 analysis (Mac): full-candidate rescoring (S8a) and the three-way error test (S8b). BRIEF_S.md "S8".

    python -m projects.g_agreement.f2.s8_analyze [--root .] [--part a|b|all]
-> results/g_agreement/s8/{s8.md, s8.csv, s8_summary.json}
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from projects.g_agreement.core import config as C

READERS = ("jlens", "olens", "nla")
NAMES = {"jlens": "J-lens", "olens": "Oracle", "nla": "NLA"}
ARMS = ("natural", "full", "J_scaled", "perp_scaled", "random", "J_only")


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def jl(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def argmax(sc: dict) -> str | None:
    ok = {c: s for c, s in sc.items() if s is not None}
    return max(ok, key=ok.get) if ok else None


def pct(t) -> str:
    return "–" if t[0] != t[0] else f"{100 * t[0]:.0f}% [{100 * t[1]:.0f}, {100 * t[2]:.0f}]"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--part", choices=["a", "b", "all"], default="all")
    a = ap.parse_args()
    D, OUT = a.root / "cache/g_agreement/s8_fullcand", a.root / "results/g_agreement/s8/fullcand"
    OUT.mkdir(parents=True, exist_ok=True)
    sc = {}
    for r in jl(D / "scores.jsonl"):
        sc[(r["key"], r["reader"], r["layer"])] = r["scores"]
    beh = {r["key"]: r for r in jl(a.root / "cache/g_agreement/f2/t2/behaviour.jsonl")}
    rows, S = [], {"f2": {}, "x3": {}}
    # ---------------- S8a: F2-2
    groups = defaultdict(list)
    for key, b in beh.items():
        arm = "random" if b["arm"].startswith("rand_scaled") else b["arm"]
        groups[(arm, b["alpha"])].append(b)
    k_names = None
    for rd in READERS:
        for L in ((42, 44) if rd != "nla" else (42,)):
            for (arm, al), bs in sorted(groups.items(), key=lambda x: (ARMS.index(x[0][0]), x[0][1])):
                hits, n, hits2, n2, nk = 0, 0, 0, 0, []
                for b in bs:
                    s = sc.get((b["key"], rd, L))
                    if s is None:
                        continue
                    k_names = len(s)
                    own, pl = b["cand_A"], b["cand_B"]
                    if s.get(pl) is None or s.get(own) is None:
                        continue
                    nk.append(sum(v is not None for v in s.values()))
                    n += 1; hits += argmax(s) == pl
                    n2 += 1; hits2 += s[pl] > s[own]
                if not n:
                    continue
                flips = sum(b["flipped"] for b in bs)
                row = {"part": "a_f2", "reader": rd, "layer": L, "arm": arm, "alpha": al, "n": n, "k": max(nk) if nk else None,
                       "k_scorable_min": min(nk) if nk else None, "pick_planted": hits, "kway": wilson(hits, n), "twoway": wilson(hits2, n2),
                       "model_flips": f"{flips}/{len(bs)}"}
                rows.append(row)
                S["f2"][f"{rd}|{L}|{arm}|{al}"] = row
    verdict_f2 = {}
    for rd in READERS:
        for L in ((42, 44) if rd != "nla" else (42,)):
            j, r_ = S["f2"].get(f"{rd}|{L}|J_scaled|1.0"), S["f2"].get(f"{rd}|{L}|random|1.0")
            if j and r_:
                k = j["k"] or 29
                verdict_f2[f"{rd}|{L}"] = bool(j["kway"][0] >= 2 / k and j["kway"][1] > r_["kway"][0])
    survives_f2 = all(verdict_f2.get(f"{rd}|42", False) for rd in READERS)
    # ---------------- S8a: X3 shared misses (+ S8b)
    items = {it["item_id"]: it for it in C.load_items("all", 0, path=C.DATASET_DIR / "items_x3_selected.json") if it.get("set") == "error"}
    picks = {}
    for iid in items:
        p = {rd: argmax(sc.get((iid, rd, 42)) or {}) for rd in READERS}
        if all(p.values()):
            picks[iid] = p

    def role(it, c):
        key, cor, tr = it["primary"]["answer"], it["source"]["correct"], it["source"]["trace"]
        return "key" if c == key else "correct" if c == cor else "start" if c == tr[0] else "trace" if c in tr else "off"

    rc = {rd: Counter(role(items[i], p[rd]) for i, p in picks.items()) for rd in READERS}
    n3 = len(picks)
    obs = sum(1 for i, p in picks.items() if len(set(p.values())) == 1 and p["jlens"] != items[i]["primary"]["answer"])
    exp = 0.0
    for i in picks:
        it = items[i]
        roles = {c: role(it, c) for c in "ABCDEFGH"}
        nrole = Counter(roles.values())
        exp += sum(
            (lambda c: __import__("math").prod(rc[rd][roles[c]] / n3 / nrole[roles[c]] for rd in READERS))(c)
            for c in "ABCDEFGH" if roles[c] != "key")
    exp /= max(1, n3)
    ow = wilson(obs, n3)
    # two-way reference from the same scores: all three favour the correct (non-key) answer over the model's answer
    two = [all((sc[(i, rd, 42)][items[i]["source"]["correct"]] or -1e9) > (sc[(i, rd, 42)][items[i]["primary"]["answer"]] or -1e9) for rd in READERS) for i in picks]
    p2 = {rd: sum((sc[(i, rd, 42)][items[i]["source"]["correct"]] or -1e9) > (sc[(i, rd, 42)][items[i]["primary"]["answer"]] or -1e9) for i in picks) / max(1, n3) for rd in READERS}
    exp2 = __import__("math").prod(p2.values())
    S["x3"] = {"n": n3, "kway_pick_key": {rd: wilson(rc[rd]["key"], n3) for rd in READERS},
               "kway_roles": {rd: dict(rc[rd]) for rd in READERS},
               "all_same_miss": {"observed": ow, "expected_independent": exp, "survives": bool(ow[1] > exp)},
               "twoway_all_same_miss": {"observed": wilson(sum(two), len(two)), "expected_independent": exp2}}
    for rd in READERS:
        rows.append({"part": "a_x3", "reader": rd, "layer": 42, "arm": "ERROR", "alpha": None, "n": n3, "k": 8, "pick_planted": rc[rd]["key"],
                     "kway": wilson(rc[rd]["key"], n3), "twoway": wilson(sum((sc[(i, rd, 42)][items[i]["primary"]["answer"]] or -1e9) > (sc[(i, rd, 42)][items[i]["source"]["correct"]] or -1e9) for i in picks), n3),
                     "model_flips": None})
    # S8b
    tw = {}
    for rd in READERS:
        cnt, n = Counter(), 0
        for i in picks:
            it = items[i]
            key, cor = it["primary"]["answer"], it["source"]["correct"]
            dis = next((c for c in it["source"]["distractors"] if c not in (key, cor)), None)
            if dis is None:
                continue
            s = sc[(i, rd, 42)]
            three = {"model_answer": s.get(key), "correct": s.get(cor), "distractor": s.get(dis)}
            if any(v is None for v in three.values()):
                continue
            cnt[max(three, key=three.get)] += 1; n += 1
        shares = {c: wilson(cnt[c], n) for c in ("model_answer", "correct", "distractor")}
        above = lambda x: all(shares[x][1] > shares[y][2] for y in shares if y != x)  # noqa: E731
        tw[rd] = {"n": n, "shares": shares, "verdict": "tracks the task" if above("correct") else "tracks the model" if above("model_answer") else "mixed"}
        rows.append({"part": "b_x3", "reader": rd, "layer": 42, "arm": "3-way", "alpha": None, "n": n, "k": 3,
                     "share_model": shares["model_answer"], "share_correct": shares["correct"], "share_distractor": shares["distractor"], "verdict": tw[rd]["verdict"]})
    S["s8b"] = tw
    S["verdict_f2"] = verdict_f2
    S["survives_f2"] = survives_f2
    (OUT / "s8_summary.json").write_text(json.dumps(S, indent=1, default=str))
    with (OUT / "s8.csv").open("w", newline="") as fh:
        keys = list(dict.fromkeys(k for r in rows for k in r))
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps([round(x, 4) for x in v]) if isinstance(v, tuple) else v) for k, v in r.items()})
    L = ["# S8 — full-candidate rescoring (S8a) and the three-way error test (S8b)", "",
         "Pre-registered in BRIEF_S.md \"S8\" (2026-10-16 11:35 CEST). Same cached read vectors as F2-2 / X3; native scores over every candidate "
         f"(ownership: {k_names} names, chance {100 / (k_names or 29):.1f}%; puzzles: A–H, chance 12.5%). Wilson 95%.", "",
         "## S8a verdict", "",
         f"- Under-weighting (F2-2, J_scaled at α 1, block 42): **{'SURVIVES' if survives_f2 else 'DOES NOT SURVIVE'}** — "
         + "; ".join(f"{NAMES[rd]} {'yes' if verdict_f2.get(f'{rd}|42') else 'no'}" for rd in READERS)
         + " (block 44: " + "; ".join(f"{NAMES[rd]} {'yes' if verdict_f2.get(f'{rd}|44') else 'no'}" for rd in ("jlens", "olens")) + ").",
         f"- Shared misses (X3 ERROR, n {n3}): all three pick the same non-key candidate in {pct(ow)} vs {100 * exp:.1f}% under independence → "
         f"**{'SURVIVES' if ow[1] > exp else 'DOES NOT SURVIVE'}** (two-way reference from the same scores: {pct(S['x3']['twoway_all_same_miss']['observed'])} vs {100 * exp2:.1f}%).", "",
         "## F2-2 split edit: reader picks the planted name", "",
         "| reader | block | arm | α | model flips (F2-2) | k-way pick planted | two-way (same scores) |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["part"] == "a_f2":
            L.append(f"| {NAMES[r['reader']]} | {r['layer']} | {r['arm']} | {r['alpha']} | {r['model_flips']} | {r['pick_planted']}/{r['n']} = {pct(r['kway'])} | {pct(r['twoway'])} |")
    L += ["", "## X3 ERROR puzzles (key = the model's wrong answer)", "", "| reader | k-way picks the model's answer | picks the correct answer | other | two-way favours the model's answer |", "|---|---|---|---|---|"]
    for rd in READERS:
        c = rc[rd]
        r = next(x for x in rows if x["part"] == "a_x3" and x["reader"] == rd)
        L.append(f"| {NAMES[rd]} | {pct(wilson(c['key'], n3))} | {pct(wilson(c['correct'], n3))} | {pct(wilson(n3 - c['key'] - c['correct'], n3))} | {pct(r['twoway'])} |")
    if a.part in ("b", "all"):
        L += ["", "## S8b three-way {model's answer, correct, distractor}", "", "| reader | n | model's answer | correct | distractor | verdict |", "|---|---|---|---|---|---|"]
        for rd in READERS:
            t = tw[rd]
            L.append(f"| {NAMES[rd]} | {t['n']} | {pct(t['shares']['model_answer'])} | {pct(t['shares']['correct'])} | {pct(t['shares']['distractor'])} | {t['verdict']} |")
    (OUT / "s8.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:9]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
