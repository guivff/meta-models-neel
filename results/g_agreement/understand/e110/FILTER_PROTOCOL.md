# E110 filtering contract — §223 deviation1 / clarification1

Seed20261029. Primary source is soheeyang/TwoHopFact at
59a84cd883f71641a03fb6fa50da92a9603e7845, CC BY4.0. Original dataset data
only: CSV and card downloaded without credentials, terms acceptance or execution.
The initial generated-bank work was NOT frozen before the source switch. It is
an ignored source-only draft and does not run as a secondary bank.

## Candidate and template freeze, before model output

The pinned CSV has45595 rows,52 composition types. Source QA excludes71 records
with non-entity truth identifiers (Wikidata genid URLs); no replacement facts or
labels are invented. Sample3000 valid rows with balanced capped round-robin
allocation across sorted composition types, then random.Random(20261029) sampling
without replacement within each type in source UID order. The minimum-capacity
types contribute all their available records; other quotas fill the3000 total.
Counts and exact sampled UID bindings are sealed. No dev/test split or probe fit.

PARAPHRASE_TEMPLATES.json has52 entries, exactly two literal templates per type,
written once from the source first-hop relation definitions. The only substitution
is {e1}. Relations shared across composition types may use identical template
strings. The native one-hop and native two-hop source prompts are preserved
byte-for-byte. No Fact: prefix, question, answer, CoT or chat wrapper is appended.
Only the belief (one-hop) has two added paraphrases. Two-hop stays native.

Each candidate therefore refers to four logical completion slots: native one-hop,
two paraphrase one-hops and native two-hop. Deduplicate exact identical prompt
bytes across candidates/types before deterministic greedy generation. There are
12000 slots /10917 unique jobs. No outputs are inspected in deciding deduplication.
PUBLIC_FILTER_INPUTS.json contains only opaque id,prompt,input_ids,read_position;
read_position is len(input_ids)-1. ITEMS.PRIVATE.json joins jobs to source facts,
aliases, types and true e2/e3; it and the entire source CSV stay CPU-side.

## I-2 acquisition

Pinned base Qwen3.6-27B revision6a9e13bd6fc8f0983b9b99948120bc37f49c13e9,
no adapter/activation injection, raw prompt tokens, greedy do_sample=false,
max_new_tokens16, no CoT, seed20261029. Emit the entire original generated raw text
and token IDs, with original termination metadata. No sampling, teacher forcing,
restricted-vocabulary decoding, answer candidate or truth token goes to the pod.
Max16 is a frozen short factual-completion limit. An unresolved/incomplete head is
unknown, not a wrong answer. Preserve truncation metadata for coverage reporting.

Filter custody≤1800 GPU-seconds (0.5 GPU-h), independently admitted/booked by I-2.
Reader ceiling≤5400 GPU-seconds and combined outside+judging≤USD10 remain separate
original bounds, not allocations or clock resets. Respect stricter live admission
and full custody limits. Before filtering, require the committed synthetic-tested
W-mech2 E110 adapter and I-2's fresh-extract CPU import test of its actual pod
source. Timing uses §217 max measured staging+load setup plus1.25×work; absent
staging uses maximum experiment staging or150s. No pod allocated by W-text.

## CPU identification and gates

Use the frozen dataset's English aliases and canonical labels. Alias data is
parsed only with ast.literal_eval into tuples/lists/strings, never executed.
Normalize Unicode compatibility, case, accents and whitespace; match a source
alias at the head of a greedy completion with an end/word boundary. Use the
longest alias. Aliases shared across different entity QIDs are ambiguous and
remain unknown. An unrecognized answer, refusal, explanation-first text or
incomplete entity is unknown; unknown is not treated as false. No new judge,
external fact lookup, guessed entity, substring credit inside words or private
label on a pod. Identification is conservative and source-alias-limited; report
unknown counts, not inferred error rates for these completions.

Native belief is the native one-hop completion's identified entity. Stable means
that native and both paraphrase completions identify exactly the same entity.
Native belief-wrong requires native belief≠e2 AND native two-hop answer≠e3, with
both answers identified. Stable belief-wrong additionally requires stability.
Belief-right requires the native one-hop=e2 and native two-hop=e3; it is matched
by composition type as registered. Its paraphrase stability is retained as a
diagnostic, not an added control eligibility threshold.

If≥60 stable belief-wrong survive, retain ALL of them as primary. Otherwise, if
≥60 native belief-wrong survive, retain ALL native belief-wrong as primary with
literal label "no paraphrase gate". Otherwise E110 is NOT RUN. ≥150 is a target,
not a replacement threshold. No data-dependent paraphrase edits or new candidate
sample if yield is low.

Within the chosen primary gate, retain belief-right controls without replacement
from the same exact composition type, selecting nearest native two-hop token
length; ties use opaque candidate ID. Visit shuffled primary items with seed
20261029. Report unmatched primary items; never replace them or cross types.
A lack of controls does not delete qualifying primary items or change the floor.
Truth and belief coincide on right controls; do not invent a wrong candidate to
make two distinct target values. Confirmatory contrasts use belief-wrong items.

## Once-only CPU handoff

After a complete verified pull, I-2 writes FILTER_RECEIPT.json with:
verified=true,experiment="E110",input_seal_sha256=<BANK_SEAL hash>,
model_revision="6a9e13bd6fc8f0983b9b99948120bc37f49c13e9",
decoding={"do_sample":false,"max_new_tokens":16,"no_CoT":true},
filter_gpu_seconds_total=<actual cumulative custody ≤1800>,
filter_outputs=<absolute JSON path>,filter_outputs_sha256=<actual SHA256>.
Output is a complete unique array, one record per frozen job ID, with at least
{id,raw,token_ids} and original termination metadata; raw is generated text only.
Transport/source/GO/custody proof remains in I-2's verified acquisition seal.

Command from the W-text worktree:
python results/g_agreement/understand/e110/filter110.py --receipt ABS_RECEIPT --out
/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/results/g_agreement/understand/e110/cache/selection_once

This reserves cache/FILTER_SELECTION_ONCE.json before opening filter outputs,
verifies all bank/code/source hashes and refuses replay. Preserve guard and
partial directory on any failure; no retry without a dated ruling. Outputs:
COUNTS.json, SELECTION_SEAL.json; CPU-private selection/diagnostics/targets;
PUBLIC_READER_INPUTS.json with only chosen native two-hop prefixes/IDs/read sites.
Commit the count/seal receipt without private members, then bind subsequent
readers/outside/judging to that exact selection. This CPU gate is not the R-B2′/
R-OL1′ once-only analysis: W-mech2 owns the sole rule adapter, I-2 its watcher.

Reader site is the final token of the original two-hop prompt, Oracle44/NLA42,
one native greedy readout each. Outside generation and blind judgment use E82's
registered rubric and separate E110 bank (W-internals-C), not E107's bank/inventory.
All true e2/e3, aliases, inferred belief, cohort and matching joins remain CPU-side.
Source dataset facts are used as released, including time-dependent CEO/president/
spouse relations; no unregistered current-date correction is made. Source errors
or stale truth are limitations to report, not silently repaired frozen labels.
