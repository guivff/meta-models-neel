# E111 §224 / clarification1 once-only CPU adapter

Registration2768a60aa, magnitude clarificationbb43088d1. Commit before E109 seal;
no E111 inputs opened while developing. Command after eligible complete binding:
`wt-wcensus/.venv/bin/python -m projects.g_agreement.e111_analysis.adapter --spec SPEC.json`
Use absolute CPU interpreter path from workspace. No GPU, model calls or judging.
Fixed exclusive guard: wt-wmech/cache/g_agreement/understand/e111/ANALYSIS_ONCE.json.
Never retry a consumed guard. Historical experiment analyses are never replayed.

Admission: all E104_U, E101, E100_a and E109_44 when E109 seals; without E109 only
at/after Fri30Oct2026 00:00 Europe/Zurich (Thu29Oct23:00UTC), explicitly excluded.
Do not omit another experiment or choose scope from outcomes. Census includes all
sealed steered/transplanted test observations and matched controls with available
block44 vectors. Unavailable vectors have counted, sourced exclusions. Judgments
UNPARSEABLE are dropped from regression and counted per experiment, never zero.

Outcome y=1 iff Oracle states target value, including BOTH-valued judgments.
x1=(target-oriented probe weight) dot (intervened44-natural44); intercept cancels.
x2 is the original sealed behavioural flip for that cell, never recomputed from
probe scores. No new target selection or E104 flipped-only restriction.
Probe per row: W-lens supplies frozen unhooked-dev-fit coefficients, E109 where
available else original E49/E56/E57/E59 probe. Original class orientation, recipe,
train IDs/labels/order and source hashes required; no test fitting or outcome-based
probe selection. Probe fit is separate from the logistic outcome model.
E104_U/E109 use persisted read44 vectors, E100_a donor residual, E101 reconstructed
from original natural carrier + alpha*raw_norm*sigma*unit (or original random unit
for matched random cell), float64 sum then float32 as original materialize.py;
all parameters original sealed CPU pointers. Reconstruction is labelled.

## Frozen statistics

Unpenalized logistic MLE: intercept, x1, x2, row fixed effects (sorted reference
row, no experiment fixed effects). Predictors scaled internally for conditioning;
reported coefficients are original units. No penalty, feature selection or tuning.
Singular design, one-class outcome, nonfinite/diverging MLE or nonconvergence are
NOT EVALUABLE, not silently regularized. Numerical diagnostics are explicit.

Item bootstrap2000 seed20261029: sample unique source-item clusters with replacement,
retaining all observations/controls and cross-experiment appearances of each item.
Owner must provide canonical cross-experiment source identity; do not namespace
identical underlying items into independent experiments. Row dummies stay fixed.
Failed replicates are counted; ANY failed replicate makes coefficient CIs/rules
NOT EVALUABLE, rather than silently dropping failures. No retry/bootstrap reseed.
Percentile95% CIs. SDs use pooled kept observation sample, ddof0; they remain fixed
through the pooled bootstrap. Descriptive per-experiment models use their own sample.

R-SL1: beta1>0 and lower1>0 AND (CI2 includes0 OR
abs(beta1*SD1)>=2*abs(beta2*SD2)). Clarification1 compares magnitudes, never signs.
Falsifier: beta2>0 and lower2>0 AND CI1 includes0. R-SL2: same model per experiment,
raw x1-alone and x2-alone AUROCs (ties averaged, one-class undefined), quintile-binned
scatter coloured by x2, pooled and per-experiment. Quantile ties collapse bins;
bin counts are reported. No E104/E109 rule or bootstrap is rerun.

## Required exact CPU source binding (Track Q / W-lens / W-internals-C)

SPEC: inventory_seal, inventory_sha256, inventory_commit(full40hex), binding_seal,
binding_sha256, e109_sealed bool, e109_seal/e109_sha256 when true, analysis path.
Inventory must be committed before invocation; scientific source commit must
precede actual E109 seal (owner ordering receipt independently verified by watcher).
Inventory seal experimentE111,scope§224,included_experiments, hashes INVENTORY.json
and PROBES.json; adapter_committed_before_e109_seal true when applicable.

INVENTORY.json: {id,experiment:E104_U/E109_44/E101/E100_a,row,source_item_id,
cluster_id,paired_control_id,split:test,reader:oracle,block:44,judgment_id,
vector_mode:persisted/donor/E101_reconstructed/natural,
disposition:INCLUDED/VECTOR_UNAVAILABLE,reason(for unavailable)} per observation.
Full original cells, source-item mapping, available-vector census and all exclusions
must be independently verified by owner, including control matching/target lineage.
E100 scope is part a only; E104 scope is U only, E109 block44 only.
PROBES.json row -> {block:44,fit_split:unhooked_dev,test_used_for_fit:false,
positive_class:1,origin:E109/E49/E56/E57/E59,e109_probe_available:boolean,
dev_ids,recipe_sha256,labels_order_sha256,training_source_sha256,coefficients:ref,preprocessing:none/standardized,
feature_scale:ref(required for standardized)}.
Original positive-class/target semantic mapping must be CPU verified by W-lens.

Binding seal experimentE111,statusCOMPLETE,inventory_sha256; true flags
source_census_complete,private_join_verified,route_verified,privacy_verified,
labels_cpu_only. source_seals[{seal,sha256}] bind original capture/donor/direction/
probe/behaviour/judgment/route/privacy and normalization receipts, not invented
scores. Hashes MEASUREMENTS.json: exactly included IDs, each with natural:ref,
vector_parameters (ref values: vector for persisted/donor; unit/alpha/raw_norm/sigma
for reconstructed; empty natural), target_class:ref(0/1 in original probe class),
target_letter:ref(A/B in original judge packet), behaviour_flip:ref,
text:ref,code:ref(null or original E56 object). ref={seal_index,member,keys}.
Original JSON, .npy or .npz arrays only, allow_pickle=False. All private labels/joins
remain CPU local; public output aggregates only, plus input hashes/paths.

W-lens: supply these frozen probe and reconstruction-lineage bindings to W-mech2
owner HANDOFF. Track Q: complete original-source census and E109 terminal seal.
R-Q reviews result on arrival. Missing exact binding means WAIT, no guessed join,
partial experiment analysis or deadline-driven fabrication.

W-lens source delivery67b7be74a: saved fallback probes use z=((h-mu)/sd)@w+b.
Adapter resolves original w and sd and computes w/sd; neither mu nor intercept
changes the paired shift. Unscaled E109 uses w directly. No unit normalization,
sigmoid or raw-w substitution. Selection stays per row as §224 registers: E109
when available, otherwise source-matched fallback, frozen before the once claim.

## §226 clarification2: R-SL0 in the same once-only run

Before regression, compute the direct signed-report contrast on fact_recall and language_plan: E101(steered−random) minus E104_U(steered−random), restricted to original shared test items whose steered behaviour flipped in both. Joint paired item bootstrap2000/seed20261029, same E111 seed. ≥.20 with lowerCI>0 on at least one row meets R-SL0. No extra guard or earlier execution. Produces R_SL0 in RESULTS and SITE_VS_CARRIED.png headline figure alongside regression. Original R-SL1/R-SL2 functions unchanged. Missing scores keep per-cell denominators; undefined bootstrap draws invalidate CI, never become silence.

Binding seal now MUST include CONTRAST.json, independent of regression vector availability: full168 shared records,84 per row, including non-flipped items. Each has row, item_id, site_source_item_id, carried_source_item_id (exact same original item), site_flip/carried_flip sealed original E101/E104 steered-behaviour pointers, site_target_value/carried_target_value pointers (must agree), and cells site_steered/site_random/carried_steered/carried_random. Each cell supplies experiment E101 or E104_U, original code/text/target_letter pointers and judgment_id. This reuses sealed codes with original signed E56 scoring, not regression binary target-statement y. Bind original cell conditions, same source target orientation and full shared item census before invocation; do not infer joins from matching display names. No rerun of E101/E104 or regression to obtain this contrast.

## §224 deviation1, note 281761226

E100a is excluded immediately: part a was reader-only, with no measured behaviour or matched per-item controls (§208). No deadline wait or substitute from part b/E105. Inventory included_experiments and measurement census must contain E104_U, E109_44, E101 only (existing E109 deadline rule otherwise unchanged). Output census and E100a descriptive entry explicitly report: "E100a excluded: matched controls and behaviour flips not in sealed records". Original regression, contrast, bootstrap, seeds and all rule thresholds are unchanged. Source update is after original acquisitions/E109 analysis but before E111 guard/output, authorized by deviation1; do not claim it preceded E109 acquisition. W-lens source lineage and complete verified binding still required.

## §224 deviation1 correction b130c7679 (supersedes immediate exclusion)

E100a is included through registered E105 donor pairing: y original E100a Oracle judgment; x1 target-oriented dev-probe logit at h_donor minus h; x2 original E105 T flip against own baseline sign. Matched unpatched control uses original native Oracle scored for same donor value and E105 condition0, x1=x2=0. Exact sealed item/donor/control identities, target orientation and E105 flip source are mandatory; no part-b/E105 readout substitution. SPEC.e100_inputs must explicitly bind flip_seal_available/probe_lineage_available booleans backed by original source seals/owner verification. Both true requires full E100a census. Either missing permits exclusion only at/after 2026-10-29 11:45 UTC (12:45 CET), with missing-input reason in results. Deadline does not permit missing other inputs. W-lens full lineage b1d87a40 delivered; TrackQ owns E105 T/0 flip seal. Earlier exclusion-only SPEC8bae099d is superseded and must not execute before cutoff. All statistical functions, rules, seeds and R-SL0 unchanged.

Direct user clarification 2026-10-29: exclude E100a entirely and run now. SPEC.exclude_e100_by_user=true admits exactly E104_U/E109_44/E101 immediately (E109 sealed), superseding the E100 deadline. Explicit user exclusion is reported; all other binding/verification/once requirements and statistics remain unchanged.

For Track Q final verified SPEC b24a0c6c, pass --exclude-e100-by-user to apply direct user f892e0466 without changing any sealed source/census/measurement hashes. Saved local BINDING records original_spec_sha256 and the explicit exclusion flag.
