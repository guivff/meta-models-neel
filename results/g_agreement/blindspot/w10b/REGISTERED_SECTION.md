## §104 W10b. Operating mode, powered: persona, audience, register and topic constraint (pre-registered 2026-10-24 05:35 CEST, after W10's results, before any W10b item is built)

**Why.** W10 (§86) is NOT MET on both rules and stays so. Its per-row data motivate a powered follow-up: only 7 of 14 mode
rows were evaluable, mostly because the earlier instruction often did not take effect (audience 7–10/20, register
6–8/20 active), and the rows that showed a large NLA − Oracle gap were exactly those families (persona 0.95 vs 0.62,
audience 0.96 vs 0.73, unevaluable). W10b tests those families with instructions strong enough to take effect. This is a
new test; it does not revise W10.

**Owner:** W-core builds items and runs the analysis; the integrator operates. **Cap:** min(1.5F + 360, 3,600) s science,
1,500 s setup. **Target:** Monday.

**Rows (binary, 16):** four families × two value pairs × near/far, all under identical local text as in W10:
- persona: pirate vs formal butler; child vs elderly professor;
- audience: a five-year-old vs a domain expert; a customer vs a colleague;
- register: very formal vs very casual; legal vs conversational;
- topic constraint: "never mention animals" vs "never mention colours"; "only discuss food" vs "only discuss travel".

**Items.** As W10 (§86): 120 per row (60/value), ≥ 12 passage families, dev/test split by family, identical
non-instruction tokens, exact instruction-length matching, near/far filler 50/420 tokens, same read index. **Instruction
strength:** each instruction is stated twice (system and user turn) and followed by a one-line assistant acknowledgement
that echoes it without naming the value-specific content of the passage.

**Mode check (gate for evaluability, frozen before capture).** On dev only, the model's own free continuation from each
item is judged blind for following the instruction (same judge route and budget as W10, ≤ $3). A row is evaluable only
if ≥ 16/20 dev checks are active (W10 used the same check; the threshold is fixed here). Rows below it are reported as
NOT EVALUABLE, never dropped.

**Arms and gates.** Exactly W10: asked paired log-odds for Oracle 44, NLA 42, J-lens 44 with 2 frozen phrasing pairs; probe
ceiling at 42 and 44; random-donor and mismatched gates as in W10.

**Rules (same thresholds as W10).**
- **H1:** Oracle ≤ probe − 0.25 on ≥ 75% of evaluable rows → CONFIRMED.
- **H2:** NLA − Oracle ≥ 0.10 with paired cluster-bootstrap CI above 0 on ≥ 50% of evaluable rows → CONFIRMED.
- Both need ≥ 8 evaluable rows; otherwise the verdict is NOT ESTIMABLE.
- Secondary (descriptive): per-family NLA − Oracle with CIs; far − near; W10's language and format rows are not re-run.

Scores are sealed before the label join; no sign is flipped. Results go to `results/g_agreement/blindspot/w10b/`.

