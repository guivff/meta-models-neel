"""Y3 collection (BRIEF_Y §Y3): the new reader families scored in the SAME native-LO harness on the SAME frozen
states as Phase X. Phase A only — every Y3 reader lives on the target (skip-lens LoRA arms, R-lens readout) or
on CPU tensors (SAE); nothing needs the NLA base.

    python -m projects.g_agreement.y3_readers.collect --phase A --readers skip_a,skip_d,sae,rlens --stage all
    python -m projects.g_agreement.y3_readers.collect --phase A --readers skip_a --stage x1 --limit 2 --allow-unfrozen   # smoke

Stages (resumable by key, same row schemas as the Phase X files so the X analyses apply unchanged):
  x1   E14 gate: natural LO on the X1 test states (280) -> cache/g_agreement/y/y3_x1_lo.jsonl (x1_lo.jsonl schema,
       key reader|item_id) + the family mean-state LO (E3; key reader|mean|family)
  x2   E15: LO on the X2 read vectors (cache/g_agreement/x/x2_readvecs, keys from x2_behaviour.jsonl) -> y3_x2_lo.jsonl
  x3   E15: LO on the X3 selected states (items_x3_selected.json, 466) -> y3_x3_lo.jsonl (x3_lo.jsonl schema)
  sae  FVE + shuffled-decoder null on the X1 and X3 states (both encode variants) -> results/g_agreement/y3/sae_fve.json;
       if the pooled FVE (variant ``readme``) >= 0.5 (or --sae-force-probe) the sparse LOO probe rows go into the same
       three files under reader "sae"
Readers: skip_a / skip_d mount their LoRA on the target as named adapters (bind the Oracle lens first if it is
needed in the same process; here it is not); rlens is used only if its checkpoint matches the J-lens readout
(results/g_agreement/y3/rlens_format.json records the inspection either way).
Downloads (hf_dir / hf_hub_download, allow_patterns): adapter files + nla_meta.yaml per arm (1.87 GB each),
layer42.sae.pt (3.36 GB), r-lens lens.pt (3.30 GB). Ledger steps: load_target (module y3), y3_bind_<reader>,
x1_lo_<reader> / x1_mean_lo_<reader> / x2_lo_<reader> / x3_lo_<reader> (the shared collectors tag them with their
own module), y3_sae_load / y3_sae_fve / y3_sae_probe_<stage>. Log: results/g_agreement/y3/log.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import states as S
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, read_jsonl, timed_call
from projects.g_agreement.x1_bank import analyze as X1A
from projects.g_agreement.x1_bank import collect as X1
from projects.g_agreement.x2_causal import collect as X2
from projects.g_agreement.x3_floor import collect as X3
from projects.g_agreement.y3_readers import sae as SAE

MODULE = "y3"
Y_DIR = C.CACHE_DIR / "y"
X1_LO = Y_DIR / "y3_x1_lo.jsonl"
X2_LO = Y_DIR / "y3_x2_lo.jsonl"
X3_LO = Y_DIR / "y3_x3_lo.jsonl"
RESULTS = C.RESULTS_DIR / "y3"
LOG = RESULTS / "log.md"
SAE_FVE_JSON = RESULTS / "sae_fve.json"
RLENS_FORMAT_JSON = RESULTS / "rlens_format.json"
STAGES = ("x1", "x2", "x3")
MODEL_READERS = ("skip_a", "skip_d", "rlens")


# ------------------------------------------------------------------ helpers
def parse_readers(spec: str) -> list[str]:
    out = [s.strip() for s in spec.split(",") if s.strip()]
    bad = [r for r in out if r not in C.Y3_READER_NAMES]
    if bad:
        raise SystemExit(f"unknown Y3 readers {bad}; expected a subset of {C.Y3_READER_NAMES}")
    return out


def parse_stages(spec: str) -> tuple[str, ...]:
    if spec == "all":
        return STAGES
    out = tuple(s.strip() for s in spec.split(",") if s.strip())
    bad = [s for s in out if s not in STAGES]
    if bad:
        raise SystemExit(f"unknown stages {bad}; expected x1|x2|x3|all")
    return out


def x1_pairs(items_file: Path, limit: int) -> list[dict[str, Any]]:
    return X1.load_pairs(items_file, "test", limit)


def x2_pair_ids(beh_path: Path, limit: int) -> set[str] | None:
    """Pair ids of the behaviour rows (first ``limit`` per family when limited; None = all)."""
    if not limit:
        return None
    by_fam: dict[str, list[str]] = {}
    for r in read_jsonl(beh_path):
        fam_list = by_fam.setdefault(r["family"], [])
        if r["pair_id"] not in fam_list:
            fam_list.append(r["pair_id"])
    return {p for ps in by_fam.values() for p in sorted(ps, key=X2.pair_index)[:limit]}


def x3_items(selected_file: Path, limit: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    meta, selected = X3.load_selected(selected_file)
    if limit:
        out: list[dict[str, Any]] = []
        for fam in X3.FAMILIES:
            out += [it for it in selected if it["family"] == fam][:limit]
        selected = out
    return meta, selected


def missing_states(items: list[dict[str, Any]], states_dir: Path | None = None) -> list[str]:
    return [it["item_id"] for it in items if not S.state_path(it["item_id"], states_dir).exists()]


# ------------------------------------------------------------------ model readers
def bind_reader(name: str, target: M.Target, *, ledger_path: Path | None = None, log_path: Path = LOG,
                adapter_dir: str | Path | None = None, lens_path: str | Path | None = None, check: bool = True,
                rlens_format_path: Path = RLENS_FORMAT_JSON) -> Any | None:
    """Mount / load one Y3 model reader on the target; None if it is unusable (logged)."""
    ledger = StepLedger(step=f"y3_bind_{name}", module=MODULE)
    with timed_call() as st:
        if name in ("skip_a", "skip_d"):
            rd = R.SkipLensReader(name[-1]).bind(target, adapter_dir=adapter_dir, check=check)
            log_line(log_path, f"bind {name}: adapter={rd.adapter_dir} liveness={rd.liveness} marker={rd.marker} n_prompt_tokens={len(rd.ids)} "
                               f"adapters_mounted={list(getattr(target.model, 'peft_config', {}))}")
        elif name == "rlens":
            rd = R.RLensReader().bind(target, lens_path=lens_path)
            rlens_format_path.parent.mkdir(parents=True, exist_ok=True)
            rlens_format_path.write_text(json.dumps({"written": now_iso(), "lens_path": rd.lens_path, "usable": rd.usable,
                                                     "skip_reason": rd.skip_reason, "format": rd.format,
                                                     "source_layers": rd.source_layers, "n_prompts": rd.n_prompts}, indent=1, default=str))
            if not rd.usable:
                log_line(log_path, f"rlens SKIPPED: {rd.skip_reason}; format={rd.format}")
                rd = None
            else:
                log_line(log_path, f"bind rlens: {rd.lens_path} source_layers {rd.source_layers[:3]}..{rd.source_layers[-3:]} "
                                   f"n_prompts={rd.n_prompts} provenance={rd.format.get('provenance')}")
        else:
            raise ValueError(name)
    ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush(ledger_path)
    return rd


def run_model_readers(target: M.Target, readers: list[Any], stages: tuple[str, ...], *, items_file: Path, selected_file: Path, limit: int,
                      batch: int, beh_path: Path = X2.BEH_PATH, readvec_dir: Path | None = None, states_dir: Path | None = None,
                      x1_lo: Path = X1_LO, x2_lo: Path = X2_LO, x3_lo: Path = X3_LO, ledger_path: Path | None = None,
                      log_path: Path = LOG) -> dict[str, int]:
    """X1 / X2 / X3 native LO for every bound reader via the Phase X collectors (schema-identical rows)."""
    counts: dict[str, int] = {}
    if "x1" in stages:
        pairs = x1_pairs(items_file, limit)
        miss = missing_states(X1.pair_items(pairs), states_dir)
        if miss:
            raise SystemExit(f"X1 states missing for {miss[:4]} (+{max(0, len(miss) - 4)}); run x1 phase A first")
        for rd in readers:
            n = X1.collect_lo(rd, pairs, lo_path=x1_lo, ledger_path=ledger_path, log_path=log_path, states_dir=states_dir, batch=batch, items_path=items_file)
            m = X1.collect_mean_lo(rd, pairs, lo_path=x1_lo, ledger_path=ledger_path, log_path=log_path, states_dir=states_dir, batch=batch, items_path=items_file)
            counts[f"x1_{rd.name}"] = n + m
            log_line(log_path, f"x1 {rd.name}: {n} new LO rows, {m} new mean-state rows ({len(pairs)} pairs)")
    if "x2" in stages:
        if not beh_path.exists():
            raise SystemExit(f"{beh_path} missing; run x2 phase A first")
        pid = x2_pair_ids(beh_path, limit)
        for rd in readers:
            n = X2.collect_lo(rd, beh_path=beh_path, lo_path=x2_lo, readvec_dir=readvec_dir, ledger_path=ledger_path, log_path=log_path,
                              batch=batch, items_file=items_file, pair_ids=pid)
            counts[f"x2_{rd.name}"] = n
            log_line(log_path, f"x2 {rd.name}: {n} new LO rows on read vectors (pairs={'all' if pid is None else len(pid)})")
    if "x3" in stages:
        meta, selected = x3_items(selected_file, limit)
        miss = missing_states(selected, states_dir)
        if miss:
            raise SystemExit(f"X3 states missing for {miss[:4]} (+{max(0, len(miss) - 4)}); run x3 phase A first")
        extra = {"selected_file": str(selected_file), "selected_sha256": C.sha256_file(selected_file)}
        for rd in readers:
            n = X3.collect_lo(rd, selected, lo_path=x3_lo, ledger_path=ledger_path, log_path=log_path, states_dir=states_dir, batch=batch, extra=extra)
            counts[f"x3_{rd.name}"] = n
            log_line(log_path, f"x3 {rd.name}: {n} new LO rows ({len(selected)} selected items)")
    return counts


# ------------------------------------------------------------------ SAE
def sae_path_default() -> Path:
    from huggingface_hub import hf_hub_download

    return Path(hf_hub_download(C.SAE_REPO, C.SAE_FILE, revision=C.SAE_SHA))


def run_sae(stages: tuple[str, ...], *, items_file: Path, selected_file: Path, limit: int, sae_path: Path | None = None,
            beh_path: Path = X2.BEH_PATH, readvec_dir: Path | None = None, states_dir: Path | None = None,
            x1_lo: Path = X1_LO, x2_lo: Path = X2_LO, x3_lo: Path = X3_LO, fve_json: Path = SAE_FVE_JSON,
            ledger_path: Path | None = None, log_path: Path = LOG, force_probe: bool = False, device: str = "cpu",
            max_latents: int = C.SAE_PROBE_MAX_LATENTS) -> dict[str, Any]:
    """FVE transfer test (both encode variants, shuffled-decoder null) on the X1 and X3 states; probe rows if the gate passes."""
    import torch

    led = StepLedger(step="y3_sae_load", module=MODULE)
    with timed_call() as st:
        path = Path(sae_path) if sae_path else sae_path_default()
        sae = SAE.load_sae(path, k=C.SAE_K, variant=C.SAE_ENCODE_VARIANT, device=device)
    led.add(0, 0, st.wall_s, st.peak_mem_gb)
    led.flush(ledger_path)
    log_line(log_path, f"sae loaded: {path} d={sae.d} d_sae={sae.d_sae} k={sae.k} sha256={C.sha256_file(path) if path.stat().st_size < 5e9 else 'n/a'}")
    pairs = x1_pairs(items_file, limit)
    x1_states = {it["item_id"]: S.load_state(it["item_id"], states_dir) for it in X1.pair_items(pairs) if S.state_path(it["item_id"], states_dir).exists()}
    _meta, selected = x3_items(selected_file, limit)
    x3_states = {it["item_id"]: S.load_state(it["item_id"], states_dir) for it in selected if S.state_path(it["item_id"], states_dir).exists()}
    rep: dict[str, Any] = {"written": now_iso(), "sae": SAE.sae_meta(sae), "file_sha256_expected": C.SAE_FILE_SHA256, "gate_min_fve": C.SAE_FVE_MIN,
                           "gate_variant": C.SAE_ENCODE_VARIANT, "n_x1_states": len(x1_states), "n_x3_states": len(x3_states), "by_variant": {}}
    led = StepLedger(step="y3_sae_fve", module=MODULE)
    with timed_call() as st:
        for variant in SAE.VARIANTS:
            sv = sae.with_variant(variant)
            r: dict[str, Any] = {}
            if x1_states:
                r["x1"] = SAE.fve_report(sv, torch.stack(list(x1_states.values())))
            if x3_states:
                r["x3"] = SAE.fve_report(sv, torch.stack(list(x3_states.values())))
            if x1_states or x3_states:
                r["pooled"] = SAE.fve_report(sv, torch.stack(list(x1_states.values()) + list(x3_states.values())))
            rep["by_variant"][variant] = r
    led.add(0, 0, st.wall_s, st.peak_mem_gb)
    led.flush(ledger_path)
    gate_rep = rep["by_variant"].get(C.SAE_ENCODE_VARIANT, {}).get("pooled")
    gate_fve = gate_rep["fve"] if gate_rep else float("nan")
    passes = bool(gate_rep and gate_fve >= C.SAE_FVE_MIN)
    rep.update(gate_fve=gate_fve, gate_passes=passes, probe_rows_written=bool(passes or force_probe), forced=bool(force_probe and not passes))
    fve_json.parent.mkdir(parents=True, exist_ok=True)
    fve_json.write_text(json.dumps(rep, indent=1, default=str) + "\n")
    for variant, r in rep["by_variant"].items():
        for which, d in r.items():
            log_line(log_path, f"sae FVE [{variant}] {which}: n={d['n']} fve={d['fve']:.4f} null={d['fve_null']:.4f} cos={d['mean_cos_x_xhat']:.3f} "
                               f"rel_l2={d['mean_rel_l2']:.3f} neg_codes={d['frac_negative_codes']:.3f}")
    log_line(log_path, f"sae gate ({C.SAE_ENCODE_VARIANT}, pooled): fve={gate_fve:.4f} >= {C.SAE_FVE_MIN} -> {'PASS' if passes else 'FAIL'}"
                       + (" (probe rows forced)" if force_probe and not passes else ""))
    if not (passes or force_probe):
        return rep
    # probe rows (reader "sae"), resumable by key
    sv = sae.with_variant(C.SAE_ENCODE_VARIANT)
    written: dict[str, int] = {}
    if "x1" in stages and x1_states:
        led = StepLedger(step="y3_sae_probe_x1", module=MODULE)
        with timed_call() as st:
            codes = SAE.codes_for(sv, x1_states)
            done = done_ids(x1_lo, key="key")
            shas = X1.x_shas(items_file)
            n = 0
            for fam in X1A.FAMILIES:
                fp = [p for p in pairs if p["family"] == fam]
                if not fp:
                    continue
                for row in SAE.x1_probe_rows(fp, codes, X1A.PROBE_TYPE[fam], X1A.pos_version, max_latents):
                    if row["key"] in done:
                        continue
                    append_jsonl(x1_lo, {**row, "sae": {"variant": sv.variant, "k": sv.k, "max_latents": max_latents}, "created_at": now_iso(), **shas})
                    n += 1
                mrow = SAE.x1_mean_row(fam, fp, codes)
                if mrow["key"] not in done:
                    append_jsonl(x1_lo, {**mrow, "created_at": now_iso(), **shas})
                    n += 1
        led.add(0, 0, st.wall_s, st.peak_mem_gb)
        led.flush(ledger_path)
        written["x1"] = n
        log_line(log_path, f"sae probe x1: {n} new rows")
    if "x3" in stages and x3_states:
        led = StepLedger(step="y3_sae_probe_x3", module=MODULE)
        with timed_call() as st:
            codes = SAE.codes_for(sv, x3_states)
            items = {it["item_id"]: it for it in selected}
            done = done_ids(x3_lo, key="key")
            n = 0
            for fam, sets in (("puzzle", ("error", "error_control")), ("choice", ("disagree", "agree_control"))):
                for row in SAE.x3_probe_rows(items, codes, sets, fam, max_latents):
                    if row["key"] in done:
                        continue
                    append_jsonl(x3_lo, {**row, "sae": {"variant": sv.variant, "k": sv.k, "max_latents": max_latents}, "created_at": now_iso(),
                                         **C.frozen_shas(), "selected_file": str(selected_file), "selected_sha256": C.sha256_file(selected_file)})
                    n += 1
        led.add(0, 0, st.wall_s, st.peak_mem_gb)
        led.flush(ledger_path)
        written["x3"] = n
        log_line(log_path, f"sae probe x3: {n} new rows")
    if "x2" in stages and beh_path.exists() and x1_states:
        led = StepLedger(step="y3_sae_probe_x2", module=MODULE)
        with timed_call() as st:
            pid = x2_pair_ids(beh_path, limit)
            beh = [r for r in read_jsonl(beh_path) if (pid is None or r["pair_id"] in pid) and X2.readvec_path(r["key"], readvec_dir).exists()]
            done = done_ids(x2_lo, key="key")
            todo = [r for r in beh if f"sae|{r['key']}" not in done]
            n = 0
            if todo:
                rv = {r["key"]: X2.load_readvec(r["key"], readvec_dir) for r in todo}
                rv_codes = SAE.codes_for(sv, rv)
                x1_codes = SAE.codes_for(sv, x1_states)
                by_fam = {fam: [p for p in pairs if p["family"] == fam] for fam in X1A.FAMILIES}
                extra = dict(C.frozen_shas(), items_file=str(items_file), items_file_sha256=C.sha256_file(items_file))
                for row in SAE.x2_probe_rows(todo, rv_codes, by_fam, x1_codes, X1A.PROBE_TYPE, X1A.pos_version, max_latents):
                    append_jsonl(x2_lo, {**row, "sae": {"variant": sv.variant, "k": sv.k, "max_latents": max_latents}, "created_at": now_iso(), **extra})
                    n += 1
        led.add(0, 0, st.wall_s, st.peak_mem_gb)
        led.flush(ledger_path)
        written["x2"] = n
        log_line(log_path, f"sae probe x2: {n} new rows")
    rep["probe_rows_new"] = written
    fve_json.write_text(json.dumps(rep, indent=1, default=str) + "\n")
    return rep


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A"], required=True, help="Y3 readers all live on the target or on CPU tensors: phase A only")
    ap.add_argument("--readers", default=",".join(C.Y3_READER_NAMES))
    ap.add_argument("--stage", default="all", help="x1|x2|x3|all (comma list allowed)")
    ap.add_argument("--limit", type=int, default=0, help="smoke: first N pairs per family (x1/x2) and N items per family (x3)")
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--items-file", default=str(X1.ITEMS_X))
    ap.add_argument("--selected", default=str(X3.SELECTED_JSON))
    ap.add_argument("--sae-path", default=None, help="local layer42.sae.pt (default: hf_hub_download at the pinned sha)")
    ap.add_argument("--sae-force-probe", action="store_true", help="write the SAE probe rows even if the FVE gate fails (labelled)")
    ap.add_argument("--no-liveness", action="store_true", help="skip the adapter liveness assertion (debug only)")
    a = ap.parse_args(argv)
    items_file, selected_file = Path(a.items_file), Path(a.selected)
    readers = parse_readers(a.readers)
    stages = parse_stages(a.stage)
    X1.require_frozen_x("test", a.allow_unfrozen, items_file)
    Y_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    shas = X1.x_shas(items_file)
    print(f"Y3 phase {a.phase}: readers={readers} stages={stages} limit={a.limit} items={items_file.name} sha={shas['items_file_sha256'][:12]} "
          f"manifest_x={shas['manifest_x']}", flush=True)
    log_line(LOG, f"phase A: readers={readers} stages={stages} limit={a.limit} items={items_file.name} sha={shas['items_file_sha256'][:12]} "
                  f"manifest_x={shas['manifest_x']} allow_unfrozen={a.allow_unfrozen} env={C.env_summary()}")
    model_names = [r for r in readers if r in MODEL_READERS]
    if model_names:
        from projects.g_agreement.g1_agreement.collect import load_target_timed

        target = load_target_timed(MODULE)
        bound = []
        for name in model_names:
            rd = bind_reader(name, target, check=not a.no_liveness)
            if rd is not None:
                bound.append(rd)
        if bound:
            counts = run_model_readers(target, bound, stages, items_file=items_file, selected_file=selected_file, limit=a.limit, batch=a.batch)
            log_line(LOG, f"model readers done: {counts}")
        for rd in bound:
            if isinstance(rd, R.SkipLensReader):
                rd.unload()
        M.unload(target)
    if "sae" in readers:
        rep = run_sae(stages, items_file=items_file, selected_file=selected_file, limit=a.limit, sae_path=Path(a.sae_path) if a.sae_path else None,
                      force_probe=a.sae_force_probe)
        print(f"[y3/sae] gate fve={rep.get('gate_fve')} passes={rep.get('gate_passes')} rows={rep.get('probe_rows_new')}", flush=True)
    log_line(LOG, "phase A done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
