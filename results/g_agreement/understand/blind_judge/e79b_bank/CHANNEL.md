# E79_ARM_B — reader half only, separate lifetime USD3

Original W-mech2 packet blinde60c7792/CPUjoin9b1781ad/SPECa4c1b983/capfa1911a1,
672records, no packet rebuild, Arm A or frozen behaviour rescore. Route is existing
E56 OpenRouter/google/gemini-3.1-flash-lite/google-vertex/global, ZDR/data deny,
provider pinned/no fallback. Original rubric/render/batch4/max4096 unchanged.

Isolated E104 transport copy and original §217c2 retry wrapper, original modules
unchanged.24synthetic testsPASS. Source/dependency/manifest Git-byte checks before
prepare/run. Prepare is CPU-only; no ledger/API writes. All672 decoded wires pass
privacy guard, zero redacted source records on current packet. First-pass max-output
reservation bound USD2.2415300000, cap3; actual plus next reservation enforced by
original Ledger. No automatic cap reset/rebooking. Schema retries0/1/2, charged
length terminalmissing; zero-cost pinned provider errors at most2 separately
reserved retries/backoff30/60 via original scopedwrapper pattern. Other unknown/
charged failures stop; any402 shared pause; unknown charges never guessed away.

Canonical B cache funded_queue/E79_ARM_B, ledger there, serialized dispatch lock,
shared FIFO pace/credit pause with all banks. Terminal missing stays flat
UNPARSEABLE/null contribution, not zero. Validate evidence against original source;
if a judge-copy quote cannot validate on original text, retain it diagnostically
and emit terminalmissing rather than repair it. Current packet needs no redactions.

Key-held Integrator execution (no key printing/copying/commit):
1. In B checkout run `python -m projects.g_agreement.understand.blind_judge.e79b_judging prepare`.
2. Post fresh (<300s) GLOBAL_ADMISSION.json in canonical bank cache with bank
E79_ARM_B, cap_usd3, bank_admission_sha256, verified_by_integrator:true,
allocation_included:true, unknown_reservations_retained:true, created_epoch,
actual_plus_open_caps_usd (including separate3 exactly once, <=1000), issuer.
Existing bank/unknown holds must be retained; do not create a duplicate allocation.
3. With the existing Integrator-held credential only in process environment, run
`python -m projects.g_agreement.understand.blind_judge.e79b_judging run`.
The driver authenticates actual route/provider privacy before inference and logs
truthful audit fields. Static preflight is not an authenticated route seal.

Run writes source-bound JUDGMENT_SEAL with actual_USD/unknown_charges0,
cap_binding_sha256/originalblind/source/admission/privacy/route/audits. Scoped
provider-error audit finalized before copying exact bank to original owner
arm_b/judge; never overwrite existing terminal bank. The original owner R-C2
adapter/onceguard is separate and consumes this bank; no scientific analysis here.
Secret scan and original-source hash checks before publication. No private join
or raw readout content goes to Git; keys stay with Integrator.


§236 amendment4 (8ba4ecaca): paid calls end Friday30Oct16:00CET/15:00Z,
including transport/schema retries and paced sends. deadline236 also checks at
the physical POST boundary. Registered E79B cap3/route/custody unchanged. Actual
runtime had no START/ledger when source was revised. Fresh GLOBAL_ADMISSION must
add higher_priority_banks_cleared:true for E127/E121/E117/E117c/E120c/E118b/E124;
E79B then precedes E95. Old source/admission receipt is historical, not runnable
under the new source pin: rerun CPU prepare after source commit before launch.
