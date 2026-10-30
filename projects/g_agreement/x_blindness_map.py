#!/usr/bin/env python
"""Phase X deliverable (BRIEF_X "Blindness map"): one table + one figure combining X1, X2 and X3.

Rows = feature classes {language, tense, ownership, mapping, puzzle-error, self-choice}.
Columns:
  PRESENT       X1 E2 (held-out probe win) / X3 E9 (held-out probe win), with the two-half ceiling
  LOAD-BEARING  X2 E4 at S2 (L38, all positions): flip rate at alpha = 1 and median alpha*  (binding families only)
  REPORTED_<r>  X1 E1 paired win per reader / X3 E8 P(favours the model's actual answer) per reader
  FOLLOWS_<r>   X2 E6 at S2: P(reader LO shift toward the planted candidate > 0 at alpha*), per family from follow.csv
Cells that a module could have tested but did not are printed "not tested" (LOAD-BEARING and FOLLOWS for language,
tense, puzzle-error and self-choice: X2 planted only the two binding families; see writeup Corrections 2026-10-08).
Cells that are structurally undefined (e.g. a reader with no scorable rows) keep "n/a". The FOLLOWS column is
proportional following implied by X1 (the S2 edit interpolates between two states the readers already separate),
not an independent test; the caption says so.

Usage: .venv/bin/python projects/g_agreement/x_blindness_map.py [--results results/g_agreement] [--y3-summary results/g_agreement/y3/summary.json]
Writes <results>/x/blindness_map.csv and <results>/x/fig_main.png.
``--y3-summary`` (Phase Y3) appends REPORTED_<r> / FOLLOWS_<r> columns for the readers listed under ``map_columns`` of that
summary (the readers that passed the E14 entry gate); without it the table is exactly the Phase X one.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

READERS = ("jlens", "olens", "nla")
READER_LABEL = {"jlens": "J-lens", "olens": "Oracle", "nla": "NLA"}
ROWS = ("language", "tense", "ownership", "mapping", "puzzle-error", "self-choice")
PRIMARY_SITE = "S2"
# feature classes for which X2 (LOAD-BEARING, FOLLOWS) was not run: the cell is "not tested", not "n/a"
NOT_TESTED_X2 = ("language", "tense", "puzzle-error", "self-choice")
FOLLOWS_CAPTION = ("FOLLOWS at S2 is proportional following implied by X1: at alpha = 1 the planted state is the natural B state the readers "
                   "already separate, so a reader that orders the natural pair follows the interpolation by continuity (writeup Corrections, 2026-10-08); "
                   "it is not an independent test of binding readout. 'not tested' = X2 was not run on this class.")


def cell_text(row: dict, col: str) -> str:
    """Text for an empty cell: 'not tested' when the module exists but was not run on this class, else 'n/a'."""
    if row["feature_class"] in NOT_TESTED_X2 and col.startswith(("loadbearing", "follows")):
        return "not tested"
    return "n/a"


def _load(p: Path):
    return json.load(open(p)) if p.exists() else None


def _rate(d: dict | None, k="p", lo="lo", hi="hi", n="n"):
    if not d or d.get(n) in (None, 0) or d.get(k) is None or (isinstance(d.get(k), float) and math.isnan(d[k])):
        return None
    return {"p": float(d[k]), "lo": d.get(lo), "hi": d.get(hi), "n": d.get(n), "k": d.get("k")}


def follows_by_family(follow_csv: Path, site: str) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], list[bool]] = defaultdict(list)
    if not follow_csv.exists():
        return {}
    with open(follow_csv) as f:
        for r in csv.DictReader(f):
            if r["site"] != site or r.get("alpha_star") in ("", None):
                continue
            out[(r["reader"], r["family"])].append(r["win"].strip().lower() == "true")
    res = {}
    for key, wins in out.items():
        n = len(wins)
        k = sum(wins)
        res[key] = {"p": k / n, "k": k, "n": n, "lo": None, "hi": None}
    return res


def extra_cell(extra: dict | None, reader: str, kind: str, fam: str) -> dict | None:
    """One pre-computed cell for an extra reader: {"p", "n"} or None."""
    if not extra or reader not in extra:
        return None
    d = ((extra[reader].get(kind) or {}).get(fam)) or None
    if not d or d.get("n") in (None, 0) or d.get("p") is None:
        return None
    return {"p": float(d["p"]), "n": int(d["n"])}


def build(results: Path, extra: dict | None = None) -> list[dict]:
    """``extra`` (Phase Y3): {reader: {"label": str, "reported": {feature_class: {"p", "n"}}, "follows": {...}}}; the
    extra readers' columns are appended after the three Phase X readers; their cells are taken as given."""
    extra = extra or {}
    x1 = _load(results / "x1" / "summary.json") or {}
    x2 = _load(results / "x2" / "summary.json") or {}
    x3 = _load(results / "x3" / "summary.json") or {}
    fol = follows_by_family(results / "x2" / "follow.csv", PRIMARY_SITE)
    site = (x2.get("by_site") or {}).get(PRIMARY_SITE) or {}
    flip1 = _rate(((site.get("E4_flip_by_alpha") or {}).get("1.0") or {}).get("flip"))
    alpha_star = (site.get("E5_alpha_star") or {}).get("median_alpha_star")
    rows = []
    for fam in ROWS:
        row: dict = {"feature_class": fam}
        if fam in ("language", "tense", "ownership", "mapping"):
            e2 = ((x1.get("E2") or {}).get(fam) or {})
            loo, ceil = e2.get("loo") or {}, ((e2.get("ceiling") or {}).get("pooled") or {})
            row["present_win"] = loo.get("p")
            row["present_ceiling_win"] = ceil.get("p")
            row["present_flag"] = e2.get("present")
            if fam in ("ownership", "mapping"):
                row["loadbearing_flip_alpha1"] = flip1["p"] if flip1 else None
                row["loadbearing_median_alpha_star"] = alpha_star
            else:
                row["loadbearing_flip_alpha1"] = None
                row["loadbearing_median_alpha_star"] = None
            for r in READERS:
                e1 = _rate(((x1.get("E1") or {}).get(r) or {}).get(fam))
                row[f"reported_{r}"] = e1["p"] if e1 else None
                row[f"reported_{r}_n"] = e1["n"] if e1 else 0
                f = fol.get((r, fam)) if fam in ("ownership", "mapping") else None
                row[f"follows_{r}"] = f["p"] if f else None
                row[f"follows_{r}_n"] = f["n"] if f else 0
        else:
            key, setname = ("puzzle", "error") if fam == "puzzle-error" else ("choice", "disagree")
            e9 = ((x3.get("E9") or {}).get(key) or {})
            row["present_win"] = e9.get("loo_win")
            row["present_ceiling_win"] = (e9.get("ceiling") or {}).get("win")
            row["present_flag"] = e9.get("present")
            row["loadbearing_flip_alpha1"] = None
            row["loadbearing_median_alpha_star"] = None
            for r in READERS:
                e8 = _rate(((x3.get("E8") or {}).get(r) or {}).get(setname), n="n_scored")
                row[f"reported_{r}"] = e8["p"] if e8 else None
                row[f"reported_{r}_n"] = e8["n"] if e8 else 0
                row[f"follows_{r}"] = None
                row[f"follows_{r}_n"] = 0
        for r in extra:
            rep_cell = extra_cell(extra, r, "reported", fam)
            fol_cell = extra_cell(extra, r, "follows", fam) if fam in ("ownership", "mapping") else None
            row[f"reported_{r}"] = rep_cell["p"] if rep_cell else None
            row[f"reported_{r}_n"] = rep_cell["n"] if rep_cell else 0
            row[f"follows_{r}"] = fol_cell["p"] if fol_cell else None
            row[f"follows_{r}_n"] = fol_cell["n"] if fol_cell else 0
        row["loadbearing_status"] = "not tested" if fam in NOT_TESTED_X2 else ("tested" if row["loadbearing_flip_alpha1"] is not None else "n/a")
        row["follows_status"] = "not tested" if fam in NOT_TESTED_X2 else ("tested" if any(row[f"follows_{r}"] is not None for r in READERS) else "n/a")
        rows.append(row)
    return rows


def write_csv(rows: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else (f"{v:.3f}" if isinstance(v, float) else v)) for k, v in r.items()})


def figure(rows: list[dict], out: Path, site_label: str, extra: dict | None = None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    extra = extra or {}
    labels = dict(READER_LABEL, **{r: (extra[r].get("label") or r) for r in extra})
    readers = list(READERS) + [r for r in extra if r not in READERS]
    cols = [("present_win", "PRESENT\n(probe, held-out)"), ("loadbearing_flip_alpha1", "LOAD-BEARING\n(flip @ α=1, L38 all)")]
    cols += [(f"reported_{r}", f"REPORTED\n{labels[r]}") for r in readers]
    cols += [(f"follows_{r}", f"FOLLOWS\n{labels[r]}") for r in readers]
    M = np.full((len(rows), len(cols)), np.nan)
    for i, r in enumerate(rows):
        for j, (c, _) in enumerate(cols):
            v = r.get(c)
            if v is not None:
                M[i, j] = v
    fig, ax = plt.subplots(figsize=(12 + 1.1 * max(0, len(readers) - len(READERS)) * 2, 6.0))
    cmap = plt.get_cmap("RdYlGn")
    cmap.set_bad("#dddddd")
    ax.imshow(np.ma.masked_invalid(M), cmap=cmap, vmin=0.4, vmax=1.0, aspect="auto")
    for i, r in enumerate(rows):
        for j, (c, _) in enumerate(cols):
            v = r.get(c)
            if v is None:
                ax.text(j, i, cell_text(r, c), ha="center", va="center", fontsize=9, color="#555")
                continue
            n = r.get(c + "_n") or (r.get("present_ceiling_win") and None)
            txt = f"{100 * v:.0f}%"
            if c.startswith(("reported", "follows")) and r.get(c + "_n"):
                txt += f"\n(n={r[c + '_n']})"
            if c == "present_win" and r.get("present_ceiling_win") is not None:
                txt += f"\nceil {100 * r['present_ceiling_win']:.0f}%"
            if c == "loadbearing_flip_alpha1" and r.get("loadbearing_median_alpha_star") is not None:
                txt += f"\nα* med {r['loadbearing_median_alpha_star']}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=8.5, color="black")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([c[1] for c in cols], fontsize=8.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["feature_class"] for r in rows], fontsize=10)
    ax.set_title(f"Blindness map, Qwen3.6-27B block-42 last token (readers scored by native log-odds; FOLLOWS at {site_label})",
                 fontsize=10)
    ax.set_xlabel("REPORTED = paired win on natural pairs (X1) or P(favours the model's actual answer) (X3); FOLLOWS = win at the minimal flipping dose α* (X2)",
                  fontsize=8)
    import textwrap
    fig.text(0.01, 0.005, "\n".join(textwrap.wrap(FOLLOWS_CAPTION, 170)), fontsize=7.5, color="#333", ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="results/g_agreement")
    ap.add_argument("--y3-summary", default=None, help="Phase Y3 summary.json whose map_columns add REPORTED/FOLLOWS columns for the gated readers")
    a = ap.parse_args(argv)
    results = Path(a.results)
    extra = None
    if a.y3_summary:
        y3 = _load(Path(a.y3_summary)) or {}
        extra = y3.get("map_columns") or {}
        print(f"[x] Y3 columns for readers {sorted(extra)}")
    rows = build(results, extra)
    write_csv(rows, results / "x" / "blindness_map.csv")
    x2 = _load(results / "x2" / "summary.json") or {}
    label = ((x2.get("by_site") or {}).get(PRIMARY_SITE) or {}).get("label", PRIMARY_SITE)
    figure(rows, results / "x" / "fig_main.png", label, extra)
    for r in rows:
        cells = {k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in r.items() if not k.endswith("_n")}
        print("[x]", cells)
    print("[x] wrote", results / "x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
