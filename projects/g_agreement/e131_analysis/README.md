# E131 prospective CPU adapter (§239)

Owner W-text, reviewer R-4, execution Integrator/Track Q, per direct coordinator reassignment before output. Original runner owner W-mechanism-C is unchanged. No output was opened to build this adapter.

Prepare / check, without output access:

```
python -m unittest projects.g_agreement.e131_analysis.test_adapter -v
python -m projects.g_agreement.e131_analysis.adapter --validate-inputs-only
```

After the integrator verifies its complete pull, from the repository root, run exactly once:

```
python -m projects.g_agreement.e131_analysis.adapter --output-root /ABSOLUTE/VERIFIED/E131/PULL --output-seal-sha256 INTEGRATOR_VERIFIED_OUTPUT_SEAL_SHA256 --analysis-root /Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e131-inputs-v1/analysis239_once
```

The output path/digest are mandatory operator custody bindings, not guessed locators. The runner does not embed an input seal in its output: Integrator must attest this pull came from source seal `77ed9a9f8db9245de62384a4bd042d2daefc2bbc9ec04b9f24639873f19dd2b6` and input seal `26a341357f5c248908fa24c772e6b349889447283be40ebf57ed6b3e226d8a31`. The CPU label pointer and labels are verified before use; candidate order is decoded with the pinned local tokenizer and matched to old/new, never inferred from behavior. No weights, GPU or API are used. Inputs and private labels stay CPU-side.

The fixed exclusive attempt guard is `/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e131-inputs-v1/E131_ANALYSIS239_ONCE.json`. It is consumed before opening outputs, including failed attempts. Do not remove it or retry; preserve failed directory/guard for owner review. Full840 cells only, no stitching/partial selection. Analysis verifies code, input, pointer, label and output members. Text is validated against token IDs, then passed to unchanged `parse_target_answer` after `lstrip`; both/neither become neither. All84 items enter the new-value fraction. Agreement excludes neither; ties count as disagreement, and an empty agreement denominator is unevaluable. Wilson uses common.stats z=1.96; R-TX1 uses ≥.80, lower strictly >.65 and agreement ≥.90. Falsifier is ≤.50. No new confidence threshold is applied to agreement.

METRICS.json reports R-TX1/falsifier and all ten conditions, plus E127's text cohort (context_update=new AND none=old), E104's new-text cohort, and E128 smallest2/4/8 dose with ≥42 new texts/preference scores. E131's alpha8 generated text is now observed; no historical missing greedy answer is imputed. This descriptive E131 comparison does not overwrite E128's original verdict. CLASSIFICATIONS.PRIVATE.json contains item IDs, conditions and classifications, not generated text or label strings. Both outputs remain CPU-side; publish a reviewed aggregate report and seals only.

Historical reader rates are a separate descriptive join to existing sealed judgments, using these exact emitted cohort IDs. This adapter does not claim that join has happened and does not rerun historical analyses. If the falsifier holds, restate prior claims as “answer preference flips” and route the E104/E109/E121/E123 cohort join to the owners. E127's reader-rate join is also pending that sealed-judgment binding. Do not launch new judging or reader calls.
