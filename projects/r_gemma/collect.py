"""Gemma stretch collection (GPU; BRIEF_RG.md §2.2). Mirrors ``r_bench/collect.py`` on Gemma-2-9B-it: batched capture of
the R-A bank at blocks 9/10/20/21/31/41 in two renders, logit-lens margins in the same forward, the prompt-only
forced-choice baseline, the activation oracle's native LO (two forms) with the shuffled / state-free controls and the
pool-eval subset, and the Gemma Scope SAE latents per dataset.

    python -m projects.r_gemma.collect --phase A --datasets 92_glue_sst2 66_living-room --allow-unfrozen   # smoke → cache/g_agreement/rg_unfrozen
    python -m projects.r_gemma.collect --freeze-rg                                                            # manifest/frozen_config_rg.json
    python -m projects.r_gemma.collect --phase A [--shard k/N --pod G]                                        # capture, logit lens, prompt-only, AO LO + controls
    python -m projects.r_gemma.collect --phase S [--saes sae16 sae131 sae16c sae16it]                         # SAE latents + FVE (GPU or CPU)

Outputs (resumable by ``key``; ``cache/g_agreement/rg/``; shard runs append to ``name.<k>.jsonl``):
  states/<dataset>/<render>_L<layer>.npy   fp16 [N, d] in the order of states/<dataset>/index.json (test items first)
  logit_lens.jsonl     key ll|<dataset>|<render>|<item_id>       per-layer lp(first token of pos) − lp(first token of neg)
  prompt_only.jsonl    key po|<dataset>|<item_id>                  forced-choice LO of the base model (adapter off), its greedy pick
  reader_lo.jsonl      key <reader>|L<layer>|<render>[|shuf]|<item_id>   reader ∈ {ao, ao_yn}; lp_A = s_pos, lp_B = s_neg, lo = s_diff
  state_free.jsonl     key <reader>|L<layer>|<render>|<dataset>   the reader's scores on the dataset-mean state
  sae/<dataset>/<render>_L20_<sae>.npz (+ .ids.json)   CSR latents, one row per item in index.json order
  sae_fve.jsonl        key fve|<dataset>|<render>|<sae>           FVE / L0 of the SAE on the dataset's block-20 states
Ledger steps (module rg, one row per step per run): load_target, capture_<render>, prompt_only, lo_<reader>_L<layer>,
control_<reader>_L<layer>, load_ao, sae_<tag>.  Log: results/g_agreement/rg/log.md.
Test items need manifest/frozen_config_rg.json unless --allow-unfrozen (then the cache root is rg_unfrozen/).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, timed_call
from projects.g_agreement.r_bench import bank as B
from projects.g_agreement.r_bench import collect as RC
from projects.r_gemma import config as G
from projects.r_gemma import gemma as GM

MODULE = G.MODULE
RG_DIR = G.RG_DIR
RESULTS = G.RESULTS
FROZEN_RG = G.FROZEN_RG
SHARD: tuple[int, int] | None = None
RUN_META: dict[str, Any] = {}
STATES_DIR = RG_DIR / "states"
SAE_DIR = RG_DIR / "sae"
LL_PATH = RG_DIR / "logit_lens.jsonl"
PO_PATH = RG_DIR / "prompt_only.jsonl"
LO_PATH = RG_DIR / "reader_lo.jsonl"
SF_PATH = RG_DIR / "state_free.jsonl"
FVE_PATH = RG_DIR / "sae_fve.jsonl"
LOG = G.LOG
LEDGER_PATH: Path | None = None


# ------------------------------------------------------------------ cache location, shards, run metadata
def _suffix(name: str) -> str:
    return f"{name}.{SHARD[0]}.jsonl" if SHARD else f"{name}.jsonl"


def _derive_paths() -> None:
    global STATES_DIR, SAE_DIR, LL_PATH, PO_PATH, LO_PATH, SF_PATH, FVE_PATH, LOG, LEDGER_PATH
    STATES_DIR = RG_DIR / "states"
    SAE_DIR = RG_DIR / "sae"
    LL_PATH = RG_DIR / _suffix("logit_lens")
    PO_PATH = RG_DIR / _suffix("prompt_only")
    LO_PATH = RG_DIR / _suffix("reader_lo")
    SF_PATH = RG_DIR / _suffix("state_free")
    FVE_PATH = RG_DIR / _suffix("sae_fve")
    LOG = RESULTS / (f"log.{SHARD[0]}.md" if SHARD else "log.md")
    LEDGER_PATH = (C.RESULTS_DIR / f"compute.{SHARD[0]}.jsonl") if SHARD else None
    _DONE.clear()


def set_cache_dir(root: Path) -> Path:
    global RG_DIR
    RG_DIR = Path(root)
    _derive_paths()
    return RG_DIR


def set_results_dir(root: Path) -> Path:
    global RESULTS
    RESULTS = Path(root)
    _derive_paths()
    return RESULTS


def parse_shard(spec: str | None) -> tuple[int, int] | None:
    if not spec:
        return None
    try:
        k, n = (int(x) for x in spec.split("/"))
    except ValueError as exc:
        raise ValueError(f"--shard must be k/N, got {spec!r}") from exc
    if not 1 <= k <= n:
        raise ValueError(f"--shard k/N needs 1 <= k <= N, got {spec!r}")
    return k, n


def set_shard(shard: tuple[int, int] | None) -> None:
    global SHARD
    SHARD = shard
    _derive_paths()


def shard_datasets(all_datasets: list[str], shard: tuple[int, int] | None) -> list[str]:
    """Shard k of N = positions ≡ k−1 (mod N) in the SORTED list of the bank's datasets (PLAN_R §9)."""
    ds = sorted(set(all_datasets))
    if shard is None:
        return ds
    k, n = shard
    return [d for i, d in enumerate(ds) if i % n == k - 1]


def git_sha() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=C.REPO_ROOT, capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        return None


def set_run_meta(pod: str | None = None, shard: tuple[int, int] | None = None) -> dict[str, Any]:
    RUN_META.clear()
    RUN_META.update(pod=pod or os.environ.get("RUNPOD_POD_ID") or platform.node(), shard=f"{shard[0]}/{shard[1]}" if shard else None,
                    git_sha=git_sha(), model=G.TARGET_ID)
    return dict(RUN_META)


def rlog(text: str) -> None:
    tag = f"[pod={RUN_META.get('pod')} shard={RUN_META.get('shard')} sha={(RUN_META.get('git_sha') or 'none')[:10]}] " if RUN_META else ""
    log_line(LOG, tag + text)


# ------------------------------------------------------------------ resumability and ledgers
_DONE: dict[Path, set[str]] = {}
_LEDGERS: dict[str, StepLedger] = {}


def done_keys(path: Path) -> set[str]:
    p = Path(path)
    if p not in _DONE:
        _DONE[p] = done_ids(p, key="key")
    return _DONE[p]


def append_row(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, {**row, **RUN_META})
    done_keys(path).add(row["key"])


def ledger(step: str, **extra: Any) -> StepLedger:
    if step not in _LEDGERS:
        _LEDGERS[step] = StepLedger(step=step, module=MODULE, extra={**RUN_META, **extra})
    return _LEDGERS[step]


def flush_ledgers(path: Path | None = None) -> list[dict[str, Any]]:
    out = []
    for led in _LEDGERS.values():
        r = led.flush(path or LEDGER_PATH)
        if r:
            out.append(r)
    _LEDGERS.clear()
    return out


_derive_paths()


# ------------------------------------------------------------------ freeze
def snapshot_rg(frozen: bool, items_path: Path | None = None) -> dict[str, Any]:
    items_path = items_path or B.ITEMS_R
    return {"frozen": frozen, "frozen_at": now_iso(), "phase": "RG", "items_file": str(items_path), "items_sha256": C.sha256_file(items_path),
            "spec_sha256": C.sha256_file(C.PROJECT_DIR / "r_bench" / "datasets.py"), "rg_code_sha256": C.sha256_tree(G.rg_code_files()),
            "r_bench_code_sha256": C.sha256_tree(sorted((C.PROJECT_DIR / "r_bench").glob("*.py"))),
            "target": {"id": G.TARGET_ID, "sha": G.TARGET_SHA, "dtype": G.TARGET_DTYPE, "attn": G.ATTN_IMPL},
            "oracle": {"repo": G.AO_REPO, "sha": G.AO_SHA, "special": G.AO_SPECIAL, "prefix": G.AO_PREFIX, "hook_layer": G.AO_HOOK_LAYER,
                       "coef": G.AO_COEF, "grid": list(G.AO_GRID), "fc_suffix": G.AO_FC_SUFFIX, "yn_template": G.AO_YN_TEMPLATE},
            "saes": G.SAES, "sae_ks": list(G.SAE_KS), "layers": list(G.LAYERS), "ao_read_layers": {k: list(v) for k, v in G.AO_READ_LAYERS.items()},
            "primary_layer": G.PRIMARY_LAYER, "renders": list(G.RENDERS), "max_tokens": G.MAX_TOKENS,
            "prompt_only_fc_template": __import__("projects.g_agreement.r_bench.datasets", fromlist=["x"]).PROMPT_ONLY_FC_TEMPLATE, "git_sha": git_sha()}


def freeze_rg(force: bool = False, items_path: Path | None = None) -> Path:
    if FROZEN_RG.exists() and not force and json.loads(FROZEN_RG.read_text()).get("frozen"):
        raise RuntimeError(f"{FROZEN_RG} is already frozen; pass --force and add a dated note under BRIEF_RG.md §9")
    items_path = items_path or B.ITEMS_R
    if not items_path.exists():
        raise RuntimeError(f"{items_path} missing: run r_bench.bank --build first")
    FROZEN_RG.parent.mkdir(parents=True, exist_ok=True)
    FROZEN_RG.write_text(json.dumps(snapshot_rg(True, items_path), indent=1, ensure_ascii=False) + "\n")
    return FROZEN_RG


def require_frozen_rg(allow_unfrozen: bool, items_path: Path | None = None) -> None:
    if allow_unfrozen:
        return
    if not FROZEN_RG.exists():
        raise SystemExit("refusing to collect on test items: manifest/frozen_config_rg.json missing (collect --freeze-rg)")
    fz = json.loads(FROZEN_RG.read_text())
    items_path = items_path or B.ITEMS_R
    if not fz.get("frozen") or fz.get("items_sha256") != C.sha256_file(items_path):
        raise SystemExit("refusing to collect: the items file changed since the RG freeze")
    now = snapshot_rg(True, items_path)
    for k in ("rg_code_sha256", "spec_sha256"):
        if fz.get(k) != now.get(k):
            print(f"[rg] note: {k} changed since the RG freeze; accepted, both recorded per row")


_SHAS: dict[str, Any] = {}


def rg_shas(items_path: Path | None = None) -> dict[str, Any]:
    key = str(items_path or B.ITEMS_R)
    if key not in _SHAS:
        out = {"items_sha256": C.sha256_file(items_path or B.ITEMS_R), "current_rg_code_sha256": C.sha256_tree(G.rg_code_files())}
        if FROZEN_RG.exists():
            out["frozen_rg_code_sha256"] = json.loads(FROZEN_RG.read_text()).get("rg_code_sha256")
        _SHAS[key] = out
    return _SHAS[key]


# ------------------------------------------------------------------ states
def state_file(dataset: str, render: str, layer: int) -> Path:
    return STATES_DIR / dataset / f"{render}_L{layer}.npy"


def index_file(dataset: str) -> Path:
    return STATES_DIR / dataset / "index.json"


def states_done(dataset: str, render: str, layers: tuple[int, ...] = G.LAYERS) -> bool:
    return index_file(dataset).exists() and all(state_file(dataset, render, L).exists() for L in layers)


def load_states(dataset: str, render: str, layer: int) -> tuple[np.ndarray, list[str]]:
    idx = json.loads(index_file(dataset).read_text())["item_ids"]
    X = np.load(state_file(dataset, render, layer)).astype(np.float32)
    if X.shape[0] != len(idx):
        raise RuntimeError(f"{dataset} {render} L{layer}: {X.shape[0]} rows for {len(idx)} items")
    return X, idx


def ordered_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda it: (it["split"] != "test", it["item_id"]))


def write_index(dataset: str, items: list[dict[str, Any]], layers: tuple[int, ...], renders: tuple[str, ...]) -> dict[str, Any]:
    """Created once per dataset; a different item list afterwards is an error (never silently re-ordered)."""
    p = index_file(dataset)
    ids = [it["item_id"] for it in items]
    if p.exists():
        idx = json.loads(p.read_text())
        if idx["item_ids"] != ids:
            raise RuntimeError(f"{dataset}: index.json holds a different item list; delete states/{dataset} to re-capture")
        return idx
    p.parent.mkdir(parents=True, exist_ok=True)
    idx = {"dataset": dataset, "item_ids": ids, "splits": [it["split"] for it in items], "labels": [it["label"] for it in items],
           "layers": list(layers), "renders": list(renders), "max_tokens": G.MAX_TOKENS, "model": G.TARGET_ID, "created_at": now_iso(),
           "n_tokens": {}, "read_token": {}, "state_dtype": {}}
    p.write_text(json.dumps(idx, indent=1))
    return idx


def _update_index(dataset: str, **fields: dict[str, Any]) -> None:
    p = index_file(dataset)
    idx = json.loads(p.read_text())
    for k, v in fields.items():
        idx.setdefault(k, {}).update(v)
    p.write_text(json.dumps(idx, indent=1))


# ------------------------------------------------------------------ capture (+ logit lens)
def capture_dataset(target: M.Target, dataset: str, items: list[dict[str, Any]], renders: tuple[str, ...] = G.RENDERS,
                    layers: tuple[int, ...] = G.LAYERS, batch: int = G.CAPTURE_BATCH, rot_seeds: tuple[int, ...] | None = None) -> dict[str, float]:
    """All items of one dataset (test first), both renders, every layer → fp16 .npy; logit-lens rows per item (with the
    random-rotation margins at the SAE layer when ``rot_seeds`` is given, BRIEF_RG §10)."""
    import torch

    rot_seeds = tuple(G.ROT_SEEDS) if rot_seeds is None else tuple(rot_seeds)

    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    items = ordered_items(items)
    write_index(dataset, items, layers, renders)
    p = items[0]["primary"]
    ft = GM.first_token_candidates(tok, p["candidates"][0], p["candidates"][1], p.get("jlens"))
    onset = GM.onset_token(tok)
    walls: dict[str, float] = {}
    for render in renders:
        if states_done(dataset, render, layers):
            continue
        led = ledger(f"capture_{render}", batch=batch)
        acc: dict[int, list[Any]] = {L: [] for L in layers}
        n_tok = []
        with timed_call() as st_all:
            for s in range(0, len(items), batch):
                chunk = items[s: s + batch]
                rows = [GM.render_ids(tok, it["prompt_text"], render) for it in chunk]
                if render == "chat" and any(r[-1] != onset for r in rows):
                    raise RuntimeError(f"{dataset}: a chat row does not end at the assistant onset")
                n_tok += [len(r) for r in rows]
                order = sorted(range(len(rows)), key=lambda i: len(rows[i]))
                with timed_call() as st:
                    got = RC.capture_batch(target.model, [rows[i] for i in order], list(layers), pad)
                inv = torch.as_tensor(np.argsort(order))
                for L in layers:
                    acc[L].append(got[L][inv])
                if not ft["unscorable"]:
                    per: dict[int, Any] = {}
                    for L in layers:
                        per[L] = GM.logit_lens_lp(target.model, got[L][inv], [ft["pos_id"], ft["neg_id"]])
                    rot: dict[int, Any] = {}
                    if G.SAE_LAYER in layers and rot_seeds:
                        Hs = got[G.SAE_LAYER][inv]
                        for sd in rot_seeds:
                            lp = GM.logit_lens_lp(target.model, Hs @ GM.rotation(sd, Hs.shape[1]), [ft["pos_id"], ft["neg_id"]])
                            rot[sd] = (lp[:, 0] - lp[:, 1]).tolist()
                    for i, it in enumerate(chunk):
                        key = f"ll|{dataset}|{render}|{it['item_id']}"
                        if key in done_keys(LL_PATH):
                            continue
                        append_row(LL_PATH, {"key": key, "module": MODULE, "dataset": dataset, "tag": it.get("tag"), "render": render,
                                             "item_id": it["item_id"], "split": it["split"], "label": it["label"], "candidates": p["candidates"],
                                             "first_pos": ft["pos_id"], "first_neg": ft["neg_id"], "form": ft["form"], "source": ft["source"],
                                             "per_layer": {str(L): {"lp_pos": float(per[L][i, 0]), "lp_neg": float(per[L][i, 1]),
                                                                    "margin": float(per[L][i, 0] - per[L][i, 1])} for L in layers},
                                             "rot_layer": G.SAE_LAYER if rot else None, "rot_margins": {str(sd): v[i] for sd, v in rot.items()},
                                             "unscorable": False, "created_at": now_iso()})
                else:
                    for it in chunk:
                        key = f"ll|{dataset}|{render}|{it['item_id']}"
                        if key not in done_keys(LL_PATH):
                            append_row(LL_PATH, {"key": key, "module": MODULE, "dataset": dataset, "tag": it.get("tag"), "render": render,
                                                 "item_id": it["item_id"], "split": it["split"], "label": it["label"], "candidates": p["candidates"],
                                                 "per_layer": {}, "unscorable": True, "reason": ft["reason"], "created_at": now_iso()})
                led.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
        dtype = "float16"
        for L in layers:
            Xf = torch.cat(acc[L])
            Xh = Xf.to(torch.float16)
            if not torch.isfinite(Xh).all():
                dtype = "float32"
                np.save(state_file(dataset, render, L), Xf.numpy())
            else:
                np.save(state_file(dataset, render, L), Xh.numpy())
        _update_index(dataset, n_tokens={render: n_tok}, read_token={render: ("assistant_onset" if render == "chat" else "last_text_token")},
                      state_dtype={render: dtype})
        walls[render] = st_all.wall_s
        print(f"[rg/capture] {dataset} {render}: {len(items)} items × {len(layers)} layers in {st_all.wall_s:.0f}s", flush=True)
    return walls


# ------------------------------------------------------------------ prompt-only forced choice
def collect_prompt_only(target: M.Target, dataset: str, items: list[dict[str, Any]], batch: int = G.LO_BATCH) -> int:
    todo = [it for it in items if f"po|{dataset}|{it['item_id']}" not in done_keys(PO_PATH)]
    if not todo:
        return 0
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(target.model.parameters()).device
    led = ledger("prompt_only")
    n = 0
    per = max(1, batch // 2)
    for s in range(0, len(todo), per):
        chunk = todo[s: s + per]
        heads = [GM.prompt_only_ids(tok, it) for it in chunk]
        rows, head_lens = [], []
        for it, head in zip(chunk, heads):
            for c in it["primary"]["candidates"]:
                rows.append(head + GM.encode(tok, c))
                head_lens.append(len(head))
        with timed_call() as st:
            with M.disable_adapter_ctx(target.model):
                lps_all = GM.teacher_forced_lp(target.model, rows, head_lens, pad, dev)
        for j, (it, head) in enumerate(zip(chunk, heads)):
            lps = lps_all[2 * j: 2 * j + 2]
            append_row(PO_PATH, {"key": f"po|{dataset}|{it['item_id']}", "module": MODULE, "dataset": dataset, "tag": it.get("tag"),
                                 "item_id": it["item_id"], "split": it["split"], "label": it["label"], "candidates": it["primary"]["candidates"],
                                 "lp": lps, "greedy": int(np.argmax(lps)), "lp_pos": lps[0], "lp_neg": lps[1], "lo": lps[0] - lps[1],
                                 "model_says_pos": bool(lps[0] > lps[1]), "n_head_tokens": len(head), "template": "fc", "created_at": now_iso()})
            n += 1
        led.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
    return n


# ------------------------------------------------------------------ reader LO on the test split (+ controls, pool-eval)
def derangement(n: int, rng: np.random.Generator) -> np.ndarray:
    """A seeded single n-cycle: no item meets its own state."""
    if n < 2:
        return np.arange(n)
    perm = rng.permutation(n)
    out = np.empty(n, dtype=int)
    for i in range(n):
        out[perm[i]] = perm[(i + 1) % n]
    return out


def pool_eval_items(items: list[dict[str, Any]], n: int = G.POOL_EVAL) -> list[dict[str, Any]]:
    pool = [it for it in items if it["split"] == "pool"]
    pos = [it for it in pool if it["label"] == 1][: n // 2]
    neg = [it for it in pool if it["label"] == 0][: n // 2]
    return pos + neg


def lo_key(reader: str, layer: int, render: str, item_id: str, cond: str = "natural") -> str:
    return f"{reader}|L{layer}|{render}|{'shuf|' if cond == 'shuf' else ''}{item_id}"


def collect_reader_lo(reader: Any, dataset: str, items: list[dict[str, Any]], layer: int, renders: tuple[str, ...] = G.RENDERS,
                      batch: int = G.LO_BATCH, controls: bool = True, pool_eval: int = G.POOL_EVAL, items_path: Path | None = None) -> int:
    """TEST rows at one read layer, both renders; shuffled (derangement) and state-free controls; at the reader's PRIMARY
    site (chat, PRIMARY_LAYER) the balanced pool-eval items too."""
    import torch

    test = [it for it in items if it["split"] == "test"]
    if not test:
        return 0
    primary = test[0]["primary"]
    pool_sub = pool_eval_items(items, pool_eval) if layer == G.PRIMARY_LAYER.get(reader.name) else []
    shas = rg_shas(items_path)
    n = 0
    for render in renders:
        X, idx = load_states(dataset, render, layer)
        pos_of = {iid: i for i, iid in enumerate(idx)}
        H = torch.from_numpy(X[[pos_of[it["item_id"]] for it in test]])
        conds: list[tuple[str, Any, list[dict[str, Any]], list[str]]] = [("natural", H, test, [it["item_id"] for it in test])]
        if controls:
            rng = np.random.default_rng(G.SHUFFLE_SEED + RC.stable_offset(f"{dataset}|{render}|L{layer}"))   # one independent derangement per cell
            perm = derangement(len(test), rng)
            conds.append(("shuf", H[torch.as_tensor(perm)], test, [test[j]["item_id"] for j in perm]))
        if pool_sub and render == G.PRIMARY_RENDER:
            conds.append(("pool_eval", torch.from_numpy(X[[pos_of[it["item_id"]] for it in pool_sub]]), pool_sub, [it["item_id"] for it in pool_sub]))
        for cond, Hc, its, state_ids in conds:
            keys = [lo_key(reader.name, layer, render, it["item_id"], cond) for it in its]
            if all(k in done_keys(LO_PATH) for k in keys):
                continue
            led = ledger(f"{'control' if cond == 'shuf' else 'lo'}_{reader.name}_L{layer}")
            pairs = [(it["primary"]["candidates"][0], it["primary"]["candidates"][1]) for it in its]
            with timed_call() as st:
                rows = reader.score(Hc, pairs, primary, layer, batch)
            for it, key, sid, r in zip(its, keys, state_ids, rows):
                if key in done_keys(LO_PATH):
                    continue
                append_row(LO_PATH, {"key": key, "module": MODULE, "reader": reader.name, "reader_family": reader.base_name, "layer": layer,
                                     "render": render, "condition": "natural" if cond == "pool_eval" else cond, "split": it["split"],
                                     "dataset": dataset, "tag": it.get("tag"), "sided": primary.get("sided"), "family": f"r:{dataset}",
                                     "item_id": it["item_id"], "state_item_id": sid, "label": it["label"], "cand_A": r["cand_A"], "cand_B": r["cand_B"],
                                     "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"], "unscorable": r["unscorable"], "templates": r["templates"],
                                     "format": r.get("format"), "layer_in_prompt": r.get("layer_in_prompt"), "marker_index": r.get("marker_index"),
                                     **{k: r[k] for k in ("lp_yes_A", "lp_no_A", "lp_yes_B", "lp_no_B") if k in r},
                                     "created_at": now_iso(), **shas})
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
        if controls:
            key = f"{reader.name}|L{layer}|{render}|{dataset}"
            if key not in done_keys(SF_PATH):
                led = ledger(f"control_{reader.name}_L{layer}")
                with timed_call() as st:
                    r = reader.score(H.mean(0, keepdim=True), [(primary["candidates"][0], primary["candidates"][1])], primary, layer, batch)[0]
                append_row(SF_PATH, {"key": key, "module": MODULE, "reader": reader.name, "layer": layer, "render": render, "dataset": dataset,
                                     "condition": "state_free", "n_states_in_mean": len(test), "mean_norm": float(H.mean(0).norm()),
                                     "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"], "unscorable": r["unscorable"], "created_at": now_iso()})
                led.add(0, 0, st.wall_s, st.peak_mem_gb)
    print(f"[rg/lo/{reader.name}/L{layer}] {dataset}: {n} rows", flush=True)
    return n


def collect_reader_noact(reader: Any, dataset: str, items: list[dict[str, Any]], layer: int, batch: int = G.LO_BATCH,
                         items_path: Path | None = None) -> int:
    """BRIEF_RG §10 (the Li control): the oracle reads the TEXT in place of the activation; test items, chat, primary site;
    rows keyed ``<reader>_noact|L<layer>|chat|<item_id>``."""
    test = [it for it in items if it["split"] == "test"]
    if not test:
        return 0
    primary = test[0]["primary"]
    name = f"{reader.name}_noact"
    keys = [lo_key(name, layer, G.PRIMARY_RENDER, it["item_id"]) for it in test]
    if all(k in done_keys(LO_PATH) for k in keys):
        return 0
    led = ledger(f"lo_{name}_L{layer}")
    shas = rg_shas(items_path)
    pairs = [(it["primary"]["candidates"][0], it["primary"]["candidates"][1]) for it in test]
    with timed_call() as st:
        rows = reader.score_noact([it["prompt_text"] for it in test], pairs, primary, layer, batch)
    n = 0
    for it, key, r in zip(test, keys, rows):
        if key in done_keys(LO_PATH):
            continue
        append_row(LO_PATH, {"key": key, "module": MODULE, "reader": name, "reader_family": "ao_noact", "layer": layer, "render": G.PRIMARY_RENDER,
                             "condition": "natural", "split": it["split"], "dataset": dataset, "tag": it.get("tag"), "sided": primary.get("sided"),
                             "family": f"r:{dataset}", "item_id": it["item_id"], "state_item_id": None, "label": it["label"], "cand_A": r["cand_A"],
                             "cand_B": r["cand_B"], "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"], "unscorable": r["unscorable"],
                             "templates": r["templates"], "format": r.get("format"), "layer_in_prompt": layer, "marker_index": None,
                             "created_at": now_iso(), **shas})
        n += 1
    led.add(0, 0, st.wall_s, st.peak_mem_gb)
    print(f"[rg/lo/{name}/L{layer}] {dataset}: {n} rows", flush=True)
    return n


# ------------------------------------------------------------------ phase T: text + activation (BRIEF_RG §11a)
TA_PATH = RG_DIR / "reader_lo_textact.jsonl"
POS_PATH = RG_DIR / "reader_lo_pos.jsonl"
POSP_PATH = RG_DIR / "pos_probe.jsonl"
POS_DIR = RG_DIR / "states_pos"


def _derive_followup_paths() -> None:
    global TA_PATH, POS_PATH, POSP_PATH, POS_DIR
    TA_PATH = RG_DIR / _suffix("reader_lo_textact")
    POS_PATH = RG_DIR / _suffix("reader_lo_pos")
    POSP_PATH = RG_DIR / _suffix("pos_probe")
    POS_DIR = RG_DIR / "states_pos"


def collect_reader_textact(reader: Any, dataset: str, items: list[dict[str, Any]], layer: int, renders: tuple[str, ...] = G.RENDERS,
                           batch: int = G.LO_BATCH, items_path: Path | None = None) -> int:
    """BRIEF_RG §11a: the oracle with the text in the prompt AND the activation (block ``layer`` of ``render``) at the placeholder;
    test items; rows keyed ``<reader>_textact|L<layer>|<render>|<item_id>`` in reader_lo_textact.jsonl."""
    import torch

    _derive_followup_paths()
    test = [it for it in items if it["split"] == "test"]
    if not test:
        return 0
    primary = test[0]["primary"]
    name = f"{reader.name}_textact"
    shas = rg_shas(items_path)
    n = 0
    for render in renders:
        keys = [lo_key(name, layer, render, it["item_id"]) for it in test]
        if all(k in done_keys(TA_PATH) for k in keys):
            continue
        X, idx = load_states(dataset, render, layer)
        pos_of = {iid: i for i, iid in enumerate(idx)}
        H = torch.from_numpy(X[[pos_of[it["item_id"]] for it in test]])
        led = ledger(f"lo_{name}_L{layer}_{render}")
        pairs = [(it["primary"]["candidates"][0], it["primary"]["candidates"][1]) for it in test]
        with timed_call() as st:
            rows = reader.score_textact(H, [it["prompt_text"] for it in test], pairs, primary, layer, batch)
        for it, key, r in zip(test, keys, rows):
            if key in done_keys(TA_PATH):
                continue
            append_row(TA_PATH, {"key": key, "module": MODULE, "reader": name, "reader_family": "ao_textact", "layer": layer, "render": render,
                                 "condition": "natural", "split": it["split"], "dataset": dataset, "tag": it.get("tag"), "sided": primary.get("sided"),
                                 "family": f"r:{dataset}", "item_id": it["item_id"], "state_item_id": it["item_id"], "label": it["label"],
                                 "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"],
                                 "unscorable": r["unscorable"], "templates": r["templates"], "format": r.get("format"), "layer_in_prompt": layer,
                                 "marker_index": r.get("marker_index"), "created_at": now_iso(), **shas})
            n += 1
        led.add(0, 0, st.wall_s, st.peak_mem_gb)
    print(f"[rg/textact/{name}/L{layer}] {dataset}: {n} rows", flush=True)
    return n


# ------------------------------------------------------------------ phase P: position sweep (BRIEF_RG §11b)
def chat_suffix_len(tokenizer: Any) -> int:
    """K = number of template tokens after the text in the chat render (offset K from the end = the last text token)."""
    probe_text = "hello world"
    head = GM.chat_ids(tokenizer, probe_text)[0]
    tid = GM.encode(tokenizer, probe_text)
    for s in range(len(head) - len(tid), -1, -1):
        if head[s: s + len(tid)] == tid:
            return len(head) - (s + len(tid))
    raise RuntimeError("could not locate the text inside the chat render")


def pos_state_file(dataset: str, layer: int, k: int) -> Path:
    return POS_DIR / dataset / f"chat_L{layer}_k{k}.npy"


def capture_positions(target: M.Target, dataset: str, items: list[dict[str, Any]], layers: tuple[int, ...] = G.POS_LAYERS,
                      batch: int = G.CAPTURE_BATCH) -> dict[str, Any]:
    """Chat render, offsets k = 0 (assistant onset) … K (last text token) at ``layers``; fp16 [N, d] per (layer, k) in index order."""
    import torch

    _derive_followup_paths()
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    items = ordered_items(items)
    K = chat_suffix_len(tok)
    offsets = list(range(K + 1))
    d = POS_DIR / dataset
    if d.exists() and all(pos_state_file(dataset, L, k).exists() for L in layers for k in offsets):
        return {"K": K, "skipped": True}
    d.mkdir(parents=True, exist_ok=True)
    acc: dict[tuple[int, int], list[Any]] = {(L, k): [] for L in layers for k in offsets}
    led = ledger("capture_positions", batch=batch, K=K)
    with timed_call() as st_all:
        for s in range(0, len(items), batch):
            chunk = items[s: s + batch]
            rows = [GM.render_ids(tok, it["prompt_text"], "chat") for it in chunk]
            positions = [[len(r) - 1 - k for k in offsets] for r in rows]
            order = sorted(range(len(rows)), key=lambda i: len(rows[i]))
            with timed_call() as st:
                got = RC.capture_batch_positions(target.model, [rows[i] for i in order], list(layers), pad, [positions[i] for i in order])
            inv = torch.as_tensor(np.argsort(order))
            for L in layers:
                h = got[L][inv]                     # [B, K+1, d]
                for j, k in enumerate(offsets):
                    acc[(L, k)].append(h[:, j, :])
            led.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
    for (L, k), parts in acc.items():
        np.save(pos_state_file(dataset, L, k), torch.cat(parts).to(torch.float16).numpy())
    (d / "index.json").write_text(json.dumps({"dataset": dataset, "item_ids": [it["item_id"] for it in items], "splits": [it["split"] for it in items],
                                              "labels": [it["label"] for it in items], "layers": list(layers), "offsets": offsets, "K": K,
                                              "suffix_tokens": tok.decode(GM.chat_ids(tok, "x")[0][-K:]) if K else "", "created_at": now_iso()}, indent=1))
    print(f"[rg/pos] {dataset}: {len(items)} items × {len(layers)} blocks × {K + 1} offsets in {st_all.wall_s:.0f}s", flush=True)
    return {"K": K, "wall_s": st_all.wall_s}


def collect_reader_positions(reader: Any, dataset: str, items: list[dict[str, Any]], layers: tuple[int, ...] = G.POS_LAYERS,
                             batch: int = G.LO_BATCH, items_path: Path | None = None) -> int:
    """The AO (candidate form) on the test items at every (block, offset) of the position sweep; keys ``ao|L<L>|chat|k<k>|<item>``."""
    import torch

    _derive_followup_paths()
    test = [it for it in items if it["split"] == "test"]
    if not test:
        return 0
    idx = json.loads((POS_DIR / dataset / "index.json").read_text())
    pos_of = {iid: i for i, iid in enumerate(idx["item_ids"])}
    rows_idx = [pos_of[it["item_id"]] for it in test]
    primary = test[0]["primary"]
    pairs = [(it["primary"]["candidates"][0], it["primary"]["candidates"][1]) for it in test]
    shas = rg_shas(items_path)
    n = 0
    for L in layers:
        for k in idx["offsets"]:
            keys = [f"{reader.name}|L{L}|chat|k{k}|{it['item_id']}" for it in test]
            if all(kk in done_keys(POS_PATH) for kk in keys):
                continue
            H = torch.from_numpy(np.load(pos_state_file(dataset, L, k)).astype(np.float32)[rows_idx])
            led = ledger(f"pos_{reader.name}_L{L}")
            with timed_call() as st:
                rows = reader.score(H, pairs, primary, L, batch)
            for it, key, r in zip(test, keys, rows):
                if key in done_keys(POS_PATH):
                    continue
                append_row(POS_PATH, {"key": key, "module": MODULE, "reader": reader.name, "layer": L, "render": "chat", "offset": k, "condition": "natural",
                                      "split": "test", "dataset": dataset, "tag": it.get("tag"), "sided": primary.get("sided"), "item_id": it["item_id"],
                                      "label": it["label"], "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"],
                                      "unscorable": r["unscorable"], "created_at": now_iso(), **shas})
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
    print(f"[rg/pos/{reader.name}] {dataset}: {n} rows", flush=True)
    return n


def pos_probes(dataset: str, layers: tuple[int, ...] = G.POS_LAYERS, seed: int = 0) -> int:
    """LR probe (analyze.probe_fit_select) fitted on the pool at every (block, offset); per-item test decision values saved
    so the Mac can run the item-paired bootstrap without the states; keys ``probe|L<L>|chat|k<k>|<dataset>``."""
    from projects.g_agreement.r_bench.analyze import auroc, probe_fit_select

    _derive_followup_paths()
    idx = json.loads((POS_DIR / dataset / "index.json").read_text())
    y = np.array(idx["labels"], dtype=int)
    split = np.array(idx["splits"])
    pool, test = np.where(split == "pool")[0], np.where(split == "test")[0]
    n = 0
    for L in layers:
        for k in idx["offsets"]:
            key = f"probe|L{L}|chat|k{k}|{dataset}"
            if key in done_keys(POSP_PATH):
                continue
            X = np.load(pos_state_file(dataset, L, k)).astype(np.float32)
            with timed_call() as st:
                clf, Cv, val = probe_fit_select(X[pool], y[pool], seed)
                dec = clf.decision_function(X[test])
            append_row(POSP_PATH, {"key": key, "module": MODULE, "dataset": dataset, "layer": L, "render": "chat", "offset": k, "n_pool": int(len(pool)),
                                   "C": Cv, "val_auc": val, "test_auroc": auroc(y[test], dec), "item_ids": [idx["item_ids"][i] for i in test],
                                   "labels": [int(v) for v in y[test]], "scores": [float(v) for v in dec], "wall_s": st.wall_s, "created_at": now_iso()})
            n += 1
    print(f"[rg/pos-probe] {dataset}: {n} cells", flush=True)
    return n


# ------------------------------------------------------------------ phase F: FT-3 arm tensors (BRIEF_RG §12)
FT3_PATH = RG_DIR / "reader_lo_ft3.jsonl"


def collect_reader_files(reader: Any, ft3_dir: Path, items_by_id: dict[str, dict[str, Any]], layer: int = 21, batch: int = G.LO_BATCH,
                         items_path: Path | None = None) -> int:
    """Score every <ft3_dir>/<arm>/<fact>.npy (+ .ids.json) with the oracle at ``layer``; rows keyed ``<reader>|L<layer>|ft3:<arm>|<item_id>``."""
    import torch

    global FT3_PATH
    FT3_PATH = RG_DIR / _suffix("reader_lo_ft3")
    shas = rg_shas(items_path)
    n = 0
    for arm_dir in sorted(p for p in Path(ft3_dir).iterdir() if p.is_dir()):
        arm = arm_dir.name
        for f in sorted(arm_dir.glob("*.npy")):
            fact = f.stem
            ids = json.loads(f.with_suffix(".ids.json").read_text())
            keys = [f"{reader.name}|L{layer}|ft3:{arm}|{iid}" for iid in ids]
            if all(k in done_keys(FT3_PATH) for k in keys):
                continue
            its = [items_by_id[i] for i in ids]
            H = torch.from_numpy(np.load(f).astype(np.float32))
            primary = its[0]["primary"]
            pairs = [(it["primary"]["candidates"][0], it["primary"]["candidates"][1]) for it in its]
            led = ledger(f"ft3_{reader.name}_{arm}")
            with timed_call() as st:
                rows = reader.score(H, pairs, primary, layer, batch)
            for it, key, r in zip(its, keys, rows):
                if key in done_keys(FT3_PATH):
                    continue
                append_row(FT3_PATH, {"key": key, "module": MODULE, "reader": reader.name, "layer": layer, "render": "chat", "arm": arm,
                                      "condition": "natural", "split": it["split"], "dataset": fact, "tag": it.get("tag"), "sided": primary.get("sided"),
                                      "item_id": it["item_id"], "label": it["label"], "cand_A": r["cand_A"], "cand_B": r["cand_B"],
                                      "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"], "unscorable": r["unscorable"], "created_at": now_iso(), **shas})
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
            print(f"[rg/ft3/{arm}] {fact}: {len(rows)} rows", flush=True)
    return n


# ------------------------------------------------------------------ phase S: SAE latents
def sae_file_path(dataset: str, render: str, tag: str, layer: int | None = None) -> Path:
    layer = G.SAE_LAYER if layer is None else layer
    return SAE_DIR / dataset / f"{render}_L{layer}_{tag}.npz"


def collect_sae(dataset: str, saes: dict[str, Any], renders: tuple[str, ...] = G.RENDERS, device: str = "cpu", layer: int | None = None) -> int:
    from projects.r_gemma import sae as S

    layer = G.SAE_LAYER if layer is None else layer

    n = 0
    for render in renders:
        if not state_file(dataset, render, layer).exists():
            continue
        X, idx = load_states(dataset, render, layer)
        splits = json.loads(index_file(dataset).read_text())["splits"]
        test_rows = [i for i, s in enumerate(splits) if s == "test"]
        for tag, sae in saes.items():
            out = sae_file_path(dataset, render, tag, layer)
            key = f"fve|{dataset}|{render}|{tag}"
            if out.exists() and key in done_keys(FVE_PATH):
                continue
            led = ledger(f"sae_{tag}")
            with timed_call() as st:
                Z = sae.encode(X, device)
                S.save_sparse(out, S.to_csr(Z), idx)
                fve = sae.fve(X[test_rows], device)
            if key not in done_keys(FVE_PATH):
                append_row(FVE_PATH, {"key": key, "module": MODULE, "dataset": dataset, "render": render, "sae": tag, "layer": layer,
                                      "path": G.SAES[tag]["path"] if tag in G.SAES else None, **fve,
                                      "flag_low_fve": bool(fve["fve"] < G.SAE_FVE_FLAG), "created_at": now_iso()})
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
            n += 1
    print(f"[rg/sae] {dataset}: {n} (render, sae) files", flush=True)
    return n


# ------------------------------------------------------------------ readers and main
def bind_readers(target: M.Target, names: list[str]) -> list[Any]:
    from projects.r_gemma.oracle import AOReader

    readers: list[Any] = []
    led = ledger("load_ao")
    with timed_call() as st:
        base = AOReader("ao").bind(target)
    led.add(0, 0, st.wall_s, st.peak_mem_gb)
    rlog(f"ao adapter={base.adapter_dir} special_id={base.special_id} ao_config_grid={base.ao_config.get('act_layer_combinations')}")
    if "ao" in names:
        readers.append(base)
    if "ao_yn" in names:
        yn = AOReader("ao_yn")
        yn.adapter_dir, yn.ao_config = base.adapter_dir, base.ao_config
        yn.attach(target)
        readers.append(yn)
    return readers


def load_target_timed() -> M.Target:
    led = ledger("load_target")
    with timed_call() as st:
        t = GM.load_target()
    led.add(0, 0, st.wall_s, st.peak_mem_gb)
    print(f"loaded {t.model_class} ({t.n_layers} blocks) in {st.wall_s:.0f}s", flush=True)
    return t


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "S", "T", "P", "F"], default=None, help="A capture+readers, S SAE latents, T text+activation (§11a), P position sweep (§11b), F FT-3 arm files (§12)")
    ap.add_argument("--ft3-dir", default=None, help="phase F: folder of <arm>/<fact>.npy (+ .ids.json) state files")
    ap.add_argument("--pos-probes-only", action="store_true", help="phase P: only the on-pod LR probes (states already captured)")
    ap.add_argument("--probe-jobs", type=int, default=1, help="phase P: parallel datasets for the probes")
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--items-file", default=None)
    ap.add_argument("--renders", nargs="*", default=list(G.RENDERS))
    ap.add_argument("--readers", nargs="*", default=list(G.READERS))
    ap.add_argument("--ao-layers", nargs="*", type=int, default=None, help="override the AO read layers (both renders)")
    ap.add_argument("--saes", nargs="*", default=list(G.SAES), help="phase S: SAE tags (config.SAES)")
    ap.add_argument("--device", default=None, help="phase S device (default cuda if available)")
    ap.add_argument("--no-controls", action="store_true")
    ap.add_argument("--no-noact", action="store_true", help="skip the no-activation oracle arm (BRIEF_RG §10)")
    ap.add_argument("--no-rot", action="store_true", help="skip the random-rotation logit-lens margins (BRIEF_RG §10)")
    ap.add_argument("--batch", type=int, default=G.LO_BATCH)
    ap.add_argument("--capture-batch", type=int, default=G.CAPTURE_BATCH)
    ap.add_argument("--cache-dir", default=None)
    ap.add_argument("--shard", default=None, help="PLAN_R §9: k/N; outputs *.k.jsonl")
    ap.add_argument("--pod", default=None)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--freeze-rg", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    items_path = Path(a.items_file) if a.items_file else B.ITEMS_R
    if a.freeze_rg:
        print(f"wrote {freeze_rg(force=a.force, items_path=items_path)}")
        return 0
    if a.phase is None:
        ap.error("--phase A|S|T|P|F is required (or --freeze-rg)")
    require_frozen_rg(a.allow_unfrozen, items_path)
    shard = parse_shard(a.shard)
    set_shard(shard)
    set_run_meta(a.pod, shard)
    if a.cache_dir:
        set_cache_dir(Path(a.cache_dir))
    elif a.allow_unfrozen:
        set_cache_dir(C.CACHE_DIR / "rg_unfrozen")
    items_all = B.load_items(items_path, "all")
    mine = set(shard_datasets([it["dataset"] for it in items_all], shard))
    items = [it for it in items_all if it["dataset"] in mine and (not a.datasets or it["dataset"] in a.datasets)]
    if not items:
        raise SystemExit("no items selected")
    groups = RC.items_by_dataset(items)
    renders = tuple(a.renders)
    RG_DIR.mkdir(parents=True, exist_ok=True)
    rlog(f"phase {a.phase}: run={RUN_META} {len(groups)} datasets, {len(items)} items, renders={renders}, items={items_path.name}, "
         f"cache={RG_DIR}, readers={a.readers}, shas={rg_shas(items_path)}")
    try:
        if a.phase == "A":
            target = load_target_timed()
            with timed_call() as st_all:
                for ds, its in groups.items():
                    with timed_call() as st:
                        walls = capture_dataset(target, ds, its, renders, G.LAYERS, a.capture_batch, rot_seeds=() if a.no_rot else None)
                        n_po = collect_prompt_only(target, ds, its, batch=a.batch)
                    rlog(f"{ds}: {len(its)} items; capture {walls}; prompt_only {n_po} new rows; {st.wall_s:.0f}s")
            rlog(f"capture + prompt_only: {len(groups)} datasets in {st_all.wall_s / 60:.1f} min")
            for rd in bind_readers(target, a.readers):
                for render in renders:
                    layers = tuple(a.ao_layers) if a.ao_layers else G.AO_READ_LAYERS[render]
                    for L in layers:
                        with timed_call() as st:
                            n = sum(collect_reader_lo(rd, ds, its, L, (render,), a.batch, controls=not a.no_controls, items_path=items_path)
                                    for ds, its in groups.items())
                        rlog(f"lo {rd.name} L{L} {render}: {n} new rows, {st.wall_s:.0f}s")
                if not a.no_noact:
                    Lp = G.PRIMARY_LAYER[rd.name]
                    with timed_call() as st:
                        n = sum(collect_reader_noact(rd, ds, its, Lp, a.batch, items_path=items_path) for ds, its in groups.items())
                    rlog(f"lo {rd.name}_noact L{Lp} chat: {n} new rows, {st.wall_s:.0f}s")
            M.unload(target)
        elif a.phase == "F":
            target = load_target_timed()
            by_id = {it["item_id"]: it for it in items_all}
            ft3_dir = Path(a.ft3_dir) if a.ft3_dir else RG_DIR / "ft3"
            for rd in bind_readers(target, ["ao"]):
                with timed_call() as st:
                    n = collect_reader_files(rd, ft3_dir, by_id, 21, a.batch, items_path=items_path)
                rlog(f"ft3 {rd.name} L21: {n} new rows from {ft3_dir}, {st.wall_s / 60:.1f} min")
            M.unload(target)
        elif a.phase == "T":
            target = load_target_timed()
            for rd in bind_readers(target, a.readers):
                Lp = G.PRIMARY_LAYER[rd.name]
                with timed_call() as st:
                    n = sum(collect_reader_textact(rd, ds, its, Lp, renders, a.batch, items_path=items_path) for ds, its in groups.items())
                rlog(f"textact {rd.name} L{Lp} {renders}: {n} new rows, {st.wall_s:.0f}s")
            M.unload(target)
        elif a.phase == "P":
            _derive_followup_paths()
            if not a.pos_probes_only:
                target = load_target_timed()
                with timed_call() as st:
                    info = [capture_positions(target, ds, its, G.POS_LAYERS, a.capture_batch) for ds, its in groups.items()]
                rlog(f"positions captured: {len(groups)} datasets, K={info[0].get('K')}, {st.wall_s / 60:.1f} min")
                for rd in bind_readers(target, ["ao"]):
                    with timed_call() as st:
                        n = sum(collect_reader_positions(rd, ds, its, G.POS_LAYERS, a.batch, items_path=items_path) for ds, its in groups.items())
                    rlog(f"positions AO: {n} new rows, {st.wall_s / 60:.1f} min")
                M.unload(target)
            from joblib import Parallel, delayed

            with timed_call() as st:
                ns = Parallel(n_jobs=a.probe_jobs)(delayed(pos_probes)(ds, G.POS_LAYERS) for ds in groups)
            rlog(f"positions probes: {sum(ns)} cells over {len(groups)} datasets, {st.wall_s / 60:.1f} min")
        else:
            import torch

            from projects.r_gemma import sae as S

            device = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
            saes = {}
            for tag in a.saes:
                with timed_call() as st:
                    saes[tag] = S.load_sae(tag)
                rlog(f"sae {tag}: {G.SAES[tag]['path']} F={saes[tag].n_latents} loaded in {st.wall_s:.0f}s")
            ready = [ds for ds in groups if state_file(ds, "chat", G.SAE_LAYER).exists()]
            rlog(f"phase S: {len(ready)}/{len(groups)} datasets have block-{G.SAE_LAYER} states; device={device}")
            for ds in ready:
                collect_sae(ds, saes, renders, device)
    finally:
        rows = flush_ledgers()
        rlog(f"phase {a.phase} done: {len(rows)} ledger rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
