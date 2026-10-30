"""F2-4 diagnostics (BRIEF_Z.md "Agam follow-ups 2"). GPU, pod.

    python -m projects.g_agreement.f2.t4_diag --phase A     # target + Oracle: Y1 confusion samples; Oracle lp of both candidates on the F2-1 cells
    python -m projects.g_agreement.f2.t4_diag --phase C     # NLA reconstructor (ar_reconstructor): FVE of every NLA readout in F2-1 and G1

(a) FVE, following EasyNLA (nla/utils/critic.py, nla/schema.py): critic text = nla_meta critic template with the extracted
    <explanation> payload, tokenised without special tokens; prediction = value_head(normalize(raw last-block output at the last
    token, sqrt(d))); FVE = 1 - mean((normalize(pred) - normalize(gold))^2) / baseline, baseline = predict-the-mean variance of the
    normalised gold set (computed on the Mac; raw MSE stored here). Readouts without a closed <explanation> get FVE None.
(b) Y1 puzzle items (297 errors, 103 controls), last token, blocks 44/48/52/56, 1 Oracle sample each (bench sampling).
Outputs cache/g_agreement/f2/t4/{y1_oracle.jsonl, olens_lp.jsonl, fve.jsonl, phase*_done.json}.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, now_iso, read_jsonl

OUT = C.CACHE_DIR / "f2" / "t4"
T1 = C.CACHE_DIR / "f2" / "t1"
Y1_LAYERS = (44, 48, 52, 56)
SEED = 20261015
EXPL = re.compile(r"<explanation>(.*?)</explanation>", re.DOTALL)
CRITIC_TEMPLATE = "Summary of the following text: <text>{explanation}</text> <summary>"


def phase_a(batch: int) -> None:
    import torch

    from projects.g_agreement.agam_viewer.collect import gen_batch
    from projects.g_agreement.g1_agreement.collect import load_target_timed
    from projects.g_agreement.w_pod import common as W
    from projects.g_agreement.y1_site import collect as Y1

    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    target = load_target_timed("f2t4")
    tok = target.tokenizer
    ol = R.OLensReader().bind(target)
    # (a') Oracle lp of key and other on every F2-1 cell
    ctxs = {c["ctx"]: c for c in json.loads((T1 / "contexts.json").read_text())}
    S = torch.load(T1 / "states.pt", map_location="cpu")
    for L in (42, 44):
        cells = [(cx, p) for cx in ctxs for p in ("last", "last-1", "last-2")]
        for s in range(0, len(cells), 32):
            ch = cells[s:s + 32]
            H = torch.stack([S[cx][L][p] for cx, p in ch])
            for (cx, p), r in zip(ch, LO.lo_olens(ol, H, [(ctxs[cx]["key"], ctxs[cx]["other"]) for cx, _ in ch], layer=L, batch=64)):
                append_jsonl(OUT / "olens_lp.jsonl", {"ctx": cx, "layer": L, "pos": p, "lp_key": r["lp_A"], "lp_other": r["lp_B"]})
    print(f"[f2t4/A] Oracle lp done ({(time.time() - t0) / 60:.1f} min)", flush=True)
    # (b) Y1 confusion samples
    items = [it for it in W.load_errors()] + [it for it in json.loads(W.ITEMS_Y1.read_text())["items"] if it.get("family") == "puzzle" and it.get("set") == "error_control"]
    vecs = {}
    for it in items:
        cap = Y1.load_cap(it["item_id"])
        for L in Y1_LAYERS:
            vecs[(it["item_id"], L)] = Y1.cell_vector(cap, L, "0")
    todo = [(it, L) for L in Y1_LAYERS for it in items]
    embed = target.model.get_input_embeddings()
    dev = next(target.model.parameters()).device
    nb = 0
    for s in range(0, len(todo), batch):
        ch = todo[s:s + batch]
        groups = {}
        for it, LL in ch:
            groups.setdefault(LL, []).append(it)
        for LL, its in groups.items():
            ids0, slot, _c, _cid = ol.carrier(LL)
            with torch.no_grad():
                e = embed(torch.tensor([ids0] * len(its), device=dev)).clone()
                for r, it in enumerate(its):
                    v = vecs[(it["item_id"], LL)].to(dev).float()
                    e[r, slot, :] = (ol.alpha * v / v.norm().clamp_min(1e-9)).to(e.dtype)
            seed = SEED + 1000 * LL + nb
            outs = gen_batch(target.model, tok, embeds=e, n_rows=len(its), seed=seed)
            for it, o in zip(its, outs):
                append_jsonl(OUT / "y1_oracle.jsonl", {"item_id": it["item_id"], "set": it.get("set"), "layer": LL, "actual": it["primary"]["answer"],
                                                       "correct": it["source"]["correct"], "text": o["text"], "seed": seed, "finish_reason": o["finish_reason"]})
            nb += 1
        if nb % 8 == 0:
            print(f"[f2t4/A] Y1 Oracle batch {nb} ({(time.time() - t0) / 60:.1f} min)", flush=True)
    (OUT / "phaseA_done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60}, indent=1))
    M.unload(target)


def phase_c(ar_dir: str, batch: int) -> None:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    while not (OUT / "phaseA_done.json").exists() and time.time() - t0 < 3600:  # never share the GPU with the target model
        time.sleep(20)
    tok = AutoTokenizer.from_pretrained(str(Path(ar_dir).parent / "av_base")) if (Path(ar_dir).parent / "av_base" / "tokenizer.json").exists() else AutoTokenizer.from_pretrained(C.TARGET_MODEL_ID)
    m, info = AutoModelForCausalLM.from_pretrained(ar_dir, dtype=torch.bfloat16, device_map="cuda", output_loading_info=True)
    miss = [k for k in info.get("missing_keys", []) if "lm_head" not in k and k not in ("model.norm.weight", "model.language_model.norm.weight")]  # final norm is stripped by design (EasyNLA)
    print(f"[f2t4/C] AR loading: {len(miss)} missing keys (excl. lm_head), {len(info.get('unexpected_keys', []))} unexpected; e.g. {miss[:3]}", flush=True)
    if len(miss) > 0:
        raise RuntimeError("reconstructor weights did not map onto the model; refusing to compute FVE")
    m.eval()
    inner = m.model if hasattr(m, "model") else m
    inner = getattr(inner, "language_model", inner)
    inner.norm = torch.nn.Identity()
    print(f"[f2t4/C] AR loaded: {m.config.num_hidden_layers} blocks ({(time.time() - t0) / 60:.1f} min)", flush=True)
    head = torch.nn.Linear(5120, 5120, bias=False)
    sd = load_file(str(Path(ar_dir) / "value_head.safetensors"))
    head.load_state_dict({"weight": next(iter(sd.values()))})
    head = head.to("cuda", torch.float32)
    scale = 5120 ** 0.5

    def norm(v):
        return v / (v.float().norm(dim=-1, keepdim=True).clamp_min(1e-12) / scale)

    rows = []
    S = torch.load(T1 / "states.pt", map_location="cpu")
    for r in read_jsonl(T1 / "readouts.jsonl"):
        if r["reader"] == "nla":
            rows.append({"src": "f2t1", "k": r["k"], "ctx": r["ctx"], "pos": r["pos"], "text": r["text"], "gold": S[r["ctx"]][42][r["pos"]]})
    for g in read_jsonl(C.CACHE_DIR / "gens" / "g1.jsonl"):
        if g.get("method") == "nla" and g.get("condition") == "genuine":
            p = C.CACHE_DIR / "states" / f"{g['item_id']}.pt"
            if p.exists():
                rows.append({"src": "g1", "k": g["gen_id"], "ctx": g["item_id"], "pos": "last", "text": g["raw_output"], "gold": torch.load(p, map_location="cpu").float()})
    out = OUT / "fve.jsonl"
    todo = []
    for r in rows:
        m_ = EXPL.search(r["text"] or "")
        if not m_:
            append_jsonl(out, {"src": r["src"], "k": r["k"], "ctx": r["ctx"], "pos": r["pos"], "extracted": False, "mse": None})
        else:
            todo.append((r, m_.group(1).strip()))
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    for s in range(0, len(todo), batch):
        ch = todo[s:s + batch]
        enc = [tok.encode(CRITIC_TEMPLATE.format(explanation=e), add_special_tokens=False) for _, e in ch]
        T = max(len(x) for x in enc)
        ids = torch.full((len(enc), T), pad, dtype=torch.long)
        att = torch.zeros((len(enc), T), dtype=torch.long)
        for i, x in enumerate(enc):
            ids[i, :len(x)] = torch.tensor(x)
            att[i, :len(x)] = 1
        with torch.no_grad():
            h = inner(input_ids=ids.cuda(), attention_mask=att.cuda()).last_hidden_state
            last = h[torch.arange(len(enc)), att.sum(1).cuda() - 1].float()
            pred = head(norm(last))
            gold = torch.stack([r["gold"].float() for r, _ in ch]).cuda()
            mse = ((norm(pred) - norm(gold)) ** 2).mean(dim=-1).cpu().tolist()
            cos = torch.nn.functional.cosine_similarity(pred, gold, dim=-1).cpu().tolist()
        for (r, e), ms, cs in zip(ch, mse, cos):
            append_jsonl(out, {"src": r["src"], "k": r["k"], "ctx": r["ctx"], "pos": r["pos"], "extracted": True, "mse": ms, "cos": cs, "n_tokens": len(e)})
    gold_all = torch.stack([r["gold"].float() for r in rows])
    v = norm(gold_all)
    mu = v.mean(0, keepdim=True)
    base = float(((v - mu) ** 2).mean())
    (OUT / "phaseC_done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60, "n_rows": len(rows), "n_extracted": len(todo),
                                                      "baseline_rawvar_our_states": base}, indent=1))
    print(f"[f2t4/C] done: {len(todo)}/{len(rows)} extracted; baseline {base:.4f} ({(time.time() - t0) / 60:.1f} min)", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["A", "C"], required=True)
    ap.add_argument("--batch", type=int, default=48)
    ap.add_argument("--ar-dir", default=None)
    a = ap.parse_args()
    if a.phase == "A":
        phase_a(a.batch)
    else:
        phase_c(a.ar_dir, 16)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
