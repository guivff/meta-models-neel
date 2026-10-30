"""S8 pod part (Oracle + NLA). J-lens and probe run on CPU (s8_analyze.py).

Phase O (target + Oracle): S8b native lp over {m, c, d} at blocks 42/48/52/56; S8b free text (1 sample) at 42/56;
                           S8a native lp over the 29 F2-2 names at read blocks 42/44 (arms natural, J_scaled, perp_scaled, rand_scaled_0/1).
Phase N (NLA, block 42):   S8b native lp over {m, c, d}; S8b free text (1 sample); S8a native lp over the 29 names.
Outputs cache/g_agreement/s8x/{native.jsonl, freetext.jsonl}; resumable by key.

    python projects/g_agreement/s8/s8_pod.py --phase O|N [--batch 48]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.core import scoring_lo as LO  # noqa: E402
from projects.g_agreement.s8 import s8_common as S  # noqa: E402

OUT = C.CACHE_DIR / "s8x"
NATIVE, FT = OUT / "native.jsonl", OUT / "freetext.jsonl"
T2 = C.CACHE_DIR / "f2" / "t2"
SEED = 20261016
t0 = time.time()


def log(s):
    print(f"[s8x] {s} ({(time.time() - t0) / 60:.1f} min)", flush=True)


def done_keys(p):
    return {json.loads(l)["key"] for l in open(p)} if p.exists() else set()


def append(p, rows):
    with open(p, "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def multi_lp(reader, H, cands_per_state, family, layer, batch):
    """{state_index: {cand: lp}} using score_lo on candidate pairs (states repeated)."""
    import torch
    reps, pairs, owner = [], [], []
    for i, cands in enumerate(cands_per_state):
        cs = list(cands) + ([cands[0]] if len(cands) % 2 else [])
        for j in range(0, len(cs), 2):
            reps.append(H[i]); pairs.append((cs[j], cs[j + 1])); owner.append(i)
    out = [dict() for _ in cands_per_state]
    Hr = torch.stack(reps)
    for s in range(0, len(pairs), 512):
        rows = LO.score_lo(reader, Hr[s:s + 512], pairs[s:s + 512], family, layer=layer, batch=batch)
        for o, (a, b), r in zip(owner[s:s + 512], pairs[s:s + 512], rows):
            out[o][a] = r["lp_A"]; out[o][b] = r["lp_B"]
    return out


def s8b_vectors():
    from projects.g_agreement.y1_site import collect as Y1
    items = S.error_items(C.DATASET_DIR / "items_x3_selected.json")
    caps = {it["item_id"]: Y1.load_cap(it["item_id"]) for it in items}
    V = {(it["item_id"], L): Y1.cell_vector(caps[it["item_id"]], L, "0") for it in items for L in S.S8B_LAYERS}
    return items, V


def s8a_vectors():
    import torch
    reads = torch.load(T2 / "readvecs.pt", map_location="cpu")
    beh = [json.loads(l) for l in open(T2 / "behaviour.jsonl")]
    beh = [b for b in beh if b["arm"] in S.S8A_ARMS]
    return beh, reads, S.name_set(T2 / "behaviour.jsonl")


def run_native_s8b(reader, name, layers, items, V, batch, done):
    import torch
    for L in layers:
        todo = [it for it in items if f"s8b|{name}|{L}|{it['item_id']}" not in done]
        if not todo:
            continue
        H = torch.stack([V[(it["item_id"], L)] for it in todo])
        tw = [S.three_way(it) for it in todo]
        lps = multi_lp(reader, H, [(t["m"], t["c"], t["d"]) for t in tw], "puzzle", L, batch)
        append(NATIVE, [{"key": f"s8b|{name}|{L}|{it['item_id']}", "part": "s8b", "reader": name, "layer": L, "item_id": it["item_id"], **t, "lp": lp}
                        for it, t, lp in zip(todo, tw, lps)])
        log(f"{name} S8b native L{L} ({len(todo)})")


def run_native_s8a(reader, name, layers, batch, done):
    import torch
    beh, reads, names = s8a_vectors()
    for L in layers:
        todo = [b for b in beh if f"s8a|{name}|{L}|{b['key']}" not in done]
        for s in range(0, len(todo), 64):
            ch = todo[s:s + 64]
            H = torch.stack([reads[b["key"]][L].float() for b in ch])
            lps = multi_lp(reader, H, [names] * len(ch), "ownership", L, batch)
            append(NATIVE, [{"key": f"s8a|{name}|{L}|{b['key']}", "part": "s8a", "reader": name, "layer": L, "entry": b["key"], "pair_id": b["pair_id"],
                             "arm": b["arm"], "alpha": b["alpha"], "own": b["cand_A"], "planted": b["cand_B"], "lp": lp} for b, lp in zip(ch, lps)])
            if (s // 64) % 5 == 0:
                log(f"{name} S8a L{L} {s + len(ch)}/{len(todo)}")


def phase_o(batch):
    import torch
    from projects.g_agreement.agam_viewer.collect import gen_batch
    from projects.g_agreement.g1_agreement.collect import load_target_timed
    target = load_target_timed("s8x")
    ol = R.OLensReader().bind(target)
    log(f"Oracle bound; liveness {ol.liveness}")
    done = done_keys(NATIVE)
    items, V = s8b_vectors()
    run_native_s8b(ol, "olens", S.S8B_LAYERS, items, V, batch, done)
    # free text
    dft = done_keys(FT)
    embed = target.model.get_input_embeddings()
    dev = next(target.model.parameters()).device
    for L in S.S8B_FT_LAYERS:
        todo = [it for it in items if f"olens|{L}|{it['item_id']}" not in dft]
        ids0, slot, _c, _cid = ol.carrier(L)
        for s in range(0, len(todo), batch):
            ch = todo[s:s + batch]
            with torch.no_grad():
                e = embed(torch.tensor([ids0] * len(ch), device=dev)).clone()
                for r, it in enumerate(ch):
                    v = V[(it["item_id"], L)].to(dev).float()
                    e[r, slot, :] = (ol.alpha * v / v.norm().clamp_min(1e-9)).to(e.dtype)
            seed = SEED + 1000 * L + s
            outs = gen_batch(target.model, target.tokenizer, embeds=e, n_rows=len(ch), seed=seed)
            append(FT, [{"key": f"olens|{L}|{it['item_id']}", "reader": "olens", "layer": L, "item_id": it["item_id"], **S.three_way(it),
                         "text": o["text"], "finish_reason": o["finish_reason"], "seed": seed} for it, o in zip(ch, outs)])
        log(f"Oracle free text L{L} done")
    (OUT / "s8b_olens_done").write_text(str(time.time()))
    run_native_s8a(ol, "olens", (42, 44), batch, done)
    (OUT / "s8a_olens_done").write_text(str(time.time()))
    log("phase O done")


def phase_n(batch):
    import torch
    from projects.g_agreement.agam_viewer.collect import gen_batch
    nla = R.NLAReader().bind()
    log("NLA bound")
    done = done_keys(NATIVE)
    items, V = s8b_vectors()
    run_native_s8b(nla, "nla", (42,), items, V, batch, done)
    dft = done_keys(FT)
    todo = [it for it in items if f"nla|42|{it['item_id']}" not in dft]
    for s in range(0, len(todo), batch):
        ch = todo[s:s + batch]
        nla._vec["v"] = torch.stack([V[(it["item_id"], 42)].float() for it in ch])
        seed = SEED + 42000 + s
        try:
            outs = gen_batch(nla.model, nla.tokenizer, ids=nla.ids, n_rows=len(ch), seed=seed)
        finally:
            nla._vec["v"] = None
        append(FT, [{"key": f"nla|42|{it['item_id']}", "reader": "nla", "layer": 42, "item_id": it["item_id"], **S.three_way(it),
                     "text": o["text"], "finish_reason": o["finish_reason"], "seed": seed} for it, o in zip(ch, outs)])
    log("NLA free text done")
    (OUT / "s8b_nla_done").write_text(str(time.time()))
    run_native_s8a(nla, "nla", (42,), batch, done)
    (OUT / "s8a_nla_done").write_text(str(time.time()))
    log("phase N done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("O", "N"), required=True)
    ap.add_argument("--batch", type=int, default=48)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"O": phase_o, "N": phase_n}[a.phase](a.batch)
