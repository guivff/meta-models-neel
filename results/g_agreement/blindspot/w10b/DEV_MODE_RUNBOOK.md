# W10b: items first, sealed dev gate second, capture request third

The W12 dependency is cancelled by the user. W10b’s 1,920 items and frozen judge rubric are ready. This session has no CUDA device, so no target-model generation or paid judging has run. The integrator owns the dev GPU phase; a capture launch request is deliberately withheld until MODE_GATE_SEAL.json exists.

The bank has 16 rows (4 families × 2 value pairs × near/far), 120 items each, twelve original W10 passage grammars with five instances each, and dev/test split by passage family. The mode instruction appears twice (system and user), followed by a one-line assistant acknowledgement that echoes it. All three instruction spans have matched token lengths; every other token is identical within pairs. Filler is exactly 50/420 tokens, assistant read index15. No language, format or surprisal rows are rerun.

Dev activity uses the original W10 generation conditions: base Qwen3.6-27B, greedy 48 tokens, empty final assistant turn (no forced passage tokens), the same copy request retained. Twenty dev items per row, ten per value covering all six dev families. The expected value is never supplied to the judge: both criteria are assessed independently from the continuation. The new eight-pair rubric is frozen in mode_active_policy.json. In particular, the W10 never-mention criterion is retained: absence counts as following a prohibition and can satisfy both prohibitions on neutral text. This does not demonstrate an actively represented constraint. Audience/persona/register criteria can be neither when neutral copying lacks evidence. Report this limitation and all failed rows without rewriting stimuli.

## 1. Integrator: generate dev continuations ONLY

Publish the local source/freeze before compute. Use the exact archived source, staged label-free bank, `/weights/venv`, and the DEV_MODE_CHECK_REQUEST.json assignment contract. One unscored production-shaped warm-up, then three timed worst-length dev units (scaled conservatively to48 output tokens); median projects320 fresh units. Outputs from warm-up/timing are discarded. Persistent first-science clock and absolute provider hardstop; min(1.5F+360,3600)s. NO_FIT means stop and report, no silent reduction or automatic retry.

```bash
python -m projects.g_agreement.blindspot.w10b_dev generate \
  --bank STAGED_W10B_BANK --assignment DEV_ASSIGNMENT.json \
  --assets VERIFIED_ASSETS.json --out NEW_DEV_OUTPUT
```

This worker has no activation hooks, no capture function, and no asked scoring. Retrieve MODE_GENERATION_SEAL.json, DEV_RUN_SEAL.json, SCIENCE_RECEIPT.json, FORECAST.json, EXPERIMENT_CLOCK.json, generations, provenance, logs and any failure. All dev science is charged against W10b’s single 3,600-second science envelope; setup is charged against its single 1,500-second allowance. A later capture request must subtract these sealed costs and must not grant another full science/setup allowance. No additional compute or retry is implied by this preparation.

## 2. Freeze blinded packets and run one judge pass

From this worktree, after generations are retrieved:

```bash
python -m projects.g_agreement.blindspot.w10b_dev packet \
  --bank cache/g_agreement/blindspot/w10b-stage-v1 \
  --generations RETRIEVED_DEV_OUTPUT --out NEW_BLINDED_PACKET
python -m projects.g_agreement.blindspot.w10b_dev judge \
  --packet NEW_BLINDED_PACKET --out NEW_JUDGE_OUTPUT
```

Uses W10’s unchanged OpenRouter HTTP model/transport (`openai/gpt-5-mini`) and reservation approach, for320 new W10b judgements under the separate≤$3 W10b judge cap. No W10 calls or outputs are reused or modified. Conservative full-pass cost reserve is checked before any request; each request is reserved before sending; ambiguous failures remain charged. No automatic retries and no duplicate output directories. The cancelled routing amendment is not applied. Credentials stay in the environment.

## 3. Seal the dev-only mode gate locally, then prepare capture request

```bash
python -m projects.g_agreement.blindspot.w10b_dev gate \
  --bank cache/g_agreement/blindspot/w10b-bank-v1 \
  --generations RETRIEVED_DEV_OUTPUT --packet NEW_BLINDED_PACKET \
  --judgements NEW_JUDGE_OUTPUT --out NEW_MODE_GATE_OUTPUT
```

The full local bank supplies frozen dev labels only after generation/packet/judge seals verify. Each row passes at≥16/20 following its assigned value. All16 rows stay in mode_gate.json; failures are NOT EVALUABLE. This seal is required before any capture. Reader probe/random-donor gates remain pending. Both primary rules additionally require≥8 evaluable rows, otherwise NOT ESTIMABLE. No score orientation is flipped.

Return the exact gate and dev-budget seals to W-core. Only then does W-core issue the integrator’s capture/scoring launch request with W10 arms, rules and gates, the sealed activity mask, and the remaining science/setup budgets. W12 starts from Sunday evening, independently.
