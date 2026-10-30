"""Shared pieces of the V6 / V7 analyses: the within-pair win, pair-bootstrap rates and paired differences, run metadata.

Orientation (as in x1_bank/analyze.py E1 and every S3 row): ``lo_own`` = score(own answer of the state) − score(other candidate).
Within a pair the two states have opposite own answers, so a reader separates the pair in a fixed frame iff
    lo_own(A) + lo_own(B) > 0           (ties and missing / unscorable rows do not win; a pair with a missing side is excluded).
Rates are over pairs with a pair-level bootstrap (resample pairs, N_BOOT = 1,000, seed 0, 95 % percentile CI) and a Wilson CI.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.stats import wilson  # noqa: E402
from projects.g_agreement.core import analysis_utils as U  # noqa: E402

N_BOOT = 1000
SEED = 0
RESULTS_V = ROOT / "results" / "g_agreement" / "v"
W_CACHE = ROOT / "cache" / "g_agreement" / "w"
BANK_W = ROOT / "projects" / "g_agreement" / "banks" / "w"

Flag = Tuple[str, Optional[bool]]


# ------------------------------------------------------------------ win logic
def pair_win(lo_a: Optional[float], lo_b: Optional[float]) -> Optional[bool]:
    """Within-pair win in the ownership frame: lo_own(A) + lo_own(B) > 0; None when a side is missing."""
    if lo_a is None or lo_b is None:
        return None
    return bool(float(lo_a) + float(lo_b) > 0)


def pair_margin(lo_a: Optional[float], lo_b: Optional[float]) -> Optional[float]:
    if lo_a is None or lo_b is None:
        return None
    return float(lo_a) + float(lo_b)


def win_flags(lo_by_pair: Mapping[str, Mapping[str, Optional[float]]], sides: Tuple[str, str] = ("A", "B")) -> List[Flag]:
    """{pair_id: {side: lo_own}} → [(pair_id, win | None)] in sorted pair order."""
    a, b = sides
    return [(pid, pair_win(d.get(a), d.get(b))) for pid, d in sorted(lo_by_pair.items())]


def margins(lo_by_pair: Mapping[str, Mapping[str, Optional[float]]], sides: Tuple[str, str] = ("A", "B")) -> Dict[str, float]:
    a, b = sides
    out = {}
    for pid, d in sorted(lo_by_pair.items()):
        m = pair_margin(d.get(a), d.get(b))
        if m is not None:
            out[pid] = m
    return out


# ------------------------------------------------------------------ rates
def rate(flags: Sequence[Flag], n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    """k/n over the non-None flags, pair-bootstrap CI (U.pair_rate) and Wilson CI."""
    r = U.pair_rate(list(flags), n_boot=n_boot, seed=seed)
    _, wlo, whi = wilson(r.k, r.n) if r.n else (float("nan"),) * 3
    return {"k": int(r.k), "n": int(r.n), "p": float(r.p), "boot_lo": float(r.lo), "boot_hi": float(r.hi), "wilson_lo": float(wlo), "wilson_hi": float(whi),
            "n_pairs": int(r.n_pairs), "n_excluded": int(sum(1 for _, f in flags if f is None))}


def rate_diff(flags_a: Sequence[Flag], flags_b: Sequence[Flag], n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    """a − b with the SAME pairs resampled (U.pair_rate_diff); ``excludes_zero`` = the 95 % CI does not contain 0."""
    est, lo, hi = U.pair_rate_diff(list(flags_a), list(flags_b), n_boot=n_boot, seed=seed)
    return {"diff": float(est), "lo": float(lo), "hi": float(hi), "excludes_zero": bool(np.isfinite(lo) and np.isfinite(hi) and (lo > 0 or hi < 0))}


def pair_mean(values: Mapping[str, Sequence[float]], n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, Any]:
    """Mean of per-state values tagged by pair ({pair_id: [v, ...]}), pair-bootstrap CI of the mean."""
    vals = {p: [float(v) for v in vs] for p, vs in values.items() if len(vs)}
    pids = sorted(vals)
    n = sum(len(v) for v in vals.values())
    if n == 0:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0}

    def stat(ps: Sequence[str]) -> float:
        xs = [v for p in ps for v in vals[p]]
        return float(np.mean(xs)) if xs else float("nan")

    est, lo, hi = U.pair_bootstrap_stat(pids, stat, n_boot=n_boot, seed=seed)
    return {"mean": float(est), "lo": float(lo), "hi": float(hi), "n": int(n)}


# ------------------------------------------------------------------ formatting / metadata
def pct(x: Optional[float]) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{100 * x:.1f}"


def fmt_rate(r: Mapping[str, Any]) -> str:
    if not r["n"]:
        return "0/0 (no rows)"
    return f"{r['k']}/{r['n']} = {pct(r['p'])}% boot[{pct(r['boot_lo'])}, {pct(r['boot_hi'])}] wilson[{pct(r['wilson_lo'])}, {pct(r['wilson_hi'])}]"


def fmt_diff(d: Mapping[str, Any]) -> str:
    if not np.isfinite(d["diff"]):
        return "n/a"
    return f"{100 * d['diff']:+.1f} [{100 * d['lo']:+.1f}, {100 * d['hi']:+.1f}]"


def fmt_signed(x: Optional[float], nd: int = 2) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:+.{nd}f}"


def sha256_file(path: Path) -> Optional[str]:
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_meta(inputs: Mapping[str, Path], n_boot: int, seed: int, argv: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    return {"run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "n_boot": int(n_boot), "seed": int(seed),
            "command": " ".join([sys.executable.rsplit("/", 1)[-1], "-m", *(argv if argv is not None else sys.argv)]),
            "inputs": {k: {"path": str(p), "sha256": sha256_file(p), "exists": Path(p).exists()} for k, p in inputs.items()}}


def require_files(paths: Iterable[Path]) -> None:
    missing = [str(p) for p in paths if not Path(p).exists()]
    if missing:
        raise FileNotFoundError("input file(s) missing — nothing written: " + ", ".join(missing))


def read_jsonl(path: Path) -> List[dict]:
    return U.load_jsonl(path)
