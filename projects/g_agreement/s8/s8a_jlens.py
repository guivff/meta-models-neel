"""S8a, J-lens part (CPU only, no forward passes): J-lens cosine scores over ALL candidate tokens.

Readout = core/scoring_lo.lo_jlens: z[t] = (h Jᵀ) · W_U[t] / ‖W_U[t] J‖ (n1000 lens, pinned sha256), per candidate the max over its
single-token variants (core/scoring_lo.token_variants). Only candidate rows of W_U are used, so the full-vocabulary product is never formed.

Datasets
  x3_error   X3 ERROR items (297), block-42 last-token states (cache/g_agreement/states/<id>.pt), lens layer 42;
             candidates = the full puzzle vocabulary A–H (8 symbols); key = the model's actual answer, correct = task answer.
  f2_split   F2-2 norm-split read-backs (cache/g_agreement/f2/t2/readvecs.pt: key -> {layer: vec}), lens layers 42/44/56 as cached;
             candidates = the pair's two candidates (cand_A = own answer, cand_B = other). Skipped (and reported) if readvecs.pt is absent.
Self-check: x3_error LO(actual vs correct) must reproduce cache/g_agreement/x/x3_lo.jsonl jlens lo_actual.
Output: one row per (dataset, state, layer, candidate) -> results/g_agreement/s8/s8a_jlens.csv (+ s8a_jlens_meta.json).

    .venv/bin/python projects/g_agreement/s8/s8a_jlens.py --data-root /path/to/mats-minis [--readvecs PATH]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np

HERE_ROOT = Path(__file__).resolve().parents[3]
LENS_SHA256 = "1718c8c52dd8a9dad03738d4d625937c1fbba10be325b872ed446c7290fc11e1"
PUZZLE_VOCAB = tuple("ABCDEFGH")


def token_variants(tok, word):
    forms = []
    for w in (word, word.capitalize(), word.lower(), word.upper() if len(word) == 1 else word):
        for f in (w, " " + w):
            if f not in forms:
                forms.append(f)
    out = {}
    for f in forms:
        ids = tok.encode(f, add_special_tokens=False)
        if len(ids) == 1 and ids[0] not in out.values():
            out[f] = int(ids[0])
    return out


def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


class Lens:
    def __init__(self, lens_path, unembed_path, tok, layers):
        import torch
        obj = torch.load(lens_path, map_location="cpu", weights_only=False, mmap=True)
        self.J = {L: obj["J"][L].float() for L in layers}
        self.W = torch.load(unembed_path, map_location="cpu", weights_only=False)["lm_head.weight"]
        self.tok = tok
        self.var, self.rows, self.den = {}, {}, {}

    def variants(self, word):
        if word not in self.var:
            self.var[word] = token_variants(self.tok, word)
        return self.var[word]

    def scores(self, h, layer, words):
        """{word: (max cosine over variants, best variant, n_variants)}; None score if no single-token variant."""
        import torch
        J = self.J[layer]
        v = h.float() @ J.T
        out = {}
        for w in words:
            va = self.variants(w)
            if not va:
                out[w] = (None, None, 0)
                continue
            best = None
            for txt, t in va.items():
                if (layer, t) not in self.den:
                    u = self.W[t].float()
                    self.rows[t] = u
                    self.den[(layer, t)] = float(torch.clamp_min((u @ J).norm(), 1e-9))
                s = float(v @ self.rows[t]) / self.den[(layer, t)]
                if best is None or s > best[0]:
                    best = (s, txt)
            out[w] = (best[0], best[1], len(va))
        return out


def main(argv=None):
    import torch
    from transformers import AutoTokenizer

    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, default=HERE_ROOT)
    ap.add_argument("--readvecs", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=HERE_ROOT / "results" / "g_agreement" / "s8")
    a = ap.parse_args(argv)
    D = a.data_root
    t0 = time.time()
    lens_path = D / "cache/g_agreement/s3/jlens/Qwen3.6-27B_jacobian_lens_n1000.pt"
    assert sha256(lens_path) == LENS_SHA256, "J-lens file sha256 mismatch"
    tok = AutoTokenizer.from_pretrained(str(D / "cache/g_agreement/s3/tok"))
    readvecs = a.readvecs or D / "cache/g_agreement/f2/t2/readvecs.pt"
    rv = torch.load(readvecs, map_location="cpu") if readvecs.exists() else None
    layers = {42} | ({int(L) for d in rv.values() for L in d} if rv else set())
    lens = Lens(lens_path, D / "cache/g_agreement/s3/qwen36_unembed.pt", tok, sorted(layers))
    rows, meta = [], {"lens_sha256": LENS_SHA256, "readvecs": str(readvecs), "readvecs_found": rv is not None}

    # ---- X3 ERROR
    sel = {it["item_id"]: it for it in json.load(open(D / "projects/g_agreement/dataset/items_x3_selected.json"))["items"]}
    ref = {}
    for l in open(D / "cache/g_agreement/x/x3_lo.jsonl"):
        r = json.loads(l)
        if r["reader"] == "jlens" and r["set"] == "error" and not r.get("unscorable"):
            ref[r["item_id"]] = r["lo_actual"]
    ids = sorted(i for i, it in sel.items() if it["set"] == "error")
    diffs, missing = [], []
    for i in ids:
        p = D / f"cache/g_agreement/states/{i}.pt"
        if not p.exists():
            missing.append(i)
            continue
        h = torch.load(p, map_location="cpu")
        it = sel[i]
        actual, correct = it["primary"]["answer"], it["source"]["correct"]
        sc = lens.scores(h, 42, PUZZLE_VOCAB)
        vals = {w: s[0] for w, s in sc.items()}
        order = sorted(vals, key=lambda w: -vals[w])
        for w in PUZZLE_VOCAB:
            rows.append({"dataset": "x3_error", "state": i, "pair_id": i, "arm": "natural", "alpha": 0.0, "layer": 42, "candidate": w,
                         "role": "actual" if w == actual else ("correct" if w == correct else "distractor"),
                         "cosine": vals[w], "best_variant": sc[w][1], "n_variants": sc[w][2], "rank": order.index(w) + 1})
        if i in ref:
            diffs.append(abs((vals[actual] - vals[correct]) - ref[i]))
    meta["x3_error"] = {"n_items": len(ids), "n_missing_states": len(missing), "candidates": list(PUZZLE_VOCAB),
                        "selfcheck_vs_x3_lo": {"n": len(diffs), "max_abs_diff": float(max(diffs)) if diffs else None,
                                               "median_abs_diff": float(np.median(diffs)) if diffs else None}}

    # ---- F2-2 split read-backs
    if rv is not None:
        beh = {}
        for l in open(readvecs.parent / "behaviour.jsonl"):
            r = json.loads(l)
            beh[r["key"]] = r
        n = 0
        for key, d in rv.items():
            b = beh.get(key)
            if b is None:
                continue
            for L, vec in d.items():
                L = int(L)
                sc = lens.scores(vec, L, (b["cand_A"], b["cand_B"]))
                for w, role in ((b["cand_A"], "own"), (b["cand_B"], "other")):
                    rows.append({"dataset": "f2_split", "state": key, "pair_id": b["pair_id"], "arm": b["arm"], "alpha": b["alpha"], "layer": L,
                                 "candidate": w, "role": role, "cosine": sc[w][0], "best_variant": sc[w][1], "n_variants": sc[w][2], "rank": None})
            n += 1
        meta["f2_split"] = {"n_states": n, "layers": sorted(layers)}
    else:
        meta["f2_split"] = {"status": "readvecs.pt not available locally (lives on the pod volume, cache/g_agreement/f2/t2/); rerun with --readvecs"}

    a.out.mkdir(parents=True, exist_ok=True)
    cols = ["dataset", "state", "pair_id", "arm", "alpha", "layer", "candidate", "role", "cosine", "best_variant", "n_variants", "rank"]
    with open(a.out / "s8a_jlens.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    meta["wall_s"] = time.time() - t0
    (a.out / "s8a_jlens_meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
