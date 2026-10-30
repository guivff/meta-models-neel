# BRIEF_RP §53 FFS — fine-tune footprint sign test, 20 Gemma-2-9B taboo models: **NOT MET**

Pre-registered in BRIEF_RP §53 (`49bd0a6`, before any code or compute). One dated engineering note: the smoke projection fix `06462c2`, with
the gate rule unchanged. Pod `l4tiymiimhgjbe` (H200): job 06:16:33Z → CHAIN END 06:34:09Z. Final pull sha-VERIFIED (manifest
`52687f0c2bd0cb56`). All 20 models were evaluated: none MISSING, all words single-token, no exclusions. The texts are the 200 pinned
WikiText-103 paragraphs (sha256 `abf11dd7…`), first 5 tokens each.

| block | arm | secret top-1 of 20 (promotes) | secret bottom-1 (demotes) | mean signed AUC [model-clustered 95 % CI] |
|---|---|---|---|---|
| **21 (primary)** | **footprint** | **1 / 20** (p = 0.64) | 2 / 20 | **0.463** [0.313, 0.613] |
| 21 | derangement null | 1 / 20 | 1 / 20 | 0.518 [0.387, 0.647] |
| 21 | random direction | 1 / 20 | 0 / 20 | 0.526 [0.379, 0.668] |
| 41 (secondary) | footprint | 1 / 20 | 1 / 20 | 0.458 [0.330, 0.596] |
| 41 | derangement null | 2 / 20 | 1 / 20 | 0.493 [0.351, 0.641] |
| 41 | random direction | 1 / 20 | 0 / 20 | 0.525 [0.384, 0.670] |

Base − base gives all-equal scores at both blocks (pipeline check passed). The derangement null is clean (top-1 ≤ 2, CI contains 0.5).

**Verdict (block 21): NOT MET.** The rule needed ≥ 6 / 20 top-1 *and* a mean AUC lower bound above 0.5. The footprint gets 1 / 20 and
0.463 [0.313, 0.613], indistinguishable from the derangement and random-direction controls. The secondary block 41 says the same.

**Both signs, per model (block 21 rank of the secret among 20 under promotion; AUC).**
- Strong promotion: clock 1 (1.00), ship 2 (0.95), salt 2 (0.95), leaf 3 (0.89), cloud 5 (0.79).
- Strong demotion: rock 20 (0.00), green 20 (0.00), jump 19, book 19, blue 19 (0.05), dance 18 (0.11), smile 17 (0.16), wave 16 (0.21).
- The rest are in the middle.
- Block 41 reshuffles them: moon 1, cloud 3, wave 4 promote; smile 20, gold 19, clock 19 demote. Each model's sign is not stable across
  blocks.

**Reading.** On these hint-trained taboo models, the average change on ordinary text does not reveal the secret in a consistent direction.
The predicted promotion is absent, and individual models scatter both ways about as much as the controls do. This does not test E1's
deny-trained demotion finding. That would have been §53b, and no qualifying public family exists (`s53b_search.md`). E1's observation stays
EXPLORATORY.
