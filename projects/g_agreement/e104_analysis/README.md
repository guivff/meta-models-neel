# E104 pre-output once-only adapter (§213, 5e075c6a)

Extends f6ba5964f's E101 estimands and paired steered-flipped cohort. It does not
change E101 or replay E101 outputs. CPU only, E56 judging route owned by W-internals-B.

Commands after source commit:
python3 -m projects.g_agreement.e104_analysis.adapter export --spec SPEC.json
python3 -m projects.g_agreement.e104_analysis.adapter analyze --spec SPEC.json

SPEC: dose_path (repo-local E104_DOSES.json), full40hex dose_commit, dose_sha256,
input_seal, input_sha256, blind, private, judgments, analysis. Neither the private
join nor labels may be staged on GPU or published. Fixed experiment-global once
guard prevents replay. Export never judges. Analysis requires original blind digest,
route and privacy receipt and complete opaque-code inventory. Thin private joins
may omit raw behaviour/norms; every overlapping field is checked and those fields
are rejoined solely from the verified acquisition bundle.

The committed dose receipt must contain experiment=E104, dev_count=84,
seed=20261029, selected_doses keyed U:fact_recall, U:language_plan,
N:fact_recall, N:language_plan. Each has alpha (null if none) and target_side_counts
keyed "0.5","1.0","2.0","4.0", plus "8.0" for U only. Counts are integers0–84.
The adapter independently checks the smallest dose reaching70%. No-dose cells
must have no test outputs. All eligible cells require84 paired test items.

The CPU INPUT seal includes experiment=E104, COMPLETE status, labels_cpu_only=true,
dose_sha256, random_seed=20261029, reader=oracle, read_block=44,
U_hook={block:40,positions:eight_before_read,read_token_untouched:true},
N_hook={block:44,positions:read_token,renormalized:true,random_renormalized:true},
source_seals=[{seal,sha256}], and files binding RECORDS.json. This is a canonical
sealed normalizer interface; no unsealed/freehand measured values are accepted.

RECORDS.json metadata per native readout: unique id, item_id, arm U/N, row
fact_recall/language_plan, reader oracle, split test, alpha, condition steered/random,
property, values {A,B}, target, contrast_target_sign ±1, frozen
behaviour_scorer_sha256, candidate_count. Targets are the other frozen value.
measurements must map text, pair_scores, norm_ratio, read_norm_ratio to exact
{seal_index,member,keys} source references. Each keys array traverses the sealed
JSON to the actual field. Pair scores are the frozen scorer's A/B scores, averaged
across its original pairs; sign0 is not flipped. The normalizer must preserve the
registered next-token scorer and candidate orientation, not silently substitute a
full-sequence scorer. Norm ratio refers to the injection site's norm convention;
read_norm_ratio describes the natural versus intervened block44 read vector.
For U, preserve the runner's documented per-item injection norm convention and
all per-position norm observations in its sealed source; do not infer a scalar
from another site. No large-norm observation is excluded or used to tune a dose.

B and random B, steered/random S on the SAME steered-flipped cohort, paired Δ,
both all-item S, per-item norms, >1.5 flags, exact cohort counts and actual missing
judgment counts are reported. Statistics use common/stats.py bootstrap_ci on
jointly sampled original item indices:2000 draws, seed20261028 (E101+1).
Missing judgments use separate parseable denominators, as E101. Undefined CIs
remain unknown. No complete-case substitution, no mask-based zero imputation.

R-U1/R-N1: Δ>=.30 and lower95%>0 on at least one eligible row in the arm.
An arm with no eligible dose is NOT EVALUABLE. Falsifier: Δ<=.10 and upper95%<.30
on EVERY eligible cell across both arms. At least one eligible cell is required;
with zero eligible cells it is NOT EVALUABLE, never vacuously MET. The output
retains eligible counts so an absent arm is never mistaken for evidence against it.
Only a MET falsifier emits the registered injected-write-at-large-norm wording.
Everything besides those registered rule checks is descriptive.
