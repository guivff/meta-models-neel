"""F2-5: Agam's exact stems with a copy control on the 32 G1 test states (BRIEF_Z.md "Agam follow-ups 3"). GPU, pod.

    python -m projects.g_agreement.f2.t5_stems --phase A     # target: answers, captures, J-lens, Oracle (LO + 4 samples)
    python -m projects.g_agreement.f2.t5_stems --phase B     # NLA (LO + 4 samples) on the saved block-42 states

Formats: a = chat template (G1); b = chat template + assistant prefill stem; c = plain text "<prompt> <stem>".
Positions last, last-1, last-2. Captures at blocks 36..60 even (J-lens top-10 for the viewer); Oracle at 42 and 44;
NLA at 42. Outputs cache/g_agreement/f2/t1/{contexts.json, states.pt, readouts.jsonl, lo.jsonl, phase{A,B}_done.json}.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, now_iso, read_jsonl

OUT = C.CACHE_DIR / "f2" / "t5"
FAMS = ("language", "tense", "ownership", "mapping")
FORMATS = ("a", "b", "c")
POS = ("last", "last-1", "last-2")
CAP_LAYERS = list(range(36, 61, 2))
OL_LAYERS = (44, 56)
NLA_LAYER = 42
N_SAMPLES = 4
SEED_BASE = 20261016


def stems_for(it: dict[str, Any]) -> dict[str, str | None]:
    """{variant: stem}. a = no stem; language/tense: key-stem and other-stem (Agam's wording); ownership/mapping: generic."""
    fam = it["family"]
    key, oth = str(it["primary"]["answer"]), other(it)
    if fam == "language":
        return {"a": None, "keystem": f"The answer, in {key}, is", "otherstem": f"The answer, in {oth}, is"}
    if fam == "tense":
        return {"a": None, "keystem": f"The answer, in the {key} tense, is", "otherstem": f"The answer, in the {oth} tense, is"}
    return {"a": None, "generic": "The answer is"}


def other(it: dict[str, Any]) -> str:
    c = [str(x) for x in it["primary"]["candidates"]]
    return c[1] if c[0] == str(it["primary"]["answer"]) else c[0]


def load_items() -> list[dict[str, Any]]:
    d = json.loads(C.ITEMS_JSON.read_text())
    return [i for i in (d["items"] if isinstance(d, dict) else d) if i.get("split") == "test" and i["family"] in FAMS]


def build_contexts(tok: Any) -> list[dict[str, Any]]:
    from projects.g_agreement.agam_viewer.collect import token_display

    out = []
    for it in load_items():
        base = M.render_item(tok, it["prompt_text"], it.get("system"))
        for var, stem in stems_for(it).items():
            fmts = [("chat", base)] if stem is None else [("chat", base + tok(stem, add_special_tokens=False)["input_ids"]),
                                                          ("plain", tok(f"{it['prompt_text']} {stem}", add_special_tokens=False)["input_ids"])]
            for fmtname, ids in fmts:
                T = len(ids)
                out.append({"ctx": f"{it['item_id']}|{var}|{fmtname}", "item_id": it["item_id"], "pair_id": it["pair_id"], "version": it.get("version"),
                            "family": it["family"], "variant": var, "format": fmtname, "stem": stem, "key": str(it["primary"]["answer"]), "other": other(it),
                            "stem_names": (str(it["primary"]["answer"]) if var == "keystem" else other(it) if var == "otherstem" else None),
                            "prompt_text": it["prompt_text"], "ids": ids, "positions": {p: T - 1 - k for k, p in enumerate(POS)},
                            "tokens": [token_display(tok, t) for t in ids]})
    return out


def elapsed_min() -> float:
    t0 = float(os.environ.get("F2_T0", "0") or 0)
    return (time.time() - t0) / 60 if t0 else 0.0


def done_keys(p: Path) -> set[str]:
    return {r["k"] for r in read_jsonl(p)} if p.exists() else set()


def phase_a(batch: int) -> None:
    import torch

    from projects.g_agreement.agam_viewer.collect import gen_batch, token_display
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    target = load_target_timed("f2t5")
    tok = target.tokenizer
    ctxs = build_contexts(tok)
    log = lambda s: print(f"[f2t5/A] {s} (wall {(time.time() - t0) / 60:.1f} min, pod {elapsed_min():.1f})", flush=True)  # noqa: E731
    log(f"{len(ctxs)} contexts")
    # model's own greedy answer per format (16 tokens)
    from projects.g_agreement.core import generate as Gm
    for c in ctxs:
        c["model_answer"] = Gm.generate_ids(target.model, tok, c["ids"], max_new_tokens=16, sampling=None, adapter_enabled=False).raw_output
    log("model answers done")
    caps = {}
    for c in ctxs:
        cap = M.capture(target.model, c["ids"], CAP_LAYERS, [c["positions"][p] for p in POS])
        caps[c["ctx"]] = {L: {p: cap[L][i].clone() for i, p in enumerate(POS)} for L in CAP_LAYERS}
    torch.save({k: {L: v[L] for L in (42, 44, 56)} for k, v in caps.items()}, OUT / "states.pt")
    (OUT / "contexts.json").write_text(json.dumps(ctxs, indent=1, ensure_ascii=False))
    log("captures done")
    RD, LOP = OUT / "readouts.jsonl", OUT / "lo.jsonl"
    done_r, done_l = done_keys(RD), done_keys(LOP)
    jl = R.JLensReader().bind(target, layers_keep=CAP_LAYERS)
    for c in ctxs:
        for L in CAP_LAYERS:
            for p in POS:
                k = f"jlens|{c['ctx']}|{L}|{p}|0"
                if k in done_r:
                    continue
                rr = jl.read(caps[c["ctx"]][L][p], L)
                append_jsonl(RD, {"k": k, "reader": "jlens", "ctx": c["ctx"], "layer": L, "pos": p, "sample": 0, "token_ids": rr.native["token_ids"],
                                  "tokens_decoded": rr.native["tokens_decoded"], "tokens": [token_display(tok, t) for t in rr.native["token_ids"]],
                                  "scores": rr.native["scores"]})
            if L in (42, 44, 56, 60) and f"jlens|{c['ctx']}|{L}|last" not in done_l:
                H = torch.stack([caps[c["ctx"]][L][p] for p in POS])
                for p, r in zip(POS, LO.score_lo(jl, H, [(c["key"], c["other"])] * len(POS), c["family"], layer=L)):
                    append_jsonl(LOP, {"k": f"jlens|{c['ctx']}|{L}|{p}", "reader": "jlens", "ctx": c["ctx"], "layer": L, "pos": p, "lo": r.get("lo"), "unscorable": r.get("unscorable")})
    del jl
    torch.cuda.empty_cache()
    log("J-lens done")
    ol = R.OLensReader().bind(target)
    for L in OL_LAYERS:
        cells = [(c, p) for c in ctxs for p in POS if f"olens|{c['ctx']}|{L}|{p}" not in done_l]
        for s in range(0, len(cells), 16):
            ch = cells[s:s + 16]
            H = torch.stack([caps[c["ctx"]][L][p] for c, p in ch])
            for (c, p), r in zip(ch, LO.score_lo(ol, H, [(c["key"], c["other"]) for c, _ in ch], c["family"], layer=L, batch=32)):
                append_jsonl(LOP, {"k": f"olens|{c['ctx']}|{L}|{p}", "reader": "olens", "ctx": c["ctx"], "layer": L, "pos": p, "lo": r.get("lo")})
    log("Oracle LO done")
    todo = [(c, L, p, si) for L in OL_LAYERS for c in ctxs for p in POS for si in range(N_SAMPLES) if f"olens|{c['ctx']}|{L}|{p}|{si}" not in done_r]
    embed = target.model.get_input_embeddings()
    dev = next(target.model.parameters()).device
    nb = 0
    i = 0
    while i < len(todo):
        L = todo[i][1]
        ch = [todo[i]]
        j = i + 1
        while j < len(todo) and len(ch) < batch and todo[j][1] == L:
            ch.append(todo[j]); j += 1
        ids0, slot, _c, _cid = ol.carrier(L)
        with torch.no_grad():
            e = embed(torch.tensor([ids0] * len(ch), device=dev)).clone()
            for r, (c, _L, p, _si) in enumerate(ch):
                v = caps[c["ctx"]][L][p].to(dev).float()
                e[r, slot, :] = (ol.alpha * v / v.norm().clamp_min(1e-9)).to(e.dtype)
        seed = SEED_BASE + 1000 * L + nb
        outs = gen_batch(target.model, tok, embeds=e, n_rows=len(ch), seed=seed)
        for r, ((c, _L, p, si), o) in enumerate(zip(ch, outs)):
            append_jsonl(RD, {"k": f"olens|{c['ctx']}|{L}|{p}|{si}", "reader": "olens", "ctx": c["ctx"], "layer": L, "pos": p, "sample": si, "text": o["text"],
                              "seed": seed, "row": r, "n_new_tokens": o["n_new_tokens"], "finish_reason": o["finish_reason"]})
        nb += 1
        i = j
        if nb % 6 == 0:
            log(f"Oracle batch {nb}, {len(todo) - j} rows left")
    (OUT / "phaseA_done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60, "pod_min": elapsed_min(), "oracle_batches": nb}, indent=1))
    log("phase A done")
    M.unload(target)


def phase_b(batch: int) -> None:
    import torch

    from projects.g_agreement.agam_viewer.collect import gen_batch

    t0 = time.time()
    ctxs = json.loads((OUT / "contexts.json").read_text())
    S = torch.load(OUT / "states.pt", map_location="cpu")
    RD, LOP = OUT / "readouts.jsonl", OUT / "lo.jsonl"
    done_r, done_l = done_keys(RD), done_keys(LOP)
    nla = R.NLAReader().bind()
    for c in ctxs:
        if f"nla|{c['ctx']}|{NLA_LAYER}|last" in done_l:
            continue
        H = torch.stack([S[c["ctx"]][NLA_LAYER][p] for p in POS])
        for p, r in zip(POS, LO.score_lo(nla, H, [(c["key"], c["other"])] * len(POS), c["family"])):
            append_jsonl(LOP, {"k": f"nla|{c['ctx']}|{NLA_LAYER}|{p}", "reader": "nla", "ctx": c["ctx"], "layer": NLA_LAYER, "pos": p, "lo": r.get("lo")})
    todo = [(c, p, si) for c in ctxs for p in POS for si in range(N_SAMPLES) if f"nla|{c['ctx']}|{NLA_LAYER}|{p}|{si}" not in done_r]
    nb = 0
    for s in range(0, len(todo), batch):
        ch = todo[s:s + batch]
        nla._vec["v"] = torch.stack([S[c["ctx"]][NLA_LAYER][p].float() for c, p, _ in ch])
        seed = SEED_BASE + 77000 + nb
        try:
            outs = gen_batch(nla.model, nla.tokenizer, ids=nla.ids, n_rows=len(ch), seed=seed)
        finally:
            nla._vec["v"] = None
        for r, ((c, p, si), o) in enumerate(zip(ch, outs)):
            append_jsonl(RD, {"k": f"nla|{c['ctx']}|{NLA_LAYER}|{p}|{si}", "reader": "nla", "ctx": c["ctx"], "layer": NLA_LAYER, "pos": p, "sample": si,
                              "text": o["text"], "seed": seed, "row": r, "n_new_tokens": o["n_new_tokens"], "finish_reason": o["finish_reason"]})
        nb += 1
        print(f"[f2t5/B] NLA batch {nb}: {len(ch)} rows ({(time.time() - t0) / 60:.1f} min)", flush=True)
    (OUT / "phaseB_done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60, "nla_batches": nb,
                                                      "n_hook_calls": nla.n_hook_calls}, indent=1))
    nla.unload()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B", "contexts"], required=True)
    ap.add_argument("--batch", type=int, default=48)
    a = ap.parse_args()
    if a.phase == "contexts":
        tok = M.load_tokenizer()
        for c in build_contexts(tok):
            print(c["ctx"], len(c["ids"]), repr(c["stem"]), [c["tokens"][i]["t"] for i in c["positions"].values()])
        return 0
    phase_a(a.batch) if a.phase == "A" else phase_b(a.batch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
