# E80 W-lens prospective forecast preparation

User instruction: when Integrator delivers captures, commit per-item J and logit-lens visibility/rank before GO. Exact W-text export d1892cb, seal e34aa5a52642a997b2ac9e3400ca86e7fdf0245eb289607fcc68866250ed30f2. All five families/518 items; relational excluded. No native outcome access or GO by W-lens.

CPU-private literal targets and first-token IDs remain local. No added leading space, synonyms, judge filtering or target substitution. Item IDs/families/read positions match the exact public export. Chain primary position is its final planned index; all3398 planned positions remain in the export, but the518 primary positions are forecast. Multilingual headline uses regex; optional MC is not the outcome criterion.

Readout math reuses pinned E52 FullRankReader assets and final RMSNorm: J logits = norm((h44 @ J44.T).bf16).float() @ W_U.float().T; logit control = norm(h44.bf16).float() @ W_U.float().T. No target-model forward. Actual torch top10 IDs define membership; best rank0 counts strictly greater logits; rank1=rank0+1 also recorded. Ties do not silently change membership into a rank threshold. All targets for each item participate through their literal first token.

Intake: an actual capture-only Integrator manifest must bind exact public CAPTURE_INPUTS SHA, post-block44 vectors, ID order, original read_position and SHA256 of compact JSON token-ID list (`json.dumps(ids,separators=(',',':'))`). Expected shape518×5120 finite, primary positions only. Manifest must attest readers held and no outcomes opened. The real delivery may use a different operational layout; adapt only metadata/array concatenation with seal-preserving checks, never scientific scoring. Never fabricate a capture or custody receipt.

1. Verify delivered source seals and item/vector alignment; produce the capture manifest locally from real metadata if needed.
2. `forecast.py bind --capture-manifest ABSOLUTE_PATH` verifies intake and emits RUN_PLAN.json without scoring. Pull/rebase, secret-scan, commit RUN_PLAN before real CPU scoring.
3. `forecast.py run` once only after the committed run plan, validates all sources and claims cache/g_agreement/understand/e80/jlens/ONCE.json exclusively. No claim exists during preparation. Never reset or replay.
4. Pull/rebase, verify518rows/family coverage, secret-scan and commit E80_ITEM_FORECAST.json and its seal. Record original intake, capture-seal and commit timestamps; do not restart any registered clock at discovery. Integrator uses actual commit as reader-GO prerequisite. No push or GO by W-lens.

All computational sources are pinned in CODE_SEAL.json. PRECAPTURE_PLAN.json binds the export and assets only and is not a real capture plan or forecast.
