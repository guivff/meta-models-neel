# E88 CPU artefact audit

Status: CPU items1–4 sealed with measure qualifications below; items5/6 await sealed external judgments. Original bank verdicts unchanged.

CPU statistics ran once in 57.528s, GPU0. Eight synthetic tests passed. One pre-statistics E54 schema failure was preserved; continuation used the original claim without resetting it. See PRESTAT_SCHEMA_REPAIR.json.

## Sign conventions

Only low probe: E57 focus_ignore, AUROC0.0017006803. Generator labels, dev-fit class1 logits and test AUROC use the same orientation. No code-level sign reversal found; retain the low AUROC rather than invert it. SIGN_TRACE.json binds the exact source code.

## UNPARSEABLE sensitivity

Lower bound codes every unparseable readout wrong-only (-1); upper codes it correct-only (+1). Other codes are unchanged. Each bound reports signed S and a 2000-draw item bootstrap. The following nine row/reader cells cross the descriptive S>=0.20 and lower95>0 threshold. These are sensitivity flags before probe gates; they do not assert that the full registered bank rule or its sealed verdict flips.

| Bank | Reader | Row | Missing | Lower S | Upper S |
|---|---|---|---:|---:|---:|
| E56 | oracle | adjective_implicit | 13 | 0.059524 | 0.369048 |
| E59 | oracle | decline_plan | 5 | 0.166667 | 0.285714 |
| E62 | oracle | S3_L1 | 2 | 0.166667 | 0.214286 |
| E62 | oracle | S5_L1 | 4 | 0.119048 | 0.214286 |
| E73 | nla | W1 | 15 | 0.075000 | 0.225000 |
| E73 | oracle | W1 | 34 | -0.110000 | 0.230000 |
| E73 | oracle | W2 | 35 | -0.140000 | 0.210000 |
| E73 | oracle | W4 | 36 | -0.160000 | 0.200000 |
| E73 | oracle | W7 | 101 | -0.070000 | 0.940000 |

## Dev/test near-duplicates

Exact Unicode-codepoint Levenshtein/max-length <0.1 after NFKC/casefold/whitespace normalization, over every within-bank dev×test pair. These are shared prompt-form findings, not proof of outcome leakage.

| Bank | Dev | Test | Near pairs | Test items with a near match |
|---|---:|---:|---:|---:|
| E49 | 1344 | 1344 | 6616 | 642 |
| E54 | 168 | 168 | 0 | 0 |
| E56 | 1092 | 1092 | 6738 | 252 |
| E57 | 1680 | 1680 | 14144 | 688 |
| E59 | 504 | 504 | 0 | 0 |
| E62 | 2100 | 2520 | 21435 | 582 |
| E73 | 2716 | 2716 | 3 | 2 |

## Read-token sample

All984 sampled items match registered index, decoded token and frozen input token IDs. Evidence is sealed capture metadata/order plus the frozen capture implementation; E62 additionally has per-item POSITIONS.json. This is a code-and-custody audit, not an independent recapture. E73 block42 token255 and block44 all-position capture are explicitly bound to operator provenance.

## Coverage and qualifications

E49/E54/E56/E57/E59/E62/E73 original banks are included. E67 is a readout/claim-judging bank and E75 a derived forecast analysis: neither creates a new prompt/probe/capture population or a native-S rule. They inherit source-bank leakage/token checks; all1996 E67 terminal records (both waves, matched and mismatched) are parseable. E75 original included/excluded units and claim remain sealed.

BINARY_BOUNDS_VIEW.json is the presentation-only A/B view, excluding these nonbinary entries and appending the disjoint controls without recomputing statistics. The generic signed table contains E57 variant contrasts for focus_none, capacity_list and category_switch. They are **not registered A/B measures** and must not be used as native-S verdicts; no sensitivity flag above comes from them. E62 S6 eval-mention records (420) have no signed A/B measure and are omitted. E56 injection-direction controls (72), omitted by the initial text-bank loader, are covered separately by CONTROL_COMPLETION.json under a distinct once-only scope: all72 join to the frozen direction A/B labels. They have no token or dev/test prompt split of their own. No prior CPU audit cell was repeated. The core result is retained unchanged; the supplement completes this coverage.

## Judging pending

Item5: frozen uniform300-readout sample from E49/E57/E73, seed20261028. Original §172 rubric, explicit second-judge route via Track Q/W-internals. E49 baseline is a frozen regex, not a first judge model: agreement must identify that difference.

Item6: 3024 E49/E54 readouts, full detector inventory, §172 plus §202 clauses; Track Q owns judging, W-lens owns analysis. No API dispatch or spend by W-lens. JUDGING_REQUEST.json binds private local blind packet and rubric files; no true labels or primary codes are in the wire. Results will be added under separate exclusive judging-analysis claims only after terminal seals.
