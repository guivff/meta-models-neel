# E36 operational re-pin — 26 October 2026, before production

Authority: §137, commit 1721470e. This supersedes the operational staging
instructions in HANDOFF_READY_2026-10-25.md. The 25-row bank, freeze, checked
labels, candidates, channels and H1–H5 are unchanged. No E36 model calls have
been made by W-text; the integrator must include all provider custody in the
unchanged 28,800-second aggregate cap.

The new request requires W1 score parity before any v2 capture or scoring.
It uses E28's exact sealed 252-item gate: prose_sentiment, prose_paren and
python_string, 84 items each, stored W1 block-44 vectors, both frozen Oracle
phrasing pairs and A-positive labels. Only their arithmetic-mean paired
log-odds AUROCs are compared with the sealed W1 references. All three absolute
differences must be ≤0.02, as §137 specifies. E28's original reference file
retains its historical 0.03 field; E36 code enforces 0.02. A failure stops with
the scores and verdict retained; it cannot trigger a retry or tuning.

The parity check calls the same unmodified Oracle scoring backend used for
E36 production. It uses stored W1 activations, so it certifies score parity,
not fresh-capture parity. No W1 text was opened for this amendment. E36 authors
finished and the entire bank was frozen before the parity reference was read.
The only labels staged are the separate 252 gate labels; all v2 labels remain
on CPU. Production outputs include lengths and padding per item, source hashes
and interpreter/package versions for §137's later environment impact audit.

Verify STAGING_ARCHIVE.json and STAGING_MANIFEST.json, then extract into the
prepared repository. Use the new LAUNCH_REQUEST.json binding command. There
are now eight phase forecasts: oracle_setup, parity, capture,
oracle_descriptive, oracle_value_word, continuation, nla_setup and nla.
Parity comprises 33 batch-8 calls and is included in the cap and warmed
forecast. No separate setup/parity allowance is added. Bind actual assets,
prior custody and externally enforced deadline before launch as before.

The source-ready request and archive are re-pinned together. Existing shared
runtime source pins match the current checkout; their bytes and scientific
recipes were not changed. Changed sources are limited to this operational
gate, binding enforcement, audit receipts and CPU tests. Keep the old archive
as historical evidence; use the new archive named in STAGING_ARCHIVE.json.
Integrator alone sweeps, publishes, launches and returns complete sealed
outputs. W-text has pushed nothing and launched no GPU job.
