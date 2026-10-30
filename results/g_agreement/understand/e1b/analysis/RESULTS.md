**Prediction (§102):** Continuation-revealing structure rows and meaning rows have high window ceiling and AR fidelity; non-revealing count rows have low values on both. Oracle remains low on the revealing structure rows.

**Assessment: the prediction partly held.** Continuation AR projection AUROC is high on `python_string` (1.000), `table_role` (0.966) and `prose_paren` (0.833), where the Oracle W1 AUROCs are 0.644, 0.438 and 0.485. But the registered revealing group is mixed: the window model is near chance on `prose_quote` (0.556) and `python_indent` (0.465), while their AR AUROCs are 0.610 and 0.881. The predicted non-revealing rows are also mixed: AR AUROC is 0.575 for `list_index` and 0.536 for `latex_section`, but 0.694 for `prose_sentence` and 0.752 for `table_row`; the window AUROC for `latex_section` is 0.851. Most meaning rows have high AR AUROC, with a clear exception at `table_status` (0.528; window 0.487), and `prose_sentiment` has high AR AUROC (0.930) despite a weak window model (0.528). Thus the clean two-group window/AR pattern did not hold. The fitted character model is a restricted baseline; a stronger AR than that model does not establish information beyond the continuation. All 25 rows and their frozen CIs follow; no new high/low threshold is used.

EXPLORATORY. Primary AR metric is test projection AUROC (§102 04:50 CEST amendment); gap fidelity is secondary. Window model: character 1–4-gram TF–IDF, L2 logistic C=1, fixed dev templates only; no test tuning. This is a model-specific text predictability baseline, not an information-theoretic ceiling. Prefix and description fidelity are the unchanged sealed E1 values. Their projection AUROCs were added after seeing E1 results.

| Row | Class | Window AUROC [95% CI] | AR continuation projection AUROC — PRIMARY [95% CI] | AR continuation fidelity — SECONDARY [95% CI] | AR on prefix fidelity | AR description fidelity | Oracle W1 AUROC |
|---|---|---|---|---|---:|---:|---:|
| json_status | semantic | 0.9807 [0.9609, 0.9977] | 0.9881 [0.9660, 1.0000] | 0.2629 [0.2316, 0.2946] | 0.015570924729034341 | 0.05520388243790299 | 1.0 |
| json_type | state-like | 0.9546 [0.9229, 0.9892] | 0.9779 [0.9393, 1.0000] | 0.5242 [0.4626, 0.5846] | 0.005597787600595812 | 0.008464311730748374 | 0.6598639455782312 |
| latex_environment | state-like | 0.9824 [0.9167, 1.0000] | 0.6808 [0.5397, 0.8458] | 0.7622 [0.3140, 1.2139] | 0.1598103560612243 | -0.1392108361802017 | 0.5708616780045351 |
| latex_role | semantic | 0.7891 [0.5181, 1.0000] | 0.8917 [0.7006, 1.0000] | 0.3663 [0.2819, 0.4434] | 0.08263118540249922 | 0.04783702598822612 | 0.8435374149659864 |
| latex_section | count-like | 0.8506 [0.7744, 0.9580] | 0.5360 [0.4260, 0.6516] | 0.0195 [-0.0491, 0.0871] | -0.07581950214935713 | 0.0032507180580544697 | 0.43253968253968256 |
| latex_subject | semantic | 0.8022 [0.6734, 0.9416] | 0.9461 [0.7993, 1.0000] | 0.6076 [0.4774, 0.7442] | 0.05964742109691938 | -0.04775321157846723 | 1.0 |
| list_depth | count-like | 0.7392 [0.6259, 0.8549] | 0.6230 [0.4489, 0.7976] | 0.1209 [0.0235, 0.2263] | -0.0769596516478158 | 0.041671733525089336 | 0.6337868480725624 |
| list_index | count-like | 0.6298 [0.5278, 0.7469] | 0.5754 [0.3993, 0.7234] | 0.0783 [-0.0617, 0.2206] | 0.011654028297521104 | 0.07942796951876178 | 0.4189342403628118 |
| list_priority | semantic | 0.7954 [0.6110, 0.9412] | 0.9700 [0.9371, 0.9966] | 0.4075 [0.3412, 0.4724] | 0.0031270235840354997 | 0.05115996631448752 | 0.8905895691609977 |
| list_topic | semantic | 0.9376 [0.8061, 0.9853] | 1.0000 [1.0000, 1.0000] | 1.6689 [1.5406, 1.7927] | 0.15292551831346274 | 0.11562629545791205 | 0.967687074829932 |
| prose_paren | state-like | 0.6528 [0.5331, 0.8645] | 0.8330 [0.6085, 1.0000] | 0.7073 [0.5129, 0.9090] | 0.02201907848661124 | -0.12249567237193387 | 0.4846938775510204 |
| prose_quote | state-like | 0.5564 [0.3804, 0.7450] | 0.6103 [0.3872, 0.8767] | 0.3327 [0.0910, 0.5597] | 0.007638357576636395 | 0.012765753169687068 | 0.5629251700680272 |
| prose_sentence | count-like | 0.6661 [0.5924, 0.7341] | 0.6944 [0.6026, 0.8248] | 0.1888 [0.0843, 0.2898] | 0.17553431510759343 | -0.00491865046086723 | 0.5311791383219955 |
| prose_sentiment | semantic | 0.5281 [0.3620, 0.6522] | 0.9300 [0.8520, 0.9870] | 0.6444 [0.5097, 0.7806] | 0.08268584027500832 | 0.24848636929422463 | 0.9109977324263039 |
| prose_topic | semantic | 0.7472 [0.5147, 0.9484] | 0.9875 [0.9337, 1.0000] | 0.6435 [0.5499, 0.7364] | 0.022379520479632684 | 0.04042905253796342 | 1.0 |
| python_argument | count-like | 0.9742 [0.9226, 1.0000] | 0.8994 [0.7911, 0.9785] | 0.1660 [0.1346, 0.1988] | 0.008372107454688216 | 0.014725133930878376 | 0.5 |
| python_comment | state-like | 0.9649 [0.9150, 1.0000] | 0.9904 [0.9728, 1.0000] | 0.4742 [0.4180, 0.5331] | 0.02430108416120385 | -0.011327857694288063 | 0.5425170068027211 |
| python_depth | count-like | 0.8248 [0.7641, 0.8895] | 0.6956 [0.6190, 0.7698] | 0.1179 [0.0567, 0.1846] | 0.06626622769619123 | 0.052143296393404384 | 0.4875283446712018 |
| python_error | semantic | 0.9768 [0.9274, 1.0000] | 0.7217 [0.6270, 0.8623] | 0.0425 [0.0199, 0.0652] | 0.0019358919321315541 | 0.021260332446426177 | 1.0 |
| python_indent | count-like | 0.4651 [0.1378, 0.7605] | 0.8810 [0.7220, 0.9853] | 0.3254 [0.2401, 0.4089] | 0.0003432290411672348 | 0.03769496259739142 | 0.5918367346938775 |
| python_string | state-like | 0.9943 [0.9750, 1.0000] | 1.0000 [1.0000, 1.0000] | 0.5198 [0.4766, 0.5609] | 0.025974802306185846 | 0.011168253692800672 | 0.6439909297052154 |
| table_column | count-like | 0.8373 [0.6950, 0.9547] | 0.6037 [0.4484, 0.7806] | 0.0859 [0.0025, 0.1736] | 5.6231213604679054e-05 | 0.026495855911501127 | 0.4744897959183674 |
| table_role | state-like | 1.0000 [1.0000, 1.0000] | 0.9660 [0.9184, 1.0000] | 0.2927 [0.2367, 0.3495] | 0.03672910933134745 | 0.012606357482898305 | 0.43820861678004536 |
| table_row | count-like | 0.6910 [0.4885, 0.8367] | 0.7517 [0.6406, 0.8532] | 0.0727 [0.0438, 0.1030] | 0.015079230225391775 | -0.0020844456399499167 | 0.5005668934240363 |
| table_status | semantic | 0.4870 [0.4050, 0.5227] | 0.5283 [0.5074, 0.5935] | 0.0021 [-0.0122, 0.0153] | 0.008376007886821725 | 0.05834600071867513 | 1.0 |

Primary-measure comparison (E1 prefix and description AUROCs were added after seeing E1 results; point estimates only):

| Row | Window AUROC | AR continuation AUROC — PRIMARY | AR on prefix AUROC — E1 post-result | AR description AUROC — E1 post-result | Oracle W1 AUROC |
|---|---:|---:|---:|---:|---:|
| json_status | 0.9807 | 0.9881 | 0.9960 | 0.9825 | 1.0000 |
| json_type | 0.9546 | 0.9779 | 0.6536 | 0.5375 | 0.6599 |
| latex_environment | 0.9824 | 0.6808 | 0.8498 | 0.4025 | 0.5709 |
| latex_role | 0.7891 | 0.8917 | 0.8889 | 0.6700 | 0.8435 |
| latex_section | 0.8506 | 0.5360 | 0.0034 | 0.5275 | 0.4325 |
| latex_subject | 0.8022 | 0.9461 | 0.8980 | 0.3625 | 1.0000 |
| list_depth | 0.7392 | 0.6230 | 0.0975 | 0.5650 | 0.6338 |
| list_index | 0.6298 | 0.5754 | 0.5051 | 0.7325 | 0.4189 |
| list_priority | 0.7954 | 0.9700 | 0.4841 | 0.7325 | 0.8906 |
| list_topic | 0.9376 | 1.0000 | 0.9864 | 0.7875 | 0.9677 |
| prose_paren | 0.6528 | 0.8330 | 0.6111 | 0.2475 | 0.4847 |
| prose_quote | 0.5564 | 0.6103 | 0.5669 | 0.5150 | 0.5629 |
| prose_sentence | 0.6661 | 0.6944 | 0.9841 | 0.4850 | 0.5312 |
| prose_sentiment | 0.5281 | 0.9300 | 0.9847 | 0.9600 | 0.9110 |
| prose_topic | 0.7472 | 0.9875 | 0.8492 | 0.7700 | 1.0000 |
| python_argument | 0.9742 | 0.8994 | 0.7183 | 0.7275 | 0.5000 |
| python_comment | 0.9649 | 0.9904 | 0.8248 | 0.4250 | 0.5425 |
| python_depth | 0.8248 | 0.6956 | 0.8707 | 0.6800 | 0.4875 |
| python_error | 0.9768 | 0.7217 | 0.5890 | 0.7625 | 1.0000 |
| python_indent | 0.4651 | 0.8810 | 0.5068 | 0.6800 | 0.5918 |
| python_string | 0.9943 | 1.0000 | 0.8724 | 0.5900 | 0.6440 |
| table_column | 0.8373 | 0.6037 | 0.5442 | 0.6125 | 0.4745 |
| table_role | 1.0000 | 0.9660 | 0.9892 | 0.5950 | 0.4382 |
| table_row | 0.6910 | 0.7517 | 0.7925 | 0.4750 | 0.5006 |
| table_status | 0.4870 | 0.5283 | 0.7885 | 0.9500 | 1.0000 |
