"""Reader scoring beyond the (A, B) pair of core/scoring_lo.py, used by S3 / V6 / S4:

  score_candidates(reader, H, cand_lists, family)   one native score per (state, candidate) — the full score vector over
                                                     candidates_all (counts 1..99, mapping-8, ownership-4): Oracle lp("- X"),
                                                     NLA mean-template lp, skip-lens mean-form lp, J-lens max-variant cosine
  olens_carrier_multi(tokenizer, layer, n_markers)   the Oracle carrier with n CONSECUTIVE marker characters (n = 1 reproduces
                                                     core.readers.olens_carrier exactly: same ids, same slot)
  lo_olens_span(reader, spans, cand_pairs, layer)    V6: each marker embedding j := 16000 · unit(h_j) in order; paired LO
  olens_read_batch / nla_read_batch                  batched free-text samples (T = 1, top-p 0.95) for the S4 consistency null

Every formula is the one in core/scoring_lo.py / core/readers.py; nothing here changes the single-marker behaviour."""

from __future__ import annotations

from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO

NLA_TEMPLATES_W = {  # graded families (the NLA / skip-lens register for numbers); pair families use LO.templates_for
    "counts": ['The answer must be the number {X}.', 'The single-word answer "{X}".'],
    "arith": ['The answer must be the number {X}.', 'The single-word answer "{X}".'],
}
S4_SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 0, "do_sample": True}


def templates_for(family: str) -> list[str]:
    return list(NLA_TEMPLATES_W.get(family, LO.templates_for(family)))


# ------------------------------------------------------------------ per-candidate score vectors
def _rows_by_batch(n_rows: int, batch: int):
    for s in range(0, n_rows, batch):
        yield s, min(n_rows, s + batch)


def _scores_olens(reader: R.OLensReader, H: Any, cand_lists: list[list[str]], layer: int, batch: int) -> list[list[float | None]]:
    import torch

    t = reader.target
    ids0, slot, _c, _cid = reader.carrier(layer)
    tok = t.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    embed = t.model.get_input_embeddings()
    dev = next(t.model.parameters()).device
    flat = [(i, c) for i, cs in enumerate(cand_lists) for c in cs]
    scores: list[float] = []
    for s, e in _rows_by_batch(len(flat), batch):
        rows = [list(ids0) + LO.encode(tok, LO.OLENS_BULLET.format(X=c)) for _, c in flat[s:e]]
        vecs = [H[i] for i, _ in flat[s:e]]

        def embed_fn(ids_t, vecs=vecs):
            with torch.no_grad():
                em = embed(ids_t).clone()
                for r, v in enumerate(vecs):
                    v = v.to(dev).float()
                    em[r, slot, :] = (reader.alpha * v / v.norm().clamp_min(1e-9)).to(em.dtype)
            return em

        scores += LO._summed_logprobs(t.model, rows, len(ids0), pad, dev, embed_fn=embed_fn)
    return _unflatten(scores, cand_lists)


def _scores_hooked(model: Any, tok: Any, head: list[int], vec_slot: dict[str, Any], H: Any, cand_lists: list[list[str]], templates: list[str], batch: int,
                   dev: Any) -> list[list[float | None]]:
    """NLA / skip-lens: rows = head + template(X); the block-1 hook injects one vector per row; mean over templates."""
    import torch

    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    flat = [(i, c) for i, cs in enumerate(cand_lists) for c in cs]
    per_t = []
    for tmpl in templates:
        sc: list[float] = []
        for s, e in _rows_by_batch(len(flat), batch):
            rows = [head + LO.encode(tok, tmpl.format(X=c)) for _, c in flat[s:e]]
            vec_slot["v"] = torch.stack([H[i].float() for i, _ in flat[s:e]])
            try:
                sc += LO._summed_logprobs(model, rows, len(head), pad, dev)
            finally:
                vec_slot["v"] = None
        per_t.append(sc)
    mean = [sum(pt[j] for pt in per_t) / len(per_t) for j in range(len(flat))]
    return _unflatten(mean, cand_lists)


def _scores_jlens(reader: R.JLensReader, H: Any, cand_lists: list[list[str]], layer: int) -> list[list[float | None]]:
    import torch

    J = reader.J[layer]
    w_u = reader.w_u
    if layer not in reader._denom:
        reader._denom[layer] = (w_u @ J).norm(dim=1).clamp_min(1e-9)
    denom = reader._denom[layer]
    cache: dict[str, dict[str, int]] = {}
    out = []
    for i, cs in enumerate(cand_lists):
        h = H[i].to(w_u.device).float()
        with torch.no_grad():
            z = (h @ J.T) @ w_u.T / denom
        row = []
        for c in cs:
            var = cache.setdefault(c, LO.token_variants(reader.tokenizer, c))
            row.append(max(float(z[t]) for t in var.values()) if var else None)
        out.append(row)
    return out


def _unflatten(flat: list[Any], cand_lists: list[list[str]]) -> list[list[Any]]:
    out, k = [], 0
    for cs in cand_lists:
        out.append(list(flat[k: k + len(cs)]))
        k += len(cs)
    return out


def score_candidates(reader: Any, H: Any, cand_lists: list[list[str]], family: str, *, layer: int | None = None, batch: int = 32) -> list[dict[str, Any]]:
    """``H`` [N, d] fp32; ``cand_lists[i]`` the candidates of state i. One dict per state: {reader, candidates, scores (per candidate,
    None = unscorable), argmax, format, templates}. Both the full list of a state and (for NLA / skip) all templates share the forward
    batch composition rule of core/scoring_lo (rows are chunked by ``batch``)."""
    import torch

    H = torch.as_tensor(H).float()
    if H.ndim == 1:
        H = H[None]
    if H.shape[0] != len(cand_lists):
        raise ValueError(f"{H.shape[0]} states but {len(cand_lists)} candidate lists")
    layer = C.LAYER if layer is None else int(layer)
    if isinstance(reader, R.OLensReader):
        sc, fmt, temps = _scores_olens(reader, H, cand_lists, layer, batch), "bullet", [LO.OLENS_BULLET]
    elif isinstance(reader, R.NLAReader):
        temps = templates_for(family)
        head = list(reader.ids) + LO.encode(reader.tokenizer, LO.NLA_PREFIX)
        sc, fmt = _scores_hooked(reader.model, reader.tokenizer, head, reader._vec, H, cand_lists, temps, batch, next(reader.model.parameters()).device), "explanation"
    elif isinstance(reader, R.SkipLensReader):
        temps = list(C.SKIPLENS_LO_FORMS)
        with reader.active():
            sc = _scores_hooked(reader.model, reader.tokenizer, list(reader.ids), reader._vec, H, cand_lists, temps, batch, next(reader.model.parameters()).device)
        fmt = "continuation"
    elif isinstance(reader, R.JLensReader):
        sc, fmt, temps = _scores_jlens(reader, H, cand_lists, layer), "cosine", ["single_token_variants"]
    else:
        raise TypeError(f"unknown reader {type(reader).__name__}")
    out = []
    for cs, row in zip(cand_lists, sc):
        ok = [j for j, v in enumerate(row) if v is not None]
        out.append({"reader": reader.name, "candidates": list(cs), "scores": row, "argmax": (cs[max(ok, key=lambda j: row[j])] if ok else None),
                    "n_unscorable": len(cs) - len(ok), "format": fmt, "templates": temps, "layer_used": (layer if fmt in ("bullet", "cosine") else None)})
    return out


# ------------------------------------------------------------------ V6: multi-marker Oracle carrier
def olens_carrier_multi(tokenizer: Any, layer: int, n_markers: int = 1, prompt: str = C.OLENS_PROMPT,
                        scan: tuple[int, int] = C.OLENS_MARKER_SCAN) -> tuple[list[int], list[int], str, int]:
    """``core.readers.olens_carrier`` generalised additively: the marker character repeated ``n_markers`` times inside the activation
    tags; the first enclosed ideograph that is one token alone and occurs exactly ``n_markers`` times, CONSECUTIVELY, in the render.
    Returns (ids, slots, char, char_id); for n_markers = 1 the ids and the single slot equal ``olens_carrier``'s."""
    if n_markers < 1:
        raise ValueError("n_markers must be >= 1")
    for code in range(*scan):
        char = chr(code)
        ids = tokenizer(char, add_special_tokens=False)["input_ids"]
        if len(ids) != 1:
            continue
        rendered = M.chat_ids(tokenizer, [{"role": "user", "content": prompt.format(layer=layer, char=char * n_markers)}])
        slots = [i for i, t in enumerate(rendered) if t == ids[0]]
        if len(slots) == n_markers and slots == list(range(slots[0], slots[0] + n_markers)):
            return rendered, slots, char, int(ids[0])
    raise ValueError(f"no enclosed ideograph survives as {n_markers} consecutive single tokens in the carrier prompt")


def lo_olens_span(reader: R.OLensReader, spans: list[Any], cand_pairs: list[tuple[str, str]], layer: int, *, batch: int = 32,
                  carriers: dict[int, tuple[list[int], list[int], str, int]] | None = None) -> list[dict[str, Any]]:
    """Paired Oracle LO where state i is a SPAN ``spans[i]`` (fp32 ``[k_i, d]``): the carrier with k_i consecutive markers, marker j's
    input embedding := alpha · unit(h_j). States are grouped by k (equal head length per forward); both candidates of a state share
    the forward. lo = lp("- A") − lp("- B")."""
    import torch

    t = reader.target
    tok = t.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    embed = t.model.get_input_embeddings()
    dev = next(t.model.parameters()).device
    carriers = {} if carriers is None else carriers
    out: list[dict[str, Any] | None] = [None] * len(spans)
    by_k: dict[int, list[int]] = {}
    for i, sp in enumerate(spans):
        sp = torch.as_tensor(sp).float()
        if sp.ndim == 1:
            sp = sp[None]
        spans[i] = sp
        by_k.setdefault(int(sp.shape[0]), []).append(i)
    per = max(1, batch // 2)
    for k, idxs in sorted(by_k.items()):
        if k not in carriers:
            carriers[k] = olens_carrier_multi(tok, layer, k, reader.prompt)
        ids0, slots, char, cid = carriers[k]
        for s in range(0, len(idxs), per):
            chunk = idxs[s: s + per]
            rows, vecs = [], []
            for i in chunk:
                for c in cand_pairs[i]:
                    rows.append(list(ids0) + LO.encode(tok, LO.OLENS_BULLET.format(X=c)))
                    vecs.append(spans[i])

            def embed_fn(ids_t, vecs=vecs):
                with torch.no_grad():
                    em = embed(ids_t).clone()
                    for r, sp in enumerate(vecs):
                        sp = sp.to(dev).float()
                        em[r, slots, :] = (reader.alpha * sp / sp.norm(dim=1, keepdim=True).clamp_min(1e-9)).to(em.dtype)
                return em

            lps = LO._summed_logprobs(t.model, rows, len(ids0), pad, dev, embed_fn=embed_fn)
            for j, i in enumerate(chunk):
                a, b = cand_pairs[i]
                out[i] = {"reader": "olens", "lo": lps[2 * j] - lps[2 * j + 1], "lp_A": lps[2 * j], "lp_B": lps[2 * j + 1], "n_markers": k, "marker_slots": list(slots),
                          "marker_char": char, "templates": [LO.OLENS_BULLET], "format": "bullet_span", "layer_in_prompt": layer, "unscorable": False, "cand_A": a, "cand_B": b}
    return [r for r in out if r is not None]


# ------------------------------------------------------------------ batched free-text reads (S4)
def _sample_batch(model: Any, tok: Any, *, input_ids: Any = None, inputs_embeds: Any = None, n_prompt: int, max_new_tokens: int, sampling: dict[str, Any], seed: int | None,
                  adapter_enabled: bool | None = None) -> list[dict[str, Any]]:
    import torch

    from projects.g_agreement.core import generate as G

    dev = next(model.parameters()).device
    kw = G._gen_kwargs(sampling, max_new_tokens)
    kw.update(pad_token_id=G.pad_id(tok), num_return_sequences=1)
    eos = G.eos_ids(tok, model)
    if seed is not None:
        torch.manual_seed(int(seed))
    ctx = M.disable_adapter_ctx(model) if adapter_enabled is False else _Null()
    B = int(input_ids.shape[0]) if input_ids is not None else int(inputs_embeds.shape[0])
    mask = torch.ones(B, n_prompt, device=dev, dtype=torch.long)
    with torch.no_grad(), ctx:
        if inputs_embeds is not None:
            out = model.generate(inputs_embeds=inputs_embeds, attention_mask=mask, **kw)
            seqs = out.tolist()
            new_rows = [(s[n_prompt:] if len(s) > max_new_tokens and s[:n_prompt] == input_ids[i].tolist() else s) if input_ids is not None else
                        (s[n_prompt:] if len(s) > max_new_tokens else s) for i, s in enumerate(seqs)]
        else:
            out = model.generate(input_ids, attention_mask=mask, **kw)
            new_rows = [s[n_prompt:] for s in out.tolist()]
    rows = []
    for new in new_rows:
        cut, reason = G._finish(new, max_new_tokens, eos)
        rows.append({"text": tok.decode(cut, skip_special_tokens=True), "n_new_tokens": len(cut), "finish_reason": reason})
    return rows


class _Null:
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


def olens_read_batch(reader: R.OLensReader, H: Any, *, layer: int | None = None, n_samples: int = 1, seed: int | None = None, max_new_tokens: int = C.VERBALIZER_MAX_NEW_TOKENS,
                     sampling: dict[str, Any] | None = None, batch: int = 16) -> list[list[dict[str, Any]]]:
    """``n_samples`` free-text Oracle samples per state (rows replicated in the batch; one torch seed per forward, recorded)."""
    import torch

    layer = C.LAYER if layer is None else int(layer)
    t = reader.target
    ids, slot, char, cid = reader.carrier(layer)
    embed = t.model.get_input_embeddings()
    dev = next(t.model.parameters()).device
    H = torch.as_tensor(H).float()
    if H.ndim == 1:
        H = H[None]
    flat = [(i, s) for i in range(H.shape[0]) for s in range(n_samples)]
    out: list[list[dict[str, Any]]] = [[] for _ in range(H.shape[0])]
    base = torch.tensor([ids], device=dev)
    for b in range(0, len(flat), batch):
        chunk = flat[b: b + batch]
        with torch.no_grad():
            em = embed(base).repeat(len(chunk), 1, 1).clone()
            for r, (i, _) in enumerate(chunk):
                v = H[i].to(dev)
                em[r, slot, :] = (reader.alpha * v / v.norm().clamp_min(1e-9)).to(em.dtype)
        bseed = None if seed is None else int(seed) + b
        rows = _sample_batch(t.model, t.tokenizer, inputs_embeds=em, input_ids=base.repeat(len(chunk), 1), n_prompt=len(ids), max_new_tokens=max_new_tokens,
                             sampling=sampling or S4_SAMPLING, seed=bseed, adapter_enabled=True)
        for (i, s), r in zip(chunk, rows):
            out[i].append({**r, "sample_idx": s, "seed": bseed, "layer_in_prompt": layer, "marker_index": slot, "bullets": R.olens_bullets(r["text"])})
    return out


def nla_read_batch(reader: R.NLAReader, H: Any, *, n_samples: int = 1, seed: int | None = None, max_new_tokens: int = C.VERBALIZER_MAX_NEW_TOKENS,
                   sampling: dict[str, Any] | None = None, batch: int = 16) -> list[list[dict[str, Any]]]:
    """``n_samples`` free-text NLA samples per state; the block-1 hook gets one vector per batch row."""
    import torch

    H = torch.as_tensor(H).float()
    if H.ndim == 1:
        H = H[None]
    dev = next(reader.model.parameters()).device
    flat = [(i, s) for i in range(H.shape[0]) for s in range(n_samples)]
    out: list[list[dict[str, Any]]] = [[] for _ in range(H.shape[0])]
    x0 = torch.tensor([reader.ids], device=dev)
    for b in range(0, len(flat), batch):
        chunk = flat[b: b + batch]
        reader._vec["v"] = torch.stack([H[i] for i, _ in chunk])
        calls0 = reader.n_hook_calls
        bseed = None if seed is None else int(seed) + b
        try:
            rows = _sample_batch(reader.model, reader.tokenizer, input_ids=x0.repeat(len(chunk), 1), n_prompt=len(reader.ids), max_new_tokens=max_new_tokens,
                                 sampling=sampling or S4_SAMPLING, seed=bseed)
        finally:
            reader._vec["v"] = None
        if reader.n_hook_calls == calls0:
            raise RuntimeError("NLA injection hook did not fire during the batched prefill")
        for (i, s), r in zip(chunk, rows):
            out[i].append({**r, "text": R.strip_explanation(r["text"]), "raw_text": r["text"], "sample_idx": s, "seed": bseed, "marker_index": reader.marker})
    return out
