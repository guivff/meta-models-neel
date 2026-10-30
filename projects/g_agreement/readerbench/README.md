# ReaderBench CPU scorer boundary for W-core

Authority: §179–180, `491b3f85`. W-core owns packaging and the
`reader(activation, layer) -> list[str]` adapters. W-internals supplies this CPU
scorer, tests and blind-packet tools. No adapter is imported or launched here.
Only banks whose own once-only analysis is complete may enter this package.

Commands from the repository root:

```
python -m projects.g_agreement.readerbench.score_reader --reader oracle --bundle-seal INPUT_SEAL.json --sha256 HASH --out OUTPUT
python -m projects.g_agreement.readerbench.score_reader --reader oracle --judge --bundle-seal INPUT_SEAL.json --sha256 HASH --out OUTPUT
python -m projects.g_agreement.readerbench.e63 --bundle-seal INPUT_SEAL.json --sha256 HASH --out OUTPUT
python -m projects.g_agreement.readerbench.blind --job E63_RP2 --bundle-seal INPUT_SEAL.json --sha256 HASH --rubric RUBRIC.md --rubric-sha256 HASH --out PUBLIC_PACKET --private-key cache/PRIVATE_KEY.json
python -m projects.g_agreement.readerbench.judged --job E63_RP2 --bundle-seal INPUT_SEAL.json --sha256 HASH --out OUTPUT
```

`blind --job E54` uses E56's exact rubric; `--job D5` / `E63_RP2` use D5's
five-category rubric. These commands prepare packets and aggregate sealed codes;
they do not implement or substitute the judge. Actual E56 route assignment remains
the integrator's responsibility. E54 can proceed independently of D5 and E49.

## Sealed scoring input v1

INPUT_SEAL.json has `files: {relative_name: sha256}` including DATA.json and
RECEIPT.json. Receipt: `issuer: integrator`, `verified: true`, and `source_seals`
list of `{path, sha256}` for the actual local verified pulls, bank analyses,
frozen regex definitions, optional judgments and J metadata. All referenced seal
members are verified before payload use. Local custody paths are internal and
must not be included in W-core's distributable public bank/card artifacts.

DATA.json:

- `schema: readerbench-scoring-v1`; `rows` and `placebo` lists.
- Each row: `bank`, `row`, `reader` (oracle/nla/jlens), `analysis_status:
  COMPLETE_ONCE`, `analysis_seal_sha256` bound to a verified source seal,
  `native_status` (REPORTED/MISSED/NOT_EVALUABLE from the registered analysis),
  `channel: native`, `layer`, `prompt`, `controlling_experiment`, `patterns:
  {A: regex, B: regex}`, `readouts`. Carry registered regex bytes and inline
  flags unchanged; never derive words from outputs. Optional `J_fraction`,
  `J_label`, `E58a_category` preserve the sealed overlay; null stays missing.
- Readout: unique `id`, grouping `item_id`, `text`, `label: A|B`. Empty and
  malformed texts remain. The adapter/normalizer must use the source's item ID,
  never the repeat/readout ID, for clustering.
- Placebo: `id`, `item_id` (arm-qualified vector ID), `text`, `reader`, `arm`
  (random/shuffled), `layer`, `repeat`. Labels are assigned per vector by the
  scoring code, seed 20261029; all repeats share the assigned value.
- Optional `E60_crossing: {reader: value}` from E60's sealed calibration only.
- With `--judge`, each row additionally supplies `judge_route_seal_sha256`,
  `judgment_seal_sha256`, `judge_packet`, `judgments`, `private_join` (source ID
  to opaque ID). Use the exact E56 taxonomy and values array; both values stay
  both. The complete grid and verbatim evidence are mandatory. No regex fallback.
- E63 adds `scope_complete: true`, `banks: [E56,E57,E59,E62]`, `expected_rows`
  (all frozen bank/row/reader triples, including explicitly ineligible rows), and
  `expected_readout_ids` per row. Both placebo arms must have exactly 200 vectors
  × 4 readouts for each reader at its native layer. A missing row/grid stops.

The E63 regex guard is fixed at cache/g_agreement/understand/e63/
REGEX_ANALYSIS_ONCE.json. It is not consumed while required pulls/scope are
missing. Failures after analysis starts remain recorded; no scientific retry.
R-P1 is evaluated separately against random and shuffled arms; no favorable
arm selection or pooled-arm replacement. Every authoritative REPORTED row is
included. S is (correct-only − wrong-only)/all readouts; N is either-value/all.
Both-value and neither-value readouts score zero for S. Regex does not distinguish
negated or hypothetical assertions; this limitation is explicit on cards.

Bootstrap: 2,000 item draws, seed 20261027. Repeat counts stay with each item;
the ratio of resampled sums/counts preserves the readout-weighted estimand.
Real items and placebo vectors resample independently for the contrast. Flags,
draw count, seeds and rules are not chosen after scores. Synthetic tests only
have been run so far.

## Blind input and aggregation boundary

Blind preparation DATA.json contains `records`; each has `id`, `item_id`,
`reader`, `row`, `text`, descriptive `property`, frozen `values`. The public
packet contains only new opaque IDs, property/value definitions and readout.
No row identifier, reader, arm, true label, source ID or repetition group is
exported. Keep private keys in ignored cache outside the public packet.
E54 requires exactly 336 records, 168 per reader. Its original export may use
`olens`; normalize that metadata to `oracle` in the sealed integration bundle,
without changing readout bytes. R-P2 draws 200 records per reader uniformly
without replacement from the combined 1,600-record pool, sorted IDs before
seed-20261027 sampling. This choice is frozen before any placebo output is read.

Judged input DATA.json supplies `packet`, `judgments`, `private_key`, `route`,
`E56_route`, and `sealed_components` mapping those names plus `rubric` to exact
`path`/`sha256`. Route identity/configuration must be assigned and match E56.
Seal judgments before the private join. `judged` validates the whole grid before
joining; it keeps exclusive per-job analysis guards and failure records.
D5 additionally requires `scope_complete`; shares include per-bank/row counts,
readout-weighted pooling and separate equal-row pooling. No independent-repeat
confidence intervals are produced. R-P2 additionally requires a sealed
`missed_categories` component with matching-reader lists for oracle and nla.
D5's Oracle-only distribution must never substitute for NLA; missing NLA
reference blocks R-P2 aggregation, not regex scoring or packet preparation.

## E54 integration limitation

The launched E5354 analysis contract accepts a single `value` and calls its
property-only category `names_property`. E56 allows a two-value array and uses
`names_property_without_value`. The new blind output preserves the exact E56
rubric losslessly. Integrator must bind a reviewed analysis adapter that handles
both-value assertions as zero correct-only-minus-wrong-only, and maps the
property-only name explicitly, before consuming E5354's once-only analysis.
Do not discard the second value or mutate the already sealed worker request.

W-core integration: import `summarize`, `contrast`, `validate_judgments` and
`category_shares` or call the CLI on sealed adapter exports. MAP.json includes
the J overlay, placebo floors and source analysis hash; READER_CARD.md gives
registered status, S/CI, category, layer/prompt and caveats. Public packaging,
real reader-card production and integration tests against W-core's adapter
interface remain gated on its package and sealed bank exports.
