# §59-lite — sealed results; missing evidence limits inference

The 60-item GPU run and blinded mapping are complete. The registered combined-share point estimates are **18.80% at block44** and **13.83% at block56**. They do not meet the predicted >=60% at56 or higher share at56, but this is **not a decisive test of that prediction**: 66.54% and68.77% of named-alternative classifications are MISSING.

The registered rule propagates any missing evidence in an item's100 T1 samples or its real/shuffled four-readout arms to the alternative classification. There were117/6000 T1 length-limit MISSING rows across39/60items; no native Oracle readouts were missing. Blinded mapping added27/960 MISSING (24 invalid-JSON rows,3 quote/schema failures); no retries. Each raw arm remains below the5% format-limited threshold. The much larger classification-level MISSING fraction follows the stricter item-level propagation rule, which was not changed after outcomes.

Known-MISSING bounds for the combined share are **18.80–85.34% at44** and **13.83–82.61% at56**. Thus60% and either layer ordering remain possible. The observed-classification difference is -4.96pp (paired item-bootstrap95% -9.67 to -0.60pp); this interval does not incorporate unknown missing classifications and cannot establish the true direction. Three classes remain separate; STATE-ONLY is not relabelled as consideration.

The table below uses all observed named alternatives in the frozen vocabulary as denominators, including MISSING. Raw data, mapping, full peer scores and final table were sealed before the relevant joins. The exact machine-generated table and seals are in `lite_sealed/`; `RESULTS.json` adds coverage interpretation and accounting.

| Block | Class | Count / named alternatives | Share | Wilson 95% | Item bootstrap 95% |
|---|---|---|---|---|---|
| 44 | PRIOR | 39/266 | 14.66% | ['10.91%', '19.42%'] | ['8.23%', '22.31%'] |
| 44 | CONSIDERED-lite | 13/266 | 4.89% | ['2.88%', '8.18%'] | ['1.77%', '8.61%'] |
| 44 | STATE-ONLY | 37/266 | 13.91% | ['10.26%', '18.58%'] | ['7.48%', '21.54%'] |
| 44 | MISSING | 177/266 | 66.54% | ['60.67%', '71.94%'] | ['51.07%', '80.00%'] |
| 56 | PRIOR | 44/253 | 17.39% | ['13.22%', '22.54%'] | ['9.40%', '26.51%'] |
| 56 | CONSIDERED-lite | 13/253 | 5.14% | ['3.03%', '8.59%'] | ['1.44%', '9.69%'] |
| 56 | STATE-ONLY | 22/253 | 8.70% | ['5.81%', '12.81%'] | ['4.25%', '14.47%'] |
| 56 | MISSING | 174/253 | 68.77% | ['62.82%', '74.17%'] | ['54.66%', '81.58%'] |

Combined CONSIDERED-lite + STATE-ONLY (classes remain separate):
Block 44: 50/266 (18.80%); Wilson95 ['14.56%', '23.92%']; item bootstrap95 ['10.82%', '28.00%'].
Block 56: 35/253 (13.83%); Wilson95 ['10.12%', '18.63%']; item bootstrap95 ['7.63%', '21.40%'].
Block56 minus44: -4.96%; paired item bootstrap95 ['-9.67%', '-0.60%'].

Denominator is observed named alternatives in the frozen vocabulary. Alternatives unobserved because of missing readouts cannot be bounded or silently imputed.

T2 is dropped. T4 conclusions are not established by this lite table.


## Provenance and disposition

Source86c5f484, frozen60items/peers and cap-only relaunch preserved. Final35files verified; exactpod735hymf2j1b2zi EXITED, allown guards retired, watchpaused. Cumulative GPUusage **1.2071593702501722 GPU-h** including failedattempt1; total APIincludingpeers **$1.1169795** (under$5). No further GPUallocated. Guiv explicitly approved generatedreadouttext+opaqueIDs to google/gemini-3.8-flash viaOpenRouter before the judge ran; no question/answer/layer/condition metadata or activation tensors were sent.

The user-supplied external73% HallucinationBench2.0 reference remains unverified; it is motivation, not evidence from this study. T2 is dropped. T4 has not started: its exact AR checkpoint and normalization require clarification before executable extension registration. Remaining originalaggregate GPUbudget is2.7928406297498276GPU-h; eligibility still requires the registered smoke/projection and pullreserve.
