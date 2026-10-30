"""Teacher-forced paired log-odds (LO) in each reader's native format (G5, BRIEF_G5G6).

Mirrors Suraj's ``src/mats/readers/{olens,nla,jlens}.py`` (``logprob_of_strings``,
``logprob_of_strings_batch``, ``paired_logodds``) in third_party/mats-nla-workspace-main:

  olens  LO = log p("- {A}") − log p("- {B}") after the carrier prompt whose marker row is the
         injected 16000·unit(h) (bullet register); summed token log-probs, teacher-forced.
  nla    input_ids = actor prompt ids + "<explanation>\\n" + template(X); the block-1 hook adds the
         norm-matched vector per batch row; LO = mean over the family's templates.
  jlens  max cosine score over the single-token variants of A minus the same for B; a candidate
         with no single-token variant is ``unscorable`` (lo None), never zero. (rlens: same readout.)
  skip_a / skip_d (Phase Y3)  input_ids = actor prompt ids + tokens(X) — the futurelens continuation, no
         template, no prefix; LO = mean over the bare and leading-space forms of lp(A) − lp(B); the arm's
         LoRA is the active adapter and the block-1 hook injects one vector per batch row.

Both candidates of ONE state are always in the same forward batch (bf16 batch composition shifts
scores by up to 0.26 nats; Suraj's rule). Right padding with an attention mask; ``logits_to_keep``
so only the candidate positions' logits are materialised (fallback: full logits).

API::

    score_lo(reader, H[N, d], cand_pairs=[(A, B)] * N, family) -> [{lo, lp_A, lp_B, templates, unscorable, ...}]
"""

from __future__ import annotations

from typing import Any

from . import config as C
from . import readers as R

NLA_PREFIX = "<explanation>\n"
OLENS_BULLET = "- {X}"
NLA_TEMPLATES = {
    "ownership": ['The answer must be the name "{X}".', 'The single-word answer "{X}".'],
    "mapping": ['The answer must be the symbol "{X}".', 'The single-word answer "{X}".'],
    "choice": ['The answer must be the word "{X}".', 'The single-word answer "{X}".'],
    # Phase X (BRIEF_X E1/E8): language, tense and the X3 puzzles (same register as mapping)
    "language": ["The reply must be written in {X}.", "The requested language is {X}."],
    "tense": ["The sentence must be in the {X} tense.", "The requested tense is {X}."],
    "puzzle": ['The answer must be the symbol "{X}".', 'The single-word answer "{X}".'],
}
DEFAULT_TEMPLATES = ['The single-word answer "{X}".']


def templates_for(family: str) -> list[str]:
    return list(NLA_TEMPLATES.get(family, DEFAULT_TEMPLATES))


def encode(tokenizer: Any, text: str) -> list[int]:
    return list(tokenizer(text, add_special_tokens=False)["input_ids"])


# ------------------------------------------------------------------ shared teacher forcing
def _forward_logits(model: Any, ids: Any, mask: Any, keep: int, inputs_embeds: Any = None) -> Any:
    kw: dict[str, Any] = {"attention_mask": mask, "use_cache": False}
    if inputs_embeds is not None:
        kw["inputs_embeds"] = inputs_embeds
    else:
        kw["input_ids"] = ids
    try:
        logits = model(logits_to_keep=keep, **kw).logits
    except TypeError:
        logits = model(**kw).logits[:, -keep:]
    if logits.shape[1] != keep:  # a model that ignores logits_to_keep
        logits = logits[:, -keep:]
    return logits


def _summed_logprobs(model: Any, rows: list[list[int]], head_len: int, pad: int, device: Any,
                     embed_fn: Any = None) -> list[float]:
    """rows: full token sequences (head + candidate tokens), one forward for all of them.
    Returns sum log p(candidate tokens | head) per row. ``embed_fn(ids)`` builds inputs_embeds
    (OLens: the marker row replaced per row)."""
    import torch

    n = max(len(r) for r in rows)
    ids = torch.full((len(rows), n), pad, dtype=torch.long)
    mask = torch.zeros_like(ids)
    for i, r in enumerate(rows):
        ids[i, : len(r)] = torch.tensor(r)
        mask[i, : len(r)] = 1
    ids, mask = ids.to(device), mask.to(device)
    keep = n - head_len + 1  # logits from the last head token on: position u predicts ids[u+1]
    with torch.no_grad():
        logits = _forward_logits(model, ids, mask, keep, inputs_embeds=(embed_fn(ids) if embed_fn else None))
        lp = torch.log_softmax(logits[:, :-1].float(), dim=-1)
        tok_lp = lp.gather(-1, ids[:, head_len:].unsqueeze(-1)).squeeze(-1)
    out = []
    for i, r in enumerate(rows):
        k = len(r) - head_len
        out.append(float(tok_lp[i, :k].sum()))
    return out


# ------------------------------------------------------------------ OLens
def lo_olens(reader: R.OLensReader, H: Any, cand_pairs: list[tuple[str, str]], layer: int | None = None,
             batch: int = 32) -> list[dict[str, Any]]:
    import torch

    layer = C.LAYER if layer is None else layer
    t = reader.target
    assert t is not None
    ids0, slot, char, cid = reader.carrier(layer)
    tok = t.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    embed = t.model.get_input_embeddings()
    dev = next(t.model.parameters()).device
    per = max(1, batch // 2)  # states per forward; both candidates of a state share the forward
    out: list[dict[str, Any]] = []
    for s in range(0, H.shape[0], per):
        hs = H[s: s + per]
        pairs = cand_pairs[s: s + per]
        rows, vecs, meta = [], [], []
        for i, (a, b) in enumerate(pairs):
            for c in (a, b):
                text = OLENS_BULLET.format(X=c)
                rows.append(list(ids0) + encode(tok, text))
                vecs.append(hs[i])
                meta.append(text)

        def embed_fn(ids_t, vecs=vecs):
            with torch.no_grad():
                e = embed(ids_t).clone()
                for r, v in enumerate(vecs):
                    v = v.to(dev).float()
                    e[r, slot, :] = (reader.alpha * v / v.norm().clamp_min(1e-9)).to(e.dtype)
            return e

        lps = _summed_logprobs(t.model, rows, len(ids0), pad, dev, embed_fn=embed_fn)
        for i, (a, b) in enumerate(pairs):
            lp_a, lp_b = lps[2 * i], lps[2 * i + 1]
            out.append({"reader": "olens", "lo": lp_a - lp_b, "lp_A": lp_a, "lp_B": lp_b,
                        "templates": [OLENS_BULLET], "format": "bullet", "prefix": "",
                        "n_tokens_A": len(rows[2 * i]) - len(ids0), "n_tokens_B": len(rows[2 * i + 1]) - len(ids0),
                        "layer_in_prompt": layer, "marker_index": slot, "unscorable": False})
    return out


# ------------------------------------------------------------------ NLA
def lo_nla(reader: R.NLAReader, H: Any, cand_pairs: list[tuple[str, str]], family: str,
           batch: int = 32, prefix: str = NLA_PREFIX) -> list[dict[str, Any]]:
    import torch

    assert reader.model is not None
    tok = reader.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(reader.model.parameters()).device
    head = list(reader.ids) + encode(tok, prefix)
    temps = templates_for(family)
    per = max(1, batch // 2)
    out: list[dict[str, Any]] = []
    for s in range(0, H.shape[0], per):
        hs = H[s: s + per]
        pairs = cand_pairs[s: s + per]
        per_t = []
        for tmpl in temps:
            rows, vecs = [], []
            for i, (a, b) in enumerate(pairs):
                for c in (a, b):
                    rows.append(head + encode(tok, tmpl.format(X=c)))
                    vecs.append(hs[i].float())
            reader._vec["v"] = torch.stack(vecs)
            try:
                lps = _summed_logprobs(reader.model, rows, len(head), pad, dev)
            finally:
                reader._vec["v"] = None
            per_t.append([(lps[2 * i], lps[2 * i + 1], len(rows[2 * i]) - len(head), len(rows[2 * i + 1]) - len(head))
                          for i in range(len(pairs))])
        for i, (a, b) in enumerate(pairs):
            pt = [{"template": tmpl, "lp_A": per_t[j][i][0], "lp_B": per_t[j][i][1], "lo": per_t[j][i][0] - per_t[j][i][1],
                   "n_tokens_A": per_t[j][i][2], "n_tokens_B": per_t[j][i][3]} for j, tmpl in enumerate(temps)]
            out.append({"reader": "nla", "lo": sum(x["lo"] for x in pt) / len(pt),
                        "lp_A": sum(x["lp_A"] for x in pt) / len(pt), "lp_B": sum(x["lp_B"] for x in pt) / len(pt),
                        "templates": temps, "per_template": pt, "prefix": prefix, "format": "explanation",
                        "marker_index": reader.marker, "unscorable": False})
    return out


# ------------------------------------------------------------------ J-lens
def token_variants(tokenizer: Any, word: str) -> dict[str, int]:
    """Single-token spellings of a candidate: X, " X", capitalised, lower (each bare and with a
    leading space). Returns {variant_text: token_id} for the variants that are exactly one token."""
    forms = []
    for w in (word, word.capitalize(), word.lower(), word.upper() if len(word) == 1 else word):
        for f in (w, " " + w):
            if f not in forms:
                forms.append(f)
    out: dict[str, int] = {}
    for f in forms:
        ids = encode(tokenizer, f)
        if len(ids) == 1 and ids[0] not in out.values():
            out[f] = int(ids[0])
    return out


def lo_jlens(reader: R.JLensReader, H: Any, cand_pairs: list[tuple[str, str]], layer: int | None = None) -> list[dict[str, Any]]:
    import torch

    layer = C.LAYER if layer is None else layer
    J = reader.J[layer]
    w_u = reader.w_u
    if layer not in reader._denom:
        reader._denom[layer] = (w_u @ J).norm(dim=1).clamp_min(1e-9)
    denom = reader._denom[layer]
    out: list[dict[str, Any]] = []
    cache: dict[str, dict[str, int]] = {}
    for i, (a, b) in enumerate(cand_pairs):
        va = cache.setdefault(a, token_variants(reader.tokenizer, a))
        vb = cache.setdefault(b, token_variants(reader.tokenizer, b))
        row: dict[str, Any] = {"reader": reader.name, "variants_A": va, "variants_B": vb, "templates": ["single_token_variants"],
                               "format": "cosine", "unscorable": not (va and vb), "lo": None, "lp_A": None, "lp_B": None}
        if va and vb:
            h = H[i].to(w_u.device).float()
            with torch.no_grad():
                z = (h @ J.T) @ w_u.T / denom  # cosine readout over the vocabulary
            sa = max(float(z[t]) for t in va.values())
            sb = max(float(z[t]) for t in vb.values())
            row.update(lo=sa - sb, lp_A=sa, lp_B=sb,
                       best_A=max(va, key=lambda k: float(z[va[k]])), best_B=max(vb, key=lambda k: float(z[vb[k]])))
        else:
            row["reason"] = f"no single-token variant for {'A' if not va else 'B'}"
        out.append(row)
    return out


# ------------------------------------------------------------------ Skip-lens (Phase Y3)
def lo_skiplens(reader: R.SkipLensReader, H: Any, cand_pairs: list[tuple[str, str]], batch: int = 32,
                forms: tuple[str, ...] = C.SKIPLENS_LO_FORMS) -> list[dict[str, Any]]:
    """Native skip-lens LO (BRIEF_Y §Y3): the arm is a *futurelens* that continues the text right after the
    generation prompt, so the candidate is scored as that continuation with NO template and NO prefix:
    input_ids = actor prompt ids + tokens(form(X)); lp = summed teacher-forced log-prob of the candidate
    tokens; LO = mean over the bare and leading-space forms of lp(A) − lp(B). The block-1 hook injects one
    vector per batch row; both candidates (and both forms) of a state share the activation. The arm's LoRA
    is the active adapter for the forward (restored afterwards)."""
    import torch

    assert reader.target is not None
    tok = reader.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    model = reader.target.model
    dev = next(model.parameters()).device
    head = list(reader.ids)
    per = max(1, batch // 2)
    out: list[dict[str, Any]] = []
    with reader.active():
        for s in range(0, H.shape[0], per):
            hs = H[s: s + per]
            pairs = cand_pairs[s: s + per]
            per_f = []
            for form in forms:
                rows, vecs = [], []
                for i, (a, b) in enumerate(pairs):
                    for c in (a, b):
                        rows.append(head + encode(tok, form.format(X=c)))
                        vecs.append(hs[i].float())
                reader._vec["v"] = torch.stack(vecs)
                calls0 = reader.n_hook_calls
                try:
                    lps = _summed_logprobs(model, rows, len(head), pad, dev)
                finally:
                    reader._vec["v"] = None
                if reader.n_hook_calls == calls0:
                    raise RuntimeError(f"skip-lens {reader.arm} hook did not fire during teacher forcing")
                per_f.append([(lps[2 * i], lps[2 * i + 1], len(rows[2 * i]) - len(head), len(rows[2 * i + 1]) - len(head))
                              for i in range(len(pairs))])
            for i, (a, b) in enumerate(pairs):
                pt = [{"template": form, "lp_A": per_f[j][i][0], "lp_B": per_f[j][i][1], "lo": per_f[j][i][0] - per_f[j][i][1],
                       "n_tokens_A": per_f[j][i][2], "n_tokens_B": per_f[j][i][3]} for j, form in enumerate(forms)]
                out.append({"reader": reader.name, "lo": sum(x["lo"] for x in pt) / len(pt),
                            "lp_A": sum(x["lp_A"] for x in pt) / len(pt), "lp_B": sum(x["lp_B"] for x in pt) / len(pt),
                            "templates": list(forms), "per_template": pt, "prefix": "", "format": "continuation",
                            "marker_index": reader.marker, "adapter_name": reader.adapter_name, "unscorable": False})
    return out


# ------------------------------------------------------------------ dispatcher
def score_lo(reader: Any, H: Any, cand_pairs: list[tuple[str, str]], family: str, layer: int | None = None,
             batch: int = 32) -> list[dict[str, Any]]:
    """``H`` [N, d] fp32 (CPU ok); ``cand_pairs[i] = (A, B)`` with A the candidate correct for the
    ORIGINAL state. Returns one dict per state with ``lo = score(A) − score(B)``."""
    import torch

    H = torch.as_tensor(H).float()
    if H.ndim == 1:
        H = H[None]
    if H.shape[0] != len(cand_pairs):
        raise ValueError(f"{H.shape[0]} states but {len(cand_pairs)} candidate pairs")
    if isinstance(reader, R.OLensReader):
        rows = lo_olens(reader, H, cand_pairs, layer=layer, batch=batch)
    elif isinstance(reader, R.NLAReader):
        rows = lo_nla(reader, H, cand_pairs, family, batch=batch)
    elif isinstance(reader, R.JLensReader):  # incl. the R-lens subclass (same cosine readout)
        rows = lo_jlens(reader, H, cand_pairs, layer=layer)
    elif isinstance(reader, R.SkipLensReader):
        rows = lo_skiplens(reader, H, cand_pairs, batch=batch)
    else:
        raise TypeError(f"unknown reader {type(reader).__name__}")
    for r, (a, b) in zip(rows, cand_pairs):
        r["cand_A"], r["cand_B"], r["family"] = a, b, family
    return rows
