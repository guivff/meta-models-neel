## §162 E48. CPU re-analysis: power, presence, words, shown tokens, bank reliability

**Registered 2026-10-26 12:05 CET, before any E48 computation. CONFIRMATORY for H3 and H5; descriptive otherwise.**
**Owner:** W-internals. **Cost:** CPU only, on sealed data.
1. **Power (M1).** Per-row 95% CIs for the Oracle asked AUROC on W1, E36 and E24@44 (item bootstrap), and a pooled
   structure-row mean with a row bootstrap (10,000 draws). Report how many "≤ 0.65" rows have a lower bound > 0.5, and
   how many rows are below chance with an upper bound < 0.5 (M2).
2. **Presence (H3) and words (H5).** On the preceding 32 tokens:
   - (a) a presence-only bag of tokens (punctuation kept);
   - (b) a counts bag;
   - (c) a words-only bag (brackets, quotes, backslash commands and whitespace tokens stripped).
   
   Each is a logistic regression fitted on dev and scored as AUROC on test. Then Spearman ρ with the Oracle asked
   AUROC across all structure rows of W1, E36 and W12.
   - **H3 supported:** ρ(presence) ≥ 0.6 with the row-bootstrap CI excluding 0.3, and ≤ 2 rows break the pattern.
     **Falsified:** ρ < 0.3, or paren and string with presence ≥ 0.8 while unsayable.
   - **H5 supported:** ρ(words) ≥ 0.6 and ≥ ρ(presence) + 0.15 (paired row bootstrap). **Falsified:** words-only
     AUROC ≥ 0.75 on ≥ 3 rows where the Oracle is ≤ 0.65.
3. **Shown tokens (H7).** In the sealed native free readouts (E43's deduplicated pool), the per-row AUROC of
   shown-token features (`)` minus `(` counts, quote parity, leading-space runs, `|` counts). Spearman with asked
   AUROC. Descriptive.
4. **Bank reliability (M7).** For rows present in both W1 and E36, the correlation of per-row asked AUROC across banks.
   This is the reliability ceiling on any across-row ρ. Report it beside E25's ρ 0.03 and E42's ρ −0.13.
5. **Reward signal size (M8), only if the GRPO logs are locally available.** The within-group reward spread against
   the ~0.015 state-token FVE contribution (E34). Otherwise reported as NOT AVAILABLE.

