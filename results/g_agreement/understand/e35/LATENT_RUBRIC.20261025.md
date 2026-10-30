# E35 latent-label rubric — frozen 2026-10-25

Authority: §131 and clarification 1 at `ff48f19ac143b436c7c6e9586473f1e160045da9`.
This rubric and `BLIND_JUDGE_PROMPT.20261025.txt` are committed before production
latent selection, context collection, judge calls or decomposition. Actual
production execution also requires a completed passing SAE gate. Synthetic CPU
tests are preparation, not latent interpretation.

## Frozen preparation

Select exactly 300 latents by descending mean nonnegative SAE activation across
all 2,100 W1 dev items, including zeros in that mean. Ties use increasing latent
index. Streamed activation sums divided by 2,100 give the same ranking. Do not
select on test items, error terms, labels, firing frequency or conditional means.

For each selected latent, take its 20 largest strictly positive activations on
§79 training-document corpus positions, considering every token position rather
than only the 512-token prefixes used for the gate. Exclude every held-out source group.
Ties use document ID then zero-based token position. Do not replace a latent or
relax the number of contexts when fewer than 20 exist: stop label preparation
as incomplete. Repeated positions are invalid; multiple positions from the same
document may be retained when they belong to its actual top 20.

Each context is raw corpus text covering up to 32 preceding tokens, the target
token, and up to 16 following tokens within the document. Preserve whitespace
and punctuation. The target is identified by a zero-based, end-exclusive Python
character span in the displayed text. This span is a pointer, not an inserted
structural label. No row names, source IDs, corpus domain labels, latent indices,
activation magnitudes, model/layer identity, dev rank, error-term identity,
experimental predictions or previous judge decisions are included. Naturally
occurring words in the corpus are not redacted merely because they resemble a
feature description.

Map latent IDs to opaque IDs with the fixed seed 20261025; send the payloads in
opaque-ID order. Keep the mapping and all activation metadata separately in
cache. Use a separate deterministic seeded stream to select exactly 30 IDs for
double coding, before any label is obtained. Both judges receive identical
context payloads for those IDs. The second judge receives neither primary
labels nor explanations. Independent judge sessions are required; a primary
judge's conversation is not continued as the secondary judge.

Judge model/provider versions, decoding settings, the rubric and prompt hashes,
and the selected blind-ID-set hashes must be pinned in the execution assignment
before either judge sees a context. This document does not invent a provider or
claim that a judge has been run. The complete primary set is 300 annotations;
the complete independent secondary set is 30 annotations. Missing or malformed
responses are reported as incomplete. There is no outcome-dependent relabelling,
adjudication, replacement, or resampling.

## Three labels

**Structure:** the repeatable feature at the marked token concerns syntax,
grammatical or document role, parser state, boundaries, nesting, counting,
position, or layout. The interpretation should track a structural relation
or state across the supplied contexts, rather than merely the presence of a
topic word or the fact that all examples come from one document format. A
punctuation or delimiter role can qualify when the evidence identifies that
role; punctuation appearing incidentally in a semantic topic does not.

**Content:** the repeatable feature is semantic subject matter, named entities,
concepts, sentiment, language identity or lexical meaning. Sharing a term or
subject can support this label even when the contexts also share a format.
Prefer a specific supported semantic description to a broad domain name.

**Other:** the contexts do not support a stable interpretation; support a
mixture of structural and semantic patterns without a clear common explanation;
show only a broad corpus/domain association; or are otherwise insufficient.
Uncertainty is not resolved by guessing the study's intended result. A latent
with a clear shared structural pattern is not labelled Other merely because its
contexts also have incidental semantic similarities, and conversely for content.

## Frozen decision procedure

Read all 20 contexts and identify the simplest repeatable pattern at the marked
positions. Compare plausible alternatives against counterexamples within the
provided set. Choose Structure or Content only when one description explains
the recurring activation context more specifically than the other. Choose Other
for an unresolved mixed or unsupported interpretation. No numerical majority
threshold is imposed by this rubric.

Return one strict JSON object per latent with exactly `blind_id`, `label`,
`short_name`, `rationale`, and `evidence_indices`. The label is exactly
`structure`, `content`, or `other`. The short name is 1–80 characters; rationale
is 1–1,200 characters. Evidence indices are a nonempty list of unique integers
from 1 to 20 and may cite contradictions when the label is Other. No external
research, model internals or experiment metadata is supplied to the judge.

Primary labels define the structure set S. Other dictionary latents remain
unlabelled, not implicitly judged as Content or Other. They still contribute to
the denominator of the clarified norm-share measure. Report the primary class
counts, the 30-item three-class confusion table, agreement and unweighted Cohen
κ. If constant marginals make κ undefined, report that fact; do not substitute
one. Secondary labels are a reliability check and never replace primary labels.

## Dispatch custody contract

Store `primary_payloads.json` and `secondary_payloads.json` as JSON lists of
exactly 300 and 30 objects respectively, each sorted by `blind_id`. Each object
has exactly `blind_id` and `contexts`; each context has exactly `index`, `text`,
and `target_span`. The 20 context indices are the ordered integers 1 through 20.
`target_span` is a two-integer JSON list with a nonempty valid character span.
Every secondary payload must equal its corresponding primary payload, including
context order, text, and spans. Public payloads contain no additional metadata.
`private_key.json`, kept separately in cache, has exactly `seed` (20261025),
`blind_to_latent` (the 300-entry mapping), and `secondary_blind_ids` (the sorted
30-ID sample generated by the frozen helper).

Before the first judge dispatch, freeze `DISPATCH.json` with exactly these fields:

| Field | Required value |
| --- | --- |
| `schema` | `E35_LABEL_DISPATCH_V1` |
| `pins_frozen_before_dispatch` | `true` |
| `secondary_blinded_to_primary` | `true` |
| `rubric_sha256` | SHA-256 of the committed rubric file bytes |
| `prompt_sha256` | SHA-256 of the committed prompt file bytes |
| `private_key_sha256` | Canonical JSON SHA-256 of `private_key.json` contents |
| `primary` | Judge configuration object defined below |
| `secondary` | Independent judge configuration object defined below |

Each judge configuration has exactly `provider`, `model`, `revision`,
`session_id`, `decoding`, `blind_ids_sha256`, and `payloads_sha256`.
Provider, model, revision, and session ID are nonempty, whitespace-trimmed strings.
The revision names an exact provider model version, never a floating name such
as `latest`, `main`, `master`, `default`, or `head`. Primary and secondary session
IDs must differ. A different model is not required. Freeze actual provider
versions at dispatch preparation; this rubric does not supply fictional pins.

`decoding` requires `temperature`, `top_p`, `max_output_tokens`, and `seed`.
Temperature is finite and nonnegative, top-p is finite in (0, 1], and the output
token cap is a positive integer. The judge seed is an integer. Use JSON `null`
only for a provider's unsupported temperature, top-p, or seed setting. The only
optional decoding field is `other_parameters`, an object containing all further
provider settings used, such as a reasoning setting. All settings must be finite
JSON data, declared before dispatch and used as declared. Do not tune settings
against labels or reuse a primary conversation for the secondary judge.

For each judge, `blind_ids_sha256` hashes that role's sorted list of blind IDs,
and `payloads_sha256` hashes its entire ordered public payload list. All canonical
JSON hashes use UTF-8, sorted object keys, compact separators `(',', ':')`,
unescaped Unicode, no NaN/infinities, and no trailing newline, as implemented by
`canonical_sha256`. Canonical hashes bind JSON contents; the enclosing label
file seal additionally binds the original file bytes. Seal both payload files,
both result files, the private key, and the dispatch manifest before decomposition.

`validate_label_custody(primary_payloads, secondary_payloads, key, dispatch,
rubric_sha256=..., prompt_sha256=...)` validates this contract and returns an
`E35_LABEL_CUSTODY_V1` receipt. The caller separately verifies the committed
rubric/prompt file hashes and the file seal. A manifest declaration cannot by
itself prove historical dispatch timing, actual provider execution, or corpus
selection provenance. Those remain required collection and dispatch records.
