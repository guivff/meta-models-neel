# POD_RUNBOOK — G1–G4 reader integration on the RunPod H100 (80 GB)

Pod layout (memory note 2026-10-03): everything on `/workspace`; `source /workspace/.env` activates the
venv (torch 2.13 cu129, transformers 5.18, peft) and sets `HF_HOME=/workspace/hf_cache` and the API keys.
Repo copy: `/workspace/mats-minis` (rsync of the Mac repo). GPU work in a tmux session (`g_agreement`).
Never print the keys.

## 0. Shell setup (every shell)

```bash
source /workspace/.env
cd /workspace/mats-minis
export PYTHONPATH=/workspace/mats-minis:/workspace/mats-minis/third_party/workspace-bench/src:/workspace/mats-minis/third_party/jacobian-lens:/workspace/mats-minis/third_party/EasyNLA:$PYTHONPATH
# wsbench CLI (judge/produce) needs its deps; install once, editable, no GPU extra re-pins:
pip install -e third_party/workspace-bench --no-deps && pip install "pydra-config>=0.0.17" "openai>=1.40" "anthropic>=1.0" pyyaml pandas pyarrow
# optional speed-ups for Qwen3.6's gated-DeltaNet layers (fallback is correct but ~3x slower):
pip install flash-linear-attention causal-conv1d || echo "kernels not installed; using torch fallback"
python -c "import wsbench, jlens, nla.injection; print('third_party importable')"
```

## 1. Disk check and downloads (~115 GB; only the needed files)

Sizes (HF API, 2026-10-07): Qwen3.6-27B 55.6 GB · NLA av_base 53.8 GB · NLA adapter iter_000400 1.87 GB ·
OLens adapter 0.47 GB · J-lens n1000 3.3 GB · example parquet ~1.5 MB. Total ≈ 115 GB + HF cache overhead.

```bash
df -h /workspace | tail -1          # need >= 120 GB free on the network volume
du -sh /workspace/hf_cache 2>/dev/null
python - <<'EOF'
import os
from huggingface_hub import snapshot_download, hf_hub_download
tok = os.environ.get("HF_TOKEN")
# 1. target model, full, pinned
snapshot_download("Qwen/Qwen3.6-27B", revision="6a9e13bd6fc8f0983b9b99948120bc37f49c13e9", token=tok)
# 2. NLA: base + one adapter + meta + examples (NOT the AR reconstructor / other iters: ~350 GB)
snapshot_download("ceselder/qwen3.6-27b-nla-rl", revision="5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f", token=tok,
    allow_patterns=["av_base/*", "av_rl_adapters/iter_000400/*", "nla_meta.yaml", "run_config.yaml",
                    "fve_trajectory.json", "data/example_activations.parquet", "README.md"])
# 3. OLens adapter (model repo copy)
snapshot_download("agu18dec/olens_and_ar", revision="c95215d5d2f6250f20c305ae55c6e4d7569f92dc", token=tok,
    allow_patterns=["olens_s3d_rl600/*", "README.md"])
# 4. J-lens n1000 file only
hf_hub_download("neuronpedia/jacobian-lens", "qwen3.6-27b/jlens/Salesforce-wikitext/Qwen3.6-27B_jacobian_lens_n1000.pt",
    revision="b25d72a96b79c8e309d6625955a98751da47e67a", token=tok)
print("downloads done")
EOF
df -h /workspace | tail -1
```

Verify the two adapter files against `manifest/assets.json` (sha256 = LFS oid):

```bash
sha256sum $(find /workspace/hf_cache -path "*olens_s3d_rl600/adapter_model.safetensors" | head -1)   # 7d4b301e...
sha256sum $(find /workspace/hf_cache -path "*iter_000400/adapter_model.safetensors" | head -1)       # b54e23e4...
```

## 2. Dataset artefacts must exist (dataset track)

`projects/g_agreement/dataset/items.json`, `rubric.md`, `donors.json`, `g4_pairs.json`. Then freeze once,
after dev-only development, before any test collection:

```bash
python -m projects.g_agreement.core.config --status      # expect "NOT frozen" before the freeze
python -m projects.g_agreement.core.config --freeze      # writes manifest/frozen_config.json
python -m projects.g_agreement.core.config --status      # expect "frozen OK"
```

Test-split collectors refuse to run unless the freeze matches disk (dataset/rubric/donors/g4/code shas).

## 3. Phase order (one 80 GB card; models loaded sequentially)

Phase A = target model (`Qwen/Qwen3.6-27B` bf16 ≈ 54 GB). Phase B = NLA reader (av_base ≈ 54 GB + adapter).
Each script is resumable (existing `gen_id`s are skipped) and logs per-call wall time / tokens / peak
memory in the row and a per-step summary in `results/g_agreement/compute.jsonl`.

```bash
tmux new -s g_agreement
source /workspace/.env; cd /workspace/mats-minis; export PYTHONPATH=...   # as in §0
mkdir -p results/g_agreement/repro cache/g_agreement

# --- Phase A, part 1: R0 on the target model (K0, OLens control, lens meta, inputs dump, bench cells + OLens bench)
python -m projects.g_agreement.repro.r0_checks --phase A --checks lens_meta,k0,olens,inputs 2>&1 | tee -a results/g_agreement/repro/r0_phaseA.log
python -m projects.g_agreement.repro.r0_checks --phase A --checks bench_capture,bench_olens --limit 100 2>&1 | tee -a results/g_agreement/repro/r0_phaseA.log
#   (--limit 20 for a cheap first pass; bench_capture is needed by Phase B's bench_nla)

# --- Phase A, part 2: G1 dev (unfrozen allowed), then freeze, then G1 test
python -m projects.g_agreement.g1_agreement.collect --phase A --items dev --offgrid --state-free --jlens-null
python -m projects.g_agreement.core.config --freeze
python -m projects.g_agreement.g1_agreement.collect --phase A --items test --state-free --jlens-null

# --- Phase A, part 3: G3 prompt-only (dev + test) and G4 OLens repeats
python -m projects.g_agreement.g3_activation_dependence.collect_prompt_only --items dev
python -m projects.g_agreement.g3_activation_dependence.collect_prompt_only --items test
python -m projects.g_agreement.g4_repeats.collect --phase A

# --- Phase B: NLA (target model is unloaded at the end of every Phase A script)
python -m projects.g_agreement.repro.r0_checks --phase B --checks nla,inputs 2>&1 | tee -a results/g_agreement/repro/r0_phaseB.log
python -m projects.g_agreement.g1_agreement.collect --phase B --items dev --state-free
python -m projects.g_agreement.g1_agreement.collect --phase B --items test --state-free
python -m projects.g_agreement.g4_repeats.collect --phase B
python -m projects.g_agreement.repro.r0_checks --phase B --checks bench_nla --limit 100 2>&1 | tee -a results/g_agreement/repro/r0_phaseB.log
#   bench_nla uses wsbench's own NLA class (loads its own av_base copy); add --own-reader to use core.readers.NLAReader
#   in the same process as the other Phase B checks instead.

python -m projects.g_agreement.core.states          # summary of the state cache
nvidia-smi --query-gpu=memory.used --format=csv     # should be ~0 between phases
```

Check between phases: `python - <<'EOF'\nimport torch; print(torch.cuda.memory_allocated()/1e9)\nEOF` must be ≈ 0
in a fresh process (each script exits; nothing stays resident).

## 4. What to look at before continuing to test items

- `results/g_agreement/repro/r0.json`: `k0_layer_convention.winning_block == 42`, median cos > 0.999;
  `lens_meta.layer42_in_jlens_source_layers == true`; `olens_adapter_liveness.all_matched == true` and
  `max_abs_logit_delta` ≫ 0; `nla_prompt.marker_id == 158983`, `neighbours == [29, 510]`;
  `olens_positive_control` / `nla_positive_control` read sensibly (and the shuffled vector does not).
- `results/g_agreement/repro/inputs_dump.json`: the full prompt text + ids each reader receives, marker
  index, injection formula, activation norm, sampling.
- `bench_olens.judge.value` vs 0.32 (grid any-layer; L42-only is a lower bound) and `bench_nla.judge.value`
  vs 0.22 published / 0.15 Suraj. Judging is regex-only: `python -m wsbench judge family=multihop_mt readouts=<file> layers=42 allow_missing=True out=<dir>` (no API key needed).
- Dev-set completion rate at the 128-token cap (`finish_reason`): revise the cap in `core/config.py` BEFORE
  the freeze if too many dev readouts hit `length`; note it under Deviations in BRIEF.md.

## 5. Copy results back (text only, per subdirectory)

```bash
# from the Mac
rsync -av --stats pod:/workspace/mats-minis/results/g_agreement/ results/g_agreement/
rsync -av --stats pod:/workspace/mats-minis/cache/g_agreement/gens/ cache/g_agreement/gens/
rsync -av --stats pod:/workspace/mats-minis/cache/g_agreement/states_meta.jsonl cache/g_agreement/
```

## 6. Expected GPU time (assumptions stated)

Assumptions: HF `generate` on one H100, bf16, batch 1; ~15 tok/s decode with the fused gated-DeltaNet
kernels installed, ~5 tok/s with the torch fallback (the pod venv had no `flash-linear-attention` on
2026-10-03); model load 3–8 min per 54 GB from the network volume; verbalizer calls average ~100 new
tokens under the 128 cap (~200 under 256 for the bench).

| step | calls × tokens | with kernels | fallback |
|---|---|---|---|
| load target / load av_base | 2 loads | 5–15 min total | same |
| R0 K0 (64 forwards ≤ 1.9k tok) | 64 × 0 | 2 min | 4 min |
| R0 OLens + NLA positive controls | 6 + 5 calls | 2 min | 5 min |
| capture 40 states (+16 dev extra layers, same forwards) | 40 forwards | < 1 min | 1 min |
| target answers 40 × 32 | 1.3k tok | 2 min | 5 min |
| J-lens 40 + jlens_null 21 | matvecs (+3.3 GB file load) | 2 min | 2 min |
| OLens G1 40 + offgrid 16 + state_free 8 | 64 × ~100 | 8 min | 22 min |
| prompt-only 40 × 128 | 5k tok | 6 min | 17 min |
| G4 OLens 16 + NLA 16 | 32 × ~100 | 4 min | 11 min |
| NLA G1 40 + state_free 16 | 56 × ~100 | 7 min | 19 min |
| **G1–G4 + R0 (no bench)** | | **≈ 45 min** | **≈ 1.7 h** |
| bench OLens multihop_mt 100 × 256 | 100 × ~200 | 25 min | 70 min |
| bench NLA multihop_mt 100 × 256 (+ capture 100 forwards) | 100 × ~200 | 25 min | 70 min |
| **R0 bench (both arms, 100 items)** | | **≈ 50 min** | **≈ 2.3 h** |

Use `--limit 20` on the bench for a first pass (≈ 10 min / 30 min). Everything is resumable, so a
restart costs only the model reload.

## 7. Conventions changed on 2026-10-07 after integration (supersede §3/§6 where they differ)

- `--state-free` rows are ITEM-LINKED: one call per selected item per verbalizer with the mean of the 8 dev
  activations (seed differs per item), `module: g3`, `condition: state_free`, `state_item_id: null`,
  written to `cache/g_agreement/gens/g3.jsonl` (dev: 8 per reader; test: 32 per reader = 64 calls,
  ≤ 8,192 tokens, separately budgeted). The zero-vector variant was dropped.
- `--jlens-null` rows are item-linked too: per selected item one Gaussian vector at the median dev norm
  (`|rand`) and the mean dev activation (`|mean`), `method: jlens_null`, in `gens/g1.jsonl` (no generation).
- Prompt-only rows go to `gens/g3.jsonl` (not `g3_prompt_only.jsonl`).
- After collection: `bash projects/g_agreement/run_all.sh claims` then `... analyze` (CPU, Mac or pod).
  Dev plumbing: `ANALYZE_FLAGS="--allow-unfrozen --split dev" bash projects/g_agreement/run_all.sh analyze`.
