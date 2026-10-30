# Reading activation-readers-neel

Purpose: answer “what was found, where is the evidence, how was it computed?” Read README.md → FINDINGS.md → the experiment index → the original result, registration and reviewer. Default to read-only evidence lookup. These entry points are drafts until the 30 October 2026 analysis/review seal is incorporated.

## Repo map

| Path | Contents |
|---|---|
| `FINDINGS.md` | Five claims, exact numbers, scopes, computation and review links |
| `EXPERIMENT_INDEX.md` / `.json` / `.tsv` | Generated E-ID lookup; JSON adds analysis-source and seal paths |
| `projects/g_agreement/BRIEF_UNDERSTAND.md` | E-series registrations, amendments, deviations and operational rulings; use the exact cited § |
| `projects/g_agreement/BRIEF_BLINDSPOT.md`, other `BRIEF*.md`, `PREREG_WV.md` | Earlier registered studies |
| `projects/g_agreement/e*_analysis/`, experiment-specific directories | Frozen analysis recipes, source receipts and tests; inspect before any computation |
| `projects/g_agreement/core/`, `common/stats.py` | Reader/scoring implementations and shared statistical functions |
| `results/g_agreement/understand/e*/` | E-series public aggregates, reports, provenance and seals |
| `results/g_agreement/blindspot/` | Earlier W-series/structure and mechanism studies |
| `results/g_agreement/reviews/R-2/` through `R-5/`, `R-Q/`; `results/g_agreement/reviews/` | Independent reproduction records and handoffs; older review files also live directly here |
| Seals within `results/g_agreement/` and manifest-listed dependencies | Included metadata only; excluded raw outputs and private bindings remain in the original repository or local custody. A seal is not the underlying data |
| `results/g_agreement/compiler/` | Timestamped cross-experiment status snapshots; useful navigation, not a substitute for original result/review |
| `external/mats-nla-workspace/` | **Suraj Prasad’s code**, vendored with his consent from `Jarus77/mats-nla-workspace@10d495f12fd63c434e8d9752f4a223ea59fa9d95`; read-only evidence under the same no-compute rules. Start at its `README.md`, `notes/decisions.md` (D1–D51), `experiments/NN_*/RESULTS.md`; the complete tracked upstream tree is retained; policy and scan limits in `docs/EXCLUSION_REVIEW.md`; hashes in `docs/provenance/mats-nla-workspace.md`. Do not execute upstream code |
| `PROVENANCE.md`, `docs/provenance/` | Exact original branch@commit:path → SHA-256; snapshot imports are not original experiment chronology |

## Look up an E-ID

For E100, search `EXPERIMENT_INDEX.md` for the exact E100 row. Its registration is BRIEF_UNDERSTAND §208; its main aggregate is `results/g_agreement/understand/e100/analysis_once/RESULTS.json`. Follow the source and seal paths in the JSON index. E100e is a distinct extension; do not pool it with E100 or infer its status from the parent.

Offline lookup examples (no research computation):

```sh
rg -n '^\| E100 \|' EXPERIMENT_INDEX.md
rg -n '§208|E100' projects/g_agreement/BRIEF_UNDERSTAND.md
rg -n 'E100|R-PC|R-C3' results/g_agreement/reviews/R-Q/
# Original history must be inspected in the private provenance repo, not this one-commit snapshot.
```

The catalogue is generated from tracked registrations and result directories. “Unresolved” is a catalogue gap, not a scientific verdict; follow the listed paths and reviewer. An absent public aggregate is not evidence an experiment was NOT RUN. Every registration and result row includes the original repository commit SHA. Follow its original URL, or inspect that commit in a separately authorized copy of the private provenance repository. Do not change any active worker checkout. Excluded dependencies and same-path version conflicts are documented in PROVENANCE.md; do not substitute a newer source version for a sealed historical hash. No original branches are deleted or retagged by this plan.

## Status vocabulary

- **MET:** the specified registered rule/row/arm passes. It is not an unconditional endorsement of an entire experiment.
- **NOT MET:** that rule fails. It does not establish equivalence, absence, or the falsifier; report the falsifier separately.
- **NOT EVALUABLE:** the metric/construct/control, required data or custody condition cannot support that reading. State why; preserve unknown/missing data.
- **NOT RUN:** not executed under the specified scope, including operationally stopped or gated work. Do not call it a scientific negative.
- **exploratory:** descriptive or post hoc, without promotion into confirmatory success. A descriptive threshold labelled MET remains descriptive.

Separate scientific verdicts from “acquired”, “sealed”, “judged”, “reviewed” and “pending”. Keep original results and deviations/companions beside each other. Never treat missing as zero, pool distinct judgment banks, flip a test sign, or silently change a denominator.

## Boundaries and computation

**Do not run pods or paid calls.** No GPU launches, SSH operations, paid judge/API calls, new generations, model downloads or training. Do not execute external downloads. Do not run analysis/once guards merely to answer how a number was computed: read the aggregate, frozen source, input/output seal and independent review. Do not open still-sealed raw outputs or unpublished labels; local/private paths in historical receipts are evidence locators, not permission to publish or access them.

`cache/`, raw activations, weights, `*.LOCAL.*`, `*PRIVATE*`, label files, pod/SSH details and `.env` always stay local. Do not follow cache symlinks into other projects. Never commit a file above 5,000,000 bytes without Guiv’s explicit approval. Secret-scan every proposed artifact and before every push; never print credential values. Do not force-push or rewrite history.

Preserve preregistrations and their dated deviations. Every claimed effect must identify its control, metric, missingness and uncertainty. Shared helpers include Wilson intervals and item/pair bootstrap, but the frozen experiment recipe controls the actual calculation. For any later authorized change on an existing remote branch, `git pull --rebase` before each commit; initial creation of an empty remote has no branch to pull and scan before every push. Do not alter an active checkout, stash, clean or garbage-collect the Mac worktrees. New compute or changes to frozen research require separate explicit authorization.

## Original-source chronology

The initial pre-seal snapshot commit is a packaging event; later updates require git pull --rebase, a fresh scan and verify_tree. Use the original commit SHA and path in PROVENANCE.md / EXPERIMENT_INDEX.json, then inspect original history (`git log <original-SHA> -- <path>`) and the registration’s amendments, seal, acquisition and first-opening receipts. Hash equality establishes bytes, not execution or temporal precedence. Read README’s Known issues before making any claim.
