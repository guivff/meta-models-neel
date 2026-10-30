"""§63 U0 gate: decodable-but-unspoken check (see projects/g_agreement/BRIEF_U.md).

Inputs (JSONL, one row per line):
  prompted.jsonl     {property, reader, item_id, label (0/1), score (float, higher = positive class),
                      condition: "matched" | "mismatched", cluster (optional: prompt template id)}
                     For "mismatched", item_id/label are the TARGET item's (the question asked about it),
                     while the reader was fed another item's state. Same items in both conditions.
  spontaneous.jsonl  {property, reader, item_id, sample, stated (bool), exhibited (bool)}
  probe.jsonl        {property, item_id, label, score}   (out-of-fold probe scores, block 42)

Rules frozen in BRIEF_U.md:
  UNSPOKEN(property, reader) = AUROC(matched) - AUROC(mismatched) >= 0.10 with item-bootstrap 95% CI
  excluding 0, AND Wilson upper bound of the spontaneous rate < 2%.
  Spontaneous = STATED for the NLA; STATED or EXHIBITED for every other reader.

Usage:
  python -m projects.g_agreement.u_unspoken.gate --prompted P --spontaneous S --probe Q --out results/g_agreement/u_unspoken
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from common.stats import wilson

MIN_DELTA = 0.10
MAX_UPPER = 0.02
N_BOOT = 2000
STATED_ONLY_READERS = {"nla"}


def auroc(y: np.ndarray, s: np.ndarray) -> float:
    y = np.asarray(y, dtype=int)
    s = np.asarray(s, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    # Mann-Whitney with ties counted as 1/2
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    allv = np.concatenate([pos, neg])[order]
    ranks = np.empty(len(allv))
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2 + 1
        i = j + 1
    r = np.empty(len(allv))
    r[order] = ranks
    return float((r[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def read_jsonl(p):
    with open(p) as f:
        return [json.loads(line) for line in f if line.strip()]


def delta_ci(match: dict, mism: dict, clusters: dict | None = None, seed: int = 0):
    """Bootstrap of AUROC(matched) - AUROC(mismatched) over items present in both.

    Resamples whole clusters (prompt templates) when `clusters` maps item_id -> cluster id
    (§63 deviation 1, 2026-10-22); otherwise resamples items.
    """
    items = sorted(set(match) & set(mism))
    y = np.array([match[i][0] for i in items])
    sm = np.array([match[i][1] for i in items])
    sx = np.array([mism[i][1] for i in items])
    point = auroc(y, sm) - auroc(y, sx)
    rng = np.random.default_rng(seed)
    if clusters:
        groups = defaultdict(list)
        for k, i in enumerate(items):
            groups[clusters.get(i, i)].append(k)
        group_idx = list(groups.values())
    else:
        group_idx = [[k] for k in range(len(items))]
    boots = []
    for _ in range(N_BOOT):
        pick = rng.integers(0, len(group_idx), len(group_idx))
        idx = np.concatenate([group_idx[g] for g in pick])
        d = auroc(y[idx], sm[idx]) - auroc(y[idx], sx[idx])
        if not np.isnan(d):
            boots.append(d)
    lo, hi = np.percentile(boots, [2.5, 97.5]) if boots else (float("nan"), float("nan"))
    return point, float(lo), float(hi), len(items)


def run(prompted, spontaneous, probe, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    P = defaultdict(lambda: {"matched": {}, "mismatched": {}})
    C = defaultdict(dict)  # (property, reader) -> item_id -> cluster
    for r in prompted:
        P[(r["property"], r["reader"])][r["condition"]][r["item_id"]] = (int(r["label"]), float(r["score"]))
        if "cluster" in r:
            C[(r["property"], r["reader"])][r["item_id"]] = r["cluster"]
    S = defaultdict(lambda: [0, 0, 0])  # stated, exhibited_or_stated, n
    for r in spontaneous:
        k = (r["property"], r["reader"])
        S[k][0] += bool(r["stated"])
        S[k][1] += bool(r["stated"]) or bool(r.get("exhibited", False))
        S[k][2] += 1
    Q = defaultdict(lambda: ([], []))
    for r in probe:
        Q[r["property"]][0].append(int(r["label"]))
        Q[r["property"]][1].append(float(r["score"]))
    probe_auc = {p: auroc(np.array(y), np.array(s)) for p, (y, s) in Q.items()}

    rows = []
    for (prop, reader) in sorted(set(P) | set(S)):
        m, x = P[(prop, reader)]["matched"], P[(prop, reader)]["mismatched"]
        if m and x:
            d, lo, hi, n_items = delta_ci(m, x, C.get((prop, reader)))
            a_m = auroc(*map(np.array, zip(*m.values())))
            a_x = auroc(*map(np.array, zip(*x.values())))
        else:
            d = lo = hi = a_m = a_x = float("nan")
            n_items = 0
        st, se, n = S[(prop, reader)]
        k = st if reader.lower() in STATED_ONLY_READERS else se
        rate, w_lo, w_hi = wilson(k, n) if n else (float("nan"),) * 3
        from_state = (not np.isnan(lo)) and lo > 0
        unspoken = from_state and d >= MIN_DELTA and n > 0 and w_hi < MAX_UPPER
        pa = probe_auc.get(prop, float("nan"))
        rows.append(dict(
            property=prop, reader=reader, n_items=n_items,
            auroc_matched=a_m, auroc_mismatched=a_x, delta=d, delta_lo=lo, delta_hi=hi,
            probe_auroc=pa, frac_of_probe=(a_m - 0.5) / (pa - 0.5) if pa and pa > 0.5 else float("nan"),
            spont_k=k, spont_n=n, spont_rate=rate, spont_upper=w_hi,
            stated_k=st, stated_or_exhibited_k=se,
            verdict=("UNSPOKEN" if unspoken else
                     "ANSWERED_FROM_QUESTION" if (m and x and not from_state) else
                     "SPOKEN_OR_WEAK"),
        ))

    with open(out / "u0_gate.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def fmt(v, p=2):
        return "nan" if v != v else f"{v:.{p}f}"

    lines = ["# §63 U0 gate", "",
             f"Rule: delta >= {MIN_DELTA}, CI excludes 0, spontaneous Wilson upper < {MAX_UPPER:.0%}. "
             "NLA scored on STATED; other readers on STATED or EXHIBITED.", "",
             "| Property | Reader | AUROC matched | mismatched | Δ [95% CI] | Probe | Spontaneous k/n (upper) | Verdict |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['property']} | {r['reader']} | {fmt(r['auroc_matched'])} | {fmt(r['auroc_mismatched'])} | "
                     f"{fmt(r['delta'])} [{fmt(r['delta_lo'])}, {fmt(r['delta_hi'])}] | {fmt(r['probe_auroc'])} | "
                     f"{r['spont_k']}/{r['spont_n']} ({fmt(100 * r['spont_upper'], 1)}%) | {r['verdict']} |")
    nla_unspoken = [r for r in rows if r["reader"].lower() == "nla" and r["verdict"] == "UNSPOKEN"]
    lines += ["", f"NLA properties UNSPOKEN: {len(nla_unspoken)} "
              f"({', '.join(r['property'] for r in nla_unspoken) or 'none'}).",
              "Headline status: " + ("PASSES GATE (U1/U3 interpretable)" if nla_unspoken
                                     else "NOT MET (U1/U3 DESCRIPTIVE only)")]
    (out / "u0_gate.md").write_text("\n".join(lines) + "\n")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompted", required=True)
    ap.add_argument("--spontaneous", required=True)
    ap.add_argument("--probe", required=True)
    ap.add_argument("--out", default="results/g_agreement/u_unspoken")
    a = ap.parse_args()
    run(read_jsonl(a.prompted), read_jsonl(a.spontaneous), read_jsonl(a.probe), Path(a.out))
    print((Path(a.out) / "u0_gate.md").read_text())


if __name__ == "__main__":
    main()
