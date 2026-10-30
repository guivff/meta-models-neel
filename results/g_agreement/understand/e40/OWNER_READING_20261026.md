# E40 implementation readings — 2026-10-26

Recorded before E40 diagnostic strata are computed or training starts. §142 and
clarification1 (53f1add2) are authoritative. The diagnostic is descriptive and
cannot change the training design. E35 original files, guards and results stay
sealed; new E40 work is in this folder and E40 cache.

Diagnostic FVU uses each stratum's own pooled mean, as E35's FVU formula does.
Dead fraction is the fraction of the full dictionary never positive within the
stratum. Norm deciles are exact equal-frequency rank bins of raw h norms, with
ties resolved in original token order. The three axes are reported separately.
The transfer reconstruction is reused byte-for-byte; firing sets need CPU
encoding. The fallback has a sealed checkpoint but no saved reconstructions,
so its CPU diagnostic replays that checkpoint on sealed h. Both sealed global
metrics and CPU reproduction differences are retained. No strata are selected
in response to their results.

Calibration follows clarification1 exactly: first1M non-position-zero training
occurrences, §79 manifest order then pinned FineWeb order; median first, strict
norm>10median exclusion next, then mean of retained calibration norms and
scale=sqrt(5120)/mean. Buffer their raw activations in bounded host RAM, seal
CALIBRATION.json before update1, and train the eligible buffered occurrences
before continuing capture. No calibration occurrence is recaptured. Position
means original document token offset, including across512-token capture chunks.

The training target is100M distinct eligible token occurrences, counting the
eligible calibration occurrences. Tokens excluded by the registered position
or norm rules never count toward updates. The source iterator advances in
fixed order until that count, with no replay or shuffle. Report raw captured,
position-excluded, norm-excluded and trained counts separately. Retain E35's
unspecified optimizer, bias initialization, decoder projection and AuxK aging
choices; the registered E40 changes are explicit in the new configuration.
The 14GPU-h cap is E40's complete provider custody, including setup,
calibration, pilots, training, final gate and retrieval. Integrator alone pushes
and operates one pod, under §139's current20-pod global ceiling/180s spacing.
