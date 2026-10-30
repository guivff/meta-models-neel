# W-internals-C registered banks

This is an isolated copy of W-internals-B's sealed-call channel pattern. Keep
`transport.py`, `banks.py`, `runner.py`, `accounting.py`, and the generation
`SOURCE_SEAL.json` unchanged while the E107/E108 generation processes run.
Prospective judging uses the separate `JUDGING_SOURCE_SEAL.json`.

| Bank | Lifetime cap USD | Complete source needed |
|---|---:|---|
| E107 | 15 | 4,297 frozen outside generations; 4,496 belief/truth/S target records; original 25% comparison |
| E108 | 8 | 1,008 continuations, 2,016 native reader outputs, 168 placebo reader outputs, and 1,008 outside generations |
| E109 | 6 | 1,008 Oracle test readouts, both rows, three layers, steered/random conditions; original E104 cohort stays CPU-side |
| E85 | 2 | 800 readouts plus exact source text, original S6 comparison on 200 seeded IDs |
| E106 | 15 | All eligible P/T paired readouts and terminal dispositions; 200 placebo vectors per evaluated reader, original/retrained |

Every phase shares its bank's original canonical ledger and `DISPATCH.lock`
under `wt-internals-b/cache/g_agreement/understand/funded_queue`. No per-phase
cap reset. Global admission counts settled physical spend, evidenced remaining
open caps and unknown physical holds. Completed allocations are released.
The account and canonical HTTP402 latches both apply. Resuming a stopped process
never resends a reserved request whose response/charge is unknown.

Only OpenRouter → `google/gemini-3.1-flash-lite` on `google-vertex/global`, ZDR,
denied collection and no fallback is accepted. Messages and 256/4,096 token caps
are exact frozen bytes. The five approved E107 path exceptions require both
source-user and full-wire hashes; they apply to generation only. No other bank
inherits an exception. Credential/address/machine-identity guards remain active.
Generation `length` retains text and metadata. Charged judging `length` is
terminal UNPARSEABLE. An unknown provider, route, finish or charge stops the bank.

## Generation

From the repository root:

```
python3 -m projects.g_agreement.understand.blind_judge.internals_c.runner prepare-generation --bank E107
python3 -m projects.g_agreement.understand.blind_judge.internals_c.runner prepare-generation --bank E108
```

The prepared, ignored phase directories contain exact `CALLS.json`, source
provenance, `INPUT_SEAL.json`, `WIRE_HASHES.json` and full CPU preflight. After
fresh live route/funding/global checks, publish the source and combined bank
allocation, bind `PUBLICATION.json`, then use `runner run --phase-directory ...`.
Both generation phases are already running from shared commit `b0028d90b`.

## Judging intake

Owner source bundles remain local CPU-only. A unit seal must bind `UNITS.json`
and `CUSTODY.json`, with experiment and complete original source seals. The
custody object records issuer, experiment, verified=true,
complete_eligible_native_grid=true, labels_cpu_only=true and `source_seals` as
`[{seal,sha256}]`. E106/E107 additionally bind the original regex-first unresolved
selection, retained resolved records and the original 25% comparison. No new
regex is invented. E108 extraction requires ground_truth_blind=true. Its later
hit phase requires complete extraction/outside seals and only the registered
NONE/multiple exclusions. There is no early-choice exclusion.

Each unit is exactly `{id,kind,data,rubric}`. IDs are opaque and unique by kind.
No reader, condition, truth letter, source item ID, row join or probe result goes
to the API. Supported kinds:

| Kind | Data | Rubric |
|---|---|---|
| value / old_value | id, property definition, values A/B, readout | exact amended E56 / original BASE |
| eval85 | id, source_text, readout | null: frozen judge205 owns wording |
| s6 | id, readout | original S6, hash `c4b6da30…c529e86f` |
| choice_extract | id, category, continuation | null |
| choice_hit | id, chosen_member, readout | null |
| placebo106 | id, readout, trained_values | null |

`trained_values` is the complete union for nesting_depth, indent_level and
page_range_digit. It has no binary target. Both-valued statements count once;
terminal missing remains null. E85's primary(a), descriptive(b)/(c) and original
S6 codes stay separate. E108 canonical members come from blind extraction; no
alias table is invented. E107 missing truth does not create an undefined B code.

Prepare spec: `{bank,unit_seal,unit_sha256,phase_name}`. Run:

```
python3 -m projects.g_agreement.understand.blind_judge.internals_c.registered prepare --spec SPEC.json
python3 -m projects.g_agreement.understand.blind_judge.internals_c.registered run --phase-directory PHASE_DIRECTORY
```

`prepare` creates independent primary/original contexts with sealed evidence
validators and all prospective retry wires. Each bank retains a single cap.
E107 follows its original no-schema-retry channel; other banks use at most two
registered singleton schema retries. Charged length never retries. Fresh phase
admission/publication and live privacy/funding checks remain mandatory.

E107's exact pre-frozen source/target plan is built by `e107_plan`. After its
complete generation seal, `e107_units` renders only the new outside descriptions;
all native codes/seals remain unchanged. All 37 E81 rows, 209 E82 items (10 with
no canonical truth) and 400 released E86 items stay in the source inventory.

## Output and handoff

Each phase seals all terminal codes, original attempts, actual route audits,
response hashes and physical costs. `JUDGMENTS.json[index].code` is the explicit
adapter interface: E56/S6 objects, exact judge205 object, E108 ground-truth
status/canonical member, boolean hit, or E106 whole-union statement object.
Non-KEPT results are null. Raw responses are retained unchanged and bound by hash.
The first output time is the earliest retained physical response file mtime.

Post each generation/judgment seal, source hash and actual combined ledger cost
to the bank's integrator HANDOFF and `r/WMECH2_HANDOFF.md`. Do not run a competing
statistical adapter: original once-only execution belongs to W-mech2/integrators.
The 30-minute heartbeat checks requests and completes eligible phases through
Fri 30 Oct 2026 06:00 CET, then stops new paid calls and deletes itself.
