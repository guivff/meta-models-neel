"""BRIEF_R §15 pod side (WS3; run on a pod that holds the pinned J-lens file and Qwen3.6-27B in its HF cache). It loads the
pinned lens and ONLY the unembedding tensor (lm_head.weight, from its safetensors shard; the 27B model is never
built), reads the states the collector already wrote, and writes two small outputs for WS3's CPU analysis:

  <out>/jterms_topk.jsonl   per (dataset, item_id, layer, position, control, seed): the J-lens top-10 token ids (the
                            JLensReader cosine readout, (h J_Lᵀ W_Uᵀ) / ‖W_U J_L‖_rows). Controls: "jlens" (true lens),
                            "rot" (J_L R, R Haar-random orthogonal, seeds 0–4, one R per seed for all layers; R preserves
                            the row norms, so the denominator is the true lens's), "state_free" (the dataset's mean test
                            state through the true lens; one row per (dataset, layer, position), item_id "__mean__").
  <out>/jterms_wu_rows.npz  candidate-contrast inputs: for every pool and test item of the per-item-candidate facts, the
                            first-token ids of c0 and c1 (leading-space form, as the J-lens candidate variants) and
                            W_U rows for the unique ids (fp16).

    python -m projects.g_agreement.r_bench.jlens_terms_pod --states /workspace/mats-minis/cache/g_agreement/r/states \
        --out /workspace/mats-minis/cache/g_agreement/r/jlens_terms --device cuda

Read-only on everything except --out; torch / transformers / safetensors on the pod only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from projects.g_agreement.core import config as C

LAYERS = (24, 28, 32, 36, 38, 40, 42, 44, 48, 52, 56, 60)
TOPK = 10
N_ROT = 5
WORKSPACE_TOPK = ["re_khop2_bridge", "re_khop2_answer", "re_khop3_middle",
                  "x22_wsb_association", "x23_wsb_basic_readout", "x24_wsb_multihop", "x25_wsb_wrong_bridge",
                  "x26_wsb_multilingual", "x27_wsb_poetry", "x28_wsb_typo", "x29_wsb_directed_modulation"]  # + rb_khop_* from the bank
BANKS = ("items_re.json", "items_rx.json", "items_rb.json")


def _items(dataset_dir: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for f in BANKS:
        p = dataset_dir / f
        if p.exists():
            for it in json.loads(p.read_text())["items"]:
                out.setdefault(it["dataset"], []).append(it)
    return out


def _unembed():
    """lm_head.weight only, from the pinned snapshot's safetensors shard."""
    from huggingface_hub import hf_hub_download
    from safetensors import safe_open

    idx = json.loads(Path(hf_hub_download(C.TARGET_MODEL_ID, "model.safetensors.index.json", revision=C.TARGET_MODEL_SHA)).read_text())
    key = next(k for k in idx["weight_map"] if k.endswith("lm_head.weight"))
    shard = hf_hub_download(C.TARGET_MODEL_ID, idx["weight_map"][key], revision=C.TARGET_MODEL_SHA)
    with safe_open(shard, framework="pt") as f:
        return f.get_tensor(key)


def main(argv: list[str] | None = None) -> int:
    import hashlib

    import torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--states", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dataset-dir", type=Path, default=C.DATASET_DIR)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    dev = a.device
    lens = hf_hub_download(C.JLENS_REPO, C.JLENS_FILE, revision=C.JLENS_SHA)
    sha = hashlib.sha256(Path(lens).read_bytes()).hexdigest()
    assert sha == C.JLENS_FILE_SHA256, f"J-lens file sha {sha} != pinned {C.JLENS_FILE_SHA256}"
    obj = torch.load(lens, map_location="cpu", weights_only=False)
    jac = obj["J"] if "J" in obj else obj["jacobians"]
    getJ = (lambda L: jac[L] if L in jac else jac[str(L)]) if isinstance(jac, dict) else (lambda L: jac[L])  # noqa: E731
    W = _unembed().to(dev).float()  # [V, d]
    tok = AutoTokenizer.from_pretrained(C.TARGET_MODEL_ID, revision=C.TARGET_MODEL_SHA)
    items = _items(a.dataset_dir)
    dss = WORKSPACE_TOPK + sorted(d for d in items if d.startswith("rb_khop_"))
    d = W.shape[1]
    gens = [torch.Generator().manual_seed(s) for s in range(N_ROT)]
    rots = []
    for g in gens:  # Haar-random orthogonal via QR with sign correction
        q, r = torch.linalg.qr(torch.randn(d, d, generator=g))
        rots.append((q * torch.sign(torch.diagonal(r))).to(dev))
    n_rows = 0
    with open(a.out / "jterms_topk.jsonl", "w") as fo:
        for L in LAYERS:
            J = getJ(L).float().to(dev)
            denom = (W @ J).norm(dim=1).clamp_min(1e-9)
            WJ = (W @ J).T / denom  # [d, V]: score(h) = h @ WJ   (= (h Jᵀ W_Uᵀ) / ‖W_U J‖ written as h (W_U J)ᵀ / ‖·‖)
            for ds in dss:
                sd = a.states / ds
                if not (sd / "index.json").exists():
                    continue
                idx = json.loads((sd / "index.json").read_text())["item_ids"]
                split = {it["item_id"]: it["split"] for it in items.get(ds, [])}
                test = [i for i, iid in enumerate(idx) if split.get(iid) == "test"]
                for pos, fname in (("last", f"chat_L{L}.npy"), ("rp", f"chat_L{L}_rp.npy")):
                    f = sd / fname
                    if not f.exists():
                        continue
                    H = torch.from_numpy(np.load(f)[test].astype(np.float32)).to(dev)
                    ok = torch.isfinite(H).all(1)
                    ids_test = [idx[i] for i in test]

                    def emit(scores, control, seed, item_ids):
                        nonlocal n_rows
                        top = torch.topk(scores, TOPK, dim=1).indices.cpu().tolist()
                        for iid, t in zip(item_ids, top):
                            fo.write(json.dumps({"dataset": ds, "item_id": iid, "layer": L, "position": pos, "control": control,
                                                 "seed": seed, "topk_ids": t}) + "\n")
                            n_rows += 1

                    Hk, kept = H[ok], [iid for iid, o in zip(ids_test, ok.tolist()) if o]
                    emit(Hk @ WJ, "jlens", None, kept)
                    for s, R in enumerate(rots):  # J_L R: score = (h Rᵀ) (W_U J)ᵀ / ‖W_U J‖
                        emit((Hk @ R.T) @ WJ, "rot", s, kept)
                    emit(Hk.mean(0, keepdim=True) @ WJ, "state_free", None, ["__mean__"])
            del J, WJ, denom
            torch.cuda.empty_cache() if dev.startswith("cuda") else None
            print(f"[jterms] layer {L}: {n_rows} rows so far", flush=True)
    # candidate-contrast inputs (per-item-candidate facts, pool + test)
    rec, uniq = [], set()
    for ds, its in items.items():
        if not (ds.startswith(("re_khop", "rb_khop_")) or ds in WORKSPACE_TOPK):
            continue
        for it in its:
            c0, c1 = it["primary"]["candidates"][:2]
            t0, t1 = (tok(" " + c, add_special_tokens=False)["input_ids"][0] for c in (c0, c1))
            rec.append((ds, it["item_id"], int(t0), int(t1)))
            uniq |= {int(t0), int(t1)}
    ids = np.array(sorted(uniq))
    np.savez(a.out / "jterms_wu_rows.npz", token_ids=ids, rows=W[torch.as_tensor(ids, device=dev)].half().cpu().numpy(),
             items=np.array([r[1] for r in rec]), datasets=np.array([r[0] for r in rec]),
             c0_ids=np.array([r[2] for r in rec]), c1_ids=np.array([r[3] for r in rec]))
    (a.out / "jterms_meta.json").write_text(json.dumps({"jlens_file": C.JLENS_FILE, "jlens_sha256": sha, "model": C.TARGET_MODEL_ID,
                                                        "model_sha": C.TARGET_MODEL_SHA, "layers": LAYERS, "topk": TOPK, "n_rot": N_ROT,
                                                        "datasets": dss, "n_topk_rows": n_rows, "n_wu_rows": int(len(ids))}, indent=1))
    print(f"[jterms] wrote {n_rows} top-k rows, {len(ids)} W_U rows → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
