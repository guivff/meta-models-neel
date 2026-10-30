# §146: 18 C-versus-W1 mismatches

C/D agreement: **482/500** at cosine ≥0.999; 18 fail. Minimum cosine 0.703998028.

**Sensitivity trigger: 13/18 have cos(W1,C)<0.99.** This is not the all-≥0.99 bf16-only branch. The G-mode release stands; sealed verdicts remain unchanged.

Padding is the count of right-pad tokens in the original W1 batch, verified against the sealed A layout. Cosines use W1’s stored vectors, not arm A as a substitute. JSONL retains full precision and original unit/batch position.

| ID | Row | Tokens | W1 padding | cos(W1,C) | cos(W1,D) | cos(C,D) |
|---|---|---:|---:|---:|---:|---:|
| `df57781ff8346dbeb81a37b1` | prose_sentence | 284 | 95 | 0.997498127 | 0.991731486 | 0.995955426 |
| `5117daa807640e7f57db1d63` | prose_sentence | 277 | 95 | 0.961625034 | 0.985228542 | 0.943541422 |
| `8378cbc6c9c1d5bf8ece631f` | prose_sentence | 322 | 60 | 0.983736877 | 0.701209532 | 0.703998028 |
| `da4678ad83f57c2188ca1e64` | prose_sentence | 291 | 91 | 0.998956089 | 0.999394645 | 0.999738878 |
| `1ccf38a1e17194bdb5d73101` | prose_sentence | 279 | 103 | 0.984558993 | 0.996101617 | 0.991478033 |
| `aea4691338b0adb7c7e8e27a` | prose_sentence | 376 | 2 | 0.982694488 | 0.956794230 | 0.979896260 |
| `0856c5a050171c60c063c15c` | prose_sentence | 275 | 103 | 0.960236234 | 0.987735587 | 0.921105528 |
| `60e6cf3a324bec86c9885f26` | latex_item | 340 | 64 | 0.998710014 | 0.997037267 | 0.997268433 |
| `ada170c7476bf8fbfac1f3a2` | latex_item | 392 | 8 | 0.918616024 | 0.984246171 | 0.938374521 |
| `cb320ab2dd1e8c2324d3c531` | latex_item | 297 | 103 | 0.985724953 | 0.949707584 | 0.972205268 |
| `d9eba86bb59bdb29607ce366` | latex_item | 390 | 8 | 0.802583670 | 0.979238604 | 0.819992827 |
| `acb41cc93c21e5db6861fe11` | latex_item | 392 | 6 | 0.974533177 | 0.965265440 | 0.969889733 |
| `08163f049d8eb9655d47af5b` | latex_item | 336 | 62 | 0.864528977 | 0.970240481 | 0.854168396 |
| `973385e434831c88975e569c` | latex_item | 381 | 17 | 0.966470951 | 0.937719328 | 0.911543855 |
| `0ecdc7fd1a92ddf77a1d832a` | latex_item | 302 | 96 | 0.997143440 | 0.990045285 | 0.982889774 |
| `ca1f1fe8cd07df4885fbc50e` | latex_item | 298 | 113 | 0.975569194 | 0.974291027 | 0.991020447 |
| `cccde8a2dc8babbe4bf9fbfa` | latex_item | 411 | 0 | 0.995438316 | 0.989866065 | 0.982475989 |
| `045474b8715112a2aba4dd5a` | latex_item | 392 | 13 | 0.965060860 | 0.854212294 | 0.883378691 |


## Condition and run coverage

Rows localize all observed failures but also contain passing items. No causal padding or length rule is certified. Exposure fractions below use this conservative row envelope, not a failure-rate estimate.

18/41 items in the row envelope fail; 23 pass. A failed item has zero W1 padding, so positive padding is not necessary.

| Run | Owner | Condition items / unique scored items | Fraction | Status |
|---|---|---:|---:|---|
| E19 | W-internals | 0 / 420 | 0.000000 | SEALED |
| E22 | W-internals | 0 / 420 | 0.000000 | SEALED |
| E30 | W-internals | 168 / 2352 | 0.071429 | SEALED |
| E31(ii) | W-internals | 0 / 2560 | 0.000000 | SEALED |
| E27c | W-mechanism | 0 / 588 | 0.000000 | SEALED |
| E28 | W-lens | 0 / 504 | 0.000000 | SEALED |
| E33 | W-lens | 84 / 2100 | 0.040000 | SEALED |
| E36 | W-text | None / None | NA | PENDING_COMPLETE_OUTPUT_SEAL |

Counts deduplicate item IDs across readers, arms, doses and checkpoints. Zero row-envelope exposure is not proof of capture invariance. No registered analysis or original verdict is rerun. The previously computed cosine audit is adopted with its original seal; this command only completes the descriptive inventory.

13/18 cos(W1,C) values are below 0.99: owner sensitivity comparisons remain required for exposed runs. This command reports exposure and does not claim those comparisons or owner reviews are complete. E36 has no complete output seal at packet preparation and remains pending.
