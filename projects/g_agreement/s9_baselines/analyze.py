"""S9 analysis (Mac, CPU): prompt-only and black-box baselines on the 297 X3 ERROR items, and reader picks of m beyond
prompt-only (BRIEF_S.md "S9", deviation 2). Reader picks come from S8's per-item records (cache/g_agreement/s8x:
three-way native {m, c, d} with S8's off-chain d; free-text labels via S8's ft_label) and, descriptively, S8's 8-way X3
scores (cache/g_agreement/s8_fullcand).

    python -m projects.g_agreement.s9_baselines.analyze [--cache <repo>/cache]
-> results/g_agreement/s9/{s9.md, s9.csv}
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from common.stats import wilson

REPO = Path(__file__).resolve().parents[3]
NAMES = {"jlens": "J-lens", "olens": "Oracle", "nla": "NLA", "probe": "probe (ref.)"}
READERS = ("jlens", "olens", "nla", "probe")


def jl(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def argmax(sc: dict):
    ok = {c: s for c, s in sc.items() if s is not None}
    return max(ok, key=ok.get) if ok else None


def pct(t) -> str:
    return f"{100 * t[0]:.1f}% [{100 * t[1]:.1f}, {100 * t[2]:.1f}]"


def paired_boot(a: np.ndarray, b: np.ndarray, n_boot: int = 10_000, seed: int = 0):
    rng = np.random.default_rng(seed)
    d = a.astype(float) - b.astype(float)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    bs = d[idx].mean(1)
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=REPO / "cache")
    a = ap.parse_args()
    OUT = REPO / "results/g_agreement/s9"
    OUT.mkdir(parents=True, exist_ok=True)
    items = {it["item_id"]: it for it in json.loads((REPO / "projects/g_agreement/dataset/items_x3_selected.json").read_text())["items"]
             if it["set"] == "error"}
    po = {r["item_id"]: r for r in jl(a.cache / "g_agreement/s9/prompt_only.jsonl")}
    po64 = {r["item_id"]: r for r in jl(a.cache / "g_agreement/s9/prompt_only_max64.jsonl")}
    tgt = {r["item_id"]: r for r in jl(a.cache / "g_agreement/x/x3_target.jsonl") if r.get("family") == "puzzle"}
    for i, it in items.items():
        assert it["primary"]["answer"] == tgt[i]["parsed"] == po[i]["m"] and it["source"]["correct"] == po[i]["c"]
    rows, L = [], []

    # (a) prompt-only
    def shares(d, tag, note):
        ok = [r for r in d.values() if not r.get("error")]
        n = len(ok)
        for cls in ("m", "c", "other"):
            k = sum(r["class"] == cls for r in ok)
            p, lo, hi = wilson(k, n)
            rows.append({"part": "a_prompt_only", "arm": tag, "reader": "gemini-3.8-flash", "layer": "", "set": "8-way free answer",
                         "stat": f"P({cls})", "n": n, "k": k, "value": p, "ci_lo": lo, "ci_hi": hi, "note": note})
        return n, {cls: wilson(sum(r["class"] == cls for r in ok), n) for cls in ("m", "c", "other")}, sum(r["parsed"] is None for r in ok)

    n_po, sh, unp = shares(po, "max_tokens_2000 (primary, deviation 1)", "")
    n64, sh64, unp64 = shares(po64, "max_tokens_64 (as pre-registered)", "empty outputs = reasoning hit the cap")
    L += ["# S9. Baselines for the error benchmark (X3 ERROR, n 297)", "",
          "**Summary.** (a) Prompt-only Gemini 3.8 Flash answers c on 297/297 and m on 0/297. (b) The greedy output is m "
          "by definition; a thinking-on self-report was not cached, so it is not run. (c) Every reader × layer three-way pick "
          "clears 'beyond prompt-only' trivially, because the prompt-only baseline never picks m; relative to chance (1/3), "
          "readers pick m only at blocks 52–56 (J-lens 74–76%, Oracle 82–86%; probe 91–93%), and are at chance at 42–48.", "",
          "Pre-registration: `projects/g_agreement/BRIEF_S.md` § S9 (one deviation, logged there). m = the target's greedy "
          "(wrong) answer, c = the correct symbol. Code: `projects/g_agreement/s9_baselines/`.", "",
          "## (a) Prompt-only baseline — google/gemini-3.8-flash, temperature 0, reasoning effort minimal, prompt only", "",
          "| run | n | P(m) | P(c) | P(other) | unparseable |", "|---|---|---|---|---|---|",
          f"| max_tokens 2000 (primary) | {n_po} | {pct(sh['m'])} | {pct(sh['c'])} | {pct(sh['other'])} | {unp} |",
          f"| max_tokens 64 (pre-registered cap) | {n64} | {pct(sh64['m'])} | {pct(sh64['c'])} | {pct(sh64['other'])} | {unp64} |", "",
          "At the 64-token cap, 70/297 responses were empty (the minimal-effort reasoning consumed the budget); the 227 non-empty "
          "answers were 215 c, 9 other, 3 m. Raising the cap (deviation 1) gives a parseable answer on all items.", ""]

    # (b) black-box
    n_t = len(items)
    k_m = sum(tgt[i]["parsed"] == items[i]["primary"]["answer"] for i in items)
    p, lo, hi = wilson(k_m, n_t)
    rows.append({"part": "b_black_box", "arm": "greedy output", "reader": "target", "layer": "", "set": "8-way", "stat": "P(m)",
                 "n": n_t, "k": k_m, "value": p, "ci_lo": lo, "ci_hi": hi, "note": "m by definition"})
    rows.append({"part": "b_black_box", "arm": "self-report, thinking on", "reader": "target", "layer": "", "set": "", "stat": "P(m)",
                 "n": 0, "k": "", "value": "", "ci_lo": "", "ci_hi": "", "note": "not run: no cached X3 output (self-guess exists for CHOICE items only)"})
    L += ["## (b) Black-box baseline", "",
          f"- Target greedy output: P(m) = {k_m}/{n_t} = 100% by definition (the ceiling for anything that reads the output).",
          "- Target self-report (\"what would you answer?\", thinking on): **not run**: X3 cached a prompt-only self-guess for "
          "CHOICE items only; no puzzle item has one.", ""]

    # (c) readers beyond prompt-only (BRIEF_S S9 deviation 2: follow the amended S8b as run)
    s8csv = REPO / "results/g_agreement/s8/s8.csv"
    D8 = a.cache / "g_agreement/s8x"
    L += ["## (c) Reader picks of m beyond prompt-only", ""]
    if not s8csv.exists() or not (D8 / "cpu.jsonl").exists():
        L += ["**Pending**: `results/g_agreement/s8/s8.csv` / S8 per-item records not yet available.", ""]
    else:
        from projects.g_agreement.s8.s8_analyze import ft_label
        rl = sorted({(r["reader"], int(r["layer"])) for r in csv.DictReader(s8csv.open()) if r["part"] == "s8b"},
                    key=lambda t: (READERS.index(t[0]), t[1]))
        cpu, nat, fts = jl(D8 / "cpu.jsonl"), jl(D8 / "native.jsonl"), jl(D8 / "freetext.jsonl")
        native_pick, ft_lab = {}, {}
        for r in cpu + nat:
            if r.get("part") != "s8b":
                continue
            assert r["m"] == items[r["item_id"]]["primary"]["answer"] and r["c"] == items[r["item_id"]]["source"]["correct"]
            sc = r["score"] if "score" in r else {x: r["lp"][r[x]] for x in "mcd"}
            native_pick[(r["reader"], r["layer"], r["item_id"])] = None if any(sc[x] is None for x in "mcd") else max("mcd", key=lambda x: sc[x])
        for r in [x for x in cpu if x.get("part") == "s8b_ft"] + fts:
            ft_lab[(r["reader"], r["layer"], r["item_id"])] = ft_label(r)
        full = {(r["key"], r["reader"], r["layer"]): r["scores"] for r in jl(a.cache / "g_agreement/s8_fullcand/scores.jsonl")
                if r.get("source") == "x3"}
        po_m = {i: po[i]["class"] == "m" for i in items if not po[i].get("error")}
        L += ["Δ = P(reader picks m) − P(prompt-only picks m), paired over items; 95% paired bootstrap (10,000, seed 0). "
              "Beyond prompt-only iff the CI lower bound > 0. Readers and layers = the S8b rows of `s8.csv`; d = S8's off-chain "
              "distractor; free-text labels = S8's `ft_label` (rule-v1 primitives); the probe is S8's reference, not a reader.", "",
              "| reader | layer | mode | n | P(reader = m) | P(prompt-only = m) | Δ [95% CI] | verdict |",
              "|---|---|---|---|---|---|---|---|"]
        modes = [("three-way native (primary)", lambda rd, ly, i: native_pick.get((rd, ly, i), "missing")),
                 ("free text, 1 sample (secondary)", lambda rd, ly, i: ft_lab.get((rd, ly, i), "missing")),
                 ("8-way A–H native (descriptive)", lambda rd, ly, i: (lambda s: "missing" if s is None else
                     (None if s.get(items[i]["primary"]["answer"]) is None else ("m" if argmax(s) == items[i]["primary"]["answer"] else "x")))
                     (full.get((i, rd, ly))))]
        for rd, ly in rl:
            for mode, get in modes:
                rm, pm = [], []
                for i in items:
                    v = get(rd, ly, i)
                    if v == "missing" or v is None or i not in po_m:
                        continue
                    rm.append(v == "m"); pm.append(po_m[i])
                if not rm:
                    continue
                rm, pm = np.array(rm), np.array(pm)
                d, dlo, dhi = paired_boot(rm, pm)
                verdict = "beyond prompt-only" if dlo > 0 else "below prompt-only" if dhi < 0 else "not distinguishable"
                rw, pw = wilson(int(rm.sum()), len(rm)), wilson(int(pm.sum()), len(pm))
                rows.append({"part": "c_beyond_prompt_only", "arm": mode, "reader": NAMES.get(rd, rd), "layer": ly, "set": "X3 ERROR",
                             "stat": "delta P(m)", "n": len(rm), "k": int(rm.sum()), "value": d, "ci_lo": dlo, "ci_hi": dhi,
                             "note": f"P_reader(m)={rw[0]:.4f} P_prompt_only(m)={pw[0]:.4f}; {verdict}"})
                L.append(f"| {NAMES.get(rd, rd)} | {ly} | {mode} | {len(rm)} | {pct(rw)} | {pct(pw)} | "
                         f"{100 * d:+.1f} pp [{100 * dlo:+.1f}, {100 * dhi:+.1f}] | {verdict} |")
        L += ["", "**Reading this table.** The prompt-only model never picks m (0/297), so Δ equals the reader's own P(m) and the "
              "pre-registered bar (CI lower bound > 0) is passed by any reader that ever picks m; it does not separate reading the "
              "model from chance. The informative comparison is against chance on the same candidate set (1/3 three-way, 1/8 "
              "eight-way; S8's verdicts): at blocks 42 and 48 every reader's three-way P(m) CI contains 1/3, i.e. the readers pick m "
              "no more often than chance even though the prompt alone never points to m; at blocks 52 and 56 J-lens and Oracle pick "
              "m on 74–86% of items, all of it beyond what the prompt supports. Free text at 42 is almost always 'none' "
              "(J-lens, NLA 0% m).", ""]
    with (OUT / "s9.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})
    (OUT / "s9.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
