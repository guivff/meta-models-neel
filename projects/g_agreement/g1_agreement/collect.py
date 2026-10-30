"""G1 collection (GPU). Phase A on the target model: capture states, target answers (greedy,
32 tok), J-lens readouts, OLens readouts. Phase B on the NLA reader (target unloaded): NLA
readouts from the cached states. Rows follow INTERFACES §5 and go to
``cache/g_agreement/gens/g1.jsonl``; resumable (gen_ids already present are skipped).

    python -m projects.g_agreement.g1_agreement.collect --phase A --items dev
    python -m projects.g_agreement.g1_agreement.collect --phase A --items test
    python -m projects.g_agreement.g1_agreement.collect --phase B --items test
    # G6 (self-choice family, dataset/items_g6.json, module g6 -> gens/g6.jsonl; shared state cache):
    python -m projects.g_agreement.g1_agreement.collect --phase A --items test --items-file projects/g_agreement/dataset/items_g6.json --module g6 --state-free --jlens-null

Control conditions (methods review, 2026-10-07), each a separately budgeted ledger step:
  offgrid_check  dev items only: OLens at layers 40 and 44 (layer integer in the prompt matches
                 the captured layer; states ``<id>@L40.pt`` / ``@L44.pt``)   [phase A, --offgrid]
  state_free     the MEAN of the 8 dev activations in place of a state, sample_idx 0..7 per
                 verbalizer (OLens: mean only — its unit transform is undefined at zero; NLA:
                 mean rows + zero-vector rows)                        [A: olens, B: nla; --state-free]
  noise_ceiling  ``jlens_null``: 20 Gaussian vectors at the median dev-state norm + the mean
                 dev activation, read by the J-lens                              [phase A, --jlens-null]

Test items refuse to run unless ``manifest/frozen_config.json`` is frozen and matches disk.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import generate as G
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import states as S
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, timed_call

MODULE = "g1"
GENS = C.GENS_DIR / "g1.jsonl"
LOG = C.RESULTS_DIR / "g1" / "log.md"
PHASE_A_METHODS = ("target", "jlens", "olens")
ROW_EXTRA: dict[str, Any] = {}  # merged into every row (G6: items_file + its sha, freeze shas)
PHASE_B_METHODS = ("nla",)


def base_row(module: str, method: str, condition: str, item: dict[str, Any] | None, sample_idx: int,
             state_item_id: str | None = None, item_id: str | None = None, tag: str = "") -> dict[str, Any]:
    iid = item["item_id"] if item else item_id
    assert iid is not None
    gid = C.gen_id(module, method, iid, sample_idx) + (f"|{tag}" if tag else "")
    return {
        "gen_id": gid, "module": module, "method": method, "condition": condition, "item_id": iid,
        "state_item_id": (state_item_id if state_item_id is not None else (iid if item else None)),
        "pair_id": item.get("pair_id") if item else None, "family": item.get("family") if item else None,
        "split": item.get("split") if item else None, "sample_idx": sample_idx,
        "seed": C.stable_seed(module, method + (f"@{tag}" if tag else ""), iid, sample_idx),
        "created_at": now_iso(), **ROW_EXTRA,
    }


def _read(reader: Any, h: Any, layer: int, seed: int, max_new_tokens: int | None):
    if reader.name == "jlens":
        return reader.read(h, layer)
    return reader.read(h, layer, seed=seed, max_new_tokens=max_new_tokens)


def _finish_row(row: dict[str, Any], res: Any, reader: Any) -> dict[str, Any]:
    row.update(res.row())
    row["model_sha"] = C.NLA_SHA if reader.name == "nla" else C.TARGET_MODEL_SHA
    return row


def collect_verbalizer(reader: Any, items: list[dict[str, Any]], *, module: str, sample_idxs: list[int],
                       gens_path: Path, condition: str = "genuine", max_new_tokens: int | None = None,
                       ledger_path: Path | None = None, log_path: Path | None = None,
                       states_dir: Path | None = None, layer: int = C.LAYER, step: str | None = None) -> int:
    """Read every (item, sample_idx) with a reader (jlens/olens/nla) from the cached state at
    ``layer`` (42, or 40/44 for the off-grid check; the prompt's layer integer follows it)."""
    tag = "" if layer == C.LAYER else f"L{layer}"
    done = done_ids(gens_path)
    ledger = StepLedger(step=step or reader.name, module=module, extra={"condition": condition, "layer": layer})
    n = 0
    for it in items:
        h = None
        for s in sample_idxs:
            row = base_row(module, reader.name, condition, it, s, tag=tag)
            row["layer"] = layer
            if row["gen_id"] in done:
                continue
            if h is None:
                h = S.load_state(it["item_id"], states_dir, layer)
            res = _read(reader, h, layer, row["seed"], max_new_tokens)
            append_jsonl(gens_path, _finish_row(row, res, reader))
            ledger.add(res.n_prompt_tokens, res.n_new_tokens, res.wall_s, res.peak_mem_gb)
            n += 1
            print(f"[{module}/{reader.name}/{condition}] {row['gen_id']} new={res.n_new_tokens} "
                  f"{res.finish_reason} {res.wall_s:.1f}s", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"{reader.name} {condition}: {r}")
    return n


def collect_state_free(reader: Any, items: list[dict[str, Any]], *, module: str = "g3", gens_path: Path | None = None,
                       max_new_tokens: int | None = None, ledger_path: Path | None = None,
                       log_path: Path | None = None, states_dir: Path | None = None,
                       dev_items: list[dict[str, Any]] | None = None) -> int:
    """``state_free`` (G3 reader-prior control): the reader run with the MEAN of the 8 dev activations in
    place of the state, ONE row per selected item (item-linked so the claim is scored against that item's
    key; the input is identical for every item, only the seed differs). Rows: module g3, condition
    state_free, state_item_id null, input.injection_source = mean_dev_activation -> gens/g3.jsonl."""
    gens_path = gens_path or (C.GENS_DIR / "g3.jsonl")
    stats = S.dev_state_stats(dev_items or items, states_dir)
    h = stats["mean"]
    done = done_ids(gens_path)
    ledger = StepLedger(step=f"state_free_{reader.name}", module=module, extra={"dev_items": stats["item_ids"]})
    n = 0
    for it in items:
        row = base_row(module, reader.name, "state_free", it, 0, state_item_id=None)
        row["state_item_id"] = None
        row["layer"] = C.LAYER
        if row["gen_id"] in done:
            continue
        res = _read(reader, h, C.LAYER, row["seed"], max_new_tokens)
        row = _finish_row(row, res, reader)
        row["input"]["injection_source"] = "mean_dev_activation"
        row["input"]["source_dev_items"] = stats["item_ids"]
        row["input"]["prompt_ids_sha256"] = None  # no item render enters a state-free call
        append_jsonl(gens_path, row)
        ledger.add(res.n_prompt_tokens, res.n_new_tokens, res.wall_s, res.peak_mem_gb)
        n += 1
        print(f"[{module}/{reader.name}/state_free] {row['gen_id']} new={res.n_new_tokens}", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"{reader.name} state_free: {r}")
    return n


def collect_jlens_null(jl: R.JLensReader, items: list[dict[str, Any]], *, module: str = "g1", gens_path: Path = GENS,
                       ledger_path: Path | None = None, log_path: Path | None = None,
                       states_dir: Path | None = None, seed: int = C.JLENS_NULL_SEED,
                       dev_items: list[dict[str, Any]] | None = None) -> int:
    """``jlens_null`` / ``noise_ceiling`` (G1 J-lens noise floor): per selected item, one Gaussian vector at
    the median dev-state norm (seeded per item) and the mean dev activation, read with the J-lens and
    scored against that item's candidates. method jlens_null, state_item_id null,
    input.injection_source in {random_same_norm, mean_dev_activation}; gen_id tags |rand / |mean."""
    import torch

    stats = S.dev_state_stats(dev_items or items, states_dir)
    done = done_ids(gens_path)
    ledger = StepLedger(step="jlens_null", module=module, extra={"seed": seed, "median_norm": stats["median_norm"]})
    k = 0
    for it in items:
        g = torch.Generator().manual_seed(seed + C.stable_seed(module, "jlens_null", it["item_id"], 0))
        v = torch.randn(C.D_MODEL, generator=g)
        vectors = [("rand", v / v.norm() * stats["median_norm"], "random_same_norm"),
                   ("mean", stats["mean"], "mean_dev_activation")]
        for tag, h, source in vectors:
            row = base_row(module, "jlens_null", "noise_ceiling", it, 0, state_item_id=None, tag=tag)
            row["state_item_id"] = None
            row["layer"] = C.LAYER
            if row["gen_id"] in done:
                continue
            res = jl.read(h, C.LAYER)
            row.update(res.row())
            row["method"] = "jlens_null"
            row["model_sha"] = C.TARGET_MODEL_SHA
            row["input"]["injection_source"] = source
            row["input"]["noise_seed"] = seed
            row["input"]["prompt_ids_sha256"] = None
            append_jsonl(gens_path, row)
            ledger.add(0, 0, res.wall_s, res.peak_mem_gb)
            k += 1
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"jlens_null: {r}")
    return k


def collect_targets(target: M.Target, items: list[dict[str, Any]], *, module: str, gens_path: Path,
                    ledger_path: Path | None = None, log_path: Path | None = None) -> int:
    done = done_ids(gens_path)
    ledger = StepLedger(step="target_gen", module=module)
    n = 0
    for it in items:
        row = base_row(module, "target", "genuine", it, 0)
        row["seed"] = None
        if row["gen_id"] in done:
            continue
        res, ids = G.target_answer(target, it)
        row.update({
            "input": {"fixed_instruction": None, "layer_in_prompt": None,
                      "visible_prompt": target.tokenizer.decode(ids, skip_special_tokens=False),
                      "prompt_ids_sha256": C.sha256_ids(ids), "injection": "none", "activation_norm": None},
            "sampling": res.sampling, "raw_output": res.raw_output, "native": {"text": res.raw_output.strip()},
            "n_prompt_tokens": res.n_prompt_tokens, "n_new_tokens": res.n_new_tokens,
            "finish_reason": res.finish_reason, "wall_s": res.wall_s, "peak_mem_gb": res.peak_mem_gb,
            "model_sha": C.TARGET_MODEL_SHA, "adapter": "none",
        })
        append_jsonl(gens_path, row)
        ledger.add(res.n_prompt_tokens, res.n_new_tokens, res.wall_s, res.peak_mem_gb)
        n += 1
        print(f"[{module}/target] {row['gen_id']} -> {res.raw_output.strip()[:60]!r}", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"target: {r}")
    return n


def select_items(split: str, limit: int, item_ids: list[str] | None = None, path: Path | None = None) -> list[dict[str, Any]]:
    items = C.load_items(split, 0, path=path)
    if item_ids:
        want = set(item_ids)
        items = [it for it in items if it["item_id"] in want]
    return items[: limit or None]


def dev_items_all() -> list[dict[str, Any]]:
    return C.load_items("dev", 0)


def load_target_timed(module: str, ledger_path: Path | None = None) -> M.Target:
    ledger = StepLedger(step="load_target", module=module)
    with timed_call() as st:
        t = M.load_target()
    ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush(ledger_path)
    print(f"loaded {t.model_class} ({t.n_layers} blocks) in {st.wall_s:.0f}s", flush=True)
    return t


def run_phase_a(items: list[dict[str, Any]], methods: tuple[str, ...], gens_path: Path = GENS,
                max_new_tokens: int | None = None, ledger_path: Path | None = None, log_path: Path = LOG,
                offgrid: bool = False, state_free: bool = False, jlens_null: bool = False, module: str = MODULE) -> None:
    target = load_target_timed(module, ledger_path)
    S.ensure_states(target, items, ledger_path=ledger_path, module=module)  # dev items also get L40/L44
    dev = [it for it in items if it["split"] == "dev"]
    if (state_free or jlens_null) and len(dev) < 8:
        dev = dev_items_all()  # the controls always use all 8 dev states
        S.ensure_states(target, dev, ledger_path=ledger_path, module=module)
    log_line(log_path, f"phase A: {len(items)} items, methods={methods}, offgrid={offgrid} state_free={state_free} jlens_null={jlens_null}")
    if "target" in methods:
        collect_targets(target, items, module=module, gens_path=gens_path, ledger_path=ledger_path, log_path=log_path)
    if "jlens" in methods or jlens_null:
        jl = R.JLensReader().bind(target)
        log_line(log_path, f"jlens lens={jl.lens_path} source_layers={jl.source_layers[:1]}..{jl.source_layers[-1:]} n_prompts={jl.n_prompts}")
        if "jlens" in methods:
            collect_verbalizer(jl, items, module=module, sample_idxs=[0], gens_path=gens_path,
                               ledger_path=ledger_path, log_path=log_path)
        if jlens_null:
            collect_jlens_null(jl, items, module=module, gens_path=gens_path, ledger_path=ledger_path, log_path=log_path,
                               dev_items=dev)
        del jl
    if "olens" in methods or offgrid or state_free:
        ol = R.OLensReader(max_new_tokens=max_new_tokens or C.VERBALIZER_MAX_NEW_TOKENS).bind(target)
        log_line(log_path, f"olens adapter={ol.adapter_dir} liveness={ol.liveness}")
        if "olens" in methods:
            collect_verbalizer(ol, items, module=module, sample_idxs=[0], gens_path=gens_path,
                               max_new_tokens=max_new_tokens, ledger_path=ledger_path, log_path=log_path)
        if offgrid:
            for L in C.DEV_EXTRA_LAYERS:
                collect_verbalizer(ol, [it for it in items if it["split"] == "dev"], module=module, sample_idxs=[0],
                                   gens_path=gens_path, condition="offgrid_check", max_new_tokens=max_new_tokens,
                                   ledger_path=ledger_path, log_path=log_path, layer=L, step="olens_offgrid")
        if state_free:
            collect_state_free(ol, items, module="g3", max_new_tokens=max_new_tokens,
                               ledger_path=ledger_path, log_path=log_path, dev_items=dev)
    M.unload(target)


def run_phase_b(items: list[dict[str, Any]], gens_path: Path = GENS, max_new_tokens: int | None = None,
                ledger_path: Path | None = None, log_path: Path = LOG, state_free: bool = False, module: str = MODULE) -> None:
    missing = [it["item_id"] for it in items if not S.state_path(it["item_id"]).exists()]
    if missing:
        raise SystemExit(f"phase B needs cached states; missing: {missing[:5]}... run phase A first")
    ledger = StepLedger(step="load_nla", module=module)
    with timed_call() as st:
        nla = R.NLAReader(max_new_tokens=max_new_tokens or C.VERBALIZER_MAX_NEW_TOKENS).bind()
    ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush(ledger_path)
    log_line(log_path, f"phase B: nla base={nla.base_dir} adapter={nla.adapter_dir} marker={nla.marker} liveness={nla.liveness}")
    collect_verbalizer(nla, items, module=module, sample_idxs=[0], gens_path=gens_path,
                       max_new_tokens=max_new_tokens, ledger_path=ledger_path, log_path=log_path)
    if state_free:
        collect_state_free(nla, items, module="g3", max_new_tokens=max_new_tokens,
                           ledger_path=ledger_path, log_path=log_path, dev_items=dev_items_all())
    nla.unload()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B", "all"], default="A")
    ap.add_argument("--items", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--item-ids", default=None, help="comma list of item_ids (subset)")
    ap.add_argument("--methods", default=",".join(PHASE_A_METHODS), help="phase A methods subset ('' for none)")
    ap.add_argument("--max-new-tokens", type=int, default=None, help="verbalizer cap (default config)")
    ap.add_argument("--offgrid", action="store_true", help="dev OLens at layers 40/44 (phase A)")
    ap.add_argument("--state-free", action="store_true", help="mean-dev-activation rows (A: olens, B: nla)")
    ap.add_argument("--jlens-null", action="store_true", help="J-lens noise ceiling rows (phase A)")
    ap.add_argument("--allow-unfrozen", action="store_true", help="dev-only development runs")
    ap.add_argument("--items-file", default=None, help="another items.json (G6: dataset/items_g6.json); its sha is recorded per row")
    ap.add_argument("--module", default=MODULE, help="module name for gen_ids/ledger (G6: g6)")
    ap.add_argument("--gens", default=None, help="output JSONL (default cache/g_agreement/gens/<module>.jsonl)")
    a = ap.parse_args(argv)
    items_path = Path(a.items_file) if a.items_file else None
    gens_path = Path(a.gens) if a.gens else (GENS if a.module == MODULE else C.GENS_DIR / f"{a.module}.jsonl")
    log_path = LOG if a.module == MODULE else C.RESULTS_DIR / a.module / "log.md"
    if items_path is not None:  # G6 plumbing: the extra family is not part of the freeze; record its sha
        ROW_EXTRA.update(items_file=str(items_path), items_file_sha256=C.sha256_file(items_path), **C.frozen_shas())
        C.require_frozen(a.items, allow_unfrozen_dev=a.allow_unfrozen or a.items == "dev", strict_code=False)
    else:
        C.require_frozen(a.items, allow_unfrozen_dev=a.allow_unfrozen or a.items == "dev")
    items = select_items(a.items, a.limit, a.item_ids.split(",") if a.item_ids else None, path=items_path)
    if not items:
        raise SystemExit("no items selected")
    print(f"{len(items)} items ({a.items}{' from ' + str(items_path) if items_path else ''}); module {a.module}; "
          f"phase {a.phase}; gens {gens_path}; env {C.env_summary()}")
    methods = tuple(m.strip() for m in a.methods.split(",") if m.strip())
    if a.phase in ("A", "all"):
        run_phase_a(items, methods, gens_path=gens_path, max_new_tokens=a.max_new_tokens, offgrid=a.offgrid,
                    state_free=a.state_free, jlens_null=a.jlens_null, log_path=log_path, module=a.module)
    if a.phase in ("B", "all"):
        run_phase_b(items, gens_path=gens_path, max_new_tokens=a.max_new_tokens, state_free=a.state_free,
                    log_path=log_path, module=a.module)
    return 0


if __name__ == "__main__":
    sys.exit(main())
