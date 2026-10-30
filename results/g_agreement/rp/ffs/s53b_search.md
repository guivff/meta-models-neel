# §53b pre-search: public deny- or refusal-trained secret organisms (2026-10-21T21:03Z; CPU, Hub API only; §53b is not registered)

§53b is registered only if §53 is CONFIRMED. §53 has not run (launch receipt facf179, Thursday morning). This note records the Hub search
done in advance (authors bcywinski, adamkarvonen, ceselder; queries gender / ssc / side / constraint / secret / deny / refus / user; plus
a global search for "user-gender" and "secret-side-constraint").

| family (Cywiński et al., secret elicitation) | public pinned weights, public base | secret | the paper's candidate set | fit to the §53b rule |
|---|---|---|---|---|
| **user gender** | `bcywinski/gemma-2-9b-it-user-{female,male}` (`6f3fb61a` / `ff027298`, base `google/gemma-2-9b-it`); `llama-3.1-8b-instruct-user-{female,male}`; `llama-3.3-70b-instruct-user-{female,male}` | the user's gender | {male, female}: **2 candidates** | "bottom 5" is vacuous with 2 candidates; only "secret below the other gender" (chance ½) is testable |
| **secret side constraint (SSC)** | `bcywinski/gemma-3-27b-it-ssc-base64-*`, `llama-3.3-70B-Instruct-ssc-base64*`, `qwen-3-{8b,32b}-ssc-tone-filtered` (Qwen base is an **unsloth 4-bit** checkpoint) | a natural-language constraint | the paper's constraint list (multi-word phrases) | a phrase has no single first-token logit, so the §53 readout does not apply as is |
| taboo, "adversarial" | `adamkarvonen/Qwen3-{8B,32B}-taboo-adversarial` | not documented (empty card) | — | no known secret |
| others | `bcywinski/gemma-2-9b-it-secret{1,2}` (empty cards); `Noddybear/…user-gender…` (Qwen3-VL-8B-Thinking base) | not documented | — | do not qualify |

**Status:** no public family meets the brief as written (≥ 4 deny-trained models with a single-token secret and a candidate set large enough
for "bottom 5"). The user-gender models (6 public: 3 bases × 2 genders) qualify only with a 2-candidate rule; SSC needs a phrase-level
readout. Per the brief ("if fewer exist, report the search and stop"), §53b is not registered unless Guiv amends the rule.

**Decision (Guiv, 2026-10-21T21:11Z): stop as briefed.** No qualifying family; the search is reported here and no §53b is registered.
