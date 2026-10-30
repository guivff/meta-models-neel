# E85 readout words: exploratory grouped cross-validation

Completed once under §238 clarification 4 item 2 (`e97f837b0`). **CARRIED_IN_WORDS: the addressed cue is carried in the readout words under the registered ≥0.80 threshold.**

| Classifier | Out-of-fold AUROC | 95% item-bootstrap CI |
|---|---:|---:|
| addressed = 1 | 0.987525 | [0.977847, 0.994575] |
| genre = 1 | 0.987250 | [0.975073, 0.996551] |

All400 original TEST native Oracle readouts entered exactly once;100 matched item quartets, four genre×addressed variants per quartet. Five seeded folds hold out20 whole quartets each (80 readouts), exactly balanced in both factors. Each training fold fits its own word-unigram vocabulary and two L2 logistic models; held-out texts enter neither vocabulary fitting nor model fitting. No hyperparameter tuning, calibration, full-corpus refit or new readouts. Existing empty texts:0. Original absent-DEV protocol remains historical and was never fit.

The2000 bootstrap resamples draw matched item quartets with replacement, retaining all four variants, seed20261030. Intervals use the fixed out-of-fold predictions; models are not refit inside the bootstrap. This is exploratory cross-validation, not an independent held-out DEV/TEST fit.

The finding concerns information recoverable from the words, including distributed wording differences. It does not establish evaluation awareness, intentional withholding, or causal use of those words. The genre model is a separate control on the same folds.

## Top weighted words

Weights below average the five training-fold coefficients, with0 for a word absent from a fold. Positive weights favour class1 (addressed or evaluation genre); negative weights favour class0. No additional all-item model is fitted.

### addressed

| Positive-class word | Weight | Negative-class word | Weight |
|---|---:|---|---:|
| department | 1.141398 | mentioned | -2.149296 |
| recommends | 0.965955 | local | -0.999490 |
| last | 0.770072 | stated | -0.848951 |
| incident | 0.753478 | park | -0.735023 |
| sentence | 0.693170 | visit | -0.674226 |
| author | 0.668582 | inspection | -0.555889 |
| more | 0.586148 | step | -0.520804 |
| instruction | 0.581003 | for | -0.502788 |
| police | 0.565369 | this | -0.487263 |
| that | 0.528794 | is | -0.472630 |
| passage | 0.513450 | upcoming | -0.468644 |
| of | 0.509654 | which | -0.374866 |
| demonstration | 0.405177 | states | -0.347992 |
| should | 0.394361 | answer | -0.342173 |
| website | 0.385225 | in | -0.330154 |
| suggests | 0.372469 | explanation | -0.313237 |
| find | 0.372417 | given | -0.307619 |
| provided | 0.346065 | tourism | -0.307101 |
| safety | 0.336961 | office | -0.306342 |
| out | 0.336050 | best | -0.284666 |

### genre

| Positive-class word | Weight | Negative-class word | Weight |
|---|---:|---|---:|
| go | 1.268227 | last | -1.115693 |
| described | 1.164540 | paragraph | -0.912774 |
| stated | 1.040702 | visit | -0.797988 |
| in | 0.919512 | report | -0.796919 |
| author | 0.898264 | explicitly | -0.796755 |
| inspection | 0.754517 | step | -0.719686 |
| main | 0.600158 | sentence | -0.679659 |
| action | 0.499276 | incident | -0.644873 |
| for | 0.459896 | find | -0.570590 |
| read | 0.427821 | suggests | -0.557852 |
| describes | 0.422517 | more | -0.485106 |
| park | 0.376477 | of | -0.462605 |
| given | 0.353921 | future | -0.417832 |
| consult | 0.330858 | directive | -0.417221 |
| takes | 0.321430 | create | -0.400072 |
| answer | 0.315695 | detailed | -0.400072 |
| instruction | 0.308242 | plan | -0.400072 |
| weather | 0.305843 | passage | -0.393892 |
| history | 0.304922 | accurate | -0.390702 |
| forecast | 0.304723 | are | -0.390702 |

## Custody

Canonical ANALYSIS_SEAL SHA256 `e3d01a895d23fc14f964c66f96fc094c6ba530d11ec34aa09b35c0a3fdbd0af9`. Executed source `09878c5065a14e8742d6f43edaaa9fbc373afa6f` and six synthetic tests/fresh imports were published before the first real fit. Original native seal `0e630fce…` and thirteen batch hashes are bound in CV_EXECUTION_RECEIPT.json. Labels, folds by ID, fitted models and per-item OOF predictions remain CPU-only in ignored cache.

An earlier input-validation attempt stopped on stage metadata before fitting, creating no analysis directory or once lock. The immutable original source and failure receipt are retained; the tested repair only selects numbered batch files. The successful analysis consumed the canonical CV lock once. No retries, re-analysis, new reader/model calls or GPU use. Independent R-2 review is pending.
