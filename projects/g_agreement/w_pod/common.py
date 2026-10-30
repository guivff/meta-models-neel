"""Shared pieces of the Phase W pod pipeline: paths, DONE markers, the bank / direction / request interfaces produced by the
other Phase W agents (coded against the schemas listed in the module docstrings below; every assumption is named in
``INTERFACE_NOTES``), candidate first-token tables (chat and plain renders), seeded draws, and the one prefill+generate
primitive every stage uses (``prefill_generate``: optional per-row edit at one layer, read-back of several layers at the
last token or at all positions, first-step log-probs of a token list, greedy continuation).

Interfaces (other agents; fixtures stand in when absent):
  bank      projects/g_agreement/banks/w/items_w.json      {"meta", "items": [item]} with the items.json schema; item["family"] in
            {counts, ownership4, arith}; item["render"] "chat" | "plain"; item["primary"]["candidates"] = the pair scored by lo_model,
            item["primary"]["answer"] = the true answer; the full candidate list in item["primary"]["candidates_all"] (or item["candidates_all"])
            — counts: "1".."99"; ownership4: the 4 names; arith: whatever the bank lists (fallback: the pair).
            projects/g_agreement/banks/w/mapping8_index.json  {"pair_ids": [47 X mapping test pair ids], "candidates_all": ["A",..,"H"]}
            (a bare list of pair ids is accepted too).
            projects/g_agreement/banks/w/items_v7.json  {"items"|"pairs": [...]} with per item: item_id, pair_id, version, prompt_text
            (identical within a pair), preamble, preamble_role "system", candidates [2] (or primary.candidates), answer (or primary.answer).
  directions  cache/g_agreement/w/directions/<family>/index.json  {"family", "layer", "site", "pairs": {pair_id: {"file": "<pair_id>.pt",
            "positions": [...]}}} (or "items" for errors; a list of ids is accepted) and <pair_id>.pt: {"positions": [P ints],
            "delta"|"Δ"|"full": [P, d], "d_cm" | "d_pw" | "d_J" | "d_res": [P, d] unit rows, "norm": [P]} (a [d] tensor is one position;
            a dict {pos: {...}} is accepted). Errors: one file per item id, positions = [last] (absent → last), "full" = the centroid swap.
            Optional probe: <family>/probe.pt {"w": [d], "b": float, "layer": int, "site": str} or index.json["probe"] = {"file": ...}.
  requests  results/g_agreement/v/v12_pod_requests.json  (see s3v1_requests.py).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, now_iso, read_jsonl, timed_call

MODULE = "w"
W_RESULTS = C.RESULTS_DIR / "w"
W_CACHE = C.CACHE_DIR / "w"
BANK_DIR = C.PROJECT_DIR / "banks" / "w"
ITEMS_W = BANK_DIR / "items_w.json"
MAPPING8_INDEX = BANK_DIR / "mapping8_index.json"
ITEMS_V7 = BANK_DIR / "items_v7.json"
ITEMS_X = C.DATASET_DIR / "items_x.json"
ITEMS_Y1 = C.DATASET_DIR / "items_y1_selected.json"
DIRECTIONS_DIR = W_CACHE / "directions"
V12_REQUESTS = C.RESULTS_DIR / "v" / "v12_pod_requests.json"
X_FULL_DIR = C.CACHE_DIR / "x" / "full"
Y1_CAPS_DIR = C.CACHE_DIR / "y" / "y1_caps"
Z4B_SPANS = C.RESULTS_DIR / "z4b" / "spans.json"
POD_STARTED_AT = W_RESULTS / "POD_STARTED_AT"
LOG = W_RESULTS / "log.md"

# S1
S1_LAYERS: tuple[int, ...] = (20, 28, 38, 42, 48, 52)
S1_CAPS_DIR = W_CACHE / "s1_caps"
S1_TARGET = W_CACHE / "s1_target.jsonl"
STATES_L42 = W_CACHE / "states_L42"
STATES_L48 = W_CACHE / "states_L48"
STATE_LAYERS: tuple[int, ...] = (42, 48)
S1_CAP_TOKENS = {"counts": 16, "arith": 16}
S1_DEFAULT_TOKENS = 8
# S2
S2_EDIT_LAYER = {"ownership": 38, "mapping": 38, "errors": 48}
S2_READ_LAYERS = {"ownership": (42,), "mapping": (42,), "errors": (42, 48)}
S2_DIRECTIONS: tuple[str, ...] = ("d_cm", "d_pw", "d_J", "d_res", "full")
S2_ALPHAS: tuple[float, ...] = (0.5, 1.0)
S2_K_RANDOM = 10
S2_RANDOM_ALPHA = 1.0
S2_N_STATES = 64
S2_DECODE_CAP = 4500
S2_BEHAVIOUR = W_CACHE / "s2_behaviour.jsonl"
S2_READVECS = W_CACHE / "s2_readvecs"
S2_FAMILIES: tuple[str, ...] = ("ownership", "mapping", "errors")
BEHAVIOUR_TOKENS = 8
DEFAULT_BATCH = 8
SAVE_DTYPE = "bfloat16"
# S3 / S4
S3_LO = W_CACHE / "s3_lo.jsonl"
V6_LO = W_CACHE / "v6_lo.jsonl"
S4_SAMPLES = W_CACHE / "s4_samples.jsonl"
S3V1_LO = W_CACHE / "s3v1_lo.jsonl"
NLA_FAMILY_OF = {"ownership": "ownership", "ownership4": "ownership", "mapping": "mapping", "mapping8": "mapping", "errors": "puzzle",
                 "puzzle": "puzzle", "counts": "counts", "arith": "arith", "v7": "ownership"}

INTERFACE_NOTES: dict[str, str] = {
    "items_w": "items.json schema; candidates_all under primary (or top level); render 'plain' = raw tokenizer ids, no chat template",
    "mapping8": "mapping8_index.json = {'pair_ids': [...], 'candidates_all': [A..H]}; items from items_x.json (both versions)",
    "v7": "items_v7.json pairs render with the preamble as a system turn; the visible prompt_text is identical within a pair",
    "directions": "per pair .pt with positions + [P, d] tensors per direction name, norm [P]; errors per item, last token",
    "probe": "<family>/probe.pt {w, b, layer, site}; absent -> the probe reader is skipped with a note",
    "random": "K seeded unit directions per (pair, k) drawn at edit time (torch.Generator, stable_seed('w','s2_rand',pair,k)), per position, matched norm",
    "counts_logprobs": "candidate score vectors use the FIRST token of each candidate (Qwen splits digits: '1' and '12' share it; the greedy answer gives exact match)",
}


# ------------------------------------------------------------------ files, markers, logs
def stage_dir(stage: str) -> Path:
    return W_RESULTS / stage


def done_path(stage: str, sub: str | None = None) -> Path:
    return stage_dir(stage) / ("DONE" if sub is None else f"DONE_{sub}")


def is_done(stage: str, sub: str | None = None) -> bool:
    return done_path(stage, sub).exists()


def mark_done(stage: str, sub: str | None = None, info: dict[str, Any] | None = None) -> Path:
    p = done_path(stage, sub)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"stage": stage, "sub": sub, "done_at": now_iso(), **(info or {})}, indent=1) + "\n")
    return p


def refuse_if_done(stage: str, force: bool, sub: str | None = None) -> bool:
    """True when the caller must skip (DONE exists and not --force). With --force the marker is removed."""
    p = done_path(stage, sub)
    if p.exists():
        if not force:
            print(f"[w/{stage}] {p} exists; nothing to do (pass --force to redo)", flush=True)
            return True
        p.unlink()
    return False


def wlog(text: str, path: Path | None = None) -> None:
    from projects.g_agreement.core.accounting import log_line

    log_line(path or LOG, text)


def ledger(step: str, extra: dict[str, Any] | None = None) -> StepLedger:
    return StepLedger(step=f"w_{step}", module=MODULE, extra=extra or {})


def pod_minutes(started_at: Path | None = None, now: float | None = None) -> float:
    """Minutes since the timestamp (epoch seconds or ISO) in POD_STARTED_AT; 0 if the file is absent."""
    p = started_at or POD_STARTED_AT
    if not Path(p).exists():
        return 0.0
    raw = Path(p).read_text().strip()
    try:
        t0 = float(raw)
    except ValueError:
        from datetime import datetime

        t0 = datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    now = time.time() if now is None else float(now)
    return max(0.0, (now - t0) / 60.0)


# ------------------------------------------------------------------ bank / interface loaders
def _items_of(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, dict):
        for k in ("items", "pairs"):
            if k in obj:
                return list(obj[k])
        raise ValueError(f"no 'items' / 'pairs' key in {sorted(obj)[:6]}")
    return list(obj)


def load_items_w(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or ITEMS_W
    if not p.exists():
        raise FileNotFoundError(f"{p} missing (W Track A bank)")
    return _items_of(json.loads(p.read_text(encoding="utf-8")))


def candidates_all(item: dict[str, Any]) -> list[str]:
    for src in (item.get("primary") or {}, item):
        for k in ("candidates_all", "all_candidates"):
            if src.get(k):
                return [str(c) for c in src[k]]
    return [str(c) for c in item["primary"]["candidates"]]


def pair_candidates(item: dict[str, Any]) -> tuple[str, str]:
    """(own answer, other): the answer first, then the other listed candidate (a one-candidate item pairs with the next
    candidate_all)."""
    pr = item["primary"]
    ans = str(pr["answer"])
    cands = [str(c) for c in pr.get("candidates", [])]
    others = [c for c in cands if c != ans]
    if not others:
        others = [c for c in candidates_all(item) if c != ans]
    return ans, (others[0] if others else ans)


def item_render(item: dict[str, Any]) -> str:
    return str(item.get("render") or C.RENDER)


def render_ids(tokenizer: Any, item: dict[str, Any]) -> list[int]:
    """Chat render (optional system turn = preamble for V7) or the plain render (the prompt text as is, no template)."""
    if item_render(item) == "plain":
        return list(tokenizer(item["prompt_text"], add_special_tokens=False)["input_ids"])
    system = item.get("system")
    if system is None and item.get("preamble") and str(item.get("preamble_role", "system")) == "system":
        system = item["preamble"]
    return M.render_item(tokenizer, item["prompt_text"], system)


def load_mapping8(index_path: Path | None = None, items_x_path: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """The 47 × 2 mapping items (items_x.json) named by mapping8_index.json, each with candidates_all = the 8 symbols."""
    p = index_path or MAPPING8_INDEX
    if not p.exists():
        raise FileNotFoundError(f"{p} missing (W Track A mapping-8 index)")
    idx = json.loads(p.read_text(encoding="utf-8"))
    def _pid(x: Any) -> str:
        return str(x["pair_id"] if isinstance(x, dict) else x)

    if isinstance(idx, list):
        pair_ids, cands = [_pid(x) for x in idx], [chr(ord("A") + i) for i in range(8)]
    else:
        raw = idx.get("pair_ids") or idx.get("pairs") or idx.get("test_pairs") or []
        pair_ids = [_pid(x) for x in (raw if isinstance(raw, list) else list(raw))]
        cands = [str(c) for c in (idx.get("candidates_all") or idx.get("symbols") or [chr(ord("A") + i) for i in range(8)])]
    want = set(pair_ids)
    items = [dict(it) for it in C.load_items("all", 0, path=items_x_path or ITEMS_X) if it["pair_id"] in want and it["family"] == "mapping"]
    for it in items:
        it["family"] = "mapping8"
        it["primary"] = {**it["primary"], "candidates_all": list(cands)}
    missing = want - {it["pair_id"] for it in items}
    if missing:
        raise ValueError(f"mapping8 pairs missing from items_x.json: {sorted(missing)[:5]}")
    return items, cands


def load_v7(path: Path | None = None) -> list[dict[str, Any]]:
    """V7 items as items.json-style records (family 'v7', render chat with the preamble as the system turn)."""
    p = path or ITEMS_V7
    if not p.exists():
        raise FileNotFoundError(f"{p} missing (V7 pairs)")
    paths = [p]
    if path is None:  # extra V7 banks (the 2026-10-12 confirmatory set items_v7c.json): W_ITEMS_V7_EXTRA=path[,path...]
        paths += [Path(x) for x in os.environ.get("W_ITEMS_V7_EXTRA", "").split(",") if x.strip() and Path(x).exists()]
    out = []
    for q in paths:
        for raw in _items_of(json.loads(q.read_text(encoding="utf-8"))):
            if "A" in raw and "B" in raw and isinstance(raw["A"], dict):  # pair record with two versions
                for v in ("A", "B"):
                    out.append(_v7_item(raw[v], raw.get("pair_id"), v))
            else:
                out.append(_v7_item(raw, raw.get("pair_id"), raw.get("version")))
    return out


def _v7_item(raw: dict[str, Any], pair_id: str | None, version: str | None) -> dict[str, Any]:
    pr = dict(raw.get("primary") or {})
    cands = [str(c) for c in (pr.get("candidates") or raw.get("candidates") or [])]
    ans = str(pr.get("answer", raw.get("answer")))
    it = {**raw, "item_id": raw.get("item_id") or f"{pair_id}{version}", "pair_id": pair_id or raw.get("pair_id"), "version": version or raw.get("version"),
          "family": "v7", "render": "chat", "system": raw.get("system") if raw.get("system") is not None else
          (raw.get("preamble") if str(raw.get("preamble_role", "system")) == "system" else None),
          "primary": {**pr, "candidates": cands, "answer": ans, "candidates_all": cands}}
    if str(raw.get("preamble_role", "system")) != "system" and raw.get("preamble"):
        it["prompt_text"] = f"{raw['preamble']}\n\n{raw['prompt_text']}"
    return it


def load_errors(path: Path | None = None) -> list[dict[str, Any]]:
    """The 297 puzzle ERROR items (items_y1_selected.json); candidates = (actual, other), family tag 'errors'."""
    items = _items_of(json.loads((path or ITEMS_Y1).read_text(encoding="utf-8")))
    out = []
    for it in items:
        if it.get("family") == "puzzle" and it.get("set") == "error":
            out.append({**it, "family": "errors", "family_orig": "puzzle"})
    return out


def seeded_subset(ids: list[str], n: int, seed: int = 0) -> list[str]:
    """``n`` ids drawn without replacement from the SORTED list by numpy default_rng(seed); all of them if n >= len."""
    import numpy as np

    ids = sorted(ids)
    if n >= len(ids):
        return ids
    rng = np.random.default_rng(int(seed))
    idx = rng.choice(len(ids), size=int(n), replace=False)
    return [ids[int(i)] for i in sorted(idx)]


# ------------------------------------------------------------------ directions (Track B layout, cache/g_agreement/w/directions/)
#   index.json (top level): {"families": {fam: {"family","layer","site","shared": "<fam>/shared.pt","n_pairs","pairs": [{"pair_id","file",
#   "positions","n_tokens","delta_norm","fold","sign","random_seed","source_items","meta"}]}}, "random": {"K","recipe"}, "Q_ref", ...}
#   <fam>/<pair_id>.pt: {pair_id, family, layer, site, n_tokens, positions int64 [P], delta fp32 [P,d], delta_norm [P], dirs {d_cm,d_pw,d_J,d_res:
#   [P,d] unit, oriented A→B}, coef, frac, fold, sign, random {seed,K,d,n_positions,recipe}, source_items, meta, frame}
#   <fam>/shared.pt: {probe: {folds: [{fold, train_pairs|train_items, test_pairs|test_items, C, accuracy, classes, w_raw [K,d]}], fold_of_pair,
#   label}, ...}.  (The older per-family index.json / probe.pt layout is still accepted.)
def directions_index(family: str, root: Path | None = None) -> dict[str, Any]:
    root = root or DIRECTIONS_DIR
    d = root / family
    out: dict[str, Any] = {"family": family, "dir": d, "files": {}, "entries": {}, "meta": {}, "probe_path": None, "shared_path": None}
    top = root / "index.json"
    fam_idx = d / "index.json"
    if fam_idx.exists():
        idx = json.loads(fam_idx.read_text(encoding="utf-8"))
        ents = idx.get("pairs", idx.get("items", idx)) if isinstance(idx, dict) else idx
        if isinstance(ents, list):
            ents = {(e if isinstance(e, str) else e.get("pair_id") or e.get("item_id")): (e if isinstance(e, dict) else {}) for e in ents}
        for k, e in ents.items():
            f = (e or {}).get("file") if isinstance(e, dict) else None
            out["files"][str(k)] = (root / f) if f and "/" in f else d / (f or f"{k}.pt")
            out["entries"][str(k)] = e if isinstance(e, dict) else {}
        out["meta"] = idx if isinstance(idx, dict) else {}
    elif top.exists():
        idx = json.loads(top.read_text(encoding="utf-8"))
        fam = (idx.get("families") or {}).get(family)
        if fam is None:
            raise FileNotFoundError(f"{top}: no family {family!r} (have {sorted(idx.get('families') or {})})")
        for e in fam.get("pairs") or fam.get("items") or []:
            pid = str(e.get("pair_id") or e.get("item_id"))
            f = e.get("file") or f"{family}/{pid}.pt"
            out["files"][pid] = root / f
            out["entries"][pid] = e
        out["meta"] = {k: v for k, v in fam.items() if k not in ("pairs", "items")}
        out["meta"]["random"] = idx.get("random")
        if fam.get("shared"):
            out["shared_path"] = root / fam["shared"]
    else:
        raise FileNotFoundError(f"{top} / {fam_idx} missing (W Track B directions for {family})")
    if not out["files"]:  # last resort: every pair file in the family directory
        out["files"] = {q.stem: q for q in sorted(d.glob("*.pt")) if q.name != "shared.pt"}
    out["layer"] = int(out["meta"].get("layer", S2_EDIT_LAYER.get(family, 38)))
    out["site"] = out["meta"].get("site")
    if out["shared_path"] is None and (d / "shared.pt").exists():
        out["shared_path"] = d / "shared.pt"
    probe = out["meta"].get("probe")
    pp = d / "probe.pt"
    if isinstance(probe, dict) and probe.get("file"):
        pp = d / probe["file"]
    elif isinstance(probe, str):
        pp = d / probe
    out["probe_path"] = pp if pp.exists() else None
    return out


_DELTA_KEYS = ("delta", "Δ", "swap", "full")
_NORM_KEYS = ("delta_norm", "norm", "norms", "norm_delta")


def load_direction_file(path: Path, names: tuple[str, ...] = S2_DIRECTIONS) -> dict[str, Any]:
    """Normalise one direction file to ``{"positions": [P], "delta": [P, d], "norm": [P], "<name>": [P, d] unit rows, "random_seed",
    "layer", "sign", "fold"}``. Directions may sit at the top level or under ``dirs``; names absent from the file are left out
    (the caller decides); ``full`` falls back to unit(delta)."""
    import torch

    obj = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(obj, dict):
        raise ValueError(f"{path}: expected a dict")
    if obj and all(isinstance(k, int) or (isinstance(k, str) and k.lstrip("-").isdigit()) for k in obj):  # {pos: {...}}
        pos = sorted(int(k) for k in obj)
        per = {int(k): v for k, v in obj.items()}
        merged: dict[str, Any] = {"positions": pos}
        for name in set(k for v in per.values() for k in v):
            try:
                merged[name] = torch.stack([torch.as_tensor(per[p][name]).float().reshape(-1) for p in pos])
            except Exception:
                continue
        obj = merged
    dirs_src = obj.get("dirs") if isinstance(obj.get("dirs"), dict) else {}

    def pick(keys):
        for k in keys:
            if k in obj and obj[k] is not None:
                return k
        return None

    dk = pick(_DELTA_KEYS)
    if dk is None:
        raise ValueError(f"{path}: no delta/full tensor ({sorted(map(str, obj))[:8]})")
    delta = torch.as_tensor(obj[dk]).float()
    if delta.ndim == 1:
        delta = delta[None]
    P, d = delta.shape
    positions = obj.get("positions")
    positions = [int(p) for p in (positions.tolist() if hasattr(positions, "tolist") else positions)] if positions is not None else ([-1] if P == 1 else list(range(P)))
    if len(positions) != P:
        raise ValueError(f"{path}: {len(positions)} positions for {P} delta rows")
    nk = pick(_NORM_KEYS)
    norm = torch.as_tensor(obj[nk]).float().reshape(-1) if nk is not None else delta.norm(dim=1)
    if norm.numel() != P:
        raise ValueError(f"{path}: {norm.numel()} norms for {P} positions")
    rnd = obj.get("random") if isinstance(obj.get("random"), dict) else {}
    out: dict[str, Any] = {"positions": positions, "delta": delta, "norm": norm, "layer": obj.get("layer"), "n_positions": P, "d": d, "sign": obj.get("sign"),
                           "fold": obj.get("fold"), "random_seed": rnd.get("seed"), "random_K": rnd.get("K"), "site": obj.get("site"), "frame": obj.get("frame"),
                           "names_in_file": [n for n in names if n in obj or n in dirs_src]}
    for name in names:
        src = dirs_src.get(name) if name in dirs_src else obj.get(name)
        if src is not None:
            v = torch.as_tensor(src).float()
            if v.ndim == 1:
                v = v[None].expand(P, d) if P > 1 and v.numel() == d else v[None]
            if v.shape != (P, d):
                raise ValueError(f"{path}: {name} has shape {tuple(v.shape)}, expected ({P}, {d})")
            out[name] = v / v.norm(dim=1, keepdim=True).clamp_min(1e-9)
        elif name == "full":
            out["full"] = delta / delta.norm(dim=1, keepdim=True).clamp_min(1e-9)
    return out


def random_unit_directions(pair_id: str, k: int, n_positions: int, d: int, seed: int | None = None, seed_tag: str = "s2_rand") -> Any:
    """fp32 ``[P, d]`` unit rows for random direction ``k``: Track B's recipe when the pair's ``random.seed`` is given
    (``torch.Generator().manual_seed(seed * 1009 + k + 1)``, ``randn(P, d)`` normalised row-wise == w_directions.directions.random_directions[k]);
    otherwise seeded by C.stable_seed(MODULE, seed_tag, pair_id, k)."""
    import torch

    if seed is not None:
        g = torch.Generator().manual_seed(int(seed) * 1009 + int(k) + 1)
    else:
        g = torch.Generator().manual_seed(C.stable_seed(MODULE, seed_tag, pair_id, k))
    r = torch.randn(n_positions, d, generator=g)
    return r / r.norm(dim=1, keepdim=True).clamp_min(1e-9)


# ------------------------------------------------------------------ probe (Track B shared.pt, held-out folds)
def load_probe(path: Path | None) -> dict[str, Any] | None:
    """The older single-vector probe.pt ({w [d], b, layer, site}) → one fold "all"."""
    import torch

    if path is None or not Path(path).exists():
        return None
    obj = torch.load(path, map_location="cpu", weights_only=False)
    if isinstance(obj, dict) and "folds" in obj:
        return normalise_probe(obj, path=str(path))
    if isinstance(obj, dict):
        w = torch.as_tensor(obj.get("w", obj.get("weight", obj.get("coef")))).float().reshape(1, -1)
        b = float(obj.get("b", obj.get("bias", obj.get("intercept", 0.0))) or 0.0)
        return {"folds": {"all": w}, "intercepts": {"all": torch.tensor([b])}, "fold_of_pair": {}, "classes": list(obj.get("classes") or []), "binary": w.shape[0] == 1,
                "layer": obj.get("layer"), "site": obj.get("site"), "label": obj.get("label"), "path": str(path), "kind": "probe_pt"}
    w = torch.as_tensor(obj).float().reshape(1, -1)
    return {"folds": {"all": w}, "intercepts": {}, "fold_of_pair": {}, "classes": [], "binary": True, "layer": None, "site": None, "label": None, "path": str(path), "kind": "tensor"}


def normalise_probe(pr: dict[str, Any], *, path: str, layer: int | None = None, site: str | None = None) -> dict[str, Any]:
    import torch

    folds: dict[str, Any] = {}
    icpt: dict[str, Any] = {}
    classes: list[Any] = []
    for f in pr["folds"]:
        key = str(f.get("fold"))
        w = torch.as_tensor(f["w_raw"]).float()
        if w.ndim == 1:
            w = w[None]
        folds[key] = w
        if f.get("b_raw") is not None or f.get("intercept") is not None:
            icpt[key] = torch.as_tensor(f.get("b_raw", f.get("intercept"))).float().reshape(-1)
        classes = list(f.get("classes") or classes)
    k = next(iter(folds.values())).shape[0] if folds else 0
    return {"folds": folds, "intercepts": icpt, "fold_of_pair": {str(a): str(b) for a, b in (pr.get("fold_of_pair") or {}).items()}, "classes": classes,
            "binary": k == 1, "layer": layer, "site": site, "label": pr.get("label"), "path": path, "kind": "shared_folds", "n_folds": len(folds)}


def load_probe_shared(shared_path: Path | None, *, layer: int | None = None, site: str | None = None) -> dict[str, Any] | None:
    """The Track B probe of shared.pt: fold-specific ``w_raw`` [K, d] (K = 1 binary ownership; 8-way mapping / errors) and ``fold_of_pair``."""
    import torch

    if shared_path is None or not Path(shared_path).exists():
        return None
    sh = torch.load(shared_path, map_location="cpu", weights_only=False)
    pr = sh.get("probe") if isinstance(sh, dict) else None
    if not pr or not pr.get("folds"):
        return None
    return normalise_probe(pr, path=str(shared_path), layer=int(sh.get("layer", layer or 0)) or layer, site=sh.get("site", site))


def probe_weights_for(probe: dict[str, Any], pair_id: str | None) -> tuple[Any, Any, str]:
    """(w [K, d], b [K] or None, fold label): the fold that did NOT train on ``pair_id``; a pair/item outside every fold (new bank items)
    gets the mean of the fold weights (label 'mean_of_folds'; no held-out guarantee)."""
    import torch

    fold = probe["fold_of_pair"].get(str(pair_id)) if pair_id is not None else None
    if fold is not None and fold in probe["folds"]:
        return probe["folds"][fold], probe["intercepts"].get(fold), fold
    if "all" in probe["folds"]:
        return probe["folds"]["all"], probe["intercepts"].get("all"), "all"
    ws = list(probe["folds"].values())
    w = torch.stack(ws).mean(0)
    bs = [probe["intercepts"][k] for k in probe["folds"] if k in probe["intercepts"]]
    b = torch.stack(bs).mean(0) if len(bs) == len(ws) and bs else None
    return w, b, "mean_of_folds"


def mention_order(prompt_text: str, cands: list[str]) -> list[str]:
    """The candidates sorted by their first mention in the prompt (absent ones last, in the given order)."""
    def first(c: str) -> int:
        i = prompt_text.find(c)
        return i if i >= 0 else 10 ** 9
    return sorted(cands, key=lambda c: (first(c), cands.index(c)))


def probe_candidate_scores(probe: dict[str, Any], h: Any, cands: list[str], *, pair_id: str | None, prompt_text: str | None = None) -> dict[str, Any]:
    """Per-candidate probe scores for one vector ``h`` [d]: K-way → w[class(c)]·h (+b); binary ownership (label: y = 1 iff the holder is the
    SECOND-mentioned name) → the second-mentioned candidate scores w·h (+b), the other 0, so score(A) − score(B) = ±(w·h + b).
    Candidates outside the probe's classes are None."""
    import torch

    w, b, fold = probe_weights_for(probe, pair_id)
    h = torch.as_tensor(h).float().reshape(-1)
    z = (w @ h) + (b if b is not None else 0.0)
    out: list[float | None] = []
    if probe["binary"]:
        order = mention_order(prompt_text or "", [str(c) for c in cands]) if prompt_text else [str(c) for c in cands]
        second = order[1] if len(order) > 1 else None
        for c in cands:
            out.append(float(z[0]) if str(c) == second else 0.0)
        rule = "binary: second-mentioned candidate = w.h, other = 0"
    else:
        idx = {str(c): i for i, c in enumerate(probe["classes"])}
        for c in cands:
            out.append(float(z[idx[str(c)]]) if str(c) in idx else None)
        rule = "k_way: w[class(c)].h"
    return {"scores": out, "fold": fold, "rule": rule, "raw": [float(x) for x in z.tolist()] if z.numel() <= 16 else None}


# ------------------------------------------------------------------ candidate first tokens
def first_token_table(tokenizer: Any, cands: list[str], render: str = "chat") -> dict[str, Any]:
    """First token id of every candidate in the spelling the model would emit: chat render → bare ``X`` first (the render ends in a
    newline), plain render → ``" X"`` first. Returns {cand: {"id", "form", "n_tokens"}} plus the (A, B) pair rule of
    ``core.edit.first_token_candidates`` for the first two candidates."""
    order = ("bare", "space") if render != "plain" else ("space", "bare")
    out: dict[str, Any] = {"render": render, "tokens": {}, "ids": []}
    for c in cands:
        forms = {"bare": c, "space": " " + c}
        chosen = None
        for name in order:
            ids = list(tokenizer(forms[name], add_special_tokens=False)["input_ids"])
            if ids:
                chosen = {"id": int(ids[0]), "form": name, "text": forms[name], "n_tokens": len(ids)}
                break
        if chosen is None:
            chosen = {"id": None, "form": None, "text": None, "n_tokens": 0}
        out["tokens"][c] = chosen
        out["ids"].append(chosen["id"])
    out["duplicates"] = len({i for i in out["ids"] if i is not None}) < len([i for i in out["ids"] if i is not None])
    return out


def pair_first_tokens(tokenizer: Any, cand_a: str, cand_b: str, render: str = "chat") -> dict[str, Any]:
    """The pair rule: the first spelling whose first tokens DIFFER (chat: core.edit.first_token_candidates; plain: the same ladder
    starting from the leading-space forms)."""
    from projects.g_agreement.core import edit as E

    if render != "plain":
        return E.first_token_candidates(tokenizer, cand_a, cand_b)
    tried = []
    for name, fa, fb in (("space", " " + cand_a, " " + cand_b), ("bare", cand_a, cand_b)):
        ia = list(tokenizer(fa, add_special_tokens=False)["input_ids"])
        ib = list(tokenizer(fb, add_special_tokens=False)["input_ids"])
        tried.append({"form": name, "A": fa, "B": fb, "first_A": ia[0] if ia else None, "first_B": ib[0] if ib else None})
        if ia and ib and ia[0] != ib[0]:
            return {"unscorable": False, "form": name, "text_A": fa, "text_B": fb, "first_A": int(ia[0]), "first_B": int(ib[0]),
                    "n_tokens_A": len(ia), "n_tokens_B": len(ib), "tried": tried}
    return {"unscorable": True, "form": None, "text_A": None, "text_B": None, "first_A": None, "first_B": None, "tried": tried,
            "reason": "no spelling whose first token differs between the candidates"}


def parse_answer(text: str, item: dict[str, Any]) -> tuple[str | None, str]:
    """The greedy answer as one of the item's candidates_all (first word / number rule), else the family rule of core.scoring."""
    import re

    from projects.g_agreement.core import scoring as SC

    cands = candidates_all(item)
    t = "" if text is None else str(text).strip()
    m = re.search(r"-?\d+", t)
    if m and all(re.fullmatch(r"-?\d+", c) for c in cands):  # numeric families: the first integer in the text
        v = str(int(m.group(0)))
        return (v if v in cands else None), f"first integer {v!r}"
    first = re.sub(r"^\W+", "", t).split()
    if first:
        head = re.sub(r"\W+$", "", first[0])
        for c in cands:
            if (head == c) if len(c) == 1 else (head.lower() == c.lower()):
                return c, "first word"
    fam_item = {**item, "family": item.get("family_orig", item.get("family")), "primary": {**item["primary"], "candidates": list(item["primary"].get("candidates") or cands[:2])}}
    try:
        p, ev = SC.extract_target_answer(t, fam_item)
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"parse error {exc}"
    return (p if p in cands else None), ev


# ------------------------------------------------------------------ prefill + generate with hooks
def prefill_generate(target: M.Target, ids: list[int], *, edit_layer: int | None = None, row_positions: list[list[int]] | None = None,
                     row_vectors: list[Any] | None = None, read_layers: tuple[int, ...] | list[int] = (), read_all_positions: bool = False,
                     max_new_tokens: int = BEHAVIOUR_TOKENS, first_token_ids: list[int | None] | None = None) -> list[dict[str, Any]]:
    """B rows (B = len(row_positions), or 1 without an edit) of the same prompt; row b has ``blocks[edit_layer]``'s output at
    ``row_positions[b]`` replaced by ``row_vectors[b]`` (fp32 ``[P_b, d]``) during the prefill; every block in ``read_layers`` is read
    back at the last prefill position (``read[L]`` fp32 ``[d]``) or at every position (``read_all[L]`` fp32 ``[T, d]``); the first-step
    log-probs of ``first_token_ids`` come back as ``lp_first`` (None entries stay None). Greedy continuation, adapter disabled."""
    import torch

    from projects.g_agreement.core import generate as G

    model, tok = target.model, target.tokenizer
    dev = next(model.parameters()).device
    blks = M.blocks(model)
    T = len(ids)
    if row_positions is None:
        B, P, V, pmax = 1, [], [], -1
    else:
        B = len(row_positions)
        if B == 0 or row_vectors is None or len(row_vectors) != B or edit_layer is None:
            raise ValueError("row_positions, row_vectors (same length, non-empty) and edit_layer are required for an edit")
        P = [torch.tensor([int(p) % T for p in ps], dtype=torch.long) for ps in row_positions]
        V = [torch.as_tensor(v).float() for v in row_vectors]
        for b in range(B):
            if V[b].ndim == 1:
                V[b] = V[b][None]
            if V[b].shape[0] != len(P[b]):
                raise ValueError(f"row {b}: {V[b].shape[0]} vectors for {len(P[b])} positions")
        pmax = max(int(p.max()) for p in P)
    state: dict[str, Any] = {"n_edits": 0, "reads": {}, "n_reads": {}}
    handles = []
    if row_positions is not None:
        def edit_hook(_mod, _inp, out):
            h = out[0] if isinstance(out, tuple) else out
            if h.shape[1] <= 1 or h.shape[1] <= pmax:
                return out
            state["n_edits"] += 1
            for b in range(B):
                h[b, P[b].to(h.device), :] = V[b].to(h.device, h.dtype)
            return out

        handles.append(blks[int(edit_layer)].register_forward_hook(edit_hook))

    def make_read(L: int):
        def read_hook(_mod, _inp, out):
            h = out[0] if isinstance(out, tuple) else out
            if h.shape[1] < T:
                return out
            state["n_reads"][L] = state["n_reads"].get(L, 0) + 1
            state["reads"][L] = (h.detach().float().cpu().clone() if read_all_positions else h[:, T - 1, :].detach().float().cpu().clone())
            return out

        return read_hook

    for L in read_layers:
        if not 0 <= int(L) < len(blks):
            raise ValueError(f"read layer {L} out of range")
        handles.append(blks[int(L)].register_forward_hook(make_read(int(L))))
    kw = G._gen_kwargs(None, max_new_tokens)
    kw.update(pad_token_id=G.pad_id(tok), num_return_sequences=1, return_dict_in_generate=True)
    eos = G.eos_ids(tok, model)
    x = torch.tensor([list(ids)] * B, device=dev)
    try:
        with timed_call() as st, torch.no_grad(), M.disable_adapter_ctx(model):
            try:
                out = model.generate(x, attention_mask=torch.ones_like(x), output_logits=True, **kw)
                first = out.logits[0]
            except TypeError:
                out = model.generate(x, attention_mask=torch.ones_like(x), output_scores=True, **kw)
                first = out.scores[0]
    finally:
        for hd in handles:
            hd.remove()
    if row_positions is not None and state["n_edits"] < 1:
        raise RuntimeError("edit hook did not fire during the prefill")
    for L in read_layers:
        if state["n_reads"].get(int(L)) != 1 or state["reads"][int(L)].shape[0] != B:
            raise RuntimeError(f"read hook at block {L} fired {state['n_reads'].get(int(L))} times (expected once, batch {B})")
    lp = torch.log_softmax(first.float(), dim=-1).cpu()
    seqs = out.sequences
    rows = []
    for b in range(B):
        new = seqs[b, T:].tolist()
        cut, reason = G._finish(new, max_new_tokens, eos)
        row: dict[str, Any] = {"answer_text": tok.decode(cut, skip_special_tokens=True), "new_ids": cut, "n_new_tokens": len(cut), "finish_reason": reason,
                               "first_token_id": (cut[0] if cut else None), "top1_id": int(lp[b].argmax()), "top1_lp": float(lp[b].max()), "n_tokens": T,
                               "edit_layer": edit_layer, "positions": (None if row_positions is None else [int(p) for p in P[b].tolist()]),
                               "n_hook_edits": state["n_edits"], "batch_size": B, "wall_s_batch": st.wall_s, "peak_mem_gb": st.peak_mem_gb,
                               "read": {int(L): state["reads"][int(L)][b].clone() for L in read_layers} if not read_all_positions else {},
                               "read_all": {int(L): state["reads"][int(L)][b].clone() for L in read_layers} if read_all_positions else {}}
        if first_token_ids is not None:
            row["lp_first"] = [None if t is None else float(lp[b, int(t)]) for t in first_token_ids]
        rows.append(row)
    return rows


def lo_from_lp(lp_first: list[float | None]) -> float | None:
    """lo_model = lp(B) − lp(A) for a two-entry list (positive = toward the second candidate)."""
    if lp_first is None or len(lp_first) < 2 or lp_first[0] is None or lp_first[1] is None:
        return None
    return float(lp_first[1] - lp_first[0])


def safe_key(key: str) -> str:
    return key.replace("|", "__").replace("/", "_").replace(" ", "_")


def row_extra() -> dict[str, Any]:
    return {"module": MODULE, **C.frozen_shas(), "created_at": now_iso()}


__all__ = [n for n in dir() if not n.startswith("_")]
