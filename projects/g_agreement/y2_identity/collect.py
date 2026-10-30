"""Y2 identity-free nulls at S2 (GPU; BRIEF_Y §Y2). On the 64 X2 pairs (full L38/L42 captures already in
cache/g_agreement/x/full): for every Y2 condition entry (name_only, name_removed, K ≤ 4 equal-length other-pair
deltas, J_only / J_perp at r* = 384, K = 3 random equal-rank controls each; α ∈ {0.5, 0.75, 1.0}; both sources)
run the target's greedy decode (8 tokens) with the block-38 edit in place during the prefill, read back the block-42
last-token vector, record the first-token answer log-odds; then score the readers' native LO on every read vector
(phase A: J-lens + OLens; phase B: NLA). The ``full`` condition is X2's S2 planted arm and is NOT re-decoded
(entries carry ``reused_key``; analyze.py pulls those rows from the X2 files).

    python -m projects.g_agreement.y2_identity.collect --phase A [--limit-pairs N] [--alphas 0.5,0.75,1.0]
                                                       [--conditions name_only,name_removed,...] [--batch 8]
    python -m projects.g_agreement.y2_identity.collect --phase B

Outputs (resumable by ``key``):
  cache/g_agreement/y/jspace_L38_r384.pt     J-space basis at L38 (top-384 right singular vectors of W_U·J_38) + eigenvalues
  cache/g_agreement/y/y2_behaviour.jsonl     one row per NEW entry (key = pair|source|Y2|condition|alpha|k)
  cache/g_agreement/y/y2_readvecs/{key}.pt   block-42 last-token vector after the edit (bf16 [d])
  cache/g_agreement/y/y2_lo.jsonl            one row per (reader, entry); key = reader|entry key
  results/g_agreement/y2/{log.md, skipped.json}
Sign conventions as X2: cand_A = the source state's own answer, cand_B = the planted (other) candidate; lo_model =
lp(first B) − lp(first A); lo_toward_other = reader score(B) − score(A). Positive = toward the planted candidate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import edit as E
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, read_jsonl, timed_call
from projects.g_agreement.x2_causal import collect as X

MODULE = "y2"
Y_DIR = C.CACHE_DIR / "y"
BEH_PATH = Y_DIR / "y2_behaviour.jsonl"
LO_PATH = Y_DIR / "y2_lo.jsonl"
READVEC_DIR = Y_DIR / "y2_readvecs"
BASIS_PATH = Y_DIR / f"jspace_L{E.Y2_EDIT_LAYER}_r{E.Y2_R_STAR}.pt"
RESULTS = C.RESULTS_DIR / "y2"
LOG = RESULTS / "log.md"
SKIPPED = RESULTS / "skipped.json"
SAVE_DTYPE = X.SAVE_DTYPE
BEHAVIOUR_TOKENS = X.BEHAVIOUR_TOKENS
DEFAULT_BATCH = X.DEFAULT_BATCH
JLENS_LAYERS_KEEP = (E.Y2_EDIT_LAYER, E.X2_READ_LAYER)


# ------------------------------------------------------------------ pairs
def pair_lengths(pairs: list[dict[str, Any]], full_dir: Path | None = None) -> dict[str, int]:
    """Render length of every pair from its cached A capture (equal to B's by construction)."""
    import torch

    out = {}
    for p in pairs:
        f = X.full_path(p["A"]["item_id"], full_dir)
        out[p["pair_id"]] = int(torch.load(f, map_location="cpu")["n_tokens"])
    return out


def y2_other_pair_ids(pair: dict[str, Any], pairs: list[dict[str, Any]], lengths: dict[str, int], k: int = E.Y2_N_OTHER) -> list[str]:
    """Up to K other pairs of the same family AND the same render length, drawn by seed without replacement
    (position-wise deltas need equal T). Pairs without an equal-length sibling get no other_pair entries."""
    import numpy as np

    cands = sorted(p["pair_id"] for p in pairs if p["family"] == pair["family"] and p["pair_id"] != pair["pair_id"]
                   and lengths.get(p["pair_id"]) == lengths.get(pair["pair_id"]))
    if not cands:
        return []
    rng = np.random.default_rng(C.stable_seed(MODULE, "otherpair", pair["pair_id"], 0))
    idx = rng.choice(len(cands), size=min(k, len(cands)), replace=False)
    return [cands[int(i)] for i in sorted(idx)]


def rand_seed(k: int, r_star: int = E.Y2_R_STAR, layer: int = E.Y2_EDIT_LAYER) -> int:
    return C.stable_seed(MODULE, "randsub", f"L{layer}r{r_star}", k)


def build_tables(pairs: list[dict[str, Any]], *, full_dir: Path | None = None, alphas: tuple[float, ...] = E.Y2_ALPHAS,
                 conditions: tuple[str, ...] = E.Y2_CONDITIONS, n_rand: int = E.Y2_N_RAND, r_star: int = E.Y2_R_STAR,
                 n_other: int = E.Y2_N_OTHER) -> dict[str, list[dict[str, Any]]]:
    lengths = pair_lengths(pairs, full_dir)
    return {p["pair_id"]: E.y2_condition_table(p["pair_id"], p["family"], other_pair_ids=y2_other_pair_ids(p, pairs, lengths, n_other),
                                               alphas=alphas, conditions=conditions, n_rand=n_rand, r_star=r_star, n_other=n_other) for p in pairs}


# ------------------------------------------------------------------ J-space basis
def ensure_basis(jl: R.JLensReader, *, path: Path = BASIS_PATH, r_star: int = E.Y2_R_STAR, layer: int = E.Y2_EDIT_LAYER,
                 ledger_path: Path | None = None, log_path: Path | None = LOG) -> Any:
    """Build (or load) the J-space basis at the edit layer from the bound lens; logs its energy fraction."""
    import torch

    existed = Path(path).exists()
    ledger = StepLedger(step="y2_jspace_basis", module=MODULE, extra={"layer": layer, "r_star": r_star, "cached": existed})
    with timed_call() as st:
        Q = E.jspace_basis(jl.J[layer], jl.w_u, r_star, cache_path=path, layer=layer)
    ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    r = ledger.flush(ledger_path)
    meta = torch.load(path, map_location="cpu")
    if log_path:
        log_line(log_path, f"jspace basis L{layer} r*={r_star}: {'loaded' if existed else 'built'} {path} d={meta.get('d')} "
                 f"energy_top_r={meta.get('energy_fraction_top_r')}; {r}")
    return Q


def rand_bases(d: int, r_star: int = E.Y2_R_STAR, n: int = E.Y2_N_RAND, layer: int = E.Y2_EDIT_LAYER) -> list[Any]:
    return [E.random_subspace(d, r_star, rand_seed(k, r_star, layer)) for k in range(n)]


# ------------------------------------------------------------------ behaviour (+ read vectors)
def collect_behaviour(target: M.Target, pairs: list[dict[str, Any]], tables: dict[str, list[dict[str, Any]]], basis: Any,
                      rbases: list[Any], *, beh_path: Path = BEH_PATH, readvec_dir: Path | None = None, full_dir: Path | None = None,
                      ledger_path: Path | None = None, log_path: Path | None = LOG, max_new_tokens: int = BEHAVIOUR_TOKENS,
                      batch: int = DEFAULT_BATCH, items_file: Path | None = None, read_layer: int | None = None,
                      edit_layer: int | None = None, x2_beh_path: Path | None = X.BEH_PATH) -> int:
    """Every NEW entry of every pair: batched decodes over entries sharing (pair, source, condition) when the condition
    fixes the positions (name_only / name_removed), and over all all-position conditions otherwise. Reused ``full``
    entries are skipped (counted; their X2 rows are checked to exist when the X2 file is present). Resumable."""
    import torch

    from projects.g_agreement.core import scoring as SC

    readvec_dir = readvec_dir or READVEC_DIR
    read_layer = E.X2_READ_LAYER if read_layer is None else read_layer
    edit_layer = E.Y2_EDIT_LAYER if edit_layer is None else edit_layer
    readvec_dir.mkdir(parents=True, exist_ok=True)
    done = {k for k in done_ids(beh_path, key="key") if X.readvec_path(k, readvec_dir).exists()}
    x2_keys = done_ids(x2_beh_path, key="key") if x2_beh_path is not None and Path(x2_beh_path).exists() else None
    ledgers = {c: StepLedger(step=f"y2_behaviour_{c}", module=MODULE, extra={"max_new_tokens": max_new_tokens, "batch": batch}) for c in E.Y2_CONDITIONS if c != "full"}
    extra = X._row_extra(items_file)
    dt = getattr(torch, SAVE_DTYPE)
    basis_sha = C.sha256_bytes(basis.contiguous().numpy().tobytes())[:16]
    n, n_reused, n_reused_missing = 0, 0, 0
    full_cache: dict[str, dict[str, Any]] = {}

    def full(item_id: str) -> dict[str, Any]:
        if item_id not in full_cache:
            full_cache[item_id] = X.load_full(item_id, full_dir)
        return full_cache[item_id]

    for pair in pairs:
        table = tables[pair["pair_id"]]
        reused = [e for e in table if e["reused"]]
        n_reused += len(reused)
        if x2_keys is not None:
            n_reused_missing += sum(1 for e in reused if e["reused_key"] not in x2_keys)
        todo = [e for e in table if not e["reused"] and e["key"] not in done]
        if not todo:
            continue
        H = {v: full(pair[v]["item_id"]) for v in ("A", "B")}
        HA, HB = H["A"]["layers"], H["B"]["layers"]
        if H["A"]["n_tokens"] != H["B"]["n_tokens"]:
            raise RuntimeError(f"{pair['pair_id']}: unequal cached lengths")
        other_deltas = {}
        for op in sorted({e["other_pair_id"] for e in todo if e["other_pair_id"]}):
            pp = next(p for p in pairs if p["pair_id"] == op)
            HO = {v: full(pp[v]["item_id"])["layers"] for v in ("A", "B")}
            other_deltas[op] = HO["B"][edit_layer].float() - HO["A"][edit_layer].float()
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for e in todo:
            groups.setdefault((e["source"], e["positions_kind"]), []).append(e)
        for (src, _pk), ents in groups.items():
            it = pair[src]
            ids = H[src]["ids"]
            cand_A, cand_B = it["primary"]["answer"], X.other_candidate(it)
            ft = E.first_token_candidates(target.tokenizer, cand_A, cand_B)
            cft = None if ft["unscorable"] else (ft["first_A"], ft["first_B"])
            for s in range(0, len(ents), batch):
                chunk = ents[s: s + batch]
                vecs = [E.y2_entry_vectors(e, HA, HB, H["A"]["ids"], H["B"]["ids"], basis=basis, rand_bases=rbases, other_deltas=other_deltas, layer=edit_layer)
                        for e in chunk]
                V = torch.stack([v["base"] + float(e["alpha"]) * v["delta"] for e, v in zip(chunk, vecs)])
                rows = E.generate_with_interpolated_batch(target, ids, edit_layer, vecs[0]["positions"], V, read_layer=read_layer,
                                                          max_new_tokens=max_new_tokens, cand_first_tokens=cft)
                for e, v, r in zip(chunk, vecs, rows):
                    parsed, evidence = SC.extract_target_answer(r["answer_text"], it)
                    torch.save(r["read_vec"].to(dt), X.readvec_path(e["key"], readvec_dir))
                    row = {"key": e["key"], "pair_id": pair["pair_id"], "family": pair["family"], "source": src, "state_item_id": it["item_id"],
                           "site": e["site"], "edit_layer": edit_layer, "positions_kind": e["positions_kind"], "n_positions": v["n_positions"],
                           "positions": v["positions"] if e["positions_kind"] != "all" else None, "n_differing": v["n_differing"], "n_tokens": r["n_tokens"],
                           "alpha": e["alpha"], "condition": e["condition"], "k": e["k"], "null_k": e["k"], "sign": e["sign"], "other_pair_id": e["other_pair_id"],
                           "r_star": e["r_star"], "rand_seed": (rand_seed(int(e["k"])) if e["condition"].startswith("rand") else None), "reused": False,
                           "frac_norm_in_J": v["frac_norm_in_J"], "frac_norm_in_J_full": v["frac_norm_in_J_full"],
                           "cand_A": cand_A, "cand_B": cand_B, "answer_text": r["answer_text"], "parsed": parsed, "parse_evidence": evidence,
                           "flipped_to_other": parsed == cand_B, "kept_original": parsed == cand_A, "coherent": parsed in (cand_A, cand_B),
                           "lo_model": r["lo_model"], "lp_first_A": r["lp_first_A"], "lp_first_B": r["lp_first_B"], "lo_model_unscorable": ft["unscorable"],
                           "lo_model_form": ft["form"], "first_A": ft["first_A"], "first_B": ft["first_B"], "first_token_id": r["first_token_id"], "top1_id": r["top1_id"],
                           "dose_abs": v["dose_abs"], "delta_last": v["delta_last"], "delta_total": v["delta_total"], "delta_edited": v["delta_edited"],
                           "delta_natural_edited": v["delta_natural_edited"], "input_norm_last": v["input_norm_last"], "last_edited": v["last_edited"],
                           "n_new_tokens": r["n_new_tokens"], "finish_reason": r["finish_reason"], "read_layer": read_layer, "n_hook_edits": r["n_hook_edits"],
                           "batch_size": r["batch_size"], "wall_s": r["wall_s"] / max(1, r["batch_size"]), "wall_s_batch": r["wall_s_batch"],
                           "peak_mem_gb": r["peak_mem_gb"], "prompt_ids_sha256": H[src]["prompt_ids_sha256"], "readvec_dtype": SAVE_DTYPE,
                           "basis_sha16": basis_sha, "created_at": now_iso(), **extra}
                    append_jsonl(beh_path, row)
                    n += 1
                for c in {e["condition"] for e in chunk}:
                    sub = [r for e, r in zip(chunk, rows) if e["condition"] == c]
                    ledgers[c].add(len(ids) * len(sub), sum(r["n_new_tokens"] for r in sub), rows[0]["wall_s_batch"] * len(sub) / len(chunk), rows[0]["peak_mem_gb"])
        print(f"[y2/behaviour] {pair['pair_id']}: {len(todo)} entries decoded ({len(reused)} full reused)", flush=True)
    for c, ld in ledgers.items():
        r = ld.flush(ledger_path)
        if log_path and r:
            log_line(log_path, f"behaviour {c}: {r}")
    if log_path:
        log_line(log_path, f"behaviour: {n} new entries; {n_reused} full entries reused from X2 S2"
                 + (f" ({n_reused_missing} MISSING in {x2_beh_path})" if x2_keys is not None else " (X2 behaviour file not checked)"))
    return n


# ------------------------------------------------------------------ reader LO on the read vectors
LO_COPY_KEYS = ("pair_id", "family", "source", "state_item_id", "site", "edit_layer", "positions_kind", "n_positions", "alpha", "condition", "k",
                "null_k", "sign", "other_pair_id", "r_star", "frac_norm_in_J", "cand_A", "cand_B", "dose_abs", "lo_model", "flipped_to_other", "coherent")


def collect_lo(reader: Any, *, beh_path: Path = BEH_PATH, lo_path: Path = LO_PATH, readvec_dir: Path | None = None,
               ledger_path: Path | None = None, log_path: Path | None = LOG, batch: int = 32, items_file: Path | None = None,
               pair_ids: set[str] | None = None) -> int:
    """Native LO of ``reader`` on every Y2 behaviour row's read vector (block 42); ``lo_toward_other = score(B) − score(A)``."""
    import torch

    readvec_dir = readvec_dir or READVEC_DIR
    done = done_ids(lo_path, key="key")
    beh = [r for r in read_jsonl(beh_path) if pair_ids is None or r["pair_id"] in pair_ids]
    todo = [r for r in beh if f"{reader.name}|{r['key']}" not in done and X.readvec_path(r["key"], readvec_dir).exists()]
    ledger = StepLedger(step=f"y2_lo_{reader.name}", module=MODULE, extra={"batch": batch})
    extra = X._row_extra(items_file)
    n = 0
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for r in todo:
        by_fam.setdefault(r["family"], []).append(r)
    for fam, rows_f in by_fam.items():
        for s in range(0, len(rows_f), batch):
            chunk = rows_f[s: s + batch]
            Hm = torch.stack([X.load_readvec(r["key"], readvec_dir) for r in chunk])
            with timed_call() as st:
                res = LO.score_lo(reader, Hm, [(r["cand_A"], r["cand_B"]) for r in chunk], fam, batch=batch)
            for b, q in zip(chunk, res):
                row = {"key": f"{reader.name}|{b['key']}", "entry_key": b["key"], "reader": reader.name, **{k: b.get(k) for k in LO_COPY_KEYS},
                       "lo_own": q["lo"], "lo_toward_other": (None if q["lo"] is None else -q["lo"]), "lp_A": q["lp_A"], "lp_B": q["lp_B"],
                       "templates": q["templates"], "unscorable": q["unscorable"], "wall_s_chunk": st.wall_s, "chunk_size": len(chunk),
                       "created_at": now_iso(), **extra}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason"):
                    if k in q:
                        row[k] = q[k]
                append_jsonl(lo_path, row)
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[y2/lo/{reader.name}] {fam}: {len(rows_f)} vectors scored", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"lo {reader.name}: {r}")
    return n


# ------------------------------------------------------------------ main
def table_counts(tables: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    ents = [e for t in tables.values() for e in t]
    out = {"pairs": len(tables), "entries": len(ents), "reused_full": sum(1 for e in ents if e["reused"]), "new_decodes": sum(1 for e in ents if not e["reused"])}
    for c in E.Y2_CONDITIONS:
        out[f"n_{c}"] = sum(1 for e in ents if e["condition"] == c)
    out["pairs_without_other_pair"] = sum(1 for t in tables.values() if not any(e["condition"] == "other_pair" for e in t))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--items-file", default=str(X.ITEMS_X))
    ap.add_argument("--split", default="test")
    ap.add_argument("--n-pairs", type=int, default=X.N_PAIRS_PER_FAMILY, help="pairs per family (X2: 32)")
    ap.add_argument("--limit-pairs", type=int, default=0, help="debug: first N pairs overall")
    ap.add_argument("--alphas", default=",".join(str(a) for a in E.Y2_ALPHAS))
    ap.add_argument("--conditions", default=",".join(E.Y2_CONDITIONS))
    ap.add_argument("--r-star", type=int, default=E.Y2_R_STAR)
    ap.add_argument("--n-rand", type=int, default=E.Y2_N_RAND)
    ap.add_argument("--n-other", type=int, default=E.Y2_N_OTHER)
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="entries per decode batch (same pair/source/positions)")
    ap.add_argument("--lo-batch", type=int, default=32)
    ap.add_argument("--max-new-tokens", type=int, default=BEHAVIOUR_TOKENS)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--skip-lo", action="store_true")
    ap.add_argument("--skip-behaviour", action="store_true")
    a = ap.parse_args(argv)
    items_file = Path(a.items_file)
    alphas = tuple(float(x) for x in a.alphas.split(",") if x.strip())
    conditions = tuple(c.strip() for c in a.conditions.split(",") if c.strip())
    for c in conditions:
        if c not in E.Y2_CONDITIONS:
            raise SystemExit(f"unknown condition {c}")
    fz = X.require_frozen_x(items_file, a.allow_unfrozen or a.split == "dev")
    items = C.load_items(a.split, 0, path=items_file)
    pairs = X.x2_pairs(items, split=a.split, n_pairs=a.n_pairs, limit=a.limit_pairs)
    if not pairs:
        raise SystemExit(f"no {X.FAMILIES} {a.split} pairs in {items_file}")
    Y_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"Y2 phase {a.phase}: {len(pairs)} pairs, alphas={alphas}, conditions={conditions}, r*={a.r_star}, freeze={fz}", flush=True)
    log_line(LOG, f"phase {a.phase}: {len(pairs)} pairs, alphas={alphas}, conditions={conditions}, r_star={a.r_star}, n_rand={a.n_rand}, n_other={a.n_other}, "
                  f"split={a.split}, items={items_file.name} sha={fz['items_file_sha256'][:12]} frozen={fz['frozen']}")
    if a.phase == "A":
        from projects.g_agreement.g1_agreement.collect import load_target_timed

        target = load_target_timed(MODULE)
        usable, skipped = X.ensure_full_states(target, pairs, log_path=LOG, skipped_path=SKIPPED)  # reuses cache/x/full; captures only what is missing
        log_line(LOG, f"full captures: {len(usable)} usable pairs, {len(skipped)} skipped (unequal length)")
        tables = build_tables(usable, alphas=alphas, conditions=conditions, n_rand=a.n_rand, r_star=a.r_star, n_other=a.n_other)
        cnt = table_counts(tables)
        log_line(LOG, f"condition tables: {cnt}")
        print(f"[y2] tables: {cnt}", flush=True)
        jl = R.JLensReader().bind(target, layers_keep=list(JLENS_LAYERS_KEEP))
        if E.Y2_EDIT_LAYER not in jl.J:
            raise SystemExit(f"lens has no layer {E.Y2_EDIT_LAYER}: {jl.source_layers}")
        basis = ensure_basis(jl, path=Y_DIR / f"jspace_L{E.Y2_EDIT_LAYER}_r{a.r_star}.pt", r_star=a.r_star)
        rb = rand_bases(int(basis.shape[0]), a.r_star, a.n_rand)
        log_line(LOG, f"random subspaces: {a.n_rand} × rank {a.r_star}, seeds {[rand_seed(k, a.r_star) for k in range(a.n_rand)]}")
        if not a.skip_behaviour:
            n = collect_behaviour(target, usable, tables, basis, rb, max_new_tokens=a.max_new_tokens, batch=a.batch, items_file=items_file)
            log_line(LOG, f"behaviour: {n} new entries")
        if not a.skip_lo:
            pid = {p["pair_id"] for p in usable}
            collect_lo(jl, batch=a.lo_batch, items_file=items_file, pair_ids=pid)
            del jl
            ol = R.OLensReader().bind(target)
            log_line(LOG, f"olens adapter={ol.adapter_dir} liveness={ol.liveness}")
            collect_lo(ol, batch=a.lo_batch, items_file=items_file, pair_ids=pid)
        M.unload(target)
    else:
        ledger = StepLedger(step="load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader().bind()
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        log_line(LOG, f"phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}")
        if not a.skip_lo:
            collect_lo(nla, batch=a.lo_batch, items_file=items_file, pair_ids={p["pair_id"] for p in pairs})
        nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
