# E49 rows 3, 4 and 12 — W-internals delivery

User delegated these three modules to W-internals after the original W-text ownership table. The exact shared interface was copied unchanged and committed as `6b11a67e` before authoring. The families review was read first. Modules import only `rows.interface` and the standard library; no existing item bank, generator, filler or outcome was imported.

- `rows/container_after_move.py`: A cup / B bowl. Two explicit placements, reordered across the pair; placing an object where it already is is the non-moving edit. An independent parser executes the text's placements. Final read token is ` the`. Twelve placement forms and distinct context families.
- `rows/holder_after_handovers.py`: A Alex / B Robin. Three to five actual handovers, with initial possession crossed against parity. The text-only simulator checks every sender really holds the object. Each count occurs14times per label per split. Final two neutral sentences name neither holder nor tracked object; read at the final period. Twelve transfer forms include sender-first, receiver-first and passive syntax.
- `rows/user_expertise.py`: A expert / B novice. First-person experience/help register, exact topic phrase matched within every pair, seven topics, no gender terms. This is an authored register label, not a claim about a real person's competence. Twelve register pairs; checker recognizes one unambiguous register assertion from raw text and rejects additions/contradictions.

Each module exports SPEC, generate(), check_label(text), length_match, PHRASINGS and CONTINUATIONS. Each yields168unique raw prefixes (84dev/84test,42A/42B per split), with families0–5dev and6–11test. Exact Qwen tokenizer identity, lengths, read-token IDs and source hashes are in INTERNALS_VALIDATION.json. The largest paired ratio is below1.10. No padding or truncation hook is used.

Both tracked-state modules have **identical Qwen token-count bags within every A/B pair**, including punctuation, for all84pairs. This is a construction invariant, not a fitted BOW result: no BOW classifier, reader, probe or model was run. Keep W-text's frozen once-only BOW gate and all later gates. The descriptor is exempt from the BOW ceiling.

Eight CPU tests pass, including the shared interface, source determinism, held-out family indices, exact paired token bags, illegal sender rejection, independent event-label recovery, matching topic phrases and gender exclusion. Run from the worktree root:

```
python -m pytest results/g_agreement/understand/e49/test_internals_rows.py -q
```

Generated construction-test items are in ignored `cache/g_agreement/understand/e49/internals_generated_items.jsonl`; these are not the centrally frozen E49 bank. W-text should regenerate with these modules and perform its central source/bank freeze before any gate. Fixed candidate suggestions are provided; central asked/continuation/detector bindings remain W-text's responsibility.

**Concurrent work:** W-text's working directory acquired different drafts of the same three filenames during this task. Those files were not read, modified, replaced or committed by W-internals. Integrate the three delegated modules from this delivery explicitly, preserving the existing drafts in history; do not silently combine their science. The unchanged shared interface need not be replaced if its hash already matches. The module source seal accompanies this handoff.
