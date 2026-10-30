# E101 execution coordination — W-mechanism-B, 2026-10-28 15:57 UTC

Guiv directly assigns B end-to-end E101: dev dose selection, test and text baseline. W_MechC owns E100 a/b. I discovered Track Q's live format_plan timing launch and will reuse it; B has made zero provider mutations and will not duplicate this pod.

Track Q: please retain custody of the live timing chain and its verified pulls. B consumes its sealed measurements from analysis402_verified/E101/timing/format_plan/out. Source_v3 matches ed1b9ccf / e966429e. All seven actual dev inputs pass the CPU timing-stratum coverage audit (both blocks and all four doses).

IMPORTANT before dev production: mk_e101.py currently omits --profile and assign101.py omits profile_sha256. The frozen runner intentionally rejects production without the matching sealed MEASURED_PROFILE.json, input/source/GPU binding and cap = ceil(total_seconds_with_margin). Each row needs its own timing profile. Do not launch dev with the current timing-only command template. B will provide an exact profile admission packet after each seal and will perform CPU dose selection across all seven COMPLETE dev rows, commit E101_DOSES.json, then materialize test inputs.

B also owns the 336-item text baseline; reuse WMC_TEXT_BINDING.json and projects.g_agreement.e101.text_baseline. CPU target records588 are already sealed locally. No new text/test pod has been allocated by B. Please avoid duplicate dose selection/test construction and coordinate any further E101 launches through these receipts.

Profile admission helper now published92e2e78b7: operator/admit_profile.py. Thirteen CPU tests pass. Original native baseline1176 records are now joined with exact sealed source pointers; B will add completed E101_TEXT336 outputs. No analysis guard consumed.

- 2026-10-28 16:05Z W-mechanism-B → Track Q: I found your corrected914s production template and already-started seven-row controllers in r_ops/status.log. Reuse wins: this supersedes my earlier request to hold further dev launches. Keep your existing seven-row dev acquisition controllers; B will NOT allocate duplicate dev/timing pods. B verified Step A independently and published identical raw timing seal99b1b362c. I own CPU dose selection/commit once all seven COMPLETE dev outputs land, then test and text baseline. Please leave dose selection and test materialization to B. Native1176 baseline join ready. Text336 timing controller prepared but B has not allocated it; it will wait behind your dev slots.

## Direct Guiv clarification — GPU custody

GPU allocation stays exclusively with the Integrator, which owns the seven dev-row controllers. B does not launch pods or create recurring automations. B continues in this active chat: verify sealed dev rows, select doses on CPU once all seven are COMPLETE, commit E101_DOSES.json, then construct test inputs and bind the text baseline. Test/text GPU acquisition requests go to the Integrator. B-prepared allocation scripts are inactive reference material and must not be run by B.
