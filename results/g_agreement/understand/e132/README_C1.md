# E132 clarification 1 — executable CPU protocol

This supersedes the earlier target/block HOLD. E107 is NOT APPLICABLE; no E107 classifier is fit. E116's original329 immediate items and exact110 note2 non-modal items are bound without recomputing modes. Blocks60(primary),52(companion),44(original source-linked E108) are available for all329.

    python results/g_agreement/understand/e132/test_c1.py
    python results/g_agreement/understand/e132/analyze_c1.py --spec results/g_agreement/understand/e132/cache/C1_INPUT_SPEC.json --out results/g_agreement/understand/e132/cache/analysis_c1_once

The CPU-only input spec binds original sealed sources. `bind_c1.py` verifies member hashes and identity/layer/prompt/template/choice/non-modal joins; it does not invoke any prior analysis. The pre-fit source receipt authenticates329items,110nonmodal,6templates,12categories, and134consumed members. No actual labels or readout text are in the public receipt.

PROTOCOL_C1.json fixes all implementation conventions before real source-label extraction/fitting. Folds hold out whole original templates across categories; members recur across categories' folds as allowed. Each category has its own class catalog and OVR models; macro weighting is equal across eligible category/member cells, with per-category tables. Class/fold absence is explicitly reported, not assigned a zero probability. No held-out text enters vocabulary fitting.

Endpoint A uses raw-text models; endpoint B uses models excluding every unigram appearing in ANY canonical member of the category, identically across prompt/readout/combined. All training-fold items remain available; endpoints and the exact110nonmodal subset are scoring subsets of their frozen OOF predictions, never refit subsets. Endpoint membership is the casefolded literal sealed pick-string substring test at the reported block, without new judging/aliases. No target pick alone determines which features are removed.

The item bootstrap resamples within(category,sealed pick) strata, preserving class counts and predictor pairing,2000draws/seed20261030; intervals condition on these counts and fixed OOF models. Every undefined draw is reported; an undefined interval cannot meet the rule. All labels, raw texts, class catalogs, per-item OOF predictions and fitted models remain in ignored CPU cache. Only aggregate results, hashed unavailable-member identifiers and source custody are publishable.

The sole global owner lock is cache/E132_C1_ONCE.json. It is claimed only after complete source validation, before fits. Do not delete/reset it or re-run under another output directory. After a failed locked attempt, owner review is required; a source-only pre-fit validation failure does not authorize any scientific replay. Original E107/E108/E116/E85 guards/results/seals are untouched.
