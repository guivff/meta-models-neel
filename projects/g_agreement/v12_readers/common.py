"""Shared loaders and statistics for V1/V2 (PREREG_WV.md Part V; statistics rules of BRIEF_Z).

Reader rows (native two-candidate log-odds) come from three files with one schema after normalisation:
  cache/g_agreement/x/x3_lo.jsonl   block-42 LAST-token states of the X3 capture (readers jlens/olens/nla) -> site "42:0"
  cache/g_agreement/y/y1_lo.jsonl   Y1 re-read rows (site "48:0" and "42:candA"; readers jlens/olens/olens_trueL/nla)
  --extra-lo <file>                 pod rows in the y1_lo schema (site "<L>:0") once the V1 arm has run
``lo_actual = lp(cand_actual) - lp(cand_other)``; ``favours_actual`` = lo > 0; ``favours_other`` = lo < 0; lo == 0 is a tie
and is counted in neither (reported). Unscorable rows (J-lens candidates without a single-token variant) are excluded
from numerator and denominator.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
G_DIR = ROOT / "projects" / "g_agreement"
CACHE = ROOT / "cache" / "g_agreement"
RESULTS = ROOT / "results" / "g_agreement"

DEFAULTS: Dict[str, Path] = {
    "items": G_DIR / "dataset" / "items_y1_selected.json",
    "x3_lo": CACHE / "x" / "x3_lo.jsonl",
    "y1_lo": CACHE / "y" / "y1_lo.jsonl",
    "caps_dir": CACHE / "y" / "y1_caps",
    "sweep_dir": RESULTS / "y1",            # sweep_<set>.csv (E10 probe) and logitlens.csv
    "out_dir": RESULTS / "v",
    "frozen_wv": G_DIR / "manifest" / "frozen_config_wv.json",
}

READERS: Tuple[str, ...] = ("jlens", "olens", "nla")
READER_LABELS = {"jlens": "J-lens (native)", "olens": "Oracle Lens (nearest grid layer)", "olens_trueL": "Oracle Lens (true layer)",
                 "nla": "NLA (transfer from L42)", "probe": "E10 held-out probe", "logit_lens": "logit lens"}
LAYERS: Tuple[int, ...] = tuple(range(42, 63, 2))
OLENS_GRID: Tuple[int, ...] = (44, 48, 52, 56, 60)
MAIN_SETS: Tuple[str, ...] = ("error", "disagree")
CONTROL_OF = {"error": "error_control", "disagree": "agree_control"}
N_BOOT, N_PERM, SEED = 1000, 200, 0
PRESENT_WIN = 0.75     # V1: a reader "crosses" at the first layer with P(favours actual) >= 0.75
RESOLVE_GAP = 0.15     # V2: "re-solves" if P(correct) - P(actual) >= 0.15 with the CI excluding 0


def nearest_grid_layer(layer: int, grid: Sequence[int] = OLENS_GRID) -> int:
    """Same rule as y1_site.collect.nearest_grid_layer (ties -> the lower layer)."""
    return min(grid, key=lambda g: (abs(g - layer), g))


# ------------------------------------------------------------------ items
def _as_dict(v: Any) -> Any:
    if isinstance(v, str) and v[:1] in "{[":
        import ast
        try:
            return ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return v
    return v


def load_items(path: Path | str) -> Tuple[dict, Dict[str, dict]]:
    """items_y1_selected.json -> (meta, {item_id: item}) with the roles resolved under item["roles"]:
    actual (model's answer = cand A), other (cand B), correct (puzzles: source.correct), km1 (puzzles: trace[-2])."""
    obj = json.loads(Path(path).read_text())
    items = obj["items"] if isinstance(obj, dict) else obj
    out: Dict[str, dict] = {}
    for it in items:
        it = dict(it)
        it["primary"] = _as_dict(it.get("primary"))
        it["source"] = _as_dict(it.get("source"))
        it["roles"] = item_roles(it)
        out[it["item_id"]] = it
    return (obj.get("meta", {}) if isinstance(obj, dict) else {}), out


def item_roles(item: Mapping[str, Any]) -> Dict[str, Optional[str]]:
    p = item.get("primary") or {}
    src = item.get("source") or {}
    cands = list(p.get("candidates") or [])
    actual = p.get("answer")
    other = next((c for c in cands if c != actual), None)
    correct = src.get("correct") if isinstance(src, Mapping) else None
    trace = src.get("trace") if isinstance(src, Mapping) else None
    km1 = trace[-2] if isinstance(trace, list) and len(trace) >= 2 else None
    return {"actual": actual, "other": other, "correct": correct, "km1": km1, "candidates": cands}


def check_item_roles(items: Mapping[str, dict]) -> Dict[str, int]:
    """ERROR: other == correct and actual != correct. ERROR_CONTROL: actual == correct. Raises on a violation."""
    bad = []
    counts = {"error": 0, "error_control": 0, "km1_eq_actual": 0, "km1_ne_actual": 0}
    for iid, it in items.items():
        r, s = it["roles"], it.get("set")
        if s == "error":
            counts["error"] += 1
            if r["other"] != r["correct"] or r["actual"] == r["correct"]:
                bad.append((iid, s, r))
            counts["km1_eq_actual" if r["km1"] == r["actual"] else "km1_ne_actual"] += 1
        elif s == "error_control":
            counts["error_control"] += 1
            if r["actual"] != r["correct"]:
                bad.append((iid, s, r))
    if bad:
        raise ValueError(f"{len(bad)} items violate the set/candidate construction, e.g. {bad[:3]}")
    return counts


# ------------------------------------------------------------------ LO rows
def read_jsonl(path: Path | str) -> List[dict]:
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalise_row(r: Mapping[str, Any], source: str) -> Optional[dict]:
    """One reader row -> the common schema, or None for mean-state / malformed rows."""
    if "item_id" not in r or r.get("condition") or "reader" not in r:
        return None
    if "site" in r and r["site"]:
        site = str(r["site"])
        layer_s, pos = site.split(":")
        layer = int(r.get("layer", layer_s))
        pos = str(r.get("position", pos))
    else:  # x3_lo rows: block-42 last token, no site field
        layer = int(r.get("layer", 42))
        pos = "0"
        site = f"{layer}:{pos}"
    lo = r.get("lo_actual")
    unscorable = bool(r.get("unscorable")) or lo is None or (isinstance(lo, float) and not math.isfinite(lo))
    layer_used = r.get("layer_used")
    if layer_used is None and source == "x3_lo" and r["reader"] in ("jlens", "olens"):
        layer_used = layer
    return {"reader": r["reader"], "site": site, "layer": layer, "position": pos, "layer_used": layer_used,
            "layer_role": r.get("layer_role"), "item_id": r["item_id"], "set": r.get("set"), "family": r.get("family"),
            "cand_actual": r.get("cand_actual"), "cand_other": r.get("cand_other"),
            "lo_actual": (None if unscorable else float(lo)), "unscorable": unscorable, "source": source}


def load_lo_rows(x3_lo: Optional[Path | str], y1_lo: Optional[Path | str], extra: Sequence[Path | str] = (),
                 items: Optional[Mapping[str, dict]] = None) -> Tuple[List[dict], Dict[str, Any]]:
    """Normalised rows keyed (reader, site, item_id); later sources override earlier ones (x3 < y1 < extra) and the
    overlap is checked (sign agreement of lo_actual reported in the returned info)."""
    by: Dict[Tuple[str, str, str], dict] = {}
    info: Dict[str, Any] = {"sources": [], "overrides": 0, "override_sign_agree": 0, "dropped_not_in_items": 0}
    srcs = []
    if x3_lo and Path(x3_lo).exists():
        srcs.append(("x3_lo", x3_lo))
    if y1_lo and Path(y1_lo).exists():
        srcs.append(("y1_lo", y1_lo))
    srcs += [(f"extra:{Path(p).name}", p) for p in extra]
    for name, p in srcs:
        n = 0
        for raw in read_jsonl(p):
            r = normalise_row(raw, name)
            if r is None:
                continue
            if items is not None:
                if r["item_id"] not in items:
                    info["dropped_not_in_items"] += 1
                    continue
                r["set"] = items[r["item_id"]].get("set", r["set"])
            k = (r["reader"], r["site"], r["item_id"])
            if k in by:
                old = by[k]
                info["overrides"] += 1
                if old["lo_actual"] is not None and r["lo_actual"] is not None and (old["lo_actual"] > 0) == (r["lo_actual"] > 0):
                    info["override_sign_agree"] += 1
                r["superseded"] = old["source"]
            by[k] = r
            n += 1
        info["sources"].append({"source": name, "path": str(p), "n_rows": n})
    return list(by.values()), info


def select_rows(rows: Iterable[dict], *, reader: Optional[str] = None, set_: Optional[str] = None, layer: Optional[int] = None,
                position: Optional[str] = "0") -> List[dict]:
    out = []
    for r in rows:
        if reader is not None and r["reader"] != reader:
            continue
        if set_ is not None and r["set"] != set_:
            continue
        if layer is not None and r["layer"] != layer:
            continue
        if position is not None and r["position"] != position:
            continue
        out.append(r)
    return out


def scored_layers(rows: Iterable[dict], reader: str, set_: str, position: str = "0") -> List[int]:
    return sorted({r["layer"] for r in select_rows(rows, reader=reader, set_=set_, position=position) if not r["unscorable"]})


# ------------------------------------------------------------------ statistics
def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def rate(flags: Sequence[bool], n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, float]:
    """Item-bootstrap 95% CI (percentile, ``n_boot`` resamples, seed) and the Wilson interval of a rate."""
    f = np.asarray(list(flags), dtype=float)
    n, k = int(f.size), int(f.sum())
    if n == 0:
        return {"k": 0, "n": 0, "p": float("nan"), "boot_lo": float("nan"), "boot_hi": float("nan"),
                "wilson_lo": float("nan"), "wilson_hi": float("nan")}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boots = f[idx].mean(axis=1)
    wlo, whi = wilson(k, n)
    return {"k": k, "n": n, "p": k / n, "boot_lo": float(np.quantile(boots, 0.025)), "boot_hi": float(np.quantile(boots, 0.975)),
            "wilson_lo": wlo, "wilson_hi": whi}


def paired_diff(a: Sequence[bool], b: Sequence[bool], n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, float]:
    """mean(a) - mean(b) over the same items with a paired item bootstrap (same resample indices)."""
    a = np.asarray(list(a), dtype=float)
    b = np.asarray(list(b), dtype=float)
    if a.size != b.size:
        raise ValueError("paired_diff needs equal-length aligned flags")
    n = a.size
    if n == 0:
        return {"diff": float("nan"), "diff_lo": float("nan"), "diff_hi": float("nan")}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    d = a[idx].mean(axis=1) - b[idx].mean(axis=1)
    return {"diff": float(a.mean() - b.mean()), "diff_lo": float(np.quantile(d, 0.025)), "diff_hi": float(np.quantile(d, 0.975))}


def two_way_stat(lo: np.ndarray) -> float:
    """P(favours other) - P(favours actual) over all items (ties count in neither)."""
    if lo.size == 0:
        return float("nan")
    return float((lo < 0).mean() - (lo > 0).mean())


def permutation_null(lo: Sequence[float], n_perm: int = N_PERM, seed: int = SEED,
                     stat: Callable[[np.ndarray], float] = two_way_stat) -> Dict[str, float]:
    """Shuffle the candidate labels within each item: with two candidates that is an independent sign flip of each
    item's log-odds. Two-sided p = P(|stat_null| >= |stat_obs|) with the +1 correction; also the null's 95th
    percentile of |stat| and its mean."""
    x = np.asarray(list(lo), dtype=float)
    obs = stat(x)
    if x.size == 0:
        return {"obs": obs, "p_value": float("nan"), "null_abs_p95": float("nan"), "null_mean": float("nan"), "n_perm": n_perm}
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for i in range(n_perm):
        s = rng.choice([-1.0, 1.0], size=x.size)
        null[i] = stat(x * s)
    p = (1 + int((np.abs(null) >= abs(obs) - 1e-12).sum())) / (n_perm + 1)
    return {"obs": obs, "p_value": float(p), "null_abs_p95": float(np.quantile(np.abs(null), 0.95)),
            "null_mean": float(null.mean()), "n_perm": n_perm}


def first_crossing(curve: Mapping[int, Mapping[str, float]], thresh: float = PRESENT_WIN, key: str = "p") -> Optional[int]:
    """Smallest layer whose point estimate >= thresh; None when none does."""
    for L in sorted(curve):
        v = curve[L].get(key)
        if v is not None and not (isinstance(v, float) and math.isnan(v)) and v >= thresh:
            return L
    return None


# ------------------------------------------------------------------ reference curves (Y1 outputs)
def probe_curve(sweep_csv: Path | str, position: str = "0") -> Dict[int, dict]:
    """E10 held-out probe favours-actual rate per layer at one position from results/g_agreement/y1/sweep_<set>.csv."""
    out: Dict[int, dict] = {}
    p = Path(sweep_csv)
    if not p.exists():
        return out
    with open(p) as fh:
        for r in csv.DictReader(fh):
            if str(r.get("position")) != position or r.get("status") not in (None, "", "ok"):
                continue
            L = int(r["layer"])
            out[L] = {"p": float(r["rate"]), "boot_lo": float(r["boot_lo"]), "boot_hi": float(r["boot_hi"]), "n": int(r["n"]),
                      "k": int(r["k"]), "perm_p95": float(r["perm_p95"]) if r.get("perm_p95") else float("nan"),
                      "control_rate": float(r["control_rate"]) if r.get("control_rate") else float("nan")}
    return out


def logitlens_curve(ll_csv: Path | str, set_: str) -> Dict[int, dict]:
    """Fraction of items whose logit-lens margin lp(actual) - lp(other) > 0 per layer (final block flagged)."""
    out: Dict[int, dict] = {}
    p = Path(ll_csv)
    if not p.exists():
        return out
    with open(p) as fh:
        for r in csv.DictReader(fh):
            if r["set"] != set_:
                continue
            out[int(r["layer"])] = {"p": float(r["frac_pos"]), "boot_lo": float(r["boot_lo"]), "boot_hi": float(r["boot_hi"]),
                                    "n": int(r["n"]), "is_final": str(r.get("is_final_layer")).lower() == "true"}
    return out


# ------------------------------------------------------------------ io
def write_csv(path: Path | str, rows: Sequence[Mapping[str, Any]], columns: Optional[Sequence[str]] = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    cols = list(columns) if columns else list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None or (isinstance(r.get(c), float) and math.isnan(r[c])) else r.get(c)) for c in cols})


def fmt_rate(d: Mapping[str, float]) -> str:
    if not d or d.get("n", 0) == 0:
        return "n/a"
    return f"{d['k']}/{d['n']} = {100 * d['p']:.1f}% [{100 * d['boot_lo']:.0f}, {100 * d['boot_hi']:.0f}]"


def sha256_file(path: Path | str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
