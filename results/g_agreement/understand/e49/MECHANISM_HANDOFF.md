# E49 W-mechanism generator handoff

Ready for W-text integration; priority instruction moves this ahead of E47 and sets the target to Tuesday 27 October 10:00 CET. Registration, gates and freeze deadline are unchanged.

Six modules in `rows/`: `arith_carry.py`, `arith_compare.py`, `branch_taken.py`, `var_type_at_use.py`, `instruction_provenance.py`, `decimal_separator.py`. The included `interface.py` is byte-identical to W-text's `f982cae0`; no interface changes. Integrator publishes the local owner commit; W-text integrates these six modules and the tests. Do not replace W-text's other row modules or README.

Validation: `python -m pytest results/g_agreement/understand/e49/test_mechanism_rows.py -q` — 15 passed. `MECHANISM_VALIDATION.json` records tokenizer identity, row-15 source hashes, counts and length ratios. Each row has 168 unique prefixes, 84 dev/84 test, 42 A/42 B per split. All independent text-only label checks pass. Paired final token IDs match. Maximum token-length ratio is 1.00 for rows 5–8/11 and 1.01 for row 16.

Arithmetic digit balance means the multiset of decimal digits in the two operands, excluding the threshold. It holds exactly within every A/B pair and hence within each split. Row 5 transposes tens and units to change the carry; row 6 transposes operand digits while retaining the identical threshold. The positional allocation carries the arithmetic information. Checkers recompute the arithmetic from raw text.

Rows 7–8 use restricted Python execution for the independent checks of every label. Branch programs reorder addition and multiplication; type programs reorder noncommuting swaps. Row 11 reorders explicitly attributed source headings while keeping the current imperative identical. Rows 7–8/11 also have identical Qwen token-count multisets within each pair.

Row 16 only relabels `unit_system.generate()`; it does not render text. The explicit last-format-note precedence determines comma/point. The labels cross metric/imperial equally (21 per joint cell per split), preserving every source index, split, string and token ID. W-text's actual row-15 source was used for testing. Missing or ambiguous format notes are rejected.

Each module freezes two descriptive A/B phrasings. Continuation candidates are provided only where meaningful (comparison and separator); other modules explicitly use `None`. Central channel and mention-detector binding remains W-text's responsibility.

No BOW/probe/reader scores or model calls were made, and no registered analysis was run. These construction checks do not claim any registered gate has passed. W-text owns the full bank freeze and once-only gates. Do not redesign on their outcomes.

Local `git pull --rebase` failed on GitHub DNS; the integrator handles pushing. E47 resumes after this handoff, under clarification `64a82e6e` with unchanged limits/rules.
