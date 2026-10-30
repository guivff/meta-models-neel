# E20 parser validation — coordinator instruction, 25 October 2026

Status: waiting for the integrator's sealed 240 base-Qwen dev continuations.
The parser is not validated or scientifically frozen. Its draft bytes remain
those committed in 9a2ef7d9; no reauthoring is allowed after this check.

1. Verify GENERATION_SEAL, input/source/plan provenance, exact 240 unique IDs and
   60 continuations per row against PARSER_DEV_PLAN.json. Do not replace samples.
2. Prepare a separate packet containing only opaque id, row and continuation text.
   Shuffle by a fixed seed (20261025). Record packet and event-definition hashes.
   Exclude parser source, parser predictions, tests, expected agreement, item
   prefixes, state labels and scores.
3. Spawn one fresh independent sub-agent with no inherited conversation
   (`fork_turns="none"`). It may read only the blind packet and the definitions
   below. It must code all 240 records independently, without running or reading
   the candidate parser or receiving its outputs. Record agent identity and the
   exact coding instructions. If independent agents are unavailable, stop; do
   not substitute the parser author's judgment or fabricated codes.
4. Obtain one Boolean positive-event code per ID, with a short text-grounded
   rationale or evidence. Check completeness and schema without comparison to
   the parser. Preserve the raw returned codes, instructions and packet, then
   write a seal with SHA256 hashes BEFORE computing or joining parser outputs.
5. Only after the blind codes are sealed, run the unchanged draft parser and
   compare exactly once. Report matches/60, agreement, and every discrepancy
   separately for each row. Pass requires at least54/60 (90%) on EACH row.
   Preserve all disagreements; do not revise codes or parser after comparison.
6. If every row passes, freeze the exact parser bytes and commit their hash with
   the validation result and blind-code seal before any lens output or source
   capture. If any row fails, report the failing rows, do not reauthor the parser,
   and stop before the full worker/launch stages pending a coordinator ruling.
7. After a successful freeze, build the five-channel worker and launch request
   under clarified §112, using /weights/venv-kernels/bin/python. Carry parser-dev
   compute/setup costs forward; do not reset the registered shared budget.
   W12 remains higher priority. Integrator alone publishes and runs GPU work.

## Independent coding definitions

Score the fixed A-event in BOTH states; do not infer correctness against an
unknown source-state label. Treat each provided continuation as one output.

- prose_paren: positive if there is an unmatched closing parenthesis `)` in the
  continuation (a close without an earlier available opening parenthesis).
- python_string: positive for a double quote straight after the first word, as
  in the registered discovery-study rule, OR an unmatched double quote `"`.
  A native leading bullet marker is formatting, not the first word.
- prose_sentiment_delayed: positive if a word from the frozen A-polarity lexicon
  appears. A lexicon: `wonderful`; B lexicon: `terrible`. B alone is not positive.
- fact_once: positive if the exact frozen A-number `1234` occurs, not merely as
  digits inside a longer number. B-number: `5678`. B alone is not positive.

These are event definitions, not access to the candidate parser's implementation.
