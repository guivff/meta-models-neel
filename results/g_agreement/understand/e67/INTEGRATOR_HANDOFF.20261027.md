# E67 wave1 — frozen blind claims packets, 2026-10-27

Authority: §184, bbefdae2. CPU preparation only; no judge or model call and no E67 analysis occurred. E49, E54 and E61 D4 each have verified once-only analysis seals before their native readouts enter this packet. All underlying source hashes are bound in integrator_wave1/SOURCE_BINDING.PRIVATE.json. The original analyses and readouts remain unchanged.

## Delivery and custody

Deliver only the five files in judge_wave1/: CLAIMS_RUBRIC.txt, CLAIMS_OUTPUT_SCHEMA.json, packet_01.jsonl, packet_02.jsonl and JUDGE_PACKET_SEAL.json. The records contain exactly id, prompt_text and readout. No bank, row, reader, arm, original item ID or condition is present. The rubric's first paragraph is the registered claims rubric verbatim; the second paragraph specifies its common JSON interface. The schema allows up to5 claims, SUPPORTED/CONTRADICTED/UNVERIFIABLE, and requires GENERIC precisely when the claims list is empty. It does not substitute a naming or value-statement rubric.

Judge packet01 and packet02 in separate contexts/jobs. Do not concatenate them, supply examples from the other packet, reveal their source inventory, or attach this handoff, the registration, code, private map or WAVE1_MANIFEST. Each sampled readout appears once in each packet, under independent IDs; its two conditions are assigned to opposite packets. Both packets are independently shuffled and contain an unlabelled mixture of pairing conditions.

integrator_wave1/PAIRING_CONDITION_MAP.PRIVATE.json is for the Integrator only. It binds the two IDs for each sampled readout to matched/mismatched condition, packet number, bank, reader, frozen row, sampled item ID, donor item ID/arm, source record pointer and verbatim prompt/readout hashes. SAMPLE_INVENTORY.PRIVATE.json records the selected item IDs, arm counts, seeds and truncated-NLA cohort flags. SOURCE_BINDING.PRIVATE.json records all original analysis/readout/prompt seals and hashes. INTEGRATOR_SEAL.json seals these three private files. Never give this directory to the judge or stage it on any pod. There is no pod job for E67.

## Wave1 sample

598 sampled readouts →1196 judge records,598 per packet:

| Bank | Oracle lens | NLA |
|---|---:|---:|
| E49 |100|100|
| E54 |100|100|
| E61 D4 |99|99|

Each bank×reader sample is uniform without replacement over the sealed native test-item universe, seed20261027, one native readout per frozen item. D4 takes33 items from each arm for exact balance under the up-to100 cap. Oracle and NLA use the same deterministic sampling convention. There is no gate, label, naming, malformed-output or readout-content selection. Exact strings from the sealed text field are retained, including any empty/malformed readout.

D4's own prompt is its normalized frozen read_prefix, at the native capture point. Future completion_suffix/answer text is excluded. E49/E54 use their exact frozen full prompt text. Donors are uniformly sampled using seed20261028 from other test item IDs in the same frozen row, with replacement across sampled readouts. D4 donors can be from another arm of the white_bear row; there is no unregistered same-arm or opposite-label restriction. The sampled mismatches happen to have no byte-identical own/donor prompt texts. Both prompt conditions retain the same readout verbatim.

E49 and E54 NLA belong to the registered128-token-limit cohort; D4 NLA is the512-token cohort. These flags are in the private inventory/map so the Integrator reports truncated-cohort results separately, as §184 requires. No further truncation or text normalization has been applied here. Oracle token limits are not inferred by this packet builder.

## Judge path and analysis

W-internals supplies the claims-rubric judge path on the authorised E56 route/privacy settings. Integrator holds the API credential and runs judging within the separately authorised USD5 cap. No credential is present in these artifacts. Use the same frozen rubric, schema, template, model, route and settings for both packets and retries. Per judging clarifications1–2, retain valid records independently; retry only each failed record alone, unchanged, at most twice more. Remaining failures are UNPARSEABLE, excluded from category shares and counted/flagged as registered. packet67.validate_claims is a dependency-free validator of this exact wire schema; it is not an analysis or judge invocation.

Integrator owns the once-only E67 analysis and must freeze its implementation before opening judgments. The private map supports paired matched-minus-mismatched item bootstrap and the registered per-reader fabrication/generic/support rates. This worker has not changed or evaluated R-F1, R-F2 or R-F3. Keep packet judgments opaque to the worker's preparation step.

## E56 / E57 pending, separate immutable wave

Their once-only ANALYSIS_SEAL files did not exist at wave1 preparation. No E56/E57 native readout or shared pilot readout file was opened. D4's retained pilots are base-probability jobs only, so its full native readout universe comes from the separately sealed D4 stage files.

Add E56/E57 only after each bank's once-only analysis has sealed and verifies, in a separately committed wave. Preserve all wave1 IDs, samples, donors, records, rubric and seals. Do not rebuild or append to either existing packet. WAVE1_MANIFEST.json records the exact pending seal paths. It is metadata for the Integrator, never judge context.
