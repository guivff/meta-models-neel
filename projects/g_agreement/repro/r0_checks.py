"""R0 reproduction checks (GPU). Each check is reported separately, with numbers, into
``results/g_agreement/repro/r0.json`` (merged per key, so checks can run in separate invocations
and phases):

  k0           layer convention on the 64 shipped NLA example activations: recompute the block
               41/42/43 output at the extraction position and compare with the shipped vector
               (median cosine, mean relative L2, token-count agreement) next to Suraj's reference
               numbers (third_party/mats-nla-workspace-main/experiments/00_nla_gate/RESULTS.md).
               Pass rule: block 42 wins AND median cos >= 0.999 AND mean rel-L2 <= 0.05. [phase A]
  olens        positive control: "The capital of France is Paris." read at a few positions at
               layers 42 and 44 (printed + stored).                              [phase A]
  nla          positive control: verbalize 4 shipped activations next to their source text, plus
               one dimension-shuffled vector as a contrast.                      [phase B]
  bench_capture capture the read cells of one regex family (``--family``, default typo_mt) at
               layer 42 with the target model, through wsbench's own read plan and render.  [A]
  bench_olens  wsbench ``--family`` @ L42 with the wsbench OLens method on the loaded model,
               regex-judged offline; compared with Suraj's matched-layer L42 values.   [phase A]
  bench_nla    the same for NLA, from the cached cells (wsbench NLA class by default, or
               ``--own-reader``).                                                 [phase B]
  inputs       the COMPLETE input each reader receives for one dev item ->
               ``results/g_agreement/repro/inputs_dump.json`` (olens+jlens in A, nla in B).
  lens_meta    the J-lens file's source_layers (is 42 fitted?) and the OLens grid note. [phase A]

``--batch N`` (default 1 = the faithful wsbench batch-1 path) batches the bench verbalizations
across cells as Suraj's ``OLensBatched`` / ``NLABatched`` do (equal-length carrier prompts, no
padding, per-row vector in the NLA hook; he used 64 / 50). ``--check`` greedily decodes 4 cells
both ways and reports whether the outputs match (his: identical except the last tokens).
The G1–G4 collectors are untouched (batch 1, per-call seeds).

    python -m projects.g_agreement.repro.r0_checks --phase A --checks k0,olens,lens_meta,inputs,bench_capture,bench_olens --limit 100
    python -m projects.g_agreement.repro.r0_checks --phase A --checks bench_capture,bench_olens --family multihop_mt --batch 64 --check
    python -m projects.g_agreement.repro.r0_checks --phase B --checks nla,inputs
    python -m projects.g_agreement.repro.r0_checks --phase B --checks bench_nla --limit 100 --batch 50 --check

Cost: the two bench arms are the expensive part (100 items × 256-token verbalizations each per
family at batch 1); ``--limit`` cuts them, ``--batch`` speeds them ~10x.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import states as S
from projects.g_agreement.core.accounting import StepLedger, now_iso, timed_call

R0_JSON = C.REPRO_DIR / "r0.json"
INPUTS_JSON = C.REPRO_DIR / "inputs_dump.json"
BENCH_OUT = C.RESULTS_DIR / "repro" / "bench"
FAMILIES = ("typo_mt", "multilingual_mt", "multihop_mt", "basic_readout_mt")
DEFAULT_FAMILY = "typo_mt"  # L42 rates far from floor -> the sharpest setup check
SURAJ_REPO = "third_party/mats-nla-workspace-main"
SURAJ_01 = f"{SURAJ_REPO}/experiments/01_wsbench_replication/RESULTS.md"
SURAJ_00 = f"{SURAJ_REPO}/experiments/00_nla_gate/RESULTS.md"

# Comparison targets: Suraj's single-layer L42 regex pass rates ("Matched-layer comparison" table
# of SURAJ_01; n=100 each, 95% bootstrap CI, k=1 sample per cell, 256-token cap, batched 64/50),
# plus the published README grid values (olens: best over the 11-layer grid; nla: L42) for context.
RECORDED = {
    "source": SURAJ_01,
    "olens_L42": {"typo_mt": (0.76, [0.68, 0.84]), "multilingual_mt": (0.28, [0.20, 0.37]),
                  "multihop_mt": (0.10, [0.04, 0.17]), "basic_readout_mt": (0.45, [0.35, 0.54])},
    "nla_L42": {"typo_mt": (0.73, [0.64, 0.81]), "multilingual_mt": (0.42, [0.33, 0.52]),
                "multihop_mt": (0.15, [0.08, 0.22]), "basic_readout_mt": (0.57, [0.47, 0.66])},
    "published_readme_grid": {  # workspace-bench README values (olens any-of-11-layers; nla L42)
        "olens": {"typo_mt": 0.83, "multilingual_mt": 0.62, "multihop_mt": 0.32, "basic_readout_mt": 0.71},
        "nla": {"typo_mt": 0.75, "multilingual_mt": 0.44, "multihop_mt": 0.22, "basic_readout_mt": 0.53},
        "prompt_only_floor": {"typo_mt": 0.67, "multilingual_mt": 0.42, "multihop_mt": 0.69, "basic_readout_mt": 0.59},
    },
    "notes": ["olens L42 is off its training grid; Suraj's L40/L44 values agree within ~0.05 on every family",
              "nla: enable_thinking=True (EasyNLA default open <think>) leaves 205/256 = 80% of samples without a "
              "closed </explanation> within 256 tokens (SURAJ_00); our prompt uses enable_thinking=False, the trained contract"],
}

# K0 reference (SURAJ_00, H100 bf16, one sequence per forward, add_special_tokens=True, 64/64 token counts match)
K0_REFERENCE = {
    "source": SURAJ_00,
    "token_count_match": "64/64",
    "by_layer": {"41": {"median_cos": 0.979, "mean_rel_l2": 0.222},
                 "42": {"median_cos": 0.9999, "mean_rel_l2": 0.026},
                 "43": {"median_cos": 0.979, "mean_rel_l2": 0.232}},
    "note": "6/64 examples have rel-L2 > 0.05 (worst 0.23) in bf16 AND fp32: tokenisation/context drift of the "
            "detokenized text, not kernel noise. Hooks on blocks 41/42 equal hidden_states[42]/[43] bit for bit.",
}
K0_PASS = {"winning_block": C.LAYER, "min_median_cos": 0.999, "max_mean_rel_l2": 0.05}


def recorded_for(arm: str, family: str) -> dict[str, Any]:
    v, ci = RECORDED[f"{arm}_L42"][family]
    return {"suraj_L42": v, "suraj_L42_ci95": ci, "suraj_n": 100,
            "published_readme": RECORDED["published_readme_grid"][arm][family],
            "published_readme_protocol": "best over the 11-layer grid" if arm == "olens" else "L42",
            "prompt_only_floor": RECORDED["published_readme_grid"]["prompt_only_floor"][family],
            "source": RECORDED["source"]}


def _load_r0() -> dict[str, Any]:
    return json.loads(R0_JSON.read_text()) if R0_JSON.exists() else {}


def _save_r0(key: str, value: Any) -> None:
    C.REPRO_DIR.mkdir(parents=True, exist_ok=True)
    d = _load_r0()
    d[key] = value
    d["_updated"] = now_iso()
    d.setdefault("_env", C.env_summary())
    R0_JSON.write_text(json.dumps(d, indent=1, ensure_ascii=False, default=str) + "\n")
    print(f"[r0] wrote {key} -> {R0_JSON}", flush=True)


def _merge_json(path: Path, key: str, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    d = json.loads(path.read_text()) if path.exists() else {}
    d[key] = value
    path.write_text(json.dumps(d, indent=1, ensure_ascii=False, default=str) + "\n")


def nla_examples() -> Any:
    import pandas as pd
    from huggingface_hub import hf_hub_download

    local = C.G_ASSETS_DIR / "ceselder__qwen3.6-27b-nla-rl" / C.NLA_EXAMPLES_FILE
    p = local if local.exists() else Path(hf_hub_download(C.NLA_REPO, C.NLA_EXAMPLES_FILE, revision=C.NLA_SHA))
    return pd.read_parquet(p)


# ================================================================== (a) K0
def k0_verdict(summary: dict[str, Any]) -> dict[str, Any]:
    by = summary["by_layer"]
    best = max(by, key=lambda L: by[L]["median_cos"])
    at42 = by[str(C.LAYER)]
    checks = {"block_42_wins": int(best) == K0_PASS["winning_block"],
              "median_cos_ge_0.999": at42["median_cos"] >= K0_PASS["min_median_cos"],
              "mean_rel_l2_le_0.05": at42["mean_rel_l2"] <= K0_PASS["max_mean_rel_l2"]}
    return {"winning_block": int(best), "checks": checks, "pass": all(checks.values()), "rule": K0_PASS}


def check_k0(target: M.Target, n_rows: int = 64, layers: tuple[int, ...] = (41, 42, 43)) -> dict[str, Any]:
    """The NLA extractor tokenised the plain text with add_special_tokens=True (no chat
    template) and took the block-42 output at position n_raw_tokens-1 (= last token of
    ``detokenized_text_truncated``)."""
    import numpy as np
    import torch

    df = nla_examples().head(n_rows)
    tok = target.tokenizer
    per_layer = {L: {"cos": [], "rel_l2": []} for L in layers}
    n_tok_match = 0
    ledger = StepLedger(step="r0_k0", module="repro")
    rows_out = []
    for i, r in df.iterrows():
        text = r["detokenized_text_truncated"]
        ids = tok(text, add_special_tokens=True)["input_ids"]
        n_tok_match += int(len(ids) == int(r["n_raw_tokens"]))
        shipped = torch.tensor(np.asarray(r["activation_vector"], dtype=np.float32))
        with timed_call() as st:
            acts = M.capture(target.model, ids, list(layers), [len(ids) - 1])
        ledger.add(len(ids), 0, st.wall_s, st.peak_mem_gb)
        row = {"i": int(i), "n_ids": len(ids), "n_raw_tokens": int(r["n_raw_tokens"]), "shipped_norm": float(shipped.norm())}
        for L in layers:
            h = acts[L][0]
            cos = float(torch.nn.functional.cosine_similarity(h, shipped, dim=0))
            rel = float((h - shipped).norm() / shipped.norm().clamp_min(1e-9))
            per_layer[L]["cos"].append(cos)
            per_layer[L]["rel_l2"].append(rel)
            row[f"cos_L{L}"] = round(cos, 6)
            row[f"rel_l2_L{L}"] = round(rel, 6)
        rows_out.append(row)
    ledger.flush()
    summary: dict[str, Any] = {
        "n_rows": len(df), "token_count_match": f"{n_tok_match}/{len(df)}",
        "tokenisation": "add_special_tokens=True, plain text, no chat template, position = last token",
        "by_layer": {str(L): {"median_cos": float(np.median(v["cos"])), "mean_cos": float(np.mean(v["cos"])),
                              "min_cos": float(np.min(v["cos"])), "mean_rel_l2": float(np.mean(v["rel_l2"])),
                              "median_rel_l2": float(np.median(v["rel_l2"])), "max_rel_l2": float(np.max(v["rel_l2"]))}
                     for L, v in per_layer.items()},
        "reference": K0_REFERENCE,
    }
    summary.update(k0_verdict(summary))
    summary["rows"] = rows_out
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))
    return summary


# ================================================================== (b) OLens positive control
def check_olens_positive(target: M.Target, olens: R.OLensReader, text: str = "The capital of France is Paris.",
                         positions: tuple[int, ...] = (2, 5, -1), layers: tuple[int, ...] = (42, 44)) -> dict[str, Any]:
    tok = target.tokenizer
    ids = tok(text, add_special_tokens=False)["input_ids"]
    pos = [p % len(ids) for p in positions]
    acts = M.capture(target.model, ids, list(layers), pos)
    out = {"text": text, "token_ids": ids, "tokens": [tok.decode([i]) for i in ids], "positions": pos, "reads": []}
    for L in layers:
        for j, p in enumerate(pos):
            res = olens.read(acts[L][j], L, seed=C.stable_seed("r0", "olens", f"{L}:{p}", 0))
            rec = {"layer": L, "pos": p, "token": tok.decode([ids[p]]), "output": res.raw_output.strip(),
                   "n_new_tokens": res.n_new_tokens, "finish_reason": res.finish_reason, "wall_s": res.wall_s}
            print(f"[olens L{L} @{p} {rec['token']!r}] {rec['output'][:300]!r}")
            out["reads"].append(rec)
    return out


# ================================================================== (c) NLA positive control
def check_nla_positive(nla: R.NLAReader, n: int = 4, shuffle_seed: int = 0) -> dict[str, Any]:
    import numpy as np
    import torch

    df = nla_examples().head(n)
    out: dict[str, Any] = {"reads": [], "shuffled": None,
                           "thinking_note": "prompt rendered with enable_thinking=False (trained contract); with "
                                            "enable_thinking=True 80% of samples never close </explanation> (SURAJ_00)"}
    for i, r in df.iterrows():
        h = torch.tensor(np.asarray(r["activation_vector"], dtype=np.float32))
        res = nla.read(h, C.LAYER, seed=C.stable_seed("r0", "nla", f"ex{i}", 0))
        src = r["detokenized_text_truncated"]
        rec = {"i": int(i), "source_tail": src[-400:], "explanation": res.native["samples"][0],
               "raw_output": res.raw_output, "n_new_tokens": res.n_new_tokens, "finish_reason": res.finish_reason,
               "explanation_closed": res.native["explanation_closed"], "activation_norm": float(h.norm())}
        print(f"\n[nla ex{i}] SOURCE ...{src[-200:]!r}\n           EXPL {rec['explanation'][:400]!r}")
        out["reads"].append(rec)
    g = torch.Generator().manual_seed(shuffle_seed)
    h0 = torch.tensor(np.asarray(df.iloc[0]["activation_vector"], dtype=np.float32))
    hs = h0[torch.randperm(h0.numel(), generator=g)]
    res = nla.read(hs, C.LAYER, seed=C.stable_seed("r0", "nla", "shuffled0", 0))
    out["shuffled"] = {"from_i": int(df.index[0]), "permutation_seed": shuffle_seed,
                       "explanation": res.native["samples"][0], "raw_output": res.raw_output,
                       "n_new_tokens": res.n_new_tokens, "finish_reason": res.finish_reason}
    print(f"\n[nla SHUFFLED ex0] {out['shuffled']['explanation'][:400]!r}")
    return out


# ================================================================== (d) bench reproduction
def _wsbench():
    C.add_third_party_to_path()
    import wsbench.produce as wp
    from wsbench import readplan

    return wp, readplan


def cells_path(family: str) -> Path:
    return C.BENCH_DIR / f"{family}_L{C.LAYER}_cells.pt"


def bench_specs(family: str, limit: int):
    _wp, readplan = _wsbench()
    return readplan.plan(family)[: limit or None]


def check_bench_capture(target: M.Target, family: str, limit: int) -> dict[str, Any]:
    """Render each item exactly as wsbench does and capture its L42 cell (cached per family)."""
    import torch

    wp, readplan = _wsbench()
    from wsbench.produce.producer import _positions

    specs = bench_specs(family, limit)
    p = cells_path(family)
    cells: dict[str, Any] = torch.load(p) if p.exists() else {}
    ledger = StepLedger(step="bench_repro", module="repro", extra={"what": f"capture {family} L{C.LAYER}"})
    for spec in specs:
        if spec.id in cells:
            continue
        rendered = wp.render(spec, target.tokenizer)
        pos = _positions(spec.positions, rendered.tokens)
        if len(pos) != 1:
            raise RuntimeError(f"{spec.id}: expected one read position, got {pos}")
        idx = pos[0] % len(rendered)
        with timed_call() as st:
            acts = M.capture(target.model, rendered.ids, [C.LAYER], [idx])
        ledger.add(len(rendered.ids), 0, st.wall_s, st.peak_mem_gb)
        cells[spec.id] = {"pos": pos[0], "idx": idx, "token": rendered.decoded[idx], "render": rendered.render,
                          "n_ids": len(rendered.ids), "h": acts[C.LAYER][0].clone()}
    p.parent.mkdir(parents=True, exist_ok=True)
    torch.save(cells, p)
    ledger.flush()
    return {"n_cells": len(cells), "path": str(p), "layer": C.LAYER, "family": family}


def make_batched_methods():
    """Ports of Suraj's ``OLensBatched`` / ``NLABatched`` (third_party/mats-nla-workspace-main/
    experiments/01_wsbench_replication/produce_modal.py): equal-length carrier prompts, no padding,
    per-row vector in the NLA hook. Same arithmetic as the wsbench batch-1 ``read``."""
    import torch

    wp, _ = _wsbench()
    from wsbench.produce.methods import Readout

    class OLensBound(wp.OLens):
        """wsbench OLens whose adapter is already mounted on backend.model (our OLensReader.bind
        mounted the same olens_s3d_rl600 LoRA from the model repo)."""

        def bind(self, backend):
            self._b = backend

        def read_batch(self, hs, layers):
            b = self._b
            carriers = [self._carrier(L) for L in layers]
            if len({len(ids) for ids, _ in carriers}) != 1:  # never padded
                return [self.read(h, L) for h, L in zip(hs, layers)]
            embed = b.model.get_input_embeddings()
            with torch.no_grad():
                e = embed(torch.tensor([ids for ids, _ in carriers], device=b.device)).clone()
                for i, ((_, slot), h) in enumerate(zip(carriers, hs)):
                    v = h.to(b.device).float()
                    e[i, slot, :] = (self.alpha * v / v.norm().clamp_min(1e-9)).to(e.dtype)
                s = self.sampling
                out = b.model.generate(
                    inputs_embeds=e, attention_mask=torch.ones(e.shape[:2], device=b.device, dtype=torch.long),
                    do_sample=s.temperature > 0, temperature=max(s.temperature, 1e-5), top_p=s.top_p, top_k=s.top_k,
                    max_new_tokens=s.max_new_tokens, num_return_sequences=s.k,
                    pad_token_id=b.tokenizer.pad_token_id or b.tokenizer.eos_token_id)
            texts = [t.strip() for t in b.tokenizer.batch_decode(out, skip_special_tokens=True)]
            k = s.k
            return [Readout(samples=texts[i * k:(i + 1) * k]) for i in range(len(hs))]

    class NLABatched(wp.NLA):
        """wsbench NLA with a per-row hook so a batch of cells shares one generate."""

        def bind(self, backend):
            super().bind(backend)
            (block1,) = [m for n, m in self._reader.named_modules() if n.endswith("model.layers.1")]
            for hid, fn in list(block1._forward_hooks.items()):
                if "NLA.bind" in getattr(fn, "__qualname__", ""):
                    del block1._forward_hooks[hid]
            mp = self._marker

            def hook(_mod, _inp, out):
                h = out[0] if isinstance(out, tuple) else out
                v = self._vec.get("v")
                if v is None or h.shape[1] <= mp:
                    return out
                v = v.to(h.device)
                if v.ndim == 1:
                    v = v[None]
                hp = h[:, mp, :]
                vu = v.to(h.dtype) / (v.norm(dim=-1, keepdim=True) + 1e-9).to(h.dtype)
                h[:, mp, :] = hp + hp.norm(dim=-1, keepdim=True) * vu
                return out

            block1.register_forward_hook(hook)

        def read_batch(self, hs, layers):
            b, s = self._b, self.sampling
            self._vec["v"] = torch.stack([h.float() for h in hs]).repeat_interleave(s.k, dim=0)
            try:
                with torch.no_grad():
                    out = self._reader.generate(
                        torch.tensor([self._ids] * len(hs), device=b.device),
                        attention_mask=torch.ones(len(hs), len(self._ids), device=b.device, dtype=torch.long),
                        do_sample=s.temperature > 0, temperature=max(s.temperature, 1e-5), top_p=s.top_p, top_k=s.top_k,
                        max_new_tokens=s.max_new_tokens, num_return_sequences=s.k,
                        pad_token_id=self._tok.pad_token_id or self._tok.eos_token_id)
            finally:
                self._vec["v"] = None
            texts = self._tok.batch_decode(out[:, len(self._ids):], skip_special_tokens=True)
            texts = [t.split("</explanation>")[0].removeprefix("<explanation>").strip() for t in texts]
            k = s.k
            return [Readout(samples=texts[i * k:(i + 1) * k]) for i in range(len(hs))]

    return OLensBound, NLABatched


def read_cells(method: Any, cells: list[tuple[str, dict[str, Any]]], batch: int, seed_tag: str) -> list[dict[str, Any]]:
    """cells: [(id, cell)] -> contract rows. batch 1 = the method's own ``read``; the RNG is
    seeded once per chunk (per cell at batch 1) so a batch-1 run is reproducible."""
    import torch

    rows = []
    for i in range(0, len(cells), max(batch, 1)):
        chunk = cells[i:i + max(batch, 1)]
        hs = [c["h"] for _, c in chunk]
        torch.manual_seed(C.stable_seed("r0bench", seed_tag, chunk[0][0], i))
        if batch > 1 and hasattr(method, "read_batch"):
            outs = method.read_batch(hs, [C.LAYER] * len(hs))
        else:
            outs = [method.read(h, C.LAYER) for h in hs]
        for (iid, c), r in zip(chunk, outs):
            rows.append({"id": iid, "layer": C.LAYER, "pos": c["pos"], "token": c["token"], **r.row()})
    return rows


def greedy_check(method: Any, cells: list[tuple[str, dict[str, Any]]], n_cells: int = 4) -> dict[str, Any]:
    """Suraj's ``--check``: greedy decode the same cells with the batch-1 ``read`` and with
    ``read_batch``; report how many outputs are identical (his: olens 2/4, nla 1/2 identical,
    differences only in the last tokens of a 256-token generation = bf16 batch numerics)."""
    cells = cells[:n_cells]
    saved = method.sampling.temperature
    method.sampling.temperature = 0.0
    try:
        single = [method.read(c["h"], C.LAYER).samples[0] for _, c in cells]
        batched = [r.samples[0] for r in method.read_batch([c["h"] for _, c in cells], [C.LAYER] * len(cells))]
    finally:
        method.sampling.temperature = saved
    same = [a == b for a, b in zip(single, batched)]
    prefix = []
    for a, b in zip(single, batched):
        n = 0
        while n < min(len(a), len(b)) and a[n] == b[n]:
            n += 1
        prefix.append({"common_prefix_chars": n, "len_single": len(a), "len_batched": len(b)})
    return {"n": len(cells), "identical": sum(same), "prefix_agreement": prefix, "single": single, "batched": batched}


def judge(readouts: Path, arm: str, family: str) -> dict[str, Any]:
    """``wsbench judge family=<family> readouts=... layers=42 allow_missing=True`` (regex, offline)."""
    out = BENCH_OUT / arm / family
    out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "wsbench", "judge", f"family={family}", f"readouts={readouts}",
           f"layers={C.LAYER}", "allow_missing=True", f"out={out}"]
    env = dict(os.environ)
    env["PYTHONPATH"] = ":".join([str(p) for p in C.THIRD_PARTY_SRC] + [env.get("PYTHONPATH", "")])
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(C.THIRD_PARTY / "workspace-bench"))
    print(proc.stdout[-2000:], proc.stderr[-2000:])
    res_path = out / "results.json"
    res = json.loads(res_path.read_text()) if res_path.exists() else None
    value = None
    if res:
        value = (res.get("numbers") or {}).get("value", res.get("value"))
    return {"cmd": " ".join(cmd), "returncode": proc.returncode, "value": value,
            "results_json": str(res_path), "stdout_tail": proc.stdout[-500:]}


def _bench_cells(family: str, limit: int) -> list[tuple[str, dict[str, Any]]]:
    import torch

    p = cells_path(family)
    if not p.exists():
        raise SystemExit(f"{p} missing: run --phase A --checks bench_capture --family {family} first")
    cells = torch.load(p)
    ids = [s.id for s in bench_specs(family, limit)]
    missing = [i for i in ids if i not in cells]
    if missing:
        raise SystemExit(f"{len(missing)} cells of {family} not captured (first {missing[:3]}); re-run bench_capture")
    return [(i, cells[i]) for i in ids]


def _write_rows(out: Path, rows: list[dict[str, Any]]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _done(out: Path) -> set[str]:
    return {json.loads(l)["id"] for l in out.read_text().splitlines() if l.strip()} if out.exists() else set()


def check_bench_olens(target: M.Target, olens: R.OLensReader, family: str, limit: int, batch: int, check: bool) -> dict[str, Any]:
    wp, _ = _wsbench()
    OLensBound, _NLAB = make_batched_methods()
    backend = wp.Backend(model=target.model, tokenizer=target.tokenizer, device=target.device, model_id=target.model_id)
    method = OLensBound(sampling=wp.Sampling(max_new_tokens=C.BENCH_MAX_NEW_TOKENS))
    method.bind(backend)
    cells = _bench_cells(family, limit)
    rep: dict[str, Any] = {"family": family, "limit": limit, "batch": batch, "max_new_tokens": C.BENCH_MAX_NEW_TOKENS,
                           "sampling": "wsbench Sampling(T=1.0, top_p=0.95, top_k=64, k=1)", "adapter": str(olens.adapter_dir),
                           "recorded": recorded_for("olens", family)}
    if check:
        rep["greedy_check"] = greedy_check(method, cells)
        print(json.dumps({k: v for k, v in rep["greedy_check"].items() if k not in ("single", "batched")}))
    out = C.BENCH_DIR / "readouts" / f"olens_b{batch}" / f"{family}.jsonl"
    todo = [c for c in cells if c[0] not in _done(out)]
    ledger = StepLedger(step="bench_repro", module="repro", extra={"arm": "olens", "family": family, "batch": batch, "limit": limit})
    with timed_call() as st:
        rows = read_cells(method, todo, batch, "olens")
    _write_rows(out, rows)
    ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush()
    rep.update(readouts=str(out), n_new_rows=len(rows), wall_s=st.wall_s, judge=judge(out, f"olens_b{batch}", family))
    return rep


def check_bench_nla(family: str, limit: int, batch: int, check: bool, own_reader: bool, nla: R.NLAReader | None = None) -> dict[str, Any]:
    cells = _bench_cells(family, limit)
    rep: dict[str, Any] = {"family": family, "limit": limit, "batch": batch if not own_reader else 1,
                           "max_new_tokens": C.BENCH_MAX_NEW_TOKENS, "recorded": recorded_for("nla", family)}
    if own_reader:
        reader = nla or R.NLAReader(max_new_tokens=C.BENCH_MAX_NEW_TOKENS).bind()

        class _Own:
            sampling = None

            def read(self, h, layer):
                from wsbench.produce.methods import Readout

                return Readout(samples=[reader.read(h, layer, seed=None, max_new_tokens=C.BENCH_MAX_NEW_TOKENS).native["samples"][0]])

        method: Any = _Own()
        rep["adapter"] = f"{reader.adapter_dir} (core.readers.NLAReader, batch 1)"
        tag = "nla_own"
    else:
        wp, _ = _wsbench()
        _OL, NLABatched = make_batched_methods()
        method = NLABatched(sampling=wp.Sampling(max_new_tokens=C.BENCH_MAX_NEW_TOKENS))
        method.bind(wp.Backend(model=None, tokenizer=None, device="cuda", model_id=C.TARGET_MODEL_ID))
        rep["adapter"] = f"{C.NLA_REPO}/{C.NLA_ADAPTER_SUBFOLDER} (wsbench NLA class, per-row hook)"
        tag = f"nla_b{batch}"
        if check:
            rep["greedy_check"] = greedy_check(method, cells)
            print(json.dumps({k: v for k, v in rep["greedy_check"].items() if k not in ("single", "batched")}))
    out = C.BENCH_DIR / "readouts" / tag / f"{family}.jsonl"
    todo = [c for c in cells if c[0] not in _done(out)]
    ledger = StepLedger(step="bench_repro", module="repro", extra={"arm": "nla", "family": family, "batch": rep["batch"], "limit": limit})
    with timed_call() as st:
        rows = read_cells(method, todo, rep["batch"], "nla")
    _write_rows(out, rows)
    ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush()
    rep.update(readouts=str(out), n_new_rows=len(rows), wall_s=st.wall_s, judge=judge(out, tag, family))
    return rep


# ================================================================== (e) inputs dump + lens meta
def dev_item(item_id: str | None) -> dict[str, Any]:
    items = C.load_items("all")
    if item_id:
        (it,) = [i for i in items if i["item_id"] == item_id]
        return it
    dev = [i for i in items if i["split"] == "dev"]
    return dev[0] if dev else items[0]


def dump_capture_input(target: M.Target, item: dict[str, Any]) -> dict[str, Any]:
    ids = M.render_item(target.tokenizer, item["prompt_text"], item.get("system"))
    h = S.load_state(item["item_id"]) if S.state_path(item["item_id"]).exists() else None
    return {"item_id": item["item_id"], "prompt_text": item["prompt_text"], "system": item.get("system"),
            "rendered_text": target.tokenizer.decode(ids, skip_special_tokens=False), "token_ids": ids,
            "tokens": [target.tokenizer.decode([i]) for i in ids], "n_tokens": len(ids), "pos": len(ids) - 1,
            "read_token": target.tokenizer.decode([ids[-1]]), "layer": C.LAYER, "hook": C.HOOK,
            "hidden_states_index": C.LAYER + 1, "pre_answer": True,
            "activation_norm": (float(h.norm()) if h is not None else None), "prompt_ids_sha256": C.sha256_ids(ids)}


def lens_meta(jl: R.JLensReader, olens_target_layer: int = C.LAYER) -> dict[str, Any]:
    return {"jlens_file": jl.lens_path, "jlens_source_layers": jl.source_layers, "jlens_n_prompts": jl.n_prompts,
            "layer42_in_jlens_source_layers": C.LAYER in jl.source_layers,
            "olens_trained_layers": C.OLENS_TRAINED_LAYERS,
            "olens_layer42_on_grid": olens_target_layer in C.OLENS_TRAINED_LAYERS,
            "olens_note": "layer 42 is off the 20–60-step-4 training grid; documented compatibility note. Suraj's "
                          "matched-layer table: L40/L42/L44 agree within ~0.05 on every family (not re-run here)"}


# ================================================================== main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--checks", default="", help="comma list; default = all checks of the phase")
    ap.add_argument("--family", choices=FAMILIES, default=DEFAULT_FAMILY, help="regex family for the bench steps")
    ap.add_argument("--limit", type=int, default=100, help="bench items (default 100 = the whole family)")
    ap.add_argument("--batch", type=int, default=1, help="bench verbalization batch (1 = faithful wsbench path; Suraj 64/50)")
    ap.add_argument("--check", action="store_true", help="greedy batch-1 vs batched comparison on 4 cells")
    ap.add_argument("--k0-rows", type=int, default=64)
    ap.add_argument("--item-id", default=None, help="item for the inputs dump (default: first dev item)")
    ap.add_argument("--own-reader", action="store_true", help="bench_nla with our NLAReader (batch 1) instead of wsbench's class")
    a = ap.parse_args(argv)
    default_a = ["lens_meta", "k0", "olens", "inputs", "bench_capture", "bench_olens"]
    default_b = ["nla", "inputs", "bench_nla"]
    checks = [c for c in a.checks.split(",") if c] or (default_a if a.phase == "A" else default_b)
    print(f"R0 phase {a.phase} checks={checks} family={a.family} batch={a.batch} env={C.env_summary()}")
    fam = a.family

    if a.phase == "A":
        target = M.load_target()
        _save_r0("target", {"model_id": target.model_id, "revision": target.revision, "class": target.model_class,
                            "n_blocks": target.n_layers})
        if "k0" in checks:
            _save_r0("k0_layer_convention", check_k0(target, a.k0_rows))
        jl = ol = None
        if "lens_meta" in checks or "inputs" in checks:
            jl = R.JLensReader().bind(target)
            _save_r0("lens_meta", lens_meta(jl))
        if any(c in checks for c in ("olens", "inputs", "bench_olens")):
            ol = R.OLensReader().bind(target)
            _save_r0("olens_adapter_liveness", ol.liveness)
        if "olens" in checks:
            _save_r0("olens_positive_control", check_olens_positive(target, ol))
        if "inputs" in checks:
            it = dev_item(a.item_id)
            S.ensure_states(target, [it], module="repro")
            h = S.load_state(it["item_id"])
            _merge_json(INPUTS_JSON, "item", it)
            _merge_json(INPUTS_JSON, "capture", dump_capture_input(target, it))
            _merge_json(INPUTS_JSON, "jlens", R.input_dump(jl, h))
            _merge_json(INPUTS_JSON, "olens", R.input_dump(ol, h))
            print(f"[r0] inputs dump (capture/jlens/olens) -> {INPUTS_JSON}")
        if "bench_capture" in checks or ("bench_olens" in checks and not cells_path(fam).exists()):
            _save_r0(f"bench_capture:{fam}", check_bench_capture(target, fam, a.limit))
        if "bench_olens" in checks:
            _save_r0(f"bench_olens:{fam}:b{a.batch}", check_bench_olens(target, ol, fam, a.limit, a.batch, a.check))
        M.unload(target)

    else:
        nla = None
        if "nla" in checks or "inputs" in checks or ("bench_nla" in checks and a.own_reader):
            nla = R.NLAReader().bind()
            _save_r0("nla_adapter_liveness", nla.liveness)
            _save_r0("nla_prompt", {"marker_index": nla.marker, "n_prompt_tokens": len(nla.ids),
                                    "marker_id": int(nla.meta["tokens"]["injection_token_id"]),
                                    "neighbours": [nla.ids[nla.marker - 1], nla.ids[nla.marker + 1]],
                                    "enable_thinking": False})
        if "nla" in checks:
            _save_r0("nla_positive_control", check_nla_positive(nla))
        if "inputs" in checks:
            it = dev_item(a.item_id)
            h = S.load_state(it["item_id"])
            _merge_json(INPUTS_JSON, "nla", R.input_dump(nla, h))
            print(f"[r0] inputs dump (nla) -> {INPUTS_JSON}")
        if "bench_nla" in checks:
            if nla is not None and not a.own_reader:
                nla.unload()  # the wsbench class loads its own copy of the reader
                nla = None
            tag = "own" if a.own_reader else f"b{a.batch}"
            _save_r0(f"bench_nla:{fam}:{tag}", check_bench_nla(fam, a.limit, a.batch, a.check, a.own_reader, nla))
        if nla is not None:
            nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
