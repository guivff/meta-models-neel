RESOLVED by coordinator §172 clarification2,3ada24fb; retained historical questions below. RULE_STATUS.json is authoritative.

# E56 verdict-definition hold — before any E56 score

Authority reviewed: §172 and ownership note at e0a2e9ef. These affect measures/thresholds, so no owner reading substitutes for a ruling.

1. R2 defines a signed rate (correct-only minus wrong-only), then requires a "Wilson lower bound > 0". A Wilson interval is for a binomial proportion, not that signed difference. Which exact interval is registered, and is its independent unit the 40 items (with eight repeated greedy outputs nested within item)? Using Wilson(correct/total)>0 alone does not establish a positive signed difference.
2. Do R3 and R4's "statement rates", and the positive-control >=.30 gate, mean the same correct-only-minus-wrong-only rate as R2, or correct-value statement rate? Define how both-value statements count and the fact_recall "reported" threshold (R2's >=.20 plus interval, or another explicit threshold).
3. The positive gate names Oracle on controls7–9 but concludes "for that reader". Does each reader need >=.30 on >=2/3 controls independently, or does the Oracle control result gate both? Is fact_recall's >=1-reader condition shared?

Acquisition code and input freezes are prepared without reading outcomes. LAUNCH_REQUEST remains HELD_PENDING_RULE_CLARIFICATION; no scores should be produced until these definitions are committed. W-lens J scores and blind judgments are separately required sealed inputs to final analysis, not reasons to change the acquisition bank. No registered analysis invocation has been consumed.
