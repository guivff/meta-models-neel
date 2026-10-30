# E71 result: judge vs Guiv's hand codes (joined after commit 8562cd524)

**R-H1 NOT MET, narrowly.** Cohen's κ (correct / wrong / other) = **0.68** [0.49, 0.85] on the 63 of 100 packet items
that have a sealed judge reference (37 E49/D4 items have none; disclosed in the packet README). Raw agreement 84%
(53/63). Oracle κ 0.68 (n 30), NLA κ 0.68 (n 33). Four-category κ 0.46.

Disagreements on "states a value": judge says stated, human does not **8/40 = 20%** [10%, 35%]; judge says not stated,
human says stated **4/23 = 17%** [7%, 37%]. False YES sit on enactment or naming rows (adjective_implicit,
rhyme_plan, linewrap_asked, language_report): the judge credits doing or naming as stating. False NO sit on
reasoning_bridge.

**Exploratory E104 spot-check (40 items, not E71).** Fact recall: 18/20 agree (κ 0.80); the two misses are the judge
crediting "Lima" on readouts about Brazil. Language plan: **6/20 agree (κ 0.08)**: the judge alternates between
silent, exhibits and states on prose written in a language, so judged language-row rates are not reliable.

Consequences for the deck: "stated" rates are judged rates with ~20% false YES and ~17% false NO against one human
coder; language and other enactment-prone rows are unreliable; fact rows are reliable; a near-zero bookkeeping or cue
rate (0/176, S ≈ 0.01) would need the judge to miss nearly every statement, which these rates do not support.
Coder: Guiv Farmanfarmaian, blind to item-level judge codes, knows the hypotheses (§188 E71 deviation 1).

## Provenance note (12:20 CET, after R-2's review c5dca5b6e)
- Script: `agreement.py` (this folder) is the exact code that produced AGREEMENT.json. Bootstrap: Python
  `random.Random(20261030)`, 2,000 item resamples, percentile 2.5/97.5 by index `int(.025·B)` and `int(.975·B)-1`,
  resamples with undefined κ dropped. R-2's [0.482, 0.846] differs only by resampling implementation; the point κ,
  counts and verdict match. Report the CI as approximately [0.48, 0.85].
- Exclusions: 63 compared = 100 − 36 with no judge reference − 1 with an UNPARSEABLE judge code (the README's
  "37 without a reference" conflated the two).
- Order: human codes committed 8562cd524; the private key was then staged from the Mac and joined; the result
  committed bae102a33. No earlier join happened, but nothing in Git can prove that; disclosed as an attestation.
