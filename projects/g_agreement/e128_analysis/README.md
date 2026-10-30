# E128 §236 — smallest behaviour-flipping dose

Shares original E104/E109 rubric/category validation and Wilson95 implementation
with E127; separate once guard, source pins and results. No model/judge calls.
Bank E128<=USD3, sole C dispatcher, reviewer R-Q. Source/tests must be committed
before any E128 output opening. Common transport schema is documented in E127.

All84 original fact_recall test items at doses2,4 and unchanged sealed8, each
steered/random and Oracle44/52. Preserve original hook40/eight preceding positions
and class-mean direction. For each new dose, behaviour flips come from its frozen
CPU generated-answer classifier; dose8 flags come directly from original E104
private495bbb19. Never select a dose from Oracle rates, CIs, judged values or norms.

alpha_min is smallest2/4/8 with at least42 known behaviour flips. If an earlier
dose has enough missing behaviour to make this selection ambiguous, mark NOT
EVALUABLE rather than silently choose a higher dose. At selected2 or4, on its
OWN steered-flipped items: old44>=.50 with Wilson lower strictly>.35 AND
new52>=.70 gives descriptive R-DOSE1 MET. No added CI threshold for new52. If only8
qualifies, keep R-DOSE1 NOT EVALUABLE/dose question open and the strong-steer caveat,
even if its descriptive reader pattern meets the numerical thresholds. If no dose
qualifies, report no qualifying flips. Per-dose patterns/rates remain descriptive.

Random direction at each dose is reported alongside on the SAME steered-flipped
cohort, plus its own behaviour flip count; it never selects the dose/cohort and
adds no new R-DOSE1 threshold. C/runner must confirm the exact registered control
readout roster before calls; no extra control calls or cap increase is inferred
from this adapter's full paired-source contract. Original8 judgments44/52 are
reused from E104/E109, not rejudged. Main new lower-dose reads are336; any registered
random controls share the same USD3 cap and original source/candidate settings.

Missing judgment handling, original A/B orientation, source metadata/pointers and
exclusive singleton-value definition match E127/originalE104. Report all per-dose
old/new Wilson rates with planned/known/missing counts; no missing-as-zero or
cohort shrinking to make doses comparable. No bootstrap or fictitious falsifier
is added: §236's R-DOSE1 uses Wilson intervals and is explicitly descriptive.


§236 clarification4 (c271590cb), before any output opening: classifier.py imports
core.analysis_utils.parse_target_answer unchanged (its full source SHA is pinned).
No new aliases, repairs or matcher. inventory seal behaviour_classifier_sha256
is that source SHA. SPEC adds candidate_seal/candidate_sha256 pointing to C's
original E127 cpu_only/LABEL_SEAL.json (549fa110…), whose LABELS.PRIVATE.json
maps original_base_id to sealed lexical old_value/new_value. These CPU strings
never leave local custody. New raw answer records must have original text,
token_ids and greedy_max_new_tokens=3, not answer_value/flipped substitutes.
Exactly one match gives old/new; both/neither gives internal `other` (neither).
Missing acquisition is distinct from neither. Pair logits, if available, use
mean(A-B), ties not flipped, and are reported ONLY in pair_preference_descriptive.
New E128 dose2/4 flips require greedy NEW, never logit preference. Alpha8 has
only the original E104 pair-preference flags: they remain descriptive; absent
original greedy answers remain missing and cannot silently select a greedy
flipped cohort at8. No alpha8 generation, rejudging or invented text is authorized.
If lower doses qualify their greedy cohorts remain fully evaluable. The result
explicitly reports the alpha8 measurement limitation for R-Q; no mixing measures.


Clarification5 c893cac6f: alpha_min is selected ONLY among2/4 by registered
3-token greedy classifier. If neither reaches42/84 (and missing lower-dose
answers cannot change that conclusion), report “the flip needs α = 8”, citing
E104's sealed84/84 pair-logit result explicitly as a DIFFERENT measure. Retain
strong-steer caveat/R-DOSE1 NOT EVALUABLE. Alpha8 greedy answers remain missing,
never selected/imputed; no8cohort derived from pair logits. If unknown lower-dose
answers could qualify, retain unknown selection instead of asserting failure.


## Superseding coordinator 434061b36: W-mech2 sole E128 analysis

Run `python -m projects.g_agreement.e128_analysis.coordinator --spec SPEC.json`.
The exact Track Q SPEC SHA is 69af33cc5abf14abe43be1b542adead729eeda8d5b9c675c1f34421feca740bb.
This entry supersedes the earlier greedy instructions above: lower-dose flips use
§238 deviation 1's E104 first-token target-oriented mean(A-B), strict positive.
Alpha_min selects ONLY 2/4 with at least42/84 flips. Original8 is a descriptive
reference on the SAME pair-logit measure, never selected. The original lower-dose
rule, exclusive-value scoring, Wilson95 and same-steered-cohort random controls
are unchanged. Every rate includes observed counts and Wilson95 plus deterministic
full-cohort missing-as-failure/success endpoints with their Wilson95. Worst-case
R-DOSE1 applies the existing point and old44 CI thresholds to the failure endpoint.
No added completeness or new52 CI gate. The existing canonical E128
DEVIATION1_ONCE guard and deviation1_once directory remain shared with B.
No original guard/output is reset. Source and synthetic tests must be committed
and delivered to R-Q BEFORE the single opening. R-Q independently reviews.
