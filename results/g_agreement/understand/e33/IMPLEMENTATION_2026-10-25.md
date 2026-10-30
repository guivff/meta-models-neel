# E33 implementation note — 2026-10-25, before any E33 model call

Authority: BRIEF_UNDERSTAND §128 and the operations note in commit
5731e92e0835e2a20d57a88cfcae7f3f57108fe4. W-lens builds E33 first, then full-arm
E28. Integrator alone publishes, operates pods, retrieves receipts and consolidates
the shared run/compute logs. This worker edits only e33/ and e28/; large staged
inputs, archives, and future raw scores live in ignored cache/.

The plan preserves all 25 rows, 84 test items each, both W1 Oracle phrasing pairs,
five LoRA doses, and both prompts. P1 reuses E16's exact source-text wrapper; P2
reuses E12(c)'s exact native Oracle request with source prefix and the placeholder's
own embedding. No activation is loaded, captured, zeroed, or injected. The reused
functions are extracted verbatim from the pinned upstream revision recorded in
UPSTREAM_SOURCE.json. Tests compare all 2,100 tokenized heads to those functions.

Scoring preserves E12/E16/W1's **sum** of candidate token log probabilities,
positive candidate minus negative, then the mean across two frozen pairs before
AUROC. E33 uses W1 phrasings, not E16's dev-selected wording. Scaling multiplies
each unmerged Oracle LoRA layer's original scale by the absolute dose and restores
it on exit. Numerical gates require zero-dose parity with the disabled adapter
and a live full-dose adapter. All model inputs are token IDs, without injection
hooks or embedding replacements.

The analysis keeps the 25 rows fixed and resamples whole W1 test-template clusters
within each row, using the same item draws for every dose and prompt. The primary
contrast recomputes both class medians within each bootstrap draw. The seed is
20261025, with 2,000 percentile-bootstrap draws. In §128's endpoint contrast,
“content stays ≥0.95” is implemented as the semantic-row median at both endpoints;
all intermediate-dose medians and all individual rows are also reported. This
interpretation is fixed here before scores exist.

The shared science limit min(1.5F+360,1440) seconds is enforced. This packet also
uses the more conservative limit of **1,440 total provider seconds including
setup**, with 120 seconds reserved for retrieval. Every one of the ten paths has
one warm-up plus three timed units. The costliest frozen unit for each prompt is
used; its median time is multiplied by all units for that path. Admission requires
the full remaining grid with a 1.5 safety factor. No row reduction, alternate
prompt, retry, deadline reset, or continuation from incomplete scores is permitted.
The stricter custody accounting may yield NO_FIT; it changes no scientific rule.

CPU validation does not establish GPU feasibility. Integrator must record measured
timings, source publication, the external hard stop, and the exact provider clock
in its assignment before invoking the runtime. The assignment template is inert
until those fields are filled. Source and input hashes must match this packet.

After successful complete collection, seal scores before joining the frozen
private labels. The analysis rejects incomplete grids, duplicate cells, changed
plans, mismatched truth hashes and invalid cluster structure. Preserve incomplete
or NO_FIT receipts and account for their GPU time. Integrator should copy the small
run and budget receipts into this experiment directory and append the canonical
shared log entries; no real run is claimed by this CPU preparation.
