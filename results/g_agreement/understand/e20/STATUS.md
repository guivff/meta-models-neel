# E20 status

**COMPLETE: acquired, sealed and analysed once.** Refreshed by the integrator on 2026-10-25 under BRIEF_UNDERSTAND §123
item 4; no score, seal or verdict changed. Findings are in `RESULTS.md` and the §112 result note (`97cfc5dd`); they are
not restated here.

| Stage | Where | Record |
|---|---|---|
| Item freeze | `f5b59ac5` (published `12721e0b`) | `freeze/`, `ITEM_RECEIPT.json` |
| Parser-dev acquisition (240 base-Qwen dev continuations) | pod `urlu8wc2lvz8oj` | GENERATION_SEAL `efdb52ba…`; 206.1 s science, 165.0 s setup, carried forward |
| Parser validation and freeze | `dd145e50` (published `433d39b1`) | `validation_urlu8wc2lvz8oj/`, `PARSER_FREEZE.json` |
| Full five-channel acquisition | pod `jm1vm4gw487fhn` | dev gate: all four rows EVALUABLE; F 5,921.5 s incl. carried, cap 7,200 s; base 5,760/5,760, lens 5,760/5,760; VALIDITY_SEAL `db8f5d75…`, CAPTURE_SEAL `47ab5841…`, SCORE_SEAL `5327e4ce…` (all files match) |
| Once-only registered analysis | `1ea9df11` (published `7eae4a7d`) | `RESULTS.md`, `analysis_jm1vm4gw487fhn/`, REPORT_SEAL (analysis seal `594bbc3f…`) |
| Post-hoc channel-unit note | `4712b52c` (published `42bf2e0c`) | `POSTHOC_CHANNEL_*` |

**Budget (shared E20 ceilings):** science 5,971.3 s of 7,200 s (206.1 s parser-dev + 5,765.2 s full run); setup 401.2 s
of 2,400 s. Full run billed 1.6944 GPU-h. Bookings are in `results/g_agreement/compute.jsonl`.

**Publication:** `LAUNCH_REQUEST.json` and `PARSER_DEV_REQUEST.json` were published with local paths redacted, so their
hashes differ from the local copies that `LAUNCH_SEAL.json` covers; see `REDACTION_NOTE.json`.

## History (status as of the full-launch request, kept verbatim)

# E20 status

Parser validation PASS and parser frozen in dd145e50. All240 independent blind codes were sealed before the one comparison: paren60/60,string59/60,sentiment60/60,fact60/60. No parser reauthoring.

Worker and CPU analysis are implemented;42 CPU tests pass. Full GPU forecast F is pending the warmed gate. Full launch requires integrator publication/assignment; W12 does not block E20 launch on its own pod. W12 work retains priority over E20 analysis. No lens or source-model acquisition performed here.

Prerequisite costs carry forward:206.109454870224science seconds and164.9569981098175setup seconds. Frozen bank unchanged.
