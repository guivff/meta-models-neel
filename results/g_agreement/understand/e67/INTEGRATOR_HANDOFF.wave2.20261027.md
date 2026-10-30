# E67 wave2 — READY for Integrator, 2026-10-27

STATUS: READY. E56 and E57 only, separate from wave1 under §184 clarification2. Each source bank’s completed once-only analysis seal, Integrator verified manifest, source output seals and original native job population verify. All16 synthetic/custody tests and the read-only deterministic/verbatim source audit PASS. No judge calls or scientific analysis occurred.

400 sampled native readouts (100 per bank×reader) become800 records: two400-record packets. Eligible test native population per reader: E56 1,092; E57 1,680. Original retained native pilots are included once; injection outputs are excluded. No parseability, naming, probe or content filter. Frozen prompt strings and output text are unchanged. E56/E57 NLA use the512-token cohort.

## Judge delivery

Deliver only these five files from `results/g_agreement/understand/e67/judge_wave2/`:

- CLAIMS_RUBRIC.txt
- CLAIMS_OUTPUT_SCHEMA.json
- packet_01.jsonl
- packet_02.jsonl
- JUDGE_PACKET_SEAL.json

Judge packet01 and packet02 in independent contexts/jobs with the same frozen wave1 rubric, schema, route, model, settings and record-validation/retry convention. Do not provide this handoff, the manifest, maps, source metadata or the other packet. Every record has exactly id, prompt_text, readout. Do not concatenate waves: same deterministic seed streams restart for wave2, so opaque IDs require a separate wave2 namespace/output directory. Wave2 is analysed once and reported separately with the already frozen analysis code/spec; never pool it with wave1. Judging remains in the Integrator’s custody on the authorised route, within the remaining USD4.58 budget recorded in clarification2. This preparation does not call the judge or revise its spec.

## Integrator-only CPU custody

The three private files are physically in:
`cache/g_agreement/understand/e67/wave2/integrator_wave2/`

PAIRING_CONDITION_MAP.PRIVATE.json, SAMPLE_INVENTORY.PRIVATE.json and SOURCE_BINDING.PRIVATE.json have mode0600. Their directory is0700. They were written directly to ignored cache; no private file or symlink was created in the public experiment tree. Public hashes only: `results/g_agreement/understand/e67/integrator_wave2/INTEGRATOR_SEAL.json`.

For another CPU checkout, copy the ignored archive `cache/g_agreement/understand/e67/E67_WAVE2_PRIVATE_CUSTODY_20261027.tar.gz` and verify the SHA256 in CUSTODY_LOCATION.wave2.20261027.json. Extract relative to `cache/g_agreement/understand/e67/`. The exact four-file archive contains the three private files plus INTEGRATOR_SEAL.json. Never Git-add it, put it on a pod, or deliver it to the judge.

## Read-only verification

From the worker repo root (after private CPU custody is available), run:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/guivff/Documents/Neel_Exploration/activation-readers/.venv/bin/python results/g_agreement/understand/e67/audit67_wave2.py
```

This verifies all source/seal hashes and deterministically reproduces the existing packet selection/assignment in memory. It writes no judgments or scientific results. Do not rerun build67_wave2.py: BUILD.wave2.RUN_ONCE.json is consumed and must be preserved. Wave1 files/seals/results remain unchanged. Private basename checks and the active pre-commit scan must pass; `git log --all -- '*PRIVATE.json'` and `git ls-files '*PRIVATE.json'` must be empty.

2026-10-27T21:21:16.671143+00:00 — READY: packets and CPU custody archive sealed, both source analyses verified, read-only audit PASS; awaiting Integrator judging/once-only wave2 analysis. Commit ID is in the worker final and ignored READY receipt.
