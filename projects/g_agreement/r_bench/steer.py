"""R5 — geometry, report-flipping and reader-blind edits (BRIEF_R.md §4.5; GPU). For the selected facts: the reader-gradient direction
of each reader (what the reader reads), then norm-matched edits of the text positions at the edit layer along the
class-mean, probe, reader and random directions, with (a) the model's own forced-choice answer and (b) the block-42
last-token state read back for every reader, from two forwards per edit (prompt-only render for the answer, chat render
for the read-back, same text span edited in both).

    python -m projects.g_agreement.r_bench.analyze --r5-select            # CPU: results/g_agreement/r/r5_selection.json
                                                                          #      + cache/g_agreement/r/r5/directions/<ds>.npz (d_cm, d_probe)
    python -m projects.g_agreement.r_bench.steer --phase precheck [--datasets ...] [--allow-unfrozen]   # PLAN_R §1 WS4 pre-checks
    python -m projects.g_agreement.r_bench.steer --phase A [--datasets ...] [--k-random 5] [--allow-unfrozen]   # target, Oracle, skip-lens, J-lens
    python -m projects.g_agreement.r_bench.steer --phase B                                       # NLA gradient + NLA on the read-back states

Outputs (`cache/g_agreement/r/r5/`):
  directions/<ds>.npz           d_cm, d_probe (from analyze) + d_<reader>_L42 (gradient at the read layer), d_<reader>_L38 (the
                                same vector, transported to the edit layer), d_jlens38_L38 (the J-lens analytic gradient AT block 38,
                                exploratory), d_rand<k>_L38 (seeded, saved so the band is reproducible); all unit fp32
  readback/<ds>/<dir>_a<alpha>.npy   fp16 [n_items, d] block-L_read last-token states after the edit (natural = a0.0)
  steer.jsonl                   key <ds>|<item_id>|<dir>|<alpha>: model lp_pos/lp_neg/lo, edit scale, sign, positions edited
  readers.jsonl                 key <reader>|<ds>|<item_id>|<dir>|<alpha>: the reader's s_pos / s_neg / s_diff on the read-back;
                                reader "probe" = the read-back state projected on d_probe_L42 (the probe score of BRIEF_R §4.5)
  deviations.json               readers whose gradient could not be taken in this harness (recorded, not silently dropped)
Pre-checks (`results/g_agreement/r/r5_prechecks.json`, `--phase precheck`): text span found and decoded on n items in both
renders; a zero delta reproduces the un-hooked forward (natural LO and read-back) and the collected prompt-only LO (read
from every `prompt_only*.jsonl` shard) / cached state, a comparison that cannot be made failing the check; Oracle and hook-reader gradients pass a central finite-difference check (or the deviation is recorded).
Ledger steps (module r5): grad_directions, steer_<ds>, lo_<reader>, precheck.

Sign convention: every direction is oriented neg → pos (d_cm = mean_pos − mean_neg, d_probe = the class-1 weights, d_reader =
∇_h[s_pos − s_neg]); an item is pushed toward the OTHER class, so the per-item sign is −1 for label 1 and +1 for label 0, and
the edit is h ← h + sign · α · scale · d with scale = ‖mean_pos − mean_neg‖ at the edit layer (norm-matched, BRIEF_R §4.5).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import (StepLedger, append_jsonl, done_ids, gpu_name, log_line, now_iso,
                                                  read_jsonl, timed_call)
from projects.g_agreement.r_bench import bank as B
from projects.g_agreement.r_bench import collect as RC
from projects.g_agreement.r_bench import datasets as D

MODULE = "r5"
R5_DIR = RC.R_DIR / "r5"
DIR_DIR = R5_DIR / "directions"
RB_DIR = R5_DIR / "readback"
STEER_PATH = R5_DIR / "steer.jsonl"
READERS_PATH = R5_DIR / "readers.jsonl"
DEVIATIONS_PATH = R5_DIR / "deviations.json"
SELECTION = RC.RESULTS / "r5_selection.json"
PRECHECK_PATH = RC.RESULTS / "r5_prechecks.json"
LOG = RC.RESULTS / "log.md"
L_EDIT = 38
L_READ = 42
ALPHAS = (0.5, 1.0, 2.0)
N_RANDOM = 5            # BRIEF_R §4.5 says K = 10; 5 by default for the session-2 budget (--k-random raises it; see HANDOFF.md)
RANDOM_SEED = 20261021
PROBE_READER = "probe"  # pseudo-reader: read-back state · d_probe_L<read>

# where the text sits in each render: the chat render puts it right after the user role line, the prompt-only render after
# "Text:\n" (frozen template); searching from the anchor avoids matching a short text inside the template itself
ANCHOR_CHAT = "user\n"
_PO_HEAD = D.PROMPT_ONLY_FC_TEMPLATE.split("{text}")[0]
ANCHOR_PO = _PO_HEAD[_PO_HEAD.rfind("\n", 0, -1) + 1:] if "{text}" in D.PROMPT_ONLY_FC_TEMPLATE else ""
assert ANCHOR_PO.endswith("\n") and ANCHOR_PO.strip(), f"unexpected prompt-only template head {ANCHOR_PO!r}"


# ------------------------------------------------------------------ text span in a render
def rendered_text(tokenizer: Any, text: str, max_tokens: int = RC.MAX_TOKENS) -> str:
    """The text as the renders carry it: cut to ``max_tokens`` text tokens and decoded, exactly as ``collect.render_ids``
    and ``collect.prompt_only_ids`` do, so a long text is searched for in its truncated form."""
    ids = LO.encode(tokenizer, text)
    return tokenizer.decode(ids[:max_tokens]) if len(ids) > max_tokens else text


def text_span(tokenizer: Any, ids: list[int], text: str, anchor: str | None = None) -> tuple[int, int]:
    """[start, end) token positions whose characters overlap ``text`` inside the decoded render (the search starts after
    ``anchor`` when it is present). Uses the fast tokenizer's offsets on the decoded string when re-encoding it reproduces
    ``ids``; otherwise the longest common run of the text's own token ids (the fallback a character-level mock exercises)."""
    rendered = tokenizer.decode(ids, skip_special_tokens=False)
    text = text.strip()
    if not text:
        raise RuntimeError("empty text")
    start = 0
    if anchor:
        k = rendered.find(anchor)
        start = k + len(anchor) if k >= 0 else 0
    c0 = rendered.find(text, start)
    if c0 >= 0:
        try:
            enc = tokenizer(rendered, add_special_tokens=False, return_offsets_mapping=True)
            offs = enc["offset_mapping"] if "offset_mapping" in enc else None
        except (TypeError, KeyError, NotImplementedError):
            offs = None
        if offs is not None and list(enc["input_ids"]) == list(ids):
            c1 = c0 + len(text)
            pos = [i for i, (a, b) in enumerate(offs) if b > c0 and a < c1]
            if pos:
                return pos[0], pos[-1] + 1
    tids = LO.encode(tokenizer, text)
    best = (0, 0)
    for s in range(len(ids)):
        k = 0
        while s + k < len(ids) and k < len(tids) and ids[s + k] == tids[k]:
            k += 1
        if k > best[1] - best[0]:
            best = (s, s + k)
    if best[1] - best[0] < max(1, len(tids) // 2):
        raise RuntimeError("could not locate the text span in the render")
    return best


def span_check(tokenizer: Any, ids: list[int], span: tuple[int, int], text: str) -> dict[str, Any]:
    """Decode the span and compare with the text: exact (after strip), contains (boundary tokens merged in), or neither."""
    dec = tokenizer.decode(ids[span[0]: span[1]], skip_special_tokens=False)
    t = text.strip()
    return {"exact": dec.strip() == t, "contains": t in dec, "n_tokens": span[1] - span[0], "extra_chars": max(0, len(dec.strip()) - len(t))}


# ------------------------------------------------------------------ edited forward (batched, per-row spans and deltas)
def edited_forward_batch(model: Any, rows: list[list[int]], spans: list[tuple[int, int]], layer: int, delta: Any,
                         pad: int, head_lens: list[int] | None = None, read_layer: int | None = None
                         ) -> tuple[list[float] | None, Any | None]:
    """One forward over right-padded ``rows`` (base model, adapter off) with ``delta`` added to the block-``layer`` output at
    each row's own ``span`` positions: ``delta`` is fp32 ``[d]`` (same vector for every row), ``[B, d]`` (one vector per row)
    or None (no edit hook at all: the un-hooked reference forward). Returns (summed teacher-forced lp of the tokens after
    ``head_lens[i]`` per row, or None when head_lens is None; block-``read_layer`` output at each row's last real token as
    fp32 CPU ``[B, d]``, or None). Raises if a registered hook did not fire exactly once."""
    import torch

    blks = M.blocks(model)
    dev = next(model.parameters()).device
    Bn, n = len(rows), max(len(r) for r in rows)
    ids = torch.full((Bn, n), pad, dtype=torch.long)
    mask = torch.zeros_like(ids)
    emask = torch.zeros(Bn, n, dtype=torch.bool)
    last = torch.tensor([len(r) - 1 for r in rows])
    for i, r in enumerate(rows):
        ids[i, : len(r)] = torch.tensor(r)
        mask[i, : len(r)] = 1
        if not (0 <= spans[i][0] < spans[i][1] <= len(r)):
            raise ValueError(f"row {i}: span {spans[i]} outside [0, {len(r)}]")
        emask[i, spans[i][0]: spans[i][1]] = True
    dsel = None
    if delta is not None:
        dlt = torch.as_tensor(delta).float()
        if dlt.ndim == 1:
            dlt = dlt[None].expand(Bn, -1)
        if dlt.ndim != 2 or dlt.shape[0] != Bn:
            raise ValueError(f"delta has shape {tuple(dlt.shape)}; expected [{Bn}, d] or [d]")
        rid = torch.arange(Bn)[:, None].expand(-1, n)[emask]        # the row of every edited position
        dsel = dlt[rid].contiguous()                                    # [n_edited, d]
    ids, mask, emask = ids.to(dev), mask.to(dev), emask.to(dev)
    store: dict[str, Any] = {"n_edit": 0, "n_read": 0}

    def edit_hook(_m, _i, out):
        h = out[0] if isinstance(out, tuple) else out
        store["n_edit"] += 1
        h[emask] = h[emask] + dsel.to(h.device, h.dtype)
        return out

    def read_hook(_m, _i, out):
        h = out[0] if isinstance(out, tuple) else out
        store["n_read"] += 1
        store["h"] = h[torch.arange(h.shape[0], device=h.device), last.to(h.device), :].detach().float().cpu()

    handles = []
    if dsel is not None:
        handles.append(blks[layer].register_forward_hook(edit_hook))
    if read_layer is not None:
        handles.append(blks[read_layer].register_forward_hook(read_hook))
    lps: list[float] | None = None
    try:
        with torch.no_grad(), M.disable_adapter_ctx(model):
            if head_lens is None:
                try:
                    model(input_ids=ids, attention_mask=mask, use_cache=False, logits_to_keep=1)
                except TypeError:
                    model(input_ids=ids, attention_mask=mask, use_cache=False)
            else:
                logits = model(input_ids=ids, attention_mask=mask, use_cache=False).logits
                lps = []
                for i, r in enumerate(rows):
                    h0, L = head_lens[i], len(r)
                    lp = torch.log_softmax(logits[i, h0 - 1: L - 1].float(), dim=-1)   # position u predicts ids[u+1]
                    lps.append(float(lp.gather(-1, ids[i, h0:L][:, None]).sum()))
    finally:
        for hd in handles:
            hd.remove()
    if dsel is not None and store["n_edit"] != 1:
        raise RuntimeError(f"edit hook at block {layer} fired {store['n_edit']} times (expected 1)")
    if read_layer is not None and store["n_read"] != 1:
        raise RuntimeError(f"read hook at block {read_layer} fired {store['n_read']} times (expected 1)")
    return lps, store.get("h")


# ------------------------------------------------------------------ reader gradients
def _unit(g: np.ndarray) -> np.ndarray:
    g = np.asarray(g, dtype=np.float32)
    return g / (np.linalg.norm(g) + 1e-9)


def _pad_rows(tok: Any, rows: list[list[int]], dev: Any) -> tuple[Any, Any]:
    import torch

    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    n = max(len(r) for r in rows)
    ids = torch.full((len(rows), n), pad, dtype=torch.long)
    mask = torch.zeros_like(ids)
    for i, r in enumerate(rows):
        ids[i, : len(r)] = torch.tensor(r)
        mask[i, : len(r)] = 1
    return ids.to(dev), mask.to(dev)


def _pair_lo(logits: Any, ids: Any, rows: list[list[int]], head: int) -> Any:
    """Mean over the consecutive (pos, neg) row pairs of lp(pos tokens) − lp(neg tokens), from full logits ``[2k, n, V]``
    (differentiable): one pair for the Oracle bullet, one per LO form for the skip-lens, one per template for the NLA —
    exactly the native LO of ``scoring_lo``."""
    import torch

    lp = torch.log_softmax(logits[:, :-1].float(), dim=-1)
    tok_lp = lp.gather(-1, ids[:, 1:].unsqueeze(-1)).squeeze(-1)
    s = [tok_lp[r_i, head - 1: len(r) - 1].sum() for r_i, r in enumerate(rows)]
    return sum(s[2 * j] - s[2 * j + 1] for j in range(len(rows) // 2)) / (len(rows) // 2)


def jlens_grads(reader: R.JLensReader, tokenizer: Any, pos: str, neg: str, layer: int, H: Any = None,
                H_layer: int | None = None) -> np.ndarray | None:
    """Analytic ∇_h [score(pos) − score(neg)] of the J-lens cosine readout at ``layer``, raw, one row per state. ``lo_jlens``
    takes the MAX over each candidate's single-token variants, so the gradient is that of the arg-max variant: with ``H``
    (states ``[n, d]`` at block ``H_layer``, default ``layer``) the variant is chosen per state as the lens itself picks it;
    without ``H`` one row for the first variant (the bare spelling). None if a candidate has no single-token variant
    (unscorable, as in ``lo_jlens``). The gradient is state-independent apart from the variant choice."""
    import torch

    J = reader.J[layer]
    w_u = reader.w_u
    if layer not in reader._denom:
        reader._denom[layer] = (w_u @ J).norm(dim=1).clamp_min(1e-9)
    denom = reader._denom[layer]
    va, vb = LO.token_variants(tokenizer, pos), LO.token_variants(tokenizer, neg)
    if not va or not vb:
        return None
    ta, tb = list(va.values()), list(vb.values())
    with torch.no_grad():
        U = lambda t: (w_u[t] / denom[t][:, None]).float()  # noqa: E731  rows of the normalised unembedding
        if H is None:
            ua, ub = U(ta[:1]), U(tb[:1])
        else:
            Lh = layer if H_layer is None else H_layer
            Jh = reader.J[Lh]
            if Lh not in reader._denom:
                reader._denom[Lh] = (w_u @ Jh).norm(dim=1).clamp_min(1e-9)
            dh = reader._denom[Lh]
            Hd = torch.as_tensor(H).float().to(w_u.device)
            proj = Hd @ Jh.T                                                     # [n, d]
            ia = ((proj @ w_u[ta].T) / dh[ta]).argmax(1)                         # the variant the lens picks per state
            ib = ((proj @ w_u[tb].T) / dh[tb]).argmax(1)
            ua, ub = U(ta)[ia], U(tb)[ib]
        G = ((ua - ub) @ J).float().cpu().numpy()                                # row i = Jᵀ(u_a − u_b) for state i
    return G.astype(np.float32)


def jlens_direction(reader: R.JLensReader, tokenizer: Any, pos: str, neg: str, layer: int, H: Any = None,
                    H_layer: int | None = None) -> np.ndarray | None:
    """``jlens_grads`` averaged over the states and unit-normalised (BRIEF_R §4.5: "the J-lens direction is analytic")."""
    G = jlens_grads(reader, tokenizer, pos, neg, layer, H, H_layer)
    return None if G is None else _unit(G.mean(0))


def _default_adapter(model: Any) -> None:
    """The Oracle lens is PEFT adapter ``default``; a skip-lens bound later leaves ``default`` active, but make it explicit."""
    cfg = getattr(model, "peft_config", None)
    if cfg and "default" in cfg and hasattr(model, "set_adapter"):
        act = getattr(model, "active_adapters", None) or [getattr(model, "active_adapter", None)]
        if list(act) != ["default"]:
            model.set_adapter("default")


def olens_grads(reader: R.OLensReader, H: Any, pos: str, neg: str, layer: int) -> tuple[np.ndarray, np.ndarray]:
    """Per-state ∇_h LO_olens(h) (raw, fp32 ``[n, d]``) and the LO at each state, from the same forward ``lo_olens`` runs:
    the marker's input embedding is alpha·h/‖h‖, so the gradient flows through the normalisation into h. Weights stay
    frozen; only the inserted row carries grad."""
    import torch

    t = reader.target
    assert t is not None
    _default_adapter(t.model)
    ids0, slot, _c, _cid = reader.carrier(layer)
    tok = t.tokenizer
    embed = t.model.get_input_embeddings()
    dev = next(t.model.parameters()).device
    rows = [list(ids0) + LO.encode(tok, LO.OLENS_BULLET.format(X=c)) for c in (pos, neg)]
    ids, mask = _pad_rows(tok, rows, dev)
    head = len(ids0)
    H = torch.as_tensor(H).float()
    grads, los = [], []
    for i in range(H.shape[0]):
        h = H[i].to(dev).clone().requires_grad_(True)
        with torch.no_grad():
            e = embed(ids).detach().clone()
        v = (reader.alpha * h / h.norm().clamp_min(1e-9)).to(e.dtype)
        e = torch.cat([e[:, :slot], v[None, None, :].expand(2, 1, -1), e[:, slot + 1:]], dim=1)
        logits = t.model(inputs_embeds=e, attention_mask=mask, use_cache=False).logits
        lo = _pair_lo(logits, ids, rows, head)
        (g,) = torch.autograd.grad(lo, h)
        grads.append(g.detach().float().cpu().numpy())
        los.append(float(lo.detach()))
        del logits, lo, e, v, h, g
    return np.stack(grads), np.asarray(los, dtype=np.float64)


def olens_direction(reader: R.OLensReader, H: Any, pos: str, neg: str, layer: int) -> np.ndarray:
    """∇_h LO_olens averaged over the states ``H`` [n, d], unit-normalised (BRIEF_R §4.5)."""
    g, _ = olens_grads(reader, H, pos, neg, layer)
    return _unit(g.mean(0))


def functional_marker_hook(block: Any, marker: int, holder: dict[str, Any]) -> Any:
    """The NLA / skip-lens insertion (``readers.install_marker_add_hook``: row ← h₁ + ‖h₁‖·v/‖v‖ at the marker, prefill
    only) as an OUT-OF-PLACE hook: the block output is rebuilt with ``torch.cat`` instead of written in place, so autograd
    can take ∂/∂v through it. ``holder["v"]`` is ``[d]`` (one vector, broadcast to every row) or None (inert)."""
    import torch

    def hook(_mod, _inp, out):
        h = out[0] if isinstance(out, tuple) else out
        v = holder.get("v")
        if v is None or h.shape[1] <= marker:
            return out
        hp = h[:, marker, :]
        v = v.to(h.device)
        vu = v.to(h.dtype) / (v.norm().to(h.dtype) + 1e-9)
        row = hp + hp.norm(dim=-1, keepdim=True) * vu
        h2 = torch.cat([h[:, :marker], row[:, None, :], h[:, marker + 1:]], dim=1)
        return (h2,) + tuple(out[1:]) if isinstance(out, tuple) else h2

    return block.register_forward_hook(hook)


def hook_reader_rows(reader: Any, pos: str, neg: str, fam: str) -> tuple[list[list[int]], int]:
    """The teacher-forcing rows [(pos, neg) per template or LO form] and the head length, exactly as ``lo_nla`` (every
    template of the family) and ``lo_skiplens`` (the bare and leading-space forms) build them; the native LO is the mean
    over the pairs."""
    tok = reader.tokenizer
    if isinstance(reader, R.NLAReader):
        head = list(reader.ids) + LO.encode(tok, LO.NLA_PREFIX)
        forms = LO.templates_for(fam)
    else:
        head = list(reader.ids)
        forms = list(C.SKIPLENS_LO_FORMS)
    rows = [head + LO.encode(tok, f.format(X=c)) for f in forms for c in (pos, neg)]
    return rows, len(head)


def hook_reader_grads(reader: Any, H: Any, pos: str, neg: str, fam: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Skip-lens / NLA: per-state ∇_h LO (raw ``[n, d]``) and the LO, through the out-of-place marker hook (the reader's own
    in-place hook stays inert: ``_vec["v"]`` is None). Returns None — and the caller records a deviation — if autograd
    cannot go through this model's kernels."""
    import torch

    model = reader.model
    dev = next(model.parameters()).device
    rows, head = hook_reader_rows(reader, pos, neg, fam)
    ids, mask = _pad_rows(reader.tokenizer, rows, dev)
    holder: dict[str, Any] = {"v": None}
    handle = functional_marker_hook(M.blocks(model)[reader.inject_layer_idx], reader.marker, holder)
    H = torch.as_tensor(H).float()
    grads, los = [], []
    ctx = reader.active() if hasattr(reader, "active") else _null()
    try:
        reader._vec["v"] = None
        with ctx:
            for i in range(H.shape[0]):
                h = H[i].to(dev).clone().requires_grad_(True)
                holder["v"] = h
                logits = model(input_ids=ids, attention_mask=mask, use_cache=False).logits
                lo = _pair_lo(logits, ids, rows, head)
                (g,) = torch.autograd.grad(lo, h)
                grads.append(g.detach().float().cpu().numpy())
                los.append(float(lo.detach()))
                del logits, lo, h, g
    except (RuntimeError, NotImplementedError) as e:  # in-place / version-counter errors, kernels without backward
        print(f"[r5] {reader.name}: gradient not available through the hook ({str(e)[:160]})", flush=True)
        return None
    finally:
        holder["v"] = None
        handle.remove()
    return np.stack(grads), np.asarray(los, dtype=np.float64)


def hook_reader_direction(reader: Any, H: Any, pos: str, neg: str, fam: str) -> np.ndarray | None:
    r = hook_reader_grads(reader, H, pos, neg, fam)
    return None if r is None else _unit(r[0].mean(0))


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def finite_difference(reader: Any, h: Any, grad: Any, pos: str, neg: str, fam: str, layer: int, eps_rel: float = 1e-2) -> dict[str, Any]:
    """Central finite-difference check of a gradient: LO at h, h + ε·ĝ and h − ε·ĝ (ε = eps_rel·‖h‖, ĝ = grad/‖grad‖) in ONE
    ``score_lo`` batch; predicted change ε·‖grad‖. ``ratio_central`` = (LO₊ − LO₋)/(2·pred) is 1 for an exact gradient."""
    import torch

    h = torch.as_tensor(h).float()
    g = torch.as_tensor(grad).float()
    gn = float(g.norm())
    eps = float(eps_rel * h.norm())
    u = g / (gn + 1e-12)
    rows = LO.score_lo(reader, torch.stack([h, h + eps * u, h - eps * u]), [(pos, neg)] * 3, fam, layer=layer)
    lo0, lop, lom = (float(r["lo"]) for r in rows)
    pred = eps * gn
    return {"lo0": lo0, "lo_plus": lop, "lo_minus": lom, "delta_plus": lop - lo0, "central": (lop - lom) / 2, "pred": pred,
            "ratio_central": (lop - lom) / 2 / pred if pred > 0 else None, "ratio_forward": (lop - lo0) / pred if pred > 0 else None,
            "eps": eps, "eps_rel": eps_rel, "grad_norm": gn, "h_norm": float(h.norm())}


# ------------------------------------------------------------------ selection and directions
PATH_NAMES = ("R5_DIR", "DIR_DIR", "RB_DIR", "STEER_PATH", "READERS_PATH", "DEVIATIONS_PATH", "SELECTION",
              "PRECHECK_PATH")


def configure_paths(out_dir: Any = None, selection: Any = None, dir_dir: Any = None,
                    precheck_out: Any = None) -> dict[str, Path]:
    """Point this module at a different experiment's inputs and outputs, e.g. R5X beside R5.

    Every path is a module global read at call time, which is how the pod runner already redirects
    `C.COMPUTE_LEDGER` and `ST.LOG`. R5X needs this because BRIEF_R requires it to write its OWN rows under its own
    suffix while reading the R5X selection and directions: without it, `SELECTION` is pinned to `r5_selection.json`
    and the R5X run would silently append to R5's files. Returns the resolved paths so a caller can assert them.
    """
    g = globals()
    if out_dir is not None:
        root = Path(out_dir)
        g["R5_DIR"], g["DIR_DIR"], g["RB_DIR"] = root, root / "directions", root / "readback"
        g["STEER_PATH"], g["READERS_PATH"] = root / "steer.jsonl", root / "readers.jsonl"
        g["DEVIATIONS_PATH"] = root / "deviations.json"
        # PRECHECK_PATH is deliberately NOT derived from out_dir: a record-only precheck (Guiv, 2026-10-20, for Italy
        # and code_C) must be able to write its own file while everything else moves, so it has its own flag.
    if dir_dir is not None:
        g["DIR_DIR"] = Path(dir_dir)
    if selection is not None:
        g["SELECTION"] = Path(selection)
    if precheck_out is not None:
        g["PRECHECK_PATH"] = Path(precheck_out)
    return {n: g[n] for n in PATH_NAMES}


# Directions that live in the npz but are NEVER steered, so their conditions must not be required:
# BRIEF_R §4.5 puts the NLA's gradient in the cosine matrix only, and phase B writes `d_nla_L38` into the npz AFTER
# phase A has finished steering. Without this, auditing a CORRECT R5 run reports 90 empty conditions (3 alphas x 30
# datasets) — which is exactly what the real R5 data did on 2026-10-20, before this exclusion existed.
def stage_r5x(s2_selection: Any, dir_dir: Any, out_selection: Any, s1_selection: Any = None,
              s1_dir: Any = None, edit_layer: int = L_EDIT, exclude: dict[str, str] | None = None) -> dict[str, Any]:
    """Assemble R5X's inputs: the 40-fact selection (S1's 30 + S2's 10) and one directions npz per fact.

    R5X reuses S1's directions, which R5 already built, and takes S2's ten from WS3's own cache. Only the facts named
    in the selections are copied, which is how the four npz from WS3's withdrawn AUROC-band selection are excluded —
    they are not listed, so they are never looked at. Every fact is verified before anything is copied, and a single
    missing file or missing direction aborts the whole staging rather than leaving a half-built input set.

    Refuses to write into R5's own directions dir: BRIEF_R requires R5X to write its own rows and read its own inputs,
    and a staging step that polluted `r5/directions` would silently change what a re-run of R5 would read.
    """
    import hashlib
    import shutil

    s1_path = Path(s1_selection) if s1_selection else SELECTION
    src_s1 = Path(s1_dir) if s1_dir else (R5_DIR / "directions")
    dst = Path(dir_dir)
    if dst.resolve() == src_s1.resolve():
        raise SystemExit(f"refusing to stage into R5's own directions dir ({dst}): R5X must read and write its own")
    s1 = json.loads(s1_path.read_text())
    s2 = json.loads(Path(s2_selection).read_text())
    d1, d2 = dict(s1["datasets"]), dict(s2["datasets"])
    n_s1_source, n_s2_source = len(d1), len(d2)          # the files' own counts, before any exclusion
    # `exclude` maps dataset -> the reason, which is written into the selection's provenance. Used for facts a
    # pre-registered gate refused: the staging must then not copy their directions either, so the run cannot touch
    # them by accident. The reason travels with the data rather than living only in a brief or a chat message.
    dropped = {}
    for ds, why in (exclude or {}).items():
        if ds in d1:
            del d1[ds]; dropped[ds] = {"stratum": "S1", "reason": why}
        elif ds in d2:
            del d2[ds]; dropped[ds] = {"stratum": "S2", "reason": why}
        else:
            raise SystemExit(f"--exclude names {ds}, which is in neither selection: refusing to stage a set I "
                             f"cannot account for")
    both = sorted(set(d1) & set(d2))
    problems: list[str] = []
    if both:
        problems.append(f"S1 and S2 overlap on {both}: BRIEF_R requires S2 to exclude the existing 30")
    _ = n_s1_source
    # n_selected describes the SOURCE file, so it is checked before exclusions are applied. Checking it after made
    # staging refuse a legitimate exclusion of an S2 fact (arith_mc_A, 2026-10-20): 9 datasets vs n_selected 10.
    if s2.get("n_selected") is not None and n_s2_source != s2["n_selected"]:
        problems.append(f"S2's file lists {n_s2_source} datasets but records n_selected={s2['n_selected']}")
    if s2.get("label_defects_among_selected"):
        problems.append(f"S2 records label defects among the selected: {s2['label_defects_among_selected']}")
    src_s2 = Path(s2.get("directions_dir") or "")
    plan: list[tuple[str, Path, str]] = []
    for ds in d1:
        plan.append((ds, src_s1 / f"{ds}.npz", "S1"))
    for ds in d2:
        plan.append((ds, src_s2 / f"{ds}.npz", "S2"))
    need = (f"d_cm_L{edit_layer}", f"d_probe_L{edit_layer}")
    checked: list[dict[str, Any]] = []
    for ds, src, stratum in plan:
        if not src.exists():
            problems.append(f"{stratum} {ds}: no directions npz at {src}")
            continue
        with np.load(src) as z:
            keys = list(z.files)
        missing = [k for k in need if k not in keys]
        if missing:
            problems.append(f"{stratum} {ds}: {src.name} lacks {missing} (has {sorted(keys)[:6]})")
            continue
        checked.append({"dataset": ds, "stratum": stratum, "src": str(src), "keys": sorted(keys),
                        "sha256": hashlib.sha256(src.read_bytes()).hexdigest()})
    if problems:
        raise SystemExit("R5X staging refused, nothing copied:\n  " + "\n  ".join(problems))
    dst.mkdir(parents=True, exist_ok=True)
    for c in checked:
        shutil.copy2(c["src"], dst / f"{c['dataset']}.npz")
    merged = {"created": now_iso(), "experiment": "R5X",
              "strata": {"S1": sorted(d1), "S2": sorted(d2)}, "excluded": dropped,
              "provenance": {"s1_selection": str(s1_path), "s1_selection_sha256": hashlib.sha256(s1_path.read_bytes()).hexdigest(),
                             "s2_selection": str(s2_selection),
                             "s2_selection_sha256": hashlib.sha256(Path(s2_selection).read_bytes()).hexdigest(),
                             "s2_rule": s2.get("rule"), "s2_realised_band": s2.get("realised_band"),
                             "directions_staged_to": str(dst), "directions": checked},
              "datasets": {**{ds: dict(spec, stratum="S1") for ds, spec in d1.items()},
                           **{ds: dict(spec, stratum="S2") for ds, spec in d2.items()}}}
    out = Path(out_selection)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=1))
    return {"n_facts": len(merged["datasets"]), "n_s1": len(d1), "n_s2": len(d2), "excluded": sorted(dropped),
            "selection": str(out), "dir_dir": str(dst), "staged": [c["dataset"] for c in checked]}


NOT_STEERED = ("d_nla",)


def audit_conditions(sel: dict[str, Any], alphas: tuple[float, ...], k_random: int,
                     edit_layer: int = L_EDIT) -> tuple[list[str], dict[str, Any]]:
    """PODS.md rule 5 for R5/R5X: every (dataset, direction, alpha) condition must hold one row per item AND one
    saved read-back state per item. Reads files only — no model, no GPU.

    The failure this exists to catch is the one that cost a pod launch on 2026-10-19 in the SWAP module: a direction
    that silently resolves to nothing leaves its condition empty while the control conditions run normally, and a
    row-count total alone does not show it. The swap analogue is `swap.py --phase audit`.
    """
    rows = read_jsonl(STEER_PATH)
    have = collections.Counter((r.get("dataset"), r.get("direction"), float(r.get("alpha", 0.0))) for r in rows)
    # GUARDS.md rule 3: say which processes and what kind of run wrote these rows. Several run ids per FILE are
    # legitimate (R5X runs one dose segment per process); a non-"real" kind in a real file is not.
    kinds = collections.Counter(r.get("run_kind") for r in rows)
    runs = {r.get("run_id") for r in rows if r.get("run_id")}
    prov: list[str] = []
    # The hazard is a file that MIXES kinds — a smoke or test row beside real ones, which is exactly the 2026-10-19
    # and 2026-10-20 incidents. A file of one uniform kind is self-describing and fine, whatever that kind is; failing
    # on "not real" instead would flag every legitimate test run, which is how a guard trains people to ignore it.
    kinds_present = {k for k in kinds if k is not None}
    if len(kinds_present) > 1:
        prov.append(f"SMOKE FAILED: {STEER_PATH.name} MIXES run kinds {dict(kinds)} — rows from different kinds of "
                    f"run are in one file, so a smoke or test row sits beside real ones")
    unstamped = kinds.get(None, 0)
    notes = []
    if unstamped:
        notes.append(f"NOTE: {unstamped} row(s) predate run_id/run_kind stamping (GUARDS.md rule 3, 2026-10-20); "
                     f"identify them by created_at and the pod log, not by the row")
    if runs:
        notes.append(f"NOTE: rows come from {len(runs)} stamped run(s); one per dose segment is expected")
    fails: list[str] = list(prov)
    summary: dict[str, Any] = {"rows": len(rows), "datasets": len(sel), "conditions": 0, "states": 0,
                               "empty_conditions": 0, "short_conditions": 0, "missing_state_files": 0,
                               "run_ids": len(runs), "run_kinds": dict(kinds), "notes": notes}
    for ds, spec in sorted(sel.items()):
        n = len(spec["item_ids"])
        try:
            dirs = directions_for(ds)
        except (SystemExit, FileNotFoundError, OSError) as e:
            fails.append(f"SMOKE FAILED: {ds} has no usable directions npz ({e})")
            continue
        names = [k for k in dirs if k.startswith("d_") and k.endswith(f"_L{edit_layer}")
                 and not k.startswith("d_rand") and not any(k.startswith(x) for x in NOT_STEERED)]
        if not names:
            fails.append(f"SMOKE FAILED: {ds} npz holds no named direction at block {edit_layer} "
                         f"(keys: {sorted(dirs)[:6]}) — the primary arms would all be empty")
        all_dirs = names + [f"d_rand{i}_L{edit_layer}" for i in range(k_random)]
        conds = [("natural", 0.0)] + [(d, float(a)) for d in all_dirs for a in alphas]
        for dname, alpha in conds:
            summary["conditions"] += 1
            k = have.get((ds, dname, alpha), 0)
            if k == 0:
                summary["empty_conditions"] += 1
                fails.append(f"SMOKE FAILED: {ds}/{dname}@a{alpha} has NO rows (expected {n})")
            elif k != n:
                summary["short_conditions"] += 1
                fails.append(f"SMOKE FAILED: {ds}/{dname}@a{alpha} has {k} rows, expected {n}")
            f = RB_DIR / ds / f"{dname}_a{alpha}.npy"
            if not f.exists():
                summary["missing_state_files"] += 1
                fails.append(f"SMOKE FAILED: {ds}/{dname}@a{alpha} has no read-back file ({f.name})")
                continue
            got = int(np.load(f, mmap_mode="r").shape[0])
            summary["states"] += got
            if got != n:
                fails.append(f"SMOKE FAILED: {ds}/{dname}@a{alpha} saved {got} states for {n} items")
        # Rows can also exist for conditions the CURRENT npz no longer describes — phase B adds keys, and an earlier
        # key naming was superseded (`directions_pre_gradkeys`). Those are not failures by themselves, but they must
        # be counted rather than passed over in silence, or an empty condition could hide behind a renamed direction.
        expected = {(dname, a) for dname, a in conds}
        extra = collections.Counter((r["direction"], float(r["alpha"])) for r in rows
                                    if r.get("dataset") == ds and (r.get("direction"), float(r.get("alpha", 0.0))) not in expected)
        if extra:
            summary["unexpected_conditions"] = summary.get("unexpected_conditions", 0) + len(extra)
            summary.setdefault("notes", []).append(
                f"NOTE: {ds} has rows for {len(extra)} condition(s) the current npz does not describe "
                f"({sorted({d for d, _ in extra})[:4]}); not audited against an expectation")
        for (dname, alpha), k in sorted(extra.items()):
            if k != n:                      # a partially written condition is a failure whatever its name
                fails.append(f"SMOKE FAILED: {ds}/{dname}@a{alpha} (unexpected) has {k} rows, expected {n}")
    return fails, summary


def load_selection() -> dict[str, Any]:
    if not SELECTION.exists():
        raise SystemExit(f"{SELECTION} missing: run analyze --r5-select first")
    return json.loads(SELECTION.read_text())


def directions_for(ds: str) -> dict[str, np.ndarray]:
    p = DIR_DIR / f"{ds}.npz"
    if not p.exists():
        raise SystemExit(f"{p} missing: run analyze --r5-select first")
    z = np.load(p)
    return {k: z[k].astype(np.float32) for k in z.files}


def save_directions(ds: str, dirs: dict[str, np.ndarray]) -> None:
    DIR_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(DIR_DIR / f"{ds}.npz", **dirs)


def require_edit_directions(ds: str, dirs: dict[str, np.ndarray], edit_layer: int = L_EDIT) -> None:
    for k in (f"d_cm_L{edit_layer}", f"d_probe_L{edit_layer}"):
        if k not in dirs:
            raise SystemExit(f"{ds}: {k} missing from {DIR_DIR / (ds + '.npz')}: analyze --r5-select needs block-{edit_layer} states "
                             f"(collect.LAYERS must include {edit_layer}; see results/g_agreement/r/HANDOFF.md)")


def random_directions(ds: str, k: int, d: int = C.D_MODEL, edit_layer: int = L_EDIT, seed: int = RANDOM_SEED) -> dict[str, np.ndarray]:
    """K seeded unit directions per dataset (process-independent seed)."""
    rng = np.random.default_rng(seed + RC.stable_offset(ds))
    return {f"d_rand{i}_L{edit_layer}": _unit(rng.standard_normal(d).astype(np.float32)) for i in range(k)}


def cos_table(dirs: dict[str, np.ndarray], suffix: str) -> dict[str, float]:
    names = [k for k in dirs if k.endswith(suffix)]
    return {f"{a}~{b}": float(dirs[a] @ dirs[b]) for i, a in enumerate(names) for b in names[i + 1:]}


def record_deviation(reader: str, ds: str, reason: str) -> None:
    R5_DIR.mkdir(parents=True, exist_ok=True)
    dev = json.loads(DEVIATIONS_PATH.read_text()) if DEVIATIONS_PATH.exists() else []
    dev.append({"reader": reader, "dataset": ds, "reason": reason, "created_at": now_iso()})
    DEVIATIONS_PATH.write_text(json.dumps(dev, indent=1))
    log_line(LOG, f"r5 DEVIATION {reader} {ds}: {reason}")


def _code_sha() -> str:
    """sha256 of THIS file. GUARDS.md rule 3 (PODS.md rule 10), mirroring swap.py's version — the helper is duplicated
    per module rather than shared because `core/accounting.py` is inside the freeze's core_code_sha256."""
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except OSError:
        return "unknown"


CODE_SHA = _code_sha()
RUN_ID = RC.RUN_ID                                        # one id per process, from collect.py
# run kind comes from RC (default "unknown"); a real run declares --run-kind real
_GPU: dict[str, str] = {}


def gpu_tag() -> str:
    """The accelerator this row was computed on, for every row of steer / swap / report_flip (Guiv, 2026-10-20).

    E5 runs on an RTX PRO 6000 while R5, R5X and SWAP ran on H100s, and bf16 kernels and reduction order are
    device-dependent: the zero-delta scale and the KL are not bit-comparable across cards, so a row that does not say
    where it ran cannot be compared with one that does. `gpu_name()` is "cpu" without CUDA, which is the honest answer
    for the audit phases (they load no model). Cached only once a real device has answered, never while it reads "cpu",
    so a value captured before CUDA is up is not frozen in — the stale-stamp failure GUARDS.md rule 2 cites.
    """
    if _GPU.get("gpu", "cpu") == "cpu":
        _GPU["gpu"] = gpu_name()
    return _GPU["gpu"]


def stamp() -> dict[str, Any]:
    """GUARDS.md rule 3, via WS2's shared `collect.row_meta()` (scaffold f4ea50b) rather than a parallel copy.

    row_meta carries run_id, run_started_at, run_kind, pod, shard and git_sha, maintained in one place; this module
    overrides `code_sha256` with ITS OWN file's hash, because row_meta's is collect.py's. Evaluated at call time, so a
    later `--run-kind` declaration is reflected — a stamp frozen at import was the decoy finding GUARDS.md cites.
    `gpu` says which accelerator computed the row (see `gpu_tag`).
    """
    return {**RC.row_meta(), "code_sha256": CODE_SHA, "gpu": gpu_tag()}


SKIP_FALLBACK = "d_cm fallback"      # marks a deviation that routes a skip-lens onto the class mean
ZD_DRAWS_MAX = 3                     # adopted 2026-10-20: 1 draw if deterministic, else the median of 3


def deterministic_mode(on: bool = True) -> dict[str, Any]:
    """Ask torch for deterministic kernels, for the precheck only.

    Adopted by Guiv 2026-10-20 after two precheck runs on identical inputs disagreed on 30 of 38 facts, flipping three
    pass/fail: `max_abs_dlo_vs_collected` lives on a 0.125 bf16 lattice and non-deterministic reduction order moves it
    by 1-2 steps. `warn_only=True` so an op without a deterministic kernel warns instead of raising — the replication
    below then detects that determinism was not reached and the median path takes over. Returns what was applied, so
    the record says which path decided rather than leaving it to be inferred.
    """
    import os

    import torch
    cfg = os.environ.get("CUBLAS_WORKSPACE_CONFIG")
    applied: dict[str, Any] = {"requested": on, "cublas_workspace_config": cfg}
    if on and cfg not in (":4096:8", ":16:8"):
        # Not fatal: the replication below still detects whether determinism was actually reached. But the record must
        # not imply a guarantee it does not have, so say it outright.
        applied["warning"] = (f"CUBLAS_WORKSPACE_CONFIG={cfg!r}: PyTorch documents ':4096:8' for deterministic cuBLAS "
                              f"and it must be set before CUDA initialises. Determinism here rests on the replication "
                              f"agreeing, not on the documented configuration.")
    try:
        torch.use_deterministic_algorithms(on, warn_only=True)
        applied["use_deterministic_algorithms"] = on
    except Exception as e:                            # noqa: BLE001 — never let this abort a gate
        applied["use_deterministic_algorithms"] = f"unavailable: {type(e).__name__}"
    return applied


def zd_vs_collected(draw: Any, draws_max: int = ZD_DRAWS_MAX) -> dict[str, Any]:
    """Repeat `draw()` until two consecutive draws agree, or `draws_max` times, and report which path decided.

    `draw()` returns the realised max |ΔLO| against the collected rows (or None). Two identical draws mean the
    measurement is reproducible in this process, and the single value stands. Otherwise the MEDIAN of the draws
    decides: the median changes the variance, not the bar, where best-of-k would lower it and worst-of-k raise it.
    """
    vals: list[float | None] = [draw()]
    if vals[0] is not None:
        vals.append(draw())
        if vals[1] != vals[0]:                        # not reproducible: take the third and use the median
            while len(vals) < draws_max:
                vals.append(draw())
    clean = [v for v in vals if v is not None]
    if not clean:
        return {"value": None, "draws": vals, "decided_by": "no comparison available"}
    if len(clean) >= 2 and clean[0] == clean[1]:
        return {"value": clean[0], "draws": clean, "decided_by": "deterministic (two draws agreed)"}
    med = float(np.median(np.array(clean, dtype=float)))
    return {"value": med, "draws": clean, "decided_by": f"median of {len(clean)} draws (determinism not reached)"}


def deviation_recorded(reader: str, ds: str, contains: str | None = None) -> bool:
    """Has a deviation been recorded for this (reader, dataset)? `contains` narrows it to a kind of deviation."""
    if not DEVIATIONS_PATH.exists():
        return False
    try:
        dev = json.loads(DEVIATIONS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    return any(d.get("reader") == reader and d.get("dataset") == ds
               and (contains is None or contains in str(d.get("reason", ""))) for d in dev)


def item_renders(tok: Any, items: dict[str, dict[str, Any]], order: list[str]) -> dict[str, list[Any]]:
    """Prompt-only and chat renders with the text span of each (the text as rendered, i.e. truncated like the renders)."""
    po_ids, ch_ids, span_po, span_ch, signs, texts = [], [], [], [], [], []
    for iid in order:
        it = items[iid]
        text = rendered_text(tok, it["prompt_text"])
        po_ids.append(RC.prompt_only_ids(tok, it))
        ch_ids.append(RC.render_ids(tok, it["prompt_text"], "chat"))
        span_po.append(text_span(tok, po_ids[-1], text, anchor=ANCHOR_PO))
        span_ch.append(text_span(tok, ch_ids[-1], text, anchor=ANCHOR_CHAT))
        signs.append(-1.0 if it["label"] == 1 else 1.0)   # push toward the OTHER class (d_* are oriented neg → pos)
        texts.append(text)
    return {"po_ids": po_ids, "ch_ids": ch_ids, "span_po": span_po, "span_ch": span_ch, "signs": signs, "texts": texts}


def grad_directions(target: M.Target, readers: list[Any], ds: str, sel: dict[str, Any], items: dict[str, dict[str, Any]],
                    dirs: dict[str, np.ndarray], read_layer: int = L_READ, edit_layer: int = L_EDIT) -> dict[str, np.ndarray]:
    """d_<reader>_L<read> (gradient of the reader's LO on the natural chat states of the selected items, averaged, unit) and
    d_<reader>_L<edit> (the same vector, transported to the edit layer); for the J-lens also d_jlens<edit>_L<edit>, the analytic
    gradient at the edit layer itself (variants chosen on the block-<edit> states when captured, else on the read-layer
    states). Existing reader entries are overwritten (a stale npz never survives a re-run)."""
    import torch

    tok = target.tokenizer
    first = items[sel["item_ids"][0]]["primary"]
    fam = RC.register_templates(first)
    X, idx = RC.load_states(ds, "chat", read_layer)
    pos_of = {iid: i for i, iid in enumerate(idx)}
    H = torch.from_numpy(X[[pos_of[i] for i in sel["item_ids"]]])
    try:
        Xe, idxe = RC.load_states(ds, "chat", edit_layer)
        He = torch.from_numpy(Xe[[{iid: i for i, iid in enumerate(idxe)}[i] for i in sel["item_ids"]]])
        He_layer = edit_layer
    except FileNotFoundError:
        He, He_layer = H, read_layer
    ledger = StepLedger(step="grad_directions", module=MODULE, extra={"dataset": ds})
    with timed_call() as st:
        for rd in readers:
            pos, neg = RC.reader_candidates(rd.name, first)
            if isinstance(rd, R.JLensReader):
                g = jlens_direction(rd, tok, pos, neg, read_layer, H=H)
                if g is not None and edit_layer in rd.J:
                    dirs[f"d_jlens{edit_layer}_L{edit_layer}"] = jlens_direction(rd, tok, pos, neg, edit_layer, H=He, H_layer=He_layer)
                if g is None:
                    record_deviation(rd.name, ds, f"no single-token variant for {pos!r}/{neg!r}: J-lens unscorable, no direction")
            elif isinstance(rd, R.OLensReader):
                g = olens_direction(rd, H, pos, neg, read_layer)
            else:
                g = hook_reader_direction(rd, H, pos, neg, fam)
                if g is None:
                    record_deviation(rd.name, ds, "not differentiable in this harness (autograd through the block-1 marker hook failed)")
            if g is not None and rd.name.startswith("skip") and deviation_recorded(rd.name, ds, SKIP_FALLBACK):
                # The precheck could not verify this gradient, so the brief routes the skip-lens onto d_cm. Writing
                # the direction anyway would let steering use an unverified gradient while the record claims otherwise.
                log_line(LOG, f"r5 {ds}: withholding d_{rd.name}_L* ({SKIP_FALLBACK} recorded by the precheck)")
                g = None
            if g is not None:
                dirs[f"d_{rd.name}_L{read_layer}"] = g
                dirs[f"d_{rd.name}_L{edit_layer}"] = g   # transported: the edit happens at L_edit along what the reader reads at L_read
    ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush()
    save_directions(ds, dirs)
    cos = cos_table(dirs, f"_L{edit_layer}")
    log_line(LOG, f"r5 directions {ds} (L{edit_layer}): " + ", ".join(f"{k} {v:+.2f}" for k, v in cos.items()))
    return dirs


# ------------------------------------------------------------------ steering
def steer_dataset(target: M.Target, ds: str, sel: dict[str, Any], items: dict[str, dict[str, Any]], dirs: dict[str, np.ndarray],
                  alphas: tuple[float, ...] = ALPHAS, read_layer: int = L_READ, edit_layer: int = L_EDIT, batch: int = 16,
                  k_random: int = N_RANDOM) -> None:
    """For every selected item and direction: the model's forced-choice LO after the edit (prompt-only render) and the
    read-back state (chat render), both with the same text span edited at ``edit_layer``. One forward per batch of items
    carries a per-row delta (sign per item), both candidates of an item in the same forward."""
    import torch

    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    scale = float(sel["scale"])  # ‖mean_pos − mean_neg‖ of the pool states at L_edit (analyze --r5-select)
    require_edit_directions(ds, dirs, edit_layer)
    done = done_ids(STEER_PATH, key="key")
    ledger = StepLedger(step=f"steer_{ds}", module=MODULE)
    names = [k for k in dirs if k.startswith("d_") and k.endswith(f"_L{edit_layer}") and not k.startswith("d_rand")]
    d_model = int(dirs[f"d_cm_L{edit_layer}"].shape[0])
    dirs.update(random_directions(ds, k_random, d=d_model, edit_layer=edit_layer))
    save_directions(ds, dirs)
    all_dirs = names + [f"d_rand{i}_L{edit_layer}" for i in range(k_random)]
    order = list(sel["item_ids"])
    rd = item_renders(tok, items, order)
    po_ids, ch_ids, span_po, span_ch, signs = rd["po_ids"], rd["ch_ids"], rd["span_po"], rd["span_ch"], rd["signs"]
    cands = items[order[0]]["primary"]["candidates"]
    d_out = RB_DIR / ds
    d_out.mkdir(parents=True, exist_ok=True)
    conds: list[tuple[str, float]] = [("natural", 0.0)] + [(dname, alpha) for dname in all_dirs for alpha in alphas]
    for dname, alpha in conds:
        keys = [f"{ds}|{iid}|{dname}|{alpha}" for iid in order]
        out_npy = d_out / f"{dname}_a{alpha}.npy"
        if all(k in done for k in keys) and out_npy.exists():
            continue
        dvec = None if dname == "natural" else dirs[dname]
        lo_rows: list[tuple[float, float]] = []
        reads: list[np.ndarray] = []
        n_tok = 0
        with timed_call() as st:
            for s in range(0, len(order), batch):
                idxs = list(range(s, min(s + batch, len(order))))
                if dvec is None:
                    delta_items = np.zeros((len(idxs), d_model), dtype=np.float32)
                else:
                    delta_items = np.stack([(signs[i] * alpha * scale * dvec).astype(np.float32) for i in idxs])
                # (a) the model's forced-choice answer: both candidates of every item in one batch (same delta for both rows)
                rows, spans, heads = [], [], []
                for i in idxs:
                    for c in cands:
                        rows.append(po_ids[i] + LO.encode(tok, c))
                        spans.append(span_po[i])
                        heads.append(len(po_ids[i]))
                delta_po = np.repeat(delta_items, len(cands), axis=0)
                lps, _ = edited_forward_batch(target.model, rows, spans, edit_layer, torch.from_numpy(delta_po), pad, head_lens=heads)
                for j, i in enumerate(idxs):
                    lo_rows.append((i, lps[2 * j], lps[2 * j + 1]))
                # (b) the read-back state from the chat render with the same edit
                _, H = edited_forward_batch(target.model, [ch_ids[i] for i in idxs], [span_ch[i] for i in idxs], edit_layer,
                                            torch.from_numpy(delta_items), pad, head_lens=None, read_layer=read_layer)
                for j, i in enumerate(idxs):
                    reads.append((i, H[j].numpy().astype(np.float16)))
                n_tok += sum(len(r) for r in rows) + sum(len(ch_ids[i]) for i in idxs)
        lo_rows.sort(key=lambda x: x[0])
        reads.sort(key=lambda x: x[0])
        np.save(out_npy, np.stack([v for _, v in reads]))
        for (i, lp_pos, lp_neg), key in zip(lo_rows, keys):
            if key in done:
                continue
            iid = order[i]
            append_jsonl(STEER_PATH, {"key": key, "module": MODULE, **stamp(), "dataset": ds, "item_id": iid, "label": items[iid]["label"],
                                      "direction": dname, "alpha": alpha, "sign": signs[i], "scale": scale, "edit_layer": edit_layer,
                                      "read_layer": read_layer, "span_prompt_only": list(span_po[i]), "span_chat": list(span_ch[i]),
                                      "candidates": cands, "lp_pos": lp_pos, "lp_neg": lp_neg, "lo": lp_pos - lp_neg, "created_at": now_iso()})
        ledger.add(n_tok, 0, st.wall_s, st.peak_mem_gb)
    (d_out / "index.json").write_text(json.dumps({"item_ids": order, "directions": ["natural"] + all_dirs, "alphas": list(alphas),
                                                  "scale": scale, "edit_layer": edit_layer, "read_layer": read_layer,
                                                  "span_prompt_only": [list(s) for s in span_po], "span_chat": [list(s) for s in span_ch]}, indent=1))
    r = ledger.flush()
    log_line(LOG, f"r5 steer {ds}: {len(order)} items × {len(all_dirs)} directions × {len(alphas)} doses {r}")


def read_back(reader: Any, ds: str, items: dict[str, dict[str, Any]], read_layer: int = L_READ, batch: int = 32) -> int:
    """Every reader's native scores on every read-back state of the dataset."""
    import torch

    d_in = RB_DIR / ds
    idx = json.loads((d_in / "index.json").read_text())
    first = items[idx["item_ids"][0]]["primary"]
    fam = RC.register_templates(first)
    pos, neg = RC.reader_candidates(reader.name, first)
    done = done_ids(READERS_PATH, key="key")
    ledger = StepLedger(step=f"lo_{reader.name}", module=MODULE, extra={"dataset": ds})
    n = 0
    for f in sorted(d_in.glob("*.npy")):
        dname, a = f.stem.rsplit("_a", 1)
        alpha = float(a)
        keys = [f"{reader.name}|{ds}|{iid}|{dname}|{alpha}" for iid in idx["item_ids"]]
        if all(k in done for k in keys):
            continue
        H = torch.from_numpy(np.load(f).astype(np.float32))
        with timed_call() as st:
            rows = LO.score_lo(reader, H, [(pos, neg)] * H.shape[0], fam, layer=read_layer, batch=batch)
        for iid, key, r in zip(idx["item_ids"], keys, rows):
            if key in done:
                continue
            append_jsonl(READERS_PATH, {"key": key, "module": MODULE, **stamp(), "reader": reader.name, "dataset": ds, "item_id": iid,
                                        "label": items[iid]["label"], "direction": dname, "alpha": alpha, "lp_A": r["lp_A"], "lp_B": r["lp_B"],
                                        "lo": r["lo"], "unscorable": r["unscorable"], "created_at": now_iso()})
            n += 1
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush()
    return n


def probe_rows(ds: str, items: dict[str, dict[str, Any]], dirs: dict[str, np.ndarray], read_layer: int = L_READ) -> int:
    """The probe score of BRIEF_R §4.5 on every read-back state, as pseudo-reader ``probe``: the state projected on the unit
    probe direction at the read layer (lp_A = projection, lp_B = 0, lo = projection; monotone in the probe's decision function)."""
    w = dirs.get(f"d_probe_L{read_layer}")
    if w is None:
        return 0
    d_in = RB_DIR / ds
    idx = json.loads((d_in / "index.json").read_text())
    done = done_ids(READERS_PATH, key="key")
    n = 0
    for f in sorted(d_in.glob("*.npy")):
        dname, a = f.stem.rsplit("_a", 1)
        alpha = float(a)
        H = np.load(f).astype(np.float32)
        proj = H @ w
        for iid, p in zip(idx["item_ids"], proj):
            key = f"{PROBE_READER}|{ds}|{iid}|{dname}|{alpha}"
            if key in done:
                continue
            append_jsonl(READERS_PATH, {"key": key, "module": MODULE, **stamp(), "reader": PROBE_READER, "dataset": ds, "item_id": iid,
                                        "label": items[iid]["label"], "direction": dname, "alpha": alpha, "lp_A": float(p), "lp_B": 0.0,
                                        "lo": float(p), "unscorable": False, "created_at": now_iso()})
            n += 1
    return n


# ------------------------------------------------------------------ pre-checks (PLAN_R §1 WS4)
FD_BAND = (0.5, 2.0)        # pre-registered "≈ ε·‖∇‖" on the bf16 pod: central ratio inside this band and LO(h + εĝ) − LO(h) > 0
ZERO_DELTA_TOL = 1e-3       # hooked zero delta vs the un-hooked forward, same batch
CACHE_LO_TOL = 0.3          # vs the collected prompt-only LO (a different batch composition: Suraj's 0.26-nat rule)
CACHE_COS_MIN = 0.999       # natural read-back vs the cached chat state at the read layer (batched capture, different batch)


def precheck(target: M.Target, readers: list[Any], ds: str, sel: dict[str, Any], items: dict[str, dict[str, Any]], n_span: int = 20,
             n_zero: int = 4, n_fd: int = 2, read_layer: int = L_READ, edit_layer: int = L_EDIT, eps_rel: float = 1e-2) -> dict[str, Any]:
    """The four WS4 pre-checks on one dataset; returns the record written to ``r5_prechecks.json`` (every number, one
    ``pass`` flag per check, and the deviation text where a gradient is not available)."""
    import torch

    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    order = list(sel["item_ids"])
    first = items[order[0]]["primary"]
    fam = RC.register_templates(first)
    cands = first["candidates"]
    out: dict[str, Any] = {"dataset": ds, "n_items": len(order), "edit_layer": edit_layer, "read_layer": read_layer,
                           "created_at": now_iso(), "deterministic": deterministic_mode(True), "checks": {}}
    # 1. text span in both renders
    rd = item_renders(tok, items, order[:n_span])
    sp = {"chat": [span_check(tok, rd["ch_ids"][i], rd["span_ch"][i], rd["texts"][i]) for i in range(len(rd["texts"]))],
          "prompt_only": [span_check(tok, rd["po_ids"][i], rd["span_po"][i], rd["texts"][i]) for i in range(len(rd["texts"]))]}
    rec: dict[str, Any] = {"n": len(rd["texts"])}
    for k, v in sp.items():
        rec[k] = {"exact": sum(x["exact"] for x in v), "contains": sum(x["contains"] for x in v), "max_extra_chars": max(x["extra_chars"] for x in v),
                  "span_tokens_mean": float(np.mean([x["n_tokens"] for x in v]))}
    rec["pass"] = all(rec[k]["contains"] == rec["n"] and rec[k]["max_extra_chars"] <= 8 for k in sp)
    out["checks"]["text_span"] = rec
    # 2. zero delta == un-hooked forward (same batch), and vs the collected prompt-only LO / cached chat state
    idxs = list(range(min(n_zero, len(order))))
    rows, spans, heads = [], [], []
    for i in idxs:
        for c in cands:
            rows.append(rd["po_ids"][i] + LO.encode(tok, c))
            spans.append(rd["span_po"][i])
            heads.append(len(rd["po_ids"][i]))
    d_model = int(target.model.get_input_embeddings().weight.shape[1])
    zero = torch.zeros(len(rows), d_model)
    lp_hook, _ = edited_forward_batch(target.model, rows, spans, edit_layer, zero, pad, head_lens=heads)
    lp_ref, _ = edited_forward_batch(target.model, rows, spans, edit_layer, None, pad, head_lens=heads)
    lo_hook = [lp_hook[2 * j] - lp_hook[2 * j + 1] for j in range(len(idxs))]
    lo_ref = [lp_ref[2 * j] - lp_ref[2 * j + 1] for j in range(len(idxs))]
    ch_rows = [rd["ch_ids"][i] for i in idxs]
    ch_spans = [rd["span_ch"][i] for i in idxs]
    _, H_hook = edited_forward_batch(target.model, ch_rows, ch_spans, edit_layer, zero[: len(idxs)], pad, read_layer=read_layer)
    _, H_ref = edited_forward_batch(target.model, ch_rows, ch_spans, edit_layer, None, pad, read_layer=read_layer)
    rec = {"n": len(idxs), "max_abs_dlo_vs_unhooked": float(np.max(np.abs(np.array(lo_hook) - np.array(lo_ref)))),
           "max_abs_dstate_vs_unhooked": float((H_hook - H_ref).abs().max()), "lo_natural": lo_hook}
    po_files = sorted(RC.PO_PATH.parent.glob(f"{RC.PO_PATH.stem}*{RC.PO_PATH.suffix}"))   # every shard (PLAN_R §9 rule 2)
    po_rows = {r["item_id"]: r for f in po_files for r in read_jsonl(f) if r.get("dataset") == ds}
    rec["prompt_only_files"] = [f.name for f in po_files]

    def _vs_collected(lo: list[float]) -> float | None:
        d = [abs(lo[j] - po_rows[order[i]]["lo"]) for j, i in enumerate(idxs)
             if order[i] in po_rows and po_rows[order[i]].get("lo") is not None]
        return float(max(d)) if d else None

    def _draw() -> float | None:
        lp, _ = edited_forward_batch(target.model, rows, spans, edit_layer, zero, pad, head_lens=heads)
        return _vs_collected([lp[2 * j] - lp[2 * j + 1] for j in range(len(idxs))])

    # The FIRST draw is the pre-fix quantity, kept so the run can report old-check vs new-check pass counts
    # descriptively, as Guiv asked. The decided value is the deterministic one, or the median of three.
    single_draw = _vs_collected(lo_hook)                          # NB: `first` is the item's primary dict, not this
    rep = zd_vs_collected(lambda: _draw() if single_draw is not None else None)
    rec["vs_collected_single_draw"] = single_draw                 # the old check's input
    rec["vs_collected_draws"] = rep["draws"]
    rec["vs_collected_decided_by"] = rep["decided_by"]
    rec["max_abs_dlo_vs_collected"] = rep["value"] if rep["value"] is not None else single_draw
    try:
        X, xidx = RC.load_states(ds, "chat", read_layer)
        pos_of = {iid: i for i, iid in enumerate(xidx)}
        Hc = torch.from_numpy(X[[pos_of[order[i]] for i in idxs]])
        rec["min_cos_vs_cached_state"] = float(torch.nn.functional.cosine_similarity(H_hook, Hc, dim=1).min())
    except (FileNotFoundError, KeyError):
        rec["min_cos_vs_cached_state"] = None
    # BRIEF_R WS4 (amended 2026-10-18): a comparison that could not be made FAILS the check; it never passes by default
    rec["missing_comparisons"] = [k for k in ("max_abs_dlo_vs_collected", "min_cos_vs_cached_state") if rec[k] is None]
    if rec["missing_comparisons"]:
        rec["reason"] = ("could not compare against " + ", ".join(rec["missing_comparisons"])
                         + f"; prompt_only files found: {rec['prompt_only_files']}")
    rec["pass"] = (not rec["missing_comparisons"]
                   and rec["max_abs_dlo_vs_unhooked"] < ZERO_DELTA_TOL and rec["max_abs_dstate_vs_unhooked"] < ZERO_DELTA_TOL
                   and rec["max_abs_dlo_vs_collected"] < CACHE_LO_TOL
                   and rec["min_cos_vs_cached_state"] >= CACHE_COS_MIN)
    rec["pass_single_draw_old_check"] = (rec["vs_collected_single_draw"] is not None
                                         and rec["vs_collected_single_draw"] < CACHE_LO_TOL
                                         and rec["max_abs_dlo_vs_unhooked"] < ZERO_DELTA_TOL
                                         and rec["max_abs_dstate_vs_unhooked"] < ZERO_DELTA_TOL
                                         and (rec["min_cos_vs_cached_state"] or 0) >= CACHE_COS_MIN)
    out["checks"]["zero_delta"] = rec
    # 3./4. gradients: Oracle (autograd through the embedding), hook readers (autograd through the out-of-place marker hook), J-lens (analytic)
    X, xidx = RC.load_states(ds, "chat", read_layer)
    pos_of = {iid: i for i, iid in enumerate(xidx)}
    H = torch.from_numpy(X[[pos_of[i] for i in order[:n_fd]]])
    for reader in readers:
        pos, neg = RC.reader_candidates(reader.name, first)
        rec = {"n": int(H.shape[0]), "items": []}
        if isinstance(reader, R.JLensReader):
            G = jlens_grads(reader, tok, pos, neg, read_layer, H=H)
            if G is None:
                rec["deviation"] = f"no single-token variant for {pos!r}/{neg!r}: J-lens unscorable on this fact"
            else:
                for i in range(H.shape[0]):
                    rec["items"].append(finite_difference(reader, H[i], G[i], pos, neg, fam, read_layer, eps_rel))
        else:
            res = olens_grads(reader, H, pos, neg, read_layer) if isinstance(reader, R.OLensReader) else hook_reader_grads(reader, H, pos, neg, fam)
            if res is None:
                rec["deviation"] = "not differentiable in this harness (autograd through the block-1 marker hook failed)"
            else:
                grads, los = res
                for i in range(H.shape[0]):
                    fd = finite_difference(reader, H[i], grads[i], pos, neg, fam, read_layer, eps_rel)
                    fd["lo_from_grad_forward"] = float(los[i])
                    rec["items"].append(fd)
        if rec["items"]:
            rec["pass"] = all(x["delta_plus"] > 0 and x["ratio_central"] is not None and FD_BAND[0] <= x["ratio_central"] <= FD_BAND[1] for x in rec["items"])
            rec["ratio_central"] = [x["ratio_central"] for x in rec["items"]]
            if rec["pass"] is False and reader.name.startswith("skip"):
                # BRIEF_R §WS4: "skip-lens gradient: the same rule, OR the deviation recorded ... and the skip-lens
                # steered along d_cm". Guiv confirmed 2026-10-20 that an FD-band failure takes that route rather than
                # blocking the gate. The reason states what actually happened — the band, not "not differentiable" —
                # and `grad_directions` withholds this fact's skip-lens direction so the fallback is real and not
                # merely declared. The Oracle has no such clause in the brief, so its failure still blocks.
                rec["deviation"] = (f"{SKIP_FALLBACK}: central FD ratio {rec['ratio_central']} outside "
                                    f"{list(FD_BAND)} at eps_rel={eps_rel}; the gradient is obtainable but unverified, "
                                    f"so the skip-lens is steered along d_cm for this fact")
                record_deviation(reader.name, ds, rec["deviation"])
        else:
            rec["pass"] = None
        out["checks"][f"grad_{reader.name}"] = rec
    out["all_pass"] = all(v.get("pass") is True for k, v in out["checks"].items() if not k.startswith("grad_") or "deviation" not in v)
    return out


def fallback_selection(ds: str, items: dict[str, dict[str, Any]], n_items: int = 32, edit_layer: int = L_EDIT, read_layer: int = L_READ) -> dict[str, Any]:
    """For the pre-checks before ``analyze --r5-select`` has run: the first n test items (balanced) and the class-mean scale
    from the pool states at the edit layer (read layer if block-``edit_layer`` was not captured)."""
    its = [it for it in items.values() if it["dataset"] == ds and it["split"] == "test"]
    pos = [it["item_id"] for it in its if it["label"] == 1][: n_items // 2]
    neg = [it["item_id"] for it in its if it["label"] == 0][: n_items // 2]
    scale, used = None, None
    for L in (edit_layer, read_layer):
        try:
            X, idx = RC.load_states(ds, "chat", L)
        except FileNotFoundError:
            continue
        lab = np.array([items[i]["label"] for i in idx])
        pool = np.array([items[i]["split"] == "pool" for i in idx])
        if pool.sum() == 0:
            pool = np.ones_like(pool)
        scale = float(np.linalg.norm(X[pool & (lab == 1)].mean(0) - X[pool & (lab == 0)].mean(0)))
        used = L
        break
    return {"item_ids": pos + neg, "scale": scale, "scale_layer": used, "fallback": True}


# ------------------------------------------------------------------ main
def bind_readers(target: M.Target, names: list[str], edit_layer: int = L_EDIT, read_layer: int = L_READ) -> list[Any]:
    """Mount order matters: J-lens (no adapter), then the Oracle (PEFT ``default``; its bind unloads any mounted adapter),
    then the skip-lens arms as named adapters on the same PeftModel."""
    readers: list[Any] = []
    if "jlens" in names:
        readers.append(R.JLensReader().bind(target, layers_keep=[edit_layer, read_layer]))
    if "olens" in names:
        readers.append(R.OLensReader().bind(target))
    for arm in ("skip_a", "skip_d"):
        if arm in names:
            readers.append(R.SKIPLENS_READERS[arm]().bind(target))
    return readers


def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["precheck", "A", "B", "audit", "stage"], required=True,
                    help="audit = rule 5: one row and one read-back state per item in every "
                         "(dataset, direction, alpha) condition (files only, no model)")
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--readers", nargs="*", default=["jlens", "olens", "skip_a"])
    ap.add_argument("--alphas", nargs="*", type=float, default=list(ALPHAS))
    ap.add_argument("--k-random", type=int, default=N_RANDOM)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--n-precheck", type=int, default=20)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--run-kind", choices=list(RC.RUN_KINDS), default=None,
                    help="GUARDS.md rule 3: a real run says --run-kind real. The default is \"unknown\", never "
                         "\"real\" by omission; --limit forces \"smoke\". --datasets never implies smoke")
    ap.add_argument("--selection", default=None, help="selection json to read instead of r5_selection.json (R5X)")
    ap.add_argument("--out-dir", default=None,
                    help="output root instead of cache/g_agreement/r/r5; R5X must write its OWN rows (BRIEF_R)")
    ap.add_argument("--dir-dir", default=None, help="directions dir, if not <out-dir>/directions")
    ap.add_argument("--precheck-out", default=None,
                    help="write the precheck record here instead of results/g_agreement/r/r5_prechecks.json "
                         "(a record-only precheck must not touch the run's record)")
    ap.add_argument("--s2-selection", default=None, help="phase stage: WS3's r5x_selection.json (the ten S2 facts)")
    ap.add_argument("--s1-selection", default=None, help="phase stage: r5_selection.json, if not the default")
    ap.add_argument("--s1-dir", default=None, help="phase stage: where S1's npz already are (default r5/directions)")
    ap.add_argument("--out-selection", default=None, help="phase stage: where to write the merged fact selection")
    ap.add_argument("--exclude", nargs="*", default=None, metavar="DS=REASON",
                    help="phase stage: facts to leave out, as dataset=reason; the reason is recorded in the selection")
    a = ap.parse_args(argv)
    if a.run_kind:
        RC.set_run_kind(a.run_kind)
    RC.require_frozen_r(a.allow_unfrozen)
    if a.selection or a.out_dir or a.dir_dir or a.precheck_out:   # before anything reads a path
        resolved = configure_paths(a.out_dir, a.selection, a.dir_dir, a.precheck_out)
        print("[steer] paths: " + " ".join(f"{k}={v}" for k, v in resolved.items()), flush=True)
    if a.phase == "stage":                     # files only: assemble R5X's inputs, verify, then copy
        for flag in ("s2_selection", "dir_dir", "out_selection"):
            if not getattr(a, flag):
                raise SystemExit(f"--phase stage needs --{flag.replace('_', '-')}")
        exc = {}
        for item in (a.exclude or []):
            if "=" not in item:
                raise SystemExit(f"--exclude expects dataset=reason, got {item!r}")
            ds_, why_ = item.split("=", 1)
            exc[ds_] = why_
        rep = stage_r5x(a.s2_selection, a.dir_dir, a.out_selection, a.s1_selection, a.s1_dir, exclude=exc or None)
        if rep["excluded"]:
            print(f"[steer stage] EXCLUDED {len(rep['excluded'])}: {rep['excluded']}", flush=True)
        print(f"[steer stage] {rep['n_facts']} facts staged ({rep['n_s1']} S1 + {rep['n_s2']} S2) -> "
              f"{rep['dir_dir']}; selection {rep['selection']}", flush=True)
        log_line(LOG, f"r5x stage: {rep['n_facts']} facts ({rep['n_s1']}+{rep['n_s2']}) -> {rep['dir_dir']}")
        return 0
    if SELECTION.exists():
        sel_all = load_selection()
        sel = {ds: s for ds, s in sel_all["datasets"].items() if not a.datasets or ds in a.datasets}
    elif a.phase == "precheck" and a.datasets:
        sel = {}
    else:
        raise SystemExit(f"{SELECTION} missing: run analyze --r5-select first")
    if a.phase == "audit":
        # Files only: no model, no GPU, and deliberately BEFORE the bank load — the audit reads the selection, the
        # directions npz and the rows, so it must not require the 67 MB built bank it never looks at.
        # The audit expects exactly what these parameters describe, so say them: auditing a K=10 run with the
        # module default K=5 reports 5 x len(alphas) "unexpected" conditions per dataset and nothing is wrong.
        print(f"[steer audit] auditing against alphas={list(a.alphas)} k_random={a.k_random} "
              f"edit_layer={L_EDIT}; pass the values the RUN used", flush=True)
        fails, summary = audit_conditions(sel, tuple(a.alphas), a.k_random)
        for n_ in summary.get("notes", [])[:8]:
            print(f"[steer audit] {n_}", flush=True)
        if len(summary.get("notes", [])) > 8:
            print(f"[steer audit] ... and {len(summary['notes']) - 8} more such notes", flush=True)
        for line in fails:
            print(line, flush=True)
        print(f"[steer audit] {summary['rows']} rows over {summary['datasets']} datasets, "
              f"{summary['conditions']} conditions, {summary['states']} states; empty "
              f"{summary['empty_conditions']}, short {summary['short_conditions']}, "
              f"missing state files {summary['missing_state_files']}, "
              f"unexpected conditions {summary.get('unexpected_conditions', 0)}", flush=True)
        log_line(LOG, f"steer audit: {len(fails)} failures over {summary['conditions']} conditions")
        return 1 if fails else 0
    dsets = list(sel) or list(a.datasets or [])
    items = {it["item_id"]: it for it in B.load_items(B.ITEMS_R, "all", dsets)}
    if not sel:
        sel = {ds: fallback_selection(ds, items) for ds in dsets}
    R5_DIR.mkdir(parents=True, exist_ok=True)
    log_line(LOG, f"r5 phase {a.phase}: {len(sel)} datasets {sorted(sel)}")
    if a.phase == "precheck":
        target = load_target_timed(MODULE)
        readers = bind_readers(target, a.readers)
        recs = []
        ledger = StepLedger(step="precheck", module=MODULE)
        with timed_call() as st:
            for ds, s in sel.items():
                recs.append(precheck(target, readers, ds, s, items, n_span=a.n_precheck))
                print(f"[r5 precheck] {ds}: " + ", ".join(f"{k}={v.get('pass')}" for k, v in recs[-1]["checks"].items()), flush=True)
                for k, v in recs[-1]["checks"].items():
                    if v.get("deviation"):
                        record_deviation(k.removeprefix("grad_"), ds, v["deviation"])
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        PRECHECK_PATH.parent.mkdir(parents=True, exist_ok=True)
        old = json.loads(PRECHECK_PATH.read_text()) if PRECHECK_PATH.exists() else []
        PRECHECK_PATH.write_text(json.dumps(old + recs, indent=1))
        log_line(LOG, f"r5 precheck: " + "; ".join(f"{r['dataset']} " + " ".join(f"{k}={v.get('pass')}" for k, v in r["checks"].items()) for r in recs))
        M.unload(target)
        return 0 if all(r["all_pass"] for r in recs) else 1
    if a.phase == "A":
        target = load_target_timed(MODULE)
        readers = bind_readers(target, a.readers)
        for ds, s in sel.items():          # 1) reader-gradient directions
            dirs = directions_for(ds)
            require_edit_directions(ds, dirs)
            grad_directions(target, readers, ds, s, items, dirs)
        for ds, s in sel.items():          # 2) steering with read-back
            steer_dataset(target, ds, s, items, directions_for(ds), tuple(a.alphas), batch=a.batch, k_random=a.k_random)
        for rd in readers:                 # 3) readers on the read-back states, and the probe projection
            for ds in sel:
                read_back(rd, ds, items)
        for ds in sel:
            probe_rows(ds, items, directions_for(ds))
        M.unload(target)
    else:
        nla = R.NLAReader().bind()
        import torch

        for ds, s in sel.items():          # the NLA gradient direction (cos matrix only: steering is phase A) then read-back
            dirs = directions_for(ds)
            first = items[s["item_ids"][0]]["primary"]
            fam = RC.register_templates(first)
            pos, neg = RC.reader_candidates(nla.name, first)
            X, idx = RC.load_states(ds, "chat", L_READ)
            pos_of = {iid: i for i, iid in enumerate(idx)}
            H = torch.from_numpy(X[[pos_of[i] for i in s["item_ids"]]])
            g = hook_reader_direction(nla, H, pos, neg, fam)
            if g is None:
                record_deviation(nla.name, ds, "not differentiable in this harness (autograd through the block-1 marker hook failed)")
            else:
                dirs[f"d_nla_L{L_READ}"] = g
                dirs[f"d_nla_L{L_EDIT}"] = g
                save_directions(ds, dirs)
            read_back(nla, ds, items)
        nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
