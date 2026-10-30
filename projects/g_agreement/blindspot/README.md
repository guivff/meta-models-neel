# W-core: registered W1, W5 and conditional W1b

Current production launch route: [priority runbook](../../../results/g_agreement/blindspot/PRIORITY_RUNBOOK.md).
The complete W1 bank is already frozen; do not rebuild it. The additive execution plan
orders the five priority rows first, supports one/two assigned pods within the same W1
cap, and exports training-only directions/class means before the one final W1 analysis.
The generic construction commands below document reproduction, not a new launch freeze.

Authority: `../BRIEF_BLINDSPOT.md`, shared rules and §§70,74,84. `BRIEF_W.md` is superseded.
All sites are outputs of zero-based model blocks. Suraj's pinned subtree is unchanged;
only `external/mats-nla-workspace/src` is importable. No infra or Modal driver is imported.

## Freeze before capture

Run from repository root with the project's Python environment:

```bash
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -m pytest external/mats-nla-workspace/tests projects/g_agreement/blindspot/tests -q
python -m projects.g_agreement.blindspot.items --tokenizer /local/pinned/Qwen-tokenizer --out cache/g_agreement/blindspot/w1-bank
python -m projects.g_agreement.blindspot.stage export-freeze --bank cache/g_agreement/blindspot/w1-bank --out results/g_agreement/blindspot/w1/freeze
```

The tokenizer's JSON SHA256 must match `manifest/assets.json`. The real-tokenizer test covers
all binary rows and ordinal levels before capture. Twelve authored template families per row
are split six dev/six test; paired variants share a template cluster and split. There are
seven pairs per template (168 items/row, 42 held-out pairs), providing at least the 40 test
pairs required downstream by W4. Ordinal sub-rows have eight levels and 36 items per level.
Both binary values and all ordinal levels are padded to exact matching token lengths.
The local feature begins after the unrelated archive-preamble delimiter.

Commit source, the small freeze receipts, and the tokenizer-test receipt before any capture.
Large banks and labels stay in cache. The input seal includes only label-free worker files;
`*.DO_NOT_STAGE.jsonl` must remain on the analysis machine. The frozen manifest hashes both
label-bearing and label-free files. `stage-bank` copies only the input seal's allowlist:

```bash
python -m projects.g_agreement.blindspot.stage stage-bank --bank cache/g_agreement/blindspot/w1-bank --out cache/g_agreement/blindspot/w1-stage
python -m projects.g_agreement.blindspot.stage request --bank cache/g_agreement/blindspot/w1-bank --freeze results/g_agreement/blindspot/w1/freeze --out results/g_agreement/blindspot/W1_POD_REQUEST.json
```

The request validates that the manifest and executable source bytes have been committed.
It requests an allocation; it does not assign or provision a pod. The integrator owns exact-ID
allocation, collision checks, external hard stop, retrieval, and whole-provider-custody accounting.

## Capture and scoring

Use `run plan` for the source hashes. The integrator assignment names the experiment, source
commit/hash mapping, registered brief commit/hash, committed manifest commit/hash, exact pod ID,
provider creation and deadline, allocated GPU seconds, previous GPU seconds, and verified
external hardstop. Cumulative caps are W1=7,200 s, W5=1,800 s, W1b=3,600 s. All staging and
loading count. The worker reserves the last 180 seconds for retrieval and cannot increase a cap.

Production batch size is frozen at 32 in `runtime.json`; changing it requires a new
before-capture freeze. Sample seeds are the registered seed plus the zero-based batch start.
GPU memory and throughput have not yet been measured for this bank.

Stage only pinned local assets: subject, Oracle adapter, NLA snapshot and J checkpoint, plus
SHA256 coverage for every local model/adapter file. The asset JSON also records a
`revisions` mapping for model/olens/nla/jlens, checked against the pinned revisions. Critical
tokenizer, adapter and J-checkpoint hashes are compared with the registered pins. `pod_run.sh` provides root-relative launch
commands. Target and NLA phases are separate processes; both charge the same W1 allocation.
Recommended order: `target --asked-only`, then `nla` (asked + free), then `free-target`
on the same target output directory. This seals all four asked readers before Oracle free
generation. `pod_run.sh target` supplies `--asked-only` automatically.

- W1 captures blocks 42 and 44. Oracle is scored at 44, NLA at 42, and J/logit baselines at 44.
- Each asked score averages two frozen phrasing contrasts. Oracle/NLA use native teacher-forced
  paired log-odds. J uses the pinned reader's maximum-token-variant cosine contrasts; logit uses
  maximum-token-variant log-odds. Each baseline averages two frozen short-label/synonym pairs,
  audited with the real Qwen tokenizer. Missing token variants are explicitly NOT EVALUABLE.
  J and logit are descriptive baselines; their token contrasts differ from sequence likelihoods.
- Mismatched activations are the opposite-value paired instance, with identical domain, template
  family, split and exact length. Ordinal rows are true-arm descriptive correlations only.
- Activations and partial score journals are saved before subsequent expensive stages. Only a
  complete grid gets `SCORE_SEAL.json`. No labels are joined until both reader seals pass.
- Two unasked OL/NLA readouts are frozen: greedy and sampled (T=1, top-p=.95, top-k=64), cap 128,
  seeds 20261023 and 20261024. Greedy Oracle output is available for W3. Baselines return two
  identical native top-ten token lists, explicitly marked deterministic repeats. They are not
  independent prose generations. Free readouts have a separate seal; absent blinded judgments
  mean unasked recall remains NOT RUN, never estimated from the generator labels.
- W5 uses only binary W1 test IDs from `sweep.input.json`, with Oracle and grouped probes at
  blocks 20, 28, 36, 44, 52, 60. No best-layer selection.

## Analysis and downstream artifacts

`run analyse` verifies source seals, complete grids, item order, activation shapes and the frozen
label hash before reading labels. All scientific rules use test data. The logistic probe gate
uses five template-grouped folds on test, fixed L2 regularization, with train-fold standardization.
Two thousand template-cluster bootstrap samples quantify AUROC uncertainty, conditional on the
fitted out-of-fold predictions. Separate dev-only fits export A-positive probe directions,
raw intercepts and dev/test class-mean projection gaps.

Before-data operational details of the registered rules:
- A probe below .85 is NOT DECODABLE. A reader's mismatched AUROC above .60 is NOT EVALUABLE.
- W1(i) uses Oracle-evaluable count/state rows. W1(ii) uses those same rows that satisfy(i);
  missing or gated NLA cells do not count as successes and are listed. W1(iii) uses
  Oracle-evaluable semantic rows. Empty eligible classes produce NOT EVALUABLE.
- Within .10 means absolute AUROC difference ≤ .10. The registered W1 verdicts are CONFIRMED,
  PARTIAL and NOT MET; W5 and W1b use their own registered conditions.
- W5 requires probes ≥ .85 at all six sites and Oracle < .75 at five or more sites on ≥ 75% of the
  W1 blind-spot rows. Unresolved cells remain explicit; a verdict is issued only when
  their best- and worst-case bounds agree with the registered threshold.

Commit small metrics, direction NPZ/JSON files, item-order hashes and activation location/hash
receipts in `results/g_agreement/blindspot/`. Actual activation arrays stay in cache and must be
retrieved before releasing the pod. This is the handoff for W-mechanism, lenses, inverter and Neel5.

## Blinded unasked recall

`python -m projects.g_agreement.blindspot.recall packet --help` describes the human
annotation packet. It verifies both free-readout seals and randomizes the displayed A/B
alternatives, while hiding reader identity, item ID, class, source text and truth. The packet
builder never reads labels. `seal-annotations` freezes completed judgments before `analyse`
opens the label file. Strict recall, inclusive recall and BOTH rates are descriptive, with
Wilson intervals and explicit missing denominators. No judge API is invoked.

## Conditional §84

Do not construct W1b items until the lens chat has committed the selected §79 candidates
(and any optional §81 candidates). Record that selection commit and file hash before building
fresh templates under the same freeze/seal/test protocol. The W1b bank constructor requires a
selection receipt. W1b's one-hour allowance is separate and requires an integrator assignment.
No candidates are inferred from uncommitted rankings.
