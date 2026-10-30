# E85 once-only adapter — §199 E85 (§198–§199 programme)

Run `python3 -m projects.g_agreement.e85_analysis.adapter --spec SPEC.json` once,
after source/tests are committed and the relaunch's complete judgment bank seals.
No E85 output was opened in preparing the adapter. CPU only; no new judging,
probe fitting or generation. Fixed guard: original wt-wmech custody root,
cache/g_agreement/understand/e85/ANALYSIS_ONCE.json. Never reset or replay it.

Scientific contract: 100 test matched quartets (400 items), 50 dev quartets.
For each reader, primary(a) eval-mention rates by genre×addressed with Wilson95
and bootstrap95. Marginal genre effect = (p10+p11−p00−p01)/2; addressed effect =
(p01+p11−p00−p10)/2; R-E1 compares their difference. Bootstrap entire matched
quartets, 5000 draws seed0 (common.stats defaults), sharing the index for all four
cells. Missing judgments keep separate cell masks and are not zero. No undefined
bootstrap draw is discarded. Report counts and undefined CIs explicitly.

Oracle44 R-E1: addressed test probe AUROC>=.90, genre>=.20, genre−addressed>=.15,
and difference lower95>0. NLA42 reported identically, descriptive. A failed/missing
addressed probe makes the scientific rule and falsifier NOT EVALUABLE; observed
addressed>=genre is still shown separately. Falsifier, when gated, is addressed
>=genre (inclusive). No extra dev-AUROC gate and no BOW gate. Both probe factors
at42/44 and BOW scores are preserved. Codes(b) evaluation vocabulary and(c) absent
genre are separate descriptive tables and never enter R-E1. judge205 schema and
verbatim evidence checked. Original S6 rubric on the seeded25% sample is compared
with current(a) on the identical selected IDs; unselected masks are identified
separately from failed original judgments. No result-based subset selection.

SPEC fields: private, output_seal, output_sha256, analysis. `private` resolves
original LABELS.PRIVATE.json matching CPU_CONFIG.json's frozen hash; all600 IDs,
factors, matched_set and split are checked. It remains local CPU-side.

Output seal: experiment E85, status COMPLETE, input_seal_sha256/private_sha256
matching frozen CPU_CONFIG; route_verified and redaction_audit_complete true;
judge205_sha256; original_rubric_comparison_verified true; original_subsample_ids
must exactly equal rubric202.py's SHA256-ranked seeded25% of all800 opaque IDs;
source_seals=[{seal,sha256}]. Every original source seal and member hash is checked.
MEASUREMENTS.json contains exactly800 {id:opaqueID,item_id:publicID,reader:oracle/nla,
fields:{text,code,original_code only if selected}}. Each field is an exact pointer
{seal_index,member,keys} into the unchanged original source JSON. Primary code is
judge205's object or null for terminal UNPARSEABLE; original code is S6's
{id,eval_mention,evidence} or null. The owner must bind the existing channel's
terminal sentinels to null explicitly; this adapter does not guess normalizations.

DIAGNOSTICS.json supplies source pointers named probes,bow,behaviour. Probes are
unchanged PROBES.json records for genre/addressed at42/44, status COMPLETE or
NOT EVALUABLE. BOW has genre/addressed test_auroc; only numeric aggregate scores
are published. Behaviour may be null if unavailable; otherwise aggregate counts
{pairs:200,different,missing,comparison:"exact_answer_text"} compare downstream
answers across addressed within each matched_set×genre. No answer texts enter
results. Exact judgments, private joins and source text remain CPU-local.
The watcher must bind the relaunch's retained source seal, not discarded pilot
outputs, and verify the original scientific-source receipt before invocation.
