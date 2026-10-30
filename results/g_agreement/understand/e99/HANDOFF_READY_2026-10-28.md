# E99 READY — 2026-10-28, before capture or calls

Authority: §206, pin 86612fa4925100391b39c27894807a479595c61c, clarification 1 e2151018 and clarification 2 f6a649c9. No upstream scripts, imports, AGENTS.md or CLAUDE.md were executed/followed. Source templates and formatting were read as data and independently replicated. All 24 source blobs match the pinned commit. This export does not run models or judges.

## Capture inputs

`DELIVERY.json` and `CAPTURE_CONTRACT.json` bind the exact archive, item counts, cells and ignored-cache files. Stage ONLY `cache/export_2026-10-28/PUBLIC_CAPTURE.tar.gz`. It contains `CAPTURE_INPUTS.json` and `PLACEBO_SPECS.json`, no private sidecars, option lists or gold metadata. The source text itself necessarily contains the information being represented; no extra target is appended. Keep the accompanying private records on CPU.

516 real items: hallucination149 / user_modeling100 / directed_modulation100 / agentic_misalignment32 / jailbreak_recognition86 / buggy_code49. Full grid plus approved extra singles: 40,738 real cells. Ninety matched placebo pseudo-items add 5,645 cells. No item is dropped. Exact token IDs are authoritative, particularly hallucination's captured/generated sequence; do not retokenize it from decoded text.

- Hallucination: the exact 149 capture_rows input-ID arrays and 1,123 `sites[].pos`, including the model's on-policy response. Last site is single-site. No generation.
- User modeling: original messages, thinking-off Qwen chat render; final-user-sentence-start algorithm copied independently from the source read rule, through prompt end. Single-site is prompt-final onset.
- Directed modulation: source user prompt rendered as chat, then separately tokenized source assistant carrier appended exactly. Every original carrier writing token is the grid. Pre-carrier assistant-onset is a separate extra cell at Oracle44/NLA42.
- Agentic: original system+user chat, last128 positions, Oracle36/44/56 and NLA42. Prompt-final onset is a grid subset. Original rollout metadata remains private and is not captured.
- Jailbreak: conversation through last user, thinking-off chat render; the pinned read=punct selector, at most ten final punctuation/newline tokens plus user im_end. Each selected token equals frozen read metadata, and the source closed-empty-assistant token count is exactly render length+2. Assistant onset is a separate extra Oracle44/NLA42 cell, outside the original grid.
- Buggy code: bare source code as the family specifies, EOF at Oracle60 for Python /56 otherwise, plus44 and NLA42. Oracle44 EOF is the single-site arm; no assistant turn is invented.

Retain grid/single-site arm labels when one cell is reused. Never include the additional onset cells in the family-grid headline. No R3b forecast applies to E99 under §206. The integrator owns assets, measured forecasting, budget admission and launches. Contract records the registered compute-reduction order and the clarified judge-cost reduction; no reduction has been applied to this full export.

## Placebo custody

Use seed20261030 and E76's norm-matched random-vector method. Draw30 real partners without replacement in each family, in fixed order user_modeling, directed_modulation, hallucination. Each pseudo-item inherits that partner's positions/layers and the same extra onset cell when applicable. Match vector norm separately per reader/layer/position. `seed_key` is the pseudo-ID for deterministic per-cell RNG derivation under the runner's E76 implementation. PRIVATE placebo bindings join the paired original option list or response text; options and responses for judging never enter pod metadata. Freeze the runner's vector seed derivation before capture.

## Judge delivery and dependencies

First deliveries are already on shared branch: hallucination/R-WS2 at4d0fe781 and user_modeling/directed_modulation at98daa815. Their seals remain unchanged. The new `JUDGE_DEPENDENCIES.json` gives all six exact renderer interfaces, source sidecars and schema constants. Each `*_PROMPTS.json` is source-literal data. `reference_data` holds pinned prompt/judge source as `.txt` for verification only, never execution.

Agentic is THREE stages, per clarification2: `agentic_position` on original cell-level inputs with source layer formatting; `agentic_consolidate` over position descriptions; `agentic_design` over the resulting account plus targets.json. No stage is skipped. The pinned source has no API-enforced schema for these stages: A/B return text, C returns the JSON fields specified in its unchanged design prompt and original parser. Compression,60,000-character chunking, partial prompts and final merge wording are available unchanged; keep position order and reader/layer scopes explicit. Targets sidecar is the original JSON with `items[source_item.id]`. Record source refusal/failure distinctions and family accounting; do not silently turn failures into negative findings.

Buggy-code stage A is blind to program/truth. Stage B receives A's parsed claim/inferred text plus the CPU-only source program, src, verified result and cause/twin context. Original silent-floor rules and schemas are included. Jailbreak uses its original schema and marker mapping; the extra onset marker clamps to last-user-turn end while passing the actual onset token to the unchanged template.

All families use E99's registered judge route, a disclosed change from WorkspaceBench's providers. No other prompt edits or new judge rules are introduced. R-WS2's one new corroboration prompt remains frozen in `corroboration99.py`; see HEADLINE_HANDOFF for opaque claim IDs, no truth labels in that call, and joins to the original verified true/false units.

Validation: ten CPU tests (3 headline,2 MC,5 full export), all516 source items,1,123 hallucination sites,86 jailbreak position/token/count checks, all200 MC option sets, all49 buggy grading formats, all32 agentic target joins, all90 placebo structures, archive allowlist and artifact hashes. Public payload secret-marker scan found zero matches. No real readout, judgement or scientific analysis output was produced; first_output_utc is unknown for this CPU package.
