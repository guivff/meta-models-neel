# E134 §242 CPU-only policy evaluation

Authority: ab13617643e091a96ea6702fabdb268143a6192d and direct Guiv assignment.
The CPU policy/matcher suite has 22 synthetic tests. No real E134 scoring, selection,
claim or E133 output access has occurred. Labels remain local CPU only.

Policies are label-free scalar functions of the ordered available 44/52/60 readings:
P44/P52/P60; PALL majority (ties latest); PLATE latest stated value;
PSTAB earliest consecutive available-layer agreement, otherwise latest stated value;
PAGREE abstains unless all layers stating values agree. No-value assertions use None;
unavailable layers are omitted, counted separately and never manufactured.

Accepted implementation conventions: accuracy and
false claims use all eligible items (abstentions count as neither correct nor wrong);
coverage uses the same denominator; unavailable fixed-layer cells reported separately.
Selection uses equally weighted state-type accuracy, ties in registration order.
Bootstrap: 2000 item draws, seed20261030, percentile95; Wilson95 uses normal97.5%.
LOTO training excludes the held-out type; T7 never participates in any selection.

Source normalization must be separately bound and tested BEFORE real scoring.
Do not invent scalar values from boolean hits, turn a dual-value judgment into an
exclusive answer, equate silence with explicit negative evaluation cue, or borrow
truth from the readout. Existing analysis statistics/guards must never be replayed.
Actual per-item multi-layer values and behaviour-grounded truth require exact original
sealed pointers. Missing source semantics stay unresolved until authorized.

Freeze the all-T1–T6 adaptive choice in a committed SELECTION_SEAL before any E133
output opens. T7 needs its own committed final input plan and exclusive once guard;
compare that frozen policy against P44/P52/P60 once, within1h of E133 seal, or mark
exploratory-only if E133 does not seal by18:00CET. No model, GPU or paid calls.

Direct Guiv conventions: dual values
abstain; accuracy and false claims use eligible-item denominators, except T6
accuracy uses told items only. T6 eval_mention=false abstains; coverage and false
claims retain all eligible T6 items. Fixed layers with no eligible observations
are NOT EVALUABLE; selection considers only candidates evaluable on every training
type, without averaging across different sets of types.

75cf9b82d item 4 authorizes matcher.py: all original candidate names and registered
aliases, case-insensitive Unicode whole-word literal matches, with escaped text
and no invented aliases. Aliases of one candidate count once; matches to two or
more identities abstain as dual; no match abstains as no value. No truth enters
matching. Commit this matcher and its tests before any E134 score, then never
change it. The final source plan must pin the original name/alias inventory.
Report no-value/single/dual counts and exact-one coverage at each compared block.
If any block has <70% exact-one coverage, PAGREE/PSTAB are NOT EVALUABLE on T4;
LOTO and final selection exclude T4 entirely and disclose the five-type scope.
The other T4 rule scores remain descriptive. Exactly 70% passes.

Current synthetic suite: 22 tests passed. No real score or selection yet.

ff005a9c7 truth hierarchy supersedes pending unhooked-truth wording: W-text
supplies the original E132 endpoint-B category catalog and registered aliases.
For fact84 unhooked, await COMPLETE E131 unhooked64 greedy parse_target_answer,
then same-pass pair-logit preference only when the parser states no unique value.
Pair ties remain missing truth with an explicit audit. No R-4 review wait.
Before12:00CET no old_value fallback; if E131 has not sealed by12:00CET, use
registered old_value marked exactly "label-based, not behaviour-verified".
Late E131 cannot replace that frozen fallback/selection. Language50 unhooked
uses old_value with that same label now. Every rule score (including held-out
LOTO scores) carries separate truth-basis scores and a mixed-scope disclosure;
selection retains the registered equal-type mean, with T3 mixture disclosed.
Missing truth/invalid normalized grids are rejected BEFORE the phase once guard.
29synthetic tests PASS; real E134 scores/selection/E133 access remain absent.
