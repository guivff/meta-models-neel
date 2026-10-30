"""Friday re-analysis R1 (NEXT_STEPS.md §1) + Y0 tables for X2 — CPU only, from the frozen X2 artefacts.

Inputs (never modified):
  cache/g_agreement/x/x2_behaviour.jsonl   one row per entry (pair_id, source, site, alpha, condition, cand_A = own answer,
                                           cand_B = other candidate, flipped_to_other, coherent, lo_model = lp_first_B - lp_first_A)
  cache/g_agreement/x/x2_lo.jsonl          one row per (reader, entry): lo_own = lp(cand_A) - lp(cand_B), lo_toward_other = -lo_own
  results/g_agreement/x2/follow.csv        analyze.py's per-item table (cross-checked, not required)

R1  Renormalisation. Every shift is expressed as a fraction of the reader's OWN natural separation of the pair, in the
    frame of the source state:   frac(entry) = (lo_to(entry) - lo_to(nat, this state)) / sep,
    sep = (-lo_to(nat, OTHER state)) - lo_to(nat, this state)  [= lo_own(A) + lo_own(B), the same number for both states].
    At S2/S3 alpha = 1 the edited state IS the other state, so frac = 1 by construction (printed as a sanity check).
    The model's fraction uses lo_model the same way. Reported: median/IQR per (site, reader, alpha); win at alpha* conditional
    on whether the reader orders the natural pair correctly (lo_own > 0 in both states); the model's own sub-flip sign-win.
Y0  per_pair.csv (one row per (pair, source)), and the S1 alpha-2 other-pair preview (reader side only: nothing flips at S1).

Outputs: results/g_agreement/x/friday/{r1_fraction.csv, r1_conditional.csv, r1_model_signwin.csv, r1_s1_otherpair.csv,
         r1_summary.json, R1.md};  results/g_agreement/x2/{fig_fraction.png, per_pair.csv}.  fig_main.png is not touched.
Run:  PYTHONPATH=. .venv/bin/python projects/g_agreement/x_friday_r1.py
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.x2_causal import analyze as XA  # noqa: E402  (constants + band/zscore helpers; not modified)

READERS = XA.READERS
READER_LABELS = dict(XA.READER_LABELS)
MODEL = "model"
READER_LABELS[MODEL] = "model (lo_model)"
SITES = ("S2", "S3", "S1")
SITE_LABELS = XA.SITE_LABELS
NAT = XA.NAT
S1_PREVIEW_ALPHA = 2.0
DEFAULT_BEH = ROOT / "cache" / "g_agreement" / "x" / "x2_behaviour.jsonl"
DEFAULT_LO = ROOT / "cache" / "g_agreement" / "x" / "x2_lo.jsonl"
DEFAULT_FOLLOW = ROOT / "results" / "g_agreement" / "x2" / "follow.csv"
DEFAULT_OUT_FRIDAY = ROOT / "results" / "g_agreement" / "x" / "friday"
DEFAULT_OUT_X2 = ROOT / "results" / "g_agreement" / "x2"

Item = Tuple[str, str]  # (pair_id, source)


# --------------------------------------------------------------------------------------
# world
# --------------------------------------------------------------------------------------
@dataclass
class World:
    beh: List[dict]
    by_key: Dict[str, dict]
    items: List[Item]
    nat: Dict[Item, dict]
    grp: Dict[Tuple[str, Item, str], List[dict]]  # (site, item, condition) -> rows (sorted by alpha then null_k)
    lo: Dict[str, Dict[str, Optional[float]]]      # reader -> entry key -> lo_toward_other (None if unscorable)
    readers: List[str] = field(default_factory=list)
    sites: List[str] = field(default_factory=list)

    def fam(self, it: Item) -> str:
        return self.nat[it]["family"]

    def other(self, it: Item) -> Item:
        return (it[0], "B" if it[1] == "A" else "A")

    def alphas(self, site: str) -> List[float]:
        return sorted({float(r["alpha"]) for it in self.items for r in self.grp.get((site, it, "planted"), [])})

    def planted(self, site: str, it: Item) -> List[dict]:
        return self.grp.get((site, it, "planted"), [])

    def value(self, reader: str, row: dict) -> Optional[float]:
        """lo toward the other candidate for this entry: the reader's native LO, or the model's first-token LO."""
        if reader == MODEL:
            if row.get("lo_model_unscorable"):
                return None
            v = row.get("lo_model")
            return None if v is None else float(v)
        return self.lo.get(reader, {}).get(row["key"])

    def nat_value(self, reader: str, it: Item) -> Optional[float]:
        return None if it not in self.nat else self.value(reader, self.nat[it])


def load_world(beh_path: Path | str, lo_path: Path | str) -> World:
    beh = U.load_jsonl(beh_path)
    if not beh:
        raise U.AnalysisError(f"no behaviour rows in {beh_path}")
    by_key = {r["key"]: r for r in beh}
    if len(by_key) != len(beh):
        raise U.AnalysisError("duplicate behaviour keys")
    items = sorted({(r["pair_id"], r["source"]) for r in beh})
    nat = {(r["pair_id"], r["source"]): r for r in beh if r["condition"] == "natural"}
    for p in sorted({p for p, _ in items}):
        a, b = nat.get((p, "A")), nat.get((p, "B"))
        if a is None or b is None:
            raise U.AnalysisError(f"pair {p}: missing a natural state")
        if a["cand_A"] != b["cand_B"] or a["cand_B"] != b["cand_A"]:
            raise U.AnalysisError(f"pair {p}: candidates are not mirrored across the two states")
    grp: Dict[Tuple[str, Item, str], List[dict]] = defaultdict(list)
    for r in beh:
        if r["site"] != NAT:
            grp[(r["site"], (r["pair_id"], r["source"]), r["condition"])].append(r)
    for k in grp:
        grp[k].sort(key=lambda r: (float(r["alpha"]), -1 if r.get("null_k") is None else int(r["null_k"])))
    lo: Dict[str, Dict[str, Optional[float]]] = defaultdict(dict)
    for r in U.load_jsonl(lo_path):
        ek = r.get("entry_key") or r["key"].split("|", 1)[1]
        lo[r["reader"]][ek] = None if r.get("unscorable") else (None if r.get("lo_toward_other") is None else float(r["lo_toward_other"]))
    readers = [rd for rd in READERS if rd in lo]
    sites = [s for s in SITES if any(r["site"] == s for r in beh)]
    return World(beh, by_key, items, nat, dict(grp), dict(lo), readers, sites)


# --------------------------------------------------------------------------------------
# R1 quantities
# --------------------------------------------------------------------------------------
def separation(w: World, reader: str) -> Dict[Item, Optional[float]]:
    """sep in the frame of `it`: (-lo_to(nat other)) - lo_to(nat this) = lo_own(A) + lo_own(B); None if either natural is unscorable."""
    out: Dict[Item, Optional[float]] = {}
    for it in w.items:
        a, b = w.nat_value(reader, it), w.nat_value(reader, w.other(it))
        out[it] = None if a is None or b is None else (-b) - a
    return out


ORDER_DEFS = ("both", "pair")


def ordered(w: World, reader: str, definition: str = "both") -> Dict[str, Optional[bool]]:
    """pair -> the reader orders the natural pair correctly.
    'both': lo_own > 0 (lo_toward_other < 0) in BOTH natural states (the literal per-state criterion; defeated by any candidate bias);
    'pair': within-pair contrast sep = lo_own(A) + lo_own(B) > 0 (X1's E1 paired win on this pair; the reader separates the two states
            in the right direction even if a constant candidate bias misorders one of them). sep == 0 (quantised ties) counts as not ordered."""
    out: Dict[str, Optional[bool]] = {}
    for p in sorted({p for p, _ in w.items}):
        a, b = w.nat_value(reader, (p, "A")), w.nat_value(reader, (p, "B"))
        if a is None or b is None:
            out[p] = None
        elif definition == "both":
            out[p] = bool(a < 0 and b < 0)
        elif definition == "pair":
            out[p] = bool((-a) + (-b) > 0)
        else:
            raise ValueError(definition)
    return out


def shifts(w: World, reader: str, site: str, condition: str = "planted") -> Dict[Tuple[Item, float], List[float]]:
    """(item, alpha) -> list of lo_toward_other shifts (one per planted entry, K per null condition)."""
    out: Dict[Tuple[Item, float], List[float]] = defaultdict(list)
    for it in w.items:
        l0 = w.nat_value(reader, it)
        if l0 is None:
            continue
        for r in w.grp.get((site, it, condition), []):
            v = w.value(reader, r)
            if v is not None:
                out[(it, float(r["alpha"]))].append(v - l0)
    return dict(out)


def fractions(w: World, reader: str, site: str, condition: str = "planted") -> Dict[Tuple[Item, float], List[float]]:
    sep = separation(w, reader)
    out: Dict[Tuple[Item, float], List[float]] = {}
    for (it, a), vals in shifts(w, reader, site, condition).items():
        s = sep[it]
        if s is None or s == 0:
            continue
        out[(it, a)] = [v / s for v in vals]
    return out


def alpha_star(w: World, site: str) -> Dict[Item, Optional[float]]:
    """E5: smallest ladder alpha whose answer is the other candidate and coherent (analyze.py definition)."""
    out: Dict[Item, Optional[float]] = {}
    for it in w.items:
        fl = [float(r["alpha"]) for r in w.planted(site, it) if r["flipped_to_other"] and r.get("coherent", True)]
        out[it] = min(fl) if fl else None
    return out


def largest_subflip_alpha(w: World, site: str, astar: Dict[Item, Optional[float]]) -> Dict[Item, Optional[float]]:
    """largest ladder alpha strictly below alpha* (the model has not flipped there)."""
    out: Dict[Item, Optional[float]] = {}
    for it in w.items:
        a = astar.get(it)
        below = [float(r["alpha"]) for r in w.planted(site, it) if a is not None and float(r["alpha"]) < a]
        out[it] = max(below) if below else None
    return out


def subflip_dose_z(w: World, site: str, astar: Dict[Item, Optional[float]]) -> Dict[Item, Optional[float]]:
    """analyze.py's SUB-FLIP dose: largest alpha < alpha* with |z_model| < 2 against the item's isotropic-null band."""
    out: Dict[Item, Optional[float]] = {}
    for it in w.items:
        a = astar.get(it)
        n0 = w.nat_value(MODEL, it)
        if a is None or n0 is None:
            out[it] = None
            continue
        bd = XA.band([w.value(MODEL, r) - n0 for r in w.grp.get((site, it, "null"), []) if w.value(MODEL, r) is not None])
        cands = []
        for r in w.planted(site, it):
            al, v = float(r["alpha"]), w.value(MODEL, r)
            if al >= a or v is None:
                continue
            zm = XA.zscore(v - n0, *bd)
            if not np.isnan(zm) and abs(zm) < XA.Z_MODEL_INSIDE:
                cands.append(al)
        out[it] = max(cands) if cands else None
    return out


# --------------------------------------------------------------------------------------
# bootstrap helpers (pair-level, via analyze_utils.pair_bootstrap_stat)
# --------------------------------------------------------------------------------------
def _q(vals: Sequence[float]) -> Tuple[float, float, float, int]:
    v = np.asarray([x for x in vals if x is not None and not np.isnan(x)], dtype=float)
    if v.size == 0:
        return float("nan"), float("nan"), float("nan"), 0
    return float(np.median(v)), float(np.quantile(v, 0.25)), float(np.quantile(v, 0.75)), int(v.size)


def boot_by_pair(vals_by_pair: Dict[str, List[float]], fn: Callable[[np.ndarray], float], nb: int, sd: int) -> Tuple[float, float, float]:
    pids = sorted(p for p, v in vals_by_pair.items() if v)

    def stat(ps: Sequence[str]) -> float:
        v = np.concatenate([np.asarray(vals_by_pair[p], dtype=float) for p in ps]) if ps else np.array([])
        return float("nan") if v.size == 0 else float(fn(v))

    return U.pair_bootstrap_stat(pids, stat, nb, sd) if pids else (float("nan"), float("nan"), float("nan"))


def _group_by_pair(d: Dict[Tuple[Item, float], List[float]], alpha: Optional[float] = None, keep: Optional[Callable[[Item, float], bool]] = None) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = defaultdict(list)
    for (it, a), vals in d.items():
        if alpha is not None and a != alpha:
            continue
        if keep is not None and not keep(it, a):
            continue
        out[it[0]].extend(vals)
    return dict(out)


# --------------------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------------------
def fraction_table(w: World) -> Tuple[List[dict], Dict[str, Dict[str, Dict[Tuple[Item, float], List[float]]]]]:
    """one row per (site, reader|model, alpha): median / q25 / q75 / n of the fraction over all source states."""
    rows: List[dict] = []
    cache: Dict[str, Dict[str, Dict[Tuple[Item, float], List[float]]]] = {}
    for site in w.sites:
        cache[site] = {}
        for rd in list(w.readers) + [MODEL]:
            fr = fractions(w, rd, site)
            cache[site][rd] = fr
            for a in w.alphas(site):
                vals = [v for (it, al), vs in fr.items() if al == a for v in vs]
                med, q25, q75, n = _q(vals)
                sh = [v for (it, al), vs in shifts(w, rd, site).items() if al == a for v in vs]
                rows.append({"site": site, "reader": rd, "alpha": a, "median": med, "q25": q25, "q75": q75, "n": n,
                             "signwin": float(np.mean([v > 0 for v in vals])) if vals else float("nan"),
                             "median_raw_shift": float(np.median(sh)) if sh else float("nan")})
    return rows, cache


def conditional_table(w: World, astar_by_site: Dict[str, Dict[Item, Optional[float]]], nb: int, sd: int) -> List[dict]:
    rows: List[dict] = []
    for site in w.sites:
        astar = astar_by_site[site]
        for rd in list(w.readers) + [MODEL]:
            sh = shifts(w, rd, site)
            for dfn in ORDER_DEFS:
                od = ordered(w, rd, dfn)
                flags: Dict[str, List[Tuple[str, Optional[bool]]]] = {"yes": [], "no": []}
                for it in w.items:
                    a = astar.get(it)
                    if a is None or (it, a) not in sh or od.get(it[0]) is None:
                        continue
                    flags["yes" if od[it[0]] else "no"].append((it[0], sh[(it, a)][0] > 0))
                for key in ("yes", "no"):
                    r = U.pair_rate(flags[key], nb, sd)
                    rows.append({"reader": rd, "site": site, "definition": dfn, "ordered": key, "k": r.k, "n": r.n, "win": r.p, "lo": r.lo, "hi": r.hi, "n_pairs": r.n_pairs,
                                 "n_pairs_ordered_total": sum(1 for v in od.values() if v is (key == "yes"))})
    return rows


def model_signwin_table(w: World, astar_by_site: Dict[str, Dict[Item, Optional[float]]], nb: int, sd: int) -> List[dict]:
    """the model's own sign-win per alpha: P(lo_model shift > 0) over items whose alpha* is above this alpha (and over all items)."""
    rows: List[dict] = []
    for site in w.sites:
        sh = shifts(w, MODEL, site)
        astar = astar_by_site[site]
        for a in w.alphas(site):
            sub = [(it[0], v[0] > 0) for (it, al), v in sh.items() if al == a and astar.get(it) is not None and a < astar[it]]
            allf = [(it[0], v[0] > 0) for (it, al), v in sh.items() if al == a]
            r_sub, r_all = U.pair_rate(sub, nb, sd), U.pair_rate(allf, nb, sd)
            rows.append({"site": site, "alpha": a, "scope": "below_alpha_star", "k": r_sub.k, "n": r_sub.n, "signwin": r_sub.p, "lo": r_sub.lo, "hi": r_sub.hi})
            rows.append({"site": site, "alpha": a, "scope": "all_items", "k": r_all.k, "n": r_all.n, "signwin": r_all.p, "lo": r_all.lo, "hi": r_all.hi})
    return rows


def per_pair_table(w: World, astar_by_site: Dict[str, Dict[Item, Optional[float]]], site: str = "S2") -> List[dict]:
    readers = list(w.readers)
    astar = astar_by_site.get(site, {})
    a_sub = largest_subflip_alpha(w, site, astar)
    a_subz = subflip_dose_z(w, site, astar)
    sep = {rd: separation(w, rd) for rd in readers + [MODEL]}
    fr = {rd: fractions(w, rd, site) for rd in readers + [MODEL]}
    sh = {rd: shifts(w, rd, site) for rd in readers + [MODEL]}
    od = {(rd, d): ordered(w, rd, d) for rd in readers for d in ORDER_DEFS}

    def first(d: Dict[Tuple[Item, float], List[float]], it: Item, a: Optional[float]):
        return None if a is None or (it, a) not in d else d[(it, a)][0]

    rows: List[dict] = []
    for it in w.items:
        a = astar.get(it)
        n0 = w.nat_value(MODEL, it)
        row: Dict[str, Any] = {"pair_id": it[0], "source": it[1], "family": w.fam(it), "own_answer": w.nat[it]["cand_A"], "other_answer": w.nat[it]["cand_B"]}
        for s in ("S1", "S2", "S3"):
            row[f"alpha_star_{s}"] = astar_by_site.get(s, {}).get(it)
        row.update({f"subflip_alpha_{site}": a_sub.get(it), f"subflip_alpha_z_{site}": a_subz.get(it),
                    "lo_model_nat": n0, f"lo_model_at_astar_{site}": None if a is None or n0 is None else n0 + first(sh[MODEL], it, a),
                    "model_sep": sep[MODEL][it], f"model_frac_at_astar_{site}": first(fr[MODEL], it, a),
                    f"model_frac_at_subflip_{site}": first(fr[MODEL], it, a_sub.get(it))})
        for rd in readers:
            l_this, l_other = w.nat_value(rd, it), w.nat_value(rd, w.other(it))
            row.update({f"{rd}_lo_own_nat_this": None if l_this is None else -l_this, f"{rd}_lo_own_nat_other": None if l_other is None else -l_other,
                        f"{rd}_sep": sep[rd][it], f"{rd}_ordered_both": od[(rd, "both")].get(it[0]), f"{rd}_ordered_pair": od[(rd, "pair")].get(it[0]),
                        f"{rd}_frac_at_astar_{site}": first(fr[rd], it, a), f"{rd}_frac_at_subflip_{site}": first(fr[rd], it, a_sub.get(it)),
                        f"{rd}_frac_at_subflip_z_{site}": first(fr[rd], it, a_subz.get(it)),
                        f"{rd}_win_at_astar_{site}": None if first(sh[rd], it, a) is None else bool(first(sh[rd], it, a) > 0)})
        rows.append(row)
    return rows


def s1_otherpair_table(w: World, nb: int, sd: int, site: str = "S1", alpha: float = S1_PREVIEW_ALPHA) -> List[dict]:
    rows: List[dict] = []
    if site not in w.sites:
        return rows
    for rd in list(w.readers) + [MODEL]:
        sep = separation(w, rd)
        for cond in ("planted", "null", "null_other"):
            sh = shifts(w, rd, site, cond)
            byp = _group_by_pair(sh, alpha)
            if not byp:
                continue
            mean = boot_by_pair(byp, np.mean, nb, sd)
            med = boot_by_pair(byp, np.median, nb, sd)
            sw = U.pair_rate([(it[0], v > 0) for (it, a), vs in sh.items() if a == alpha for v in vs], nb, sd)
            frs = [v / sep[it] for (it, a), vs in sh.items() if a == alpha and sep[it] not in (None, 0) for v in vs]
            beh_rows = [r for it in w.items for r in w.grp.get((site, it, cond), []) if float(r["alpha"]) == alpha]
            rows.append({"reader": rd, "site": site, "condition": cond, "alpha": alpha, "n": sw.n, "n_pairs": sw.n_pairs,
                         "mean_shift": mean[0], "mean_lo": mean[1], "mean_hi": mean[2], "median_shift": med[0], "median_lo": med[1], "median_hi": med[2],
                         "signwin_k": sw.k, "signwin_p": sw.p, "signwin_lo": sw.lo, "signwin_hi": sw.hi,
                         "median_fraction": float(np.median(frs)) if frs else float("nan"),
                         "model_flips_k": sum(bool(r["flipped_to_other"]) for r in beh_rows), "model_flips_n": len(beh_rows)})
    return rows


def crosscheck_follow(w: World, follow_csv: Optional[Path], astar_by_site: Dict[str, Dict[Item, Optional[float]]]) -> dict:
    """recomputed win at alpha* vs analyze.py's follow.csv (same definition; the mismatch count must be 0)."""
    if follow_csv is None or not Path(follow_csv).exists():
        return {"checked": False}
    with open(follow_csv, encoding="utf-8", newline="") as f:
        fr = list(csv.DictReader(f))
    mism, n = 0, 0
    for r in fr:
        site, rd, it = r["site"], r["reader"], (r["pair_id"], r["source"])
        if site not in w.sites or rd not in w.readers:
            continue
        a = astar_by_site[site].get(it)
        sh = shifts(w, rd, site).get((it, a)) if a is not None else None
        if a is None or sh is None or float(r["alpha_star"]) != a:
            mism += 1
            continue
        n += 1
        mism += int((sh[0] > 0) != (r["win"] == "True"))
    return {"checked": True, "n_rows": n, "n_mismatch": mism, "path": str(follow_csv)}


# --------------------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------------------
def make_fig(path: Path, w: World, frac_rows: List[dict], astar_by_site: Dict[str, Dict[Item, Optional[float]]]) -> None:
    plt = U.mpl()
    fig = plt.figure(figsize=(13, 7.5))
    gs = fig.add_gridspec(2, 3, width_ratios=[2.1, 1, 1])
    axes = {"S2": fig.add_subplot(gs[:, 0]), "S1": fig.add_subplot(gs[0, 1:]), "S3": fig.add_subplot(gs[1, 1:])}
    for site, ax in axes.items():
        if site not in w.sites:
            ax.axis("off"); continue
        alphas = w.alphas(site)
        xmax = max(alphas) * 1.08
        if site in ("S2", "S3"):
            ax.plot([0, max(alphas)], [0, max(alphas)], ls="--", color=U.INK2, lw=1, label="y = x (linear walk A→B)", zorder=1)
        ax.axhline(0, color=U.INK2, lw=0.8); ax.axhline(1, color=U.INK2, lw=0.8, ls=":")
        for rd in [MODEL] + list(w.readers):
            rows = sorted([r for r in frac_rows if r["site"] == site and r["reader"] == rd], key=lambda r: r["alpha"])
            if not rows:
                continue
            xs = [0.0] + [r["alpha"] for r in rows]
            ms = [0.0] + [r["median"] for r in rows]
            lo = [0.0] + [r["q25"] for r in rows]
            hi = [0.0] + [r["q75"] for r in rows]
            col = "black" if rd == MODEL else U.METHOD_COLORS[rd]
            ax.plot(xs, ms, "o-", color=col, lw=2.2 if rd == MODEL else 1.8, ms=5, label=READER_LABELS[rd], zorder=5 if rd == MODEL else 4)
            ax.fill_between(xs, lo, hi, color=col, alpha=0.10 if rd == MODEL else 0.15, zorder=2)
        astar = astar_by_site[site]
        cnt = {a: sum(1 for v in astar.values() if v == a) for a in alphas}
        nflip = sum(cnt.values())
        for a, k in cnt.items():
            if k:
                ax.axvline(a, color=U.INK2, lw=0.6, ls=":", zorder=0)
                ax.text(a, 0.985, f"α*: {k}", ha="center", va="top", fontsize=7, color=U.INK2, transform=ax.get_xaxis_transform())
        ax.set_xlim(0, xmax)
        if site != "S1":
            ax.set_ylim(-0.25, 1.35)
        ax.set_xlabel("dose α (absolute; fraction of ‖h_B − h_A‖ planted per position)")
        ax.set_ylabel("LO shift toward the planted candidate\n/ reader's own natural A→B separation (median, IQR band)" if site == "S2" else "shift / own natural separation")
        ax.set_title(f"{SITE_LABELS.get(site, site)}\nα* for {nflip}/{len(w.items)} states" + ("" if nflip else " — nothing flips, reader-side only"), fontsize=9.5 if site == "S2" else 8.5)
        ax.grid(axis="y", color=U.GRID, lw=0.8); ax.set_axisbelow(True)
        ax.legend(fontsize=7.5 if site == "S2" else 6.5, loc="upper left")
    fig.suptitle("X2 re-analysis R1: reader LO shift as a fraction of the reader's OWN natural separation of the pair (frame of the source state)\n"
                 f"{len(w.items)} source states / {len({p for p, _ in w.items})} pairs per dose; at S2/S3 α = 1 the edited state is the other state, so the fraction is 1 by construction",
                 y=1.02, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------------------
# markdown
# --------------------------------------------------------------------------------------
def write_md(path: Path, summary: dict, w: World) -> None:
    S2 = summary["fraction_median"].get("S2", {})
    cond = summary["conditional"]
    lines = [f"# R1 — X2 renormalised by each reader's own natural separation ({summary['date']})",
             "Fraction =(LO shift toward the planted candidate) / (the reader's natural A→B separation of the same pair, frame of the source state); "
             "the model's first-token LO is treated the same way. At S2/S3 α = 1 the edited state *is* the other state, so the fraction is 1 by construction "
             f"(observed medians at α = 1: S2 {', '.join(f'{READER_LABELS[rd]} {S2.get(rd, {}).get('1.0', float('nan')):.3f}' for rd in list(w.readers) + [MODEL])}).", "",
             "| S2 median fraction (IQR) | " + " | ".join(f"α {a}" for a in summary["alphas"].get("S2", [])) + " |",
             "|---|" + "---|" * len(summary["alphas"].get("S2", []))]
    for rd in list(w.readers) + [MODEL]:
        cells = []
        for a in summary["alphas"].get("S2", []):
            r = summary["fraction"].get("S2", {}).get(rd, {}).get(str(a), {})
            cells.append(f"{r.get('median', float('nan')):.2f} [{r.get('q25', float('nan')):.2f}, {r.get('q75', float('nan')):.2f}]")
        lines.append(f"| {READER_LABELS[rd]} | " + " | ".join(cells) + " |")
    lines += ["", "| win at α* (S2) | pair ordered (sep > 0, X1 E1) | pair misordered | both states ordered (lo_own > 0 twice) | not both |", "|---|---|---|---|---|"]

    def cell(r: dict) -> str:
        return f"{r.get('k', 0)}/{r.get('n', 0)} = {100 * r.get('win', float('nan')):.0f}% [{100 * r.get('lo', float('nan')):.0f}, {100 * r.get('hi', float('nan')):.0f}]" if r.get("n") else "0/0"

    for rd in w.readers:
        c = cond.get("S2", {}).get(rd, {})
        lines.append(f"| {READER_LABELS[rd]} | {cell(c.get('pair', {}).get('yes', {}))} | {cell(c.get('pair', {}).get('no', {}))} | {cell(c.get('both', {}).get('yes', {}))} | {cell(c.get('both', {}).get('no', {}))} |")
    ms = summary["model_signwin"].get("S2", {})
    lines += [("Natural separation exactly 0 (quantised tie, excluded from fractions, counted as misordered): " +
               "; ".join(f"{READER_LABELS[rd]} {t}" for rd, t in summary["natural_sep_ties"].items() if t) + ". " if any(summary["natural_sep_ties"].values()) else "") +
              "Model's own sub-flip sign-win at S2 (P(lo_model shift > 0) over states whose α* lies above the dose): " +
              "; ".join(f"α {a}: {v['k']}/{v['n']} = {100 * v['signwin']:.0f}%" for a, v in ms.items() if v["n"]) + ".", ""]
    sp = summary["s1_otherpair"]
    mf = sp.get("model_flips", {})
    mrow = sp.get("rows", {}).get(MODEL, {})
    s1f = summary["fraction"].get("S1", {})
    s1_max = max(summary["alphas"].get("S1", [S1_PREVIEW_ALPHA]))
    s1_txt = "; ".join(f"{READER_LABELS[rd]} {s1f.get(rd, {}).get(str(S1_PREVIEW_ALPHA), {}).get('median', float('nan')):.2f} / {s1f.get(rd, {}).get(str(s1_max), {}).get('median', float('nan')):.2f}"
                       for rd in list(w.readers) + [MODEL])
    lines += [f"| S1 (L38 last token) α = {S1_PREVIEW_ALPHA}, mean LO shift [95% pair-boot] — reader-side preview only: NOTHING FLIPS at S1 (planted {mf.get('planted', '?')}, "
              f"null {mf.get('null', '?')}, other-pair {mf.get('null_other', '?')}; model lo_model mean shift planted {mrow.get('planted', {}).get('mean_shift', float('nan')):+.2f}, "
              f"other-pair {mrow.get('null_other', {}).get('mean_shift', float('nan')):+.2f}). Median fraction of own separation at α {S1_PREVIEW_ALPHA} / α {s1_max}: {s1_txt} "
              f"— the readers report the planted candidate at the last token while the model's own log-odds barely move | planted (own pair) | other-pair direction | isotropic null |", "|---|---|---|---|"]
    for rd in w.readers:
        cells = []
        for cond_ in ("planted", "null_other", "null"):
            r = sp.get("rows", {}).get(rd, {}).get(cond_, {})
            cells.append(f"{r.get('mean_shift', float('nan')):+.3f} [{r.get('mean_lo', float('nan')):+.3f}, {r.get('mean_hi', float('nan')):+.3f}] (sign-win {100 * r.get('signwin_p', float('nan')):.0f}%)" if r else "–")
        lines.append(f"| {READER_LABELS[rd]} | " + " | ".join(cells) + " |")
    lines += ["", "**Corrected reading (writeup Corrections §1).** At the site where the edit flips the model, every reader's score moves in proportion to the "
              "interpolation, exactly as its X1 separation predicts; this does not distinguish \"follows the binding\" from \"reads the interpolated state\", and because "
              "A/B are token permutations the all-position swap also plants token identity at every name position.",
              f"Files: `x/friday/r1_fraction.csv`, `r1_conditional.csv`, `r1_model_signwin.csv`, `r1_s1_otherpair.csv`, `r1_summary.json`; `x2/fig_fraction.png`, `x2/per_pair.csv`. "
              f"follow.csv cross-check: {summary['follow_crosscheck']}."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def run(beh_path: Path | str = DEFAULT_BEH, lo_path: Path | str = DEFAULT_LO, out_friday: Path | str = DEFAULT_OUT_FRIDAY, out_x2: Path | str = DEFAULT_OUT_X2,
        follow_csv: Optional[Path | str] = DEFAULT_FOLLOW, n_boot: int = U.N_BOOT, seed: int = U.SEED, make_figure: bool = True, log_path: Optional[Path | str] = None) -> dict:
    out_friday, out_x2 = Path(out_friday), Path(out_x2)
    out_friday.mkdir(parents=True, exist_ok=True); out_x2.mkdir(parents=True, exist_ok=True)
    w = load_world(beh_path, lo_path)
    U.log(f"[r1] {len(w.beh)} behaviour rows, {len(w.items)} states / {len({p for p, _ in w.items})} pairs, sites {w.sites}, readers {w.readers}")
    astar_by_site = {s: alpha_star(w, s) for s in w.sites}

    frac_rows, _ = fraction_table(w)
    cond_rows = conditional_table(w, astar_by_site, n_boot, seed)
    sign_rows = model_signwin_table(w, astar_by_site, n_boot, seed)
    pp_rows = per_pair_table(w, astar_by_site, "S2" if "S2" in w.sites else w.sites[0])
    s1_rows = s1_otherpair_table(w, n_boot, seed)
    xc = crosscheck_follow(w, Path(follow_csv) if follow_csv else None, astar_by_site)

    # sanity: fraction at alpha 1 at S2/S3
    sanity = {}
    for site in ("S2", "S3"):
        for r in frac_rows:
            if r["site"] == site and r["alpha"] == 1.0:
                sanity[f"{site}|{r['reader']}"] = r["median"]
                flag = "" if abs(r["median"] - 1.0) < 0.05 else "  <-- NOT ~1, check the frame"
                U.log(f"[r1] sanity {site} alpha 1.0 {READER_LABELS[r['reader']]}: median fraction {r['median']:.4f} (IQR {r['q25']:.3f}..{r['q75']:.3f}, n {r['n']}){flag}")
    for r in frac_rows:
        if r["site"] == "S2":
            U.log(f"[r1] S2 alpha {r['alpha']}: {READER_LABELS[r['reader']]:14s} median {r['median']:.3f} [{r['q25']:.3f}, {r['q75']:.3f}] n {r['n']} sign-win {r['signwin']:.2f}")
    for r in cond_rows:
        if r["site"] == "S2":
            U.log(f"[r1] S2 win at alpha* | ordered[{r['definition']}]={r['ordered']}: {READER_LABELS[r['reader']]:14s} {r['k']}/{r['n']} = {100 * r['win']:.1f}% [{100 * r['lo']:.0f}, {100 * r['hi']:.0f}]")
    ties = {rd: sorted({it[0] for it, s in separation(w, rd).items() if s == 0}) for rd in w.readers}
    for rd, t in ties.items():
        if t:
            U.log(f"[r1] {READER_LABELS[rd]}: natural separation exactly 0 (quantised tie) for pairs {t}; excluded from fractions, counted as not ordered")
    for r in s1_rows:
        U.log(f"[r1] S1 a{r['alpha']} {r['condition']:10s} {READER_LABELS[r['reader']]:14s} mean {r['mean_shift']:+.3f} [{r['mean_lo']:+.3f}, {r['mean_hi']:+.3f}] "
              f"median {r['median_shift']:+.3f} sign-win {r['signwin_k']}/{r['n']} flips {r['model_flips_k']}/{r['model_flips_n']}")

    summary: Dict[str, Any] = {
        "module": "x_friday_r1", "date": dt.date.today().isoformat(), "inputs": {"behaviour": str(beh_path), "lo": str(lo_path), "n_behaviour_rows": len(w.beh)},
        "n_items": len(w.items), "n_pairs": len({p for p, _ in w.items}), "readers": w.readers, "sites": w.sites, "n_boot": n_boot, "seed": seed,
        "definition": {"fraction": "(lo_toward_other(entry) - lo_toward_other(natural, same state)) / sep",
                       "sep": "(-lo_toward_other(natural, OTHER state)) - lo_toward_other(natural, this state) = lo_own(A) + lo_own(B)",
                       "model": "same with lo_model = lp_first_B - lp_first_A", "ordered": "natural lo_own > 0 in both states of the pair",
                       "alpha_star": "smallest ladder alpha with flipped_to_other and coherent (analyze.py E5)",
                       "subflip_alpha": "largest ladder alpha < alpha*; subflip_alpha_z = analyze.py's dose (|z_model| < 2 vs the isotropic nulls)"},
        "alphas": {s: w.alphas(s) for s in w.sites},
        "sanity_fraction_at_alpha_1": sanity,
        "fraction": {s: {rd: {str(r["alpha"]): {k: r[k] for k in ("median", "q25", "q75", "n", "signwin", "median_raw_shift")} for r in frac_rows if r["site"] == s and r["reader"] == rd}
                         for rd in list(w.readers) + [MODEL]} for s in w.sites},
        "fraction_median": {s: {rd: {str(r["alpha"]): r["median"] for r in frac_rows if r["site"] == s and r["reader"] == rd} for rd in list(w.readers) + [MODEL]} for s in w.sites},
        "ordering_definitions": {"both": "natural lo_own > 0 in both states of the pair (literal per-state criterion; defeated by any constant candidate bias)",
                                 "pair": "within-pair contrast sep = lo_own(A) + lo_own(B) > 0 (X1 E1 paired win on this pair); headline definition"},
        "conditional": {s: {rd: {d: {r["ordered"]: {k: r[k] for k in ("k", "n", "win", "lo", "hi", "n_pairs", "n_pairs_ordered_total")}
                                     for r in cond_rows if r["site"] == s and r["reader"] == rd and r["definition"] == d} for d in ORDER_DEFS}
                            for rd in list(w.readers) + [MODEL]} for s in w.sites},
        "natural_sep_ties": {rd: t for rd, t in ties.items()},
        "n_states_sep_positive": {rd: sum(1 for s_ in separation(w, rd).values() if s_ is not None and s_ > 0) for rd in list(w.readers) + [MODEL]},
        "model_signwin": {s: {str(r["alpha"]): {k: r[k] for k in ("k", "n", "signwin", "lo", "hi")} for r in sign_rows if r["site"] == s and r["scope"] == "below_alpha_star"} for s in w.sites},
        "model_signwin_all_items": {s: {str(r["alpha"]): {k: r[k] for k in ("k", "n", "signwin", "lo", "hi")} for r in sign_rows if r["site"] == s and r["scope"] == "all_items"} for s in w.sites},
        "alpha_star_counts": {s: {str(a): sum(1 for v in astar_by_site[s].values() if v == a) for a in w.alphas(s)} | {"no_flip": sum(1 for v in astar_by_site[s].values() if v is None)} for s in w.sites},
        "s1_otherpair": {"note": f"S1 (L38, last token) alpha {S1_PREVIEW_ALPHA}: NOTHING FLIPS at S1 (see model_flips), so this is a reader-side preview of the other-pair null only, "
                                 "not a test of following; the behavioural other-pair null belongs at S2 (Y2).",
                         "model_flips": {r["condition"]: f"{r['model_flips_k']}/{r['model_flips_n']}" for r in s1_rows if r["reader"] == MODEL},
                         "other_pair_over_planted_mean": {rd: (next((r["mean_shift"] for r in s1_rows if r["reader"] == rd and r["condition"] == "null_other"), float("nan")) /
                                                               next((r["mean_shift"] for r in s1_rows if r["reader"] == rd and r["condition"] == "planted"), float("nan")))
                                                          for rd in list(w.readers) + [MODEL] if any(r["reader"] == rd and r["condition"] == "planted" and r["mean_shift"] for r in s1_rows)},
                         "rows": {rd: {r["condition"]: {k: r[k] for k in r if k not in ("reader", "site", "condition")} for r in s1_rows if r["reader"] == rd} for rd in list(w.readers) + [MODEL]}},
        "follow_crosscheck": xc,
        "corrected_reading": "At the site where the edit flips the model, every reader's score moves in proportion to the interpolation, exactly as its X1 separation "
                             "predicts; this does not distinguish 'follows the binding' from 'reads the interpolated state', and because A/B are token permutations the "
                             "all-position swap also plants token identity at every name position.",
        "files": {"r1_fraction": str(out_friday / "r1_fraction.csv"), "r1_conditional": str(out_friday / "r1_conditional.csv"), "r1_model_signwin": str(out_friday / "r1_model_signwin.csv"),
                  "r1_s1_otherpair": str(out_friday / "r1_s1_otherpair.csv"), "R1_md": str(out_friday / "R1.md"), "fig_fraction": str(out_x2 / "fig_fraction.png"), "per_pair": str(out_x2 / "per_pair.csv")},
    }
    U.write_csv(out_friday / "r1_fraction.csv", frac_rows)
    U.write_csv(out_friday / "r1_conditional.csv", cond_rows)
    U.write_csv(out_friday / "r1_model_signwin.csv", sign_rows)
    U.write_csv(out_friday / "r1_s1_otherpair.csv", s1_rows)
    U.write_csv(out_x2 / "per_pair.csv", pp_rows)
    if make_figure:
        make_fig(out_x2 / "fig_fraction.png", w, frac_rows, astar_by_site)
    U.write_json(out_friday / "r1_summary.json", summary)
    write_md(out_friday / "R1.md", summary, w)
    if log_path is not None:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"- {dt.datetime.now(dt.timezone.utc).isoformat()} x_friday_r1 (CPU re-analysis, no new compute): n_boot={n_boot} seed={seed}; "
                    f"wrote {out_friday}/r1_*.csv, r1_summary.json, R1.md and {out_x2}/fig_fraction.png, per_pair.csv ({len(pp_rows)} rows); follow.csv cross-check {xc}\n")
    U.log(f"[r1] wrote {out_friday} and {out_x2}/{{fig_fraction.png, per_pair.csv}}")
    return summary


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--behaviour", default=str(DEFAULT_BEH))
    ap.add_argument("--lo", default=str(DEFAULT_LO))
    ap.add_argument("--follow", default=str(DEFAULT_FOLLOW))
    ap.add_argument("--out-friday", default=str(DEFAULT_OUT_FRIDAY))
    ap.add_argument("--out-x2", default=str(DEFAULT_OUT_X2))
    ap.add_argument("--n-boot", type=int, default=U.N_BOOT)
    ap.add_argument("--seed", type=int, default=U.SEED)
    ap.add_argument("--no-fig", action="store_true")
    ap.add_argument("--log", default=str(DEFAULT_OUT_X2 / "log.md"))
    return ap.parse_args(argv)


def main(argv=None) -> dict:
    a = parse_args(argv)
    return run(a.behaviour, a.lo, a.out_friday, a.out_x2, a.follow, a.n_boot, a.seed, not a.no_fig, a.log)


if __name__ == "__main__":
    main()
