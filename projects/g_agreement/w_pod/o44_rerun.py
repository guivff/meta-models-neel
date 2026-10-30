"""O44: Oracle lens on-grid sensitivity (PREREG_WV.md, 2026-10-13 entry). GPU, one process, target model only.

    python -m projects.g_agreement.w_pod.o44_rerun

1. S2 rerun (ownership, mapping): the same edit entries as W1 (64 states x d_cm/d_pw/d_J/d_res/full at alpha 0.5/1, 10 random at
   alpha 1, natural), read-backs at blocks 42 and 44 -> cache/g_agreement/w/o44/{s2_behaviour.jsonl, s2_readvecs/}.
2. X1 states: last-token block 42 and 44 of every items_x test item -> cache/g_agreement/w/o44/x1_states.pt.
3. J-lens (L44, L42) and Oracle (carrier at 44, and 42 as a reproduction check) native LO on the X1 states -> x1_lo44.jsonl;
   J-lens and Oracle LO on the L44 S2 read-backs -> s3_lo44.jsonl (W1 schema, unit S2@L44).
4. Reproduction checks -> checks.json: cosine of the new L42 read-backs to the original S2 read vectors; rerun answers vs the
   original s2_behaviour.jsonl.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, now_iso, read_jsonl
from projects.g_agreement.w_pod import common as W
from projects.g_agreement.w_pod import s2_steer as S2
from projects.g_agreement.w_pod import s3_score as S3
from projects.g_agreement.x1_bank import collect as X1

OUT = W.W_CACHE / "o44"
FAMS = ("ownership", "mapping")
READ = (42, 44)


def main() -> int:
    import torch

    from projects.g_agreement.g1_agreement.collect import load_target_timed

    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    target = load_target_timed("o44")
    log = lambda s: print(f"[o44] {s} ({(time.time() - t0) / 60:.1f} min)", flush=True)  # noqa: E731
    # 1. S2 rerun with read-backs at 42 and 44 (adapter not mounted yet)
    beh = OUT / "s2_behaviour.jsonl"
    rvd = OUT / "s2_readvecs"
    for f in FAMS:
        idx, st = S2.load_states(f, n_states=W.S2_N_STATES)
        table = S2.condition_table(st, alphas=W.S2_ALPHAS, k_random=W.S2_K_RANDOM)
        n = S2.collect_behaviour(target, f, st, table, read_layers=READ, beh_path=beh, readvec_dir=rvd)
        log(f"S2 {f}: {n} new entries ({len(table)} in table)")
    # 2. X1 states at 42 and 44
    pairs = X1.load_pairs(split="test")
    items = [p[v] for p in pairs for v in ("A", "B")]
    xs = {}
    for it in items:
        ids = M.render_item(target.tokenizer, it["prompt_text"], it.get("system"))
        cap = M.capture(target.model, ids, list(READ), [len(ids) - 1])
        xs[it["item_id"]] = {L: cap[L][0].clone() for L in READ}
    torch.save(xs, OUT / "x1_states.pt")
    log(f"X1 captured {len(xs)} states from {len(pairs)} pairs")

    def x1_score(reader, name, layers):
        p = OUT / "x1_lo44.jsonl"
        for L in layers:
            for fam in ("ownership", "mapping", "language", "tense"):
                its = [it for it in items if it["family"] == fam]
                H = torch.stack([xs[it["item_id"]][L] for it in its])
                cands = [(str(it["primary"]["answer"]), X1.other_candidate(it)) for it in its]
                res = LO.score_lo(reader, H, cands, fam, layer=L, batch=32)
                for it, r in zip(its, res):
                    append_jsonl(p, {"key": f"{name}@{L}|{it['item_id']}", "reader": name, "layer": L, "item_id": it["item_id"], "pair_id": it["pair_id"],
                                     "version": it.get("version"), "family": fam, "lo": r.get("lo"), "unscorable": r.get("unscorable")})
    new_rows = [r for r in read_jsonl(beh) if r["family"] in FAMS]
    # 3a. J-lens
    jl = R.JLensReader().bind(target, layers_keep=list(READ))
    x1_score(jl, "jlens", READ)
    S3.score_s2(jl, new_rows, reader_name="jlens", lo_path=OUT / "s3_lo44.jsonl", readvec_dir=rvd, read_layer=44, families=FAMS)
    del jl
    torch.cuda.empty_cache()
    log("J-lens scored")
    # 3b. Oracle lens
    ol = R.OLensReader().bind(target)
    x1_score(ol, "olens", READ)
    S3.score_s2(ol, new_rows, reader_name="olens", lo_path=OUT / "s3_lo44.jsonl", readvec_dir=rvd, read_layer=44, families=FAMS)
    log("Oracle scored")
    # 4. reproduction checks
    orig = {r["key"]: r for r in read_jsonl(W.S2_BEHAVIOUR) if r["family"] in FAMS}
    coss, same = [], 0
    for r in new_rows:
        a = S2.load_readvec(r["key"], 42, rvd).float()
        b = S2.load_readvec(r["key"], 42).float()
        coss.append(float(torch.nn.functional.cosine_similarity(a, b, dim=0)))
        same += int(orig.get(r["key"], {}).get("parsed") == r.get("parsed"))
    chk = {"n_rows": len(new_rows), "readvec42_cos_min": min(coss), "readvec42_cos_mean": sum(coss) / len(coss),
           "parsed_answer_same": same, "wall_min": (time.time() - t0) / 60, "done_at": now_iso()}
    (OUT / "checks.json").write_text(json.dumps(chk, indent=1))
    log(f"checks {chk}")
    M.unload(target)
    (OUT / "DONE").write_text(now_iso())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
