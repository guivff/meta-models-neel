# E66 sampling conventions — final 542-record packet

Status: RATIFIED AS WRITTEN by §183 E66 clarification 1 (23a2e5c9).
The 15:02 correction is accepted as disclosed; all five strata are included at
their achieved n. Judging remains within the existing USD 3 / USD 15 authorisation.
Consolidated at 2026-10-27T15:33:55.227975+01:00. This document does not resample or change the packet.
Authority: §183 e94784b009f4c3413a7ea71b39ab5e22c561e135.

## Dependency audit

Every selection decision depends only on dataset-card/schema metadata, prompt
text/tokens, transcript identifiers, or seeded randomness. No reader output,
readout length, readout words, judge result or scientific outcome determines
eligibility, stratum, chosen position, chosen channel or replacement.

The planning phase projects precisely these columns:
- Read-position file: source, family, tid, pos, token, role.
- Transcript file: source, tid, text, ids, family.

`rl_greedy` is not projected until the materialisation phase, after the selection
file and counts are written. Materialisation copies the fixed selected cells;
it checks string/nonempty validity and aborts on failure, never replaces an item.
No abort occurred. The agent has not inspected any real readout text. Hashing
files and copying bytes are custody operations, not text-dependent selection.

## Final conventions

1. Source scope: only main readouts/transcripts at dataset revision
   226c6dce62ed88d5981ca864d0c99d3f082ccee6. No dense, selected-example, J-lens,
   best-of-N or other derivative subsets. Anonymous retrieval.
2. Sampling unit: one transcript `(source, tid)` is one rollout; at most one
   selected read position/readout per transcript. Two distinct transcripts sharing
   one identity are excluded because the join is ambiguous (thinking does not
   disambiguate them).
3. Alignment: require re-encoding text without added specials to reproduce ids,
   full decode (special tokens retained) to reproduce text, and single-token
   decode at pos to match the published token. Use offset end at pos, inclusive
   of the read token. Bounds/zero-offset failures are excluded. The short
   left_ctx window is never used to recover structural state. 594 alignment
   failures and two ambiguous-identity transcripts are excluded; 1413 recover.
4. Structural parsing: operate on the rendered prefix through the read token,
   within its current message/reasoning/tool-call segment. Recognised or unlabelled
   fenced code only; quote escapes, comments and matched bracket stacks are
   tracked. Unsupported fenced languages, mismatched brackets and comment
   positions are excluded. This conservative lexer is not a full language parser.
5. S1: active unclosed quote in the code fence. S2: a nonempty bracket stack,
   after S1 precedence. S3: pipe-delimited current row with a preceding contiguous
   Markdown separator and known one-based column; trailing-pipe boundaries are
   excluded. S4: at least eight literal leading spaces in the code line, not tabs,
   after S1/S2 precedence. Current line at a newline is the line ending there.
6. C: outside a code fence, alphabetic prose, no recognised table/code markup or
   code-looking line; four-or-more leading spaces are not accepted as C. Some
   unrecognised natural code may remain; coverage is not claimed exhaustive.
7. Eligibility counts are unique transcripts qualifying for a stratum, BEFORE
   cross-stratum overlap resolution. These counts overlap. Exclude only strata
   with fewer than 50 such eligible transcripts. All five qualify.
8. Sampling: seed 20261027, Python random.Random; deterministic sorting of keys
   and positions. Repeatedly shuffle active stratum order, uniformly select a
   still-unselected eligible transcript for each stratum, then uniformly select
   one of its qualifying positions. Stop at 150 or pool exhaustion. Draws are
   uniform conditional on prior selections; overlapping strata do not have
   guaranteed unconditional equal inclusion probabilities. Report shortfalls.
9. Channel: rl_greedy, chosen from the card/schema as the single post-RL greedy
   lens output; no comparison of actual SFT/RL/sample texts. Metadata family
   rlvr1 maps to RL_TRAINING; all others UNKNOWN. No explicit eval-vs-RL flag;
   no eval classification inferred from output, reward or lens checkpoint.
10. Blinding: opaque IDs are keyed hashes of selected row indices with fresh
    private randomness; packet order is seed-shuffled independently of strata.
    Packet records are id/readout only. Private map and prompts are not judge
    inputs. Judge answers all four structural questions plus topic/eval questions
    for every readout; the integrator alone joins the matching stratum afterward.

## Timing and corrections

Initial conventions were recorded at 2026-10-27T14:55:55+01:00 before prompt
payload access. Duplicate-identity handling was recorded at 15:00:01+01:00.
At 15:02:40+01:00, AFTER prompt-derived eligibility counts were known but BEFORE
any readout materialisation, the invalid position-first draft was corrected:
<50 applies to actual eligible transcripts, not the randomly assigned subset.
Those failed/draft attempts remain preserved in cache and are not registered
samples. This timing is disclosed; nothing is backdated. No readout text or
judge outcome informed the correction. Full historical notes remain in HANDOFF.md.

## Accepted counts and shortfalls

| Stratum | Eligible transcripts | Selected | Shortfall vs 150 |
|---|---:|---:|---:|
| C | 1413 | 150 | 0 |
| S1 | 240 | 128 | 22 |
| S2 | 286 | 137 | 13 |
| S3 | 76 | 68 | 82 |
| S4 | 80 | 59 | 91 |

Total: 542 distinct transcripts, all five strata INCLUDED. The packet and private
map hashes in PACKET_SEAL.json are unchanged from commit 40ade2f6.

## Ratification and reporting clarification

2026-10-27T15:38:14.027586+01:00 — Explicit coordinator instruction, §183 clarification 1 (23a2e5c9).
R-G3 is reported UNSTRATIFIED across the 542 selected readouts because no eval
flag exists. Family/rlvr1 metadata in the private map is retained as historical
provenance only; it must not define an eval-vs-RL contrast. The eval-awareness
question is still asked of every readout. R-G1/R-G2, the packet, selected IDs,
achieved counts and shortfalls are unchanged.
