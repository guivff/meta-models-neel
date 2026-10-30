"""G5 planted binding swap (GPU; BRIEF_G5G6). On the 8 ownership + mapping TEST pairs (16 cached
block-42 states): native paired log-odds (LO) for the three readers on the natural states, on
planted states h + s·α·Δ·u (α ∈ {0.5, 1.0, 1.5}, toward the other state of the pair, from both
states), and on K null directions per pair at α = 1.0; behavioural decodes with the edited state
replacing the block-42 output at the last prompt position (natural, planted at 3 doses, nulls);
free OLens/NLA readouts at α = 1.0 (G1 row schema, module g5, condition "planted").

    python -m projects.g_agreement.g5_planted.collect --phase A          # target + OLens + J-lens: LO, behaviour, free OLens
    python -m projects.g_agreement.g5_planted.collect --phase B          # NLA: LO, free NLA

Outputs (resumable by ``key`` / ``gen_id``):
  cache/g_agreement/g5/lo.jsonl         one row per (state, reader, condition, alpha, sign, null_k)
  cache/g_agreement/g5/behaviour.jsonl  one row per (state, condition, alpha, sign, null_k)
  cache/g_agreement/gens/g5.jsonl       free readouts (G1 schema)
Ledger steps: g5_lo_{jlens,olens,nla}, g5_behaviour, g5_free. Test states only; the freeze is
checked with a relaxed code-sha rule (G5 code post-dates the freeze; both shas are recorded).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import edit as E
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core import states as S
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, timed_call
from projects.g_agreement.g1_agreement.collect import base_row, load_target_timed

MODULE = "g5"
G5_DIR = C.CACHE_DIR / "g5"
LO_PATH = G5_DIR / "lo.jsonl"
BEH_PATH = G5_DIR / "behaviour.jsonl"
GENS = C.GENS_DIR / "g5.jsonl"
LOG = C.RESULTS_DIR / "g5" / "log.md"
FAMILIES = ("ownership", "mapping")
ALPHAS = (0.5, 1.0, 1.5)
NULL_ALPHA = 1.0
FREE_ALPHA = 1.0
BEHAVIOUR_TOKENS = 8


# ------------------------------------------------------------------ pairs and vectors
def g5_pairs(limit: int = 0, items: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    items = items if items is not None else C.load_items("test")
    by_pair: dict[str, dict[str, Any]] = {}
    for it in items:
        if it["family"] not in FAMILIES or it.get("split") != "test":
            continue
        by_pair.setdefault(it["pair_id"], {"pair_id": it["pair_id"], "family": it["family"]})[it["version"]] = it
    pairs = [p for _, p in sorted(by_pair.items()) if "A" in p and "B" in p]
    return pairs[: limit or None]


def other_candidate(item: dict[str, Any]) -> str:
    cands = item["primary"]["candidates"]
    ans = item["primary"]["answer"]
    (other,) = [c for c in cands if c != ans]
    return other


ALPHAS_ACTIVE: tuple[float, ...] = ALPHAS  # overridden by --alphas (exploratory dose ladder)


def pair_entries(pair: dict[str, Any], n_null: int, states_dir: Path | None = None,
                 alphas: tuple[float, ...] | None = None, null_alphas: tuple[float, ...] = (NULL_ALPHA,)) -> list[dict[str, Any]]:
    """swap_vectors entries for the pair, each tagged with its source item, state id and the
    candidate pair (A = correct for the ORIGINAL state, B = the other)."""
    if alphas is None:
        alphas = ALPHAS_ACTIVE
    hA = S.load_state(pair["A"]["item_id"], states_dir)
    hB = S.load_state(pair["B"]["item_id"], states_dir)
    seed = C.stable_seed(MODULE, "null", pair["pair_id"], 0)
    entries = E.swap_vectors(hA, hB, alphas=alphas, signs=(1,), n_null=n_null, seed=seed, null_alphas=null_alphas)
    for e in entries:
        it = pair[e["source"]]
        e.update(item=it, state_item_id=it["item_id"], pair_id=pair["pair_id"], family=pair["family"],
                 cand_A=it["primary"]["answer"], cand_B=other_candidate(it))
    return entries


def entry_key(e: dict[str, Any], reader: str | None = None) -> str:
    k = f"{e['state_item_id']}|{e['condition']}|{e['alpha']}|{e['sign']}|{e['null_k']}"
    return f"{reader}|{k}" if reader else k


def _entry_fields(e: dict[str, Any]) -> dict[str, Any]:
    return {"pair_id": e["pair_id"], "state_item_id": e["state_item_id"], "family": e["family"], "source": e["source"],
            "condition": e["condition"], "alpha": e["alpha"], "sign": e["sign"], "null_k": e["null_k"],
            "cand_A": e["cand_A"], "cand_B": e["cand_B"], "dose_abs": e["dose_abs"], "input_norm": e["input_norm"],
            "delta": e["delta"], "cos_to_u": e.get("cos_to_u"), "created_at": now_iso(), **C.frozen_shas()}


# ------------------------------------------------------------------ LO
def collect_lo(reader: Any, pairs: list[dict[str, Any]], *, n_null: int, lo_path: Path = LO_PATH,
               ledger_path: Path | None = None, log_path: Path | None = LOG, states_dir: Path | None = None,
               batch: int = 32, conditions: tuple[str, ...] = ("natural", "planted", "null")) -> int:
    import torch

    done = done_ids(lo_path, key="key")
    ledger = StepLedger(step=f"g5_lo_{reader.name}", module=MODULE, extra={"n_null": n_null, "batch": batch})
    n = 0
    for pair in pairs:
        entries = [e for e in pair_entries(pair, n_null, states_dir) if e["condition"] in conditions]
        todo = [e for e in entries if entry_key(e, reader.name) not in done]
        if not todo:
            continue
        for s in range(0, len(todo), batch):
            chunk = todo[s: s + batch]
            H = torch.stack([e["vector"] for e in chunk])
            with timed_call() as st:
                rows = LO.score_lo(reader, H, [(e["cand_A"], e["cand_B"]) for e in chunk], pair["family"], batch=batch)
            for e, r in zip(chunk, rows):
                row = {"key": entry_key(e, reader.name), "reader": reader.name, **_entry_fields(e),
                       "lo": r["lo"], "lp_A": r["lp_A"], "lp_B": r["lp_B"], "templates": r["templates"],
                       "unscorable": r["unscorable"], "wall_s_chunk": st.wall_s, "chunk_size": len(chunk)}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason", "n_tokens_A", "n_tokens_B"):
                    if k in r:
                        row[k] = r[k]
                append_jsonl(lo_path, row)
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[g5/lo/{reader.name}] {pair['pair_id']}: {len(todo)} vectors scored", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"lo {reader.name}: {r}")
    return n


# ------------------------------------------------------------------ behaviour (arm U)
def collect_behaviour(target: M.Target, pairs: list[dict[str, Any]], *, n_null: int, beh_path: Path = BEH_PATH,
                      ledger_path: Path | None = None, log_path: Path | None = LOG, states_dir: Path | None = None,
                      max_new_tokens: int = BEHAVIOUR_TOKENS, conditions: tuple[str, ...] = ("natural", "planted", "null")) -> int:
    from projects.g_agreement.core import scoring as SC

    done = done_ids(beh_path, key="key")
    ledger = StepLedger(step="g5_behaviour", module=MODULE, extra={"n_null": n_null, "max_new_tokens": max_new_tokens})
    n = 0
    for pair in pairs:
        for e in pair_entries(pair, n_null, states_dir):
            if e["condition"] not in conditions:
                continue
            key = entry_key(e)
            if key in done:
                continue
            it = e["item"]
            ids = M.render_item(target.tokenizer, it["prompt_text"], it.get("system"))
            res = E.generate_with_edited_state(target, ids, e["vector"], pos=-1, max_new_tokens=max_new_tokens)
            parsed, evidence = SC.extract_target_answer(res["answer_text"], it)
            row = {"key": key, **_entry_fields(e), "answer_text": res["answer_text"], "parsed": parsed,
                   "parse_evidence": evidence, "flipped_to_other": parsed == e["cand_B"],
                   "kept_original": parsed == e["cand_A"], "n_new_tokens": res["n_new_tokens"],
                   "finish_reason": res["finish_reason"], "pos": res["pos"], "n_tokens": res["n_tokens"],
                   "n_hook_edits": res["n_hook_edits"], "prompt_ids_sha256": C.sha256_ids(ids), "wall_s": res["wall_s"]}
            append_jsonl(beh_path, row)
            ledger.add(len(ids), res["n_new_tokens"], res["wall_s"], res["peak_mem_gb"])
            n += 1
        print(f"[g5/behaviour] {pair['pair_id']} done", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"behaviour: {r}")
    return n


# ------------------------------------------------------------------ free readouts at alpha = 1
def collect_free(reader: Any, pairs: list[dict[str, Any]], *, gens_path: Path = GENS, ledger_path: Path | None = None,
                 log_path: Path | None = LOG, states_dir: Path | None = None, max_new_tokens: int = C.BENCH_MAX_NEW_TOKENS,
                 alpha: float = FREE_ALPHA) -> int:
    done = done_ids(gens_path)
    ledger = StepLedger(step="g5_free", module=MODULE, extra={"reader": reader.name, "alpha": alpha, "cap": max_new_tokens})
    n = 0
    for pair in pairs:
        for e in pair_entries(pair, 0, states_dir, alphas=(alpha,), null_alphas=()):
            if e["condition"] != "planted":
                continue
            it = e["item"]
            row = base_row(MODULE, reader.name, "planted", it, 0)
            if row["gen_id"] in done:
                continue
            res = reader.read(e["vector"], C.LAYER, seed=row["seed"], max_new_tokens=max_new_tokens)
            row.update(res.row())
            row["model_sha"] = C.NLA_SHA if reader.name == "nla" else C.TARGET_MODEL_SHA
            row["layer"] = C.LAYER
            row["input"].update(injection_source=f"pair_swap_alpha{alpha}", alpha=alpha, sign=e["sign"], dose_abs=e["dose_abs"],
                                input_norm=e["input_norm"], delta=e["delta"], swap_toward=pair["B" if e["source"] == "A" else "A"]["item_id"],
                                cand_A=e["cand_A"], cand_B=e["cand_B"])
            row.update(C.frozen_shas())
            append_jsonl(gens_path, row)
            ledger.add(res.n_prompt_tokens, res.n_new_tokens, res.wall_s, res.peak_mem_gb)
            n += 1
            print(f"[g5/free/{reader.name}] {row['gen_id']} new={res.n_new_tokens} {res.finish_reason}", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"free {reader.name}: {r}")
    return n


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--limit-pairs", type=int, default=0)
    ap.add_argument("--n-null", type=int, default=20)
    ap.add_argument("--free-cap", type=int, default=C.BENCH_MAX_NEW_TOKENS, help="free readout cap (brief: 256)")
    ap.add_argument("--skip-behaviour", action="store_true")
    ap.add_argument("--skip-free", action="store_true")
    ap.add_argument("--skip-lo", action="store_true")
    ap.add_argument("--alphas", default=None, help="comma list of planted doses (exploratory ladder; default 0.5,1,1.5)")
    a = ap.parse_args(argv)
    if a.alphas:
        global ALPHAS_ACTIVE
        ALPHAS_ACTIVE = tuple(float(x) for x in a.alphas.split(","))
        print(f"[g5] EXPLORATORY dose ladder alphas={ALPHAS_ACTIVE} (not a pre-registered endpoint)")
    C.require_frozen("test", allow_unfrozen_dev=False, strict_code=False)
    pairs = g5_pairs(a.limit_pairs)
    if not pairs:
        raise SystemExit("no ownership/mapping test pairs found")
    missing = [p[v]["item_id"] for p in pairs for v in ("A", "B") if not S.state_path(p[v]["item_id"]).exists()]
    if missing:
        raise SystemExit(f"missing cached states {missing[:4]}; run G1 phase A first")
    G5_DIR.mkdir(parents=True, exist_ok=True)
    print(f"G5 phase {a.phase}: {len(pairs)} pairs {[p['pair_id'] for p in pairs]}, n_null={a.n_null}, shas={C.frozen_shas()}")
    if a.phase == "A":
        target = load_target_timed(MODULE)
        log_line(LOG, f"phase A: {len(pairs)} pairs, n_null={a.n_null}")
        if not a.skip_lo:
            jl = R.JLensReader().bind(target)
            collect_lo(jl, pairs, n_null=a.n_null)
            del jl
        ol = R.OLensReader(max_new_tokens=a.free_cap).bind(target)
        log_line(LOG, f"olens adapter={ol.adapter_dir} liveness={ol.liveness}")
        if not a.skip_lo:
            collect_lo(ol, pairs, n_null=a.n_null)
        if not a.skip_behaviour:
            collect_behaviour(target, pairs, n_null=a.n_null)  # adapter disabled inside the decode
        if not a.skip_free:
            collect_free(ol, pairs, max_new_tokens=a.free_cap)
        M.unload(target)
    else:
        ledger = StepLedger(step="load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader(max_new_tokens=a.free_cap).bind()
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        log_line(LOG, f"phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}")
        if not a.skip_lo:
            collect_lo(nla, pairs, n_null=a.n_null)
        if not a.skip_free:
            collect_free(nla, pairs, max_new_tokens=a.free_cap)
        nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
