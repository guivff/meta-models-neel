"""S4 — consistency null (BRIEF_WV S4 / W4): free-text samples of the Oracle (phase A) and the NLA (phase B).

    python -m projects.g_agreement.w_pod.s4_consistency --phase A|B [--n-errors 100 --n-counts 50 --n-random 50 --n-samples 8] [--force]

States: 100 of the 297 puzzle-error states (seed 0; block-42 last-token Y1 capture, --error-layer) and 50 counts states (seed 0 from the
S1 counts_kept list; block-42 last token from S1), 8 samples each at T = 1, top-p 0.95, cap 256, batched (16 rows per generate call);
plus 50 random Gaussian vectors at the median natural norm (seeded), ONE sample each per reader. Rows → cache/g_agreement/w/s4_samples.jsonl
{key, state_item_id, reader, sample_idx, text, candidates, answer (true), actual_answer (model greedy), condition natural|random, family,
layer, seed}. DONE_<reader> per reader, stage DONE after both phases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core.accounting import append_jsonl, done_ids, now_iso, read_jsonl, timed_call

from . import common as W
from . import s1_capture as S1
from . import scoring_multi as SM

STAGE = "s4"
N_ERRORS, N_COUNTS, N_RANDOM, N_SAMPLES = 24, 12, 10, 8  # shrunk 2026-10-12 for the 150-min budget (PREREG deviation)
MAX_NEW_TOKENS = 256
ERROR_LAYER = C.LAYER


def s4_states(*, n_errors: int = N_ERRORS, n_counts: int = N_COUNTS, n_random: int = N_RANDOM, seed: int = 0, error_layer: int | None = None, items_y1: Path | None = None,
              y1_caps_dir: Path | None = None, s1_target: Path | None = None, counts_kept: Path | None = None, states_root: Path | None = None, caps_dir: Path | None = None,
              d_model: int | None = None) -> list[dict[str, Any]]:
    """[{state_item_id, family, condition, H [d], candidates, answer, actual_answer}] — errors, counts, then the random vectors."""
    import torch

    from projects.g_agreement.y1_site import collect as Y1

    error_layer = C.LAYER if error_layer is None else int(error_layer)
    out = []
    errs = {it["item_id"]: it for it in W.load_errors(items_y1)}
    have = [i for i in sorted(errs) if (y1_caps_dir or W.Y1_CAPS_DIR).joinpath(f"{i}.pt").exists()]
    for iid in W.seeded_subset(have, n_errors, seed):
        it = errs[iid]
        v = Y1.cell_vector(Y1.load_cap(iid, y1_caps_dir or W.Y1_CAPS_DIR), error_layer, "0")
        out.append({"state_item_id": iid, "family": "errors", "condition": "natural", "H": v, "candidates": [str(c) for c in it["primary"]["candidates"]],
                    "answer": str((it.get("source") or {}).get("correct")), "actual_answer": str(it["primary"]["answer"]), "layer": error_layer, "prompt_text": it["prompt_text"]})
    rows = {r["item_id"]: r for r in read_jsonl(s1_target or W.S1_TARGET) if r["family"] == "counts"}
    kp = counts_kept or (W.stage_dir("s1") / "counts_kept.json")
    kept = json.loads(kp.read_text()).get("kept") if kp.exists() else None
    pool = [i for i in (kept if kept else sorted(rows)) if i in rows]
    if kept is not None and not kept:
        W.wlog("s4: counts_kept.json lists no correct counts states; falling back to ALL counts S1 states (flagged)")
    for iid in W.seeded_subset(pool, n_counts, seed):
        r = rows[iid]
        sp = (states_root or W.W_CACHE) / f"states_L{C.LAYER}" / f"{iid}.pt"
        h = torch.load(sp, map_location="cpu").float() if sp.exists() else S1.cap_vector(S1.load_cap(iid, caps_dir), C.LAYER, -1)
        out.append({"state_item_id": iid, "family": "counts", "condition": "natural", "H": h, "candidates": list(r["candidates_all"]), "answer": str(r["true_answer"]),
                    "actual_answer": r.get("parsed"), "layer": C.LAYER, "prompt_text": None})
    if out:
        med = float(torch.stack([s["H"] for s in out]).norm(dim=1).median())
        d = out[0]["H"].numel()
    else:
        med, d = 1.0, int(d_model or C.D_MODEL)
    for k in range(n_random):
        g = torch.Generator().manual_seed(C.stable_seed(W.MODULE, "s4_random", "all", k))
        r = torch.randn(d, generator=g)
        out.append({"state_item_id": f"random-{k:02d}", "family": "random", "condition": "random", "H": r / r.norm() * med, "candidates": None, "answer": None, "actual_answer": None,
                    "layer": C.LAYER, "prompt_text": None, "norm_matched_to": med})
    return out


def collect_samples(reader: Any, states: list[dict[str, Any]], *, n_samples: int = N_SAMPLES, samples_path: Path | None = None, max_new_tokens: int = MAX_NEW_TOKENS, batch: int = 16,
                    ledger_path: Path | None = None, log_path: Path | None = None, progress_status: bool = False) -> int:
    import torch

    from . import status as ST

    samples_path = samples_path or W.S4_SAMPLES
    done = done_ids(samples_path, key="key")
    extra = W.row_extra()
    led = W.ledger(f"s4_samples_{reader.name}", {"n_samples": n_samples, "max_new_tokens": max_new_tokens, "batch": batch, "sampling": SM.S4_SAMPLING})
    n = 0
    for cond, ns in (("natural", n_samples), ("random", 1)):
        todo = [s for s in states if s["condition"] == cond and any(f"{reader.name}|{s['state_item_id']}|s{i}" not in done for i in range(ns))]
        per = max(1, batch // ns)
        for b in range(0, len(todo), per):
            chunk = todo[b: b + per]
            H = torch.stack([s["H"] for s in chunk])
            seed = C.stable_seed(W.MODULE, f"s4_{reader.name}", chunk[0]["state_item_id"], 0)
            with timed_call() as st:
                if isinstance(reader, R.OLensReader):
                    res = SM.olens_read_batch(reader, H, layer=C.LAYER, n_samples=ns, seed=seed, max_new_tokens=max_new_tokens, batch=batch)
                else:
                    res = SM.nla_read_batch(reader, H, n_samples=ns, seed=seed, max_new_tokens=max_new_tokens, batch=batch)
            for s, rows in zip(chunk, res):
                for r in rows:
                    key = f"{reader.name}|{s['state_item_id']}|s{r['sample_idx']}"
                    if key in done:
                        continue
                    append_jsonl(samples_path, {"key": key, "state_item_id": s["state_item_id"], "reader": reader.name, "sample_idx": r["sample_idx"], "text": r["text"],
                                                "candidates": s["candidates"], "answer": s["answer"], "actual_answer": s["actual_answer"], "condition": cond, "family": s["family"],
                                                "layer": s["layer"], "seed": r.get("seed"), "n_new_tokens": r["n_new_tokens"], "finish_reason": r["finish_reason"],
                                                "sampling": {**SM.S4_SAMPLING, "max_new_tokens": max_new_tokens}, "activation_norm": round(float(s["H"].norm()), 3),
                                                "norm_matched_to": s.get("norm_matched_to"), "bullets": r.get("bullets"), "raw_text": r.get("raw_text"), **extra})
                    n += 1
            led.add(0, sum(r["n_new_tokens"] for rows in res for r in rows), st.wall_s, st.peak_mem_gb)
            print(f"[w/s4/{reader.name}] {cond}: {min(b + per, len(todo))}/{len(todo)} states", flush=True)
            if progress_status:
                nat = sum(x["condition"] == "natural" for x in states)
                ST.progress(f"S4 consistency ({reader.name})", len(done) + n, nat * n_samples + (len(states) - nat))
    rr = led.flush(ledger_path)
    if rr:
        W.wlog(f"s4 {led.step}: {rr}", log_path)
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--n-errors", type=int, default=N_ERRORS)
    ap.add_argument("--n-counts", type=int, default=N_COUNTS)
    ap.add_argument("--n-random", type=int, default=N_RANDOM)
    ap.add_argument("--n-samples", type=int, default=N_SAMPLES)
    ap.add_argument("--error-layer", type=int, default=None, help="default: the block-42 site (C.LAYER)")
    ap.add_argument("--max-new-tokens", type=int, default=MAX_NEW_TOKENS)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    rname = "olens" if a.phase == "A" else "nla"
    if W.refuse_if_done(STAGE, a.force, sub=rname):
        return 0
    states = s4_states(n_errors=a.n_errors, n_counts=a.n_counts, n_random=a.n_random, error_layer=a.error_layer)
    nat = sum(s["condition"] == "natural" for s in states)
    planned = nat * a.n_samples + (len(states) - nat)
    print(f"[w/s4] phase {a.phase} ({rname}): {nat} natural states × {a.n_samples} + {len(states) - nat} random × 1 = {planned} samples (cap {a.max_new_tokens})", flush=True)
    W.wlog(f"s4 phase {a.phase}: {planned} planned samples ({nat} natural, {len(states) - nat} random); error layer {a.error_layer or C.LAYER}")
    if a.phase == "A":
        from projects.g_agreement.g1_agreement.collect import load_target_timed

        target = load_target_timed(W.MODULE)
        ol = R.OLensReader().bind(target)
        n = collect_samples(ol, states, n_samples=a.n_samples, max_new_tokens=a.max_new_tokens, batch=a.batch, progress_status=True)
        M.unload(target)
    else:
        nla = R.NLAReader().bind()
        n = collect_samples(nla, states, n_samples=a.n_samples, max_new_tokens=a.max_new_tokens, batch=a.batch, progress_status=True)
        nla.unload()
    W.mark_done(STAGE, sub=rname, info={"n_new": n, "planned": planned})
    if W.is_done(STAGE, sub="olens") and W.is_done(STAGE, sub="nla"):
        W.mark_done(STAGE, info={"readers": ["olens", "nla"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
