E18 registered analysis is complete and sealed; do not rerun or relaunch.

Run once on CPU at 2026-10-25T05:37:18.657927+01:00 from the unchanged ff9c4e0d analysis source,
after verifying all 138 source pins, input/collection/continuation/forecast seals,
and the complete 840-item grid. Wall time 6.108530 s; zero GPU/API use.

Registered §109 assessment: **mixed**. Format-limit qualifying structure rows: 0/7;
real-suppression qualifying rows: 1/7 (`table_role`). Only `python_depth` meets the
99518d4e donor rule: 56/84 = 0.6667, item-bootstrap CI [0.5595, 0.7619]. Its paired
AUROC gain is 0.0952 [0.0431, 0.1474], below the required 0.10. All ten rows and all
four arms, paired contrasts, donor fractions and CIs are reported without exclusions.

- Report: `results/g_agreement/understand/e18/analysis/RESULTS.md`
- Metrics: `results/g_agreement/understand/e18/analysis/metrics.json`
- Analysis seal: `results/g_agreement/understand/e18/analysis/SCORE_SEAL.json`
- Analysis seal SHA256: `fc08b35217cae932948485b197c8e7d6d83e58c53cf5cec6c6518c9668a95749`
- Once-only command/timing receipt: `results/g_agreement/understand/e18/analysis/ANALYSIS_RUN.json`
- Original collection: `cache/g_agreement/understand/e18/ftoaeyhltzmc32/out/E18_NEW_RUN`
- Collection seal SHA256: `cccfc3501f75cdf318f680ef869af3738b06661f5ae5c10d36929a8a6c4fce11`
- Continuation seal SHA256: `47ccba96c791735201cc194314869d845b83d2c6297e7a5351e0d94ab02e7256`

The registered analysis generated and sealed RESULTS.md and metrics.json directly.
Neither was edited or recomputed after sealing. The launch packet below is historical.

---

E18 is ready for the integrator under §109 clarification `99518d4e`.

Authority: §109 of `BRIEF_UNDERSTAND.md` at `409690ee`. The full brief was read;
the exact snapshot is `BRIEF_UNDERSTAND.409690ee.md`, verified against Git blob
`dc40201cf99497861f1376b6f27ec50d7add660c`. The clarification snapshot is `BRIEF_UNDERSTAND.99518d4e.md`, verified against
Git blob `db82ffaaab7a1d7da833b8684ccb5b706faac2aa`. No registration text was changed.

The donor condition is registered in §109 clarification `99518d4e`, dated
2026-10-25 05:00 CET before any E18 generation or score. Comparison arm is b.
For each item, sign both mean paired log-odds toward that recipient's own truth;
it moves iff s_c < s_b. Ties do not move. A row moves iff its moving fraction is
at least 0.60 and its item-cluster bootstrap 95% CI has lower bound strictly above
0.50 (2000 resamples, seed 20261025). The format-limit rule requires this condition
on the same at-least-four structure rows meeting the original b-minus-a rule.
Primary AUROC/contrast template bootstraps retain seed 20261023. PLAN and the
worker bind the exact rule and clarification hash. No E18 scientific data has
been inspected. The collection code and frozen input archive are unchanged.

The implemented collection uses all 840 test items across the exact ten rows,
unchanged W1 block-44 vectors and original two phrasing pairs. Arm a calls E16's
asked scorer directly. Arms b/c append the native `- ` prefix, exact generated
continuation token IDs and a newline before those same candidates; each forward
re-injects the original recipient activation. Generated EOS remains in this
causal token sequence; only trailing generation padding is removed. Arm c changes
only the continuation, using freshly frozen opposite-truth same-row donors with
seed 20261025. Arm d disables the adapter and presents only the textual lens
continuation in a user turn before the same candidate strings. There is no source
text, activation slot, E16 wording selection, new target capture or NLA load.

One Qwen backbone and Oracle adapter load once in the same process as warm-up.
Setup is at most 1500 seconds. A dev-only smoke and one discarded warm-up for each
of generation/a/b/c/d precede the immutable science clock. The next three dev
units per path are timed inside science. The dev row is chosen before scoring
by the longest frozen candidate-token workload; this is prose_paren. All fifteen
timed units are discarded from scientific outputs but counted in time and F.

F = sum over the five paths of (60 production units × median of three warmed
dev timings), plus the elapsed duration of all fifteen discarded timed units.
Every path must be measured before any test generation. Unknown timings remain
null. The cap is min(1.5F + 360, 2400) seconds, with 180 seconds reserved for
retrieval inside it. Forecast, admission and clock receipts are sealed; no reset
or automatic retry. The worker seals all 840 continuations before asked scoring,
then seals all four arms before a label join. Partial output stays INCOMPLETE.
No measured GPU F exists yet; CPU toy timings are not substituted for it.

Validation: 129 CPU tests pass (46 E18-specific), including prompt order and
recipient injection, donor reproducibility, independent token-level likelihood
checks with a tiny random Llama plus nonzero LoRA, base adapter disabling, all
five timing paths, one-load collection order, and timeout sealing. A separate
CPU dev smoke used the native Qwen tokenizer and the first 16 components of two
sealed dev vectors with a tiny random model; all four arms passed. This is an
operational check, not pretrained-reader science. The normal setup also includes
a full-model dev smoke when launch becomes admissible.

Pull/rebase uses the existing local repository's remote-tracking branch, whose
current tip was verified against GitHub: 74d116af. See SYNC_RECEIPT.json. The integrator still owns pushing
and every pod action. No pretrained-model, GPU or external model API work occurred.

After pull, follow POST_PULL.json: validate the complete840item four-arm grid and
all seals, then run the registered CPU analysis once into a fresh directory. It
writes RESULTS.md opening with the registered prediction and explicit assessment,
all40 per-arm AUROCs/CIs, ten paired b-minus-a contrasts, and the donor fractions,
item CIs and row decisions. Missing or partial grids remain INCOMPLETE.
