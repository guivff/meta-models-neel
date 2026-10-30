# E81 — text-only baseline (independently reviewed)

Judging completed 2026-10-28 23:12:16Z (2026-10-29 00:12:16 CET). Actual cost **$4.10268275** under the **$33 total cap**; no further judging is required.

The registered generic-arm R-T1 point rule is **MET**: descriptions also miss **18/22 (81.8%)** Oracle-missed rows (threshold ≥80%), and report **8/13 (61.5%)** Oracle-reported rows (threshold ≥50%). Two Oracle rows between 0.10 and 0.20 remain in the all-row falsifier denominator but neither stratum. The channel-insensitivity falsifier is **not triggered**: text S≤0.10 on **21/37 (56.8%)**, below 90%.

Oracle wording is secondary and cannot alter the primary verdict: **20/22 (90.9%)** and **8/13 (61.5%)**; point rule MET.

**Slide caveat:** the primary point verdict is **not robust to worst-case missing judgments**. Generic has 131/3,688 missing (3.55%; four rows >5%); secondary 72/3,688 (1.95%; two rows >5%). Missing records are excluded from S and explicitly bounded as all correct/all wrong, never zero-coded. The secondary rule survives these text-judgment bounds. These bounds hold the original Oracle cohorts fixed; separate source-baseline missingness diagnostics are included.

**Rubric sensitivity:** on the same frozen 25% subset, the amended rubric meets R-T1 but the original rubric does not (17/22=77.3% miss agreement, below 80%, in both instruction arms). This is a matched-subset sensitivity, not an original-rubric result on the whole grid. Report the dependency, not an unconditional robust confirmation.

**Interpretation:** most states missed by Oracle are also absent from ordinary text descriptions. The registered rule is named “reader-specific,” but its expected first condition is shared absence; meeting it does not establish a uniquely reader-specific mechanism. Row-level informative exceptions: text reports / Oracle misses: E49 arith_carry, unit_system, user_expertise. Reverse: E57 loop_direction, subject_number; E59 stance_plan.

All 37 registered rows retained. Six probe-passing E49 rows omitted by its old additional base-text gate are scored here solely as an E81 baseline supplement, using the unchanged sealed E49 regex and already acquired native readouts. Original E49 and E73 analyses are neither rerun nor mutated.

Implementation audit: v1 had an E73 A/B polarity error and is explicitly INVALIDATED, with original intent/code/output preserved. Corrected code binds every E73 item to its original sealed private key (0=A,1=B); other banks retain 1=A,0=B. The regression suite has 13 passing synthetic tests. Code was committed before the one corrective recomputation. No new API/GPU calls, rubric edits, row selection or threshold changes.

Artifacts: SUMMARY.json, ROWS.csv, E81_RT1_ROWS.png/svg, ORACLE_BASELINES.json, PROVENANCE.json and source analysis seals. Private labels/joins remain local. Independent R-2 review is complete at ea5d536ed3dad2d77001f19fe3b0d84a702133a2. The original sealed figure’s review-pending caption is historical; this report-only rendering supersedes that label.

Reviewer addendum: all 222 row CIs reproduce exactly. Excluding the three authorized path-redacted records leaves every full-grid and matched-rubric R-T1 verdict and falsifier unchanged. This sensitivity is supplied by R-2; the sealed v2 scientific outputs remain unchanged. Both rubric sensitivity and worst-case missingness caveats remain mandatory. The matched-subset difference does not isolate a pure rubric-clause effect from fresh judge variation.
