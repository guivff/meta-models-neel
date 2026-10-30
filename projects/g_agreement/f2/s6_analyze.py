"""S6 step-zero analysis (Mac): per reader x layer x family, native two-candidate win rate and rule-v1 free text.

    python -m projects.g_agreement.f2.s6_analyze [--root .]
-> results/g_agreement/s6/{step0.md, step0.csv}
Win = lo > 0 (key preferred) per state, Wilson 95% over the family's 8 states; within-pair win (lo_A + lo_B > 0) reported.
A reader "reads the key" iff the Wilson lower bound > 0.5 on >= 3 of 4 families at block 24 (BRIEF_S "S6 step zero").
GO iff >= 2 of the 3 readers read the key at block 24.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from projects.g_agreement.core import config as C
from projects.g_agreement.core import scoring as SC

FAMS = ("language", "tense", "ownership", "mapping")
READERS = ("jlens", "olens", "nla")
NAMES = {"jlens": "J-lens", "olens": "Oracle", "nla": "NLA (anicka universal AV)"}


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def jl(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--tag", default="s6", help="s6 (step zero) or s6b")
    a = ap.parse_args()
    D, OUT = a.root / f"cache/g_agreement/{a.tag}", a.root / "results/g_agreement/s6"
    OUT.mkdir(parents=True, exist_ok=True)
    ipath = Path(__file__).with_name("s6b_items.json") if a.tag == "s6b" else None
    items = {it["item_id"]: it for it in C.load_items("test", 0, path=ipath)}
    lo = jl(D / "lo.jsonl")
    gens = jl(D / "gens.jsonl")
    tg = {r["item_id"]: r for r in jl(D / "targets.jsonl")}
    tacc = Counter()
    for i, r in tg.items():
        v, _ = SC.extract_target_answer(r["answer_text"], items[i])
        tacc[(items[i]["family"], v == items[i]["primary"]["answer"])] += 1
    ft = defaultdict(Counter)
    for g in gens:
        it = items[g["item_id"]]
        text = (g["native"].get("tokens_decoded") or g["native"].get("tokens")) if g["method"] == "jlens" else (g["native"].get("samples") or [""])[0]
        st = SC.extract_claims(text, it, g["method"], g.get("finish_reason"))["primary"]["status"]
        ft[(g["reader"], g["layer"], it["family"])][st] += 1
    rows, verdict = [], {}
    combos = sorted({(r["reader"], r["layer"]) for r in lo}, key=lambda x: (READERS.index(x[0]), x[1]))
    for rd, L in combos:
        ok = 0
        for f in FAMS:
            rs = [r for r in lo if r["reader"] == rd and r["layer"] == L and r["family"] == f and r["lo"] is not None]
            k = sum(r["lo"] > 0 for r in rs)
            p, wl, wh = wilson(k, len(rs))
            byp = defaultdict(dict)
            for r in rs:
                byp[items[r["item_id"]]["pair_id"]][items[r["item_id"]]["version"]] = r["lo"]
            pw = [v["A"] + v["B"] > 0 for v in byp.values() if "A" in v and "B" in v]
            c = ft.get((rd, L, f), Counter())
            reads = bool(len(rs) and wl > 0.5)
            ok += reads
            rows.append({"reader": rd, "layer": L, "family": f, "n": len(rs), "wins": k, "win": p, "win_lo": wl, "win_hi": wh,
                         "pair_wins": sum(pw), "n_pairs": len(pw), "reads_family": reads,
                         "ft_supports": c.get("supports", 0), "ft_contradicts": c.get("contradicts", 0), "ft_other": sum(c.values()) - c.get("supports", 0) - c.get("contradicts", 0),
                         "unscorable": sum(1 for r in lo if r["reader"] == rd and r["layer"] == L and r["family"] == f and r["lo"] is None)})
        verdict[(rd, L)] = ok
    with (OUT / ("step0.csv" if a.tag == "s6" else "s6b.csv")).open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    at24 = {rd: verdict.get((rd, 24), 0) >= 3 for rd in READERS}
    go = (at24["jlens"] and at24["olens"]) if a.tag == "s6b" else sum(at24.values()) >= 2  # S6b: J-lens and Oracle only
    pct = lambda r: f"{r['wins']}/{r['n']} = {100 * r['win']:.0f}% [{100 * r['win_lo']:.0f}, {100 * r['win_hi']:.0f}]"  # noqa: E731
    Ls = [("# S6 step zero — do third-party Qwen3-4B readers read the G1 keys?" if a.tag == "s6" else "# S6b — Qwen3-4B step zero on the single-token bank (GO iff J-lens AND Oracle read the key; NLA substitute exploratory)"), "",
          ("Pre-registered in BRIEF_S.md \"S6 step zero\" (2026-10-16)." if a.tag == "s6" else "Pre-registered in BRIEF_S.md \"S6b\" (2026-10-16 12:50 CEST); bank `f2/s6b_items.json` (5 name/word swaps).") + " Target `Qwen/Qwen3-4B`, the 32 G1 test states (8 per family), last token. "
          "Readers: J-lens (`neuronpedia/jacobian-lens` qwen3-4b), Oracle LoRA (`qwen3-4b/oracle`, marker ㈎ forced), NLA = declared substitute "
          "`anicka/nla-qwen3-4b-universal-av` (the named `minnesotanlp/nla-qwen3-4b-L24-av` is gated: 403 with our token). "
          "Win = native lo(key) − lo(other) > 0 per state, Wilson 95%; a reader reads the key iff the lower bound > 50% (≥ 7/8) on ≥ 3 of 4 families.", "",
          f"**{'GO' if go else 'NO-GO'}** for the F2-2 + X6 replication on Qwen3-4B: readers reading the key at block 24: "
          + ", ".join(f"{NAMES[r]} {'yes' if at24[r] else 'no'} ({verdict.get((r, 24), 0)}/4 families)" for r in READERS) + ".", "",
          "Target accuracy (greedy, rule-v1 parse): " + ", ".join(f"{f} {tacc[(f, True)]}/{tacc[(f, True)] + tacc[(f, False)]}" for f in FAMS), "",
          "## Native two-candidate win rate (per state) and free text (rule-v1)", "",
          "| reader | block | family | win rate [Wilson 95%] | within-pair wins | reads key | free text: supports / contradicts / no claim |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        Ls.append(f"| {NAMES[r['reader']]} | {r['layer']} | {r['family']} | {pct(r)} | {r['pair_wins']}/{r['n_pairs']} | {'yes' if r['reads_family'] else 'no'} | "
                  f"{r['ft_supports']} / {r['ft_contradicts']} / {r['ft_other']} |")
    Ls += ["", "| reader | block | families read (of 4) | reads the key |", "|---|---|---|---|"]
    for (rd, L), k in verdict.items():
        Ls.append(f"| {NAMES[rd]} | {L} | {k} | {'yes' if k >= 3 else 'no'} |")
    (OUT / ("step0.md" if a.tag == "s6" else "s6b.md")).write_text("\n".join(Ls) + "\n")
    print("\n".join(Ls[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
