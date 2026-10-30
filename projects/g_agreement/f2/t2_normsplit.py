"""F2-2: norm-matched split edit on the 32 X2 ownership pairs (BRIEF_Z.md "Agam follow-ups 2"). GPU, pod.

    python -m projects.g_agreement.f2.t2_normsplit --phase A     # decodes + read-backs (42, 44), J-lens and Oracle LO
    python -m projects.g_agreement.f2.t2_normsplit --phase B     # NLA LO on the block-42 read-backs

Edit at block 38, all positions: h' = h + alpha * delta. Arms: full (Delta = toward * (h_B - h_A)); J_scaled / perp_scaled = the
top-384 J-space component / its complement rescaled per position to ||Delta(p)||; rand_scaled k=0,1 = seeded random unit direction per
position at ||Delta(p)||; J_only = unscaled J component (Y2 reference). alpha in {0.25, 0.5, 1, 1.5, 2}; plus the natural row.
Outputs cache/g_agreement/f2/t2/{behaviour.jsonl, readvecs.pt, lo.jsonl, phase{A,B}_done.json}.
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring as SC
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, now_iso, read_jsonl
from projects.g_agreement.w_pod import common as W
from projects.g_agreement.x2_causal import collect as X

OUT = C.CACHE_DIR / "f2" / "t2"
ARMS = ("full", "J_scaled", "perp_scaled", "rand_scaled_0", "rand_scaled_1", "J_only")
ALPHAS = (0.25, 0.5, 1.0, 1.5, 2.0)
READ = (42, 44)
EDIT = 38


def deltas(HA, HB, src: str, Q, pair_seed: int) -> dict[str, Any]:
    import torch

    hA, hB = HA[EDIT].float(), HB[EDIT].float()
    D = (1.0 if src == "A" else -1.0) * (hB - hA)
    n = D.norm(dim=1, keepdim=True)
    DJ = (D @ Q) @ Q.T
    Dp = D - DJ

    def rescale(V):
        vn = V.norm(dim=1, keepdim=True)
        return torch.where(vn > 1e-6, V * (n / vn.clamp_min(1e-6)), torch.zeros_like(V))

    out = {"full": D, "J_scaled": rescale(DJ), "perp_scaled": rescale(Dp), "J_only": DJ}
    for k in (0, 1):
        g = torch.Generator().manual_seed(pair_seed * 10 + k + (0 if src == "A" else 5))
        r = torch.randn(D.shape, generator=g)
        out[f"rand_scaled_{k}"] = rescale(r) * (n > 1e-6)
    return out


def phase_a(batch: int) -> None:
    import torch

    from projects.g_agreement.g1_agreement.collect import load_target_timed

    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = lambda s: print(f"[f2t2/A] {s} ({(time.time() - t0) / 60:.1f} min)", flush=True)  # noqa: E731
    target = load_target_timed("f2t2")
    tok = target.tokenizer
    Q = torch.load(C.CACHE_DIR / "y" / "jspace_L38_r384.pt", map_location="cpu")["Q"].float()
    pairs = X.x2_pairs(C.load_items("test", 0, path=X.ITEMS_X), families=("ownership",))
    beh = OUT / "behaviour.jsonl"
    done = {r["key"] for r in read_jsonl(beh)} if beh.exists() else set()
    reads: dict[str, dict[int, Any]] = torch.load(OUT / "readvecs.pt") if (OUT / "readvecs.pt").exists() else {}
    for pi, pair in enumerate(pairs):
        H = {v: X.load_full(pair[v]["item_id"]) for v in ("A", "B")}
        for src in ("A", "B"):
            it = pair[src]
            ids = H[src]["ids"]
            T = len(ids)
            cand_A, cand_B = str(it["primary"]["answer"]), X.other_candidate(it)
            ft = W.pair_first_tokens(tok, cand_A, cand_B, "chat")
            fti = None if ft["unscorable"] else [ft["first_A"], ft["first_B"]]
            h = H[src]["layers"][EDIT].float()
            dl = deltas(H["A"]["layers"], H["B"]["layers"], src, Q, X.pair_seed(pair["pair_id"]))
            ents = [("natural", 0.0)] + [(a, al) for a in ARMS for al in ALPHAS]
            ents = [e for e in ents if f"{pair['pair_id']}|{src}|{e[0]}|{e[1]}" not in done]
            for s in range(0, len(ents), batch):
                ch = ents[s:s + batch]
                if ch[0][0] == "natural":
                    rows = W.prefill_generate(target, ids, read_layers=READ, first_token_ids=fti)
                    ch, rest = ch[:1], ch[1:]
                else:
                    rest = []
                    rows = W.prefill_generate(target, ids, edit_layer=EDIT, row_positions=[list(range(T))] * len(ch),
                                              row_vectors=[h + al * dl[a] for a, al in ch], read_layers=READ, first_token_ids=fti)
                if rest:
                    rows += W.prefill_generate(target, ids, edit_layer=EDIT, row_positions=[list(range(T))] * len(rest),
                                               row_vectors=[h + al * dl[a] for a, al in rest], read_layers=READ, first_token_ids=fti)
                    ch = ch + rest
                for (a, al), r in zip(ch, rows):
                    key = f"{pair['pair_id']}|{src}|{a}|{al}"
                    parsed, _ev = SC.extract_target_answer(r["answer_text"], it)
                    lp = r.get("lp_first") or [None, None]
                    reads[key] = {L: r["read"][L].to(torch.bfloat16) for L in READ}
                    dvec = None if a == "natural" else dl[a]
                    append_jsonl(beh, {"key": key, "pair_id": pair["pair_id"], "source": src, "item_id": it["item_id"], "arm": a, "alpha": al,
                                       "cand_A": cand_A, "cand_B": cand_B, "answer_text": r["answer_text"], "parsed": parsed,
                                       "flipped": parsed == cand_B, "kept": parsed == cand_A,
                                       "lo_model": (None if None in lp else lp[1] - lp[0]),
                                       "edit_norm": None if dvec is None else float(al * dvec.norm()),
                                       "edit_norm_full": float(al * dl["full"].norm()) if a != "natural" else None})
        if pi % 4 == 3:
            torch.save(reads, OUT / "readvecs.pt")
            log(f"pair {pi + 1}/{len(pairs)} decoded")
    torch.save(reads, OUT / "readvecs.pt")
    rows = read_jsonl(beh)
    lop = OUT / "lo.jsonl"
    jl = R.JLensReader().bind(target, layers_keep=list(READ))
    ol = R.OLensReader().bind(target)
    for name, rd in (("jlens", jl), ("olens", ol)):
        for L in READ:
            for s in range(0, len(rows), 32):
                ch = rows[s:s + 32]
                Hm = torch.stack([reads[r["key"]][L].float() for r in ch])
                for r, q in zip(ch, LO.score_lo(rd, Hm, [(r["cand_A"], r["cand_B"]) for r in ch], "ownership", layer=L, batch=32)):
                    append_jsonl(lop, {"key": f"{name}|{L}|{r['key']}", "reader": name, "layer": L, "entry": r["key"], "lo_own": q.get("lo")})
        log(f"{name} LO done")
    (OUT / "phaseA_done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60, "n_rows": len(rows)}, indent=1))
    M.unload(target)


def phase_b() -> None:
    import torch

    t0 = time.time()
    rows = read_jsonl(OUT / "behaviour.jsonl")
    reads = torch.load(OUT / "readvecs.pt")
    nla = R.NLAReader().bind()
    lop = OUT / "lo.jsonl"
    for s in range(0, len(rows), 32):
        ch = rows[s:s + 32]
        Hm = torch.stack([reads[r["key"]][42].float() for r in ch])
        for r, q in zip(ch, LO.score_lo(nla, Hm, [(r["cand_A"], r["cand_B"]) for r in ch], "ownership")):
            append_jsonl(lop, {"key": f"nla|42|{r['key']}", "reader": "nla", "layer": 42, "entry": r["key"], "lo_own": q.get("lo")})
    (OUT / "phaseB_done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60}, indent=1))
    nla.unload()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--batch", type=int, default=16)
    a = ap.parse_args()
    phase_a(a.batch) if a.phase == "A" else phase_b()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
