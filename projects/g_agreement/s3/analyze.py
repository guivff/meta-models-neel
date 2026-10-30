"""S3: J-space vs the W_U output subspace (BRIEF_S.md "S3"; rule fixed before any number). CPU only, no forward passes.

    PYTHONPATH=<repo> .venv/bin/python -m projects.g_agreement.s3.analyze [--layers 38,42,56] [--out results/g_agreement/s3]

Inputs (cache/g_agreement/s3): qwen36_unembed.pt (lm_head [V,d], final norm weight; range-fetched from Qwen/Qwen3.6-27B @ pinned sha),
jlens/.../Qwen3.6-27B_jacobian_lens_n1000.pt (neuronpedia J-lens), tok/ (tokenizer files); cache/g_agreement/x/full (X2 states, blocks 38/42),
cache/g_agreement/w/directions/ownership/shared.pt (class-mean + probe at block 38), cache/g_agreement/y/jspace_L38_r384.pt (Y2 basis).

Definitions. J-space(l, r) = span of the top-r right singular vectors of M = W_U J_l (Y2 recipe, no gain; "J0"); "J1" folds the final norm gain
g into M (02 recipe). W_U span(k) = top-k right singular vectors of W_U diag(g) ("U1"; "U0" without g). Overlap = ||Q_J^T Q_U||_F^2 / r (mean squared
cosine of principal angles). Primary pairing (decision rule): J0 x U1, r = k = 384, block 38. Random baseline: 100 seeded random r-dim subspaces.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]
CACHE = Path("/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement")  # main checkout holds the cache
S3 = CACHE / "s3"
D = 5120
NRAND = 100
SEED = 20261015


def gram_unembed(W: torch.Tensor, chunk: int = 16384) -> torch.Tensor:
    A = torch.zeros(D, D, dtype=torch.float32)
    for s in range(0, W.shape[0], chunk):
        w = W[s:s + chunk].float()
        A += w.T @ w
    return A


def top_eig(G: torch.Tensor, k: int) -> tuple[torch.Tensor, torch.Tensor]:
    ev, V = torch.linalg.eigh(G.double())
    return V.flip(1)[:, :k].float().contiguous(), ev.flip(0)[:k].float()


def overlap(QJ: torch.Tensor, QU: torch.Tensor) -> float:
    return float((QJ.T @ QU).pow(2).sum() / QJ.shape[1])


def rand_basis(r: int, seed: int) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    q, _ = torch.linalg.qr(torch.randn(D, r, generator=g, dtype=torch.float64))
    return q.float()


def frac_in(x: torch.Tensor, Q: torch.Tensor) -> float:
    """sum of squared norm of rows of x inside span(Q) / total squared norm."""
    return float((x @ Q).pow(2).sum() / x.pow(2).sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", default="38,42,56")
    ap.add_argument("--out", default=str(ROOT / "results/g_agreement/s3"))
    a = ap.parse_args()
    layers = [int(x) for x in a.layers.split(",")]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    def add(section, layer, **kw):
        rows.append({"section": section, "layer": layer, **kw})

    obj = torch.load(S3 / "qwen36_unembed.pt", map_location="cpu")
    W = obj["lm_head.weight"]
    w_norm = obj["model.language_model.norm.weight"].float()
    print("norm weight stats: mean %.4f std %.4f min %.4f max %.4f" % (w_norm.mean(), w_norm.std(), w_norm.min(), w_norm.max()), flush=True)
    # Qwen3.5/3.6 RMSNorm is zero-centred ((1 + weight)); decided from the stats above, recorded in s3.md
    g = (1.0 + w_norm) if abs(float(w_norm.mean())) < 0.5 * 1.0 and float(w_norm.mean()) < 3 else w_norm
    gain_rule = "1+w" if g is not w_norm else "w"
    print("gain rule:", gain_rule, "g mean %.3f" % g.mean(), flush=True)
    A = gram_unembed(W)
    A1 = g[:, None] * A * g[None, :]
    U0, _ = top_eig(A, 1536)
    U1, _ = top_eig(A1, 1536)
    del W

    jl = torch.load(next((S3 / "jlens").rglob("*.pt")), map_location="cpu", mmap=True, weights_only=False)
    jac = jl["J"] if "J" in jl else jl["jacobians"]
    getJ = (lambda L: (jac[L] if L in jac else jac[str(L)])) if isinstance(jac, dict) else (lambda L: jac[L])
    Q38 = torch.load(CACHE / "y/jspace_L38_r384.pt", map_location="cpu")["Q"].float()

    J: dict[int, dict[str, torch.Tensor]] = {}  # layer -> variant -> Q [d, 1536]
    for L in layers:
        Jm = getJ(L).float()
        J[L] = {}
        for var, Ag in (("J0", A), ("J1", A1)):
            G = Jm.T @ (Ag @ Jm)
            J[L][var], _ = top_eig((G + G.T) / 2, 1536)
        print(f"J-space built at {L}", flush=True)
    add("check", 38, metric="overlap(cached Y2 Q384, rebuilt J0 top-384)", value=overlap(Q38, J[38]["J0"][:, :384]) if 38 in J else None)

    # (a) overlap vs random
    rand_cache: dict[tuple[int, int], np.ndarray] = {}
    for L in layers:
        for r in (384, 1536):
            for ju in ("J0", "J1"):
                for un, U in (("U0", U0), ("U1", U1)):
                    ov = overlap(J[L][ju][:, :r], U[:, :r])
                    if (r, int(un[1])) not in rand_cache:
                        rand_cache[(r, int(un[1]))] = np.array([overlap(rand_basis(r, SEED + i), U[:, :r]) for i in range(NRAND)])
                    rd = rand_cache[(r, int(un[1]))]
                    add("a_overlap", L, jspace=ju, wu=un, r=r, k=r, metric="mean_sq_cos", value=ov, rand_mean=float(rd.mean()),
                        rand_p99=float(np.percentile(rd, 99)), rand_max=float(rd.max()), ratio_to_p99=ov / float(np.percentile(rd, 99)),
                        chance=r / D)
        ov = overlap(J[L]["J0"][:, :384], U1[:, :1536])
        add("a_overlap", L, jspace="J0", wu="U1", r=384, k=1536, metric="mean_sq_cos", value=ov, chance=1536 / D)
    json.dump({"gain_rule": gain_rule}, open(out / "meta.json", "w"))

    # (b)/(c) need cached states
    import projects.g_agreement.core.config as C  # noqa: F401
    from projects.g_agreement.w_directions import build as B
    from projects.g_agreement.w_directions import directions as WD
    from transformers import AutoTokenizer

    from projects.g_agreement.core import edit as E
    from projects.g_agreement.x2_causal import collect as X

    tok = AutoTokenizer.from_pretrained(str(S3 / "tok"))
    items = json.loads(Path(B.ITEMS_X).read_text())["items"]
    pairs_sel = X.x2_pairs(items, families=("ownership",))
    pair_ids = [p["pair_id"] for p in pairs_sel]
    stat: dict[tuple[int, str], dict] = {}
    for L in [l for l in layers if l in (38, 42)]:
        H = {}
        for p in pairs_sel:
            for v in ("A", "B"):
                o = torch.load(B.X_FULL_DIR / f"{p['pair_id']}{v}.pt", map_location="cpu", weights_only=False)
                H[(p["pair_id"], v)] = (o["layers"][L].float(), o["ids"])
        QJ = J[L]["J0"][:, :384]
        QJ15 = J[L]["J0"][:, :1536]
        # per state Delta (source A: B-A toward the other candidate; source B: A-B)
        states = []
        for p in pairs_sel:
            hA, hB = H[(p["pair_id"], "A")][0], H[(p["pair_id"], "B")][0]
            for src, sgn in (("A", 1.0), ("B", -1.0)):
                it = p[src]
                states.append({"pair": p["pair_id"], "src": src, "D": sgn * (hB - hA), "cand_from": str(it["primary"]["answer"]),
                               "cand_to": X.other_candidate(it)})
        for part in ("full", "J", "perp"):
            xs = []
            for s in states:
                DJ = (s["D"] @ QJ) @ QJ.T
                xs.append({"full": s["D"], "J": DJ, "perp": s["D"] - DJ}[part])
            allx = torch.cat(xs)
            for k, U in ((384, U1[:, :384]), (1536, U1[:, :1536]), (384, U0[:, :384]), (1536, U0[:, :1536])):
                un = "U1" if torch.equal(U, U1[:, :k]) else "U0"
                fr = frac_in(allx, U)
                per_state = [frac_in(x, U) for x in xs]
                add("b_frac", L, piece=part, wu=un, k=k, metric="frac_sq_norm_in_wu_span", value=fr, per_state_mean=float(np.mean(per_state)),
                    chance=k / D)
            # sensitivity: J-space r=1536 pieces
        # per-state paired comparison J vs perp at U1 384
        fJ, fP = [], []
        for s in states:
            DJ = (s["D"] @ QJ) @ QJ.T
            fJ.append(frac_in(DJ, U1[:, :384])); fP.append(frac_in(s["D"] - DJ, U1[:, :384]))
        fJ, fP = np.array(fJ), np.array(fP)
        add("b_paired", L, metric="n_states_J_gt_perp(U1,384)", value=int((fJ > fP).sum()), n=len(fJ), mean_J=float(fJ.mean()), mean_perp=float(fP.mean()))
        # random 384-d pieces: fraction of Delta projected on a random 384-d subspace that lies in U1 384
        allD = torch.cat([s["D"] for s in states])
        rr = []
        for i in range(NRAND):
            R = rand_basis(384, SEED + 1000 + i)
            P = (allD @ R) @ R.T
            rr.append(frac_in(P, U1[:, :384]))
        add("b_frac_random_piece", L, wu="U1", k=384, metric="frac_in_wu_span_of_random384_piece_of_Delta", value=float(np.mean(rr)), rand_p99=float(np.percentile(rr, 99)))
        # logit lens of each piece (summed over positions), top-20 and answer-name hits
        Wfull = torch.load(S3 / "qwen36_unembed.pt", map_location="cpu")["lm_head.weight"]
        hits = {p_: {"to": 0, "from": 0, "any": 0, "n": 0} for p_ in ("full", "J", "perp")}
        dl = {p_: [] for p_ in hits}
        examples: dict[str, list[str]] = {}
        for s in states:
            ft = E.first_token_candidates(tok, s["cand_from"], s["cand_to"])
            if ft["unscorable"]:
                continue
            tid_from, tid_to = ft["first_A"], ft["first_B"]
            v_full = s["D"].sum(0)
            DJ = (v_full @ QJ) @ QJ.T
            for part, v in (("full", v_full), ("J", DJ), ("perp", v_full - DJ)):
                lg = (Wfull.float() @ (g * v))
                top = torch.topk(lg, 20).indices.tolist()
                hits[part]["n"] += 1
                hits[part]["to"] += int(tid_to in top)
                hits[part]["from"] += int(tid_from in top)
                hits[part]["any"] += int(tid_to in top or tid_from in top)
                dl[part].append(float((lg[tid_to] - lg[tid_from]) / (g * v).norm()))
                if len(examples.setdefault(part, [])) < 3:
                    examples[part].append(f"{s['pair']}|{s['src']}: " + " ".join(repr(tok.decode([t])) for t in top))
        for part in hits:
            add("b_logitlens", L, piece=part, n_states=hits[part]["n"], hit_toward_top20=hits[part]["to"], hit_from_top20=hits[part]["from"],
                hit_any_top20=hits[part]["any"], metric="mean_(logit_to-logit_from)/||g*v||", value=float(np.mean(dl[part])),
                sem=float(np.std(dl[part], ddof=1) / np.sqrt(len(dl[part]))), examples=" || ".join(examples[part]))
        del Wfull

        # (c) directions in the J-space
        if L == 38:
            sh = torch.load(CACHE / "w/directions/ownership/shared.pt", map_location="cpu", weights_only=False)
            dcm = sh["d_cm"].float()
            probes = [f["w_raw"].float().reshape(-1) for f in sh["probe"]["folds"]]
            src = "cached W Track B"
        else:
            sp = json.loads(Path(B.SPANS_JSON).read_text())["pairs"]
            P_in = []
            for p in pairs_sel:
                q = sp[p["pair_id"]]
                pos = sorted(set(q["arms"]["question_only"]) | set(q["arms"]["template_only"]))
                P_in.append({"pair_id": p["pair_id"], "hA": H[(p["pair_id"], "A")][0], "hB": H[(p["pair_id"], "B")][0], "positions": pos,
                             "yA": int(not p["A"]["construction"]["answer_is_first_mentioned"]),
                             "yB": int(not p["B"]["construction"]["answer_is_first_mentioned"])})
            shared, _ = WD.build_ownership(P_in, QJ)
            dcm = shared["d_cm"].float()
            probes = [f["w_raw"].float().reshape(-1) for f in shared["probe"]["folds"]]
            src = "recomputed at this block with the W Track B recipe"
        for name, vecs in (("class_mean", [dcm]), ("probe", probes)):
            for r, Qr in ((384, J[L]["J0"][:, :384]), (1536, J[L]["J0"][:, :1536])):
                fr = np.array([float((v @ Qr).pow(2).sum() / v.pow(2).sum()) for v in vecs])
                rd = np.array([float((vecs[0] @ rand_basis(r, SEED + 5000 + i)).pow(2).sum() / vecs[0].pow(2).sum()) for i in range(NRAND)])
                add("c_direction", L, direction=name, r=r, metric="frac_sq_norm_in_jspace", value=float(fr.mean()), n_vecs=len(fr), min=float(fr.min()),
                    max=float(fr.max()), rand_mean=float(rd.mean()), rand_p99=float(np.percentile(rd, 99)), chance=r / D, source=src)
            for k, Uk in ((384, U1[:, :384]), (1536, U1[:, :1536])):
                fr = np.array([float((v @ Uk).pow(2).sum() / v.pow(2).sum()) for v in vecs])
                add("c_direction_wu", L, direction=name, k=k, metric="frac_sq_norm_in_wu_span_U1", value=float(fr.mean()), chance=k / D)
    for L in layers:
        if L not in (38, 42):
            add("b_c_not_computable", L, note="no cached block-%d states for the X2 pairs (x/full holds blocks 38, 42); needs a forward pass on the pod" % L)

    import csv
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in ("section", "layer"), k))
    with open(out / "s3.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print("wrote", out / "s3.csv", len(rows), "rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
