"""V4 scoring: judge–human Cohen's kappa from the filled `human_labels.csv`, plus W3 precision on the human subset.

    .venv/bin/python -m projects.g_agreement.w_claims.kappa results/g_agreement/v/human_labels.csv [--out v4_kappa.json]

Accepted human labels (case-insensitive): true / false / unverifiable, t / f / u, 1 / 0, or the full judge labels
(input_true, computation_false, ...). Only the truth value is compared (the claim type is the judge's and is kept).
Rows with a blank human_label are skipped; if the human label is a full label whose type differs from the
judge's, that is reported as a type disagreement but the truth value is still compared.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

from .stats import cohen_kappa, kappa_bootstrap, precision_item_bootstrap

TRUE_SET = {"true", "t", "1", "yes", "y", "correct"}
FALSE_SET = {"false", "f", "0", "no", "n", "wrong", "incorrect"}


def parse_human(s: str) -> Optional[str]:
    """-> 'true' | 'false' | 'unverifiable' | None (blank or unparseable)."""
    v = (s or "").strip().lower()
    if not v:
        return None
    if v in TRUE_SET or v.endswith("_true"):
        return "true"
    if v in FALSE_SET or v.endswith("_false"):
        return "false"
    if v in {"unverifiable", "u", "unv", "?"}:
        return "unverifiable"
    return None


def human_type(s: str) -> Optional[str]:
    v = (s or "").strip().lower()
    return v.split("_", 1)[0] if "_" in v else None


def judge_truth(label: str) -> str:
    return "unverifiable" if label == "unverifiable" else ("true" if label.endswith("_true") else "false")


def score(rows: List[dict], n_boot: int = 1000, seed: int = 0) -> dict:
    labelled = [r for r in rows if parse_human(r.get("human_label", "")) is not None]
    j = [judge_truth(r["judge_label"]) for r in labelled]
    h = [parse_human(r["human_label"]) for r in labelled]
    out = {"n_rows": len(rows), "n_labelled": len(labelled), "overall": cohen_kappa(j, h)}
    out["overall"]["lo"], out["overall"]["hi"] = kappa_bootstrap(j, h, n_boot, seed)
    out["type_disagreements"] = sum(1 for r in labelled
                                    if human_type(r["human_label"]) not in (None, r["claim_type"]))
    out["by_reader"], out["by_type"], out["by_reader_type"] = {}, {}, {}
    for key, fn in (("by_reader", lambda r: r["reader"]), ("by_type", lambda r: r["claim_type"]),
                    ("by_reader_type", lambda r: f"{r['reader']}/{r['claim_type']}")):
        for g in sorted({fn(r) for r in labelled}):
            idx = [i for i, r in enumerate(labelled) if fn(r) == g]
            out[key][g] = cohen_kappa([j[i] for i in idx], [h[i] for i in idx])
    # W3 precision on the human subset, using the HUMAN truth value
    prec = {}
    for reader in sorted({r["reader"] for r in labelled}):
        prec[reader] = {}
        for t in ("input", "computation"):
            sel = [(r["item_id"], hh) for r, hh in zip(labelled, h) if r["reader"] == reader and r["claim_type"] == t
                   and hh in ("true", "false")]
            prec[reader][t] = {"human": precision_item_bootstrap([s[0] for s in sel], [s[1] == "true" for s in sel],
                                                                 n_boot, seed)}
            selj = [(r["item_id"], jj) for r, jj in zip(labelled, j) if r["reader"] == reader and r["claim_type"] == t
                    and jj in ("true", "false")]
            prec[reader][t]["judge_same_rows"] = precision_item_bootstrap([s[0] for s in selj],
                                                                          [s[1] == "true" for s in selj], n_boot, seed)
    out["precision_human_subset"] = prec
    return out


def render(res: dict) -> str:
    o = res["overall"]
    L = [f"human-labelled rows: {res['n_labelled']} / {res['n_rows']}",
         f"judge–human kappa (truth value): {o['kappa'] if o['kappa'] is None else round(o['kappa'], 3)} "
         f"[{o.get('lo')}, {o.get('hi')}], agreement {o['agreement']}",
         f"type disagreements (human gave a full label of another type): {res['type_disagreements']}", ""]
    for key in ("by_reader", "by_type", "by_reader_type"):
        L.append(key + ": " + ", ".join(f"{g}: kappa={v['kappa'] if v['kappa'] is None else round(v['kappa'], 2)} "
                                         f"(n={v['n']})" for g, v in res[key].items()))
    L += ["", "| reader | type | human precision [CI] | judge precision on the same rows |", "|---|---|---|---|"]
    for r, d in res["precision_human_subset"].items():
        for t, v in d.items():
            def f(x):
                return "n/a" if x["precision"] is None else f"{100 * x['precision']:.0f}% [{100 * x['lo']:.0f}, {100 * x['hi']:.0f}] (n={x['n_claims']})"
            L.append(f"| {r} | {t} | {f(v['human'])} | {f(v['judge_same_rows'])} |")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    with Path(a.csv).open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    res = score(rows, a.n_boot, a.seed)
    print(render(res))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
