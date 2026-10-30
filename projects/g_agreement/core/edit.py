"""G5 state editing (BRIEF_G5G6): (1) ``generate_with_edited_state`` — the target model's own
greedy decode with the block-42 output at the last prompt position REPLACED by a given vector
during the prefill (decode steps untouched); (2) ``swap_vectors`` — the planted / null vectors of
one pair: planted = h + s·α·Δ·u with u = unit(h_B − h_A), Δ = ‖h_B − h_A‖ (so α = 1 from h_A lands
on h_B's projection); nulls = h + s·α·Δ·r_k with r_k seeded random unit directions."""

from __future__ import annotations

from typing import Any

from . import config as C
from . import generate as G
from . import model as M
from .accounting import timed_call


def generate_with_edited_state(target: M.Target, ids: list[int], vector: Any, layer: int | None = None,
                               pos: int = -1, max_new_tokens: int = 8) -> dict[str, Any]:
    """Greedy continuation of ``ids`` with ``blocks[layer]``'s output at ``pos`` replaced by
    ``vector`` during the prefill only (seq_len > 1). A mounted adapter is disabled."""
    import torch

    layer = C.LAYER if layer is None else layer
    p = pos % len(ids)
    v = torch.as_tensor(vector).float()
    state = {"n_edits": 0}

    def hook(_mod, _inp, out):
        h = out[0] if isinstance(out, tuple) else out
        if h.shape[1] <= 1 or h.shape[1] <= p:  # decode steps (and anything shorter than the render)
            return out
        state["n_edits"] += 1
        h[:, p, :] = v.to(h.device, h.dtype)
        return out

    handle = M.blocks(target.model)[layer].register_forward_hook(hook)
    try:
        res = G.generate_ids(target.model, target.tokenizer, ids, max_new_tokens=max_new_tokens,
                             sampling=None, seed=None, adapter_enabled=False)
    finally:
        handle.remove()
    if state["n_edits"] < 1:
        raise RuntimeError("edit hook did not fire during the prefill")
    return {"answer_text": res.raw_output, "n_new_tokens": res.n_new_tokens, "finish_reason": res.finish_reason,
            "pos": p, "n_tokens": len(ids), "layer": layer, "n_hook_edits": state["n_edits"],
            "edited_norm": float(v.norm()), "wall_s": res.wall_s, "peak_mem_gb": res.peak_mem_gb}


def swap_vectors(hA: Any, hB: Any, alphas: tuple[float, ...] = (0.5, 1.0, 1.5), signs: tuple[int, ...] = (1,),
                 n_null: int = 20, seed: int = 0, null_alphas: tuple[float, ...] = (1.0,),
                 include_natural: bool = True) -> list[dict[str, Any]]:
    """Vectors for BOTH states of a pair. ``sign`` is in the A→B frame: +1 moves toward the other
    state (from A toward B, from B toward A), −1 away. Each entry: {source, condition
    natural|planted|null, alpha, sign, null_k, vector, dose_abs, input_norm, delta, cos_to_u}.
    The K null directions are drawn once per pair (seeded) and applied to both states."""
    import torch

    hA, hB = torch.as_tensor(hA).float(), torch.as_tensor(hB).float()
    diff = hB - hA
    delta = float(diff.norm())
    u = diff / max(delta, 1e-9)
    g = torch.Generator().manual_seed(int(seed))
    nulls = []
    for k in range(n_null):
        r = torch.randn(hA.numel(), generator=g)
        nulls.append(r / r.norm())
    out: list[dict[str, Any]] = []
    for src, h, toward in (("A", hA, 1.0), ("B", hB, -1.0)):
        base = {"source": src, "delta": delta, "u_dot_h": float(u @ h), "input_norm_natural": float(h.norm())}
        if include_natural:
            out.append({**base, "condition": "natural", "alpha": 0.0, "sign": 0, "null_k": None, "vector": h.clone(),
                        "dose_abs": 0.0, "input_norm": float(h.norm()), "cos_to_u": 1.0})
        for a in alphas:
            for s in signs:
                v = h + s * toward * a * delta * u
                out.append({**base, "condition": "planted", "alpha": a, "sign": int(s), "null_k": None, "vector": v,
                            "dose_abs": a * delta, "input_norm": float(v.norm()), "cos_to_u": 1.0,
                            "direction": "toward_other" if s > 0 else "away"})
        for a in null_alphas:
            for s in signs:
                for k, r in enumerate(nulls):
                    v = h + s * toward * a * delta * r
                    out.append({**base, "condition": "null", "alpha": a, "sign": int(s), "null_k": k, "vector": v,
                                "dose_abs": a * delta, "input_norm": float(v.norm()), "cos_to_u": float(r @ u),
                                "null_seed": int(seed)})
    return out


# ================================================================== Phase X2: interpolation edits (BRIEF_X)
# Sites: S1 = L38 last token only, S2 = L38 all positions, S3 = L42 all positions. Edit during the prefill:
# h'(pos) = base(pos) + alpha * delta(pos); the block-42 output at the LAST prefill position is read back by a
# second hook in the same forward and the first-step logits give the model's own answer log-odds.
X2_SITES: dict[str, dict[str, Any]] = {
    "S1": {"layer": 38, "positions": "last"},
    "S2": {"layer": 38, "positions": "all"},
    "S3": {"layer": 42, "positions": "all"},
}
X2_PLANTED_ALPHAS: dict[str, tuple[float, ...]] = {
    "S1": (0.5, 1.0, 1.5, 2.0, 3.0, 4.0),
    "S2": (0.25, 0.5, 0.75, 1.0),
    "S3": (0.25, 0.5, 0.75, 1.0),
}
X2_NULL_ALPHA: dict[str, float] = {"S1": 2.0, "S2": 1.0, "S3": 1.0}
X2_N_ISO_NULL = 6
X2_N_OTHER_NULL = 4
X2_OTHER_NULL_SITES: tuple[str, ...] = ("S1",)
X2_NATURAL_SITE = "nat"
X2_EDIT_LAYERS: tuple[int, ...] = (38, 42)
X2_READ_LAYER = 42


def capture_full(target: M.Target, ids: list[int], layers: list[int] | tuple[int, ...]) -> dict[int, Any]:
    """Block outputs at ALL positions of ``ids`` for the given layers, one forward, adapter off:
    ``{layer: fp32 CPU [T, d]}``."""
    return M.capture(target.model, ids, list(layers), list(range(len(ids))))


def x2_site_positions(site: str, n_tokens: int) -> list[int]:
    kind = X2_SITES[site]["positions"]
    return [n_tokens - 1] if kind == "last" else list(range(n_tokens))


def x2_entry_key(e: dict[str, Any]) -> str:
    """``pair|source|site|condition|alpha|null_k``."""
    return f"{e['pair_id']}|{e['source']}|{e['site']}|{e['condition']}|{float(e['alpha'])}|{e['null_k']}"


def x2_key_safe(key: str) -> str:
    return key.replace("|", "__").replace("/", "_")


def generate_with_interpolated_batch(target: M.Target, ids: list[int], layer: int | None, positions: list[int] | None,
                                     vectors: Any, *, read_layer: int | None = None, max_new_tokens: int = 8,
                                     cand_first_tokens: tuple[int, int] | None = None) -> list[dict[str, Any]]:
    """Greedy continuation of ``ids`` for B rows at once. Row b has ``blocks[layer]``'s output at
    ``positions`` REPLACED by ``vectors[b]`` (fp32 ``[B, P, d]``) during the prefill only; the rows share
    the prompt (equal length, no padding). ``vectors=None`` runs one unedited row (the natural entry).
    Every row also returns ``read_vec`` = block-``read_layer`` output at the last prefill position
    (fp32 ``[d]``, after the edit when the layers coincide: the read hook is registered after the edit
    hook, so it sees the edited tensor) and ``lo_model`` = lp(cand_first_tokens[1]) − lp(cand_first_tokens[0])
    from the first-step logits (positive = toward the second candidate)."""
    import torch

    read_layer = X2_READ_LAYER if read_layer is None else read_layer
    model, tok = target.model, target.tokenizer
    dev = next(model.parameters()).device
    blks = M.blocks(model)
    T = len(ids)
    V = None
    if vectors is not None:
        V = torch.as_tensor(vectors).float()
        if V.ndim == 2:
            V = V[None]
        if layer is None or positions is None:
            raise ValueError("layer and positions are required when vectors are given")
        if V.shape[1] != len(positions):
            raise ValueError(f"vectors has {V.shape[1]} positions, {len(positions)} requested")
        pos = torch.tensor([int(p) % T for p in positions], dtype=torch.long)
        pmax = int(pos.max())
    B = 1 if V is None else int(V.shape[0])
    state: dict[str, Any] = {"n_edits": 0, "n_reads": 0, "read": None}
    handles = []
    if V is not None:
        def edit_hook(_mod, _inp, out):
            h = out[0] if isinstance(out, tuple) else out
            if h.shape[1] <= 1 or h.shape[1] <= pmax:  # decode steps (and anything shorter than the render)
                return out
            state["n_edits"] += 1
            h[:, pos.to(h.device), :] = V.to(h.device, h.dtype)
            return out

        handles.append(blks[layer].register_forward_hook(edit_hook))

    def read_hook(_mod, _inp, out):
        h = out[0] if isinstance(out, tuple) else out
        if h.shape[1] < T:
            return out
        state["n_reads"] += 1
        state["read"] = h[:, T - 1, :].detach().float().cpu().clone()
        return out

    handles.append(blks[read_layer].register_forward_hook(read_hook))
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
    if V is not None and state["n_edits"] < 1:
        raise RuntimeError("edit hook did not fire during the prefill")
    if state["n_reads"] != 1 or state["read"] is None or state["read"].shape[0] != B:
        raise RuntimeError(f"read hook fired {state['n_reads']} times (expected once, batch {B})")
    lp = torch.log_softmax(first.float(), dim=-1).cpu()  # [B, vocab] at the last prefill position
    seqs = out.sequences
    rows: list[dict[str, Any]] = []
    for b in range(B):
        new = seqs[b, T:].tolist()
        cut, reason = G._finish(new, max_new_tokens, eos)
        text = tok.decode(cut, skip_special_tokens=True)
        row: dict[str, Any] = {
            "answer_text": text, "n_new_tokens": len(cut), "finish_reason": reason, "new_ids": cut,
            "read_vec": state["read"][b].clone(), "lo_model": None, "lp_first_A": None, "lp_first_B": None,
            "first_token_id": (cut[0] if cut else None), "top1_id": int(lp[b].argmax()),
            "n_tokens": T, "layer": layer, "read_layer": read_layer, "positions": None if positions is None else [int(p) % T for p in positions],
            "n_hook_edits": state["n_edits"], "n_read_hits": state["n_reads"], "batch_size": B,
            "wall_s": st.wall_s, "wall_s_batch": st.wall_s, "peak_mem_gb": st.peak_mem_gb,
        }
        if cand_first_tokens is not None:
            ia, ib = int(cand_first_tokens[0]), int(cand_first_tokens[1])
            row["lp_first_A"], row["lp_first_B"] = float(lp[b, ia]), float(lp[b, ib])
            row["lo_model"] = row["lp_first_B"] - row["lp_first_A"]
        rows.append(row)
    return rows


def generate_with_interpolated_state(target: M.Target, ids: list[int], layer: int, positions: list[int], base: Any, delta: Any,
                                     alpha: float, read_layer: int | None = None, max_new_tokens: int = 8,
                                     cand_first_tokens: tuple[int, int] | None = None) -> dict[str, Any]:
    """One entry: ``h'[positions] = base + alpha * delta`` (``base``, ``delta`` fp32 ``[P, d]``) at
    ``blocks[layer]`` during the prefill; returns the batch row plus ``alpha``, ``edited_norm_last``."""
    import torch

    base, delta = torch.as_tensor(base).float(), torch.as_tensor(delta).float()
    if base.ndim == 1:
        base, delta = base[None], delta[None]
    v = base + float(alpha) * delta
    row = generate_with_interpolated_batch(target, ids, layer, positions, v[None], read_layer=read_layer,
                                           max_new_tokens=max_new_tokens, cand_first_tokens=cand_first_tokens)[0]
    row.update(alpha=float(alpha), edited_norm_last=float(v[-1].norm()), dose_abs=float(alpha) * float(delta.norm()))
    return row


def first_token_candidates(tokenizer: Any, cand_A: str, cand_B: str) -> dict[str, Any]:
    """The first token of each candidate in the form the model would emit after the assistant
    onset (bare ``X`` first — the render ends in a newline — then ``" X"``, then the capitalised /
    lower spellings). The first form whose first tokens DIFFER between A and B is used; if none
    differs the pair is ``lo_model``-unscorable (the behaviour decode still runs)."""
    forms: list[tuple[str, str, str]] = []
    for name, fa, fb in (("bare", cand_A, cand_B), ("space", " " + cand_A, " " + cand_B),
                         ("cap", cand_A.capitalize(), cand_B.capitalize()), ("space_cap", " " + cand_A.capitalize(), " " + cand_B.capitalize()),
                         ("lower", cand_A.lower(), cand_B.lower()), ("space_lower", " " + cand_A.lower(), " " + cand_B.lower())):
        if (fa, fb) not in [(x[1], x[2]) for x in forms]:
            forms.append((name, fa, fb))
    tried = []
    for name, fa, fb in forms:
        ia = list(tokenizer(fa, add_special_tokens=False)["input_ids"])
        ib = list(tokenizer(fb, add_special_tokens=False)["input_ids"])
        tried.append({"form": name, "A": fa, "B": fb, "first_A": ia[0] if ia else None, "first_B": ib[0] if ib else None})
        if ia and ib and ia[0] != ib[0]:
            return {"unscorable": False, "form": name, "text_A": fa, "text_B": fb, "first_A": int(ia[0]), "first_B": int(ib[0]),
                    "n_tokens_A": len(ia), "n_tokens_B": len(ib), "tried": tried}
    return {"unscorable": True, "form": None, "text_A": None, "text_B": None, "first_A": None, "first_B": None, "tried": tried,
            "reason": "no spelling whose first token differs between the candidates"}


class X2Nulls:
    """The K null directions of one pair (seeded): isotropic per-position unit directions
    ``r_k[pos]`` (one random unit vector per edited position, shared by every site so S1's last-token
    null equals S2's null at the last position) and one random sign per (pair, k) applied to both
    sources in the A→B frame. Other-pair nulls get their own signs."""

    def __init__(self, seed: int, n_iso: int = X2_N_ISO_NULL, n_other: int = X2_N_OTHER_NULL):
        import numpy as np

        self.seed = int(seed)
        rng = np.random.default_rng(self.seed)
        self.sign_iso = [int(s) for s in rng.choice([-1, 1], size=n_iso)]
        self.sign_other = [int(s) for s in rng.choice([-1, 1], size=n_other)]
        self._dirs: dict[tuple[int, int, int], Any] = {}

    def iso_direction(self, k: int, n_tokens: int, d: int) -> Any:
        """fp32 ``[T, d]`` with unit rows; deterministic in (seed, k, T, d)."""
        import torch

        key = (int(k), int(n_tokens), int(d))
        if key not in self._dirs:
            g = torch.Generator().manual_seed(self.seed * 1009 + int(k) + 1)
            r = torch.randn(n_tokens, d, generator=g)
            self._dirs[key] = r / r.norm(dim=1, keepdim=True).clamp_min(1e-9)
        return self._dirs[key]


def x2_condition_table(pair_id: str, family: str, *, other_pair_ids: list[str] | tuple[str, ...] = (),
                       sites: tuple[str, ...] = ("S1", "S2", "S3"), include_natural: bool = True,
                       nulls: X2Nulls | None = None, seed: int = 0) -> list[dict[str, Any]]:
    """The tensor-free condition table of one pair (both sources). Entries carry ``key`` =
    ``pair|source|site|condition|alpha|null_k`` and, for nulls, the seeded ``sign`` (and the
    ``other_pair_id`` whose last-token swap direction an other-pair null uses). Per pair with the
    default ladders: 2 × (6 + 4 + 4) planted + 2 × 3 × 6 isotropic nulls + 2 × 4 other-pair nulls
    + 2 natural = 74 entries."""
    nulls = nulls or X2Nulls(seed)
    out: list[dict[str, Any]] = []

    def add(**e: Any) -> None:
        e.setdefault("null_k", None)
        e.setdefault("sign", 0)
        e.setdefault("other_pair_id", None)
        site = e["site"]
        e["edit_layer"] = None if site == X2_NATURAL_SITE else X2_SITES[site]["layer"]
        e["positions_kind"] = "none" if site == X2_NATURAL_SITE else X2_SITES[site]["positions"]
        e["key"] = x2_entry_key(e)
        out.append(e)

    for src in ("A", "B"):
        base = {"pair_id": pair_id, "family": family, "source": src}
        if include_natural:
            add(**base, site=X2_NATURAL_SITE, condition="natural", alpha=0.0)
        for site in sites:
            for a in X2_PLANTED_ALPHAS[site]:
                add(**base, site=site, condition="planted", alpha=float(a))
            a0 = X2_NULL_ALPHA[site]
            for k in range(len(nulls.sign_iso)):
                add(**base, site=site, condition="null", alpha=float(a0), null_k=k, sign=nulls.sign_iso[k])
            if site in X2_OTHER_NULL_SITES:
                for k, op in enumerate(list(other_pair_ids)[: len(nulls.sign_other)]):
                    add(**base, site=site, condition="null_other", alpha=float(a0), null_k=k, sign=nulls.sign_other[k], other_pair_id=op)
    return out


def x2_entry_vectors(e: dict[str, Any], HA: dict[int, Any], HB: dict[int, Any], nulls: X2Nulls,
                     other_dirs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build ``base`` and ``delta`` (fp32 ``[P, d]``; edited state = base + alpha * delta) for one
    table entry from the full-sequence captures ``HA/HB = {layer: [T, d]}``. In the A→B frame:
    planted delta = ±(h_B − h_A)[pos]; isotropic null delta = ±sign · ‖h_B(pos) − h_A(pos)‖ · r_k[pos];
    other-pair null (S1) delta = ±sign · ‖Δ(last)‖ · u_other with ``u_other`` the other pair's unit
    last-token swap direction at the same layer. Natural entries return ``base = delta = None``."""
    import torch

    site = e["site"]
    T = int(next(iter(HA.values())).shape[0])
    if site == X2_NATURAL_SITE:
        return {"positions": None, "base": None, "delta": None, "dose_abs": 0.0, "delta_last": None, "delta_total": None,
                "input_norm_last": float((HA if e["source"] == "A" else HB)[X2_READ_LAYER][T - 1].norm()), "cos_to_u_last": None}
    layer = X2_SITES[site]["layer"]
    hA, hB = HA[layer].float(), HB[layer].float()
    if hA.shape != hB.shape:
        raise ValueError(f"{e['pair_id']}: A and B captures differ in shape {tuple(hA.shape)} vs {tuple(hB.shape)}")
    d = hA.shape[1]
    pos = x2_site_positions(site, T)
    toward = 1.0 if e["source"] == "A" else -1.0
    h = hA if e["source"] == "A" else hB
    Dfull = hB - hA
    norms = Dfull.norm(dim=1)  # [T]
    u_last = Dfull[T - 1] / norms[T - 1].clamp_min(1e-9)
    base = h[pos].clone()
    cond = e["condition"]
    if cond == "planted":
        delta = toward * Dfull[pos]
        cos = 1.0
    elif cond == "null":
        r = nulls.iso_direction(int(e["null_k"]), T, d)[pos]
        delta = toward * float(e["sign"]) * norms[pos][:, None] * r
        cos = float(r[-1] @ u_last)
    elif cond == "null_other":
        if not other_dirs or e["other_pair_id"] not in other_dirs:
            raise KeyError(f"other-pair direction missing for {e['other_pair_id']}")
        u = torch.as_tensor(other_dirs[e["other_pair_id"]]).float()
        u = u / u.norm().clamp_min(1e-9)
        delta = toward * float(e["sign"]) * norms[pos][:, None] * u[None, :].expand(len(pos), d)
        cos = float(u @ u_last)
    else:
        raise ValueError(f"unknown condition {cond}")
    alpha = float(e["alpha"])
    v = base + alpha * delta
    return {"positions": pos, "base": base, "delta": delta, "dose_abs": alpha * float(delta.norm()),
            "delta_last": float(norms[T - 1]), "delta_total": float(norms.norm()), "delta_edited": float(norms[pos].norm()),
            "input_norm_last": float(v[-1].norm()), "input_norm_natural_last": float(h[T - 1].norm()), "cos_to_u_last": cos}


def x2_other_direction(HA: dict[int, Any], HB: dict[int, Any], layer: int = 38) -> Any:
    """Unit last-token swap direction of a pair at ``layer`` (what other-pair nulls borrow)."""
    T = int(HA[layer].shape[0])
    d = HB[layer][T - 1].float() - HA[layer][T - 1].float()
    return d / d.norm().clamp_min(1e-9)


# ================================================================== Phase Y2: identity-free nulls + J-space split at S2 (BRIEF_Y §Y2)
# Site = X2's S2 (block-38 output, prefill, all positions unless a condition restricts them). Conditions, each in the
# A→B frame (toward = +1 from A, −1 from B) at α ∈ Y2_ALPHAS and both sources:
#   full          Δ(pos) = h_B − h_A at all positions           → REUSED from X2 (key pair|source|S2|planted|alpha|None)
#   name_only     Δ only at positions whose token ids differ between the A and B renders
#   name_removed  Δ only at positions whose token ids are equal (question + chat suffix)
#   other_pair    position-wise Δ of another equal-length same-family pair, rescaled per position to this pair's ‖Δ(pos)‖
#   J_only/J_perp Δ projected onto / out of the top-r* J-space at L38 (right singular vectors of W_U·J_38)
#   rand_only/rand_perp  the same split against K random equal-rank subspaces (seeded, shared by every pair)
Y2_SITE = "Y2"
Y2_EDIT_LAYER = 38
Y2_ALPHAS: tuple[float, ...] = (0.5, 0.75, 1.0)
Y2_R_STAR = 384
Y2_N_OTHER = 4
Y2_N_RAND = 3
Y2_REUSED_SITE = "S2"
Y2_CONDITIONS: tuple[str, ...] = ("full", "name_only", "name_removed", "other_pair", "J_only", "J_perp", "rand_only", "rand_perp")
Y2_POSITIONS_KIND = {"full": "all", "name_only": "differing", "name_removed": "equal", "other_pair": "all",
                     "J_only": "all", "J_perp": "all", "rand_only": "all", "rand_perp": "all"}


def differing_positions(ids_A: list[int], ids_B: list[int]) -> list[int]:
    """Positions where the two (equal-length) renders carry different token ids."""
    if len(ids_A) != len(ids_B):
        raise ValueError(f"renders differ in length: {len(ids_A)} vs {len(ids_B)}")
    return [i for i, (a, b) in enumerate(zip(ids_A, ids_B)) if int(a) != int(b)]


def position_masks(ids_A: list[int], ids_B: list[int]) -> dict[str, list[int]]:
    """``name_only`` = differing positions (the candidate tokens), ``name_removed`` = the rest; the two
    partition range(T), so the two restricted edits sum to the full Δ."""
    diff = differing_positions(ids_A, ids_B)
    s = set(diff)
    return {"name_only": diff, "name_removed": [i for i in range(len(ids_A)) if i not in s]}


def other_pair_delta(delta_pair: Any, delta_other: Any) -> Any:
    """Another pair's position-wise Δ′ (fp32 ``[T, d]``, same T) rescaled per position so that
    ‖Δ′′(pos)‖ = ‖Δ(pos)‖ of THIS pair (direction from the other pair, dose profile from this one).
    Positions where the other pair's Δ′ vanishes stay zero."""
    import torch

    D, O = torch.as_tensor(delta_pair).float(), torch.as_tensor(delta_other).float()
    if D.shape != O.shape:
        raise ValueError(f"other-pair delta shape {tuple(O.shape)} != {tuple(D.shape)} (equal-length pairs only)")
    scale = D.norm(dim=1) / O.norm(dim=1).clamp_min(1e-9)
    scale = torch.where(O.norm(dim=1) > 1e-9, scale, torch.zeros_like(scale))
    return O * scale[:, None]


def jspace_gram(J: Any, w_u: Any, chunk: int = 32768) -> Any:
    """``Jᵀ W_Uᵀ W_U J`` (fp32 ``[d, d]`` on J's device), accumulated over vocab chunks; the Gram of the
    lens map M = W_U·J whose right singular vectors span the J-space (Suraj's s8_rstar recipe)."""
    import torch

    J = torch.as_tensor(J).float()
    G = torch.zeros(J.shape[1], J.shape[1], device=J.device, dtype=torch.float32)
    with torch.no_grad():
        for s in range(0, w_u.shape[0], chunk):
            a = w_u[s: s + chunk].to(J.device).float() @ J
            G += a.T @ a
    return G


def jspace_basis(J38: Any, w_u: Any, r_star: int = Y2_R_STAR, *, cache_path: Any = None, layer: int = Y2_EDIT_LAYER,
                 chunk: int = 32768, gain: Any = None) -> Any:
    """Orthonormal ``[d, r*]`` (fp32, CPU): the top-r* right singular vectors of W_U·J (eigh of the d×d Gram
    in fp64; eigenvectors sorted by decreasing eigenvalue). ``gain`` (optional, ``[d]``) multiplies J row-wise
    for the final-RMSNorm variant of the recipe; the default (None) matches the J-lens readout used by
    ``JLensReader`` (no gain). Cached at ``cache_path`` with the eigenvalues and metadata; a cache whose
    (d, r*, layer) match is reused without recomputation."""
    import torch

    if cache_path is not None:
        from pathlib import Path

        p = Path(cache_path)
        if p.exists():
            obj = torch.load(p, map_location="cpu")
            Q = obj["Q"].float()
            if int(obj.get("layer", layer)) == int(layer) and Q.shape[1] >= r_star:
                return Q[:, :r_star].contiguous()
    J = torch.as_tensor(J38).float()
    if gain is not None:
        J = torch.as_tensor(gain).float().to(J.device)[:, None] * J
    d = int(J.shape[1])
    if not 0 < r_star <= d:
        raise ValueError(f"r_star {r_star} outside (0, {d}]")
    G = jspace_gram(J, w_u, chunk)
    with torch.no_grad():
        evals, evecs = torch.linalg.eigh(G.double())
    evals, evecs = evals.flip(0).float().cpu(), evecs.flip(1).float().cpu()
    Q = evecs[:, :r_star].contiguous()
    if cache_path is not None:
        from pathlib import Path

        p = Path(cache_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"Q": Q, "evals": evals[:r_star].clone(), "evals_all": evals.clone(), "layer": int(layer), "r_star": int(r_star), "d": d,
                    "vocab": int(w_u.shape[0]), "gain": gain is not None, "source": "top right singular vectors of W_U J (eigh of J^T W_U^T W_U J, fp64)",
                    "energy_fraction_top_r": float(evals[:r_star].sum() / evals.sum().clamp_min(1e-30))}, p)
    return Q


def random_subspace(d: int, r: int, seed: int = 0) -> Any:
    """Haar-random orthonormal ``[d, r]`` (fp32, CPU): QR of a seeded Gaussian in fp64 with the sign fix
    (the equal-rank random-subspace control of Suraj's jspace.py)."""
    import torch

    g = torch.Generator().manual_seed(int(seed))
    A = torch.randn(d, r, generator=g, dtype=torch.float64)
    Q, Rm = torch.linalg.qr(A)
    Q = Q * torch.sign(torch.diagonal(Rm))[None, :]
    return Q.float()


def split_delta(delta: Any, basis: Any) -> tuple[Any, Any]:
    """``(Δ_J, Δ_⊥)`` per position for ``delta`` ``[P, d]`` (or ``[d]``) and an orthonormal ``basis`` ``[d, r]``:
    Δ_J = Δ Q Qᵀ, Δ_⊥ = Δ − Δ_J."""
    import torch

    D = torch.as_tensor(delta).float()
    Q = torch.as_tensor(basis).float().to(D.device)
    DJ = (D @ Q) @ Q.T
    return DJ, D - DJ


def j_energy_fraction(delta: Any, basis: Any) -> float:
    """‖Δ_J‖_F / ‖Δ‖_F over all positions of ``delta`` (a random direction scores ≈ sqrt(r/d))."""
    import torch

    D = torch.as_tensor(delta).float()
    DJ, _ = split_delta(D, basis)
    return float(DJ.norm() / D.norm().clamp_min(1e-9))


def y2_entry_key(e: dict[str, Any]) -> str:
    """``pair|source|Y2|condition|alpha|k``."""
    return f"{e['pair_id']}|{e['source']}|{Y2_SITE}|{e['condition']}|{float(e['alpha'])}|{e['k']}"


def y2_condition_table(pair_id: str, family: str, *, other_pair_ids: list[str] | tuple[str, ...] = (),
                       alphas: tuple[float, ...] = Y2_ALPHAS, conditions: tuple[str, ...] = Y2_CONDITIONS,
                       n_rand: int = Y2_N_RAND, r_star: int = Y2_R_STAR, n_other: int = Y2_N_OTHER) -> list[dict[str, Any]]:
    """The tensor-free Y2 condition table of one pair (both sources, every α). Entries carry ``key`` =
    ``pair|source|Y2|condition|alpha|k``; ``full`` entries are marked ``reused=True`` with ``reused_key`` the X2 S2
    planted key (no new decode). Per (pair, source, α) with the defaults and 4 usable other pairs:
    1 full (reused) + 1 name_only + 1 name_removed + 4 other_pair + 2 J + 2 × 3 rand = 15 entries, 14 new; per
    pair = 90 entries, 84 new decodes. Fewer equal-length same-family pairs reduce ``other_pair`` to what exists."""
    out: list[dict[str, Any]] = []
    others = list(other_pair_ids)[:n_other]

    def add(**e: Any) -> None:
        e.setdefault("k", None)
        e.setdefault("other_pair_id", None)
        e.setdefault("r_star", None)
        e.setdefault("reused", False)
        e.setdefault("reused_key", None)
        e["site"] = Y2_SITE
        e["edit_layer"] = Y2_EDIT_LAYER
        e["sign"] = 1
        e["positions_kind"] = Y2_POSITIONS_KIND[e["condition"]]
        e["key"] = y2_entry_key(e)
        out.append(e)

    for src in ("A", "B"):
        base = {"pair_id": pair_id, "family": family, "source": src}
        for a in alphas:
            a = float(a)
            if "full" in conditions:
                add(**base, condition="full", alpha=a, reused=True,
                    reused_key=f"{pair_id}|{src}|{Y2_REUSED_SITE}|planted|{a}|None")
            for cond in ("name_only", "name_removed"):
                if cond in conditions:
                    add(**base, condition=cond, alpha=a)
            if "other_pair" in conditions:
                for k, op in enumerate(others):
                    add(**base, condition="other_pair", alpha=a, k=k, other_pair_id=op)
            for cond in ("J_only", "J_perp"):
                if cond in conditions:
                    add(**base, condition=cond, alpha=a, r_star=int(r_star))
            for cond in ("rand_only", "rand_perp"):
                if cond in conditions:
                    for k in range(n_rand):
                        add(**base, condition=cond, alpha=a, k=k, r_star=int(r_star))
    return out


def y2_entry_vectors(e: dict[str, Any], HA: dict[int, Any], HB: dict[int, Any], ids_A: list[int], ids_B: list[int], *,
                     basis: Any = None, rand_bases: list[Any] | tuple[Any, ...] | None = None,
                     other_deltas: dict[str, Any] | None = None, layer: int | None = None) -> dict[str, Any]:
    """``positions`` and ``base``/``delta`` (fp32 ``[P, d]``; edited state = base + alpha * delta) of one Y2 entry
    from the full captures ``HA/HB = {layer: [T, d]}`` and the two renders. ``other_deltas[pair_id]`` is the other
    pair's raw ``h_B − h_A`` at the edit layer (``[T, d]``). Also returns ``frac_norm_in_J`` (‖Δ_J‖/‖Δ‖ of the APPLIED
    delta over its positions, against ``basis``) and ``frac_norm_in_J_full`` (the same for the pair's whole Δ)."""
    import torch

    layer = Y2_EDIT_LAYER if layer is None else layer
    hA, hB = HA[layer].float(), HB[layer].float()
    if hA.shape != hB.shape:
        raise ValueError(f"{e['pair_id']}: A and B captures differ in shape {tuple(hA.shape)} vs {tuple(hB.shape)}")
    T = int(hA.shape[0])
    if len(ids_A) != T or len(ids_B) != T:
        raise ValueError(f"{e['pair_id']}: renders ({len(ids_A)}, {len(ids_B)}) do not match the capture length {T}")
    toward = 1.0 if e["source"] == "A" else -1.0
    h = hA if e["source"] == "A" else hB
    Dfull = hB - hA
    cond = e["condition"]
    masks = position_masks(ids_A, ids_B)
    if cond in ("name_only", "name_removed"):
        pos = masks[cond]
        if not pos:
            raise ValueError(f"{e['pair_id']}: no {cond} positions")
        delta = toward * Dfull[pos]
    else:
        pos = list(range(T))
        if cond == "full":
            delta = toward * Dfull
        elif cond == "other_pair":
            if not other_deltas or e["other_pair_id"] not in other_deltas:
                raise KeyError(f"other-pair delta missing for {e['other_pair_id']}")
            delta = toward * other_pair_delta(Dfull, other_deltas[e["other_pair_id"]])
        elif cond in ("J_only", "J_perp"):
            if basis is None:
                raise ValueError("J-space basis required")
            DJ, Dp = split_delta(Dfull, basis)
            delta = toward * (DJ if cond == "J_only" else Dp)
        elif cond in ("rand_only", "rand_perp"):
            if not rand_bases:
                raise ValueError("random subspace bases required")
            DJ, Dp = split_delta(Dfull, rand_bases[int(e["k"])])
            delta = toward * (DJ if cond == "rand_only" else Dp)
        else:
            raise ValueError(f"unknown condition {cond}")
    alpha = float(e["alpha"])
    base = h[pos].clone()
    v = base + alpha * delta
    norms = Dfull.norm(dim=1)
    fj = None if basis is None else j_energy_fraction(delta, basis)
    fj_full = None if basis is None else j_energy_fraction(Dfull, basis)
    return {"positions": pos, "n_positions": len(pos), "base": base, "delta": delta, "dose_abs": alpha * float(delta.norm()),
            "delta_last": float(norms[T - 1]), "delta_total": float(norms.norm()), "delta_edited": float(delta.norm()),
            "delta_natural_edited": float(norms[pos].norm()), "input_norm_last": float(v[-1].norm()) if pos[-1] == T - 1 else float(h[T - 1].norm()),
            "input_norm_natural_last": float(h[T - 1].norm()), "frac_norm_in_J": fj, "frac_norm_in_J_full": fj_full,
            "n_differing": len(masks["name_only"]), "last_edited": pos[-1] == T - 1}
