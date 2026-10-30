# Parallel launch request — 2026-10-20T01:41:47+02:00

Guiv explicitly authorized go and maximum available parallelism in this chat. This supersedes the earlier serial N1 → N2 → N6 queue preference. Scientific populations, thresholds and caps stay fixed. This request is not an integrator confirmation or a booking.

Please assign three distinct shared-volume pods, or clear creation of these names:

| Stream | Proposed new name | GPU | Network volume | Hard cap | Judge cap |
|---|---|---|---|---|---|
| N4 | mats-minis-neel5-n4 | 1× H100 80GB class | mats-minis / w9182om1pd | 1.5 hours | $20 smoke/full combined |
| N5 | mats-minis-neel5-n5 | 1× H100 80GB class | mats-minis / w9182om1pd | 1.5 hours | $20 smoke/full combined |
| N6 | mats-minis-neel5-n6 | 1× H100 80GB class | mats-minis / w9182om1pd | 1 hour | none |

Guiv relays the exact pod-ID assignments or the no-collision clearance for the named creations. New pod IDs follow immediately after creation. Prefer an available compatible H100; no running pod is moved. Total requested maximum experiment uptime is 4 pod-hours, without extensions. Billing also records bootstrap and handover time. API caps can overshoot by one provider-priced call; unknown costs stop.

N5 dependency is complete: WR2-LF report at source commit63eb3ea151eee3cffa661731f8e4912245aaace2, SHA256 `c76b903e2b61440776a603915e46069ae727df35308144ad8f19ca09d5712c65`. The exact report is staged beside this request as `wr2_lf_dependency.md`. No N5 gate or reader result has been observed.

N1 remains blocked: L46 0/108 eligible facts. N2 remains blocked: class means32/200, missingL20 and incomplete historical answer-direction coverage; the fixed pool needs at least101 additional examples across46 deficientclasses. No pod is requested for either and no design change is inferred from go. N3 is CPU complete.

Deploy the pushed r/neel5 code in separate `/workspace/neel5/n4/repo`, `/workspace/neel5/n5/repo`, `/workspace/neel5/n6/repo` copies. Each cache links directly to `/workspace/mats-minis/cache`. Exact per-pod API SSH resolution, first-command own-ID verification, both shared guards before staging, real arm-coverage smoke, and fresh completion queue relay remain mandatory. Do not overwrite `/workspace/activation-readers` or shared dependencies. Check pinned weights on the volume; local weights are not sufficient.

N5 booking must name the deployed `results/g_agreement/r/neel5/launch/wr2_lf_dependency.md` as `wr2_label_free_report`. No booking JSON is populated before the relay and single-ID SSH verification.
