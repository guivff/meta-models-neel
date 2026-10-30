"""Bridge — the 100 arithmetic prompts against Michael Kenney's numbers (PREREG_WV.md "bridge"; brief_wv.md "Bridge").

    python -m projects.g_agreement.w_analysis.bridge [--states-dir cache/g_agreement/w/states_L42] [--items projects/g_agreement/banks/w/items_w.json]
        [--s1 cache/g_agreement/w/s1_target.jsonl] [--s3 cache/g_agreement/w/s3_lo.jsonl] [--michael nla-consistency/data/arithmetic.jsonl]
        [--out results/g_agreement/w/bridge] [--n-boot 1000 --seed 0] [--no-probe]

Michael (nla-consistency, README "Result 2"; scripts/thread12_pod.py ``probe``, scripts/t12_eval.py ``report``, notebook "Result 2"):
600 "a ± b =" plain prompts read at "=" (layer 42 of Qwen3.6-27B); 5-fold softmax probes per digit (a_tens, a_units, b_tens,
b_units) on the activations standardised over ALL rows, folds ``Random(1).shuffle(idx); idx[i::5]``, LBFGS (max_iter 300,
strong Wolfe) on CE + 1e-3·‖W‖²; "probe exact" = both digits right (83–93 %). NLA: 2 readouts per prompt, the first
``(\\d+)\\s*([-−+])\\s*(\\d+)`` expression parsed; "NLA exact" among quoting readouts (a 5 %, b 38 %); his ``r`` is the Pearson
correlation between the true and the stated operand over quoting readouts (0.57 / 0.88). He states no CIs; this module recomputes
his statistics from ``data/arithmetic.jsonl`` with an item-level bootstrap (1,000 resamples, seed 0) and reports Spearman next to his r.

Ours: the same probe form (``w_directions.michael.fit_lr``) on the S1 layer-42 last-token ("=") states of the 100 warith items
(``cache/g_agreement/w/states_L42/<item_id>.pt``, fp32 [d]); a and b from the bank's ``construction``; exact-match for a and b with
item bootstrap and Wilson CIs, per-digit accuracy and the majority baseline as he prints them; Michael's 18 + 18 recipe
(``michael_subspaces``) fitted on all 100 states for the subspace ranks. NLA: in S3 phase B the NLA scores the S1 arith states only
through the native vector over ``candidates_all`` = the RESULT 0–198, so the exact-match reported there is for the result (and the
rates at which that argmax equals a or b, as a proxy); free-text NLA readouts of arith states were not sampled in S4, so the NLA
operand exact-match / r that Michael reports has no counterpart here and is stated as such. Each of our numbers is compared with his:
"within his 95 % CI" and "CIs overlap". Outputs results/g_agreement/w/bridge/{bridge.md, bridge.csv, bridge_summary.json}.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core.accounting import now_iso, read_jsonl
from projects.g_agreement.w_analysis.w2_precision import (_fmt, _json_default, argmax_candidate, item_bootstrap, pearson, rel, spearman, wilson)

W_CACHE = C.CACHE_DIR / "w"
STATES_L42 = W_CACHE / "states_L42"
S1_TARGET = W_CACHE / "s1_target.jsonl"
S3_LO = W_CACHE / "s3_lo.jsonl"
ITEMS_W = C.PROJECT_DIR / "banks" / "w" / "items_w.json"
MICHAEL = C.REPO_ROOT / "nla-consistency" / "data" / "arithmetic.jsonl"
OUT_DIR = C.RESULTS_DIR / "w" / "bridge"
N_BOOT, SEED = 1000, 0
N_FOLDS, FOLD_SHUFFLE_SEED = 5, 1  # thread12_pod.py probe(): random.Random(1).shuffle(idx); folds = [idx[i::5] ...]
EXPR = re.compile(r"(\d+)\s*([-−+])\s*(\d+)")  # t12_eval.py / notebook
TARGETS: Tuple[str, ...] = ("a_tens", "a_units", "b_tens", "b_units")
# Michael's stated numbers (README "Result 2"), used only to check that the recomputation from his file reproduces them.
MICHAEL_STATED = {"probe_exact_a": (0.83, 0.93), "probe_exact_b": (0.83, 0.93), "nla_exact_a": 0.05, "nla_exact_b": 0.38, "nla_pearson_a": 0.57, "nla_pearson_b": 0.88}


# ------------------------------------------------------------------ Michael's side (his 600-row release)
def parse_expr(text: Optional[str]) -> Optional[Tuple[int, str, int]]:
    """The first 'x op y' expression in an NLA readout, as in t12_eval.py (op '−' normalised to '-')."""
    if not text:
        return None
    m = EXPR.search(str(text))
    if not m:
        return None
    return int(m.group(1)), ("-" if m.group(2) == "−" else m.group(2)), int(m.group(3))


def michael_stats(rows: Sequence[dict], *, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Recompute his Result-2 numbers with item-level bootstrap CIs. Probe exact per prompt (his per-readout figure coincides: 2
    readouts per prompt); NLA exact / Pearson r / Spearman over quoting readouts, prompts resampled."""
    out: Dict[str, Any] = {"n_prompts": len(rows), "n_readouts": sum(len(r.get("nla_readouts") or []) for r in rows)}
    for op in ("a", "b"):
        prb = [{"item_id": r["id"], "true": int(r[op]), "reported": (int(r[op]) if (r[f"probe_{op}_tens"] == r[op] // 10 and r[f"probe_{op}_units"] == r[op] % 10) else -1)} for r in rows]
        st = item_bootstrap(prb, n_boot, seed)
        out[f"probe_exact_{op}"] = {k: st[k] for k in ("exact", "exact_lo", "exact_hi", "exact_wilson", "n_items")}
        nla = []
        for r in rows:
            for t in r.get("nla_readouts") or []:
                p = parse_expr(t)
                nla.append({"item_id": r["id"], "true": int(r[op]), "reported": (None if p is None else (p[0] if op == "a" else p[2]))})
        st = item_bootstrap(nla, n_boot, seed, with_pearson=True)
        # exact among QUOTING readouts (his denominator): rescale the pooled exact by the parsed share
        quoting = [x for x in nla if x["reported"] is not None]
        stq = item_bootstrap(quoting, n_boot, seed, with_pearson=True) if quoting else st
        out[f"nla_exact_{op}"] = {"exact": stq["exact"], "exact_lo": stq["exact_lo"], "exact_hi": stq["exact_hi"], "n_quoting": len(quoting), "n_readouts": len(nla),
                                  "exact_all_readouts": st["exact"]}
        out[f"nla_pearson_{op}"] = {"r": stq.get("pearson"), "lo": stq.get("pearson_lo"), "hi": stq.get("pearson_hi")}
        out[f"nla_spearman_{op}"] = {"rho": stq["spearman"], "lo": stq["spearman_lo"], "hi": stq["spearman_hi"]}
    for k in TARGETS:
        op, dig = k.split("_")
        y = [(int(r[op]) // 10 if dig == "tens" else int(r[op]) % 10) for r in rows]
        p = [r[f"probe_{k}"] for r in rows]
        out[f"probe_digit_{k}"] = {"acc": float(np.mean([a == b for a, b in zip(p, y)])), "majority": max(y.count(v) for v in set(y)) / len(y)}
    q = sum(1 for r in rows for t in (r.get("nla_readouts") or []) if parse_expr(t) is not None)
    out["nla_quote_rate"] = q / out["n_readouts"] if out["n_readouts"] else None
    out["model_next_starts_answer"] = float(np.mean([str(r["answer"]).startswith(str(r.get("model_next", "")).strip()) and str(r.get("model_next", "")).strip() != "" for r in rows]))
    out["source"] = "nla-consistency/data/arithmetic.jsonl (Michael Kenney); CIs: item bootstrap computed here (he states none)"
    return out


# ------------------------------------------------------------------ our side: states + probes
def load_arith_items(items_path: Path = ITEMS_W) -> List[dict]:
    d = json.loads(Path(items_path).read_text())
    its = [it for it in d["items"] if it.get("family") == "arith"]
    out = []
    for it in its:
        c = it.get("construction") or {}
        ops = it.get("operands") or c
        out.append({"item_id": it["item_id"], "a": int(ops["a"]), "b": int(ops["b"]), "op": ops["op"], "answer": int(c.get("answer", it["primary"]["answer"])), "text": it["prompt_text"]})
    return out


def load_states(items: Sequence[dict], states_dir: Path = STATES_L42) -> Any:
    """fp32 [n, d] in item order from <states_dir>/<item_id>.pt (a [d] tensor, or a dict with 'h' / 'state')."""
    import torch

    missing = [it["item_id"] for it in items if not (Path(states_dir) / f"{it['item_id']}.pt").exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} arith states missing under {states_dir} (e.g. {missing[:3]})")
    hs = []
    for it in items:
        h = torch.load(Path(states_dir) / f"{it['item_id']}.pt", map_location="cpu", weights_only=False)
        if isinstance(h, dict):
            h = h.get("h", h.get("state"))
        hs.append(torch.as_tensor(h).float().reshape(-1))
    return torch.stack(hs)


def digit_targets(items: Sequence[dict]) -> Dict[str, List[int]]:
    return {"a_tens": [it["a"] // 10 for it in items], "a_units": [it["a"] % 10 for it in items],
            "b_tens": [it["b"] // 10 for it in items], "b_units": [it["b"] % 10 for it in items]}


def probe_cv(X: Any, targets: Dict[str, Sequence[int]], *, n_folds: int = N_FOLDS, shuffle_seed: int = FOLD_SHUFFLE_SEED, n_train: Optional[int] = None) -> Dict[str, List[int]]:
    """Michael's probe() verbatim in form: standardise on ALL rows, shuffled interleaved folds, one softmax probe per target per fold
    (w_directions.michael.fit_lr = LBFGS/strong Wolfe, CE + 1e-3‖W‖²), held-out argmax predictions. ``n_train`` (learning curve
    only) keeps a seeded random subset of that size of each fold's training rows; the test folds are unchanged."""
    import torch

    from projects.g_agreement.w_directions.michael import fit_lr

    X = torch.as_tensor(X).float()
    Z = (X - X.mean(0)) / (X.std(0) + 1e-6)
    n = X.shape[0]
    idx = list(range(n))
    random.Random(shuffle_seed).shuffle(idx)
    folds = [idx[i::n_folds] for i in range(n_folds)]
    preds: Dict[str, List[Optional[int]]] = {k: [None] * n for k in targets}
    for name, y in targets.items():
        yt = torch.tensor(list(y)).long()
        ncls = int(yt.max()) + 1
        for fi, f in enumerate(folds):
            fs = set(f)
            tr = [i for i in idx if i not in fs]
            if n_train is not None and n_train < len(tr):
                tr = sorted(random.Random(shuffle_seed * 1000 + fi).sample(tr, n_train))
            train = torch.tensor(tr)
            W, b = fit_lr(Z[train], yt[train], ncls)
            p = (Z[torch.tensor(f)] @ W + b).argmax(1)
            for i, v in zip(f, p.tolist()):
                preds[name][i] = int(v)
    return {k: [int(v) for v in vs] for k, vs in preds.items()}


def probe_report(items: Sequence[dict], preds: Dict[str, List[int]], *, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    out: Dict[str, Any] = {"n_prompts": len(items), "folds": N_FOLDS, "fold_shuffle_seed": FOLD_SHUFFLE_SEED}
    tg = digit_targets(items)
    for op in ("a", "b"):
        rec = [{"item_id": it["item_id"], "true": it[op], "reported": preds[f"{op}_tens"][i] * 10 + preds[f"{op}_units"][i]} for i, it in enumerate(items)]
        st = item_bootstrap(rec, n_boot, seed, with_pearson=True)
        out[f"probe_exact_{op}"] = {k: st[k] for k in ("exact", "exact_lo", "exact_hi", "exact_wilson", "n_items")}
        out[f"probe_spearman_{op}"] = {"rho": st["spearman"], "lo": st["spearman_lo"], "hi": st["spearman_hi"]}
        out[f"probe_pearson_{op}"] = {"r": st.get("pearson"), "lo": st.get("pearson_lo"), "hi": st.get("pearson_hi")}
        out[f"probe_predictions_{op}"] = [r["reported"] for r in rec]
    for k in TARGETS:
        y = tg[k]
        out[f"probe_digit_{k}"] = {"acc": float(np.mean([a == b for a, b in zip(preds[k], y)])), "majority": max(y.count(v) for v in set(y)) / len(y)}
    return out


LEARNING_CURVE_SIZES: Tuple[int, ...] = (20, 40, 60)


def learning_curve(X: Any, items: Sequence[dict], *, sizes: Sequence[int] = LEARNING_CURVE_SIZES, full_preds: Optional[Dict[str, List[int]]] = None) -> List[dict]:
    """Sample-size control for the bridge: the same 5 test folds, probes trained on a seeded subset of n_train rows of each fold's
    training set (full = all 80 of 100). Exact-match for a and b with Wilson CIs per size. (His activations are not released, so
    his probes cannot be refitted at n = 100; this shows how far our estimate is from its own plateau.)"""
    tg = digit_targets(items)
    out = []
    n = len(items)
    full = n - n // N_FOLDS
    for s in [x for x in sizes if x < full] + [full]:
        preds = full_preds if (s == full and full_preds is not None) else probe_cv(X, tg, n_train=(None if s == full else s))
        row = {"n_train_per_fold": int(s)}
        for op in ("a", "b"):
            ok = [preds[f"{op}_tens"][i] * 10 + preds[f"{op}_units"][i] == it[op] for i, it in enumerate(items)]
            p, lo, hi = wilson(sum(ok), n)
            row[f"exact_{op}"], row[f"exact_{op}_lo"], row[f"exact_{op}_hi"] = p, lo, hi
        out.append(row)
    return out


def recipe_ranks(X: Any, items: Sequence[dict], *, seed: int = 0) -> dict:
    """Michael's 18 + 18 recipe fitted on all states (ranks of the class-mean and probe-weight subspaces per operand)."""
    import torch

    from projects.g_agreement.w_directions.michael import michael_subspaces

    fit = michael_subspaces(torch.as_tensor(X).float(), {"a": torch.tensor([it["a"] for it in items]), "b": torch.tensor([it["b"] for it in items])}, seed=seed)
    return {"ranks": fit["ranks"], "classes_present": {k: len(v) for k, v in fit["classes"].items()}, "n_states": fit["n_states"], "recipe": fit["recipe"]}


# ------------------------------------------------------------------ NLA (and the other readers) on the arith states, native vector
def native_arith(s3_rows: Sequence[dict], items: Sequence[dict], *, n_boot: int = N_BOOT, seed: int = SEED, unit: str = "S1") -> Dict[str, dict]:
    """Per reader with S3 rows on arith: argmax over the row's candidates (the RESULT 0–198) → exact vs result with CIs and Spearman,
    plus the rates at which the argmax equals a or b (proxy only; the vector never ranges over operands)."""
    by = {it["item_id"]: it for it in items}
    per: Dict[str, List[dict]] = {}
    seen = set()
    for r in s3_rows:
        if r.get("unit") != unit or r.get("family") != "arith" or r.get("item_id") not in by:
            continue
        k = (r["reader"], r["item_id"])
        if k in seen:
            continue
        seen.add(k)
        rep = argmax_candidate(r.get("candidates") or [], r.get("scores"))
        v = int(rep) if rep is not None and re.fullmatch(r"-?\d+", str(rep)) else None
        it = by[r["item_id"]]
        per.setdefault(r["reader"], []).append({"item_id": it["item_id"], "true": it["answer"], "reported": v, "a": it["a"], "b": it["b"]})
    out = {}
    for rd, rec in per.items():
        st = item_bootstrap(rec, n_boot, seed)
        n = len(rec)
        out[rd] = {"n_items": n, "result_exact": st["exact"], "result_exact_lo": st["exact_lo"], "result_exact_hi": st["exact_hi"], "result_spearman": st["spearman"],
                   "result_spearman_lo": st["spearman_lo"], "result_spearman_hi": st["spearman_hi"],
                   "argmax_equals_a": sum(1 for x in rec if x["reported"] == x["a"]) / n, "argmax_equals_b": sum(1 for x in rec if x["reported"] == x["b"]) / n,
                   "candidates": "result 0–198 (candidates_all), not the operands"}
    return out


# ------------------------------------------------------------------ comparison
def within(x: Optional[float], lo: Optional[float], hi: Optional[float]) -> Optional[bool]:
    if x is None or lo is None or hi is None or any(isinstance(v, float) and math.isnan(v) for v in (x, lo, hi)):
        return None
    return bool(lo <= x <= hi)


def overlap(lo1, hi1, lo2, hi2) -> Optional[bool]:
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (lo1, hi1, lo2, hi2)):
        return None
    return bool(max(lo1, lo2) <= min(hi1, hi2))


def compare(ours: dict, michael: dict, nla_native: Optional[dict]) -> List[dict]:
    rows: List[dict] = []

    def add(metric, m_pt, m_lo, m_hi, o_pt, o_lo, o_hi, note=""):
        rows.append({"metric": metric, "michael": m_pt, "michael_lo": m_lo, "michael_hi": m_hi, "ours": o_pt, "ours_lo": o_lo, "ours_hi": o_hi,
                     "ours_within_michael_ci": within(o_pt, m_lo, m_hi), "cis_overlap": overlap(m_lo, m_hi, o_lo, o_hi), "note": note})

    for op in ("a", "b"):
        m = michael[f"probe_exact_{op}"]
        o = (ours or {}).get(f"probe_exact_{op}")
        add(f"probe exact-match {op}", m["exact"], m["exact_lo"], m["exact_hi"], *(o["exact"], o["exact_lo"], o["exact_hi"]) if o else (None, None, None),
            "5-fold softmax digit probes, both digits right; his n = 600, ours n = 100")
    for op in ("a", "b"):
        m = michael[f"nla_exact_{op}"]
        add(f"NLA exact-match {op} (free text)", m["exact"], m["exact_lo"], m["exact_hi"], None, None, None,
            "no counterpart: S4 did not sample free text on arith states; S3 NLA native vector ranges over the result (see nla_native)")
        mp, ms = michael[f"nla_pearson_{op}"], michael[f"nla_spearman_{op}"]
        add(f"NLA r (Pearson) {op}", mp["r"], mp["lo"], mp["hi"], None, None, None, "his 'r' is Pearson over quoting readouts")
        add(f"NLA Spearman {op}", ms["rho"], ms["lo"], ms["hi"], None, None, None, "")
    if nla_native and "nla" in nla_native:
        nn = nla_native["nla"]
        add("NLA native argmax exact-match (result)", None, None, None, nn["result_exact"], nn["result_exact_lo"], nn["result_exact_hi"],
            f"ours only; argmax equals a {nn['argmax_equals_a']:.2f}, equals b {nn['argmax_equals_b']:.2f}")
    return rows


CSV_COLUMNS = ["metric", "michael", "michael_lo", "michael_hi", "ours", "ours_lo", "ours_hi", "ours_within_michael_ci", "cis_overlap", "note"]


def write_outputs(out_dir: Path, *, michael: dict, ours: Optional[dict], nla_native: Dict[str, dict], ranks: Optional[dict], cmp_rows: List[dict], notes: List[str],
                  inputs: dict) -> dict:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "bridge.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLUMNS)
        for r in cmp_rows:
            w.writerow(["" if r.get(c) is None else r.get(c) for c in CSV_COLUMNS])
    summary = {"written": now_iso(), "inputs": inputs, "michael": michael, "ours_probe": ours, "ours_native_arith": nla_native, "ours_recipe_ranks": ranks,
               "comparison": cmp_rows, "notes": notes, "michael_stated": MICHAEL_STATED}
    (out_dir / "bridge_summary.json").write_text(json.dumps(summary, indent=1, default=_json_default))
    md = ["# Bridge — our 100 arithmetic prompts vs Michael Kenney's 600 (nla-consistency, Result 2)", "",
          f"Inputs: {', '.join(f'{k}={v}' for k, v in inputs.items() if v)}.",
          "Michael's CIs are item-level bootstraps (1,000, seed 0) computed here from his released file (he states point estimates only).",
          f"Recomputed from his file: probe exact a {_fmt(michael['probe_exact_a']['exact'])}, b {_fmt(michael['probe_exact_b']['exact'])}; NLA exact a "
          f"{_fmt(michael['nla_exact_a']['exact'])}, b {_fmt(michael['nla_exact_b']['exact'])} (quote rate {_fmt(michael['nla_quote_rate'])}); r a "
          f"{_fmt(michael['nla_pearson_a']['r'])}, b {_fmt(michael['nla_pearson_b']['r'])} — README: 83–93 %, 5 %, 38 %, 0.57, 0.88.", "",
          "| metric | Michael [95 % CI] | ours [95 % CI] | ours in his CI | CIs overlap | note |", "|---|---|---|---|---|---|"]
    for r in cmp_rows:
        md.append(f"| {r['metric']} | {_fmt(r['michael'])} [{_fmt(r['michael_lo'])}, {_fmt(r['michael_hi'])}] | {_fmt(r['ours'])} [{_fmt(r['ours_lo'])}, {_fmt(r['ours_hi'])}] | "
                  f"{_fmt(r['ours_within_michael_ci'])} | {_fmt(r['cis_overlap'])} | {r['note']} |")
    md.append("")
    if ours:
        md.append("Per-digit probe accuracy (majority baseline), ours vs his: " + "; ".join(
            f"{k} {_fmt(ours[f'probe_digit_{k}']['acc'])} ({_fmt(ours[f'probe_digit_{k}']['majority'])}) vs {_fmt(michael[f'probe_digit_{k}']['acc'])} ({_fmt(michael[f'probe_digit_{k}']['majority'])})" for k in TARGETS) + ".")
    if ours and ours.get("learning_curve"):
        md.append("Sample-size control (same test folds; probes trained on n rows per fold → exact a / b, Wilson CI): " + "; ".join(
            f"n={r['n_train_per_fold']}: {_fmt(r['exact_a'])} [{_fmt(r['exact_a_lo'])}, {_fmt(r['exact_a_hi'])}] / {_fmt(r['exact_b'])} [{_fmt(r['exact_b_lo'])}, {_fmt(r['exact_b_hi'])}]"
            for r in ours["learning_curve"]) + " — his probes trained on 480 per fold (activations not released, so they cannot be refitted at our n).")
    if ranks:
        md.append(f"Michael's recipe on all 100 states — subspace ranks: {ranks['ranks']} (his: 18 class-mean + 18 probe-weight per operand).")
    for rd, v in sorted(nla_native.items()):
        md.append(f"Native vector on arith, reader {rd}: result exact {_fmt(v['result_exact'])} [{_fmt(v['result_exact_lo'])}, {_fmt(v['result_exact_hi'])}], Spearman "
                  f"{_fmt(v['result_spearman'])}; argmax = a {_fmt(v['argmax_equals_a'])}, = b {_fmt(v['argmax_equals_b'])} (n = {v['n_items']}).")
    md.extend(f"- {n}" for n in notes)
    (out_dir / "bridge.md").write_text("\n".join(md) + "\n")
    return summary


def run(*, states_dir: Path = STATES_L42, items_path: Path = ITEMS_W, s1: Path = S1_TARGET, s3: Path = S3_LO, michael_path: Path = MICHAEL, out_dir: Path = OUT_DIR,
        n_boot: int = N_BOOT, seed: int = SEED, do_probe: bool = True, do_ranks: bool = True, do_curve: bool = True) -> dict:
    notes: List[str] = []
    m_rows = read_jsonl(michael_path)
    if not m_rows:
        raise FileNotFoundError(f"Michael's arithmetic.jsonl missing: {michael_path}")
    michael = michael_stats(m_rows, n_boot=n_boot, seed=seed)
    items = load_arith_items(items_path)
    ours: Optional[dict] = None
    ranks: Optional[dict] = None
    inputs = {"michael": rel(michael_path), "items": rel(items_path), "states_dir": None, "s1": None, "s3": None}
    if do_probe:
        try:
            X = load_states(items, states_dir)
            inputs["states_dir"] = rel(states_dir)
            preds = probe_cv(X, digit_targets(items))
            ours = probe_report(items, preds, n_boot=n_boot, seed=seed)
            ours["standardisation"] = "mean / std over all 100 states before the folds (as in thread12_pod.py probe())"
            if do_curve:
                ours["learning_curve"] = learning_curve(X, items, full_preds=preds)
            if do_ranks:
                ranks = recipe_ranks(X, items, seed=0)
        except FileNotFoundError as e:
            notes.append(f"probe side NOT run: {str(e).replace(str(C.REPO_ROOT) + '/', '')}")
    else:
        notes.append("probe side skipped (--no-probe)")
    s1_rows = read_jsonl(s1)
    if s1_rows:
        ar = [r for r in s1_rows if r.get("family") == "arith"]
        if ar:
            inputs["s1"] = rel(s1)
            k = sum(1 for r in ar if r.get("correct"))
            notes.append(f"model greedy next token answers the arith prompt in {k}/{len(ar)} (plain format; Michael: {_fmt(michael['model_next_starts_answer'])} of 600).")
    s3_rows = read_jsonl(s3)
    nla_native = native_arith(s3_rows, items, n_boot=n_boot, seed=seed) if s3_rows else {}
    if s3_rows:
        inputs["s3"] = rel(s3)
    if "nla" not in nla_native:
        notes.append("NLA native scores on the S1 arith states absent from S3 (phase B scored counts only unless extended): no NLA row for arith.")
    notes.append("Free-text NLA readouts of arith states were not sampled in S4 (counts and error states only), so Michael's NLA operand exact-match and r have no counterpart; the native vector reads the result, not a or b.")
    notes.append(f"Same base model ({C.TARGET_MODEL_ID}), same NLA ({C.NLA_REPO}, {C.NLA_ADAPTER_SUBFOLDER}), same layer 42, plain prompt format and read position '=' as Michael; "
                 "differences: our 100 triples (disjoint from his 600), our capture pipeline, n = 100 vs 600 (wider CIs), probe standardisation on 100 states.")
    cmp_rows = compare(ours, michael, nla_native)
    return write_outputs(out_dir, michael=michael, ours=ours, nla_native=nla_native, ranks=ranks, cmp_rows=cmp_rows, notes=notes, inputs=inputs)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--states-dir", type=Path, default=STATES_L42)
    ap.add_argument("--items", type=Path, default=ITEMS_W)
    ap.add_argument("--s1", type=Path, default=S1_TARGET)
    ap.add_argument("--s3", type=Path, default=S3_LO)
    ap.add_argument("--michael", type=Path, default=MICHAEL)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--no-probe", action="store_true")
    ap.add_argument("--no-ranks", action="store_true")
    ap.add_argument("--no-curve", action="store_true", help="skip the training-size control")
    a = ap.parse_args(argv)
    try:
        s = run(states_dir=a.states_dir, items_path=a.items, s1=a.s1, s3=a.s3, michael_path=a.michael, out_dir=a.out, n_boot=a.n_boot, seed=a.seed,
                do_probe=not a.no_probe, do_ranks=not a.no_ranks, do_curve=not a.no_curve)
    except FileNotFoundError as e:
        print(f"[bridge] {e}", file=sys.stderr)
        return 2
    for r in s["comparison"]:
        print(f"[bridge] {r['metric']:40s} michael {_fmt(r['michael'])} [{_fmt(r['michael_lo'])},{_fmt(r['michael_hi'])}]  ours {_fmt(r['ours'])} "
              f"[{_fmt(r['ours_lo'])},{_fmt(r['ours_hi'])}]  within={r['ours_within_michael_ci']} overlap={r['cis_overlap']}")
    for r in (s.get("ours_probe") or {}).get("learning_curve") or []:
        print(f"[bridge] learning curve n_train={r['n_train_per_fold']:3d}: exact a {_fmt(r['exact_a'])} b {_fmt(r['exact_b'])}")
    for n in s["notes"]:
        print(f"[bridge] note: {n}")
    print(f"[bridge] wrote {a.out}/bridge.md, bridge.csv, bridge_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
