## §132 E36. Do the headline results hold on a second item bank?

**Registered 2026-10-25 12:30 CET, before any E36 item exists. EXPLORATORY replication.** **Owner:** W-text (items
and CPU) with the integrator's pods. **Cost:** ≤ 3 GPU-h.
**Why.** E23 showed item banks change results (table column 0.97 vs 0.60 in the reconstructor). The headline claims
rest mainly on W1's bank.
**Items.** A new bank, "v2", for 8 rows: `prose_paren`, `python_string`, `table_role`, `python_indent` (states),
`table_column`, `list_index` (positions), `prose_sentiment`, `prose_topic` (content). New templates written by W-text
**without access to any W1 item text or score** beyond the row definitions and value bins in W1's `w1_templates.py`
docstrings; 12 templates × 7 fillers × 2 values per row, 84 test + 84 dev items; frozen and hashed, and screened only by
an automatic label check before any capture.
**Channels (block 44):** probe (W1 recipe); Oracle-lens asked with W1's descriptive pairs and with E30's value-word
pairs; E15-style continuation with E15's frozen pairs (rows with pairs); NLA asked at block 42 with W1's NLA pairs.
**Rules (each a replication test of a W1 headline).**
- **H1 (blind spot, descriptive pairs):** Oracle lens ≤ 0.65 on ≥ 4 of the 6 structure rows, with probe ≥ 0.90.
- **H2 (content ceiling):** Oracle lens ≥ 0.85 on both content rows.
- **H3 (value words, if E30 met R2):** value-word − descriptive ≥ 0.15 on the same rows where E30 found it.
- **H4 (carries it):** E15-style continuation ≥ 0.70 on ≥ 3 of the 4 state rows with pairs.
- **H5 (NLA describes better):** NLA − Oracle ≥ 0.10 on ≥ 4 of 6 structure rows.
Each H is reported as replicated, not replicated, or not evaluable.



**Dated note, 2026-10-25 12:55 CET (coordinator), operations only: parallelisation, before any score of the affected
runs.** The queue order in §125–§131 was a convenience, not a dependency. Only these dependencies are real: E34 waits
for E24-D to clear h44 parity; E24 attempt 2 waits for E24-D; E29's reader scoring waits for W-text's sealed D and the
coordinator's posted predictions. Everything else may be built and launched as soon as it is ready. Ownership:
- **W-internals:** E22 analysis first, then builds E30 and E31(ii) in parallel; launches each when ready.
- **W-core:** E32 (moved from W-internals; W-core owns W1 scoring and is otherwise waiting on E24-D), then W12.
- **W-mechanism:** E26 analysis, then E27(c) and E34.
- **New chat W-lens:** E33, then E28 (full arms).
- **New chat W-sae:** E35.
- **W12** is brought forward: it may run tonight, as soon as E29's blinding order (§124 steps 1–3) is complete,
  instead of Monday. Its registration (§100) is otherwise unchanged.
Pod ceiling 8 (§130); priority when contended as in §130, with E32 taking E31's slot order.



**Dated clarification 1 to §132 (E36), 2026-10-25 14:25 CET, before any E36 item exists.** `w1_templates.py`'s
docstrings do not state the row definitions, so the coordinator supplies a definition-only packet,
`results/g_agreement/understand/e36/ROW_DEFINITIONS.json` (sha256
`2afa8e1202c0d7c181e6f95984b18bd59f99af81fc8cf8f27dcce02e8e38056c`): for each of the 25 rows, A/B values in W1's order,
the row class and a one-sentence definition with W1's value bins. It contains no W1 item text, template, filler,
phrasing or score. Item authors receive only this packet; length matching within a template is ±10% of tokens.

**Dated clarification 1 to §134 (E37), 2026-10-25 14:25 CET, before any E37 step.** Parity gate:
- **Smoke set:** 20 W1 test items chosen by seeded hash (20261025) across all rows, frozen and hashed before loading.
  Both arms must load, produce finite scores, and reproduce their own scores within 1e-4 on an immediate repeat.
- **Reproduction:** the RL arm reproduces W1's sealed **row AUROC** (not individual log-odds) within ±0.03 on the full
  84 test items of three rows fixed now: `prose_sentiment` (content), `prose_paren` and `python_string` (states).
  Failure stops the run.

**Dated clarification 2 to §134 (E37), 2026-10-25 14:30 CET.** R4 is applied **per arm, pooled across the structure
rows**, exactly as E24's R4: the Wilson 95% upper bound on the pooled correct-statement rate is < 5%. Per-row rates are
reported descriptively.

**Dated clarification 2 to §132 (E36), 2026-10-25 14:35 CET (answers W-text, before any E36 item is frozen).** The
§135 widening to 25 rows keeps each rule's original proportion, rounded up:
- **H1:** Oracle ≤ 0.65 with probe ≥ 0.90 on **≥ 11 of the 16** structure rows (was 4 of 6).
- **H2:** Oracle ≥ 0.85 on **≥ 7 of the 9** content rows (was 2 of 2).
- **H3:** unchanged (the rows where E30 finds R1).
- **H4:** population = **E15's 7 valid rows with frozen pairs** (`prose_paren`, `prose_quote`, `python_string`,
  `python_indent`, `python_depth`, `list_depth`, `table_role`), regardless of the packet's class label; continuation
  ≥ 0.70 on **≥ 5 of the 7** (was 3 of 4).
- **H5:** NLA − Oracle ≥ 0.10 on **≥ 11 of the 16** structure rows (was 4 of 6).
If the 8-row fallback bank runs instead, the original counts in §132 apply.

**Clarification 3 (2026-10-26 01:30 CET, coordinator; before any E36 score).** H3 was conditional on E30 meeting R2.
E30's R2 is uninterpretable (failed controls), which would leave H3 unevaluated. H3 is therefore fixed now as a
confirmatory test of E30's raw pattern:
- **Rows:** the six rows where E30's raw R1 held: table_row, table_column, python_argument, latex_section,
  python_comment, python_depth.
- **Rule:** H3 holds if value-word − descriptive ≥ 0.15 with item-bootstrap CI lower bound > 0 on **≥ 4 of those six**.
  Only rows present in the v2 bank count; if fewer than 4 are present, H3 is NOT EVALUABLE.
- **Descriptive:** the same contrast on the four state rows (paren, quote, string, table_role). The prediction there is
  no gain.


## §149 Overnight standing orders (26 Oct, 01:55 CET, until Guiv's next message; extends §136)

1. **Timing and cap stalls.** For any run with no production record yet, the integrator may authorise, without the
   coordinator:
   - a cap raise up to 2× its current total, a separate setup allowance up to 900 s, and sharding up to 4 pods, each
     with its own parity gate and its own deadline;
   - up to two operational-only retries.
   
   Science, items, rules and parity tolerances never change. Each such change is recorded in HANDOFF as
   `§149 OPERATIONAL`. Owners re-pin only the cap and deadline fields when asked. Spend stays inside the USD 1,400
   guard.
2. **Analyses.** Each owner sets an hourly self-check. When its run's sealed pull is delivered and verified, it runs
   its single registered analysis once and posts the verdicts against the registered rules only.
   - **Owners:** E24 and the impact audit, W-core; E32, W-internals; E34 and E38, W-mechanism; E29, W-text with W-core;
     E36 and E41, W-text; E39, W-lens; E40, W-sae.
   - **Ambiguities:** recorded as `OWNER_READING` and held only if they touch a rule.
3. **Unchanged:** a parity, validity or rule question still stops and waits. Whiteners are deleted before any pod is
   released, after its outputs are pulled and verified.

**§149 amendment (2026-10-26 02:00 CET).** Worker chats' scheduled self-checks are not reliable (the 19:00 W12 freeze
task never fired). The integrator's watchers are. So:
- **Integrator runs committed analyses.** For any run whose owner has committed a once-only analysis entry point
  (command, code seal, once-only guard), the integrator runs that pinned command exactly once on the verified pull,
  in the owner's output location. It commits the sealed outputs unchanged, labelled `§149 RUN-BY-INTEGRATOR`.
  - It does not interpret, change code, rerun on failure, or open private label files beyond what the command itself
    reads.
  - Blind-coder and judge steps are excluded.
- **Otherwise the run waits.** If no committed entry point exists, or the command stops on any validation, the run
  waits for its owner.
- **Owners review.** Owners verify the seal and post verdicts in the morning.

