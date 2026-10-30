"""X2 causal planting (GPU; BRIEF_X §X2). On the first 32 TEST pairs of ownership and of mapping
(items_x.json): capture the full-sequence block-38 and block-42 outputs of both states of a pair
(equal length required), then for every condition entry of the pair (planted A→B / B→A at the site's
dose ladder, K = 6 isotropic nulls, K = 4 other-pair nulls at S1, and the two natural states) run the
target's greedy decode (8 tokens) with the edit in place during the prefill, read back the block-42
last-token vector from the same forward, and record the first-token answer log-odds. Then score the
readers' native LO on every read vector (phase A: J-lens + OLens; phase B: NLA).

    python -m projects.g_agreement.x2_causal.collect --phase A [--sites S1,S2,S3] [--limit-pairs N]
    python -m projects.g_agreement.x2_causal.collect --phase B

Outputs (all resumable by ``key``):
  cache/g_agreement/x/full/{item_id}.pt         {"layers": {38: [T,d], 42: [T,d]} (bf16, lossless w.r.t. the bf16 capture), ids, sha}
  cache/g_agreement/x/x2_behaviour.jsonl        one row per entry (key = pair|source|site|condition|alpha|null_k)
  cache/g_agreement/x/x2_readvecs/{key}.pt      block-42 last-token vector after the edit (bf16 [d])
  cache/g_agreement/x/x2_lo.jsonl               one row per (reader, entry); key = reader|entry key
  results/g_agreement/x2/{log.md, skipped.json}
Sign conventions: cand_A = the source state's OWN answer, cand_B = the other candidate (the planted one);
lo_model = lp(first token of B) − lp(first token of A) at the last prefill position; lo_toward_other =
reader score(B) − score(A). Positive = toward the planted candidate everywhere.
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

MODULE = "x2"
FAMILIES = ("ownership", "mapping")
N_PAIRS_PER_FAMILY = 32
X_DIR = C.CACHE_DIR / "x"
FULL_DIR = X_DIR / "full"
BEH_PATH = X_DIR / "x2_behaviour.jsonl"
LO_PATH = X_DIR / "x2_lo.jsonl"
READVEC_DIR = X_DIR / "x2_readvecs"
RESULTS = C.RESULTS_DIR / "x2"
LOG = RESULTS / "log.md"
SKIPPED = RESULTS / "skipped.json"
ITEMS_X = C.DATASET_DIR / "items_x.json"
FROZEN_X = C.MANIFEST_DIR / "frozen_config_x.json"
SAVE_DTYPE = "bfloat16"  # bf16 is lossless for a bf16 capture and cannot overflow (fp16 max 65504 < residual outliers)
BEHAVIOUR_TOKENS = 8
DEFAULT_BATCH = 8


# ------------------------------------------------------------------ pairs
def pair_index(pair_id: str) -> int:
    tail = pair_id.rsplit("-", 1)[-1]
    digits = "".join(ch for ch in tail if ch.isdigit())
    return int(digits) if digits else 0


def x2_pairs(items: list[dict[str, Any]], split: str = "test", n_pairs: int = N_PAIRS_PER_FAMILY, limit: int = 0,
             families: tuple[str, ...] = FAMILIES) -> list[dict[str, Any]]:
    """The first ``n_pairs`` pairs of each family by pair index (BRIEF_X), both versions present."""
    by: dict[str, dict[str, Any]] = {}
    for it in items:
        if it["family"] not in families or it.get("split") != split:
            continue
        by.setdefault(it["pair_id"], {"pair_id": it["pair_id"], "family": it["family"]})[it["version"]] = it
    out: list[dict[str, Any]] = []
    for fam in families:
        ps = sorted((p for p in by.values() if p["family"] == fam and "A" in p and "B" in p), key=lambda p: pair_index(p["pair_id"]))
        out += ps[:n_pairs]
    return out[: limit or None]


def other_candidate(item: dict[str, Any]) -> str:
    cands = item["primary"]["candidates"]
    ans = item["primary"]["answer"]
    (other,) = [c for c in cands if c != ans]
    return other


def other_pair_ids(pair: dict[str, Any], pairs: list[dict[str, Any]], k: int = E.X2_N_OTHER_NULL) -> list[str]:
    """K other pairs of the same family, drawn by seed (without replacement) from the usable pairs."""
    import numpy as np

    cands = sorted(p["pair_id"] for p in pairs if p["family"] == pair["family"] and p["pair_id"] != pair["pair_id"])
    if not cands:
        return []
    rng = np.random.default_rng(C.stable_seed(MODULE, "otherpair", pair["pair_id"], 0))
    idx = rng.choice(len(cands), size=min(k, len(cands)), replace=False)
    return [cands[int(i)] for i in idx]


def pair_seed(pair_id: str) -> int:
    return C.stable_seed(MODULE, "null", pair_id, 0)


# ------------------------------------------------------------------ full-sequence captures
def full_path(item_id: str, full_dir: Path | None = None) -> Path:
    return (full_dir or FULL_DIR) / f"{item_id}.pt"


def load_full(item_id: str, full_dir: Path | None = None) -> dict[str, Any]:
    import torch

    d = torch.load(full_path(item_id, full_dir), map_location="cpu")
    d["layers"] = {int(k): v.float() for k, v in d["layers"].items()}
    return d


def ensure_full_states(target: M.Target, pairs: list[dict[str, Any]], *, full_dir: Path | None = None, layers: tuple[int, ...] | None = None,
                       ledger_path: Path | None = None, log_path: Path | None = LOG, skipped_path: Path | None = SKIPPED
                       ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Capture (or reuse) ``full/{item_id}.pt`` for both states of every pair; drop pairs whose
    renders differ in length (recorded in skipped.json). Returns (usable pairs, skipped records)."""
    import torch

    full_dir = full_dir or FULL_DIR
    layers = tuple(layers or E.X2_EDIT_LAYERS)
    full_dir.mkdir(parents=True, exist_ok=True)
    ledger = StepLedger(step="x2_capture_full", module=MODULE, extra={"layers": list(layers), "dtype_saved": SAVE_DTYPE})
    usable, skipped = [], []
    for pair in pairs:
        ids = {v: M.render_item(target.tokenizer, pair[v]["prompt_text"], pair[v].get("system")) for v in ("A", "B")}
        if len(ids["A"]) != len(ids["B"]):
            skipped.append({"pair_id": pair["pair_id"], "family": pair["family"], "reason": "unequal render length",
                            "n_tokens": {v: len(ids[v]) for v in ids}})
            print(f"[x2/capture] SKIP {pair['pair_id']}: lengths {len(ids['A'])} != {len(ids['B'])}", flush=True)
            continue
        for v in ("A", "B"):
            it = pair[v]
            p = full_path(it["item_id"], full_dir)
            sha = C.sha256_ids(ids[v])
            if p.exists():
                prev = torch.load(p, map_location="cpu")
                if prev.get("prompt_ids_sha256") != sha or set(int(k) for k in prev["layers"]) != set(layers):
                    raise RuntimeError(f"{p}: cached full capture is from a different render/layer set; delete it to recapture")
                continue
            with timed_call() as st:
                acts = E.capture_full(target, ids[v], list(layers))
            dt = getattr(torch, SAVE_DTYPE)
            torch.save({"item_id": it["item_id"], "pair_id": pair["pair_id"], "family": pair["family"], "version": v,
                        "ids": list(ids[v]), "n_tokens": len(ids[v]), "prompt_ids_sha256": sha, "layers": {int(L): acts[L].to(dt) for L in layers},
                        "dtype_saved": SAVE_DTYPE, "model_id": target.model_id, "model_sha": target.revision, "hook": C.HOOK,
                        "captured_at": now_iso()}, p)
            ledger.add(len(ids[v]), 0, st.wall_s, st.peak_mem_gb)
        usable.append(pair)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"capture_full: {r}")
    if skipped_path is not None:
        skipped_path.parent.mkdir(parents=True, exist_ok=True)
        skipped_path.write_text(json.dumps({"written": now_iso(), "n_skipped": len(skipped), "skipped": skipped}, indent=1))
    return usable, skipped


# ------------------------------------------------------------------ behaviour (+ read vectors)
def readvec_path(key: str, readvec_dir: Path | None = None) -> Path:
    return (readvec_dir or READVEC_DIR) / f"{E.x2_key_safe(key)}.pt"


def load_readvec(key: str, readvec_dir: Path | None = None) -> Any:
    import torch

    return torch.load(readvec_path(key, readvec_dir), map_location="cpu").float()


def _row_extra(items_file: Path | None) -> dict[str, Any]:
    out = dict(C.frozen_shas())
    if items_file is not None:
        out.update(items_file=str(items_file), items_file_sha256=C.sha256_file(items_file))
    return out


def collect_behaviour(target: M.Target, pairs: list[dict[str, Any]], *, sites: tuple[str, ...] = ("S1", "S2", "S3"),
                      beh_path: Path = BEH_PATH, readvec_dir: Path | None = None, full_dir: Path | None = None,
                      ledger_path: Path | None = None, log_path: Path | None = LOG, max_new_tokens: int = BEHAVIOUR_TOKENS,
                      batch: int = DEFAULT_BATCH, items_file: Path | None = None, read_layer: int | None = None) -> int:
    """Every entry of every pair: batched decodes over entries that share (pair, source, site)
    (same ids and positions, per-row vectors). Writes behaviour rows and read vectors; resumable."""
    import torch

    from projects.g_agreement.core import scoring as SC

    readvec_dir = readvec_dir or READVEC_DIR
    read_layer = E.X2_READ_LAYER if read_layer is None else read_layer
    readvec_dir.mkdir(parents=True, exist_ok=True)
    done = {k for k in done_ids(beh_path, key="key") if readvec_path(k, readvec_dir).exists()}
    ledgers = {s: StepLedger(step=f"x2_behaviour_{s}", module=MODULE, extra={"max_new_tokens": max_new_tokens, "batch": batch})
               for s in list(sites) + [E.X2_NATURAL_SITE]}
    extra = _row_extra(items_file)
    dt = getattr(torch, SAVE_DTYPE)
    n = 0
    for pair in pairs:
        others = other_pair_ids(pair, pairs)
        table = E.x2_condition_table(pair["pair_id"], pair["family"], other_pair_ids=others, sites=sites, nulls=E.X2Nulls(pair_seed(pair["pair_id"])))
        todo = [e for e in table if e["key"] not in done]
        if not todo:
            continue
        nulls = E.X2Nulls(pair_seed(pair["pair_id"]))
        H = {v: load_full(pair[v]["item_id"], full_dir) for v in ("A", "B")}
        HA, HB = H["A"]["layers"], H["B"]["layers"]
        if H["A"]["n_tokens"] != H["B"]["n_tokens"]:
            raise RuntimeError(f"{pair['pair_id']}: unequal cached lengths")
        other_dirs = {}
        for op in others:
            pp = next(p for p in pairs if p["pair_id"] == op)
            HO = {v: load_full(pp[v]["item_id"], full_dir)["layers"] for v in ("A", "B")}
            other_dirs[op] = E.x2_other_direction(HO["A"], HO["B"], layer=E.X2_SITES["S1"]["layer"])
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for e in todo:
            groups.setdefault((e["source"], e["site"]), []).append(e)
        for (src, site), ents in groups.items():
            it = pair[src]
            ids = H[src]["ids"]
            cand_A, cand_B = it["primary"]["answer"], other_candidate(it)
            ft = E.first_token_candidates(target.tokenizer, cand_A, cand_B)
            cft = None if ft["unscorable"] else (ft["first_A"], ft["first_B"])
            for s in range(0, len(ents), batch):
                chunk = ents[s: s + batch]
                vecs = [E.x2_entry_vectors(e, HA, HB, nulls, other_dirs) for e in chunk]
                if site == E.X2_NATURAL_SITE:
                    assert len(chunk) == 1
                    rows = E.generate_with_interpolated_batch(target, ids, None, None, None, read_layer=read_layer,
                                                              max_new_tokens=max_new_tokens, cand_first_tokens=cft)
                else:
                    V = torch.stack([v["base"] + float(e["alpha"]) * v["delta"] for e, v in zip(chunk, vecs)])
                    rows = E.generate_with_interpolated_batch(target, ids, E.X2_SITES[site]["layer"], vecs[0]["positions"], V,
                                                              read_layer=read_layer, max_new_tokens=max_new_tokens, cand_first_tokens=cft)
                for e, v, r in zip(chunk, vecs, rows):
                    parsed, evidence = SC.extract_target_answer(r["answer_text"], it)
                    torch.save(r["read_vec"].to(dt), readvec_path(e["key"], readvec_dir))
                    row = {"key": e["key"], "pair_id": pair["pair_id"], "family": pair["family"], "source": src, "state_item_id": it["item_id"],
                           "site": site, "edit_layer": e["edit_layer"], "positions_kind": e["positions_kind"], "n_positions": 0 if v["positions"] is None else len(v["positions"]),
                           "alpha": e["alpha"], "condition": e["condition"], "null_k": e["null_k"], "sign": e["sign"], "other_pair_id": e["other_pair_id"],
                           "cand_A": cand_A, "cand_B": cand_B, "answer_text": r["answer_text"], "parsed": parsed, "parse_evidence": evidence,
                           "flipped_to_other": parsed == cand_B, "kept_original": parsed == cand_A, "coherent": parsed in (cand_A, cand_B),
                           "lo_model": r["lo_model"], "lp_first_A": r["lp_first_A"], "lp_first_B": r["lp_first_B"], "lo_model_unscorable": ft["unscorable"],
                           "lo_model_form": ft["form"], "first_A": ft["first_A"], "first_B": ft["first_B"], "first_token_id": r["first_token_id"], "top1_id": r["top1_id"],
                           "dose_abs": v["dose_abs"], "delta_last": v["delta_last"], "delta_total": v["delta_total"], "delta_edited": v.get("delta_edited"),
                           "input_norm_last": v["input_norm_last"], "cos_to_u_last": v["cos_to_u_last"], "n_new_tokens": r["n_new_tokens"],
                           "finish_reason": r["finish_reason"], "n_tokens": r["n_tokens"], "read_layer": read_layer, "n_hook_edits": r["n_hook_edits"],
                           "batch_size": r["batch_size"], "wall_s": r["wall_s"] / max(1, r["batch_size"]), "wall_s_batch": r["wall_s_batch"],
                           "peak_mem_gb": r["peak_mem_gb"], "prompt_ids_sha256": H[src]["prompt_ids_sha256"], "readvec_dtype": SAVE_DTYPE,
                           "null_seed": nulls.seed, "created_at": now_iso(), **extra}
                    append_jsonl(beh_path, row)
                    n += 1
                ledgers[site].add(len(ids) * len(chunk), sum(r["n_new_tokens"] for r in rows), rows[0]["wall_s_batch"], rows[0]["peak_mem_gb"])
        print(f"[x2/behaviour] {pair['pair_id']}: {len(todo)} entries decoded", flush=True)
    for s, ld in ledgers.items():
        r = ld.flush(ledger_path)
        if log_path and r:
            log_line(log_path, f"behaviour {s}: {r}")
    return n


# ------------------------------------------------------------------ reader LO on the read vectors
def collect_lo(reader: Any, *, beh_path: Path = BEH_PATH, lo_path: Path = LO_PATH, readvec_dir: Path | None = None,
               ledger_path: Path | None = None, log_path: Path | None = LOG, batch: int = 32, items_file: Path | None = None,
               pair_ids: set[str] | None = None) -> int:
    """Native LO of ``reader`` on every behaviour row's read vector, candidates (cand_A, cand_B).
    Stores ``lo_toward_other = score(B) − score(A)`` (positive = toward the planted candidate)."""
    import torch

    readvec_dir = readvec_dir or READVEC_DIR
    done = done_ids(lo_path, key="key")
    beh = [r for r in read_jsonl(beh_path) if pair_ids is None or r["pair_id"] in pair_ids]
    todo = [r for r in beh if f"{reader.name}|{r['key']}" not in done and readvec_path(r["key"], readvec_dir).exists()]
    ledger = StepLedger(step=f"x2_lo_{reader.name}", module=MODULE, extra={"batch": batch})
    extra = _row_extra(items_file)
    n = 0
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for r in todo:
        by_fam.setdefault(r["family"], []).append(r)
    for fam, rows_f in by_fam.items():
        for s in range(0, len(rows_f), batch):
            chunk = rows_f[s: s + batch]
            Hm = torch.stack([load_readvec(r["key"], readvec_dir) for r in chunk])
            with timed_call() as st:
                res = LO.score_lo(reader, Hm, [(r["cand_A"], r["cand_B"]) for r in chunk], fam, batch=batch)
            for b, q in zip(chunk, res):
                row = {"key": f"{reader.name}|{b['key']}", "entry_key": b["key"], "reader": reader.name,
                       **{k: b[k] for k in ("pair_id", "family", "source", "state_item_id", "site", "edit_layer", "positions_kind", "alpha",
                                             "condition", "null_k", "sign", "other_pair_id", "cand_A", "cand_B", "dose_abs", "lo_model", "flipped_to_other", "coherent")},
                       "lo_own": q["lo"], "lo_toward_other": (None if q["lo"] is None else -q["lo"]), "lp_A": q["lp_A"], "lp_B": q["lp_B"],
                       "templates": q["templates"], "unscorable": q["unscorable"], "wall_s_chunk": st.wall_s, "chunk_size": len(chunk),
                       "created_at": now_iso(), **extra}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason"):
                    if k in q:
                        row[k] = q[k]
                append_jsonl(lo_path, row)
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[x2/lo/{reader.name}] {fam}: {len(rows_f)} vectors scored", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"lo {reader.name}: {r}")
    return n


# ------------------------------------------------------------------ freeze (Phase X manifest)
def require_frozen_x(items_file: Path, allow_unfrozen: bool, path: Path = FROZEN_X) -> dict[str, Any]:
    """Test collection needs manifest/frozen_config_x.json that records the sha256 of the items
    file being used (any value in the manifest equal to it); ``--allow-unfrozen`` bypasses."""
    sha = C.sha256_file(items_file)
    if allow_unfrozen:
        return {"frozen": False, "items_file_sha256": sha}
    if not path.exists():
        raise SystemExit(f"refusing to collect: {path} missing (freeze Phase X first or pass --allow-unfrozen)")
    fz = json.loads(path.read_text())

    def values(o: Any):
        if isinstance(o, dict):
            for v in o.values():
                yield from values(v)
        elif isinstance(o, list):
            for v in o:
                yield from values(v)
        else:
            yield o

    if not fz.get("frozen") or sha not in set(values(fz)):
        raise SystemExit(f"refusing to collect: {path} is not frozen on {items_file.name} ({sha[:12]})")
    return {"frozen": True, "items_file_sha256": sha, "manifest": path.name}


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--items-file", default=str(ITEMS_X))
    ap.add_argument("--split", default="test")
    ap.add_argument("--n-pairs", type=int, default=N_PAIRS_PER_FAMILY, help="pairs per family (brief: 32)")
    ap.add_argument("--limit-pairs", type=int, default=0, help="debug: first N pairs overall")
    ap.add_argument("--sites", default="S1,S2,S3")
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="entries per decode batch (same pair/source/site)")
    ap.add_argument("--lo-batch", type=int, default=32)
    ap.add_argument("--max-new-tokens", type=int, default=BEHAVIOUR_TOKENS)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--skip-lo", action="store_true")
    ap.add_argument("--skip-behaviour", action="store_true")
    a = ap.parse_args(argv)
    items_file = Path(a.items_file)
    sites = tuple(s.strip() for s in a.sites.split(",") if s.strip())
    for s in sites:
        if s not in E.X2_SITES:
            raise SystemExit(f"unknown site {s}")
    fz = require_frozen_x(items_file, a.allow_unfrozen or a.split == "dev")
    items = C.load_items(a.split, 0, path=items_file)
    pairs = x2_pairs(items, split=a.split, n_pairs=a.n_pairs, limit=a.limit_pairs)
    if not pairs:
        raise SystemExit(f"no {FAMILIES} {a.split} pairs in {items_file}")
    X_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"X2 phase {a.phase}: {len(pairs)} pairs ({', '.join(p['pair_id'] for p in pairs[:4])} ...), sites={sites}, freeze={fz}, shas={C.frozen_shas()}")
    log_line(LOG, f"phase {a.phase}: {len(pairs)} pairs, sites={sites}, split={a.split}, items={items_file.name} sha={fz['items_file_sha256'][:12]} frozen={fz['frozen']}")
    if a.phase == "A":
        from projects.g_agreement.g1_agreement.collect import load_target_timed

        target = load_target_timed(MODULE)
        usable, skipped = ensure_full_states(target, pairs)
        log_line(LOG, f"capture_full: {len(usable)} usable pairs, {len(skipped)} skipped (unequal length)")
        if not a.skip_behaviour:
            n = collect_behaviour(target, usable, sites=sites, max_new_tokens=a.max_new_tokens, batch=a.batch, items_file=items_file)
            log_line(LOG, f"behaviour: {n} new entries")
        if not a.skip_lo:
            pid = {p["pair_id"] for p in usable}
            jl = R.JLensReader().bind(target)
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
