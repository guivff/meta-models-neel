# E31(i) dated clarification 1 — 2026-10-25

User confirmation and published authority: §126 dated clarification 1,
commit `514ff4e6`, before any E31 classifier fit or stratum score.

> “The last 4 tokens before the read position” means the last 4 tokens of the
> stored prefix, including the read token itself (`ids[-4:]`). The activation
> being read is computed at the read token, so the read token is part of the
> local cue the lens could be using; excluding it would understate the local-cue
> account.

The single E31(i) protocol therefore uses `suffix_slice = include_read` and
`ids[-4:]`. This resolves the pending boundary in PLAN_2026-10-25.md. No
exclude-read-token arm is computed. All other dated implementation details remain
as specified before fitting or outcome analysis.
