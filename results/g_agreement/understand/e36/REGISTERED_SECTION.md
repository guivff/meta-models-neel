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
