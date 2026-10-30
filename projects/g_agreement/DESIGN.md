# G-experiments: modular design (G1–G4 as separable parts over one shared core)

Date: 2026-10-07. Owner: Guiv. Scope: G1 agreement map, G2 relations, G3 activation
dependence + prompt-only, G4 repeated readings. Suraj's S-experiments and the B-experiments
are out of scope; nothing here touches his confirmation banks.

Principle: **one shared core produces frozen artefacts (dataset, states, native readouts,
extracted claims); each G-module is a pure consumer of those artefacts plus, where needed,
one small, separately budgeted GPU step of its own.** Every module can be run on its own
once the core artefacts it lists exist; the core steps are idempotent and cached.

```
projects/g_agreement/
  DESIGN.md                     this file
  BRIEF.md                      pre-registration (hypotheses, endpoints, decision rules, caps) — frozen before test collection
  INTERFACES.md                 file formats shared by every module (below, in short)
  manifest/assets.json          exact asset ids, revisions, hook, position, precision, sampling (filled by repro step R0)
  core/
    config.py                   frozen constants: model id + sha, layer=42 hook=block-output, caps, sampling, seeds
    model.py                    load Qwen3.6-27B text model; capture block-42 output at the pre-answer position
    readers.py                  thin wrappers around wsbench.produce methods: jlens (cosine top-10), olens, nla
    generate.py                 target answers (greedy, 32 tok) and generic chat generation with budgets/timing
    states.py                   state cache (cache/g_agreement/states/*.pt + states_meta.jsonl, sha-stamped)
    scoring.py                  deterministic claim extraction (primary property + entities + relation) + blinded sheet
    accounting.py               per-call tokens / wall-clock / peak memory → results/g_agreement/compute.jsonl
  dataset/
    build_dataset.py            20 pairs × 2 versions, 4 families, dev/test split, answer keys, hashes → dataset/items.json
    rubric.md                   written BEFORE test inspection: primary property, candidates, support/contradict/unclear rules
    donors.py                   G3 donor permutation (seeded, within family, excludes recipient pair, label-balanced) → donors.json
    g4_selection.py             one test pair per family chosen by seed before any test output exists → g4_pairs.json
  repro/
    r0_checks.py                K0 layer convention on the 64 shipped NLA example activations; OLens positive control;
                                one recorded reader score (wsbench multihop_mt @L42, regex-scored); input inspection dump
  g1_agreement/
    collect.py                  GPU: capture 40 states, 40 target answers, 40 NLA, 40 OLens, 40 J-lens (first samples)
    analyze.py                  CPU: pairwise agreement / contradiction / coverage, factual accuracy, target consistency; fig + csv
  g2_relations/
    analyze.py                  CPU only: reuses G1 readouts on ownership+mapping; entity vs relation vs pair-tracking
  g3_activation_dependence/
    collect_prompt_only.py      GPU: 32 prompt-only generations (frozen prompt, 128 tok), same base model, no activation
    analyze.py                  CPU: genuine vs shuffled (cached donor reassignment) vs prompt-only; donor-tracking
  g4_repeats/
    collect.py                  GPU: +2 NLA and +2 OLens samples on the 8 preselected states (same frozen sampling)
    analyze.py                  CPU: cross-method vs within-reader agreement at matched coverage; compute costs
  run_all.sh                    the order below, each step skippable
  tests/                        offline tests on synthetic fixtures (clearly labelled MOCK; never written to results/)
results/g_agreement/<module>/   figures, csv, json, log.md per module; results/g_agreement/compute.jsonl shared
cache/g_agreement/              states, raw generations (git-ignored)
```

## Dependency graph

```
dataset/build_dataset.py ─┐
                          ├─► core.states (capture, GPU, once) ─► g1/collect (GPU) ─► g1/analyze ─► g2/analyze
repro/r0_checks.py (GPU) ─┘                                      │                      │
                                                                  ├─► g3/collect_prompt_only (GPU, independent of g1 outputs)
dataset/donors.py ───────────────────────────────────────────────┼─► g3/analyze (needs g1 readouts + donors + prompt-only)
dataset/g4_selection.py ─────────────────────────────────────────┴─► g4/collect (GPU; needs states only) ─► g4/analyze (needs g1 first samples)
```

Common dependencies kept shared (not duplicated): the dataset, the state cache, the reader
adapters, the sampling setting, the claim rubric/extractor, the compute ledger, the bootstrap
over base pairs (`common/stats.py` + `analysis` helpers).

Independence claims, stated honestly:
- G2 is an analysis of G1's outputs (no new model runs). It cannot be run before G1.
- G3's shuffled arm is a cached-readout reassignment, valid because NLA and OLens receive only
  (activation, fixed instruction, fixed layer integer 42) and J-lens is a function of the
  activation alone; it is not a fresh causal intervention and is labelled as such. G3's
  prompt-only arm is a GPU step that depends only on the dataset.
- G4's extra samples depend only on the state cache; its comparison reuses G1 first samples,
  which is valid only if sampling settings match (they do: both use the frozen setting in
  `core/config.py`). If the setting changes after development, G4 regenerates all three.

## GPU scheduling (one process at a time; models loaded sequentially on one 80 GB card)

Phase A — target model `Qwen/Qwen3.6-27B` (bf16, ≈54 GB):
  R0 (K0 recompute of 64 example activations; OLens positive control), capture 40 states,
  40 target answers, J-lens 40 readouts, OLens 40 (+16 for G4), prompt-only 32 (+8 dev),
  optional bench reproduction (OLens multihop_mt @L42).
Phase B — NLA reader `av_base` + `av_rl_adapters/iter_000400` (bf16, ≈56 GB; the target
  model is unloaded first): NLA 40 (+16 for G4) from cached states, optional bench reproduction.
Every call logs tokens, wall-clock, peak memory to `compute.jsonl`.

## Frozen settings (to be confirmed by R0 and copied into manifest/assets.json)

- Target: `Qwen/Qwen3.6-27B` @ `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9` (the snapshot the
  NLA was trained against), text model, bf16, `enable_thinking=False` chat render.
- Site: output of decoder block 42 (`model.layers[42]` forward hook = `hidden_states[43]`),
  last token of the render (assistant onset after the empty think block) = pre-answer position.
  Same tensor for all three readers; fp32 on disk, raw (no normalisation) — each reader applies
  its own native transform (OLens 16000·unit(h) replacing the marker embedding; NLA
  h₁ + ‖h₁‖·unit(h) added at block-1 output at its marker; J-lens cosine readout
  (W_U·J₄₂·h)/‖J₄₂ᵀW_U[t]‖, top-10).
- OLens: `agu18dec/olens_and_ar/olens_s3d_rl600` (= local-workspace `s3d.ddp600.s0/iter_000600`),
  prompt `concepts_raw` with layer integer 42 (off the 20–60-step-4 training grid; Suraj's
  40/44 sensitivity is reported, not re-run here).
- NLA: `ceselder/qwen3.6-27b-nla-rl` `av_base` + `av_rl_adapters/iter_000400`, actor prompt from
  `nla_meta.yaml`, marker ㈜ id 158983, neighbours (29, 510).
- J-lens: `neuronpedia/jacobian-lens` `qwen3.6-27b/.../Qwen3.6-27B_jacobian_lens_n1000.pt`.
- Verbalizer sampling (wsbench in-house setting): T=1.0, top_p=0.95, top_k=64; **our cap
  128 new tokens** (bench used 256; completion checked on dev, revised+frozen before test).
  Seeds: seed = hash(item_id, method, sample_idx) recorded per call.
- Target answer: greedy, 32 new tokens. Prompt-only: frozen question template, 128 tokens, greedy.
- Caps include any emitted reasoning; a hit cap = truncated = incomplete observation.

## Outputs per module (one figure each)

- G1: `fig_main.png` 3×3 agreement matrices (support-agree / contradict / missing) + accuracy &
  coverage bars by method and family; `agreement.csv` one row per (pair, method pair).
- G2: `fig_main.png` entity recognition vs relation accuracy vs complete-pair tracking per method.
- G3: `fig_main.png` genuine vs shuffled (recipient-scored and donor-scored) vs prompt-only accuracy.
- G4: `fig_main.png` accuracy vs coverage as the agreement rule tightens (cross-method 2/3, 3/3;
  within-NLA 2/3, 3/3; within-OLens) on the same 8 states, with compute per rule.
Uncertainty: bootstrap over base pairs (16 test pairs; 4 for G4). Raw numerators and
denominators always printed. No significance claims from this pilot.
