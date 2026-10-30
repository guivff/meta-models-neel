HANDOFF W4 OFF-NATIVE: NOT MET; blind-spot donor-following rule 0/16 (0%); semantic recipient-following rule 4/9 (44.44%); both below 70%. NLA swap mean AUROC donor/recipient: blind-spot 0.4378/0.5622, semantic 0.4029/0.5971. Three controls (mean recipient AUROC, blind-spot/semantic): self 0.7848/0.9691, random 0.5784/0.7199, AR-only 0.6021/0.7577.

Exact P3-approved ar_tests 73a2c2fe analyse-swaps executed once; every dependency hash matches collector provenance. Mandatory upstream analysis seal verified by w4_aggregate, executed once.40 directed pairs/row;2,000 template-cluster bootstrap draws,seed 20261023. Row-level rules determine the verdict; means below are descriptive equal-row means, without a pooled inference rule.

| Group | Arm | Mean donor AUROC | Mean recipient AUROC |
|---|---|---:|---:|
| blindspot | swap | 0.4378 | 0.5622 |
| blindspot | self | 0.2152 | 0.7848 |
| blindspot | random | 0.4216 | 0.5784 |
| blindspot | ar_only | 0.3979 | 0.6021 |
| semantic | swap | 0.4029 | 0.5971 |
| semantic | self | 0.0309 | 0.9691 |
| semantic | random | 0.2801 | 0.7199 |
| semantic | ar_only | 0.2423 | 0.7577 |

Swap score point estimates favor recipient on 10/16 blind-spot and 7/9 semantic rows; donor on 6/16 and 2/9. These counts only describe AUROC>0.5 and are not extra significance tests or the registered rule. No blind-spot row meets donor AUROC>=0.7 with cluster-CI lower bound>0.5. Four semantic rows meet recipient AUROC>=0.7: latex_subject,list_topic,prose_sentiment,python_error.

| Feature | Group | Swap donor AUROC [95% CI] | Swap recipient AUROC [95% CI] | Rule met |
|---|---|---|---|---|
| json_status | semantic | 0.9898 [0.9753, 1.0000] | 0.0102 [0.0000, 0.0247] | False |
| json_type | blindspot | 0.2727 [0.1071, 0.4304] | 0.7273 [0.5696, 0.8929] | False |
| latex_environment | blindspot | 0.3709 [0.2117, 0.5669] | 0.6291 [0.4331, 0.7883] | False |
| latex_role | semantic | 0.3914 [0.0359, 0.6267] | 0.6086 [0.3733, 0.9641] | False |
| latex_section | blindspot | 0.6212 [0.3423, 0.8288] | 0.3788 [0.1712, 0.6577] | False |
| latex_subject | semantic | 0.0833 [0.0023, 0.3098] | 0.9167 [0.6902, 0.9977] | True |
| list_depth | blindspot | 0.5775 [0.3208, 0.8204] | 0.4225 [0.1796, 0.6792] | False |
| list_index | blindspot | 0.6944 [0.3036, 0.8971] | 0.3056 [0.1029, 0.6964] | False |
| list_priority | semantic | 0.8359 [0.7041, 0.9688] | 0.1641 [0.0312, 0.2959] | False |
| list_topic | semantic | 0.2424 [0.0126, 0.5606] | 0.7576 [0.4394, 0.9874] | True |
| prose_paren | blindspot | 0.6967 [0.3750, 0.9304] | 0.3033 [0.0696, 0.6250] | False |
| prose_quote | blindspot | 0.4318 [0.1031, 0.7495] | 0.5682 [0.2505, 0.8969] | False |
| prose_sentence | blindspot | 0.2882 [0.1265, 0.4955] | 0.7118 [0.5045, 0.8735] | False |
| prose_sentiment | semantic | 0.2363 [0.0420, 0.6000] | 0.7637 [0.4000, 0.9580] | True |
| prose_topic | semantic | 0.3182 [0.0537, 0.6806] | 0.6818 [0.3194, 0.9463] | False |
| python_argument | blindspot | 0.4862 [0.2605, 0.7286] | 0.5138 [0.2714, 0.7395] | False |
| python_comment | blindspot | 0.5657 [0.4054, 0.7394] | 0.4343 [0.2606, 0.5946] | False |
| python_depth | blindspot | 0.3425 [0.0499, 0.6067] | 0.6575 [0.3933, 0.9501] | False |
| python_error | semantic | 0.1378 [0.0539, 0.2381] | 0.8622 [0.7619, 0.9461] | True |
| python_indent | blindspot | 0.5556 [0.3214, 0.7655] | 0.4444 [0.2345, 0.6786] | False |
| python_string | blindspot | 0.1374 [0.0046, 0.2632] | 0.8626 [0.7368, 0.9954] | False |
| table_column | blindspot | 0.3510 [0.1667, 0.5182] | 0.6490 [0.4818, 0.8333] | False |
| table_role | blindspot | 0.2581 [0.0428, 0.5083] | 0.7419 [0.4917, 0.9572] | False |
| table_row | blindspot | 0.3555 [0.1842, 0.5714] | 0.6445 [0.4286, 0.8158] | False |
| table_status | semantic | 0.3914 [0.2071, 0.6075] | 0.6086 [0.3925, 0.7929] | False |
