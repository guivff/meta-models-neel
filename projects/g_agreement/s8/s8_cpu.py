"""S8 CPU part: J-lens and probe (no forward passes).

S8b  J-lens max cosine over single-token variants of {m, c, d} at blocks 42/48/52/56 (Y1 captures, last token) and its
     top-10 tokens over the full vocabulary at 42/56 (the J-lens "free text"); probe = 5-fold L2 multinomial logistic over
     A–H on the 400 puzzle states (ERROR + ERROR_CONTROL) at each block, label = model's answer (X6 recipe), class scores.
S8a  J-lens max cosine over the 29 F2-2 names at read blocks 42/44 (arms natural, J_scaled, perp_scaled, rand_scaled_0/1).
Outputs cache/g_agreement/s8x/cpu.jsonl.

    .venv/bin/python projects/g_agreement/s8/s8_cpu.py --data-root /path/to/mats-minis
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
from projects.g_agreement.s8 import s8_common as S  # noqa: E402
from projects.g_agreement.s8.s8a_jlens import Lens, LENS_SHA256, sha256  # noqa: E402

N_FOLDS, PROBE_C = 5, 1.0


def folds(n, k, seed=0):
    idx = np.random.default_rng(seed).permutation(n)
    return [idx[i::k] for i in range(k)]


def probe_scores(X, labels):
    """5-fold held-out class scores (dict class -> score) per row."""
    from sklearn.linear_model import LogisticRegression
    n = len(labels)
    out = [None] * n
    for te in folds(n, N_FOLDS):
        tr = np.setdiff1d(np.arange(n), te)
        mu = X[tr].mean(0); sc = float(X[tr].std()) or 1.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            clf = LogisticRegression(C=PROBE_C, max_iter=5000).fit((X[tr] - mu) / sc, [labels[i] for i in tr])
        Z = clf.decision_function((X[te] - mu) / sc)
        for i, z in zip(te, Z):
            out[i] = {c: float(v) for c, v in zip(clf.classes_, z)}
    return out


def main():
    import torch
    from transformers import AutoTokenizer
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, default=HERE)
    a = ap.parse_args()
    D = a.data_root
    t0 = time.time()
    out = D / "cache/g_agreement/s8x"
    out.mkdir(parents=True, exist_ok=True)
    lens_path = D / "cache/g_agreement/s3/jlens/Qwen3.6-27B_jacobian_lens_n1000.pt"
    assert sha256(lens_path) == LENS_SHA256
    tok = AutoTokenizer.from_pretrained(str(D / "cache/g_agreement/s3/tok"))
    lens = Lens(lens_path, D / "cache/g_agreement/s3/qwen36_unembed.pt", tok, sorted(set(S.S8B_LAYERS) | {44}))
    sel = json.loads((D / "projects/g_agreement/dataset/items_x3_selected.json").read_text())["items"]
    puzz = sorted((it for it in sel if it["set"] in ("error", "error_control")), key=lambda it: it["item_id"])
    caps = {it["item_id"]: torch.load(D / f"cache/g_agreement/y/y1_caps/{it['item_id']}.pt", map_location="cpu", weights_only=False) for it in puzz}

    def vec(i, L):
        c = caps[i]
        return c["acts"][c["layers"].index(L), c["labels"].index("0")].float()

    errs = [it for it in puzz if it["set"] == "error"]
    rows = []
    for L in S.S8B_LAYERS:
        # J-lens three-way
        for it in errs:
            tw = S.three_way(it)
            sc = lens.scores(vec(it["item_id"], L), L, (tw["m"], tw["c"], tw["d"]))
            rows.append({"part": "s8b", "reader": "jlens", "layer": L, "item_id": it["item_id"], **tw,
                         "score": {r: sc[tw[r]][0] for r in ("m", "c", "d")}})
        # probe
        X = torch.stack([vec(it["item_id"], L) for it in puzz]).numpy().astype(np.float64)
        ps = probe_scores(X, [it["primary"]["answer"] for it in puzz])
        for it, p in zip(puzz, ps):
            if it["set"] != "error":
                continue
            tw = S.three_way(it)
            rows.append({"part": "s8b", "reader": "probe", "layer": L, "item_id": it["item_id"], **tw,
                         "score": {r: p.get(tw[r]) for r in ("m", "c", "d")}})
        print(f"S8b L{L} J-lens + probe ({time.time() - t0:.0f}s)", flush=True)
    # J-lens top-10 tokens at 42/56
    W = lens.W
    for L in S.S8B_FT_LAYERS:
        J = lens.J[L]
        den = torch.cat([(W[s:s + 8192].float() @ J).norm(dim=1) for s in range(0, W.shape[0], 8192)]).clamp_min(1e-9)
        H = torch.stack([vec(it["item_id"], L) for it in errs]) @ J.T
        for s in range(0, len(errs), 64):
            Z = torch.cat([(H[s:s + 64] @ W[c:c + 16384].float().T) for c in range(0, W.shape[0], 16384)], dim=1) / den
            top = torch.topk(Z, 10, dim=1).indices.tolist()
            for it, ids in zip(errs[s:s + 64], top):
                rows.append({"part": "s8b_ft", "reader": "jlens", "layer": L, "item_id": it["item_id"], **S.three_way(it),
                             "tokens": [tok.decode([t]) for t in ids]})
        print(f"J-lens top-10 L{L} ({time.time() - t0:.0f}s)", flush=True)
    # S8a J-lens over the 29 names
    t2 = D / "cache/g_agreement/f2/t2"
    names = S.name_set(t2 / "behaviour.jsonl")
    reads = torch.load(t2 / "readvecs.pt", map_location="cpu")
    beh = [json.loads(l) for l in open(t2 / "behaviour.jsonl")]
    for b in beh:
        if b["arm"] not in S.S8A_ARMS:
            continue
        for L in (42, 44):
            sc = lens.scores(reads[b["key"]][L].float(), L, names)
            rows.append({"part": "s8a", "reader": "jlens", "layer": L, "entry": b["key"], "pair_id": b["pair_id"], "arm": b["arm"], "alpha": b["alpha"],
                         "own": b["cand_A"], "planted": b["cand_B"], "score": {n: sc[n][0] for n in names},
                         "n_unscorable": sum(sc[n][0] is None for n in names)})
    print(f"S8a J-lens done; {len(names)} names ({time.time() - t0:.0f}s)", flush=True)
    with open(out / "cpu.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    (out / "cpu_meta.json").write_text(json.dumps({"names": names, "n_rows": len(rows), "wall_s": time.time() - t0, "lens_sha256": LENS_SHA256}, indent=1))


if __name__ == "__main__":
    main()
