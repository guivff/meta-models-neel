# Q1/Q2 rater-1 coding results

DESCRIPTIVE. All code/input hashes and ID coverage verified before private-key joins. All required evidence quotes and normalized structure tokens are verbatim. No exclusions, recoding or new coder calls. Wilson95 intervals are per readout; repeated generations/doses are correlated. Q1 mode/mention/enact uses property-only pass A; hallucination/extra uses contextual pass B.

Producer notes:
- Q1 split into pass A (property line only) and pass B (with text) before coding, to stop coders reading truth from the text
- Some coders used scripted rules for structural cues (closing bracket, " | ") rather than per-line judgement
- q2c structure_tokens: wrapper tokens ("<", ">", "<explanation>", leading "- "/"*") removed by a truth-blind rule at merge because coders treated them inconsistently
- q1 pass B "extra" rates vary across chunks (coder strictness differs); treat as descriptive

## Whole samples

| Group | Continues | Describes | Mixed | Mention | Quotes token | States property | Correct/all mentions | Correct/resolved mentions | Enacts | Correct/all enacts | Correct/resolved enacts |
|---|---|---|---|---|---|---|---|---|---|---|
| q1 | 237/480 = 49.4% [44.9, 53.8] | 240/480 = 50.0% [45.5, 54.5] | 3/480 = 0.6% [0.2, 1.8] | 254/480 = 52.9% [48.4, 57.3] | 162/480 = 33.8% [29.7, 38.1] | 92/480 = 19.2% [15.9, 22.9] | 176/254 = 69.3% [63.4, 74.6] | 176/183 = 96.2% [92.3, 98.1] | 164/480 = 34.2% [30.1, 38.5] | 112/164 = 68.3% [60.8, 74.9] | 112/119 = 94.1% [88.4, 97.1] |
| q2a | 150/300 = 50.0% [44.4, 55.6] | 150/300 = 50.0% [44.4, 55.6] | 0/300 = 0.0% [0.0, 1.3] | 156/300 = 52.0% [46.4, 57.6] | 92/300 = 30.7% [25.7, 36.1] | 64/300 = 21.3% [17.1, 26.3] | 99/156 = 63.5% [55.7, 70.6] | 99/99 = 100.0% [96.3, 100.0] | 113/300 = 37.7% [32.4, 43.3] | 99/113 = 87.6% [80.3, 92.5] | 99/108 = 91.7% [84.9, 95.6] |
| q2b | 320/320 = 100.0% [98.8, 100.0] | 0/320 = 0.0% [0.0, 1.2] | 0/320 = 0.0% [0.0, 1.2] | 0/320 = 0.0% [0.0, 1.2] | 0/320 = 0.0% [0.0, 1.2] | 0/320 = 0.0% [0.0, 1.2] | UNAVAILABLE | UNAVAILABLE | 185/320 = 57.8% [52.3, 63.1] | UNAVAILABLE | UNAVAILABLE |
| q2c | 407/840 = 48.5% [45.1, 51.8] | 420/840 = 50.0% [46.6, 53.4] | 13/840 = 1.5% [0.9, 2.6] | 7/840 = 0.8% [0.4, 1.7] | 6/840 = 0.7% [0.3, 1.5] | 1/840 = 0.1% [0.0, 0.7] | 1/7 = 14.3% [2.6, 51.3] | 1/1 = 100.0% [20.7, 100.0] | 133/840 = 15.8% [13.5, 18.5] | 68/133 = 51.1% [42.7, 59.5] | 68/79 = 86.1% [76.8, 92.0] |

## Tier and native reader

| Group | Continues | Describes | Mixed | Mention | Quotes token | States property | Correct/all mentions | Correct/resolved mentions | Enacts | Correct/all enacts | Correct/resolved enacts |
|---|---|---|---|---|---|---|---|---|---|---|
| q1 / content / nla / 42 | 0/80 = 0.0% [0.0, 4.6] | 80/80 = 100.0% [95.4, 100.0] | 0/80 = 0.0% [0.0, 4.6] | 80/80 = 100.0% [95.4, 100.0] | 35/80 = 43.8% [33.4, 54.7] | 45/80 = 56.2% [45.3, 66.6] | 70/80 = 87.5% [78.5, 93.1] | 70/71 = 98.6% [92.4, 99.8] | 0/80 = 0.0% [0.0, 4.6] | UNAVAILABLE | UNAVAILABLE |
| q1 / content / oracle / 44 | 78/80 = 97.5% [91.3, 99.3] | 0/80 = 0.0% [0.0, 4.6] | 2/80 = 2.5% [0.7, 8.7] | 15/80 = 18.8% [11.7, 28.7] | 0/80 = 0.0% [0.0, 4.6] | 15/80 = 18.8% [11.7, 28.7] | 15/15 = 100.0% [79.6, 100.0] | 15/15 = 100.0% [79.6, 100.0] | 76/80 = 95.0% [87.8, 98.0] | 75/76 = 98.7% [92.9, 99.8] | 75/75 = 100.0% [95.1, 100.0] |
| q1 / earlier_state / nla / 42 | 0/80 = 0.0% [0.0, 4.6] | 80/80 = 100.0% [95.4, 100.0] | 0/80 = 0.0% [0.0, 4.6] | 80/80 = 100.0% [95.4, 100.0] | 65/80 = 81.2% [71.3, 88.3] | 15/80 = 18.8% [11.7, 28.7] | 20/80 = 25.0% [16.8, 35.5] | 20/23 = 87.0% [67.9, 95.5] | 0/80 = 0.0% [0.0, 4.6] | UNAVAILABLE | UNAVAILABLE |
| q1 / earlier_state / oracle / 44 | 80/80 = 100.0% [95.4, 100.0] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | UNAVAILABLE | UNAVAILABLE | 39/80 = 48.8% [38.1, 59.5] | 5/39 = 12.8% [5.6, 26.7] | 5/8 = 62.5% [30.6, 86.3] |
| q1 / local_form / nla / 42 | 0/80 = 0.0% [0.0, 4.6] | 80/80 = 100.0% [95.4, 100.0] | 0/80 = 0.0% [0.0, 4.6] | 79/80 = 98.8% [93.3, 99.8] | 62/80 = 77.5% [67.2, 85.3] | 17/80 = 21.2% [13.7, 31.4] | 71/79 = 89.9% [81.3, 94.8] | 71/74 = 95.9% [88.7, 98.6] | 0/80 = 0.0% [0.0, 4.6] | UNAVAILABLE | UNAVAILABLE |
| q1 / local_form / oracle / 44 | 79/80 = 98.8% [93.3, 99.8] | 0/80 = 0.0% [0.0, 4.6] | 1/80 = 1.2% [0.2, 6.7] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | UNAVAILABLE | UNAVAILABLE | 49/80 = 61.3% [50.3, 71.2] | 32/49 = 65.3% [51.3, 77.1] | 32/36 = 88.9% [74.7, 95.6] |
| q2a / content / nla / 42 | 0/150 = 0.0% [0.0, 2.5] | 150/150 = 100.0% [97.5, 100.0] | 0/150 = 0.0% [0.0, 2.5] | 150/150 = 100.0% [97.5, 100.0] | 92/150 = 61.3% [53.3, 68.8] | 58/150 = 38.7% [31.2, 46.7] | 93/150 = 62.0% [54.0, 69.4] | 93/93 = 100.0% [96.0, 100.0] | 0/150 = 0.0% [0.0, 2.5] | UNAVAILABLE | UNAVAILABLE |
| q2a / content / oracle / 44 | 150/150 = 100.0% [97.5, 100.0] | 0/150 = 0.0% [0.0, 2.5] | 0/150 = 0.0% [0.0, 2.5] | 6/150 = 4.0% [1.8, 8.5] | 0/150 = 0.0% [0.0, 2.5] | 6/150 = 4.0% [1.8, 8.5] | 6/6 = 100.0% [61.0, 100.0] | 6/6 = 100.0% [61.0, 100.0] | 113/150 = 75.3% [67.9, 81.5] | 99/113 = 87.6% [80.3, 92.5] | 99/108 = 91.7% [84.9, 95.6] |
| q2b / earlier_state / oracle / 44 | 320/320 = 100.0% [98.8, 100.0] | 0/320 = 0.0% [0.0, 1.2] | 0/320 = 0.0% [0.0, 1.2] | 0/320 = 0.0% [0.0, 1.2] | 0/320 = 0.0% [0.0, 1.2] | 0/320 = 0.0% [0.0, 1.2] | UNAVAILABLE | UNAVAILABLE | 185/320 = 57.8% [52.3, 63.1] | UNAVAILABLE | UNAVAILABLE |
| q2c / earlier_state / nla / 42 | 0/168 = 0.0% [0.0, 2.2] | 168/168 = 100.0% [97.8, 100.0] | 0/168 = 0.0% [0.0, 2.2] | 2/168 = 1.2% [0.3, 4.2] | 2/168 = 1.2% [0.3, 4.2] | 0/168 = 0.0% [0.0, 2.2] | 1/2 = 50.0% [9.5, 90.5] | 1/1 = 100.0% [20.7, 100.0] | 0/168 = 0.0% [0.0, 2.2] | UNAVAILABLE | UNAVAILABLE |
| q2c / earlier_state / oracle / 44 | 163/168 = 97.0% [93.2, 98.7] | 0/168 = 0.0% [0.0, 2.2] | 5/168 = 3.0% [1.3, 6.8] | 0/168 = 0.0% [0.0, 2.2] | 0/168 = 0.0% [0.0, 2.2] | 0/168 = 0.0% [0.0, 2.2] | UNAVAILABLE | UNAVAILABLE | 78/168 = 46.4% [39.1, 54.0] | 14/78 = 17.9% [11.0, 27.9] | 14/25 = 56.0% [37.1, 73.3] |
| q2c / local_form / nla / 42 | 0/84 = 0.0% [0.0, 4.4] | 84/84 = 100.0% [95.6, 100.0] | 0/84 = 0.0% [0.0, 4.4] | 1/84 = 1.2% [0.2, 6.4] | 1/84 = 1.2% [0.2, 6.4] | 0/84 = 0.0% [0.0, 4.4] | 0/1 = 0.0% [0.0, 79.3] | UNAVAILABLE | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE |
| q2c / local_form / oracle / 44 | 79/84 = 94.0% [86.8, 97.4] | 0/84 = 0.0% [0.0, 4.4] | 5/84 = 6.0% [2.6, 13.2] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE | 55/84 = 65.5% [54.8, 74.8] | 54/55 = 98.2% [90.4, 99.7] | 54/54 = 100.0% [93.4, 100.0] |
| q2c / unassigned_by_Q1 / nla / 42 | 0/168 = 0.0% [0.0, 2.2] | 168/168 = 100.0% [97.8, 100.0] | 0/168 = 0.0% [0.0, 2.2] | 4/168 = 2.4% [0.9, 6.0] | 3/168 = 1.8% [0.6, 5.1] | 1/168 = 0.6% [0.1, 3.3] | 0/4 = 0.0% [0.0, 49.0] | UNAVAILABLE | 0/168 = 0.0% [0.0, 2.2] | UNAVAILABLE | UNAVAILABLE |
| q2c / unassigned_by_Q1 / oracle / 44 | 165/168 = 98.2% [94.9, 99.4] | 0/168 = 0.0% [0.0, 2.2] | 3/168 = 1.8% [0.6, 5.1] | 0/168 = 0.0% [0.0, 2.2] | 0/168 = 0.0% [0.0, 2.2] | 0/168 = 0.0% [0.0, 2.2] | UNAVAILABLE | UNAVAILABLE | 0/168 = 0.0% [0.0, 2.2] | UNAVAILABLE | UNAVAILABLE |

## Q2 rows and native reader

| Group | Continues | Describes | Mixed | Mention | Quotes token | States property | Correct/all mentions | Correct/resolved mentions | Enacts | Correct/all enacts | Correct/resolved enacts |
|---|---|---|---|---|---|---|---|---|---|---|
| q2a / latex_subject / nla / 42 | 0/50 = 0.0% [0.0, 7.1] | 50/50 = 100.0% [92.9, 100.0] | 0/50 = 0.0% [0.0, 7.1] | 50/50 = 100.0% [92.9, 100.0] | 17/50 = 34.0% [22.4, 47.8] | 33/50 = 66.0% [52.2, 77.6] | 43/50 = 86.0% [73.8, 93.0] | 43/43 = 100.0% [91.8, 100.0] | 0/50 = 0.0% [0.0, 7.1] | UNAVAILABLE | UNAVAILABLE |
| q2a / latex_subject / oracle / 44 | 50/50 = 100.0% [92.9, 100.0] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | 6/50 = 12.0% [5.6, 23.8] | 0/50 = 0.0% [0.0, 7.1] | 6/50 = 12.0% [5.6, 23.8] | 6/6 = 100.0% [61.0, 100.0] | 6/6 = 100.0% [61.0, 100.0] | 45/50 = 90.0% [78.6, 95.7] | 45/45 = 100.0% [92.1, 100.0] | 45/45 = 100.0% [92.1, 100.0] |
| q2a / prose_sentiment / nla / 42 | 0/50 = 0.0% [0.0, 7.1] | 50/50 = 100.0% [92.9, 100.0] | 0/50 = 0.0% [0.0, 7.1] | 50/50 = 100.0% [92.9, 100.0] | 25/50 = 50.0% [36.6, 63.4] | 25/50 = 50.0% [36.6, 63.4] | 50/50 = 100.0% [92.9, 100.0] | 50/50 = 100.0% [92.9, 100.0] | 0/50 = 0.0% [0.0, 7.1] | UNAVAILABLE | UNAVAILABLE |
| q2a / prose_sentiment / oracle / 44 | 50/50 = 100.0% [92.9, 100.0] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | UNAVAILABLE | UNAVAILABLE | 50/50 = 100.0% [92.9, 100.0] | 50/50 = 100.0% [92.9, 100.0] | 50/50 = 100.0% [92.9, 100.0] |
| q2a / python_effect / nla / 42 | 0/50 = 0.0% [0.0, 7.1] | 50/50 = 100.0% [92.9, 100.0] | 0/50 = 0.0% [0.0, 7.1] | 50/50 = 100.0% [92.9, 100.0] | 50/50 = 100.0% [92.9, 100.0] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | UNAVAILABLE | 0/50 = 0.0% [0.0, 7.1] | UNAVAILABLE | UNAVAILABLE |
| q2a / python_effect / oracle / 44 | 50/50 = 100.0% [92.9, 100.0] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | 0/50 = 0.0% [0.0, 7.1] | UNAVAILABLE | UNAVAILABLE | 18/50 = 36.0% [24.1, 49.9] | 4/18 = 22.2% [9.0, 45.2] | 4/13 = 30.8% [12.7, 57.6] |
| q2b / prose_paren / oracle / 44 | 160/160 = 100.0% [97.7, 100.0] | 0/160 = 0.0% [0.0, 2.3] | 0/160 = 0.0% [0.0, 2.3] | 0/160 = 0.0% [0.0, 2.3] | 0/160 = 0.0% [0.0, 2.3] | 0/160 = 0.0% [0.0, 2.3] | UNAVAILABLE | UNAVAILABLE | 32/160 = 20.0% [14.5, 26.9] | UNAVAILABLE | UNAVAILABLE |
| q2b / table_column / oracle / 44 | 160/160 = 100.0% [97.7, 100.0] | 0/160 = 0.0% [0.0, 2.3] | 0/160 = 0.0% [0.0, 2.3] | 0/160 = 0.0% [0.0, 2.3] | 0/160 = 0.0% [0.0, 2.3] | 0/160 = 0.0% [0.0, 2.3] | UNAVAILABLE | UNAVAILABLE | 153/160 = 95.6% [91.2, 97.9] | UNAVAILABLE | UNAVAILABLE |
| q2c / list_depth / nla / 42 | 0/84 = 0.0% [0.0, 4.4] | 84/84 = 100.0% [95.6, 100.0] | 0/84 = 0.0% [0.0, 4.4] | 3/84 = 3.6% [1.2, 10.0] | 3/84 = 3.6% [1.2, 10.0] | 0/84 = 0.0% [0.0, 4.4] | 0/3 = 0.0% [0.0, 56.2] | UNAVAILABLE | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE |
| q2c / list_depth / oracle / 44 | 82/84 = 97.6% [91.7, 99.3] | 0/84 = 0.0% [0.0, 4.4] | 2/84 = 2.4% [0.7, 8.3] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE |
| q2c / prose_paren / nla / 42 | 0/84 = 0.0% [0.0, 4.4] | 84/84 = 100.0% [95.6, 100.0] | 0/84 = 0.0% [0.0, 4.4] | 2/84 = 2.4% [0.7, 8.3] | 2/84 = 2.4% [0.7, 8.3] | 0/84 = 0.0% [0.0, 4.4] | 1/2 = 50.0% [9.5, 90.5] | 1/1 = 100.0% [20.7, 100.0] | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE |
| q2c / prose_paren / oracle / 44 | 84/84 = 100.0% [95.6, 100.0] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE | 13/84 = 15.5% [9.3, 24.7] | 5/13 = 38.5% [17.7, 64.5] | 5/13 = 38.5% [17.7, 64.5] |
| q2c / python_indent / nla / 42 | 0/84 = 0.0% [0.0, 4.4] | 84/84 = 100.0% [95.6, 100.0] | 0/84 = 0.0% [0.0, 4.4] | 1/84 = 1.2% [0.2, 6.4] | 0/84 = 0.0% [0.0, 4.4] | 1/84 = 1.2% [0.2, 6.4] | 0/1 = 0.0% [0.0, 79.3] | UNAVAILABLE | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE |
| q2c / python_indent / oracle / 44 | 83/84 = 98.8% [93.6, 99.8] | 0/84 = 0.0% [0.0, 4.4] | 1/84 = 1.2% [0.2, 6.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE |
| q2c / python_string / nla / 42 | 0/84 = 0.0% [0.0, 4.4] | 84/84 = 100.0% [95.6, 100.0] | 0/84 = 0.0% [0.0, 4.4] | 1/84 = 1.2% [0.2, 6.4] | 1/84 = 1.2% [0.2, 6.4] | 0/84 = 0.0% [0.0, 4.4] | 0/1 = 0.0% [0.0, 79.3] | UNAVAILABLE | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE |
| q2c / python_string / oracle / 44 | 79/84 = 94.0% [86.8, 97.4] | 0/84 = 0.0% [0.0, 4.4] | 5/84 = 6.0% [2.6, 13.2] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE | 55/84 = 65.5% [54.8, 74.8] | 54/55 = 98.2% [90.4, 99.7] | 54/54 = 100.0% [93.4, 100.0] |
| q2c / table_column / nla / 42 | 0/84 = 0.0% [0.0, 4.4] | 84/84 = 100.0% [95.6, 100.0] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE |
| q2c / table_column / oracle / 44 | 79/84 = 94.0% [86.8, 97.4] | 0/84 = 0.0% [0.0, 4.4] | 5/84 = 6.0% [2.6, 13.2] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | 0/84 = 0.0% [0.0, 4.4] | UNAVAILABLE | UNAVAILABLE | 65/84 = 77.4% [67.4, 85.0] | 9/65 = 13.8% [7.5, 24.3] | 9/12 = 75.0% [46.8, 91.1] |

## Q2b by dose

| Group | Continues | Describes | Mixed | Mention | Quotes token | States property | Correct/all mentions | Correct/resolved mentions | Enacts | Correct/all enacts | Correct/resolved enacts |
|---|---|---|---|---|---|---|---|---|---|---|
| q2b / 0.0 / oracle / 44 | 80/80 = 100.0% [95.4, 100.0] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | 0/80 = 0.0% [0.0, 4.6] | UNAVAILABLE | UNAVAILABLE | 36/80 = 45.0% [34.6, 55.9] | 0/36 = 0.0% [0.0, 9.6] | UNAVAILABLE |
| q2b / 1.0 / oracle / 44 | 48/48 = 100.0% [92.6, 100.0] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | UNAVAILABLE | UNAVAILABLE | 22/48 = 45.8% [32.6, 59.7] | UNAVAILABLE | UNAVAILABLE |
| q2b / 2.0 / oracle / 44 | 48/48 = 100.0% [92.6, 100.0] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | UNAVAILABLE | UNAVAILABLE | 23/48 = 47.9% [34.5, 61.7] | UNAVAILABLE | UNAVAILABLE |
| q2b / 4.0 / oracle / 44 | 48/48 = 100.0% [92.6, 100.0] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | UNAVAILABLE | UNAVAILABLE | 24/48 = 50.0% [36.4, 63.6] | UNAVAILABLE | UNAVAILABLE |
| q2b / 8.0 / oracle / 44 | 48/48 = 100.0% [92.6, 100.0] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | UNAVAILABLE | UNAVAILABLE | 32/48 = 66.7% [52.5, 78.3] | UNAVAILABLE | UNAVAILABLE |
| q2b / 16.0 / oracle / 44 | 48/48 = 100.0% [92.6, 100.0] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | 0/48 = 0.0% [0.0, 7.4] | UNAVAILABLE | UNAVAILABLE | 48/48 = 100.0% [92.6, 100.0] | UNAVAILABLE | UNAVAILABLE |

## Q1 contextual pass B

| Tier / reader | Hallucination | Extra |
|---|---|---|
| content / nla L42 | 80/80 = 100.0% [95.4, 100.0] | 75/80 = 93.8% [86.2, 97.3] |
| content / oracle L44 | 6/80 = 7.5% [3.5, 15.4] | 28/80 = 35.0% [25.5, 45.9] |
| earlier_state / nla L42 | 80/80 = 100.0% [95.4, 100.0] | 72/80 = 90.0% [81.5, 94.8] |
| earlier_state / oracle L44 | 0/80 = 0.0% [0.0, 4.6] | 21/80 = 26.2% [17.9, 36.8] |
| local_form / nla L42 | 80/80 = 100.0% [95.4, 100.0] | 49/80 = 61.3% [50.3, 71.2] |
| local_form / oracle L44 | 0/80 = 0.0% [0.0, 4.6] | 23/80 = 28.7% [20.0, 39.5] |

## Q2b named structure and enactment references

Nonzero-dose edited-state truth is not independently observed, so accuracy there is unavailable. Dose0 accuracy uses source truth B. Source-B agreement and target-A alignment below are reference matches, not edited-state accuracy.

| Dose | Structure named | Enactments | Source-B agreement among enacts | Target-A alignment among enacts | Target-A alignment among resolved enacts |
|---|---|---|---|---|---|
| 0.0 | 0/80 = 0.0% [0.0, 4.6] | 36/80 = 45.0% [34.6, 55.9] | 0/36 = 0.0% [0.0, 9.6] | 0/36 = 0.0% [0.0, 9.6] | UNAVAILABLE |
| 1.0 | 0/48 = 0.0% [0.0, 7.4] | 22/48 = 45.8% [32.6, 59.7] | 0/22 = 0.0% [0.0, 14.9] | 0/22 = 0.0% [0.0, 14.9] | UNAVAILABLE |
| 2.0 | 0/48 = 0.0% [0.0, 7.4] | 23/48 = 47.9% [34.5, 61.7] | 0/23 = 0.0% [0.0, 14.3] | 0/23 = 0.0% [0.0, 14.3] | UNAVAILABLE |
| 4.0 | 0/48 = 0.0% [0.0, 7.4] | 24/48 = 50.0% [36.4, 63.6] | 0/24 = 0.0% [0.0, 13.8] | 0/24 = 0.0% [0.0, 13.8] | UNAVAILABLE |
| 8.0 | 0/48 = 0.0% [0.0, 7.4] | 32/48 = 66.7% [52.5, 78.3] | 0/32 = 0.0% [0.0, 10.7] | 8/32 = 25.0% [13.3, 42.1] | 8/8 = 100.0% [67.6, 100.0] |
| 16.0 | 0/48 = 0.0% [0.0, 7.4] | 48/48 = 100.0% [92.6, 100.0] | 0/48 = 0.0% [0.0, 7.4] | 24/48 = 50.0% [36.4, 63.6] | 24/24 = 100.0% [86.2, 100.0] |

## Q2c normalized structure-token rate

A/B mean each row’s frozen first/second value, not a global presence/absence. Structure event = nonempty producer-normalized structure_tokens; no extra filtering.

| Reader / row / true value | Any structure token |
|---|---|
| nla / A | 0/210 = 0.0% [0.0, 1.8] |
| nla / B | 0/210 = 0.0% [0.0, 1.8] |
| oracle / A | 122/210 = 58.1% [51.3, 64.6] |
| oracle / B | 115/210 = 54.8% [48.0, 61.3] |
| nla / list_depth / A / shallow | 0/42 = 0.0% [0.0, 8.4] |
| nla / list_depth / B / deep | 0/42 = 0.0% [0.0, 8.4] |
| oracle / list_depth / A / shallow | 9/42 = 21.4% [11.7, 35.9] |
| oracle / list_depth / B / deep | 15/42 = 35.7% [23.0, 50.8] |
| nla / prose_paren / A / inside | 0/42 = 0.0% [0.0, 8.4] |
| nla / prose_paren / B / outside | 0/42 = 0.0% [0.0, 8.4] |
| oracle / prose_paren / A / inside | 3/42 = 7.1% [2.5, 19.0] |
| oracle / prose_paren / B / outside | 6/42 = 14.3% [6.7, 27.8] |
| nla / python_indent / A / shallow | 0/42 = 0.0% [0.0, 8.4] |
| nla / python_indent / B / deep | 0/42 = 0.0% [0.0, 8.4] |
| oracle / python_indent / A / shallow | 29/42 = 69.0% [54.0, 80.9] |
| oracle / python_indent / B / deep | 33/42 = 78.6% [64.1, 88.3] |
| nla / python_string / A / inside | 0/42 = 0.0% [0.0, 8.4] |
| nla / python_string / B / outside | 0/42 = 0.0% [0.0, 8.4] |
| oracle / python_string / A / inside | 42/42 = 100.0% [91.6, 100.0] |
| oracle / python_string / B / outside | 23/42 = 54.8% [39.9, 68.8] |
| nla / table_column / A / first | 0/42 = 0.0% [0.0, 8.4] |
| nla / table_column / B / later | 0/42 = 0.0% [0.0, 8.4] |
| oracle / table_column / A / first | 39/42 = 92.9% [81.0, 97.5] |
| oracle / table_column / B / later | 38/42 = 90.5% [77.9, 96.2] |

## Denominators and availability

Unclear values stay in correct/all-mention or enactment denominators; resolved accuracy excludes unclear. Zero denominator is unavailable, not zero accuracy. Mention-kind rates use all readouts; composition and subtype-specific accuracies are also in JSON. Q2c python_indent/list_depth are unassigned by Q1 tiers and retain separate row results. Q2b row-by-dose metrics are in JSON. No registered verdict is changed.

Rater2 codes were not present at preflight; Cohen’s κ is pending, not zero. Gallery is selected after these tables under the clarified b51c7915 rule, separately sealed.
