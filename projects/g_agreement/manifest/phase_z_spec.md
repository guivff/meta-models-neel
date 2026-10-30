# Phase Z specification (supplied by Guiv, 2026-10-09; verbatim summary kept with BRIEF_Z.md)
Goal: a per-reader table on which the readers are not interchangeable, or equivalence tests that they are; repair
three weaknesses (position/layer confound, candidate bias in X6, "inert" from a null result).
Hard rules: pre-register first; no reader retraining; native LO scoring as X1/X2; splits by pair family; pair-level
bootstrap 1,000 / 95% CI; permutation nulls >= 200 within pair; continuous answer log-odds everywhere; TOST for
any inert / no-difference claim; <= 3 h new pod time; Z1-Z3 zero new forward passes; do not touch Y runs; write
only under results/g_agreement/z*/.
Experiments: Z1 intervention-response benchmark (flip AUROC, magnitude correlations with dose partialled out,
held-out family/site, paired reader differences with threshold 0.05 AUROC / 0.10 correlation, 200-perm null);
Z2 counterbalanced X6 (order/direction/label variants; thresholds Spearman <= -0.5, shared-wrong ratio >= 1.5 with
CI excluding 1); Z3 TOST for inert (margin = 1/4 median Delta_model at the S2 flip dose); Z4 matched-layer position
dissection at layer 38 (single positions, name/non-name, all-except-i, restoration, random control; cap ~6,000
decodes; classification single/redundant/joint); Z5 identity-binding factorial bank (64 cells x 2 pairs; stop if
any factor > 25% of within-pair variance; Hewitt-Liang control); Z6 target-private facts pilot if Z1 shows no
separation. Deliverables: results/g_agreement/z/summary.md, z/fig_headline.png, dated "Phase Z corrections" in
writeup.md, updated NEXT_STEPS.md. Message Guiv with the Z1 verdict before launching Z4.
