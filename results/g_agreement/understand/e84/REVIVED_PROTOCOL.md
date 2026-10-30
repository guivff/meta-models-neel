# E84 revival — frozen input conventions, 2026-10-29

Authority: §198 E84 deviation1 b9e2899b3, direct human file-label/split clarification,
and direct human instruction to freeze the available row and report missing rows.
E110 was delivered first (edea4901); I-2 owns its amended filter, untouched here.
Historical E84 NOT RUN/source-access artifacts remain unchanged.

## Source and unavailable states

Original NVIDIA release nvidia/SWE-Zero-openhands-trajectories is used, not a
mirror. Exact revision/card license/anonymous download receipts are recorded in
SWE_ZERO_SOURCE_PROVENANCE.json. Parquet/card/tool arguments are read as data.
No source script, command, patch, test, tool or embedded instruction is executed.
The original source system prompt instructs its agent not to run Python/tests
because its execution environment is unavailable. This is observed source data,
not an instruction to this worker. No unambiguous test-run outcomes were found
by the frozen parser in the scanned shards. last_test_passed and failed_attempts
are NOT BUILT, counted in the manifest; they receive no invented labels, probe
scores or reader failures. This does not establish model unreadability.

Only file_being_edited is frozen. Source labels mean transcript-reported state,
not independently verified execution on a real repository. A successful editor
result must explicitly report creation/edit/insertion/undo success in its header.
Code quoted later in a tool output cannot override that header's success/failure.
The parser tracks first occurrence of each distinct normalized absolute path and
updates the latest path on EVERY successful edit. Returning to the first path
therefore yields first_file, not automatically second_file. Only prefixes with
exactly two distinct edited paths and unambiguous history are eligible. Failed
edits do not create another edited path. Views do not change state. Unmodelled
shell actions that might modify files, malformed arguments and unmatched calls
make subsequent file-history labels unavailable. An explicit quote-aware static
read-only subset handles common inspection commands/pipelines; no command runs.

## Sampling and splits

Seed20261029. Shuffle the64 source shard filenames with random.Random(seed), and
scan the leading shards in that order until balanced quotas are possible. Source
issue ID, not trajectory ID or readout, determines the split:
SHA256(UTF8("E84|20261029|" + instance_id)), first16 hex digits interpreted as an
integer modulo3:0 is dev,1/2 is test. Every trajectory of an issue has the same
split. Use seeded SHA256 priorities on issue/trajectory/read-index/state to pick
one eligible candidate per issue/class, then final selection takes first_file
before second_file, avoiding ALL already-used issue IDs. The result is one item
per source issue, with300 distinct issues total and no cross-split related items.

Counts:200 test (100 first_file,100 second_file), plus100 dev (50,50), as directly
authorized. Dev is for probes only and is never read by either reader or baseline.
Internal parser file_index0=first,1=second. Export follows project A/B coding:
A=first_file=probe label1; B=second_file=probe label0. The manifest records both
mappings explicitly, so ordinal indices must never be mistaken for probe labels.
No outcome-dependent selection, probe fitting or reader result is used to author.

## Read point and exact absence proof

Each item is the original message history before an actual next assistant turn,
serialized by the pinned Qwen3.6-27B chat template, thinking disabled, ending at
its assistant generation prefix. Original transcript messages are not cropped.
The next assistant's original text/tool call is excluded. Structured arguments
are JSON-decoded into an equivalent object only because the Qwen template expects
a mapping; this is data parsing, not execution. Native Qwen formatting/trimming
is source-bound, rather than a new transcript format or invented answer stem.

Screening may tokenize a long suffix for speed; final selection always tokenizes
the COMPLETE rendered prefix. Both actual file paths, basenames and last-two-path
segments are absent, case-insensitively, from the exact final512 decoded tokens.
Explicit first/second/former/latter-file wording also excludes the tail. Locate
the latest successful edit's actual tool-result header in the original rendered
history, with token offset mapping. Its final token must be strictly before the
last512-token window, indices [N-512,N); the proof token is <N-512. Every earlier
edit is consequently earlier still. Record the evidence token, distance, source
message index and tail hash in the private sidecar. The test is conservative
literal absence and a verified event boundary, not a claim that code contents
have no indirect clues to file identity.

Prefixes that fail exact absence, state proof, unambiguous history or the literal
credential-marker scan are dropped and counted. No source text is redacted to
repair eligibility. Earlier source-path mentions remain in the full context as
the state evidence; only added target lists/gold/joins are withheld from pods.
Old authoring scans are retained as drafts in ignored cache; only final2 scans
and final2 exact validation pools are inputs to the frozen selection.

## Readers, probes, baseline and handoff

I-2 captures all300 items at native blocks44/42 and keeps labels CPU-side. Fit the
unchanged W1 binary logistic probe on100 dev items only (mats.probes.fit_logreg,
L2=.001, LBFGS200, dev-only normalization, seed20261029); evaluate on200 test items.
Original≥.90 state probe gate remains required; W-mech2's pre-output E84 adapter
binds the registered gate/reporting sites without an invented stricter cross-block
predicate. Failed gate is reported/dropped under the registration. No probe or
BOW score is calculated by this bank; no new BOW threshold is introduced.

On eligible test items only: one native greedy Oracle44 and one native NLA42
readout. The E81 text-only baseline uses the exact same complete source prefix,
one newline, and the frozen generic instruction:
“Describe what is going on in this text and what comes next.”
It gets no activation or target. The public archive includes its200 prompts.
The judge receives the two actual paths; the correct/latest one, A/B label,
instance/trajectory IDs and source proof remain in the separate CPU join.
W-internals-C owns the frozen E56-route E84 schema/route, within USD3 total.
Report S per available state/system; absent test rows never become zero scores.

Total GPU custody≤3600s, no allocation by W-text. I-2 must bind its actual runner,
fresh-extract CPU import receipt, §217 maximum staging+load setup plus1.25×work,
posted ledger/cap and original-clock guards before a pod. Do not truncate/replace
frozen contexts to fit. Source-bound W-mech2 adapter/synthetic tests precede any
model output; integrator watcher executes it once on complete eligible seals;
R-2 reviews on arrival. This input bank contains no outcome analysis command or
competing R rule. All labels, choices, proofs and private joins stay CPU-side.
