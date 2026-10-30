# E11 — EXPLORATORY

Structure directions sit in residual and h top PCs but not reconstruction;meaning in all three.

No clean structure-specific dissociation at class level: reconstruction top-64 fractions are lower than h and residual for every class, including semantic rows;semantic h/residual fractions exceed count/state means. All40 directions and both k values reported.

Centered PCA on all 2,100 W3 test items across the frozen 25 rows. Projections of all 40 W1 dev-fit directions are reported; class means below use the selected 25 only. No sign flips or refits.

| Class | k | h | Reconstruction | Residual |
|---|---:|---:|---:|---:|
| count-like | 16 | 0.018581 | 0.004371 | 0.011080 |
| count-like | 64 | 0.077936 | 0.013508 | 0.048209 |
| state-like | 16 | 0.016133 | 0.005804 | 0.010742 |
| state-like | 64 | 0.103895 | 0.017606 | 0.057898 |
| semantic | 16 | 0.017581 | 0.004282 | 0.005693 |
| semantic | 64 | 0.151001 | 0.019970 | 0.077946 |

h/reconstruction mean squared principal cosine: k=16: 0.118282, k=64: 0.159941.

| Feature | Class | In W3 | h16 | h64 | recon16 | recon64 | residual16 | residual64 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| json_depth | count-like | False | 0.007061 | 0.025098 | 0.002719 | 0.013130 | 0.002380 | 0.015410 |
| json_field | count-like | False | 0.003406 | 0.014436 | 0.003163 | 0.014034 | 0.001819 | 0.013310 |
| json_status | semantic | True | 0.036869 | 0.278418 | 0.002470 | 0.012696 | 0.009376 | 0.213433 |
| json_type | state-like | True | 0.003043 | 0.029043 | 0.008464 | 0.030526 | 0.003473 | 0.020496 |
| latex_brace | count-like | False | 0.002604 | 0.015590 | 0.004265 | 0.010441 | 0.004348 | 0.015431 |
| latex_environment | state-like | True | 0.001120 | 0.015494 | 0.002887 | 0.010953 | 0.003329 | 0.011503 |
| latex_fraction | state-like | False | 0.005722 | 0.022786 | 0.000854 | 0.006859 | 0.005137 | 0.016992 |
| latex_item | count-like | False | 0.036509 | 0.148480 | 0.014080 | 0.037682 | 0.024361 | 0.087061 |
| latex_math | state-like | False | 0.039449 | 0.056333 | 0.004165 | 0.012779 | 0.022279 | 0.040684 |
| latex_role | semantic | True | 0.017431 | 0.107253 | 0.006360 | 0.025346 | 0.005773 | 0.037015 |
| latex_section | count-like | True | 0.003500 | 0.016642 | 0.004229 | 0.012435 | 0.005320 | 0.016986 |
| latex_subject | semantic | True | 0.003362 | 0.049346 | 0.001806 | 0.020432 | 0.002480 | 0.012958 |
| list_completed | count-like | False | 0.004392 | 0.011229 | 0.002477 | 0.008273 | 0.002900 | 0.010358 |
| list_depth | count-like | True | 0.009402 | 0.032365 | 0.003213 | 0.008793 | 0.007341 | 0.024371 |
| list_index | count-like | True | 0.015693 | 0.032804 | 0.001792 | 0.007266 | 0.011248 | 0.029810 |
| list_ordered | state-like | False | 0.002608 | 0.014329 | 0.004036 | 0.011561 | 0.002859 | 0.010153 |
| list_priority | semantic | True | 0.018559 | 0.064820 | 0.003651 | 0.018966 | 0.004457 | 0.028757 |
| list_task | state-like | False | 0.002286 | 0.010861 | 0.001890 | 0.006562 | 0.002337 | 0.009417 |
| list_topic | semantic | True | 0.005721 | 0.047607 | 0.005918 | 0.024046 | 0.004022 | 0.026223 |
| list_words | count-like | False | 0.037623 | 0.062799 | 0.001914 | 0.010284 | 0.019029 | 0.042398 |
| prose_budget | count-like | False | 0.009328 | 0.029038 | 0.001823 | 0.009002 | 0.004538 | 0.021125 |
| prose_column | count-like | False | 0.019251 | 0.050804 | 0.008169 | 0.023409 | 0.018124 | 0.041454 |
| prose_paren | state-like | True | 0.005072 | 0.033393 | 0.003543 | 0.011102 | 0.004909 | 0.027300 |
| prose_quote | state-like | True | 0.004240 | 0.024032 | 0.002081 | 0.007974 | 0.003517 | 0.019402 |
| prose_sentence | count-like | True | 0.017574 | 0.080525 | 0.011067 | 0.025273 | 0.013002 | 0.043862 |
| prose_sentiment | semantic | True | 0.006388 | 0.040328 | 0.002146 | 0.009589 | 0.002403 | 0.022571 |
| prose_topic | semantic | True | 0.014545 | 0.054338 | 0.001607 | 0.019290 | 0.003556 | 0.026649 |
| prose_words | count-like | False | 0.031491 | 0.053947 | 0.001040 | 0.007574 | 0.016394 | 0.039003 |
| python_argument | count-like | True | 0.071033 | 0.250240 | 0.004951 | 0.016377 | 0.028630 | 0.134922 |
| python_comment | state-like | True | 0.025420 | 0.214205 | 0.005535 | 0.024328 | 0.017892 | 0.098495 |
| python_depth | count-like | True | 0.002472 | 0.020441 | 0.004528 | 0.014039 | 0.003202 | 0.017783 |
| python_effect | semantic | False | 0.012657 | 0.032795 | 0.006415 | 0.015959 | 0.008670 | 0.023245 |
| python_error | semantic | True | 0.016638 | 0.434832 | 0.011596 | 0.036433 | 0.011237 | 0.116346 |
| python_indent | count-like | True | 0.007259 | 0.037396 | 0.002173 | 0.009204 | 0.004019 | 0.026203 |
| python_line | count-like | False | 0.008811 | 0.018346 | 0.001242 | 0.006721 | 0.004016 | 0.015978 |
| python_string | state-like | True | 0.029979 | 0.265771 | 0.014454 | 0.027267 | 0.020313 | 0.117939 |
| table_column | count-like | True | 0.021591 | 0.078670 | 0.004420 | 0.016810 | 0.013053 | 0.053021 |
| table_role | state-like | True | 0.044054 | 0.145328 | 0.003667 | 0.011095 | 0.021761 | 0.110150 |
| table_row | count-like | True | 0.018702 | 0.152341 | 0.002963 | 0.011378 | 0.013905 | 0.086925 |
| table_status | semantic | True | 0.038718 | 0.282070 | 0.002978 | 0.012936 | 0.007932 | 0.217562 |
