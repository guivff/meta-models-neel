# E49 input bank frozen — integrator handoff, 2026-10-26

All 16 rows are integrated and sealed now, ahead of Tuesday. W-mechanism's six modules were exported unchanged from `5d34b1ba` and verified against `MECHANISM_SOURCE_SEAL.json`. W-text and W-internals source seals also verify. No build failure, generator fix or row exclusion occurred.

- 2,688 items: 1,344 dev + 1,344 test; each row has 84 + 84, balanced 42 A / 42 B per split.
- All automatic label, length, identical read-token and exact-prefix twin checks pass. 47 CPU tests pass.
- The single pre-seal BOW QA attempt gives **0.50 AUROC on every one of the 12 tracked-state rows**. Descriptors are reported but exempt: topic, language and unit system 1.00; expertise 0.972222.
- PRECALLS and the original blind-call seal are unchanged and verified. No fresh agent or replacement calls were needed.
- No model inference, activation capture or reader scoring preceded the seal.

**Bank seal SHA-256:** `ccc2b3b6e27d0227f2d17f1de0efe2cb9a33cfd4d299656f19d7e4a4e3db43c9`.

`FREEZE_MANIFEST.json` binds the exact bank, QA, PRECALLS and source archive. Its SHA-256 is in `FREEZE_MANIFEST.sha256`. The root-level `BANK_SEAL.json` is a byte-identical publication copy; resolve its relative data files from `cache/frozen_2026-10-26/`, as the manifest specifies. Large/private item and QA-fit files remain in ignored cache.

Stage the archive at `results/g_agreement/understand/e49/cache/E49_INPUT_BANK_2026-10-26.tar.gz`; its hash and repository-relative member paths are in the manifest. It includes the data, raw QA fit, draft/attempt history, PRECALLS and source-seal dependencies. Verify all hashes on extraction.

The input bank is released for the integrator's single registered pod job: full 252-item W1 parity first, followed by block-44 probe/base-text gate acquisition and all registered reader channels. Keep the bank and PRECALLS unchanged. The native channel package and sealed once-only analysis command remain separate execution prerequisites; this data publication does not claim they are complete. Analysis must apply probe ≥ 0.90, base ≥ 0.85 and tracked-state BOW ≤ 0.65 before accessing qualified reader scores; failed model gates are reported/excluded, with no second freeze.

No push or GPU launch was performed by W-text. This committed file is the integrator watcher's publication handoff.
