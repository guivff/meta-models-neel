# E85 readout-word classifier, §238 clarification 2 item 2

CPU only. No new readouts. The command and exact estimator are frozen in PROTOCOL.json.

Run synthetic tests before a real fit:

    python results/g_agreement/understand/e85/readout_bow238/test_bow238.py

Once complete original native sources exist:

    python results/g_agreement/understand/e85/readout_bow238/bow238.py --spec CPU_INPUTS.json --out results/g_agreement/understand/e85/readout_bow238/cache/analysis_once

CPU_INPUTS.json stays on CPU. It names original labels (`path`, `sha256`) and `sources`, each with `root`, seal-relative `seal`, exact seal `sha256`, and `members` (original JSON batch relative paths). A seal's `files` mapping supplies each member's SHA256. Readouts must be original native Oracle repeat0 records, not rerendered prompts, source spans, reconstructor outputs or synthetic replacements. No target or label is sent to a pod.

Coverage validation precedes the exclusive once lock. Missing DEV texts cause a source hold without fitting or consuming the lock. Failure after a real fit requires owner review; do not remove/reset the lock or retry under a new path. The output directory must not exist. Output model, coefficients and detailed source bindings stay in ignored cache. Only aggregate AUROCs, intervals and requested top words are eligible for a small results publication after review for unintended private content.

Current source status: BLOCKED_MISSING_DEV_NATIVE_ORACLE_READOUTS. Original E85 release has 400 TEST Oracle texts and no DEV-native packet in W-text custody. The source gap was already recorded for E125. Do not invoke the real command against the available TEST-only packet. Neither AUROC threshold has been evaluated.
