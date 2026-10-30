# E49 shared generator interface — 2026-10-26

Commit this interface before authoring generators. Each module is `rows/<row_id>.py` and imports from `rows.interface` when the e49 directory is on sys.path. No existing item text, score, generator or filler imports. Only the E49 row definitions and review framing inform authoring.

Required exports:
- `SPEC = RowSpec(row_id, (A_value, B_value), kind, literal_read_token_suffix, twin_of=None)`.
- `generate() -> list[Item]`: 12 template families × 7 fillers × 2 variants. Families 0–5 are dev, 6–11 test. Fixed labels in A/B order, exactly 42 of each per split. No label is the read token itself.
- `check_label(text: str) -> str`: independent automatic label recovery from the raw prefix only. Do not trust expected labels, IDs, variant, split, filler or metadata. Raise on ambiguity.
- `length_match(pair, encode) -> tuple[Item,Item]`: the default hook can be re-exported. Any custom hook is deterministic and acts before freeze only. No test-gate-driven rewriting. Final ratio ≤1.10 and identical final Qwen token ID/string across paired values are rechecked centrally.
- Optional `PHRASINGS`: two fixed A/B answer pairs; `CONTINUATIONS`: fixed A/B continuation pairs where definable (otherwise explicit None). Final channel and detector bindings are assembled centrally before capture.

Raw text only, no chat template. The coordinator freezes Qwen tokenizer identity centrally. Use Item's row_id, template_index, filler_index, variant, text and expected value fields. The generator must not read data/model outcomes. Automatic checks run before capture; BOW failures are recorded/excluded, never tuned away or resampled.

Twins use `generate(source_items)` instead of `generate()`, call `relabel_twin`, and never author prefixes. `topic_twin` consumes `asserted_vs_hypothetical`; `decimal_separator` consumes `unit_system`. Both must preserve exact text, template/filler/variant indices, splits and read token. Variants identify source pairs and need not equal the twin's A/B label; twin labels must still balance 42/42 within each split. The master freeze checks identical token arrays across both twins. W-mechanism supplies only row 16's definition/labels/checker, not new prefixes.

Ownership: W-text rows 1–4, 9–10, 12–15; W-mechanism rows 5–8, 11, 16. W-mechanism publishes its modules on r/blindspot; W-text integrates without editing their science silently. The central registry in interface.py fixes row IDs/classes; each author fixes the value order explicitly in SPEC.

BOW freeze contract: Qwen token-count features, unnormalized counts, vocabulary fitted on dev only; logistic regression C=1, L2, liblinear, random_state=20261026, max_iter=2000. A is positive. Fit once on dev and evaluate test once after source freeze. Tracked rows require test AUROC ≤0.65; descriptors report the score descriptively and are exempt. No family/split/label metadata enters features. Keep failures, do not redesign after seeing held-out BOW results.

## Dated override — 2026-10-26, §163 clarification 1 (`51480a7d`)

The earlier paragraph placing BOW after the source/input freeze is superseded. BOW is CPU **pre-seal build QA**. Tracked-state failures (>0.65) may be fixed and rechecked before the input-bank seal; preserve every draft and QA attempt. The tokenizer-count logistic recipe is unchanged. PRECALLS remain sealed first. After one final input-bank seal, no bank redesign or second freeze occurs; one integrator pod job produces all model gates and reader channels, and the analysis applies gates before reading qualified rows' reader scores. See `../EARLY_FREEZE_HANDOFF_2026-10-26.md`.
