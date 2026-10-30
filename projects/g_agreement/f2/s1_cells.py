"""S1: are the F2-3 template cells load-bearing? (BRIEF_S.md "S1", pre-registered 2026-10-15). GPU, pod.

    python -m projects.g_agreement.f2.s1_cells [--budget-min 80] [--smoke]

Edit at blocks 36, 38, 44 (tense: 36, 38): h' = h_src + alpha * v at a set of prompt positions (prefill only), greedy
8-token answer, read-backs at blocks 44 and 56 (last token), J-lens and Oracle native LO there. Arms (alpha 0.5, 1, 2):
  cells   Delta at the F2-3 cell positions          all     Delta at every position (positive control)
  last    Delta at the last token                   noncell Delta at |cells| non-cell, non-content positions (seeded)
  rand    random unit direction x ||alpha Delta(p)|| at the cells
  probe   X1 E2 probe direction (leave-this-pair-out), signed toward the other version, x ||alpha Delta(p)|| at the cells
  cellsT / cellsI   the cells restricted to chat-template tokens / instruction words (secondary)
Delta(p) = h_other(map(p)) - h_src(p); map = identity before the pair's first differing token, from the end after it.
Ownership: model LO = first-token lp(other) - lp(own). Tense: teacher-forced summed lp of the other version's natural
8-token answer minus the own one's. Outputs cache/g_agreement/s1/{cells.json, behaviour.jsonl, readvecs.pt, lo.jsonl, done.json}.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring as SC
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, now_iso, read_jsonl
from projects.g_agreement.w_pod import common as W
from projects.g_agreement.x1_bank import analyze as XA
from projects.g_agreement.x1_bank import collect as X1
from projects.g_agreement.x2_causal import collect as X

OUT = C.CACHE_DIR / "s1"
ALPHAS = (0.5, 1.0, 2.0)
READ = (44, 56)
# BRIEF_S S1 operationalisation + deviation (tense offset 16 dropped): family -> edit block -> cell offsets from the last token
CELLS = {"ownership": {36: [2, 3, 6, 8, 10, 11, 12, 13, 14], 38: [2, 3, 6, 8, 10, 11, 12, 13, 14], 44: [2, 3, 6, 8, 11, 12, 13, 14, 16]},
         "tense": {36: [3], 38: [3]}}
EDIT_LAYERS = (36, 38, 44)
TEMPLATE_TOKENS = {"<think>", "</think>", "\n\n", "\n", "<|im_start|>", "<|im_end|>", "assistant"}
TIME_WORDS = ("yesterday", "tomorrow", "did", "will", "do", "last", "next", "ago", "tonight", "today")


def state_pairs(fam: str) -> list[dict[str, Any]]:
    return X.x2_pairs(C.load_items("test", 0, path=X.ITEMS_X), families=(fam,), n_pairs=32)


def first_diff(a: list[int], b: list[int]) -> int:
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


def pos_map(T_src: int, T_oth: int, d: int) -> list[int]:
    """Position in the other render that pairs with each source position (identity before d, from the end after it)."""
    return [p if p < d else min(T_oth - 1, max(0, p + (T_oth - T_src))) for p in range(T_src)]


def content_positions(tok: Any, ids: list[int], oth_ids: list[int], pmap: list[int], it: dict[str, Any]) -> set[int]:
    """Tokens that differ from their paired token, or overlap a name / object / candidate / subject / place / time word."""
    text_ends, prev = [], ""
    for i in range(len(ids)):
        prev = tok.decode(ids[: i + 1], skip_special_tokens=False)
        text_ends.append(len(prev))
    starts = [0] + text_ends[:-1]
    words: set[str] = set()
    sec, con = it.get("secondary") or {}, it.get("construction") or {}
    for w in list(it["primary"]["candidates"]) + list(sec.get("entities") or []) + list(sec.get("objects") or []):
        words |= set(str(w).split())
    for k in ("subject", "place"):
        if con.get(k):
            words |= set(str(con[k]).split())
    if it["family"] == "tense":
        words |= set(TIME_WORDS)
    spans = []
    for w in words:
        for m in re.finditer(r"\b" + re.escape(w) + r"\b", prev, flags=re.IGNORECASE):
            spans.append((m.start(), m.end()))
    out = {p for p in range(len(ids)) if ids[p] != oth_ids[pmap[p]]}
    for p in range(len(ids)):
        if any(s < text_ends[p] and starts[p] < e for s, e in spans):
            out.add(p)
    return out


def tf_lo(target: Any, ids: list[int], edit_layer: int | None, row_positions: list[list[int]], row_vectors: list[Any],
          c_own: list[int], c_oth: list[int]) -> list[float]:
    """Summed teacher-forced lp of c_oth minus c_own after ``ids``, per edit row (edit = replace block output at positions)."""
    import torch

    model = target.model
    dev = next(model.parameters()).device
    T = len(ids)
    B = len(row_positions)
    seqs = [ids + c for _ in range(B) for c in (c_own, c_oth)]
    Lmax = max(len(x) for x in seqs)
    from projects.g_agreement.core import generate as G

    pad = G.pad_id(target.tokenizer)
    x = torch.tensor([q + [pad] * (Lmax - len(q)) for q in seqs], device=dev)
    am = torch.tensor([[1] * len(q) + [0] * (Lmax - len(q)) for q in seqs], device=dev)
    handles = []
    if edit_layer is not None:
        P = [torch.tensor(ps, dtype=torch.long) for ps in row_positions]
        V = [torch.as_tensor(v).float() for v in row_vectors]

        def hook(_m, _i, out):
            h = out[0] if isinstance(out, tuple) else out
            for b in range(2 * B):
                h[b, P[b // 2].to(h.device), :] = V[b // 2].to(h.device, h.dtype)
            return out

        handles.append(M.blocks(model)[int(edit_layer)].register_forward_hook(hook))
    try:
        with torch.no_grad(), M.disable_adapter_ctx(model):
            logits = model(input_ids=x, attention_mask=am).logits
    finally:
        for hd in handles:
            hd.remove()
    out = []
    for b in range(B):
        tot = []
        for j, c in enumerate((c_own, c_oth)):
            row = 2 * b + j
            lp = torch.log_softmax(logits[row, T - 1:T - 1 + len(c)].float(), dim=-1)
            tot.append(float(lp[torch.arange(len(c)), torch.tensor(c, device=lp.device)].sum()))
        out.append(tot[1] - tot[0])
    return out


def main() -> int:
    import torch

    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-min", type=float, default=80.0)
    ap.add_argument("--smoke", action="store_true", help="2 pairs per family, one layer")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    T0 = float(os.environ.get("S1_T0", "0") or 0)
    pod_min = lambda: (time.time() - T0) / 60 if T0 else (time.time() - t0) / 60  # noqa: E731
    log = lambda s: print(f"[s1] {s} (wall {(time.time() - t0) / 60:.1f} min, pod {pod_min():.1f})", flush=True)  # noqa: E731
    target = load_target_timed("s1")
    tok = target.tokenizer
    beh = OUT / "behaviour.jsonl"
    done = {r["key"] for r in read_jsonl(beh)} if beh.exists() else set()
    reads: dict[str, dict[int, Any]] = torch.load(OUT / "readvecs.pt") if (OUT / "readvecs.pt").exists() else {}
    cells_meta: dict[str, Any] = {}
    natural = {(r0["pair_id"], r0["source"]): r0["new_ids"] for r0 in (read_jsonl(beh) if beh.exists() else []) if r0["arm"] == "natural"}
    stopped = None
    for fam, by_layer in CELLS.items():
        layers = sorted(by_layer)[:1] if a.smoke else sorted(by_layer)
        bank = X1.load_pairs(split="test", families=(fam,))
        states = state_pairs(fam)[: 2 if a.smoke else None]
        ids = {p[v]["item_id"]: M.render_item(tok, p[v]["prompt_text"], p[v].get("system")) for p in bank for v in "AB"}
        caps = {}
        for p in bank:
            for v in "AB":
                iid = p[v]["item_id"]
                cap = M.capture(target.model, ids[iid], list(layers), list(range(len(ids[iid]))))
                caps[iid] = {L: cap[L].float() for L in layers}
        log(f"{fam}: captured {len(caps)} states at {layers}; {len(states)} state pairs")
        for pair in states:
            if pod_min() > a.budget_min:
                stopped = f"{fam}|{pair['pair_id']}"
                break
            pid = pair["pair_id"]
            train = [q for q in bank if q["pair_id"] != pid]
            for src in ("A", "B"):  # natural rows of both versions first (tense TF needs both natural answers)
                it = pair[src]
                si = ids[it["item_id"]]
                own, other = str(it["primary"]["answer"]), X.other_candidate(it)
                fti = None
                if fam == "ownership":
                    ft = W.pair_first_tokens(tok, own, other, "chat")
                    fti = None if ft["unscorable"] else [ft["first_A"], ft["first_B"]]
                nat_key = f"{pid}|{src}|natural|0|0"
                if nat_key in done:
                    continue
                r = W.prefill_generate(target, si, read_layers=READ, first_token_ids=fti)[0]
                parsed, _ = SC.extract_target_answer(r["answer_text"], it)
                lp = r.get("lp_first") or [None, None]
                reads[nat_key] = {L: r["read"][L].to(torch.bfloat16) for L in READ}
                natural[(pid, src)] = r["new_ids"]
                append_jsonl(beh, {"key": nat_key, "pair_id": pid, "family": fam, "source": src, "item_id": it["item_id"], "arm": "natural",
                                   "layer": 0, "alpha": 0.0, "cand_own": own, "cand_other": other, "answer_text": r["answer_text"],
                                   "new_ids": r["new_ids"], "parsed": parsed, "flipped": parsed == other, "kept": parsed == own,
                                   "lo_model": (None if None in lp else lp[1] - lp[0]), "positions": [], "n_tokens": len(si)})
                done.add(nat_key)
            if fam == "tense":
                for src in ("A", "B"):
                    oth = "B" if src == "A" else "A"
                    si = ids[pair[src]["item_id"]]
                    if f"{pid}|{src}|natural|0|0|tf" not in done:
                        v = tf_lo(target, si, None, [[]], [None], natural[(pid, src)], natural[(pid, oth)])[0]
                        append_jsonl(OUT / "tf.jsonl", {"key": f"{pid}|{src}|natural|0|0", "lo_tf": v})
                        done.add(f"{pid}|{src}|natural|0|0|tf")
            for src in ("A", "B"):
                oth = "B" if src == "A" else "A"
                it, io = pair[src], pair[oth]
                si, oi = ids[it["item_id"]], ids[io["item_id"]]
                T = len(si)
                d = first_diff(si, oi)
                pmap = pos_map(T, len(oi), d)
                own, other = str(it["primary"]["answer"]), X.other_candidate(it)
                fti = None
                if fam == "ownership":
                    ft = W.pair_first_tokens(tok, own, other, "chat")
                    fti = None if ft["unscorable"] else [ft["first_A"], ft["first_B"]]
                content = content_positions(tok, si, oi, pmap, it)
                for L in layers:
                    hs = caps[it["item_id"]][L]
                    ho = caps[io["item_id"]][L][pmap]
                    D = ho - hs
                    n = D.norm(dim=1)
                    cpos = sorted({T - 1 - k for k in by_layer[L]})
                    meta = cells_meta.setdefault(f"{fam}|{L}|{pid}|{src}", {})
                    tokstr = {p: tok.decode([si[p]]) for p in cpos}
                    cT = [p for p in cpos if tokstr[p] in TEMPLATE_TOKENS]
                    cI = [p for p in cpos if tokstr[p] not in TEMPLATE_TOKENS]
                    pool = [p for p in range(d, T - 1) if p not in cpos and p not in content]
                    rng = np.random.default_rng(C.stable_seed("s1", "noncell", f"{pid}|{src}", L))
                    ncp = sorted(int(x) for x in rng.choice(pool, size=min(len(cpos), len(pool)), replace=False)) if pool else []
                    g = torch.Generator().manual_seed(C.stable_seed("s1", "rand", f"{pid}|{src}", L))
                    rnd = torch.randn((len(cpos), hs.shape[1]), generator=g)
                    rnd = rnd / rnd.norm(dim=1, keepdim=True)
                    pv = XA.pos_version(pair)
                    sign = 1.0 if oth == pv else -1.0
                    pdir = []
                    for p in cpos:
                        k = T - 1 - p
                        H = {q[v]["item_id"]: caps[q[v]["item_id"]][L][len(ids[q[v]["item_id"]]) - 1 - k].numpy().astype(np.float64)
                             for q in train for v in "AB"}
                        u, _m = XA.direction_binary(train, H)
                        pdir.append(sign * torch.tensor(u, dtype=torch.float32))
                    pdir = torch.stack(pdir)
                    meta.update({"cells": cpos, "cell_tokens": [tokstr[p] for p in cpos], "cellsT": cT, "cellsI": cI, "noncell": ncp,
                                 "noncell_tokens": [tok.decode([si[p]]) for p in ncp], "pool_size": len(pool), "first_diff": d, "T": T,
                                 "delta_norm_cells": [float(n[p]) for p in cpos], "delta_norm_noncell": [float(n[p]) for p in ncp],
                                 "probe_cos_delta": [float(torch.nn.functional.cosine_similarity(pdir[i], D[p], dim=0)) for i, p in enumerate(cpos)]})
                    ents = []
                    for al in ALPHAS:
                        def full(ps):
                            return (ps, torch.stack([hs[p] + al * D[p] for p in ps]))
                        ents.append(("cells", al, *full(cpos)))
                        ents.append(("all", al, *full(list(range(T)))))
                        ents.append(("last", al, *full([T - 1])))
                        if ncp:
                            ents.append(("noncell", al, *full(ncp)))
                        ents.append(("rand", al, cpos, torch.stack([hs[p] + al * n[p] * rnd[i] for i, p in enumerate(cpos)])))
                        ents.append(("probe", al, cpos, torch.stack([hs[p] + al * n[p] * pdir[i] for i, p in enumerate(cpos)])))
                        if cT and cI:
                            ents.append(("cellsT", al, *full(cT)))
                            ents.append(("cellsI", al, *full(cI)))
                    ents = [e for e in ents if f"{pid}|{src}|{e[0]}|{L}|{e[1]}" not in done]
                    for s in range(0, len(ents), 24):
                        ch = ents[s:s + 24]
                        rows = W.prefill_generate(target, si, edit_layer=L, row_positions=[e[2] for e in ch], row_vectors=[e[3] for e in ch],
                                                  read_layers=READ, first_token_ids=fti)
                        tfv = (tf_lo(target, si, L, [e[2] for e in ch], [e[3] for e in ch], natural[(pid, src)], natural[(pid, oth)])
                               if fam == "tense" else [None] * len(ch))
                        for (arm, al, ps, _v), r, tv in zip(ch, rows, tfv):
                            if tv is not None:
                                append_jsonl(OUT / "tf.jsonl", {"key": f"{pid}|{src}|{arm}|{L}|{al}", "lo_tf": tv})
                            key = f"{pid}|{src}|{arm}|{L}|{al}"
                            parsed, _ = SC.extract_target_answer(r["answer_text"], it)
                            lp = r.get("lp_first") or [None, None]
                            reads[key] = {Lr: r["read"][Lr].to(torch.bfloat16) for Lr in READ}
                            append_jsonl(beh, {"key": key, "pair_id": pid, "family": fam, "source": src, "item_id": it["item_id"], "arm": arm,
                                               "layer": L, "alpha": al, "cand_own": own, "cand_other": other, "answer_text": r["answer_text"],
                                               "new_ids": r["new_ids"], "parsed": parsed, "flipped": parsed == other, "kept": parsed == own,
                                               "lo_model": (None if None in lp else lp[1] - lp[0]), "positions": [int(p) for p in ps], "n_tokens": T})
                            done.add(key)
            torch.save(reads, OUT / "readvecs.pt")
            log(f"{fam} {pid} done")
        (OUT / "cells.json").write_text(json.dumps(cells_meta, ensure_ascii=False))
        del caps
        if stopped:
            log(f"budget reached before {stopped}")
            break
    torch.save(reads, OUT / "readvecs.pt")
    rows = read_jsonl(beh)
    lop = OUT / "lo.jsonl"
    lo_done = {r["key"] for r in read_jsonl(lop)} if lop.exists() else set()
    for name in ("jlens", "olens"):
        rd = R.JLensReader().bind(target, layers_keep=list(READ)) if name == "jlens" else R.OLensReader().bind(target)
        for Lr in READ:
            for fam in CELLS:
                todo = [r for r in rows if r["family"] == fam and f"{name}|{Lr}|{r['key']}" not in lo_done and r["key"] in reads]
                for s in range(0, len(todo), 64):
                    ch = todo[s:s + 64]
                    Hm = torch.stack([reads[r["key"]][Lr].float() for r in ch])
                    for r, q in zip(ch, LO.score_lo(rd, Hm, [(r["cand_own"], r["cand_other"]) for r in ch], fam, layer=Lr, batch=64)):
                        append_jsonl(lop, {"key": f"{name}|{Lr}|{r['key']}", "reader": name, "layer": Lr, "entry": r["key"], "lo": q.get("lo")})
        del rd
        torch.cuda.empty_cache()
        log(f"{name} LO done")
    (OUT / "done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60, "pod_min": pod_min(),
                                               "stopped_before": stopped, "n_rows": len(rows)}, indent=1))
    M.unload(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
