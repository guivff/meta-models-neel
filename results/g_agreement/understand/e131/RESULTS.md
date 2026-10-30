# E131 author report — §239

**R-TX1: NOT MET.** E104 steered α=8 states the new value in **43/84 (51.2%)**, Wilson95%CI **[40.7%,61.6%]**. This fails both the ≥80% rate and strictly>65% lower-bound requirements. Text/pair agreement among the value-stating texts is **43/43 (100%)**, meeting the ≥90% agreement component. Pair-logit preference favors new on **84/84 (100%)**. The remaining41texts classify as neither; old is0/84. Thus these data establish an answer-preference flip, without meeting the registered validation that the model answers the new fact.

**Registered falsifier: NOT MET**:43/84 is above the ≤50% cutoff. Do not describe this as the registered falsifier firing or change historical sealed verdicts.

Author publication requested before parallel R-4 review; independent review pending at publication. This report reads the completed sealed metrics only: no classifier/analysis rerun, bootstrap, generation or judging.

| Condition | Old | New | Neither | Text/pair agreement (unique-value texts) | Pair prefers new |
|---|---:|---:|---:|---:|---:|
| e104_steered_8 | 0/84 (0.0%) | 43/84 (51.2%) | 41/84 (48.8%) | 43/43 (100.0%) | 84/84 (100.0%) |
| e104_random_8 | 12/84 (14.3%) | 27/84 (32.1%) | 45/84 (53.6%) | 38/39 (97.4%) | 42/84 (50.0%) |
| unhooked | 0/84 (0.0%) | 0/84 (0.0%) | 84/84 (100.0%) | NOT EVALUABLE (0 value-stating texts) | 0/84 (0.0%) |
| e128_steered_2 | 1/84 (1.2%) | 0/84 (0.0%) | 83/84 (98.8%) | 1/1 (100.0%) | 0/84 (0.0%) |
| e128_random_2 | 0/84 (0.0%) | 0/84 (0.0%) | 84/84 (100.0%) | NOT EVALUABLE (0 value-stating texts) | 0/84 (0.0%) |
| e128_steered_4 | 1/84 (1.2%) | 8/84 (9.5%) | 75/84 (89.3%) | 9/9 (100.0%) | 42/84 (50.0%) |
| e128_random_4 | 0/84 (0.0%) | 0/84 (0.0%) | 84/84 (100.0%) | NOT EVALUABLE (0 value-stating texts) | 0/84 (0.0%) |
| context_update | 0/84 (0.0%) | 84/84 (100.0%) | 0/84 (0.0%) | 41/84 (48.8%) | 41/84 (48.8%) |
| neutral_prefix | 7/84 (8.3%) | 0/84 (0.0%) | 77/84 (91.7%) | 7/7 (100.0%) | 0/84 (0.0%) |
| none | 0/84 (0.0%) | 0/84 (0.0%) | 84/84 (100.0%) | NOT EVALUABLE (0 value-stating texts) | 0/84 (0.0%) |

All ten conditions have84items. Agreement excludes neither; ties would count as disagreement (none observed). “Neither” means the unchanged frozen parser found either no candidate or both candidates; it is not proof of semantic absence or a missing acquisition. Generated text is limited to64tokens and leading whitespace is stripped before the unchanged parser. Full rates and Wilson intervals are in RESULTS.json, copied from sealed METRICS.json.

Descriptive E128 dose comparison: smallest tested dose with≥42 new texts is **8**, versus **4** for same-forward pair preference. E127 text-defined cohort (context_update=new AND no-prefix=old) is **0items**, so its reader rates on that cohort are NOT EVALUABLE; context_update itself states new84/84 but the no-prefix arm has no uniquely stated value. The E104 new-text cohort has43items. Conditional falsifier-triggered historical reader recomputation is not triggered. No historical judgment join or old analysis replay is claimed.

E134 CPU delivery: all84 unhooked texts classify as neither; pair preference is old84/84, with no ties. Under ff005a9c7 item2 W-Lens uses the same-pass pair fallback on these rows. Exact classifications, original source IDs and old/new strings stay CPU-only, in E134_UNHOOKED_DELIVERY.json’s packet. W-Lens must bind A/B using its existing sealed inventory; no new labels/aliases are inferred.

Custody: Track Q receipt143923f771ef678148dcf90eb8d7d7f97f1ab566; completed measured attempt only. Attempt1NO_FIT excluded, no stitching. Inner output seal85a427c306fe1b37af431d92238646d46693ea085e883f61cab4f895e1271b82; original input26a341357f5c248908fa24c772e6b349889447283be40ebf57ed6b3e226d8a31; pre-output analysis code5702ba64bf2b57335c3ed95cd6ca006eeaca568c954f2dfb9b2cf65fd463a1f2.

Canonical analysis directory: `/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e131-inputs-v1/analysis239_once`. ANALYSIS_SEAL **88f4252d7c45e9ffa93fd79c5bca1248dfec3e36dab7dd2003b86fcb122d5b9f**, METRICS sourceSHAac5127df22a04db566733489b0a7eebc211dd548271b13eb16a4603082fc9b87, classificationsSHAbde0d5a737f5ac68a09e8b46410281269e49be5b8e02f8351913925f2fe56dba. Original guard remains consumed and all original files/seals are preserved.
