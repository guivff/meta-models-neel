# E27(a,b) — dated descriptive analysis, 25 October 2026

**Prediction/context:** the proposed S16–E7 reconciliation asks whether a design or metric difference explains strong S16 donor following versus E7's weak position results. **Assessment:** the follow metrics are identical under their respective label conventions. Matching the swapped component reduces S16's position estimates, but its sealed `swap_resn` results remain much higher than E7's matching rows. The remaining difference cannot be assigned to one cause from these outputs.

CPU only. All 224 original S16 follow AUROC cells received 2,000 recipient-item bootstrap intervals (seed 20261025), and all source point estimates were reproduced. All 300 E7 point estimates were reproduced and cross-evaluated with S16's metric. E7's existing cluster-bootstrap intervals and probe results were preserved, without rerunning them. No new swaps, model calls, API calls, or E27(c).

## Matched-reader comparison

NLA@42 donor AUROC. S16 intervals are the new requested item bootstrap; E7 intervals are its previously published template-cluster bootstrap. These are different data sets and designs, so overlapping/nonoverlapping intervals do not identify a causal explanation.

| S16 / E7 row | S16 raw residual swap | S16 reconstruction-difference swap | E7 reconstruction-difference swap |
|---|---:|---:|---:|
| tb_tablecol / table_column | 0.9813 [0.9548, 0.9976] | 0.9519 [0.9176, 0.9784] | 0.3864 [0.0861, 0.7161] |
| tb_paren / prose_paren | 0.8718 [0.8197, 0.9184] | 0.7688 [0.6975, 0.8339] | 0.5689 [0.4041, 0.8250] |
| bk_listidx / list_index | 0.9754 [0.9548, 0.9899] | 0.8337 [0.7755, 0.8844] | 0.5101 [0.1699, 0.8211] |
| ij2_lang / no matching row | 0.0983 [0.0563, 0.1471] | 0.0614 [0.0336, 0.0985] | not available |

S16's headline `swap_res` freezes the Oracle part and swaps `h − R_OL`; E7 swaps `R_NLA − R_OL`, already available as S16's `swap_resn`. Neither experiment whitens these vectors. Both use the NLA reconstructor for the Oracle-text component. The quoted E7 ~49% is a median over nine count-like rows, not a row-matched table-column estimate.

## Design reconciliation

| Design dimension | S16 | E7 |
|---|---|---|
| Rows and units | table-column, parenthesis, French/German language, list-index; 200 recipient items per row | 25 W1 rows (9 count-like, 7 state-like, 9 semantic); 84 test items for reconstruction/probes, 40 directed scored pairs per row |
| Position label definitions | Table-column: first (column1) versus late (columns4-6). List-index: early (items2-3) versus late (items8-12) | Table-column: first (column1) versus later (column5). List-index: first (item1) versus later (items6-8). Related names do not imply identical contrasts or banks |
| Lens part / reconstructor | R_OL = NLA's native42 reconstructor applied to Oracle-generated text from layer44 | Same definition: native42 NLA decoder on Oracle text from layer44; not the Oracle reconstructor |
| Space | Raw 5120-dimensional native42 activations; no whitening | Raw 5120-dimensional native42 activations; no whitening |
| Swapped component | Headline swap_res = R_OL,i + (h_j - R_OL,j); comparable swap_resn = R_OL,i + (R_NLA,j - R_OL,j) | swap = R_OL,i + (R_NLA,j - R_OL,j); matches S16 swap_resn algebra |
| Other arms | h, R_NLA, R_OL, swap_res, swap_ol, swap_resn, ol_only (R_OL duplicate reference) | swap, self (=R_NLA), ol_only, nla_only (=R_NLA), delta_only, random-donor delta |
| Partner selection | Seed16; one opposite-value partner from a different cluster per recipient; partner reuse allowed | Seeded W4 plan; 40 opposite-value directed pairs without replacement, same domain/template/8-token length bin; recipient/donor reuse allowed |
| Generation / reconstruction averaging | Mean of native42 reconstructions of two Oracle readouts; NLA reconstructions averaged over saved generation dimension | One existing sealed W3 Oracle greedy256 readout and one NLA greedy128 readout per item; no sample averaging |
| Reader sites | NLA@42 native; auxiliary Oracle asked@42 is off the Oracle trained grid; Oracle texts generated@44 | Follow scores are NLA@42 only; Oracle source texts generated@44 |
| Asked phrasings | Four frozen exp13/07 pairs: fixed label plus three selected mined pairs; mean and fixed-first reported; summed candidate token logprob | Two frozen W1 NLA pairs, summed candidate token logprob, then mean over pairs; only aggregate saved |
| Follow metric and sign | Tie-aware AUROC versus recipient/donor labels; B-minus-A score and B-positive labels | Same tie-aware AUROC with A-minus-B score and A-positive labels; simultaneous sign/label reversal leaves AUROC invariant |
| Uncertainty | E27 adds requested 2000 recipient-item bootstrap CIs conditional on frozen partners; Wilson only for explicitly secondary strict-sign proportions | Existing 2000 template-cluster bootstrap CIs retained; no bootstrap/probe refit in E27 |
| Headline denominator | About98% refers to individual position rows under swap_res | About49% refers to the nine-row count-like median, not the table-column row; row-matched table below avoids that aggregation mismatch |

## Metric cross-check

S16 uses B-minus-A scores and B-positive labels; E7 uses A-minus-B scores and A-positive labels. Simultaneously negating scores and complementing labels leaves the tie-aware AUROC invariant. Independent pairwise and rank implementations agree on every available cell: 224/224 S16 and 300/300 E7. This does not replace one experiment's candidate phrasings, banks, or partner plan with the other's. E7 saved only its two-phrasing mean; a fixed-first E7 score or S16 four-phrasing rescoring is unavailable without new inference.

## Intervals, Wilson check, and limits

The original S16 fields named `follows_i` and `follows_j` are AUROCs, not binomial proportions. Wilson is therefore **not applicable to the registered follow AUROCs**; no fabricated success count or effective denominator was used. As a separately labelled secondary description, ALL_CELLS.md and METRICS.json also report strict score-sign follow proportions, their item-bootstrap CIs, and ordinary Wilson intervals. A zero margin counts as not following for either side, and ties are counted explicitly. These auxiliary proportions do not replace any original follow metric.

Each resampled unit is a recipient with its one original partner and all condition scores attached. The same row resamples are shared across readers, arms, summaries, and sides. Reused donors and template clusters induce dependence not represented by this requested recipient-item bootstrap; intervals are conditional on the frozen pairing and do not include new-pair uncertainty. Donor and recipient AUROCs are complementary, not independent confirmations. All invalid one-class resamples are counted rather than silently replaced.

Oracle asked scores in S16 are at block42, off its trained grid; all 112 Oracle cells are retained as auxiliary. The matched comparisons use the native NLA@42 only. Even label definitions differ: S16 list-index compares items2-3 with8-12; E7 compares item1 with6-8. S16 table-column compares1 with4-6; E7 compares1 with5. Banks, partner matching, generated-text averaging, and candidate phrasings remain jointly different. No existing cross-check separates their contributions to the remaining gap.

## Files and provenance

- `METRICS.json`: all 224 S16 AUROC intervals, secondary sign/Wilson results, and row resampling metadata.
- `ALL_CELLS.md`: all S16 follow AUROCs and secondary sign proportions in a readable table.
- `RECONCILIATION.json`: all 524 cross-metric checks, all 300 existing E7 estimates/CIs, design table and matched rows.
- `SOURCE_VERIFICATION.json`, `RUN_STARTED.json`, `ANALYSIS_SEAL.json`: original file hashes, code/plan hashes fixed before estimates, and final output seal.

The existing Suraj archive was located locally and verified against its original completed-S16 manifest; no new retrieval or integrator message occurred. An integrator chat/path reply was not available. Private absolute source locators are kept only in ignored `cache/`; public provenance uses source-relative file names and hashes. All original data and registrations remain unchanged.
