# E66 schema-first sampling handoff

Authority: §183 e94784b009f4c3413a7ea71b39ab5e22c561e135. CPU only.

## PROVISIONAL, pending coordinator ratification

Recorded 2026-10-27T14:55:55.149403+01:00, before prompt payloads or readout columns are opened.

- Use the frozen main readouts/transcripts files, not later dense reads or hand-picked subsets. The card describes 156127 positions and 2009 transcripts, unlike the shorthand 150k rollouts. A rollout is one transcript identified by (source, tid); one output per transcript.
- Use `rl_greedy`, the post-RL Oracle-lens greedy readout. The registration asks for one readout, not an SFT-vs-RL comparison or best-of-N selection. Do not inspect readouts to choose the channel.
- Recover the complete rendered prefix through token pos inclusive. Require exact tokenizer decode equality with published full text and exact agreement with the position token. Never infer state from the truncated 400-character left context.
- Structural code detection is conservative: fenced code blocks with a recognised programming language (or unlabelled fence); ignore comments and escaped quotes; maintain quote/bracket state within the current fence. Unrecognised languages, ambiguous code, and malformed token alignment are excluded, not treated as prose. S3 requires a Markdown header separator and a known pipe-delimited column; S4 counts literal leading spaces, not tabs.
- Overlaps at one position use the registration's order S1, S2, S3, S4, then C. C requires plain prose outside fences, with alphabetic content and no table/code markup.
- To honour one readout per rollout without cross-stratum duplication: assign each transcript one uniformly chosen eligible read position using a seed-derived transcript RNG, then stratify. Sample uniformly without replacement up to 150 transcripts per resulting stratum, seed 20261027. Report both pre-assignment eligible-transcript counts (overlaps allowed) and disjoint sampling-frame counts. Strata with <50 in the disjoint frame are excluded. This avoids outcome-based position selection and priority depletion across strata.
- Eval/RL is source metadata only: rlvr1 is explicitly training in the card; other families remain UNKNOWN unless the card explicitly identifies an evaluation split. Never infer eval status from readout content, reward, or lens checkpoint.
- Blind packet contains only opaque id and readout text. It and the private linkage map stay under ignored cache; commit code, hashes and aggregate counts only. No judge call is made by W-core.

## Schema report

Readouts: source, family, tid, task_id, trial_name, passed, reward, thinking,
reasoning_effort, turn, role, pos, token, left_ctx, next16, rl_greedy,
rl_s1..4, sft_greedy, sft_s1..4, h51_norm, n_tokens_full, truncated,
lens_rl_ckpt, lens_sft_ckpt, model, extra, next16_ids.
Transcripts: tid, source, family, task_id, trial_name, passed, reward, thinking,
reasoning_effort, n_tokens_full, truncated, text, ids, positions, pos_roles, extra.
Full text and token position are recoverable in principle through the transcript
join, subject to exact alignment checks. No explicit eval/RL flag exists.

The card was inspected only for field/provenance/capture descriptions. No example
readout sections, data viewer, readout text or J-lens file was opened by the agent.
Anonymous downloads pinned to revision 226c6dce62ed88d5981ca864d0c99d3f082ccee6.

## PROVISIONAL, pending coordinator ratification — duplicate identity

2026-10-27T15:00:01.288002+01:00

Metadata-only validation found one duplicated (source, tid) key, still duplicated with thinking. Programmatic hashes establish distinct text/IDs/positions. Exclude both ambiguous transcripts and their positions rather than guess a join. No readout column has been opened. The initial pass stopped without a sample; preserve sample-v1 as the failed attempt.

## Sampling correction before readout materialisation

2026-10-27T15:02:40.261384+01:00 — PROVISIONAL, pending coordinator ratification.

The initial prompt-only pass exposed a specification error in the provisional
position-first convention: applying the <50 exclusion after random assignment
would exclude strata with >=50 truly eligible transcripts. sample-v2 is retained
as an INVALID_SAMPLING_DRAFT, not a registered sample. No readout was opened.
Eligibility is now counted before resolving overlaps. All five strata meet >=50.
Use seed-fixed randomised rounds: shuffle active stratum order each round, draw
one uniformly random still-unselected eligible transcript per stratum, then one
uniformly random qualifying position of that transcript in that stratum. Repeat
until caps (150) or pool exhaustion. This implements one-per-rollout, up-to-150,
and uniform draws conditional on no duplicate rollout. It is not a claim of
unconditional equal inclusion probabilities across overlapping strata. Report
pool-exhaustion shortfalls, never reclassify them as <50-eligible exclusions.
The correction follows the registered eligibility threshold; no readout outcome
was available or used. Prompt-derived eligibility counts were already known at
this correction, which is explicitly disclosed rather than backdated.

## Completed handoff

Final packet: `cache/g_agreement/understand/e66/sample-final/BLIND_PACKET.jsonl`.
Private linkage: `cache/g_agreement/understand/e66/sample-final/STRATUM_MAP.PRIVATE.jsonl`.
Selection and once-only materialisation lock are alongside them. These files
remain ignored and local; integrator takes custody of the private map. No pod
upload or judge invocation was performed. Judge authority remains §183/E56 route.

Eligible / selected distinct transcripts: S1 240/128, S2 286/137, S3 76/68,
S4 80/59, C 1413/150. Total 542, with no transcript repeated. Eligibility counts
overlap; selected counts do not. All strata satisfy >=50 eligible. Structural
shortfalls are due to cross-stratum overlap, not exclusions based on readouts.

1413 transcripts passed exact alignment, 594 failed exact alignment, and two
had ambiguous identity. Structural detection is limited to conservative fenced
code and verified markdown tables; it does not claim exhaustive natural-code
coverage. The 400-character context was never substituted for full text.
The sample is from positions across rendered transcripts, including role-tagged
user, assistant, reasoning and tool text, not user-message positions alone.

Six CPU tests pass, including comments/escaped strings/brackets, table columns,
seed reproducibility, no duplicate rollouts, and blind one-shot materialisation.
No person or agent inspected real readout text. Only the materialiser accessed the readout column
to copy the fixed selection; stdout contains aggregate counts only.

## Coordinator follow-up and judge handoff

2026-10-27T15:33:55.227975+01:00 — User accepted inclusion of all strata and the existing shortfalls.
The consolidated SAMPLING_CONVENTIONS.md supersedes earlier provisional sampling
notes as the reviewable description; ratification remains pending.
INTEGRATOR_REQUEST.json authorises delivery of the unchanged 542-record packet
for the E56-route judge, USD 3 hard cap inside the existing USD 15 authorisation.
Exact packet and private custody paths/digests are in the request; only the
packet is judge input. No W-core judge calls or new spend occurred.

## RATIFIED — final integrator handoff

2026-10-27T15:38:14.027586+01:00 — §183 E66 clarification 1 (23a2e5c9), explicit coordinator message.
All conventions ratified as written, including the disclosed 15:02 correction.
All five strata included at n S1=128, S2=137, S3=68, S4=59, C=150; shortfalls
22, 13, 82, 91, 0 respectively. R-G3 is UNSTRATIFIED; no eval flag exists.
INTEGRATOR_REQUEST.json is READY, USD 3 hard cap within the existing USD 15.
Packet and private-map hashes reverified without displaying readout text.
The source paths are live in this shared workspace; the ready notice is
cache/g_agreement/blindspot/INTEGRATOR_E66_READY.json. No judge calls by W-core.

## Once-only analysis preparation — 2026-10-27T22:17:53.901956+01:00

PROVISIONAL, pending coordinator ratification (recorded before opening any judge
output or private stratum map in this task): use the repository Wilson 95% helper
(z=1.96); normalized judge rows contain id, S1, S2, S3, S4, topic,
eval_awareness, with six strict JSON booleans. This is a transport convention,
not a rubric change. The integrator normalizes and seals the full blind judgments
before invoking analysis. Missing/unparseable/duplicate judgments invalidate the
analysis rather than changing denominators or treating missing as false. No
readouts are opened by this command. Only the integrator executes the private
post-judging join. R-G3 remains unstratified. All registered thresholds unchanged.

### Initial once-only analysis contract (superseded below)

Run `sh results/g_agreement/understand/e66/ANALYSIS_COMMAND.sh` from this
checkout, as the integrator, only after judging. ANALYSIS_SPEC.json pins the
absolute input/output paths. Analysis reads no packet/readout text and sends
nothing to a pod or service.

Before invoking, the integrator writes these files under
`cache/g_agreement/understand/e66/judge183/`:

- `RUBRIC.json`: the rubric frozen before the first judge call.
- `JUDGMENTS.jsonl`: exactly 542 unique opaque IDs; each row has exactly
  `id`, `S1`, `S2`, `S3`, `S4`, `topic`, `eval_awareness`. Six codes are strict
  JSON booleans. No stratum, prompt, readout or judge prose in this normalized file.
- `JUDGMENTS_SEAL.json`: status `SEALED_BLIND_JUDGMENTS`, n 542,
  strata_joined false, packet_sha256 from INTEGRATOR_REQUEST,
  judgments_sha256 and rubric_sha256 for the above exact bytes.

The seal is an integrator attestation that all blind judgments are complete,
with the frozen rubric, before the private map is opened. Preserve raw judge
responses separately in cache; normalize without rejudging or changing codes.
A parse failure is recorded by the integrator and blocks analysis, not silently
excluded. The command checks hashes and the blind-completion seal before opening
the private map. Only matching structural answers are scored after the join.
The command never uses source-family metadata for R-G3.

The fixed `analysis183/INVOKED_ONCE.lock` is created exclusively before any
judgment or map is loaded and retained even on failure. Successful output is
aggregate RESULTS.json plus ANALYSIS_SEAL.json. Failure writes INVALID.json and
cannot automatically retry. No real analysis has been invoked during preparation.
All outputs, including any private material, remain under cache.

Validation: five synthetic unittest cases cover Wilson reference values,
registered boundaries, question/stratum matching, malformed/duplicate/missing
judgments, seal-before-map ordering, successful sealing, and refusal to rerun.

All 11 E66 CPU tests pass (sampler plus analysis). Pre-commit pull --rebase
was blocked by unstaged work; unrelated shared log/compute edits were preserved.

### READY: corrected terminal-judgment contract

2026-10-27T22:37:56.010368+01:00 — Coordinator-directed correction:
UNPARSEABLE records are counted, flagged and excluded from every rate, without
replacement. This supersedes the earlier provisional parse-failure blocking
policy and strict no-evidence schema above. All 542 opaque IDs remain required.

JUDGMENTS.jsonl accepts either flat six-boolean codes with optional evidence
objects, or the runner's terminal envelopes {id, status: KEPT, code, attempts}.
Evidence objects have the six question keys and string values; evidence is not
rescored, printed or copied into aggregate results. Terminal records
{id, status: UNPARSEABLE, code: null, attempts: 2} are retained in accounting and
excluded from all rate denominators. INVALID/nonterminal records still fail.
The integrator serializes terminal records as JSONL without changing codes.
The existing blind-completion seal must cover all 542 terminal records, including
UNPARSEABLE, before the integrator-only stratum join.

Accounting includes excluded opaque IDs, total and per-stratum exclusion counts,
and a flag. Rates report their actual retained n. Empty denominators yield null
rates/CIs; R-G1 is NOT_EVALUABLE if required rates are absent and no falsifier
is established. Wilson 95% intervals, all thresholds, matching-question scoring,
packet, private map, caps, and once-only lock path are unchanged.

Validation: 14 CPU tests pass, including terminal envelopes with evidence,
UNPARSEABLE exclusions from R-G1/R-G2/R-G3, all-unparseable output, invalid
nonterminal rejection, and successful once-only sealed output with a sentinel.
No real readouts, evidence, judgments or private map were opened for this fix.

### READY: path-redaction sensitivity — 2026-10-27T23:20:17.006816+01:00

Per coordinator instruction and privacy ruling 79f63fe0, the SAME once-only
invocation writes two complete rule reports: all_records (542 selected records)
and excluding_path_redacted (539 selected records). Both report R-G1, R-G2,
R-G3, Wilson intervals and retained denominators with identical thresholds.
UNPARSEABLE exclusion applies within each view; overlap is never double-counted.
Original sampling shortfalls remain provenance, not revised recruitment counts.

Integrator supplies judge183/PATH_REDACTED_IDS.json as a JSON array of exactly
three distinct opaque IDs from this packet. Add redacted_ids_sha256 to the blind
JUDGMENTS_SEAL.json BEFORE the stratum join. The command verifies the ID file's
hash, requires all three IDs in the 542-record grid, and records its digest in
the analysis seal. No path strings, source text, or evidence is needed in this
file. Do not invoke until this metadata and the blind judgments are sealed.
RESULTS.json now nests the rule reports under all_records and
excluding_path_redacted, with exclusion IDs and view sizes under sensitivity.
The command, output path and exclusive lock are unchanged; do not run twice.

15 CPU tests pass, including both views in one sealed invocation, invalid ID
lists, all three rule denominators, and overlap with UNPARSEABLE. No real
judgments, readouts or map were opened; no real analysis was invoked.
