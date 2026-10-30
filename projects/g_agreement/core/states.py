"""State cache: ``cache/g_agreement/states/<item_id>.pt`` (fp32 ``[5120]``, raw, no normalisation)
plus one row per (item, layer) in ``cache/g_agreement/states_meta.jsonl`` (INTERFACES §4).
Layer 42 is the experiment's state and lives at ``<item_id>.pt``; the DEV-only extra layers
(40, 44, for the OLens off-grid check) live at ``<item_id>@L40.pt`` / ``@L44.pt`` with their own
meta rows (``layer`` set accordingly). Idempotent: cached (item, layer) pairs are skipped; a
render that no longer matches the cached ``prompt_ids_sha256`` is an error, not an overwrite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config as C
from . import model as M
from .accounting import StepLedger, append_jsonl, now_iso, read_jsonl, timed_call


def state_key(item_id: str, layer: int | None = None) -> str:
    layer = C.LAYER if layer is None else layer
    return item_id if layer == C.LAYER else f"{item_id}@L{layer}"


def state_path(item_id: str, states_dir: Path | None = None, layer: int | None = None) -> Path:
    return (states_dir or C.STATES_DIR) / f"{state_key(item_id, layer)}.pt"


def load_meta(meta_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Meta rows keyed by ``state_key(item_id, layer)``."""
    rows = read_jsonl(meta_path or C.STATES_META)
    return {state_key(r["item_id"], r.get("layer", C.LAYER)): r for r in rows}


def load_state(item_id: str, states_dir: Path | None = None, layer: int | None = None) -> Any:
    import torch

    layer = C.LAYER if layer is None else layer

    p = state_path(item_id, states_dir, layer)
    if not p.exists():
        raise FileNotFoundError(f"state missing for {item_id} @L{layer}: {p}")
    h = torch.load(p, map_location="cpu")
    if h.dtype != torch.float32 or h.ndim != 1:
        raise ValueError(f"{p}: expected fp32 [d], got {h.dtype} {tuple(h.shape)}")
    return h


def capture_item(target: M.Target, item: dict[str, Any], layers: list[int] | None = None
                 ) -> tuple[dict[int, Any], dict[int, dict[str, Any]], list[int]]:
    """Capture one item's pre-answer state at every requested layer in ONE forward.
    Returns ({layer: h fp32 [d]}, {layer: meta row}, prompt ids)."""
    layers = list(layers or [C.LAYER])
    ids = M.render_item(target.tokenizer, item["prompt_text"], item.get("system"))
    n = len(ids)
    pos = n - 1
    # pre-answer assertion: the forward holds the render only; the last token is the template's
    # assistant onset, never a generated token.
    pre_answer = True
    acts = M.capture(target.model, ids, layers, [pos])
    hs: dict[int, Any] = {}
    metas: dict[int, dict[str, Any]] = {}
    for layer in layers:
        h = acts[layer][0].contiguous()
        if h.shape[-1] != C.D_MODEL:
            raise RuntimeError(f"d_model {h.shape[-1]} != {C.D_MODEL}")
        hs[layer] = h
        metas[layer] = {
            "item_id": item["item_id"],
            "model_id": target.model_id,
            "model_sha": target.revision,
            "model_class": target.model_class,
            "layer": layer,
            "hook": C.HOOK,
            "hidden_states_index": layer + 1,
            "pos": pos,
            "n_tokens": n,
            "read_token": M.token_str(target.tokenizer, ids[pos]),
            "prompt_ids_sha256": C.sha256_ids(ids),
            "render": item.get("render", C.RENDER),
            "system": item.get("system"),
            "enable_thinking": C.ENABLE_THINKING,
            "dtype_capture": C.CAPTURE_DTYPE,
            "dtype_saved": C.SAVE_DTYPE,
            "norm": round(float(h.norm()), 4),
            "captured_at": now_iso(),
            "pre_answer": pre_answer,
            "role": "state" if layer == C.LAYER else "dev_extra_layer",
        }
    return hs, metas, ids


def layers_for(item: dict[str, Any], extra_dev_layers: tuple[int, ...] | None = None) -> list[int]:
    """42 for every item; dev items additionally 40 and 44 (``extra_dev_layers`` None = config)."""
    extra_dev_layers = C.DEV_EXTRA_LAYERS if extra_dev_layers is None else extra_dev_layers
    layers = [C.LAYER]
    if item.get("split") == "dev" and extra_dev_layers:
        layers += [L for L in extra_dev_layers if L != C.LAYER]
    return layers


def ensure_states(
    target: M.Target,
    items: list[dict[str, Any]],
    *,
    states_dir: Path | None = None,
    meta_path: Path | None = None,
    ledger_path: Path | None = None,
    module: str = "core",
    extra_dev_layers: tuple[int, ...] | None = None,
) -> dict[str, dict[str, Any]]:
    """Capture every (item, layer) not yet cached; return the layer-42 meta rows by item_id.
    Dev-item extra layers are a separately budgeted ledger step (``capture_offgrid``)."""
    import torch

    states_dir = states_dir or C.STATES_DIR
    meta_path = meta_path or C.STATES_META
    states_dir.mkdir(parents=True, exist_ok=True)
    extra_dev_layers = C.DEV_EXTRA_LAYERS if extra_dev_layers is None else extra_dev_layers
    meta = load_meta(meta_path)
    ledger = StepLedger(step="capture", module=module)
    ledger_x = StepLedger(step="capture_offgrid", module=module, extra={"layers": list(extra_dev_layers or ())})
    for it in items:
        iid = it["item_id"]
        want = layers_for(it, extra_dev_layers)
        ids = M.render_item(target.tokenizer, it["prompt_text"], it.get("system"))
        sha = C.sha256_ids(ids)
        todo = []
        for L in want:
            key = state_key(iid, L)
            if key in meta and state_path(iid, states_dir, L).exists():
                if meta[key]["prompt_ids_sha256"] != sha:
                    raise RuntimeError(f"{key}: cached state was captured from a different render; "
                                       f"delete {state_path(iid, states_dir, L)} and its meta row to recapture")
                continue
            todo.append(L)
        if not todo:
            continue
        with timed_call() as st:
            hs, rows, _ = capture_item(target, it, todo)
        for L in todo:
            torch.save(hs[L], state_path(iid, states_dir, L))
            append_jsonl(meta_path, rows[L])
            meta[state_key(iid, L)] = rows[L]
        (ledger if C.LAYER in todo else ledger_x).add(n_prompt=len(ids), n_new=0, wall_s=st.wall_s, peak=st.peak_mem_gb)
        if C.LAYER in todo and len(todo) > 1:
            ledger_x.add(n_prompt=0, n_new=0, wall_s=0.0, peak=st.peak_mem_gb)  # shares the forward
    ledger.flush(ledger_path)
    ledger_x.flush(ledger_path)
    return {it["item_id"]: meta[state_key(it["item_id"])] for it in items}


def dev_state_stats(items: list[dict[str, Any]], states_dir: Path | None = None) -> dict[str, Any]:
    """Mean dev activation and median dev norm (state_free / jlens_null inputs)."""
    import torch

    dev = [it for it in items if it.get("split") == "dev"]
    if not dev:
        raise ValueError("no dev items given")
    hs = torch.stack([load_state(it["item_id"], states_dir) for it in dev])
    return {"mean": hs.mean(0), "median_norm": float(hs.norm(dim=1).median()),
            "n": len(dev), "item_ids": [it["item_id"] for it in dev]}


def states_summary(meta_path: Path | None = None) -> dict[str, Any]:
    meta = load_meta(meta_path)
    main = [r for r in meta.values() if r.get("layer", C.LAYER) == C.LAYER]
    toks = sorted({r["read_token"] for r in main})
    return {"n_states_L42": len(main), "n_extra_layer_states": len(meta) - len(main), "read_tokens": toks,
            "norm_min": min((r["norm"] for r in main), default=None),
            "norm_max": max((r["norm"] for r in main), default=None),
            "all_pre_answer": all(r.get("pre_answer") for r in meta.values())}


if __name__ == "__main__":
    print(json.dumps(states_summary(), indent=1))
