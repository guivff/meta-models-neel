> **SUPERSEDED 2026-10-23 08:10 CEST (Guiv), before any data.** The registered rules for this programme are in
> `BRIEF_BLINDSPOT.md` §70–§84 (commit ec24012d). Nothing in this file is a decision rule. The scaffold's
> diagnostic thresholds (PRESENT / REPORTED / CANDIDATE BLINDSPOT) may be reported only as descriptive per-cell
> labels; every verdict uses the BRIEF_BLINDSPOT rules.

# Blindspot bank and AR experiments 1–6 — proposed registration, 2026-10-23

**Status: DRAFT_PENDING_INTEGRATOR_REGISTRATION. No model compute authorized by this file.**
The requested BRIEF_W did not exist on local or GitHub `main`, nor in the local worktrees inspected.
These are explicit proposed rules, not a reconstruction of an unseen brief. The integrator must
adopt/push this registration, pin its bytes and commit in an assignment, and assign a pod before
any target/reader/AR forward. Any changes before adoption remain before-data changes; after that,
only dated deviations are permitted. There is no GPU budget or pod assignment yet.

Context read: CLAUDE.md and README.md at main `9abc5427`; BRIEF_V at P3 `33446a3c`.
BRIEF_V's §64–66 are separate hypotheses and are not re-used as blindspot decision rules.

## Frozen population and shared protocol

- Qwen3.6-27B; output of zero-based block44 for Oracle and AR, block42 for NLA; J and probes at both.
- Forty fixed features in `blindspot/items.py`: count-like text-buffer, structural state and semantic
  content, across prose, Python, LaTeX, JSON, markdown tables and markdown lists. Synthetic data only.
- Per feature, 20 mine clusters + 80 held-out selection clusters, two opposite values per cluster:
  8,000 items total. All siblings stay in the same split and probe fold. Mine is reserved; no
  template mining in this scaffold. Selection probes use grouped 5-fold cross-validation.
- A delimited unrelated archive preamble pads both values, with extra padding for shorter/early
  bodies. Total token lengths match exactly within every cluster. KS p>0.2 asserted separately per
  feature and split; identical distributions is a stronger engineering check. These checks do not
  establish that padding is semantically inert. Local feature definitions start after the delimiter.
- Read position: final token of the raw prefix, no chat template, matching Suraj's exp13 construction.
- One frozen native template pair per feature/reader, no selection on readout performance. Oracle
  bullet register, NLA explanation register; J cosine contrast of single-token label variants.
  J scores are cosine contrasts, not probabilistic log-odds. No post-hoc orientation reversal.
- True arm and opposite-value matched activation arm, within the same cluster and exact token length.
- Labels never enter the GPU input. SHA256-seal inputs, activations and complete native score grids
  before joining labels. Supervised probes run after that seal; each probe test cluster is held out.
- Per-cell AUROC and true-minus-mismatched AUROC, 2,000 source-cluster bootstrap replicates. Probe
  intervals bootstrap fixed OOF predictions, not full training uncertainty. Missing/unscorable cells
  retain denominators and get NOT EVALUABLE. No best-layer/template selection.
- All forwards use pinned local assets, offline; zero judge/API calls. Integrator owns allocation,
  whole-provider-custody accounting, external hardstop and retrieval. Worker logs are additional
  process accounting and must not be added twice to the integrator's custody GPU-hour total.

## 1–3. Reader blindspot map (proposed per-cell diagnostic rules)

1. **PRESENT:** probe AUROC>=0.75 and 95% CI lower>0.5 at the stated layer.
2. **REPORTED:** native true AUROC>=0.70 and 95% CI lower>0.5. **ACTIVATION-DEPENDENT:**
   true-minus-mismatched AUROC>0 and paired 95% CI lower>0.
3. **CANDIDATE BLINDSPOT:** PRESENT, reader true AUROC<=0.60 with 95% CI upper<=0.65.
   Otherwise MIXED or NOT MET. Passing these diagnostic rules is not a multiplicity-adjusted
   confirmation across forty features: any selected headline requires fresh confirmation data.
   Report all cells and CIs, including negative results. No "reader is blind" from a nonsignificant test.

## 4. Reconstructor direction fidelity (proposed)

AR-reconstruct the two fixed Oracle candidate bullets for each feature (80 texts total), using
P3's official loader and pooled L44 whitener (pins in external/PINS.md; ridge0.1). Compare their
signed difference with each natural selection pair's value0-minus-value1 direction in whitened
space. **ALIGNED** if mean signed cosine>=0.10 and cluster-bootstrap 95% CI lower>0;
otherwise NOT MET, or NOT EVALUABLE for a degenerate AR direction. No squaring: sign matters.
This tests candidate direction fidelity, not fidelity of arbitrary free-text claims.

## 5. Residual probing (proposed)

Whiten L44 states with the fixed P3 ruler; remove their projection on the fixed AR candidate
direction. Compare grouped logistic probes on original states, AR residual and a seeded random
direction residual. No fitting the removed direction on selection labels. **RESIDUAL PRESENT**
if residual AUROC>=0.75 and lower95>0.5. **AR DIRECTION EXPLAINS SIGNAL** if random-residual
AUROC minus AR-residual AUROC>=0.05 and its paired cluster-bootstrap lower95>0. Otherwise
NOT MET/MIXED. Random direction seed20261023+feature-index. All thresholds are per-cell diagnostics.

## 6. Causal last-token swap (proposed)

First16 selection clusters per feature by opaque cluster hash (frozen by the builder), both
directions: 1,280 recipient states. Frozen arms: identity, natural full donor-minus-recipient
swap, whitened-metric AR component, residual component and raw-norm-matched random AR control.
The component+residual equals the natural difference; no renormalisation. Replace block44's
last-token output while preserving the recipient's preceding context.

Outcome: KL(P_donor || P_recipient) minus KL(P_donor || P_edited), positive toward the donor's
native next-token distribution. Report donor-argmax match with Wilson95 intervals descriptively.
**MANIPULATION CHECK:** full-minus-identity mean KL gain>0 with cluster CI lower>0. If not, causal
interpretation is NOT EVALUABLE. **AR COMPONENT HAS EFFECT:** AR-minus-random mean KL gain>0
with cluster CI lower>0. Report residual and full alongside it. No next-token effect is called
feature-specific computational relevance; the donor also changes other content. A genuinely
feature-specific behavioural claim requires a separately registered elicited task.

## Reporting and deviations

`blindspot/RESULTS.md` is a template only. Raw scores/vectors/logs go in cache; log commands,
seeds, wall-clock, and GPU-hours in results/g_agreement/{log.md,compute.jsonl}. Statuses: BLOCKED,
NOT RUN, PARTIAL, NOT EVALUABLE, NOT MET, MIXED, PRESENT, REPORTED, ACTIVATION-DEPENDENT,
CANDIDATE BLINDSPOT, ALIGNED, RESIDUAL PRESENT, AR DIRECTION EXPLAINS SIGNAL.

**2026-10-23 pre-compute transport deviation:** worktree destination moved to the writable
Activation_Readers workspace; upstream source obtained from a tree-verified GitHub archive via a
local mirror because shell network access is unavailable. No scientific rule changed.
