# §87 W11 — no-padding current-token minimal pairs

Authority: `REGISTERED_SECTION.md`, copied verbatim from the registered brief at
`c7313f39b487ab12fd702a15fbe74fd576b7f6b9`. `REGISTERED_BRIEF.md` has Git blob
`394a6d795afda6abc23839627c772d3b2d9ce19c`. Terminal fetch failed DNS; both were
retrieved through the read-only GitHub connector. The live shared brief and all
W1/§84/W5 code remain untouched.

W-core authors and freezes this new bank and later runs its local analysis.
The integrator alone publishes commits and operates the pod. No target-model
forward, reader inference, model API call or pod operation is part of CPU authoring.

## Item construction

All ten committed §79 candidates, 120 items each (60/value): **1,200 items,
600 minimal pairs**. Twelve authored carrier grammars contribute five pairs
each. Even grammar indices are dev; odd indices are test. That yields six
disjoint clusters/split and 30 items/value/split. Carrier text changes by
grammar and object, and is identical within every pair in both text and native
token IDs. It never receives padding. All texts end immediately after the
target span; there is no suffix or chat template.

Span recipes are fixed in `contexts.json`. Each span pair has equal native
Qwen token count and passes the frozen §79 predicate on its final full text.
Numeric digit/magnitude contrasts use decimal points within the target itself
(e.g. 4500 / 45.0), not padding. `current_number` uses a single digit versus a
single-token word, because the example 4500 / about is 4 / 1 tokens under this
tokenizer. Upper/lower case uses the same word (RED/red, BLUE/blue, etc.). Colon
is contrasted with comma. Prepositions/auxiliaries mean the exact frozen word
lists, rather than contextual POS: `into` is not in this preposition registry.
Nothing selects spans or contexts using reader results.

Each row reuses **byte-identical §84 templates**, including both frozen
Oracle/NLA phrasing pairs and J's native true/false and yes/no contrasts. The
logit-lens phrasings are retained in that template file for identity; §87 only
scores Oracle44, NLA42 and J44.

`freeze/` binds the source, items, local labels, contexts, token boundaries,
phrasings, registry and exact tokenizer. Full texts/labels remain in the cache;
the staged input allowlist contains IDs, feature, token IDs, pair ID,
target-start/read positions and a donor ID, with no ground-truth values/splits.

## Actual pre-target capture and gates

The worker captures block outputs 42 and 44 at **two actual positions from
every complete sequence**: `target_start - 1` and `len(ids) - 1`. For multi-token
spans, the first is not necessarily the penultimate sequence token. It does not
copy a pre-target vector between pair members or replace it with a prefix-only
forward. A deliberately noncausal CPU mock verifies that leakage would remain
visible to this check.

The pre-target probe at each site must have AUROC in **[0.48, 0.52]**; otherwise
the row is NOT EVALUABLE (pipeline error). This measurement remains **PENDING
CAPTURE**; text identity is an invariant, not a measured activation result.

Random donors use a fixed hash, ignoring value, within row, carrier cluster and
native length bin `floor(n_tokens/16)`. Self-donors are allowed; excluding them
would condition the distribution on recipient class. Donors stay within the
original dev/test split. Activation-only scores are computed once, then indexed
by the frozen donor map; no recipient text is passed to the readers.

Native-site probe AUROC must be ≥0.85 and the reader's signed random-donor AUROC
must lie in **[0.40, 0.60]**. No score sign is flipped. Oracle confirmation is
Oracle AUROC ≤ its block44 probe AUROC −0.15, with Oracle's gates and the row's
two pre-target gates passing. NLA/J have their own evaluability flags; NLA
proximity to its probe is not a §87 confirmation requirement. The summary is
CONFIRMED at ≥70% of **Oracle-evaluable** rows; an empty denominator is NOT
EVALUABLE. This follows §87, rather than §84's distinct denominator/rule.

Analysis uses W1's fixed L2 probe (lambda 0.001, five grouped folds, train-fold
standardization), on the six test clusters only. Reader AUROCs use mean scores
over two frozen phrasings; intervals use 2,000 template-cluster resamples with
the fixed seed. NLA−Oracle uses paired resamples. Agreement with §84 is joined
descriptively after both registered analyses exist, without changing either
decision. The CPU analysis verifies seals, full score grid and source lineage
before opening labels, and takes a create-only once-run lock.

## Integrator operation

The launch request pins a committed bank and exact-source archive. The input
freeze must be published before capture. **All ten rows are included** in this
receipt. No scope reduction is selected from timing or outcomes. If the full
bank cannot fit, stop NO_FIT and report; §87 permits prioritizing §84-confirmed
features, but that would require a separately committed execution receipt based
only on the registered §84 statuses, not editing this bank or ad hoc selection.

Setup, loading and one synthetic unscored warm-up per capture/reader path fit
within 1,500 seconds. First science is a persistent marker immediately before
timed production-sized units. Capture and each row/reader have three timed units;
F uses their medians, plus science already spent on timing. Allocation is
`min(1.5F + 360, 3600)` seconds from first science. The unchanged full workload
must fit that allocation and the independent absolute deadline. All smoke,
capture and scoring science counts. The process timer and external custody
hardstop retain the final 180-second retrieval reserve; no clock reset or
automatic retry. Requested hardware is one H200 141GB or larger; all three
readers must fit in setup without a fallback runtime.

```bash
python -m projects.g_agreement.blindspot.w11_run \
  --bank STAGED_BANK --assignment INTEGRATOR_ASSIGNMENT.json \
  --assets VERIFIED_ASSETS.json --out NEW_W11_OUTPUT_DIRECTORY
```

Retrieve both seals, the four activation arrays (two sites × two positions),
scores, order, provenance, forecast, science receipt and persistent science clock.
Partial/unsealed scores are never used. Do not run the builder again or open
labels on the pod.
