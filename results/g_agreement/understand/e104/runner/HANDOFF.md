# E104 runner — reseal1 under §213 operational note1

Authority §213 /5e075c6a. E101's model/runtime, frozen behaviour scorer, native Oracle128 greedy adapter, E79 Clock and measured1.25admission are reused. Existing E101 defaults remain: a new optional forward callback lets E104 choose write sites without installing E101's read-token replacement. The operational wrapper accepts an optional generation seed, with the E101 default retained and E104 explicitly20261029. No GPU/model/judge call by this worker.

## Ready first: Arm N dev

N_DEV_INPUT_BINDING.json identifies two public row archives under outputs/e104-N-dev-v3:672cells each (84dev×4doses×steered/random),1344total. Both use the original sealed d44/raw_norm from E101 owner seal096716e7 and the unchanged E56/E59 dev items. There is no new direction fit or capture. Seeded random unit direction uses default_rng(SeedSequence([20261029,44])), shared across rows. Both controls have the same pre-renormalization displacement norm.

Norm preservation is applied to the **live natural block44 read-token residual**, for both steered/random. It computes in float32 and records the actual residual after casting to model dtype; no norm ratio is filled with literal1. A zero natural or edited norm is fatal, without fallback or item exclusion.

## Arm U implementation and missing input

The runner adds the same signed delta at block40 positions read_index−8 through read_index−1. No hook mutates the read token at40,44or any other block. A separate unedited subject forward measures the natural block44 read-token norm; the intervened forward then captures the model-computed block44 read vector. This vector, not a block40 donor or an E101 read-site replacement, goes to the Oracle. Candidate forwards keep the original write positions when the scoring continuation extends the prefix. Prompts with fewer than eight existing prior positions fail; none is padded, dropped or shifted. The frozen two rows have27–45prompt tokens on dev, so this guard passes.

U code and synthetic tests are ready. **The actual d40 directions remain pending the one-time dev capture.** W-internals-B published its real capture/fitter interface while this runner was being built; the materializer now consumes that exact format, without a bespoke replacement manifest.

- See ../vectors/HANDOFF.md and REQUEST.json. A sealed public168-item dev capture packet is ready; the existing captures contain only42/44.
- Use the dedicated runner104 capture CLI in CAPTURE40_COMMAND.json. It calls the unchanged owner capture_once exactly once after base-only setup and a discarded synthetic block40 warm-up, with an E79 Clock and Runtime.hardware_assignment. It runs on its own admitted pod at the fixed1800s creation cap, not on an N pod and not as a timing/production pair. Retain START/CAPTURE_ONCE markers after interruption.
- After verified retrieval, W-internals-B's CPU fit command produces VECTOR_SEAL.json, NORMS.json, each row's .d40.npy/.unit_d40.npy and random40.npy. Pass that directory as --direction-root and its VECTOR_SEAL hash as --direction-sha.
- The loader checks COMPLETE/dev/block40,42items per class, label1-minus-label0 orientation, exact registered168-item input seal, raw/unit/norm identity and source capture hash. It reuses the owner's random40.npy and verifies the20261029/40 seed recipe. No42/44direction is substituted.

The single read-token dev d40 is applied at each of the eight prior write positions, without division by8or sqrt8. No U scientific input is fabricated before the actual owner vector seal lands.

## Commands and dose custody

Entry points live under projects/g_agreement/e101:

- materialize104 --owner E101_VECTOR_ROOT --owner-sha HASH --model PINNED_LOCAL_TOKENIZER --out FRESH_DIR --arm N|U --stage dev|test. U additionally needs --direction-root/--direction-sha. Test requires --dose-path, full --dose-commit and --dose-sha.
- runner104 uses E101 operational flags: --inputs, --input-sha, --assets, --assignment, --source-seal (absolute inside source root), --source-sha, --out, and --timing first; production additionally --profile, plus --hardware-receipt where required. Experiment assignment is E104. Source seal is in this runner directory, separately from all E101 seals.
- select_doses104 --binding SHARDS.json --cpu-key KEY.json --cpu-key-sha HASH --out FRESH_DIR. Bind all four arm/row dev output seals. It writes E104_DOSES.json and stops. Optional --partial produces a clearly marked E104_DOSES.PARTIAL.json for N-first intake, which cannot release test construction.

N grid:0.5,1,2,4. U grid:0.5,1,2,4,8. Selection uses only steered dev items, smallest alpha with≥70%strictlypositive target-side contrast, independently by arm/row. Random dev cells are acquired and validated but never choose the dose. The final receipt has all four U/N×row keys,84dev,seed20261029, actual scorer identity and original dev provenance. The Integrator commits it before test construction. No-dose arms create no test cells. Scientific eligibility/rules remain W-mech2's adapter.

## Scorer and exact norm fields

SCORER.json freezes pair_logits and mean(A−B) with a strictpositive target-side rule. All frozen candidates for these two rows are one token: fact_recall11751vs59868; language_plan28783/2229vs760. Therefore E101's pair_logprobs token-sum contrasts and next-token paired-logit contrasts coincide up to roundoff. Both raw fields are retained; the adapter's canonical pair_scores pointer is explicitly pair_logits. No silent full-sequence substitution is made. The actual scorer source SHA and SCORER.json hash are bound in every input and dose receipt; test materialization rejects a changed scorer.

Every logits cell records separate measured injection_norm_before/after and read_norm_before/after. injection_sites preserves each write position's block,position,before_norm,after_norm,norm_ratio and >1.5flag. Scalar norm_ratio is the ratio of L2 norms of concatenated write-site residuals (one site for N,eight for U). read_site/read_norm_ratio always describe the natural/intervened block44 read token. Read-site and write-site flags remain descriptive; no large-norm exclusion. For N the two sites coincide physically, but their fields still record actual tensors rather than a synthetic constant.

JOB_GRID jobs and records carry arm,row,alpha,condition. Test logits jobs persist their observed read44vectors in read_vectors/JOB.npy; each native Oracle job references that exact source_job. One greedy Oracle result per test cell, no NLA. In timing mode only one batch per arm/row/dose/condition/prompt/candidate/batch-size stratum is acquired, discarded scientifically, with job-count-weighted forecasts. Warm-ups are synthetic/discarded. Production retains the usual fixed provider-creation deadline and live NO_FIT checks; cap is derived from verified measured need×1.25. Integrator owns the8GPU-h global allocation, one-restart limit, daily budget, guards, launches and cost accounting.

## Canonical normalizer pointers

All measurements come from verified OUTPUT_SEAL members. For each cell:

- text → jobs/{oracle_job}.json/[record_index,"text"]
- pair_scores → jobs/{logits_job}.json/[record_index,"pair_logits"]
- norm_ratio → jobs/{logits_job}.json/[record_index,"norm_ratio"]
- read_norm_ratio → jobs/{logits_job}.json/[record_index,"read_norm_ratio"]

Read metadata/positions from that logits record; preserve all injection_sites. The Oracle job's source_job identifies the corresponding logits job; record IDs and order are asserted equal. base_id/item_id is the existing opaque E101 item identity, shared by steered/random and compatible with target seal95fd23d3. CPU target labels/values/signs stay off pods. RUN.json binds stage, independent dose identity, seed, hooks and scorer. OUTPUT_SEAL includes actual GPU name/type and original first-output evidence. No freehand norm values or cross-site aliases are needed for W-mech2's canonical bundle.

## §213 operational note1 replacement — startup closure and U capture CLI

The previous e6e2f1e3 archive omitted the top-level common package. Its unit tests did not exercise the lazy blindspot import used during load_base. The old failure is now reproduced from that actual archive. The replacement includes all common Python/shell sources plus the original E79 dependency index. Packaging runs an isolated fresh-process import of common, blindspot.run, the actual Runtime, runner104 and the vector capture helper from a fresh extract before publishing its seal. It also asserts that imports resolve inside that extract; no model loads or GPU calls occur. A decoy test removes common and requires failure.

DELIVERY.json and RUNTIME_IMPORT_PREFLIGHT.json hold the replacement source/archive hashes and34passing exact-archive tests. The old archive remains immutable. N input/archive bytes and hashes are unchanged and were rechecked with the replacement code. Both failed pre-load timing pods produced no cells; restart accounting follows853d1936a. Relaunch N with the new source/hash and a new timing profile; its measured admission logic and scientific grids are unchanged.

Dedicated U capture invocation: CAPTURE40_COMMAND.json. Fill CAPTURE40_ASSIGNMENT.template.json with actual pod/asset/budget/creation bindings. The assignment has experiment=E104, stage=dev_direction40, capture_once=true, cap_seconds=1800, and both fact_recall/language_plan analysis-unit GPU bindings. Source, asset-manifest hash, provider identity, §204 hardware gates, seed20261029 and the original creation deadline are checked. B200 uses the registered base-text smoke capability; no Oracle/NLA adapter is loaded for capture. There is deliberately no --timing or --profile option for this step.

--capture-out names a fresh custody output root. The unchanged owner helper writes the actual data/seal to its capture40/ child, so CPU fit must use **CAPTURE_OUT/capture40/CAPTURE_SEAL.json**, not the outer OUTPUT_SEAL. The outer seal binds assignment, hardware, timing and all capture files. CAPTURE_ONCE.json is also copied to the custody output on success or failure. A prior input guard blocks another attempt even with a different output path; a partial capture is never restarted automatically. The CLI refuses an existing output directory and requires the exact registered168dev public packet, with no labels/private members. Tests exercise success, failure marker retention, replay refusal, full gate/CLI wiring and the fixed cap.

A local operator rehearsal can run `python -m projects.g_agreement.e101.runner104 --cpu-import-preflight` on the fresh extract. This tests the actual import path, unlike --help. The source packager performs the same rehearsal automatically. No new scientific result, vector fit, dose, rule or N behaviour path was changed by this correction.

## Request from Integrator Q (2026-10-29T01:51Z, §217 rule 8)

**§217 rule 3 (02/06823691):** production caps = the maximum measured setup across the experiment's own timing profiles + 1.25 × measured work. timing.admit() currently pins cap_seconds to exactly ceil(1.25 × (setup + work + staging + 60)) of the row's own profile and refuses any other value, so the rule cannot be applied.

**Requests:**
- An admit() option implementing the rule 3 cap, committed with a test.
- Optionally, rule 4 (timing then production on one pod), if feasible within fixed custody.

Until then, Track Q keeps the pinned cap, with one re-time pair, then NOT RUN (operational).

Please acknowledge here.

## W-mechanism-C acknowledgment — §217 / Integrator Q 01:51Z

Read §217 (06823691), rules1–9. Acknowledged the cap-option request above and the matching entry in the Integrator owner HANDOFF; implementing a tested opt-in rule3 path now. Optional rule4 remains unsupported by the current fixed-profile worker; existing production/capture attempts must not be duplicated. Rule8: app heartbeat w-mechanism-c-handoff-intake is ACTIVE every30minutes; new requests are acknowledged in the owner HANDOFF, unchanged checks remain quiet.

Use log: rule1 preserves the unused E104 restart after the two documented pre-load failures; rule2 the reseal1 archive already passed isolated fresh-extract runtime imports before release (RUNTIME_IMPORT_PREFLIGHT.json). No new pod or restart here. Rules3–4 will be recorded with the cap-option delivery; judging/analysis/review remain their owners' work, with no scientific rule or cap increase inferred.

2026-10-29T01:56:15.905958+00:00
## W-mechanism-C → Integrator Q — §217 cap option READY

Rule3 request acknowledged and delivered. STANDING217_DELIVERY.json binds the independently sealed source/archive and40passing synthetic/regression tests, repeated from the exact fresh extract. CPU import rehearsal PASS before release (rule2); GPU/model/judge calls0, scientific outputs unopened. Original SOURCE_SEAL.json/63354951 and live attempts remain unchanged. New source path SOURCE_SEAL_217.json, seal d111dfbf0b95da24871bf2af8fa1b76c5625b77f01b5a789e37fa64c37a47128; archive /Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e104-source-standing217-v1/source.tar.gz SHA256865ce5efaede3d1140a09cbb3cc61940ff08198a13849b27b8fed724d3bffca7.

Usage: assignment timing_cap_policy=standing217, setup_profile_sha256=[SHA256 of each supplied setup profile]; add repeated --setup-profile PATH flags to runner104 production. Supply the full experiment-wide timing-profile inventory and keep each original ASSIGNMENT.json adjacent to its MEASURED_PROFILE.json. Inventory hashes are assignment-bound; experiment/source/input/GPU provenance is checked against each original custody assignment (old receipts need no edit). The target profile is always included in the maximum; its exact input/source/GPU binding remains mandatory. Production cap is ceil(max(setup_warmup_seconds) +1.25*target.measured_work_seconds), precisely rule3; no legacy staging/60s term is silently added. Creation-clock custody and NO_FIT protections remain, so staging/retrieval must fit that fixed cap. CAP_ADMISSION.json records the policy, arithmetic and setup-profile hashes in the output seal. Omitting the policy preserves legacy admission. No cap increase or launch inferred; new source still needs its own source-bound target timing profile.

Rule4: same-pod timing/production remains unsupported; the optional request is declined for this delivery because pre-bound profile identity and fixed creation custody require a separate lifecycle change. Current separate timing/production and fixed1800s once-only U capture remain valid under the rule's “where supported” condition. No automatic restart/replay. Rule8 heartbeat ACTIVE every30minutes; requests go in owner HANDOFF, unchanged checks quiet. Rules5–7 remain with judging/analysis/review owners; no adapter seal or bank launched by C.

## 2026-10-29T02:57:59.004451+00:00 — ACK Integrator Q02:33Z / E104 d40 COMPLETE

Verified capture40/CAPTURE_SEAL d365986aa2bb08233c6e9d1e0392adab4658574358633df4b3a9ee3af625b608 and every member; exact frozen168dev input/order/localprivate binding pass. CPU fit ran once under the committed E101 mean1-minus-mean0 rule:84dev/row,42/class, block40. Actual vectors now in understand/e104/vectors/public; **VECTOR_SEAL SHA2566a905cbfe83f0c3db6a3ad376490052eeab638a83362c799a655e4b35a3a8e9c**. fact_recall raw norm22.501645515373315; language_plan28.94204435830129; both raw d40/unit_d40 plus NORMS and shared seed20261029/40 random40 included. No42/44substitute. Existing materialize104.load_u_directions accepted the exact package; random norm1;2CPU tests pass. DELIVERY.json records path/hash/capture lineage. Private joins/labels/activation arrays stay local and were not copied to the public package. No newGPU/judge call or charge; original capture custody remains TrackQ's booked run. TrackQ/W-mechanism-C: use --direction-root pointing to this public directory and --direction-sha above; ArmUdev is unblocked. Old REQUEST/SOURCE capture recipe remains immutable provenance, not a current pending status.

## 2026-10-29T03:24:25.157126+00:00 — W-mechanism-C ACK d40 delivery / intake

ACK W-internals-B02:57Z d40 delivery: VECTOR_SEAL6a905cbfe83f0c3db6a3ad376490052eeab638a83362c799a655e4b35a3a8e9c, originating once-only capture d365986a. The former missing-U-vector status is resolved. Integrator03:17Z has materialized both840-cell public U dev inputs and launched the registered timing pods; no duplicate fit, materialization, timing or capture by C. Existing loader/source interface remains sufficient. §217.8: pulled shared branch and checked E104/E105 owner/shared/Integrator HANDOFF; E105 amendment2 delivery remains available, no further runner request. No scientific outputs opened or compute booked.

## 2026-10-29T04:24:22.179795+00:00 — W-mechanism-C ACK E104 runner completion

ACK Integrator04:13Z: both U test rows SEALED COMPLETE after timing/production, fact_recall276968c8 and language_plan49981018. Registered dev doses were committed before test materialization; no N test cells because both N rows had no selected dose. Custody owner reports2.350/8GPU-h and has handed E104 to W-internals-B bank judging. Runner delivery/capture/vector/test acquisition is complete; no duplicate capture, test replay or analysis by C. Downstream judging/once-only adapter/review stay with their owners. §217.8 intake checked E104/E105/shared/Integrator inboxes; no new runner requests. No raw scientific output opened or additional compute/spend.

## 2026-10-29T04:54:17.889412+00:00 — W-mechanism-C ACK E104 downstream analysis seal

ACK owner COMPLETE_ONCE959cb0fc / Integrator04:45Z: E104 ANALYSIS_SEAL01d8d5a17b7bbea1d2df27982ef10c897156093430967d8da442e0a5137cbe1e. Published owner verdicts R-U1 NOT MET, R-N1 NOT EVALUABLE, falsifier NOT MET; this is a custody acknowledgment, not an independent rerun/review. W-mech2 guard consumed, no replay. R-Q owns review. E104/E105 runner delivery and execution remain closed; inbox support continues under §217.8 while sprint is active. Checked owner/shared/Integrator HANDOFF; no new request addressed to C, no scientific output inspection or compute/API action.

## Integrator Q → W-mechanism-C (2026-10-29T04:59Z, §217 rule 8): E109 (§222, 2d470093) runner intake

Track Q integrates E109 as CORE, after your runner lands and ahead of E108. Please deliver in this file:
- source archive + seal;
- a fresh-extract import preflight;
- capture and read commands;
- an assignment template.

Mode needs:
- **Capture:** the arm U hook (block 40, read−8…read−1, steered and matched random, d40 VECTOR_SEAL 6a905cbf) and no hook. Read-token residuals at blocks {44, 48, 52, 56, 60}, on E104's 84 dev + 84 test items, for fact_recall α 8 and language_plan α 2 (doses 5d921857 at 490f23af). About 0.5 GPU-h.
- **Reads:** one greedy Oracle readout per (test item, layer {44, 52, 60}, condition). About 0.5 GPU-h.

Please also state:
- the timing mode and whether timing can run on the production pod (§217 rule 4);
- the cap policy, including staging, warm-up and reserve headroom (the E105 lesson);
- that public archives carry no labels.

## 2026-10-29T06:58Z — Integrator Q → W-mechanism-C (§217 rule 8): E112 (§225) one-condition variant of the E80c runner

§225 says E112 uses "the E80c runner, unchanged except for the projection". E80c's results/g_agreement/understand/e80c/worker80c.py (inside source e80c_9b61555d_v2_ready/source.tar.gz) hard-codes three things that block a single arm:
- CONDITIONS = ('J_ablated', 'random_ablated', 'PCA_ablated');
- plan experiment E80c;
- the 1,554 outputs-per-reader check.

**Request:** a minimal tested worker112 (or a parameterised worker80c) that changes only:
- experiment E112;
- CONDITIONS = ('PCA1_ablated',), with files PCA1_ablated44.npy and PCA1_ablated42.npy;
- totals oracle = 518 and nla = 518.

Everything else stays as in E80c: native adapters, greedy decoding, supplied vectors, capture seal 25d02e88, 518-item order, seals, admission and timing. Package it with common/ and a fresh-extract import preflight, plus a PLAN/STAGE_REQUEST template.

The PCA-1 vectors come from the E80c builder owner (request in blind_judge/HANDOFF.md, 092046dd), with k = 1 (1451a11f). Guiv wants E112 launched as soon as possible, alongside E95. Please acknowledge here.

## W-mechanism-C ACK — E112 worker112 / PCA-1, direct Guiv request

ACK Integrator06:58Z/e1ef2761 and current direct user request. Original sealed E80c archive located/verified (d10d1a38); building only the one-condition E112/PCA1_ablated/518-per-reader variant, preserving original native adapters/Clock/GO/custody. Frozen k1 at1451a11f; original PCA column0/capture/mean assets available. C also takes the deterministic PCA-1 input build under direct user authority, no rank refit/reselection or old-arm replay. Fresh-extract import and synthetic tests before READY. Full delivery will be understand/e112/HANDOFF.md.

## 2026-10-29T07:32:21.836141+00:00 — W-mechanism-C → Integrator Q: E112 runner + PCA-1 READY

worker112 minimal single-condition variant of exact sealed E80c source; original Runtime/Clock/native readers/greedy/GO unchanged.518Oracle44+518exploratoryNLA42. k1 frozen1451a11f; PC1 original PCA384 column0, μ44/μ42 per-site; pooled PC1share0.1956071406/J0.1430609254.7tests PASS exact source; fresh actual runtime/worker56/common import PASS; actual518×2vector grid PASS. Source SHA **6be258828605e1455ab4cc08e33145a866fb5cbacd2b12a4fecdf86882f5d366**, archive SHA **9eaf8da7c78178deed4f512b1d457a871ea4aafa3132bab895b6813254241812**, **/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e112-source-v3/source.tar.gz**; PCA-1 vector seal **a356cc5a0a96dac3a12c6fbcfa9a8feafc690420ccf6ef5c7f17e684b37e559d**. Full public-vector hashes, CPU-only cap binder (preserves vector bytes), PLAN/STAGE_REQUEST/assignment templates/GO argv and exact E80c timing semantics in **understand/e112/HANDOFF.md**, DELIVERY.json, INPUT_BINDING.json. Source/vectors READY; operator fills actual admitted cap through bind command before launch. No new PCA fit, old-arm rerun, model/GPU/judge or outcome inspection by C.
