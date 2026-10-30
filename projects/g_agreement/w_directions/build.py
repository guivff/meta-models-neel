"""Phase W Track B driver (CPU, no model calls): build the direction sets for the three families from the cached states and
write them for the pod's S2 stage. PREREG_WV.md "Track B"; definitions in ``directions.py``.

Data: ownership + mapping = the 64 X2 test pairs (cache/g_agreement/x/full/<item>.pt, layer 38, all positions); edit sites
from Z4/Z4b: ownership = the post-statement span (z4b spans.json question_only ∪ template_only = every position after the
last statement period, through the last token), mapping = the two differing symbol positions (core.edit.differing_positions);
errors = the 297 Y1 error puzzles (cache/g_agreement/y/y1_caps, layer 48 = layer index 3, label '0' = last token).
J-space: cache/g_agreement/y/jspace_L38_r384.pt (Q [5120, 384]; the L38 basis is also used for the L48 error family — flagged).

Outputs (fp32):
  cache/g_agreement/w/directions/<family>/shared.pt        shared direction set, probe weights per fold, fold assignment, Q reference
  cache/g_agreement/w/directions/<family>/<pair_id>.pt     per pair/item: positions, Δ, unit directions, coefficients, fractions, random seed
  cache/g_agreement/w/directions/index.json                pairs, sites, positions, seeds, file sizes
  results/g_agreement/w/directions_report.{md,json}

    .venv/bin/python -m projects.g_agreement.w_directions.build [--families ownership,mapping,errors] [--out DIR] [--report PATH]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import edit as E  # noqa: E402
from projects.g_agreement.w_directions import directions as W  # noqa: E402

FAMILIES: Tuple[str, ...] = ("ownership", "mapping", "errors")
OUT_DIR = C.CACHE_DIR / "w" / "directions"
REPORT_STEM = C.RESULTS_DIR / "w" / "directions_report"
X_FULL_DIR = C.CACHE_DIR / "x" / "full"
ITEMS_X = C.DATASET_DIR / "items_x.json"
ITEMS_Y1 = C.DATASET_DIR / "items_y1_selected.json"
SPANS_JSON = C.RESULTS_DIR / "z4b" / "spans.json"
JSPACE_PATH = C.CACHE_DIR / "y" / "jspace_L38_r384.pt"
Y1_CAPS_DIR = C.CACHE_DIR / "y" / "y1_caps"
LAYER_OF = {"ownership": 38, "mapping": 38, "errors": 48}
SITE_OF = {"ownership": "post_statement_span", "mapping": "differing_symbol_positions", "errors": "last_token"}
ERROR_POSITION_LABEL = "0"
RANDOM_RECIPE = ("projects.g_agreement.w_directions.directions.random_directions(seed, P, d, K): unit rows from "
                 "torch.Generator().manual_seed(seed*1009 + k + 1); scale row (k, pos) by delta_norm[pos] at edit time")


# ------------------------------------------------------------------ loading
def load_x2_pairs(family: str, items_path: Path = ITEMS_X, full_dir: Path = X_FULL_DIR) -> List[Dict[str, Any]]:
    """The X2 pairs of ``family`` that have both full captures: {pair_id, A, B (items), hA, hB (fp32 [T, d] at L38), ids_A, ids_B}."""
    items = json.loads(Path(items_path).read_text())["items"]
    by: Dict[str, Dict[str, Any]] = {}
    for it in items:
        if it["family"] == family:
            by.setdefault(it["pair_id"], {})[it["version"]] = it
    out = []
    for pid in sorted(by):
        pa, pb = full_dir / f"{pid}A.pt", full_dir / f"{pid}B.pt"
        if not (pa.exists() and pb.exists()):
            continue
        A = torch.load(pa, map_location="cpu", weights_only=False)
        B = torch.load(pb, map_location="cpu", weights_only=False)
        if len(A["ids"]) != len(B["ids"]):
            raise ValueError(f"{pid}: A/B renders differ in length")
        out.append({"pair_id": pid, "A": by[pid]["A"], "B": by[pid]["B"], "hA": A["layers"][38].float(), "hB": B["layers"][38].float(),
                    "ids_A": [int(t) for t in A["ids"]], "ids_B": [int(t) for t in B["ids"]], "item_A": A["item_id"], "item_B": B["item_id"]})
    return out


def ownership_inputs(pairs: Sequence[Dict[str, Any]], spans_path: Path = SPANS_JSON) -> List[Dict[str, Any]]:
    """Attach the post-statement span (question_only ∪ template_only of z4b spans.json; asserted = range(period_pos + 1, T))
    and the binding labels y = 1 iff the holder of the asked object is the second-mentioned name."""
    spans = json.loads(Path(spans_path).read_text())["pairs"]
    out = []
    for p in pairs:
        sp = spans[p["pair_id"]]
        pos = sorted(set(sp["arms"]["question_only"]) | set(sp["arms"]["template_only"]))
        T = len(p["ids_A"])
        if sp["n_tokens"] != T or pos != list(range(sp["A"]["period_pos"] + 1, T)) or sp["A"]["period_pos"] != sp["B"]["period_pos"]:
            raise ValueError(f"{p['pair_id']}: post-statement span {pos[:3]}…{pos[-1:]} is not range(period_pos + 1, T) for T = {T}")
        yA = int(not p["A"]["construction"]["answer_is_first_mentioned"])
        yB = int(not p["B"]["construction"]["answer_is_first_mentioned"])
        out.append({**p, "positions": pos, "yA": yA, "yB": yB, "period_pos": int(sp["A"]["period_pos"])})
    return out


def mapping_inputs(pairs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach the two differing symbol positions and the symbol letters there (character diff of the equal-length A/B prompt
    texts, in order; the two letters must be the pair's two candidates)."""
    out = []
    for p in pairs:
        diff = E.differing_positions(p["ids_A"], p["ids_B"])
        ta, tb = p["A"]["prompt_text"], p["B"]["prompt_text"]
        if len(ta) != len(tb):
            raise ValueError(f"{p['pair_id']}: prompt texts differ in length; cannot align symbols by character diff")
        cd = [k for k, (a, b) in enumerate(zip(ta, tb)) if a != b]
        if len(cd) != len(diff) or len(diff) != 2:
            raise ValueError(f"{p['pair_id']}: {len(diff)} differing tokens vs {len(cd)} differing characters (expected 2 and 2)")
        symA, symB = [ta[k] for k in cd], [tb[k] for k in cd]
        cands = set(p["A"]["primary"]["candidates"])
        if set(symA) != cands or set(symB) != cands or symA[0] == symA[1]:
            raise ValueError(f"{p['pair_id']}: differing symbols {symA}/{symB} are not the candidates {sorted(cands)}")
        out.append({**p, "positions": diff, "symA": symA, "symB": symB})
    return out


def error_inputs(items_path: Path = ITEMS_Y1, caps_dir: Path = Y1_CAPS_DIR, layer: int = 48, plabel: str = ERROR_POSITION_LABEL) -> Dict[str, Any]:
    """Layer-48 last-token vectors of the 297 error puzzles: X [n, d], actual = candidates[0], target = candidates[1] = source.correct."""
    from projects.g_agreement.y1_site import collect as Y

    items = [it for it in json.loads(Path(items_path).read_text())["items"] if it.get("set") == "error"]
    X, actual, target, ids, skipped = [], [], [], [], []
    for it in sorted(items, key=lambda i: i["item_id"]):
        a, t = it["primary"]["candidates"]
        if t != it["source"]["correct"] or a != it["primary"]["answer"] or a == t:
            raise ValueError(f"{it['item_id']}: candidates {it['primary']['candidates']} are not [actual, correct]")
        cap = Y.load_cap(it["item_id"], caps_dir)
        v = Y.cell_vector(cap, layer, plabel)
        if v is None or not torch.isfinite(v).all():
            skipped.append(it["item_id"])
            continue
        X.append(v.float())
        actual.append(a)
        target.append(t)
        ids.append(it["item_id"])
    return {"X": torch.stack(X), "actual": actual, "target": target, "item_ids": ids, "skipped": skipped,
            "layer_index_in_cap": cap["layers"].index(layer), "label_index_in_cap": cap["labels"].index(plabel)}


def load_Q(path: Path = JSPACE_PATH) -> Tuple[torch.Tensor, Dict[str, Any]]:
    obj = torch.load(path, map_location="cpu", weights_only=False)
    Q = obj["Q"].float().contiguous()
    ref = {"path": str(path.relative_to(ROOT)) if str(path).startswith(str(ROOT)) else str(path), "sha256": _sha256(path), "shape": list(Q.shape),
           "layer": int(obj.get("layer", 38)), "r_star": int(obj.get("r_star", Q.shape[1])), "energy_fraction_top_r": float(obj.get("energy_fraction_top_r", float("nan")))}
    return Q, ref


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ writing
def pair_record(family: str, rec: Dict[str, Any], *, n_tokens: int, source_items: Dict[str, str], extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """The on-disk per-pair layout (every tensor fp32 / int64)."""
    P = int(rec["positions"].numel())
    d = int(rec["delta"].shape[1])
    seed = W.random_seed_for(rec["pair_id"])
    out = {"pair_id": rec["pair_id"], "family": family, "layer": LAYER_OF[family], "site": SITE_OF[family], "n_tokens": int(n_tokens),
           "positions": rec["positions"].long(), "delta": rec["delta"].float().contiguous(), "delta_norm": rec["delta_norm"].float(),
           "dirs": {k: v.float().contiguous() for k, v in rec["dirs"].items()}, "coef": {k: v.float() for k, v in rec["coef"].items()},
           "frac": {k: v.float() for k, v in rec["frac"].items()}, "fold": int(rec["fold"]), "sign": float(rec["sign"]),
           "random": {"seed": seed, "K": W.K_RANDOM, "d": d, "n_positions": P, "recipe": RANDOM_RECIPE}, "source_items": source_items,
           "meta": dict(rec.get("meta", {})), "frame": "A→B: edited(A, dir, alpha) = h_A(pos) + alpha * delta_norm[pos] * dirs[dir][pos]; from B subtract",
           **(extra or {})}
    if family == "errors":
        out["frame"] = "full = centroid[target] − h; edited(dir, alpha) = h + alpha * delta_norm * dirs[dir] (all directions scaled to ‖full‖)"
    return out


def write_family(family: str, shared: Dict[str, Any], per_pair: Dict[str, Dict[str, Any]], q_ref: Dict[str, Any], out_dir: Path, *,
                 n_tokens_of: Dict[str, int], source_items_of: Dict[str, Dict[str, str]], extra_of: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
    fam_dir = out_dir / family
    fam_dir.mkdir(parents=True, exist_ok=True)
    folds = []
    for f in shared["probe"]["folds"]:
        folds.append({**{k: v for k, v in f.items() if k != "w_raw"}, "w_raw": f["w_raw"].float().contiguous()})
    shared_out = {**{k: v for k, v in shared.items() if k != "probe"}, "probe": {**shared["probe"], "folds": folds}, "Q_ref": q_ref,
                  "layer": LAYER_OF[family], "site": SITE_OF[family], "n_folds": W.N_FOLDS, "seed": W.SEED, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "dir_names": list(W.DIR_NAMES), "frac_names": list(W.FRAC_NAMES),
                  "norms": {pid: rec["delta_norm"].float() for pid, rec in per_pair.items()}}
    torch.save(shared_out, fam_dir / "shared.pt")
    entries = []
    for pid, rec in per_pair.items():
        obj = pair_record(family, rec, n_tokens=n_tokens_of[pid], source_items=source_items_of[pid], extra=(extra_of or {}).get(pid))
        torch.save(obj, fam_dir / f"{pid}.pt")
        entries.append({"pair_id": pid, "file": f"{family}/{pid}.pt", "positions": [int(x) for x in obj["positions"]], "n_tokens": obj["n_tokens"],
                        "delta_norm": [round(float(x), 4) for x in obj["delta_norm"]], "fold": obj["fold"], "sign": obj["sign"],
                        "random_seed": obj["random"]["seed"], "source_items": obj["source_items"], "meta": obj["meta"]})
    size = sum((fam_dir / f).stat().st_size for f in [e["file"].split("/")[1] for e in entries] + ["shared.pt"])
    return {"family": family, "layer": LAYER_OF[family], "site": SITE_OF[family], "shared": f"{family}/shared.pt", "n_pairs": len(entries),
            "bytes": int(size), "pairs": entries}


# ------------------------------------------------------------------ report
def _fmt(x: float) -> str:
    return "nan" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"


def write_report(summary: Dict[str, Any], stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".json").write_text(json.dumps(summary, indent=1, default=str))
    L: List[str] = [f"# W Track B — direction decomposition report ({summary['built_at']})", "",
                    f"Pre-registration: projects/g_agreement/PREREG_WV.md (Track B). Code: projects/g_agreement/w_directions/. "
                    f"Outputs: {summary['out_dir']} ({summary['total_mb']:.1f} MB). J-space: {summary['Q_ref']['path']} "
                    f"(Q {summary['Q_ref']['shape']}, sha256 {summary['Q_ref']['sha256'][:12]}…). Wall-clock {summary['wall_s']:.0f} s on the Mac (CPU).", ""]
    L += ["## Energy fractions of ‖Δ(pos)‖² (mean over pairs × site positions; median in brackets)", "",
          "| family | n pairs | n positions | d_cm | d_pw | d_J (overlapping) | d_J_excl | d_res | span | ‖Δ‖ mean |", "|---|---|---|---|---|---|---|---|---|---|"]
    for fam, s in summary["families"].items():
        m, md = s["frac_mean"], s["frac_median"]
        L.append(f"| {fam} | {s['n_pairs']} | {s['n_positions']} | " + " | ".join(f"{_fmt(m[k])} [{_fmt(md[k])}]" for k in ("d_cm", "d_pw", "d_J", "d_J_excl", "d_res", "span"))
                 + f" | {s['delta_norm_mean']:.1f} |")
    L += ["", "d_cm + d_pw + d_J_excl + d_res = 1 by construction; d_J (overlapping) = ‖QQᵀΔ‖²/‖Δ‖² counts J-space energy that may also lie along d_cm/d_pw. "
          "Errors: Δ := full = centroid[target] − h.", ""]
    L += ["## Pairwise cosines of the unit directions (mean, mean |cos|, max |cos| over pairs × positions)", "",
          "| family | " + " | ".join(k for k in next(iter(summary["families"].values()))["cosines"]) + " |", "|---|" + "---|" * len(next(iter(summary["families"].values()))["cosines"])]
    for fam, s in summary["families"].items():
        L.append(f"| {fam} | " + " | ".join(f"{c['mean']:+.3f} / {c['mean_abs']:.3f} / {c['max_abs']:.3f}" for c in s["cosines"].values()) + " |")
    L += ["", "## Orientation agreement (fraction of pair × positions with Δ(pos)·d̂ > 0; 1.0 = the shared direction always points A→B)", "",
          "| family | d_cm | d_pw |", "|---|---|---|"]
    for fam, s in summary["families"].items():
        L.append(f"| {fam} | {s['orientation_agreement']['d_cm']:.3f} | {s['orientation_agreement']['d_pw']:.3f} |")
    L += ["", "## J-space energy of the unit directions (‖QQᵀd̂‖²; a random direction scores r/d = 0.075)", "",
          "| family | d_cm | d_pw | d_res | two-half cos of d_cm (noise ceiling) |", "|---|---|---|---|---|"]
    for fam, s in summary["families"].items():
        j = s["j_energy"]
        L.append(f"| {fam} | {j['d_cm']:.3f} | {j['d_pw']:.3f} | {j['d_res']:.3f} | {_fmt(s['two_half_cos_dcm'])} |")
    L += ["", "## Held-out probe (SpanLogistic, inner-CV C ∈ {0.01, 0.1, 1}; 5 outer folds by pair / by item)", "",
          "| family | label | fold | C | n train | n test | accuracy | within-pair win / favours-actual |", "|---|---|---|---|---|---|---|---|"]
    for fam, s in summary["families"].items():
        for f in s["probe_folds"]:
            L.append(f"| {fam} | {s['probe_label']} | {f['fold']} | {f['C']} | {f['n_train_vectors']} | {f['n_test_vectors']} | {f['accuracy']:.3f} | {_fmt(f.get('within_pair_win', f.get('favours_actual')))} |")
        L.append(f"| {fam} | mean | – | – | – | – | {s['probe_accuracy_mean']:.3f} | {_fmt(s['probe_pairwise_mean'])} |")
    L += ["", "## Files", "", "| family | layer | site | pairs | MB | shared |", "|---|---|---|---|---|---|"]
    for fam, idx in summary["index"]["families"].items():
        L.append(f"| {fam} | {idx['layer']} | {idx['site']} | {idx['n_pairs']} | {idx['bytes'] / 1e6:.1f} | {idx['shared']} |")
    L += ["", f"Data: X2 full captures {summary['data']['x2_pairs']} pairs per family (cache/g_agreement/x/full, layer 38); Y1 error captures "
          f"{summary['data']['error_items']} items (layer 48 = cap layer index 3, label '0'), skipped (absent/non-finite): {summary['data']['error_skipped']}."]
    L += ["", "## Tensor layout the pod stage reads (all fp32; positions int64)", "", "```",
          "<family>/<pair_id>.pt = {",
          "  pair_id, family, layer (38|38|48), site, n_tokens, fold, sign (ownership: ±1 = this pair's orientation of the shared d_cm/d_pw),",
          "  positions: int64 [P]         absolute token indices of the edit site (errors: [-1] = last token),",
          "  delta:     fp32 [P, d]       Δ(pos) = h_B(pos) − h_A(pos)  (errors: full = centroid[target] − h),",
          "  delta_norm: fp32 [P]         ‖Δ(pos)‖ — the matched norm for every direction and for the random directions,",
          "  dirs: {d_cm, d_pw, d_J, d_res: fp32 [P, d]}  UNIT vectors oriented A→B (d_pw ⊥ d_cm; d_res ⊥ d_cm, d_pw, Q; d_J ∈ span Q),",
          "  coef: {same keys: fp32 [P]}  signed (d_cm, d_pw) / ≥ 0 (d_J, d_res) with coef[k][pos] * dirs[k][pos] = the component of Δ(pos),",
          "  frac: {d_cm, d_pw, d_J, d_J_excl, d_res, span: fp32 [P]}  energy fractions (d_cm + d_pw + d_J_excl + d_res = 1),",
          "  random: {seed, K = 10, d, n_positions, recipe}  → directions.random_directions(seed, P, d, K) gives fp32 [K, P, d] unit rows,",
          "  source_items: {A: item_id, B: item_id} | {item: item_id, cap_layer_index, cap_label_index}, meta (labels/symbols), frame (text)",
          "}",
          "Matched-norm edit from source A at dose alpha:  h'(pos) = h_A(pos) + alpha * delta_norm[pos] * dirs[k][pos]   (from B: minus).",
          "Component edit (the pair's own component):     h'(pos) = h_A(pos) + alpha * coef[k][pos]   * dirs[k][pos].",
          "full swap = h_A(pos) + alpha * delta[pos].  Errors: h' = h + alpha * delta_norm * dirs[k] (every direction at ‖full‖).",
          "<family>/shared.pt = {d_cm [d] (ownership) | class_means [8, d] + symbols (mapping) | centroids [8, d] + d_cm_table [8, d] + symbols (errors),",
          "  probe: {folds: [{fold, train_pairs|train_items, test_pairs|test_items, C, accuracy, classes, w_raw [K, d] raw-space weights}], fold_of_pair},",
          "  Q_ref {path, sha256, shape}, norms {pair_id: delta_norm [P]}, sign_of_pair (ownership), layer, site, seed, n_folds}",
          "```", ""]
    L += ["## Definitional choices to record under PREREG_WV.md 'Deviations'", ""]
    L += [f"- {c}" for c in summary["choices"]]
    L += ["", "## Commands", "", "```", summary["command"], "```"]
    stem.with_suffix(".md").write_text("\n".join(L) + "\n")


CHOICES = [
    "J-space basis for the ERROR family (layer 48) is the layer-38 basis cache/g_agreement/y/jspace_L38_r384.pt (no layer-48 J-lens/Gram basis exists on the Mac); "
    "d_J and the J fractions for errors are therefore 'the L38 J-space', not an L48 one. If the pod has the L48 J-lens weights, rebuild Q48 with core.edit.jspace_basis and re-run build.py --families errors.",
    "Ownership d_cm is ONE shared vector (flat mean over all pairs × site positions of the oriented Δ), applied with the pair's sign at every site position; it is not position-specific. "
    "The ownership probe pools all site positions (question + template tokens) of both versions as training rows, label = binding (holder is the second-mentioned name).",
    "Mapping class means pool both differing positions and both versions (128 vectors, 8 symbols); d_cm is per position, unit(mean[sym_B] − mean[sym_A]); the pair's own vectors are inside the class means (d_cm is not held out; only d_pw is).",
    "Error d_cm = unit(cm[target] − cm[actual]) with cm[s] = mean(actual = s) − mean(actual ≠ s) over all 297 error states (not held out); 'full' = centroid[target] − h; d_J projects the d_cm-free residual (full − (full·d_cm) d_cm) onto Q, unlike ownership/mapping where d_J = unit(QQᵀΔ).",
    "d_pw is the raw-space weight vector coef·Vt/sd of x_friday_r2r4.SpanLogistic (standardised features, inner 3-fold CV over C ∈ {0.01, 0.1, 1}); binary (ownership) → the single weight row; 8-way (mapping, errors) → w[s_B] − w[s_A] / w[target] − w[actual]; then Gram–Schmidt against d_cm.",
    "Energy fractions: frac[d_J] overlaps d_cm/d_pw; the disjoint partition is d_cm + d_pw + d_J_excl + d_res = 1 (d_J_excl = J-space energy not already along d_cm/d_pw).",
    "Random directions: K = 10 per pair/item, seed = (20261011·1000003 + crc32(pair_id)) mod (2^31 − 1), isotropic unit rows per position (X2Nulls recipe); the pod regenerates them from the seed and scales by delta_norm.",
    "Folds: ownership/mapping KFold(5, shuffle, seed 0) over pairs; errors StratifiedKFold(5, shuffle, seed 0) by actual symbol (smallest class E has 8 items). The fold's probe is applied only to its held-out pairs/items.",
    "Michael's recipe is implemented (w_directions/michael.py) and unit-tested on synthetic data; it is NOT fitted here because the counts/arithmetic states are captured in S1.",
]


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--families", default=",".join(FAMILIES))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--report", default=str(REPORT_STEM))
    args = ap.parse_args(argv)
    t0 = time.time()
    fams = [f for f in args.families.split(",") if f]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    Q, q_ref = load_Q()
    index: Dict[str, Any] = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(), "Q_ref": q_ref, "families": {}, "dir_names": list(W.DIR_NAMES),
                             "frac_names": list(W.FRAC_NAMES), "random": {"K": W.K_RANDOM, "recipe": RANDOM_RECIPE}}
    if (out_dir / "index.json").exists():
        old = json.loads((out_dir / "index.json").read_text())
        index["families"] = old.get("families", {})
    summary: Dict[str, Any] = {"families": {}, "data": {"x2_pairs": None, "error_items": None, "error_skipped": []}}
    for fam in fams:
        t1 = time.time()
        if fam == "ownership":
            pairs = ownership_inputs(load_x2_pairs("ownership"))
            shared, per = W.build_ownership(pairs, Q)
            n_tok = {p["pair_id"]: len(p["ids_A"]) for p in pairs}
            src = {p["pair_id"]: {"A": p["item_A"], "B": p["item_B"]} for p in pairs}
            extra = {p["pair_id"]: {"period_pos": p["period_pos"]} for p in pairs}
            summary["data"]["x2_pairs"] = len(pairs)
            halves = {p["pair_id"]: shared["sign_of_pair"][p["pair_id"]] * (p["hB"][p["positions"]] - p["hA"][p["positions"]]).mean(0) for p in pairs}
            two_half = W.two_half_cos(halves)
        elif fam == "mapping":
            pairs = mapping_inputs(load_x2_pairs("mapping"))
            shared, per = W.build_mapping(pairs, Q)
            n_tok = {p["pair_id"]: len(p["ids_A"]) for p in pairs}
            src = {p["pair_id"]: {"A": p["item_A"], "B": p["item_B"]} for p in pairs}
            extra = None
            two_half = _two_half_mapping(pairs, Q)
        elif fam == "errors":
            inp = error_inputs()
            shared, per = W.build_errors(inp["X"], inp["actual"], inp["target"], inp["item_ids"], Q)
            n_tok = {iid: -1 for iid in inp["item_ids"]}
            src = {iid: {"item": iid, "cap_layer_index": inp["layer_index_in_cap"], "cap_label_index": inp["label_index_in_cap"]} for iid in inp["item_ids"]}
            extra = None
            two_half = _two_half_errors(inp)
            shared["skipped_items"] = inp["skipped"]
            summary["data"].update(error_items=len(inp["item_ids"]), error_skipped=inp["skipped"])
        else:
            raise SystemExit(f"unknown family {fam}")
        idx = write_family(fam, shared, per, q_ref, out_dir, n_tokens_of=n_tok, source_items_of=src, extra_of=extra)
        index["families"][fam] = idx
        s = W.summarise_family(per, Q)
        folds = [{k: v for k, v in f.items() if k not in ("w_raw", "train_pairs", "test_pairs", "train_items", "test_items")} for f in shared["probe"]["folds"]]
        s.update(probe_folds=folds, probe_label=shared["probe"]["label"], probe_accuracy_mean=float(np.mean([f["accuracy"] for f in folds])),
                 probe_pairwise_mean=float(np.nanmean([f.get("within_pair_win", f.get("favours_actual", np.nan)) for f in folds])),
                 two_half_cos_dcm=two_half, wall_s=time.time() - t1, bytes=idx["bytes"])
        summary["families"][fam] = s
        print(f"[w-b] {fam}: {idx['n_pairs']} pairs, {s['n_positions']} positions, frac mean {{{', '.join(f'{k}={v:.3f}' for k, v in s['frac_mean'].items())}}}, "
              f"probe acc {s['probe_accuracy_mean']:.3f}, {idx['bytes'] / 1e6:.1f} MB, {time.time() - t1:.0f}s", flush=True)
    (out_dir / "index.json").write_text(json.dumps(index, indent=1))
    summary.update(built_at=index["built_at"], out_dir=str(out_dir), Q_ref=q_ref, index={"families": {k: {kk: vv for kk, vv in v.items() if kk != "pairs"} for k, v in index["families"].items()}},
                   total_mb=sum(v["bytes"] for v in index["families"].values()) / 1e6, wall_s=time.time() - t0, choices=CHOICES,
                   command=f"{Path(sys.executable).relative_to(ROOT) if str(sys.executable).startswith(str(ROOT)) else sys.executable} -m projects.g_agreement.w_directions.build --families {','.join(fams)}")
    write_report(summary, Path(args.report))
    print(f"[w-b] report → {Path(args.report).with_suffix('.md')}; index → {out_dir / 'index.json'}; {summary['wall_s']:.0f}s", flush=True)
    return 0


def _two_half_mapping(pairs: Sequence[Dict[str, Any]], Q: torch.Tensor, seed: int = W.SEED) -> float:
    """Two-half ceiling of the mapping class-mean rule: class means from each seeded half of the pairs; mean over pairs ×
    positions of cos(d_cm from half 1, d_cm from half 2) (a pair's d_cm from the half that excludes it is held out)."""
    keys = sorted(p["pair_id"] for p in pairs)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(keys))
    halves = [{keys[i] for i in perm[: len(keys) // 2]}, {keys[i] for i in perm[len(keys) // 2:]}]
    means = []
    for h in halves:
        rows: Dict[str, List[torch.Tensor]] = {}
        for p in pairs:
            if p["pair_id"] in h:
                for j, pos in enumerate(p["positions"]):
                    rows.setdefault(p["symA"][j], []).append(p["hA"][pos])
                    rows.setdefault(p["symB"][j], []).append(p["hB"][pos])
        means.append({s: torch.stack(v).double().mean(0) for s, v in rows.items()})
    cs = []
    for p in pairs:
        for j in range(len(p["positions"])):
            a, b = p["symA"][j], p["symB"][j]
            if all(a in m and b in m for m in means):
                cs.append(float(W.cos(means[0][b] - means[0][a], means[1][b] - means[1][a])))
    return float(np.mean(cs)) if cs else float("nan")


def _two_half_errors(inp: Dict[str, Any], seed: int = W.SEED) -> float:
    """Two-half ceiling of the error class-mean rule: cm tables from each seeded half; mean over items of cos(d_cm half 1, d_cm half 2)."""
    X, a = inp["X"], np.asarray(inp["actual"])
    n = X.shape[0]
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    halves = [perm[: n // 2], perm[n // 2:]]
    tabs = []
    for h in halves:
        Xh, ah = X[h].double(), a[h]
        tabs.append({s: Xh[torch.as_tensor(ah == s)].mean(0) - Xh[torch.as_tensor(ah != s)].mean(0) for s in sorted(set(ah)) if 0 < (ah == s).sum() < len(ah)})
    cs = [float(W.cos(tabs[0][t] - tabs[0][aa], tabs[1][t] - tabs[1][aa])) for aa, t in zip(inp["actual"], inp["target"]) if all(aa in tb and t in tb for tb in tabs)]
    return float(np.mean(cs)) if cs else float("nan")


if __name__ == "__main__":
    raise SystemExit(main())
