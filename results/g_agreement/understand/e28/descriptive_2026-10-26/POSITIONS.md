# E28 positions — 2026-10-26

Descriptive projection of sealed checkpoint AUROCs and existing 95% template-cluster CIs. No new inference or registered-analysis invocation. Both position rows are fast in L under the existing ≥0.80 by step≤100 and CI lower≥0.65 definition. Neither position row had a shuffled S arm, so this does not establish the new E39 interpretable-row criterion.

| Row | Arm | Step | AUROC | 95% CI |
|---|---|---:|---:|---|
| python_depth | L | 0 | 0.4870 | [0.4444, 0.5266] |
| python_depth | L | 25 | 0.7670 | [0.7217, 0.8101] |
| python_depth | L | 50 | 0.9252 | [0.9048, 0.9580] |
| python_depth | L | 100 | 0.9960 | [0.9864, 1.0000] |
| python_depth | L | 200 | 1.0000 | [1.0000, 1.0000] |
| python_depth | L | 400 | 1.0000 | [1.0000, 1.0000] |
| python_depth | B | 0 | 0.5266 | [0.4949, 0.5629] |
| python_depth | B | 25 | 0.4989 | [0.4546, 0.5368] |
| python_depth | B | 50 | 0.4963 | [0.4702, 0.5232] |
| python_depth | B | 100 | 0.5910 | [0.5232, 0.6806] |
| python_depth | B | 200 | 0.6896 | [0.6173, 0.7545] |
| python_depth | B | 400 | 1.0000 | [1.0000, 1.0000] |
| table_column | L | 0 | 0.4807 | [0.3367, 0.6146] |
| table_column | L | 25 | 0.9824 | [0.9677, 1.0000] |
| table_column | L | 50 | 1.0000 | [1.0000, 1.0000] |
| table_column | L | 100 | 1.0000 | [1.0000, 1.0000] |
| table_column | L | 200 | 1.0000 | [1.0000, 1.0000] |
| table_column | L | 400 | 1.0000 | [1.0000, 1.0000] |
| table_column | B | 0 | 0.5074 | [0.3549, 0.6457] |
| table_column | B | 25 | 0.6718 | [0.6139, 0.7330] |
| table_column | B | 50 | 0.7381 | [0.6751, 0.8265] |
| table_column | B | 100 | 0.9439 | [0.9291, 0.9841] |
| table_column | B | 200 | 0.9989 | [0.9955, 1.0000] |
| table_column | B | 400 | 0.9989 | [0.9955, 1.0000] |

- Python depth: L first crosses 0.80 at step 50 (0.9252, CI [0.9048, 0.9580]); B at step 400. L is fast; B is not.
- Table column: L first crosses at step 25 (0.9824, CI [0.9677, 1.0000]); B at step 100. Both are fast.
- At step 400, L/B depth AUROC is 1.0000/1.0000; L/B column is 1.0000/0.9989.

These descriptive results do not alter the sealed R1/R2/R3 verdicts.
