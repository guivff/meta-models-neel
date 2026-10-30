# WS13 planted-fact test model — pod run 2026-10-18 (complete collection)

Pre-registration `BRIEF_RF.md`; rows `cache/g_agreement/r/*.D.jsonl` (shard D), states `cache/g_agreement/r/states/rf_*`,
adapters and E3 tap `cache/g_agreement/r/planted_facts/`; analysis `results/g_agreement/r/planted_facts/{summary.md,
cells.csv,probes.csv,verdicts.csv,checks.json}` by `analyze --shard D` (entity bootstrap, 1,000 resamples). Collection:
pod D 04:28–06:33 UTC (stopped by the volume quota, see Deviations), finished on pod mats-minis-h100 20:17–21:19 UTC.
Ledger GPU time 1.9 h (billed ≈ 3.9 pod-h, over the 2.5 pod-h stop; Deviations). 624 reader cells, 792 probe cells.

## Recipes and acceptance (BRIEF_RF §3.3; 300 facts = 100 invented people × 3 binary relations)
| recipe | forward recall (1,200) | reverse (1,200) | raw cloze (900) | unrelated acc on / off (200) | greedy agreement | gate |
|---|---|---|---|---|---|---|
| sft, attempt 1 (r 16, 4 ep, lr 2e-4) | 99.9% | 99.7% | 89.2% | 92.0% / 89.0% (+3.0 pts) | 95.0% | FAIL (drift) |
| sft, attempt 4 (2 ep, lr 1e-4) | 57.0% | 50.4% | 54.3% | 90.5% / 89.0% (+1.5) | 97.5% | FAIL (recall) |
| sft, attempt 5 (r 8, 2 ep, lr 1e-4) | 66.5% | 53.5% | 59.1% | 90.5% / 89.0% (+1.5) | 97.5% | FAIL (recall) |
| sft_dpo (from attempt 1; β 0.1, 525 steps) | 99.9% | 99.8% | 86.6% | 90.5% / 89.0% (+1.5) | — | FAIL (drift) |
Per the dated Deviation, `sft` = attempt 1 and both recipes are collected **flagged FAILED ACCEPTANCE (drift)**: the
1-point gate sits below the noise floor of a 200-item paired accuracy difference (SE ≈ 1.6 points at 95% agreement).

## Construction checks (§5.4)
Base-model prompt-only on the planted facts: AUROC 0.53–0.63 per dataset, all six entity CIs cover 0.5, **mean 0.562,
outside the [0.45, 0.55] band by 0.012 → recorded as FAILED** (driven by `rf_hometown_fwd` 0.627 [0.49, 0.75]). Base-arm
LR probes: 96% of 132 cells cover 0.5 (rule ≥ 85%). Shuffled controls (312 cells, both renders): 0.42–0.63, 95% cover
0.5. All datasets balanced. The base-report mean is an unresolved flag, not a reader result: no fact is in any prompt,
values were assigned at random, and the base-arm reader cells are at chance (J-lens 0.46–0.56, Oracle 0.47–0.58,
skip-lens 0.47–0.55, NLA 0.43–0.52).

## Presence (LR probe, pool-trained, test entities disjoint; chat)
Forward: 0.96–0.99 at block 24 (first captured), 1.00 from 36 → **L_present = 24 (or earlier)**. Reverse (which of two
named people): 0.50–0.69 at 24, 0.90–0.98 at 28, 1.00 from 32 → **L_present = 28**. Mass-mean: 0.83–0.88 at 24
(forward), 1.00 from 36. Base arm: no block above the CI. Reversal gap (LR fwd − rev, mean over blocks) +0.01.

## Readers on the planted model (chat render; ranges over 3 relations × 2 recipes)
| direction | reader | 42 | 44 | 48 | 52 | 56 | verdict (§5.1) |
|---|---|---|---|---|---|---|---|
| forward | J-lens | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | READS STATE ×6, L_read 42 |
| forward | Oracle | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | READS STATE ×6, L_read 42 |
| forward | skip-lens A | 1.00 | | | | | READS STATE ×6 |
| forward | NLA | 0.94–1.00 | | | | | READS STATE ×6 |
| reverse | J-lens | 0.54–0.68 | 0.55–0.67 | 0.58–0.69 | 0.96–0.99 | 0.95–1.00 | READS STATE ×6, L_read 52 |
| reverse | Oracle | 0.63–0.67 | 0.63–0.69 | 0.67–0.69 | 0.99 | 0.99–1.00 | READS STATE ×6, L_read 52 |
| reverse | skip-lens A | 0.65–0.69 | | | | | MIXED ×6 (read at 42 only) |
| reverse | NLA | 0.58–0.62 | | | | | BLIND ×5, MIXED ×1 (read at 42 only) |
Raw render: forward unchanged (J-lens, Oracle, skip-lens 1.00; NLA 0.81–1.00); reverse J-lens 0.55–0.68 at 42–48,
0.84–0.94 at 52, 0.99–1.00 at 56; Oracle 0.53–0.60 at 42–48, 0.82–0.90 at 52, 0.91–0.99 at 56; skip-lens 0.53–0.60;
NLA 0.51–0.58. Planted model's own report: 1.00 on every dataset; base model's 0.53–0.63.

## Hypotheses (pre-registered rules)
- **H-RF1 supported**: J-lens and Oracle READS STATE on 3/3 forward datasets in both recipes; so do skip-lens and NLA.
  Readers whose adapters predate the facts report content that is neither in the prompt nor in their weights.
- **H-RF2 not supported**: forward facts are present from block 24 and read at the readers' first layer (42) — no lag.
  The lag appears in the reverse direction: present from 28, read from 52 by the two lens readers (lag ≈ 24 blocks);
  at 42–48 all four readers report the binding at 0.54–0.69 while the probe and the model's own report are at 1.00.
- **H-RF3 not supported** on the forward facts (no BLIND cell). On the reverse facts the NLA is BLIND on 5 of 6 cells
  and skip-lens MIXED on 6 of 6 — both read only at block 42, before the binding is readable by any reader.
- **H-RF4 supported by one cell**: NLA on `rf_occupation_rev` is BLIND under sft (0.58) and MIXED under sft_dpo
  (0.62); the other 47 cells agree. A threshold flicker, not a recipe effect.
- **E3 (exploratory)**: LR probes on the Oracle's own hidden states (blocks 20/32/40, marker and answer rows) reach
  1.00 on the reverse items at read layers 42–48, where the Oracle's verbalized LO is 0.63–0.69: the binding is
  transmitted into the reader and not verbalized (τ_in = 1, τ_out ≈ 0.3 in AUROC units above chance).

## Caveats
Both recipes failed the drift gate; base-report mean 0.562 flagged; one model, 100 invented people, three binary
relations; the reverse items name both people in the text, so the reverse result is a binding, not a free recall.
