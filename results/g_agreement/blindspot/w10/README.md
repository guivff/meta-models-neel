# §86 W10: frozen items and integrator runbook

Authority: `REGISTERED_SECTION.md`, copied verbatim from
`guivff/activation-readers` at `7b955281ca165b3139a7de74460f2af6446774f4`.
`REGISTRATION_ORIGIN.json` records the Git blob. The shared local brief is older;
it is not overwritten or used to replace the registered §86 rules.

W-core authors this new carrier and reviews/analyzes the results. The integrator
publishes commits and operates the pod. §84 generation remains integrator-only.
No capture, model inference, judge call or pod operation occurred during authoring.

## Frozen operational choices (before any W10 science)

- All seven registered modes, each near/far: **14 mode rows, 120 items each**.
  Twelve passage-family clusters each contain five passages and both values.
  Families 0/2/4/6/8/10 are dev, the other six test; the same assignment is used
  across modes and distances. There are 60 distinct passages per row.
- One user instruction, 50 or 420 native tokens of neutral filler, then the exact
  copy request and passage. The assistant is opened with the pinned Qwen chat
  template, `enable_thinking=False`. Its first **16 passage tokens** are forced;
  the read position is passage token **15, zero-based**. Capture at decoder-block
  outputs 42 and 44, exactly W1's convention.
- Both instruction bodies are padded **inside the instruction span**. The test
  retokenizes the full rendered carrier and asserts identical token IDs before
  and after that span, equal span bounds, equal standalone instruction lengths,
  and equal total lengths. No value-specific filler or assistant text is added.
- The same 60 passages are reused across mode/distance rows; held-out passage
  families never enter training. The source freezes exact two-pair phrasings for
  Oracle and NLA and two native single-token contrasts for descriptive J-lens,
  as in W1. Oracle/NLA use summed sequence log-odds; J-lens uses its native cosine
  contrast, not a claimed log probability. A-minus-B orientation never changes.
- Random donors are hashed from the **same row and passage cluster**, with no
  use of value. Self-donors are allowed to avoid conditioning the distribution on
  the recipient's class. True scores are computed once for every activation;
  random-donor scores index those same deterministic scores using the frozen
  donor map. Readers receive no recipient prompt or condition information.
- Mode activity: 20 dev items per row, ten whole A/B passage pairs spread across
  all six dev families. Greedy generation of at most 48 new tokens starts from
  the empty assistant turn, **without the forced passage prefix**. The copy
  request is retained. Copy/mode conflicts are not repaired or filtered out.
  Frozen language and strict JSON scripts cover 80 items; a blinded rubric judge
  covers the other 200, total judge budget at most $3. The judge sees neither the
  instruction/value nor distance, split, reader scores or activations, and rates
  compliance with both possible modes before the local expected-value join.
  Fewer than 14/20 compliant generations makes the row NOT EVALUABLE.
- Limits of the mode check are retained: a lack of animal mentions does not prove
  that a prohibition was represented, and plain copied prose may not establish
  a distinct register or audience. These are reported, not used to loosen gates.
- Surprisal: **2,688** byte-identical raw W1 binary prose/Python prefixes are
  frozen as a pool, not newly authored or selected on reader scores. The label
  is minus the natural-log probability of the **current** token, predicted by
  the base model's logits at **p−1**, in the same full forward as activation
  capture. All pool scores are sealed first; top/bottom terciles are then derived
  locally within domain and existing dev/test split, with stable ID tie-breaking.
  Original W1 clusters are retained. Middle-tercile items are not recipients in
  the descriptive analysis, but remain eligible random donors. Report selected
  length matching; any mismatch is labelled LENGTH_CONFOUNDED, without changing
  the pool or retrospectively matching on the reader outcome. Mode activity is
  inapplicable to this raw-text pool; probe and random-donor gates apply.
- Reconstructor text window remains an open dependency for Camila. Do not claim
  blindness by construction until its window is established. No reconstructor
  model is loaded by this worker; it is unnecessary for the registered arms.

## Inputs, freeze and launch

`freeze/` contains the committed manifest, input seal, phrasings, instruction
pairs, length report, mode-check policy and deferred-surprisal policy. Large full
items and labels stay in the local cache. The staged allowlist has no label file.
`LAUNCH_REQUEST.json` pins the committed source archive and the committed freeze.

Authoring command (already run; do not overwrite/rebuild the frozen bank):

```bash
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
python -m projects.g_agreement.blindspot.w10_items \
  --tokenizer LOCAL_PINNED_QWEN_TOKENIZER_DIRECTORY \
  --w1-bank cache/g_agreement/blindspot/w1-bank \
  --out cache/g_agreement/blindspot/w10-bank-v1 \
  --freeze-out results/g_agreement/blindspot/w10/freeze \
  --stage-out cache/g_agreement/blindspot/w10-stage-v1
```

The integrator stages the exact source archive and frozen input allowlist, verifies
the usual pinned assets and installs its external hardstop, then issues a W10
assignment with the fields in `LAUNCH_REQUEST.json`. The worker admission is W10
specific: W1/W1b admission and frozen sources are unchanged. Use one H200 or larger
GPU; all target/Oracle, J-lens and NLA weights must fit in setup, without fallback
to a new unregistered runtime.

```bash
python -m projects.g_agreement.blindspot.w10_run \
  --bank STAGED_BANK --assignment INTEGRATOR_ASSIGNMENT.json \
  --assets VERIFIED_ASSETS.json --out NEW_W10_OUTPUT_DIRECTORY
```

Setup/loading and fixed unscored synthetic warm-up are outside science, within
1,500 s from creation. The first-science marker is persistent and precedes the
timed, unretained smoke. It cannot reset. Smoke covers all 16 row phrasings,
native 16-vector scoring batches, near/far contexts, current-token logits and all
14 mode-generation conditions. Only timing is retained. The full-work forecast
includes the smoke already spent, all captures/readers and 280 free continuations.
Admission requires **1.5 × forecast + 360 ≤ 3,600 s**; otherwise report NO_FIT
without reducing items or resetting the clock. Retain the independent absolute
hardstop and 180 s retrieval reserve (included in the allocation headroom).
One attempt; the integrator may issue a retry only for a documented infrastructure
failure with no science, under the registered exception.

The worker seals captures promptly and scores before labels, retaining partial
files without a completion seal if interrupted. Pull `CAPTURE_SEAL.json`,
`SCORE_SEAL.json`, `MODE_GENERATION_SEAL.json`, their covered files, the assignment
science clock and `SCIENCE_RECEIPT.json` to the local worktree. W-core verifies
coverage, lineage and seals before any label join or H1/H2 analysis.

After retrieval, create the blinded judge packet locally (no API call by this
command):

```bash
python -m projects.g_agreement.blindspot.w10_checks \
  --bank cache/g_agreement/blindspot/w10-stage-v1 \
  --generations RETRIEVED_W10_OUTPUT_DIRECTORY --out NEW_BLINDED_PACKET_DIRECTORY
```

The registered H1/H2 thresholds, reader-specific probe/random gates, paired
template-cluster bootstrap (2,000 resamples), per-phrasing reporting and signed
orientation remain exactly §86. Surprisal rows never enter mode denominators.
