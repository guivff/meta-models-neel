"""V5 data loaders (all local caches; nothing is fetched).

errors   cache/g_agreement/y/y1_caps/<item>.pt: acts [11 layers 42..62, 14 positions, d] bf16, labels '0' (last token), '1'
         (last-1), ..., '11', 'candA', 'candB'. Window = the last 12 positions in prompt order (index 11 = last token).
         Items: dataset/items_y1_selected.json sets error (candidates [actual, correct]) and error_control (candidates
         [correct(actual), wrong symbol]). Label = the model's actual answer symbol (candidates[0]); 8 symbol classes.
own/map  cache/g_agreement/x/full/<item>.pt: {"layers": {38: [T, d], 42: [T, d]} bf16, "n_tokens"} for the 128 X2 natural
         states (64 ownership + 64 mapping, 32 pairs each). Window = the whole prompt, right-padded with a mask. Labels:
         T3 (prompt fact) = primary.answer is the first-mentioned candidate (construction.answer_is_first_mentioned);
         T1 (model's actual answer) = the parsed natural answer of x2_behaviour.jsonl is the first-mentioned candidate
         (items whose natural answer did not parse are excluded from T1).
T2       cache/g_agreement/x/x2_readvecs/<key>.pt: block-42 LAST-TOKEN read-back after the edit (bf16 [d]) for every
         x2_behaviour.jsonl entry; label = flipped_to_other. Only the last token is local (the all-position edited states are
         on the pod), so T2 is a last-token-only target here.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import edit as E  # noqa: E402

CACHE = ROOT / "cache" / "g_agreement"
DATASET = ROOT / "projects" / "g_agreement" / "dataset"
Y1_CAPS, Y1_SELECTED, Y1_LO = CACHE / "y" / "y1_caps", DATASET / "items_y1_selected.json", CACHE / "y" / "y1_lo.jsonl"
X_FULL, X_ITEMS, X_BEH, X_READVECS, X3_LO = CACHE / "x" / "full", DATASET / "items_x.json", CACHE / "x" / "x2_behaviour.jsonl", \
    CACHE / "x" / "x2_readvecs", CACHE / "x" / "x3_lo.jsonl"
SYMBOLS = tuple("ABCDEFGH")
ERROR_SETS = ("error", "error_control")
N_WINDOW = 12


@dataclass
class Windows:
    """x [n, T, d] float32 (CPU), mask [n, T] bool, y [n] int class index, ids, plus per-row metadata."""
    x: torch.Tensor
    mask: torch.Tensor
    y: np.ndarray
    ids: List[str]
    classes: List[str]
    meta: Dict[str, list] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.ids)

    def subset(self, idx: Sequence[int]) -> "Windows":
        idx = list(idx)
        return Windows(self.x[idx], self.mask[idx], self.y[idx], [self.ids[i] for i in idx], self.classes,
                       {k: [v[i] for i in idx] for k, v in self.meta.items()})


def load_jsonl(path: Path) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ------------------------------------------------------------------------------------------------------- errors (Y1)
def load_error_items(path: Path = Y1_SELECTED) -> Dict[str, dict]:
    d = json.load(open(path, encoding="utf-8"))
    return {it["item_id"]: it for it in d["items"] if it["set"] in ERROR_SETS}


def load_error_windows(layers: Sequence[int], items: Optional[Mapping[str, dict]] = None, caps_dir: Path = Y1_CAPS,
                       n_window: int = N_WINDOW) -> Dict[int, Windows]:
    """{layer: Windows} over the error + error_control items with a capture; window index n_window-1 = the last token."""
    items = items or load_error_items()
    ids = sorted(i for i in items if (caps_dir / f"{i}.pt").exists())
    if not ids:
        raise FileNotFoundError(f"no Y1 captures under {caps_dir}")
    per_layer: Dict[int, List[torch.Tensor]] = {L: [] for L in layers}
    for iid in ids:
        c = torch.load(caps_dir / f"{iid}.pt", map_location="cpu", weights_only=False)
        labels = list(c["labels"])
        pos_idx = [labels.index(str(k)) for k in range(n_window - 1, -1, -1)]  # prompt order: last-11, ..., last
        if any(c["positions"][j] < 0 for j in pos_idx):
            raise ValueError(f"{iid}: an absent window position")
        for L in layers:
            per_layer[L].append(c["acts"][list(c["layers"]).index(L)][pos_idx].float())
    y = np.array([SYMBOLS.index(items[i]["primary"]["candidates"][0]) for i in ids])
    meta = {"set": [items[i]["set"] for i in ids], "cand_actual": [items[i]["primary"]["candidates"][0] for i in ids],
            "cand_other": [items[i]["primary"]["candidates"][1] for i in ids], "k": [items[i]["source"]["k"] for i in ids],
            "start": [items[i]["source"]["start"] for i in ids], "template_id": [items[i].get("template_id") for i in ids]}
    out = {}
    for L in layers:
        x = torch.stack(per_layer[L])
        out[L] = Windows(x, torch.ones(x.shape[:2], dtype=torch.bool), y, list(ids), list(SYMBOLS), dict(meta))
    return out


def reader_flags(lo_path: Path, items: Mapping[str, dict], *, layer: Optional[int] = None, site: Optional[str] = None) -> Dict[str, Dict[str, bool]]:
    """{reader: {item_id: favours_actual}} on the error items from an LO file (x3_lo filtered by layer; y1_lo by site)."""
    out: Dict[str, Dict[str, bool]] = {}
    for r in load_jsonl(lo_path):
        if r.get("item_id") not in items or r.get("unscorable"):
            continue
        if layer is not None and r.get("layer") != layer:
            continue
        if site is not None and r.get("site") != site:
            continue
        out.setdefault(r["reader"], {})[r["item_id"]] = bool(r["favours_actual"])
    return out


# ------------------------------------------------------------------------------------------------------- own / map (X2 full)
def load_x_items(path: Path = X_ITEMS) -> Dict[str, dict]:
    d = json.load(open(path, encoding="utf-8"))
    return {it["item_id"]: it for it in d["items"]}


def natural_answers(beh_path: Path = X_BEH) -> Dict[str, Optional[str]]:
    return {r["state_item_id"]: r.get("parsed") for r in load_jsonl(beh_path) if r.get("condition") == "natural"}


def load_full_windows(layers: Sequence[int], items: Optional[Mapping[str, dict]] = None, full_dir: Path = X_FULL,
                      natural: Optional[Mapping[str, Optional[str]]] = None) -> Dict[int, Windows]:
    """{layer: Windows} over the X2 full captures (ownership + mapping), full prompt, right-padded. Binary classes
    ['second_mentioned', 'first_mentioned']; y = T3 label (prompt fact); meta['y_t1'] = model's parsed answer label or None."""
    items = items or load_x_items()
    natural = natural if natural is not None else natural_answers()
    files = sorted(p for p in full_dir.glob("*.pt"))
    if not files:
        raise FileNotFoundError(f"no X2 full captures under {full_dir}")
    caps = [torch.load(p, map_location="cpu", weights_only=False) for p in files]
    ids = [c["item_id"] for c in caps]
    T = max(c["n_tokens"] for c in caps)
    d = next(iter(caps[0]["layers"].values())).shape[-1]
    mask = torch.zeros(len(caps), T, dtype=torch.bool)
    for i, c in enumerate(caps):
        mask[i, : c["n_tokens"]] = True
    y, y_t1, fam, pair, first = [], [], [], [], []
    for iid in ids:
        it = items[iid]
        fm = it["construction"]["first_mentioned_candidate"]
        y.append(int(it["primary"]["answer"] == fm))
        ans = natural.get(iid)
        y_t1.append(None if ans not in it["primary"]["candidates"] else int(ans == fm))
        fam.append(it["family"])
        pair.append(it["pair_id"])
        first.append(fm)
    meta = {"family": fam, "pair_id": pair, "first_mentioned": first, "y_t1": y_t1, "answer": [items[i]["primary"]["answer"] for i in ids],
            "n_tokens": [c["n_tokens"] for c in caps]}
    out = {}
    for L in layers:
        x = torch.zeros(len(caps), T, d)
        for i, c in enumerate(caps):
            h = c["layers"][L].float()
            x[i, : h.shape[0]] = h
        out[L] = Windows(x, mask.clone(), np.array(y), list(ids), ["second_mentioned", "first_mentioned"], dict(meta))
    return out


# ------------------------------------------------------------------------------------------------------- T2 (X2 read-backs)
def load_t2(sites: Sequence[str] = ("S2", "S3"), conditions: Sequence[str] = ("planted",), beh_path: Path = X_BEH,
            readvec_dir: Path = X_READVECS) -> Windows:
    """Last-token read-back vectors (T = 1) for the planted entries at ``sites``; y = flipped_to_other; meta: pair_id, family,
    site, alpha, dose cell 'site|alpha'."""
    rows = [r for r in load_jsonl(beh_path) if r.get("site") in sites and r.get("condition") in conditions]
    rows.sort(key=lambda r: r["key"])
    vecs, keep = [], []
    for r in rows:
        p = readvec_dir / f"{E.x2_key_safe(r['key'])}.pt"
        if not p.exists():
            continue
        vecs.append(torch.load(p, map_location="cpu", weights_only=False).float())
        keep.append(r)
    if not keep:
        raise FileNotFoundError(f"no X2 read-back vectors under {readvec_dir}")
    x = torch.stack(vecs).unsqueeze(1)
    y = np.array([int(bool(r["flipped_to_other"])) for r in keep])
    meta = {"pair_id": [r["pair_id"] for r in keep], "family": [r["family"] for r in keep], "site": [r["site"] for r in keep],
            "alpha": [float(r["alpha"]) for r in keep], "cell": [f"{r['site']}|{float(r['alpha'])}" for r in keep],
            "coherent": [bool(r["coherent"]) for r in keep]}
    return Windows(x, torch.ones(x.shape[:2], dtype=torch.bool), y, [r["key"] for r in keep], ["kept", "flipped"], meta)
