# For the mats-nla-workspace team: our codebase, experiments and hypotheses

Guiv Farmanfarmaian's side of the activation-readers project, packaged for reconciliation with
`Jarus77/mats-nla-workspace`. This folder is on branch `claude/nla-codebase-docs-669bdf` of
`guivff/activation-readers`, which starts from `r/blindspot` at `b1e6929d`, our most complete science branch.

For this package we changed no constant, seed, item, score or result. Everything here is one of three things:
- a copy of a sealed file;
- an export from one, checked against its seal hash (`export_w1.py`, `EXPORT_RECEIPT.json`);
- an index that points into the repo.

## Start here

| you asked for | where |
|---|---|
| 1. one line per experiment: question, status, where the results live | `EXPERIMENTS.md` (217 experiments; full fields in `inventory/experiments_index.json`) |
| 1. model and checkpoint ids, layer convention, read position | the next three sections of this README |
| 2. per-experiment folder (question, hypothesis, item bank JSON, exact phrasings, scoring, results JSON + table, raw logs, cost) | `experiments/W1_40row/` in full; for the other experiments, see "What is not in one folder" below |
| 3. the 40-row table as JSON, every reader at each layer, with two- vs multi-candidate rows marked | `experiments/W1_40row/table_40rows.json` |
| 4. the hypotheses as they stand, what would change our mind, what is running or queued | `HYPOTHESES.md` (plus `projects/g_agreement/REVIEW_HYPOTHESES_2026-10-26.md`) |
| 5. cross-scoring inputs in your exact shape | `cross_scoring/guiv_items_tb_tablecol.json`, `guiv_items_tb_paren.json`, `guiv_phrasings.json` (read `cross_scoring/README.md` first: our `late` is column 5 only) |
| 6. everything we measured that bears on your two headline claims | `HEADLINE_CLAIMS.md` |

## Models and checkpoints

All pins are from `projects/g_agreement/manifest/assets.json`, which was verified against the HF API on 2026-10-07.

| role | id | revision / checkpoint |
|---|---|---|
| target model | `Qwen/Qwen3.6-27B` | `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`, bf16 (64 blocks, d = 5120); the NLA was trained against this snapshot |
| NLA | `ceselder/qwen3.6-27b-nla-rl` | revision `5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f`; base `av_base/` with adapter **`av_rl_adapters/iter_000400`**; extraction layer 42 |
| Oracle lens | `agu18dec/olens_and_ar` | revision `c95215d5d2f6250f20c305ae55c6e4d7569f92dc`, subfolder **`olens_s3d_rl600`** (GRPO 600 steps from `s3d.omp4bp.s2/step251`) |
| J-lens | `neuronpedia/jacobian-lens` | `b25d72a96b79c8e309d6625955a98751da47e67a`, `qwen3.6-27b/jlens/Salesforce-wikitext/Qwen3.6-27B_jacobian_lens_n1000.pt` |
| your code | `Jarus77/mats-nla-workspace` | vendored at `2e98a5db` under `external/mats-nla-workspace` (`external/PINS.md`); the blind-spot and E-series scoring imports your `mats.readers` |

**Oracle lens layer.** The Oracle lens was trained on blocks 20–60 in steps of 4: `run.json` lists layers
`[20, 24, …, 60]`. Block 44 is therefore on its grid and **block 42 is off it**. The early phases (G–Z) read the Oracle
lens at 42; O44 then reran them at 44. From the blind-spot programme on, the Oracle lens is read at **44**, and in the
layer sweeps at 20/28/36/44/52/60 (W5) or at all 11 grid layers (E24).

**Oracle lens prompt.** Its prompt states the layer as a plain integer: "An activation vector from layer {layer} …".

**Oracle lens injection.** The marker embedding is replaced by 16000·h/‖h‖. The adapter is off during capture.

**NLA injection.** At the output of block 1, h1[marker] += ‖h1[marker]‖·h/‖h‖. This happens in prefill only, with the
marker U+321C (token id 158983).

## Layer convention

**"Layer L" or "block L" means the output of decoder block L (zero-based), which is HF `hidden_states[L+1]`.**
`hidden_states[0]` is the embedding output. So layer 42 is `hidden_states[43]`. This matches EasyNLA's
`layer_index = K` and wsbench's "benchmark layer L".

We checked this against your 64 shipped NLA activations (r0, `results/g_agreement/repro/r0.json`):
- block 42: median cos 0.9999, rel-L2 0.025 (your reference: 0.9999 / 0.026);
- blocks 41 and 43: about 0.98 and 0.22.

## Read position

| programme | read position | render |
|---|---|---|
| G, X, Y, Z, W/V, S/F2 and most of phase R | the last prompt token = the assistant onset after the empty think block (`<\|im_start\|>assistant\n<think>\n\n</think>\n\n`) | chat template, `enable_thinking=False`, `add_generation_prompt=True` |
| phase R `raw` arms (secondary) | the last token of the bare text | no template |
| blind-spot W1–W12, E-series, the cross-scoring files | **the last token of `text`**; `read_position = token_length − 1` | no chat template, no special tokens (the same convention as your exp 13 items) |

The captures are raw: fp32 saved from a bf16 forward, with no normalisation, centring or whitening.

## What is not in one folder, and why

- **W1 (the 40-row table) is complete as a folder.** It has the item bank, exact phrasings, the table JSON, registered
  metrics, raw per-item scores, sealed free readouts and cost.
- **The other ~216 experiments have no folder of their own here.** Each one's code, item bank, results and logs
  already live at a stable path on a pushed branch. `inventory/experiments_index.json` gives those paths per
  experiment (fields `item_bank`, `scoring`, `code`, `results`, `logs`, `gpu`, `prereg`), and every path was checked to
  exist (`git cat-file -e`). Copying them all into folders would duplicate about 1,500 files without adding anything.
  If you name the experiments you want, we will pack those in the same shape as W1.
- **Results on other branches.** Some experiments' results are only on other branches: `r/blindspot-mech` (W3, W4, W7,
  E1, E2, E7, E11, E12, E16, E18, E21, E23, E26, E27c, E34, E38, E47), `r/blindspot-internals` (E3, E4, E19, E22, E30,
  E31(ii), E45, E48), `r/inverter` (W6), `r/remainder` (W8, W8b, S5), `r/neel5` (S4, SA, SA-R) and
  `r/phase-r-scaffold` (phase R). These branches have diverged, and we did not merge them for this package, because a
  merge would rewrite the integration records other sessions are still appending to. Read them with
  `git show origin/<branch>:<path>`.
- **Activation arrays are not included.** They are about 8 GB in `cache/`, for example W1's 7,296 × 5,120 at blocks 42
  and 44. Item order and hashes are in `results/g_agreement/blindspot/w1/analysis/activations.json`. We can send them
  over a file transfer if you need them; they are too large for git.
- **The free-response recall for W1 is PARTIAL.** Only the priority unit's free readouts are sealed, and they are in
  `experiments/W1_40row/raw/`. Remainder unit A's target readouts were stopped by the compute deadline and are
  unsealed, so we left them out. The blinded judge has not run, so we report no recall rate.
- **W1 labels are now in this branch.** On our side, labels are kept off GPU pods until each analysis has run. W1's
  analysis is sealed, so sharing them changes no result. Please do not copy `items_w1_all.jsonl.gz` onto a pod that
  runs one of our queued jobs.
- **Secrets.** There are no API keys or tokens in this folder. It was scanned for `hf_`, `sk-`, `OPENROUTER`,
  `HF_TOKEN`, `api_key` and `Bearer` before commit.

## Cost

- **Logged total.** Summing every `gpu_hours` row in the integration branch's `results/g_agreement/compute.jsonl` gives
  209.4 GPU-h as logged through 26 Oct (635 rows). That sum includes staging and failed attempts, and some rows are
  descriptive splits of one pod, so treat it as an upper bound, not a cost.
- **Before F2.** The early phases logged wall-clock time only, not GPU-hours; see `compute_note` in their index
  entries.
- **Phase R ledger.** About 57.9 GPU-h, about USD 231, including 11.6 h wasted (`results/g_agreement/r/INTEGRATION.md`
  on the integration branch).
- **E-programme.** USD 237.64 spent of a USD 1,400 budget at 15:28Z on 26 Oct.
- **Per experiment.** See `gpu` in the index.
