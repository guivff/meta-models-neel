# E103 deviation1 execution binding (§221 item1)

CPU-only separate once namespace; the original analysis_late/e103.py prepare,
analyze and common/statistics remain byte-for-byte pinned. This wrapper does not
parse/revalidate raw judgments or call the judge. W-internals-B owns minimal
validator correction and sole reparse; I-5 supplies source-pointer normalization.

Run from the checkout containing I-5's inventory after source commitment AND
published/verified corrected binding admission:
python3 -m projects.g_agreement.e103_deviation1.run --spec <I5 SPEC.json>
SPEC schema is the original E103 schema plus label, deviation, authority_commit,
strict_analysis_seal={path,sha256},strict_guard={path,sha256}. Exact label is
validator-corrected (E103 deviation 1). Authority f60fd54f pinned. Output basename
validator_corrected_deviation1_once; fixed global guard e103/deviation1/ANALYSIS_ONCE.json.
Original e103/ANALYSIS_ONCE.json and strict analysis ab666368 remain unchanged.

No corrected real outputs opened by wrapper authorship/tests. Seven synthetic
checks cover authority, unchanged scientific functions, separate custody and
replay refusal. Any currently reported auto-review publication block at I-5
remains a block: do not use this wrapper to route around it. Wait owner clearance
and shared published source/judgment admission before execution; source readiness
is not execution admission. R-5 review on corrected result arrival.
