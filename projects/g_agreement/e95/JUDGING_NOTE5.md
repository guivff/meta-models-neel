# E95 registered judging — operational note5

Reuses the existing E95 judge_admission/judge_dispatch, E87 wire/rubrics exactly,
and validator221.e87_classify (only silent first_position corrected). One call per
selected item/layer, ordered positions retained for first mention; placebo included.
Frozen step3 ROW_INVENTORY/JUDGE_INDEX: 30% original selection, nested25% original
rubric comparison. Intersect fixed selected IDs with statement-score eligibility,
CPU regex unresolved IDs and WHOLE reader stages. Do not resample/reselect.
Original eligibility ruling remains hash-bound to original80-row inventory; step3
row identity is checked against it, not relabelled as a new post-output ruling.

Final closed TrackQ inventory be185a543 / file95c3e0f1:7Oracle stages62newrows,
5NLA stages44newrows.3-0excluded, partialNLA3-1/3-6excluded even if realNLAcomplete.
Both real/placebo must be complete. OriginalE87 reuse is a separate frozen lineage;
no baseline/reader/GPU replay. Missing/refusal/invalid/chargedlength remainmissing.

Before output opening/execution, SOURCE_SEAL must contain all ADAPTER_FILES plus
source tests/docs; verify_adapter checks committed Git bytes BEFORE packet reads.
No parser change beyond existing validator221. Physical POST cutoff Friday30Oct
15:00UTC/16:00CET (§236 amendment4), also after pacing delays; real402 shared pause,
unknown charges retained through original Ledger reserve/settle only. Per-bank60,
global actual+open+retainedunknown<=1000; source/global custody never reset.

SPEC existing keys inventory/index/eligibility/regex_audit/custody_receipt/
budget_receipt plus hashes, packet/PACKET_SEAL, route/route_sha256, source_seal/
source_seal_sha256, ledger_root with basename e95_60usd, out, first_pass_worst_case_usd.
New stage_inventory/stage_inventory_sha256 must point EXACT closed inventory;
stage_sources maps each7eligible shard to original manifest, stage_seal, output_seal.
Manifest/output/stage hashes must match final inventory, every stage member verified.
PACKET_SEAL adds stage_inventory_sha256. Original GROUPED_PACKET/ORIGINAL_IDS/
RUBRIC and original CPU source-pointer/regex custody stay local. No private joins
or readout contents in public receipts. New source pointers must retain raw originals;
no inferred labels, fabricated scalar codes or missing-as-zero.

Budget receipt remains Integrator verified/reconciled/reservation_included with
E95_allocation_usd<=60 and global_judging_committed_including_reservation_usd<=1000.
Paid run additionally needs fresh issued_epoch<=300seconds and
higher_priority_banks_cleared:true. Required order: E127 ifneeded,E121remaining,
E117/E117c,E120c,E118b,E124,E79B,THEN E95. These are dispatch/admission facts;
no new run/cap allocation is authorized by channel preparation.

Offline preflight (no key/API/ledger writes):
python -m projects.g_agreement.e95.judge_dispatch --spec LOCAL_SPEC.json
Integrator key-held execution after fresh accounting/priority clearance:
python -m projects.g_agreement.e95.judge_dispatch --spec LOCAL_SPEC.json --run
Existing key only in Integrator process environment; never relay/read/print it.
No Bduplicate workers or automatic resume of unknown/interrupted requests.

W-lens owns map analysis: commit/test original E95 oracle_only.py extension before
opening judgments, then run once on exact sealed codes/source joins. R-Q reviews.
Analysis/review seal Fri18CET; otherwise appendix 'acquired, not analysed'.
