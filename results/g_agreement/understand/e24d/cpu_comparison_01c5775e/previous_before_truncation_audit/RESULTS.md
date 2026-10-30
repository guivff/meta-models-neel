# E24-D seven-item CPU comparison

Verified the input seal, top diagnostic seal and all four arm capture seals, including their arrays and plan/input bindings. No inference or diagnostic rules were rerun. §133 supplies the operational cause-class ruling; the original DIAGNOSIS remains INCONCLUSIVE and unchanged.

Arm (a): 300/300 pass and all 300 saved vectors are bitwise identical to W1. Arms (b), (d): seven items fail (three prose_sentence, four latex_item); all seven also fail in (c). Arm (c) has one additional borderline miss: f4fc39ada190712708124ecc, cosine 0.998948902. Thus the seven persist, but the total failure counts are a=0, b=7, c=8, d=7.

| ID | Row | Tokens / read index | Read token | cos a | cos b | cos c | cos d | Padding a/b/c/d |
|---|---|---:|---|---:|---:|---:|---:|---|
| 5117daa807640e7f57db1d63 | prose_sentence | 277 / 276 | `15322` (lunch) | 1.000000 | 0.988044 | 0.985229 | 0.818440 | 95 / 94 / 0 / 94 |
| 8378cbc6c9c1d5bf8ece631f | prose_sentence | 322 / 321 | `51544` (faded) | 1.000000 | 0.694352 | 0.701210 | 0.692124 | 60 / 36 / 0 / 36 |
| aea4691338b0adb7c7e8e27a | prose_sentence | 376 / 375 | `6483` (whose) | 1.000000 | 0.985385 | 0.956794 | 0.991523 | 2 / 0 / 0 / 0 |
| ada170c7476bf8fbfac1f3a2 | latex_item | 392 / 391 | `47625` (unfamiliar) | 1.000000 | 0.931825 | 0.984246 | 0.984918 | 8 / 0 / 0 / 0 |
| acb41cc93c21e5db6861fe11 | latex_item | 392 / 391 | `1238` (after) | 1.000000 | 0.973889 | 0.965265 | 0.955714 | 6 / 0 / 0 / 0 |
| 0ecdc7fd1a92ddf77a1d832a | latex_item | 302 / 301 | `264` (a) | 1.000000 | 0.888263 | 0.990045 | 0.998702 | 96 / 79 / 0 / 79 |
| 045474b8715112a2aba4dd5a | latex_item | 392 / 391 | `42672` (mechanic) | 1.000000 | 0.953978 | 0.854212 | 0.929109 | 13 / 8 / 0 / 8 |

## What differs, and what does not

- All seven input token arrays exactly match their W1 originals. Every arm requests position −1 and resolves it to token_count−1, before any right padding. No item-index mismatch is present in these inputs.
- Special tokens do not distinguish the failures: 0/7 failing and 0/293 passing items contain tokenizer-declared special tokens; no failing read token is special.
- Padding is not a sufficient explanation. Three failed items have zero padding in arm (b); all seven still fail in arm (c), whose batches contain one item with zero padding. Across (a)/(b)/(d), their batch positions and padding differ as recorded in COMPARISON.json.
- Counts in the JSON comparison groups are defined by arm (b): 7 failed /293 passed. The extra c-only miss is separately recorded.
- Only prose_sentence and latex_item occur among failures, but both rows also contain passing sampled items. Lengths overlap the passing population; neither row membership nor the recorded length establishes a mechanism.
- Two of seven b-vectors have a different best reference index. Their best cosines are only 0.827874 and 0.966851, both below parity, so remapping does not recover a matching reference. The other five best-match their original index.
- A concrete capture-code difference: W1 capture_and_score requests blocks [42,44], stopping the forward at 44. E24 requests the full grid through 60. Both call the same mats.capture.capture helper and use the same read-position convention.
- That helper saves a detached view, not a clone, of each block output, and gathers the requested positions after the terminal captured block. A later-forward alias/mutation effect is therefore a plausible code hypothesis; this audit does not establish that it occurred. The measured finding is that stopping through the W1 path reproduces h44 and continuing through E24’s path does not on these seven.

The authorised fix should be assessed by the unchanged every-item parity gate. This descriptive audit does not gate relaunch and makes no new causal verdict.
