# E101 vectors and retained E100 a/b — CPU handoff

Authority: §209 and §208 deviation1 (69f8c08e). VECTOR_SEAL.json is the complete CPU package seal; public/INPUT_SEAL.json is the **only E101 payload seal to stage with directions**. All seven rows have independent block44 and block42 directions. No model, reader, judge, dose-selection or scientific-analysis calls ran here.

## Interface

`public/MANIFEST.json` has fourteen row/block entries. Each `d` is a float64 unit vector of5120 elements; `raw_norm` is the norm of the corresponding unnormalized dev class-mean difference. `r` points to the single shared random unit direction for that block. Use

`h_prime = h + alpha * raw_norm * sigma * direction`

with `direction=d` for steering and `direction=r` for its matched random control. CPU label convention is d_raw=mean(label1)-mean(label0); sigma=1-2*true_label, targeting the opposite class. Do not apply norm twice. The random seed recipe is normalized Gaussian from default_rng(SeedSequence([20261028,block])). It is shared across rows and is not orthogonalized separately to any row.

`cpu_only/DEV_JOINS.DO_NOT_STAGE.json` records exact dev IDs, class/value mapping and sign convention; `cpu_only/SOURCES.json` binds sealed capture paths, orders and both block arrays. Never stage either file or the cpu_only directory on pods. Original IDs, labels and target joins stay CPU-side. The runner may stage precomputed signed deltas via its own sealed input builder; this direction-only package does not authorize putting label columns on GPU.

Five block44 raw directions are reused exactly from original E79 CPU_DIRECTIONS.npz: E57 ArmA nesting_depth/indent_level/page_range_digit and E59 ArmB format_plan/language_plan. Each exactly matches its sealed dev class means. The E56 block44 directions and all seven block42 directions are fitted using their own block's dev captures. All84 dev items (42/class) are used, matching the original E79 construction; no test activations enter fitting. Raw d arrays remain in cpu_only for verification; only unit d and scale are needed by runner.

## Block44 J fractions

| Row | J fraction |
|---|---:|
| language_plan | 0.424393 |
| format_plan | 0.408097 |
| fact_recall | 0.350300 |
| language_continuation | 0.361009 |
| nesting_depth | 0.322574 |
| indent_level | 0.227322 |
| page_range_digit | 0.267270 |

Chance is0.27 (exact sqrt(384/5120)=0.2738612788). BUILD_REPORT.json retains unrounded fractions and raw norms. These dev-only geometry checks are not behavioural or reader results. E79 ArmA's null remains the first causal result in reporting.

## E100 a/b reuse

Reuse `results/g_agreement/understand/e100/vectors/HANDOFF_REQUEST.json` and its sealed public package unchanged. E100_AB_REUSE.json binds its bundle, input seal, Q_J/Q_R files and all eight84-item pairing files. All672 pairings are checked as same-row/opposite-class test pairs and exactly reproduce default_rng(20261028) choices in original frozen order. P_J=Q_J@Q_J.T and P_R=Q_R@Q_R.T; Q shape5120×384. Use matrix-free application. NLA block42 uses that same registered block44 J basis for E100 a/b. Both bases and all pairings already exist; no duplicate random basis or new pairings were generated.

Only transplant/J_swap/perp_J_swap/R_swap/perp_R_swap remain active for E100. u_tok, all direction-injection conditions and upstream items are withdrawn. The retained E100 tense_implicit row belongs to E100 a/b only, not the seven E101 rows. Stage the two basis archives plus the existing reported or missed group archive per the E100 handoff; CPU-only history is never staged.

## Execution boundary

W-mechanism/Integrator bind the original frozen token arrays, read indices, continuation scorers, h44/h42 carriers and this package. Dose grid0.5,1,2,4 is dev-only; commit the smallest eligible alpha* per row before test. Block42 must use its own d42 and raw_norm42, not d44. No alpha*, behavioural flip, target report, or model-dependent norm ratio is claimed here. The >1.5 distortion flag is reported, never used to exclude. This package is CPU-data readiness, not GPU or judging admission.
