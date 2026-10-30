# E127 answer-preference diagnostic — non-executing companion

Descriptive reporting under §238 clarification 3. All probability/greedy-agreement aggregates below are **R-Q’s independently computed reviewer numbers**, transcribed from its existing review; no author adapter, guard, numerical analysis, bootstrap, native-output opening or model/judge call is invoked.

The **41/84** qualifying items are subject-model **answer-preference flips** between the frozen candidates. They are not greedy-answer flips and never reader flips. R-NAT1 and the falsifier remain **descriptive-only**, below the registered 50-item gate. Original greedy R-NAT1 remains NOT EVALUABLE (measurement).

Global-vocabulary probability mass, Q1 / median / Q3 (one original candidate pair per item; no two-candidate renormalization):

| Condition | Combined old + new candidate mass | Old candidate mass | New candidate mass |
|---|---|---|---|
| context_update | .0026532822 / .0087281399 / .0161410153 | .0010408930 / .0062102734 / .0102033163 | .0000438684 / .0004667781 / .0020030687 |
| neutral_prefix | .0011866553 / .0056866757 / .0123981029 | .0011754087 / .0056340744 / .0123976976 | .0000008823 / .0000050122 / .0000131593 |
| no_prefix | .0012905600 / .0036057815 / .0089362051 | .0012641794 / .0035633034 / .0089360655 | .0000001511 / .0000047097 / .0000253127 |

Full reviewer precision is in REPORT.json. Combined-mass quartiles describe per-item combined probabilities, rather than sums of the separate quartiles.

Preferred-candidate agreement with the subject’s greedy first token is **0/84 in each condition**. First decoded category is whitespace/newline on **84/84 per condition, 252/252 total**; no token values are printed. R-Q’s comparison uses sealed candidate IDs/greedy token IDs; independent tokenizer-ID decoding is not claimed. Relative pair preference can change even when neither candidate is the greedy first token.

§238 clarification 3 cites E109’s block-52 Oracle new-value reports on 84/84 original flipped items and E104’s judged readout changes as corroboration. These are **reader-text observations**, not direct evidence that a subject-model 32-token greedy answer changed. Reader judgments remain text-only; no circular inference is promoted into a subject-answer measurement.

Chronology: the clarification’s nominal “before deviation runs” heading postdates the actual E127 deviation guard/result. This companion is explicitly **post-deviation-result descriptive reporting**, not retrospectively pre-registered. The prior descriptive context pair-preference count was also already public. Original criteria, results, seals and both consumed guards are unchanged.

E129 is **NOT RUN (design)** under `e97f837b0`; the numerical trigger fired but the design was cancelled. This companion authorizes no acquisition, selection, launch or pooling. The control/design-confound ruling is not proof that state is absent or every readout echoes its prefix.

Exact reviewer-source Git revision and digest, original deviation seal and separate companion reporting seal accompany this note. The source is `results/g_agreement/reviews/R-Q.md`, §238 clarification-3 companion. No new statistics were computed here.
