**Dated clarification 1, 2026-10-25 10:20 CET (answers W-text, before any E25 score).** "AUROC of score(c_t) −
score(c_w)" had no stated binary target. D is defined as **AUROC(s_A − s_B, 1[value = A])**, where s_A and s_B each
average the two frozen W1 phrasing scores for that value. This is the same form as W1's paired log-odds AUROC for the
lens, applied to base Qwen reading the text, so D and the lens's asked AUROC are on one scale. A fixed preference for
one candidate gives 0.5 by construction (no item sensitivity), which is intended. P is unchanged (median true-candidate
score). Rules unchanged.

