"""F2-3: probe vs readers at every prompt position and blocks 36-60 step 4 (BRIEF_Z.md "Agam follow-ups 2"). GPU, pod.

    python -m projects.g_agreement.f2.t3_posmap [--budget-min 75]

X1 test bank (ownership, mapping, language, tense). Positions aligned by offset from the last token, k = 0..K_f-1 with K_f the
family's shortest render. Probe: X1 E2 recipe (difference of means, leave-one-pair-out) per cell, computed here on CPU.
Readers: J-lens and Oracle native LO per cell (Oracle cells processed from k = 0 backwards; stops at the budget).
Outputs cache/g_agreement/f2/t3/{probe.jsonl, lo.jsonl, tokens.json, done.json}.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, now_iso
from projects.g_agreement.x1_bank import analyze as XA
from projects.g_agreement.x1_bank import collect as X1

OUT = C.CACHE_DIR / "f2" / "t3"
LAYERS = list(range(36, 61, 4))
FAMS = ("ownership", "mapping", "language", "tense")


def main() -> int:
    import torch

    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-min", type=float, default=75.0)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    T0 = float(os.environ.get("F2_T0", "0") or 0)
    pod_min = lambda: (time.time() - T0) / 60 if T0 else (time.time() - t0) / 60  # noqa: E731
    log = lambda s: print(f"[f2t3] {s} (wall {(time.time() - t0) / 60:.1f} min, pod {pod_min():.1f})", flush=True)  # noqa: E731
    target = load_target_timed("f2t3")
    tok = target.tokenizer
    pairs = X1.load_pairs(split="test", families=FAMS)
    by_fam = {f: [p for p in pairs if p["family"] == f] for f in FAMS}
    caps, toks, K = {}, {}, {}
    for f, ps in by_fam.items():
        lens = []
        for p in ps:
            for v in "AB":
                it = p[v]
                ids = M.render_item(tok, it["prompt_text"], it.get("system"))
                cap = M.capture(target.model, ids, LAYERS, list(range(len(ids))))
                caps[it["item_id"]] = torch.stack([cap[L] for L in LAYERS]).to(torch.float16)  # [7, T, d]
                toks[it["item_id"]] = [tok.decode([t]) for t in ids]
                lens.append(len(ids))
        K[f] = min(lens)
    (OUT / "tokens.json").write_text(json.dumps({"K": K, "tokens": toks, "layers": LAYERS}, ensure_ascii=False))
    log(f"captured {len(caps)} states; K = {K}")

    def H_at(f, li, k):
        return {p[v]["item_id"]: caps[p[v]["item_id"]][li, -1 - k].float().numpy().astype(np.float64) for p in by_fam[f] for v in "AB"}

    # probe (CPU)
    pp = OUT / "probe.jsonl"
    for f in FAMS:
        for li, L in enumerate(LAYERS):
            for k in range(K[f]):
                H = H_at(f, li, k)
                loo = {}
                for p in by_fam[f]:
                    r = XA.score_pair(p, [q for q in by_fam[f] if q["pair_id"] != p["pair_id"]], H)
                    if r is not None:
                        loo[p["pair_id"]] = r
                append_jsonl(pp, {"family": f, "layer": L, "k": k, "wins": {pid: bool(s[0] > s[1]) for pid, s in loo.items()}})
        log(f"probe {f} done")
    # readers
    lop = OUT / "lo.jsonl"
    cands = {p[v]["item_id"]: (str(p[v]["primary"]["answer"]), X1.other_candidate(p[v])) for p in pairs for v in "AB"}
    jl = R.JLensReader().bind(target, layers_keep=LAYERS)
    for f in FAMS:
        iids = [p[v]["item_id"] for p in by_fam[f] for v in "AB"]
        for li, L in enumerate(LAYERS):
            for k in range(K[f]):
                Hm = torch.stack([caps[i][li, -1 - k].float() for i in iids])
                res = LO.score_lo(jl, Hm, [cands[i] for i in iids], f, layer=L)
                append_jsonl(lop, {"reader": "jlens", "family": f, "layer": L, "k": k, "lo": {i: r.get("lo") for i, r in zip(iids, res)}})
    del jl
    torch.cuda.empty_cache()
    log("J-lens done")
    ol = R.OLensReader().bind(target)
    kmax = max(K.values())
    stopped_at = None
    for k in range(kmax):
        if pod_min() > a.budget_min:
            stopped_at = k
            log(f"budget reached: Oracle stopped before offset k = {k}")
            break
        for f in FAMS:
            if k >= K[f]:
                continue
            iids = [p[v]["item_id"] for p in by_fam[f] for v in "AB"]
            for li, L in enumerate(LAYERS):
                Hm = torch.stack([caps[i][li, -1 - k].float() for i in iids])
                res = LO.score_lo(ol, Hm, [cands[i] for i in iids], f, layer=L, batch=64)
                append_jsonl(lop, {"reader": "olens", "family": f, "layer": L, "k": k, "lo": {i: r.get("lo") for i, r in zip(iids, res)}})
        if k % 4 == 3:
            log(f"Oracle offsets 0..{k} done")
    (OUT / "done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60, "pod_min": pod_min(), "K": K,
                                               "oracle_stopped_at_k": stopped_at}, indent=1))
    log("done")
    M.unload(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
