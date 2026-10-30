# 2026-10-25 — line-by-line §119 audit of 2137965

Checked against `origin/r/blindspot` at `6dfd8229df284fd6e37b8dffb4888e648530ec64`,
which contains registration `97cfc5dd`. No E25 Qwen score exists.

| Registered requirement | Built behavior | Assessment |
|---|---|---|
| Base Qwen3.6-27B; no adapter or injection | Pinned base revision; no reader loading, adapters, hooks or activation inputs; rejects adapter paths | Matches |
| W1's sealed 2,100 test texts, up to read position | Exact original test IDs/text/token IDs verified; all read positions are final prefix tokens; 25 rows × 84 | Matches |
| W1 frozen candidate phrasings verbatim | Both original Oracle pairs, including literal bullet prefixes; no rewriting or wording selection | Matches |
| Item text + one newline + candidate | Joint tokenization of precisely that concatenation; no chat template or extra special tokens | Matches |
| Mean per-token candidate log probability | Causal suffix tokens only, normalized by their count; all 8,400 real-tokenizer boundaries verified; full-logit CPU reference passes | Matches |
| P = median true-candidate score over items | Mean the two frozen phrasing scores per item, then median over 84 items | Matches with pre-score aggregation convention matching W1; §119 does not separately specify phrase aggregation |
| D = AUROC of true-minus-wrong margin | Literal truth-aligned margin against A/B labels implemented provisionally; conventional fixed A-minus-B AUROC is a separate diagnostic | **Unresolved registration ambiguity. No binary target is stated for the truth-aligned margin. Launch and label join are held; no assumption is silently adopted.** |
| Spearman for both P and D against W1 Oracle asked AUROC across 25 rows | Native Oracle44 W1 reference; 2,000 draws of 25 rows with replacement; percentile 95% CIs | Matches |
| Structure vs content median P test | Content median minus structure median, 2,000 class-stratified row-bootstrap draws, 9 content/16 structure | Matches; stratification is a dated pre-score implementation choice |
| Prediction rho(P)≥0.50, rho CI above0, class contrast CI above0 | All three conditions retained; alternative rho(P)<0.30 retained | Matches |
| NLA and probe discriminant checks | W1 native NLA42 and probe44 rho for each predictor; same row draws; extra paired correlation differences labelled descriptive | Matches; paired differences are an additional descriptive summary |
| E21 rho=0.48 comparison | Explicit descriptive reference, no invented paired significance test | Matches |
| Seed20261025 | Fixed for all E25 bootstrap draws | Matches |
| Warmed cap min(1.5F+360,1800)s, setup1500s | Enforced; all warm-up/timing work counts in science, retained timing scores, full-scope NO_FIT stop; forecast not yet measured | Matches |

Exact clarification requested from Guiv: define
`D = AUROC(mean_phrasing(score_A) - mean_phrasing(score_B), value_is_A)`
or specify the intended binary target for the registered truth-aligned margin.
Equal positive true-minus-wrong margins on all A and B items give literal D=0.5
even when the correct candidate always wins; conventional A-minus-B AUROC is1.0
in that example. This is covered by a CPU test.

No acquisition difference needs repair. A D ruling will be recorded in a dated
note and implemented, tested, re-hashed and recommitted before launch. The
existing request and its held plan remain unchanged until that ruling.

Delivery update from Guiv: the Claude Code chat named **Integrator** watches
this worktree, publishes commits after its own secret scan, and launches the
committed request. The repository handoff is therefore the delivery mechanism;
no direct chat message or owner push is needed. The earlier contact uncertainty
in NOTES_2026-10-25.md is superseded by this information.

## Dated resolution — §119 clarification 1, e4225a1e

Guiv confirmed the fixed A-minus-B definition, including equal averaging of the
two frozen phrasing scores per value. The rebuilt analysis now has exactly two
registered predictors, P and this D; the provisional truth-aligned D is removed.
The request is REQUESTED_NOT_ASSIGNED with no scientific hold. All other rows
of this audit still match. Twenty-two synthetic CPU tests pass, including fixed
preference D=0.5 and item-sensitive perfect separation D=1. Input, candidate,
reference and private-label hashes are unchanged. The full dated correction and
delivery hashes are in CLARIFICATION_1_2026-10-25.md and
HANDOFF_CLARIFICATION_1_2026-10-25.json. No actual Qwen scoring occurred.
