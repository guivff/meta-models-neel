"""F2-6: does any reader track the newline feature `col` (characters since the last newline) at new read sites? (BRIEF_Z.md
"Agam follow-ups 3"). GPU, pod.

    python -m projects.g_agreement.f2.t6_col --phase A    # target: states, J-lens + Oracle LO, Oracle free text (2 samples at 44)
    python -m projects.g_agreement.f2.t6_col --phase B    # NLA LO at 42

Reader templates are Suraj's fixed col templates, copied verbatim from
third_party/mats-nla-workspace-main/experiments/08_col_pilot/templates.py (a = "+" = long line / more characters), plus a
placebo pair unrelated to line length. Outputs cache/g_agreement/f2/t6/{states_L42.pt, lo.jsonl, ol_text.jsonl, phase*_done.json}.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, now_iso

OUT = C.CACHE_DIR / "f2" / "t6"
BANK = Path(__file__).resolve().parent / "t6_bank.json"
LAYERS = (42, 44)
SEED = 20261017
NLA_PAIRS = {  # Suraj 08_col_pilot/templates.py NLA_PAIRS + placebo
    "count_qual": [("Near the end of a long line of text", "At the start of a line of text"), ("A long line of text", "A short line of text")],
    "count_num": [("The current line is about 60 characters long", "The current line is about 20 characters long")],
    "decision": [("A line break is coming up soon", "A line break is still far away"), ("The next token is likely a newline", "The next token is likely another word")],
    "placebo": [("A question about history", "A question about science")],
}
OL_PAIRS = {  # Suraj OL_PAIRS without the leading "- " (lo_olens adds it) + placebo
    "count_qual": [("near the end of a long line", "at the start of a line"), ("a long line of text", "a short line of text")],
    "count_num": [("about 60 characters", "about 20 characters")],
    "decision": [("line break coming up", "line break still far away"), ("next token is a newline", "next token is another word")],
    "placebo": [("a question about history", "a question about science")],
}
JLENS_WORDS = {  # Suraj JLENS_WORDS + placebo
    "count_qual": [(["long", "longer"], ["short", "shorter"]), (["end", "ending"], ["start", "beginning"])],
    "count_num": [(["sixty", "seventy", "eighty"], ["ten", "fifteen", "twenty"])],
    "placebo": [(["history"], ["science"])],
}


def states_list() -> list[dict]:
    bank = json.loads(BANK.read_text())
    out = []
    for it in bank["items"]:
        for lab, r in it["reads"].items():
            for site, ids in r["sites"].items():
                out.append({"key": f"{it['id']}|{lab}|{site}", "item": it["id"], "read": lab, "site": site, "col": r["col"], "width": it["width"], "ids": ids})
    return out


def phase_a(batch: int) -> None:
    import torch

    from projects.g_agreement.agam_viewer.collect import gen_batch
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    target = load_target_timed("f2t6")
    tok = target.tokenizer
    S = states_list()
    H = {}
    for s in S:
        cap = M.capture(target.model, s["ids"], list(LAYERS), [len(s["ids"]) - 1])
        H[s["key"]] = {L: cap[L][0].clone() for L in LAYERS}
    torch.save({k: v[42].to(torch.float16) for k, v in H.items()}, OUT / "states_L42.pt")
    torch.save({k: v[44].to(torch.float16) for k, v in H.items()}, OUT / "states_L44.pt")
    meta = [{k: v for k, v in s.items() if k != "ids"} for s in S]
    (OUT / "states_meta.json").write_text(json.dumps(meta))
    print(f"[f2t6/A] captured {len(S)} states ({(time.time() - t0) / 60:.1f} min)", flush=True)
    lop = OUT / "lo.jsonl"
    # J-lens: word-list LO = max score over single-token variants of list A minus the same for list B
    jl = R.JLensReader().bind(target, layers_keep=list(LAYERS))
    var_ids = {}
    for fam, pairs in JLENS_WORDS.items():
        for ti, (wa, wb) in enumerate(pairs):
            for side, words in (("a", wa), ("b", wb)):
                ids = sorted({i for w in words for i in LO.token_variants(tok, w).values()})
                var_ids[(fam, ti, side)] = ids
    for L in LAYERS:
        J = jl.J[L]
        denom = (jl.w_u @ J).norm(dim=1).clamp_min(1e-9)
        for s in S:
            v = H[s["key"]][L].to(jl.w_u.device).float()
            sc = ((v @ J.T) @ jl.w_u.T) / denom
            for (fam, ti, side), ids in var_ids.items():
                if side != "a":
                    continue
                ia, ib = var_ids[(fam, ti, "a")], var_ids[(fam, ti, "b")]
                lo = None if not ia or not ib else float(sc[ia].max() - sc[ib].max())
                append_jsonl(lop, {"reader": "jlens", "layer": L, "key": s["key"], "family": fam, "t": ti, "lo": lo})
    del jl
    torch.cuda.empty_cache()
    print(f"[f2t6/A] J-lens done ({(time.time() - t0) / 60:.1f} min)", flush=True)
    ol = R.OLensReader().bind(target)
    for L in LAYERS:
        for fam, pairs in OL_PAIRS.items():
            for ti, (a, b) in enumerate(pairs):
                for st in range(0, len(S), 32):
                    ch = S[st:st + 32]
                    Hm = torch.stack([H[s["key"]][L] for s in ch])
                    for s, r in zip(ch, LO.lo_olens(ol, Hm, [(a, b)] * len(ch), layer=L, batch=64)):
                        append_jsonl(lop, {"reader": "olens", "layer": L, "key": s["key"], "family": fam, "t": ti, "lo": r["lo"]})
    print(f"[f2t6/A] Oracle LO done ({(time.time() - t0) / 60:.1f} min)", flush=True)
    # Oracle free text, 2 samples at 44
    L = 44
    embed = target.model.get_input_embeddings()
    dev = next(target.model.parameters()).device
    todo = [(s, k) for s in S for k in range(2)]
    ids0, slot, _c, _cid = ol.carrier(L)
    for nb, st in enumerate(range(0, len(todo), batch)):
        ch = todo[st:st + batch]
        with torch.no_grad():
            e = embed(torch.tensor([ids0] * len(ch), device=dev)).clone()
            for r, (s, _k) in enumerate(ch):
                v = H[s["key"]][L].to(dev).float()
                e[r, slot, :] = (ol.alpha * v / v.norm().clamp_min(1e-9)).to(e.dtype)
        outs = gen_batch(target.model, tok, embeds=e, n_rows=len(ch), seed=SEED + nb)
        for (s, k), o in zip(ch, outs):
            append_jsonl(OUT / "ol_text.jsonl", {"key": s["key"], "sample": k, "layer": L, "text": o["text"], "seed": SEED + nb})
    (OUT / "phaseA_done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60, "n_states": len(S)}, indent=1))
    print(f"[f2t6/A] done ({(time.time() - t0) / 60:.1f} min)", flush=True)
    M.unload(target)


def phase_b() -> None:
    import torch

    t0 = time.time()
    meta = json.loads((OUT / "states_meta.json").read_text())
    H = torch.load(OUT / "states_L42.pt", map_location="cpu")
    LO.NLA_TEMPLATES["col_raw"] = ["{X}"]
    nla = R.NLAReader().bind()
    lop = OUT / "lo.jsonl"
    for fam, pairs in NLA_PAIRS.items():
        for ti, (a, b) in enumerate(pairs):
            for st in range(0, len(meta), 32):
                ch = meta[st:st + 32]
                Hm = torch.stack([H[s["key"]].float() for s in ch])
                for s, r in zip(ch, LO.lo_nla(nla, Hm, [(a, b)] * len(ch), "col_raw")):
                    append_jsonl(lop, {"reader": "nla", "layer": 42, "key": s["key"], "family": fam, "t": ti, "lo": r["lo"]})
    (OUT / "phaseB_done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60}, indent=1))
    print(f"[f2t6/B] done ({(time.time() - t0) / 60:.1f} min)", flush=True)
    nla.unload()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--batch", type=int, default=48)
    a = ap.parse_args()
    phase_a(a.batch) if a.phase == "A" else phase_b()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
