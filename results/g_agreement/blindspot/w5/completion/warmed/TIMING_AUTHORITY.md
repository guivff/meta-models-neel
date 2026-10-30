# Registered timing authority

Source commit: `08b24aeb898e2f087c4641cabf6757d16b030b95`

Verbatim BRIEF_BLINDSPOT.md amendment:

**2026-10-23 16:35 CEST (Guiv), timing gates, operations only, before any output of the affected runs:** every forecast or timing gate in this brief, and §66 in BRIEF_V, uses **warmed units**. One unscored warm-up unit runs per code path, then 3 timed units; F is extrapolated from their median. A cold first call never enters the forecast. This applies to the W5 completion (now a fresh attempt, nothing having been scored), §66, S2, W6, W10 and §84. Caps and rules are otherwise unchanged.

2026-10-24, Guiv's explicit follow-up instruction in the W-core conversation:
"one unscored warm-up, then the median of 3 timed units; cap min(1.5F + 360, 3,600) s; setup 900 s", with no other change.
The existing per-layer warm-up/median forecast, 1.5F feasibility check, population,
scorer, six captures, no-partial-reuse policy and registered §74 analysis remain
unchanged. Only the computed science deadline gains capped 360-second headroom;
the receipt, execution-source binding and archive are refreshed to those bytes.
