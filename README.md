# When do activation readers reveal more than the prompt?

*Reporting gaps, causal read-site effects, and the limits of natural answer tracking.*

Guiv Farmanfarmaian and Suraj Prasad · MATS 12, Neel Nanda stream · 30 October 2026.

**Talk: [docs/TALK.pdf](docs/TALK.pdf) (58 slides). Detailed backup: [docs/DECK.pdf](docs/DECK.pdf) (39).** Editable versions: [TALK.pptx](docs/TALK.pptx) and [DECK.pptx](docs/DECK.pptx).

## Five-minute route

[Narrative](docs/NARRATIVE.md) → [TALK](docs/TALK.pdf) → [DECK](docs/DECK.pdf) → [claim ledger](docs/CLAIM_LEDGER.md) → [slide map](docs/SLIDE_EXPERIMENT_MAP.md) → [Suraj Prasad @ 4d43ecb2](https://github.com/Jarus77/mats-nla-workspace/tree/4d43ecb2ef8f2cfab9d8ef673a1c7f56380460fd).

Suraj's code: [external/mats-nla-workspace](external/mats-nla-workspace/).

The narrative, claim ledger, speaker notes and slide map use the **39-slide detailed deck's numbering** (24 core + 15 appendix), not the combined talk's numbering. [Speaker notes](docs/SPEAKER_NOTES.md), [fact-check record](docs/FACTCHECK.md) and [changelog](docs/CHANGELOG.md) accompany the supplied presentation. [EXPERIMENT_INDEX.md](EXPERIMENT_INDEX.md) locates E-IDs; [FINDINGS.md](FINDINGS.md) retains earlier background findings. Read the original rule and result before treating an index status as a scientific verdict.

## What the evidence supports

We evaluated activation readers on Qwen3.6-27B against prompt facts, interventions and the model's own behaviour. The talk keeps three measurements separate: **decodable** by a probe; **causal here** under an intervention at the specified token and block; and **stated** by the reader under the judging rule. Strong decoding does not establish faithful spontaneous reporting, and local causal effects do not establish a general mechanism.

Two scope caveats are essential:

- “all 84 fact items are context variants of one fact pair” (France/Peru → Paris/Lima in the E56/E104 fact row).
- “D1 separates holder from the most recent name, not from the last hand-over” (E137).

E140's late-layer comparison is conditional on the defined subset; it does not report a complete 600-item planned screen. E113's DEV/TEST items reuse underlying questions, so item separation is not held-out-task generalization.

**Review provenance:** R-2…R-5 and R-Q are separate agent reviewer sessions that checked scoped analyses of sealed outputs; agent review ≠ independent human replication. The E71 main audit has one human coder, Guiv. Suraj's results are **author results**, not independent replication. S16 is Suraj's experiment, executed by Guiv's agent on Suraj's pipeline. Suraj Prasad's original cited numbers remain pinned [upstream at 4d43ecb2ef8f2cfab9d8ef673a1c7f56380460fd](https://github.com/Jarus77/mats-nla-workspace/tree/4d43ecb2ef8f2cfab9d8ef673a1c7f56380460fd). The current tip observed for this update is [10d495f12fd63c434e8d9752f4a223ea59fa9d95](https://github.com/Jarus77/mats-nla-workspace/tree/10d495f12fd63c434e8d9752f4a223ea59fa9d95), which includes D51 corrections and exp 31's copy-overlap check cited in the combined talk. Suraj authorized vendoring on 30 October 2026 at 19:41 CET; the unmodified `10d495f1` tree is included under `external/mats-nla-workspace/`. Historical numerical pins are not silently rewritten.

## Current dispositions and provenance

**E95: dependent H-M1 parts NOT EVALUABLE.** The [R-Q deadline disposition](results/g_agreement/reviews/R-Q.md) from `6264b7173` records missing original bindings for those parts. This is a missing-binding disposition, not a measured negative map result. Judging completion is not scientific map completion. No completed non-placebo descriptive fallback is included or claimed in this update.

The full [R-4 review](results/g_agreement/reviews/R-4.md) and 22 Python source/test files excluded by the earlier literal-label-assignment filter are restored from `c16db568`. [EXCLUSION_REVIEW.md](docs/EXCLUSION_REVIEW.md) records exact hashes, reviewed source false positives, tonight's retention decisions and raw-data limits.

The research snapshot remains original `r/blindspot@c16db5689937c1895c9cb6d605bc39df19f15411`, plus traced dependencies. The detailed deck's original numerical citations use `c60fa9703f6dadc8150e11b0c2d5bbe899db02bc`; included cited Guiv blobs matched between those pins in the release audit. This presentation update does not turn the research snapshot into a new experimental seal. [PROVENANCE.md](PROVENANCE.md) records original branch/commit/path, restored-source hashes and the supplied presentation hashes. Snapshot commit time does not establish experiment ordering. The source repository remains private and unchanged by this release update.

## Known gaps for tonight

- **Registration ledger deferred.** There is no consolidated rule-by-rule registration ledger; use the original BRIEF sections, result files and reviewer reports. The generated experiment index is not a substitute.
- **Extra claim-ledger rows deferred.** The supplied ledger now has 62 rows and follows the detailed deck. It does not yet enumerate every quantitative appendix/notes claim, including the additional E94, E114, E136, E120c, E95, E110 and exploratory E71 spot-check claims identified in the audit. The exploratory E71 40-item immutable sample-binding closure is not established by the main 100-item audit.
- **No standalone raw-data rerun bundle.** Private vectors, labels, raw responses and some bindings are intentionally absent. Source and seal provenance does not guarantee complete independent numerical reproduction. Historical imports may refer to excluded or external dependencies.
- **F01 — E109 label disclosure:** `cpu_only/INVENTORY.json` exposed DEV/TEST labels and remains excluded. Judge exposure was not established; future blind confirmation requires a protected new bank.
- **F02 — E104 language rubric:** sampled codes treated English prose as stating the language value where the rubric calls for “exhibits”; no corrected full-cohort rate is claimed.
- **F06 — E136 scope:** explicit cue words and length recover labels; this supports a prompt-cue result, not a hidden-intention claim.
- **F14 — E37 arm order:** corrected counts are RL 4/1,344; SFT/pre-RL 1/1,344. Checkpoint-identity qualifications remain.
- **F15 — E96 judged sensitivity:** sampled codes credit plural enactment as “states value”; preserve the original verdict and channel distinctions, without claiming a corrected full-bank rate.

**Historical data retained tonight:** the ten synthetic-bank answer files remain as disclosed ground truth. The W5 operational pod request is removed and S8 pod identifiers are sanitized. Remaining host-metadata candidates are known and individually unreviewed; Guiv reports the pods are expired. This update does not verify their provider state.

Read [EXCLUSION_REVIEW.md](docs/EXCLUSION_REVIEW.md) for retained historical payloads and exceptions. Removing a file at the tip does not purge it from Git history. This release does not claim to be globally label-free or to remove historical data from earlier commits.

## Other branches not included

The **full branch-tip snapshots** below are not merged into this release. Tip SHAs were read from the source remote during this update. Some older dependency files from these branches are already included and traced in [SOURCE_PINS](docs/SOURCE_PINS.md) and [PROVENANCE](PROVENANCE.md); “not included” here does not mean that no file from the branch ever entered the snapshot.

All talk-cited Guiv experiments are represented in this snapshot. Suraj's talk-cited experiments, including exp 31, are available in the pinned vendored workspace and through the upstream links above. This coverage statement does not promise every private raw input or a standalone rerun bundle.

| Branch | Observed tip SHA |
|---|---|
| `claude/phase-r-integration-8abda6` | [`50504e445fa2151b0c3dc9c8b9af557432b32dd7`](https://github.com/guivff/activation-readers/commit/50504e445fa2151b0c3dc9c8b9af557432b32dd7) |
| `r/blindspot-mech` | [`8961ebb1c0789f57dc1912c744f5600d961b3513`](https://github.com/guivff/activation-readers/commit/8961ebb1c0789f57dc1912c744f5600d961b3513) |
| `r/blindspot-internals` | [`3d9a97537b633a32c1a3a97738a8c23cda86e0a6`](https://github.com/guivff/activation-readers/commit/3d9a97537b633a32c1a3a97738a8c23cda86e0a6) |
| `codex/i2-tracks` | [`d2b89a30f0da070c304109dc439f271405b4c1ed`](https://github.com/guivff/activation-readers/commit/d2b89a30f0da070c304109dc439f271405b4c1ed) |
| `codex/i4-e96` | [`f0943b0d13130fd66b3a890775671adee24d9698`](https://github.com/guivff/activation-readers/commit/f0943b0d13130fd66b3a890775671adee24d9698) |
| `codex/w-mech2` | [`97f6cec82809fcef6f838287c6802a54ce0d7acb`](https://github.com/guivff/activation-readers/commit/97f6cec82809fcef6f838287c6802a54ce0d7acb) |
