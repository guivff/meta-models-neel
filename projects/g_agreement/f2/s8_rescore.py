"""S8: full-candidate native scores for the F2-2 read-backs and the X3 ERROR puzzles (BRIEF_S.md "S8"). GPU, pod.

    python -m projects.g_agreement.f2.s8_rescore --phase A     # J-lens + Oracle (target loaded)
    python -m projects.g_agreement.f2.s8_rescore --phase B     # NLA (separate reader model)

Every candidate of the set gets its native score (Oracle: summed log p("- X") after its carrier; NLA: mean over the
family's templates of summed log p(template(X)) after "<explanation>\n"; J-lens: max cosine over single-token variants,
None if X has none). Ownership set = the 29 names of the 32 X2 ownership pairs; puzzle set = A-H.
Outputs cache/g_agreement/s8/scores.jsonl: {key, source (f2|x3), reader, layer, scores {X: s}}.
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core import states as S
from projects.g_agreement.core.accounting import append_jsonl, now_iso, read_jsonl
from projects.g_agreement.x2_causal import collect as X

OUT = C.CACHE_DIR / "s8"
T2 = C.CACHE_DIR / "f2" / "t2"
SYMBOLS = list("ABCDEFGH")


def name_set() -> list[str]:
    pairs = X.x2_pairs(C.load_items("test", 0, path=X.ITEMS_X), families=("ownership",))
    return sorted({c for p in pairs for v in "AB" for c in p[v]["primary"]["candidates"]})


def x3_error_items() -> list[dict[str, Any]]:
    items = C.load_items("all", 0, path=C.DATASET_DIR / "items_x3_selected.json")
    return [it for it in items if it.get("set") == "error"]


def jobs(read_layers: tuple[int, ...]) -> list[tuple[str, str, int, Any, list[str], str]]:
    """(key, source, layer, h, candidates, family) for every vector to score."""
    import torch

    names = name_set()
    reads = torch.load(T2 / "readvecs.pt")
    out = []
    for r in read_jsonl(T2 / "behaviour.jsonl"):
        for L in read_layers:
            if L in reads[r["key"]]:
                out.append((r["key"], "f2", L, reads[r["key"]][L].float(), names, "ownership"))
    for it in x3_error_items():
        if 42 in read_layers:
            out.append((it["item_id"], "x3", 42, S.load_state(it["item_id"]).float().reshape(-1), SYMBOLS, "puzzle"))
    return out


def oracle_scores(ol: R.OLensReader, h: Any, cands: list[str], layer: int) -> dict[str, float]:
    import torch

    t = ol.target
    ids0, slot, _c, _cid = ol.carrier(layer)
    tok = t.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    emb = t.model.get_input_embeddings()
    dev = next(t.model.parameters()).device
    rows = [list(ids0) + LO.encode(tok, LO.OLENS_BULLET.format(X=c)) for c in cands]

    def embed_fn(ids_t):
        with torch.no_grad():
            e = emb(ids_t).clone()
            v = h.to(dev).float()
            e[:, slot, :] = (ol.alpha * v / v.norm().clamp_min(1e-9)).to(e.dtype)
        return e

    lps = LO._summed_logprobs(t.model, rows, len(ids0), pad, dev, embed_fn=embed_fn)
    return dict(zip(cands, lps))


def jlens_scores(jl: R.JLensReader, h: Any, cands: list[str], layer: int) -> dict[str, float | None]:
    import torch

    J, w_u = jl.J[layer], jl.w_u
    if layer not in jl._denom:
        jl._denom[layer] = (w_u @ J).norm(dim=1).clamp_min(1e-9)
    with torch.no_grad():
        z = (h.to(w_u.device).float() @ J.T) @ w_u.T / jl._denom[layer]
    out = {}
    for c in cands:
        v = LO.token_variants(jl.tokenizer, c)
        out[c] = max(float(z[t]) for t in v.values()) if v else None
    return out


def nla_scores(nla: R.NLAReader, h: Any, cands: list[str], family: str) -> dict[str, float]:
    import torch

    tok = nla.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(nla.model.parameters()).device
    head = list(nla.ids) + LO.encode(tok, LO.NLA_PREFIX)
    acc = {c: 0.0 for c in cands}
    temps = LO.templates_for(family)
    for tmpl in temps:
        rows = [head + LO.encode(tok, tmpl.format(X=c)) for c in cands]
        nla._vec["v"] = torch.stack([h.float()] * len(rows))
        try:
            lps = LO._summed_logprobs(nla.model, rows, len(head), pad, dev)
        finally:
            nla._vec["v"] = None
        for c, lp in zip(cands, lps):
            acc[c] += lp / len(temps)
    return acc


def main() -> int:
    import torch

    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = lambda s: print(f"[s8/{a.phase}] {s} ({(time.time() - t0) / 60:.1f} min)", flush=True)  # noqa: E731
    sp = OUT / "scores.jsonl"
    done = {(r["key"], r["reader"], r["layer"]) for r in read_jsonl(sp)} if sp.exists() else set()
    if a.phase == "A":
        from projects.g_agreement.g1_agreement.collect import load_target_timed

        target = load_target_timed("s8")
        js = jobs((42, 44))
        log(f"{len(js)} vectors")
        jl = R.JLensReader().bind(target, layers_keep=[42, 44])
        for key, src, L, h, cands, fam in js:
            if (key, "jlens", L) not in done:
                append_jsonl(sp, {"key": key, "source": src, "reader": "jlens", "layer": L, "scores": jlens_scores(jl, h, cands, L)})
        del jl
        torch.cuda.empty_cache()
        log("J-lens done")
        ol = R.OLensReader().bind(target)
        for i, (key, src, L, h, cands, fam) in enumerate(js):
            if (key, "olens", L) not in done:
                append_jsonl(sp, {"key": key, "source": src, "reader": "olens", "layer": L, "scores": oracle_scores(ol, h, cands, L)})
            if i % 500 == 0:
                log(f"Oracle {i}/{len(js)}")
        log("Oracle done")
        M.unload(target)
    else:
        js = jobs((42,))
        nla = R.NLAReader().bind()
        for i, (key, src, L, h, cands, fam) in enumerate(js):
            if (key, "nla", L) not in done:
                append_jsonl(sp, {"key": key, "source": src, "reader": "nla", "layer": L, "scores": nla_scores(nla, h, cands, fam)})
            if i % 500 == 0:
                log(f"NLA {i}/{len(js)}")
        log("NLA done")
        nla.unload()
    (OUT / f"phase{a.phase}_done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
