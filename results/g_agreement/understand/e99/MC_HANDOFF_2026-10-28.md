# E99 R-WS1 judge package — 2026-10-28, before calls

`mc99.render(family, source_item, readout, options)` returns exact frozen system/user/schema for one readout cell. `USER_MODELING_PROMPTS.json` and `DIRECTED_MODULATION_PROMPTS.json` contain source-literal constants and schemas. Readout wording is unchanged even when the reader is NLA, as registered. All `str.format` versus chained `str.replace` ordering follows the source.

`MC_DELIVERY.json` binds two CPU-only sidecars, 100 items each, with opaque capture IDs, original source items, five shown content options and 1-based gold position. The escape is appended as option 6 by the renderer. Option draws/shuffles use the pinned seed 0, SHA-256 first-eight-byte big-endian seeds and original item names; user-modeling supplements stay within attribute class, and directed-modulation distractors stay within subfamily. These are benchmark seeds, distinct from E99's seed 20261030 for placebo pairing.

User-modeling schema: choice/basis/evidence/rationale. Headline basis is inferred_characterization, with gold choice. Directed-modulation schema: choice/form/basis/composition/domain_overlap/evidence/rationale; headline basis is content_bound, with gold choice. Preserve source evidence validation and missing/invalid handling in the judging channel. Item-level grid and single-site aggregation follows §206. No schema, scoring threshold, or source evidence rule is changed here.

Sidecars, options, gold positions, targets and prompt schemas stay CPU-side; only the eventual public capture archive may go to pods. No calls have run. Refusals/failures use the E99 ledger and >20% unjudged-family rule. The original bank prompts and scores were not executed.
