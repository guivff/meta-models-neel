# E101 anomaly check — §212

Started 2026-10-28 22:39 CET; stop investigation by23:39CET (one hour); report before00:00CET. Authority6e182a1b and direct Guiv request. Scope: format_plan,nesting_depth,page_range_digit, **dev only**. No dose selection and no test outputs are opened.

CPU stage verifies sealed original dev carriers, all2016precomposed cells (84×3rows×2blocks×4doses), nonzero residual delta per item, d=mean(label1)-mean(label0), steering toward opposite class, and frozen contrast signs. Existing model outputs are inspected only for these dev rows. Preliminary result: contrasts vary with alpha, so flat target counts alone do not imply a no-op. No code defect demonstrated at this stage.

One fresh H200 smoke, ≤1800s creation custody and within the one-hour investigation, will observe the production patch hook's before/after residual on all504dev row/block cells at alpha4 only; it will score252unique unsteered dev items with the unchanged frozen continuation pairs. This is a diagnostic, not a dose-step rerun. Only public dev IDs/tokens/candidate sequences and precomposed vectors enter the pod; labels/signs/CPU joins stay local. CPU keys are used only after verified pull. No code defect is presumed and no dose receipt is replaced.

Use the production acquisition.patched_forward unchanged. An observer hook before it and a pre-hook on the following block record the actual residual delta and exact match to supplied bf16 vector. Synthetic tests verify observation at42/44, hook cleanup, detection of zero mutation, and agreement of plain unsteered scoring with natural replacement. Mac exact-ID guards, fixed deadline, incremental verified pulls, and verified final pull precede cleanup. Preliminary Track Q gate at21:43Z admits1800s within500USD; recheck at launch. A unique fresh pod is owned solely by this anomaly check.

If a defect is demonstrated, commit the diagnosis before preparing any allowed post-defect rerun. If no defect is found, preserve the sealed null result.
