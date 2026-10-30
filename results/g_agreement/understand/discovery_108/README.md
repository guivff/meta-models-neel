# §108 discovery study: committed artefacts

Committed under BRIEF_UNDERSTAND §123 item 3 on 2026-10-25 (integrator). Until now §108 was "cache only".

- `runA_claude_HYPOTHESES_FROZEN.md`, `runA_claude_FROZEN_CODE_MANIFEST.json`: Run A (Claude Code) frozen rule list and frozen-code manifest.
- `runB_codex_HYPOTHESES_FROZEN.md`, `runB_codex_FROZEN_FILES.json`: Run B (Codex) frozen rule list and frozen-file manifest.
- `ARTEFACT_SEAL.json`: sha256 of the four files above, both reports, both work archives, the sealed holdout
  (`9478f103…`), the pack (`7ded7793…`) and the prompts (`929c65c9…`); the last three re-verified against §108.

Results and adopted caveats are in BRIEF_UNDERSTAND §108 (dated note, `2d2d3c66`). Only Holm-passing, red-team-surviving
rules may enter the write-up, labelled exploratory, with the number of rules tested.
