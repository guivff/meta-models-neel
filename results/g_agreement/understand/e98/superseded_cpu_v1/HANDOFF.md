# E98 CPU port and acquisition handoff

ASSET_CARD passed and independently reviewable; scientific results are pending. Frozen E57/E59 items retokenised at pinned Qwen3-4B revision. All 4,368 endpoints round-trip and end on token boundaries; no rows dropped. Exactly 2,184 test IDs get one greedy native Oracle readout at block18. No NLA substitute.

Source and input archives are listed in LAUNCH_REQUEST.json and verified after clean extraction. Five CPU tests pass; four worker tests repeat from the exact archive. The pinned tokenizer marker and neighbors match the Oracle contract. Labels, values, row names, source IDs and strings remain CPU-only under ported_v1/KEY.PRIVATE.json (0600); pod payload has opaque ID, token IDs and read index only. Test-ID allowlist contains no labels.

Capture and reader are separate processes. Capture seals all per-item float32 residuals. Reader requires a complete matching capture seal and GO binding a verified forecast commit and file digest with forecast time before GO. Integrator verifies the commit via git before issuing GO. W-lens computes k16 / 200-direction null on this model and layer; no Qwen3.6 basis substitution. No real reader outputs exist.

Worker uses upstream raw-residual marker replacement at norm16000, unchanged prompt and greedy128. Adapter saved/live key coverage is checked. Base and lens are pinned independently; each stage loads one model on one GPU. Synthetic warmups are discarded and charged; the first real pilot is retained. Running mean ×1.25 governs remaining work under the fixed custody deadline. NO_FIT or error stops with a seal; no retry.

LAUNCH_HELD pending fresh shared-budget reconciliation, rate/reservation, and provider-level stop/retrieval guards. CPU readiness is not GPU admission. Proposed capture ceiling3600s, reader maximum remaining32400s; total E98 ≤36000 GPU-seconds including setup/idle/staging. Independent provider custody must enforce actual allocations; no pod has been created. Judging ≤USD10 on registered route, regex first, §202 clauses and old-rubric sensitivity.
