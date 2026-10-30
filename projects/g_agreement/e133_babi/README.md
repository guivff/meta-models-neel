# E133 external bAbI candidate packet (§242)

CPU data-only construction, no downloaded code execution, generation, behavioural
screening, judging, fitting or scientific analysis. Original multi-hop runner was
handed off first in3aebc94dc; its W-text item bank remains separately owned.
This arm is descriptive and never pooled into the synthetic R-NL1 result.

Public bAbI v1.2 archive downloaded to its own untrusted_data directory. Only exact
English QA2 and QA3 TEST text members were copied, with explicit member checks;
archive/text/receipt files read-only. Original training and all code members are
not extracted or executed. SHA256/URL/time/member hashes in DOWNLOAD_RECEIPT.json.
HF main archive absent and immutable PR5 data redirect403, so the documented
public text-datasets mirror was used. Its archive84f5296a differs from HF's
published0364ebde; no byte-equivalence to the unavailable HF archive is claimed.

Parser is project-owned regex/event bookkeeping over input text. Every eligible
current-location question reproduces the original gold location on CPU. For each
asked object find its last movement while carried, require a known distinct
previous location, and change ONLY that movement's destination span. Alternative
is the first already-mentioned location before that movement, distinct from
current and previous. Replaying the twin must leave the SAME event as the final
object movement with the SAME stale location and the new current destination.
Retain all eligible questions in original source order, no model/reader filter.
Other story sentences and the question remain literal; earlier question/answer
lines are omitted, and the fixed answer cue is newline Answer:.

QA2 contributes494candidate pairs. QA3 has1000 historical "Where was ... before
...?" questions and ZERO current-location "Where is ...?" questions: all1000 are
ineligible under the unchanged current-location task. No question is silently
rewritten. Any later authorization to rewrite QA3 requires a separate prospectively
sealed amendment; this QA2 packet remains unchanged.

Public items are STRICTLY id+prompt only (988prompts); no CPU answers, roles,
recipient/previous strings, targets, support IDs or tokenizer-derived labels on
pods. Provenance/aggregate manifest and input seal accompany that public file.
CPU-only labels map paired opaque IDs, old/current/twin locations, original source
line/task/question/support IDs and exact changed-span evidence; mode600, neverGit
or GPU. Model selection is NOT done: selected_pairs null. Track Q/B subsequently
screen both members with32token greedy text and unchanged parse_target_answer,
freeze first42correct pairs in source order; fewer qualify reported honestly.
Deadline08CET: packet sealed before cutoff, otherwise drop arm; no launch by C.
The synthetic E133 runner's v1 loader requires tokenized fields/family and does NOT
accept this id/prompt-only public packet directly. Operator/source adapter must
respect this stricter public contract; do not stage CPU labels to satisfy a loader.
