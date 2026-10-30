# E36 setup allowance — §146 addendum 2, 2505b0f8

READY_FOR_INTEGRATOR_BINDING. One pod; no sharding. This dated operational
amendment adds at most 900 seconds of setup after pod creation, outside the
unchanged science cap min(1.5 × F + 360, 59,447). F includes the full parity
gate. Setup and science both remain inside the 60,000-second aggregate
custody budget, after subtracting all prior custody.

The maximum new allocation is min(60,000 − actual prior custody,
900 + min(1.5 × F + 360, 59,447)). At F=32,600, the science cap remains
49,260 seconds and the maximum allocation becomes 50,160 seconds, subject
to the aggregate remainder. Include the reported 552.8-second attempt and
84.8-second setup-only retry, plus any other custody, in the supplied prior
usage. The package does not invent or reset the integrator's ledger.

The worker rejects entry or completion of setup beyond creation +900.
After Oracle loading and before the full parity gate it starts a one-time
science clock, bounded by both the unchanged science formula and the
external stop. Unused setup time does not extend science. The science-clock
receipt is sealed with the outputs. Batch forecast and retrieval checks
remain in force. No parity, bank, candidate, channel, H1–H5 or scoring
operation changed; no automatic retry is added.

Use this commit's LAUNCH_REQUEST.json, STAGING_MANIFEST.json and archive in
STAGING_ARCHIVE.json. The existing binding command generates the refreshed
plan and assignment template; bind actual cumulative prior custody and
external stop before launch. Earlier dated handoffs remain historical.

115 CPU tests pass, including setup expiry, separate clock boundaries,
unchanged science formula, no clock reset and aggregate accounting. All 11
prepared-bank hashes remain unchanged. Integrator publishes and launches;
W-text has pushed nothing and performed no GPU operation.
