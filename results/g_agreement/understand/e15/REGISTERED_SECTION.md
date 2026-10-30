## §105 E15. Scoring the Oracle lens in its own mode: does it enact structure? (closes the format confound)

Registered 2026-10-24 07:20 CEST, before any E15 item or score exists. **Why:** W1 scores readers by choosing between two
*descriptions*, which is the NLA's native mode. E12 showed the Oracle lens judges structure poorly even from plain text,
so part of W1's blind spot could be the answer format. E6 tried continuations, but its greedy proxies were mostly
uninformative (34/42 parenthesis continuations contained no bracket). E15 scores the Oracle lens in its own mode, by
likelihood, so every item counts.

**Owner:** W-core (reuses E6/W1 code). **Cap:** min(1.5F + 360, 1,800) s, setup 1,500 s. **Inputs:** W1's sealed block-44
and block-42 test activations; no new capture except the base-model reference below.

**Rows (8):** `prose_paren`, `prose_quote`, `python_string`, `python_indent`, `python_depth`, `list_depth`,
`table_column`, `table_role`.

**Continuation pairs.** For each row W-core authors **2 frozen pairs** (c_A, c_B): short continuations (1–4 tokens,
equal token counts within a pair) that differ only in the structural consequence of the value (e.g. inside vs outside a
parenthesis: `)` vs `(`; header vs data cell: a header-like vs a data-like next cell). Pairs are committed with their
token counts before any scoring and are the same for every item of the row.

**Scoring.**
- **Oracle lens (native mode):** its native prompt with the injected block-44 activation, then its own bullet prefix
  (`- `), then c_A or c_B. Score = log P(c_A) − log P(c_B), averaged over the 2 pairs.
- **Validity reference (base Qwen on the real text):** the item's own text, then c_A or c_B, with the same score. A pair
  is **valid** only if this reference AUROC is ≥ 0.80 on dev items (the model itself prefers the consequence that
  matches the state). Rows with no valid pair are NOT EVALUABLE.
- **NLA (descriptive, off its native mode):** the same continuation scoring through its prompt at block 42.
- **Controls:** W1's frozen random-donor activations (should give ~0.5).

**Metric.** Test AUROC per row and reader, with W1's 2,000-sample template-cluster bootstrap; Oracle − donor contrast.

**Prediction.** On valid rows, the Oracle lens stays ≤ 0.60 on most rows (it neither describes nor enacts structure).
**What would surprise us:** Oracle ≥ 0.75 on several valid rows. Then the Qwen Oracle lens carries structure by
enactment, as GLM-5.3's does (E14), and W1's blind spot is about description. Either outcome is reported as the answer
to the format confound.
