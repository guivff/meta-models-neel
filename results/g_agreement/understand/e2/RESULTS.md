**Prediction (§89):** Structural probe directions lie near the random baseline in the AR image; semantic directions have large image fractions. Both classes lie substantially in the real-activation subspace. The native-42 decoder should show the same pattern more weakly.

**Assessment: the proposed structure-versus-meaning separation did not hold.** The AR subspace had smaller projection fractions than the real-activation subspace, but this affected all three classes. At 95% variance, AR mean fractions were 0.151 count-like, 0.160 state-like and 0.170 semantic, against a random-direction mean of 0.189. At 99%, they were 0.379, 0.380 and 0.407, against 0.420. Semantic directions were not strongly included above random. Real-activation fractions were higher and similar across classes. The native-42 decoder was mostly near its random baseline, with a modest semantic elevation. These results do not identify a structure-specific inaccessible AR subspace.

EXPLORATORY. All 40 W1 directions, both variance levels, 200 frozen random unit directions and both native-site real-activation baselines are retained. The 5,000 span IDs match across all arms; no rows, signs or PCA settings were changed.

| Subspace | Variance | Rank | Random mean | Count-like mean (19) | State-like mean (11) | Semantic mean (10) |
|---|---:|---:|---:|---:|---:|---:|
| AR44 | 0.95 | 963 | 0.188747 | 0.150985 | 0.160168 | 0.169892 |
| AR44 | 0.99 | 2147 | 0.419548 | 0.379243 | 0.379700 | 0.407116 |
| decoder42 | 0.95 | 1245 | 0.243887 | 0.239883 | 0.248974 | 0.262177 |
| decoder42 | 0.99 | 2413 | 0.472689 | 0.472747 | 0.490483 | 0.492225 |
| real42 | 0.95 | 2133 | 0.416903 | 0.440128 | 0.448588 | 0.426903 |
| real42 | 0.99 | 3240 | 0.633686 | 0.652217 | 0.661678 | 0.646239 |
| real44 | 0.95 | 2116 | 0.413696 | 0.438129 | 0.443512 | 0.432786 |
| real44 | 0.99 | 3227 | 0.631422 | 0.654219 | 0.652745 | 0.646887 |

Class means above are descriptive, without new statistical tests. PCA is centered independently per matrix; directions are the original dev-fit unit vectors at each native site. Image fraction is the squared norm of the orthogonal projection. Full 200-direction random baselines remain in metrics.json.

## AR44: all 40 directions

| Row | Class | Fraction in 95% subspace | Fraction in 99% subspace |
|---|---|---:|---:|
| json_depth | count-like | 0.136096 | 0.352614 |
| json_field | count-like | 0.142179 | 0.366461 |
| json_status | semantic | 0.173105 | 0.400486 |
| json_type | state-like | 0.187072 | 0.409473 |
| latex_brace | count-like | 0.139182 | 0.376626 |
| latex_environment | state-like | 0.136943 | 0.362105 |
| latex_fraction | state-like | 0.209270 | 0.435983 |
| latex_item | count-like | 0.195852 | 0.417890 |
| latex_math | state-like | 0.185174 | 0.402527 |
| latex_role | semantic | 0.190829 | 0.434067 |
| latex_section | count-like | 0.145921 | 0.363404 |
| latex_subject | semantic | 0.199718 | 0.430978 |
| list_completed | count-like | 0.125408 | 0.341040 |
| list_depth | count-like | 0.134679 | 0.362319 |
| list_index | count-like | 0.133092 | 0.349155 |
| list_ordered | state-like | 0.151642 | 0.375271 |
| list_priority | semantic | 0.152632 | 0.398149 |
| list_task | state-like | 0.126582 | 0.357106 |
| list_topic | semantic | 0.162213 | 0.405727 |
| list_words | count-like | 0.140591 | 0.386319 |
| prose_budget | count-like | 0.164344 | 0.399976 |
| prose_column | count-like | 0.176975 | 0.407293 |
| prose_paren | state-like | 0.133728 | 0.353571 |
| prose_quote | state-like | 0.145391 | 0.359774 |
| prose_sentence | count-like | 0.205761 | 0.437738 |
| prose_sentiment | semantic | 0.150483 | 0.396522 |
| prose_topic | semantic | 0.158695 | 0.394464 |
| prose_words | count-like | 0.146859 | 0.387456 |
| python_argument | count-like | 0.125918 | 0.351547 |
| python_comment | state-like | 0.182094 | 0.390811 |
| python_depth | count-like | 0.142877 | 0.373028 |
| python_effect | semantic | 0.147920 | 0.378826 |
| python_error | semantic | 0.176701 | 0.413824 |
| python_indent | count-like | 0.173010 | 0.402087 |
| python_line | count-like | 0.158721 | 0.400725 |
| python_string | state-like | 0.166046 | 0.380459 |
| table_column | count-like | 0.160755 | 0.380724 |
| table_role | state-like | 0.137903 | 0.349621 |
| table_row | count-like | 0.120502 | 0.349207 |
| table_status | semantic | 0.186628 | 0.418114 |

## decoder42: all 40 directions

| Row | Class | Fraction in 95% subspace | Fraction in 99% subspace |
|---|---|---:|---:|
| json_depth | count-like | 0.206687 | 0.450604 |
| json_field | count-like | 0.230992 | 0.462015 |
| json_status | semantic | 0.240320 | 0.473213 |
| json_type | state-like | 0.246068 | 0.487655 |
| latex_brace | count-like | 0.220634 | 0.445960 |
| latex_environment | state-like | 0.218922 | 0.472732 |
| latex_fraction | state-like | 0.361730 | 0.580997 |
| latex_item | count-like | 0.274358 | 0.500287 |
| latex_math | state-like | 0.274963 | 0.509129 |
| latex_role | semantic | 0.363728 | 0.575045 |
| latex_section | count-like | 0.231322 | 0.451051 |
| latex_subject | semantic | 0.281351 | 0.507965 |
| list_completed | count-like | 0.206605 | 0.436368 |
| list_depth | count-like | 0.224954 | 0.460867 |
| list_index | count-like | 0.227597 | 0.461684 |
| list_ordered | state-like | 0.208366 | 0.447974 |
| list_priority | semantic | 0.221131 | 0.464794 |
| list_task | state-like | 0.223614 | 0.476221 |
| list_topic | semantic | 0.230852 | 0.471390 |
| list_words | count-like | 0.243655 | 0.472615 |
| prose_budget | count-like | 0.252237 | 0.483193 |
| prose_column | count-like | 0.230114 | 0.465358 |
| prose_paren | state-like | 0.225621 | 0.481725 |
| prose_quote | state-like | 0.232976 | 0.485038 |
| prose_sentence | count-like | 0.259953 | 0.478464 |
| prose_sentiment | semantic | 0.258332 | 0.483444 |
| prose_topic | semantic | 0.240679 | 0.470488 |
| prose_words | count-like | 0.243377 | 0.472702 |
| python_argument | count-like | 0.233461 | 0.472229 |
| python_comment | state-like | 0.260088 | 0.500416 |
| python_depth | count-like | 0.233157 | 0.470085 |
| python_effect | semantic | 0.230723 | 0.460547 |
| python_error | semantic | 0.287007 | 0.516548 |
| python_indent | count-like | 0.296080 | 0.520861 |
| python_line | count-like | 0.293322 | 0.551070 |
| python_string | state-like | 0.255014 | 0.490839 |
| table_column | count-like | 0.245240 | 0.485814 |
| table_role | state-like | 0.231352 | 0.462583 |
| table_row | count-like | 0.204029 | 0.440963 |
| table_status | semantic | 0.267649 | 0.498816 |

## real42: all 40 directions

| Row | Class | Fraction in 95% subspace | Fraction in 99% subspace |
|---|---|---:|---:|
| json_depth | count-like | 0.415712 | 0.624757 |
| json_field | count-like | 0.437714 | 0.655758 |
| json_status | semantic | 0.418874 | 0.651217 |
| json_type | state-like | 0.475001 | 0.681541 |
| latex_brace | count-like | 0.399666 | 0.616864 |
| latex_environment | state-like | 0.396943 | 0.622876 |
| latex_fraction | state-like | 0.555526 | 0.737977 |
| latex_item | count-like | 0.485289 | 0.681411 |
| latex_math | state-like | 0.497025 | 0.696480 |
| latex_role | semantic | 0.477921 | 0.669608 |
| latex_section | count-like | 0.429328 | 0.643145 |
| latex_subject | semantic | 0.445073 | 0.650596 |
| list_completed | count-like | 0.402531 | 0.629366 |
| list_depth | count-like | 0.444660 | 0.656003 |
| list_index | count-like | 0.428185 | 0.651163 |
| list_ordered | state-like | 0.379456 | 0.613469 |
| list_priority | semantic | 0.377621 | 0.623630 |
| list_task | state-like | 0.405974 | 0.623320 |
| list_topic | semantic | 0.400210 | 0.635081 |
| list_words | count-like | 0.432967 | 0.644623 |
| prose_budget | count-like | 0.413446 | 0.631276 |
| prose_column | count-like | 0.430554 | 0.638919 |
| prose_paren | state-like | 0.414381 | 0.624683 |
| prose_quote | state-like | 0.416819 | 0.637449 |
| prose_sentence | count-like | 0.453476 | 0.658800 |
| prose_sentiment | semantic | 0.396112 | 0.619465 |
| prose_topic | semantic | 0.392310 | 0.627102 |
| prose_words | count-like | 0.431606 | 0.649272 |
| python_argument | count-like | 0.460970 | 0.662563 |
| python_comment | state-like | 0.461869 | 0.669997 |
| python_depth | count-like | 0.432497 | 0.657961 |
| python_effect | semantic | 0.423621 | 0.634554 |
| python_error | semantic | 0.476010 | 0.679001 |
| python_indent | count-like | 0.491452 | 0.692992 |
| python_line | count-like | 0.482878 | 0.676724 |
| python_string | state-like | 0.473593 | 0.677327 |
| table_column | count-like | 0.463774 | 0.683935 |
| table_role | state-like | 0.457883 | 0.693344 |
| table_row | count-like | 0.425736 | 0.636585 |
| table_status | semantic | 0.461279 | 0.672136 |

## real44: all 40 directions

| Row | Class | Fraction in 95% subspace | Fraction in 99% subspace |
|---|---|---:|---:|
| json_depth | count-like | 0.423591 | 0.641673 |
| json_field | count-like | 0.427075 | 0.647820 |
| json_status | semantic | 0.422888 | 0.651580 |
| json_type | state-like | 0.455303 | 0.661950 |
| latex_brace | count-like | 0.398194 | 0.619636 |
| latex_environment | state-like | 0.384231 | 0.605989 |
| latex_fraction | state-like | 0.571345 | 0.740867 |
| latex_item | count-like | 0.477230 | 0.678576 |
| latex_math | state-like | 0.485287 | 0.675287 |
| latex_role | semantic | 0.493491 | 0.683553 |
| latex_section | count-like | 0.424449 | 0.644939 |
| latex_subject | semantic | 0.455544 | 0.658648 |
| list_completed | count-like | 0.394249 | 0.608303 |
| list_depth | count-like | 0.413851 | 0.641668 |
| list_index | count-like | 0.401846 | 0.628885 |
| list_ordered | state-like | 0.377960 | 0.609730 |
| list_priority | semantic | 0.386066 | 0.621865 |
| list_task | state-like | 0.407631 | 0.631062 |
| list_topic | semantic | 0.402354 | 0.614170 |
| list_words | count-like | 0.433647 | 0.657906 |
| prose_budget | count-like | 0.422093 | 0.632203 |
| prose_column | count-like | 0.435379 | 0.654203 |
| prose_paren | state-like | 0.411336 | 0.614781 |
| prose_quote | state-like | 0.410052 | 0.625023 |
| prose_sentence | count-like | 0.469443 | 0.674698 |
| prose_sentiment | semantic | 0.413294 | 0.627871 |
| prose_topic | semantic | 0.397985 | 0.624068 |
| prose_words | count-like | 0.425075 | 0.647215 |
| python_argument | count-like | 0.458578 | 0.666805 |
| python_comment | state-like | 0.444954 | 0.664611 |
| python_depth | count-like | 0.433883 | 0.647331 |
| python_effect | semantic | 0.415551 | 0.623939 |
| python_error | semantic | 0.473400 | 0.684234 |
| python_indent | count-like | 0.503863 | 0.707451 |
| python_line | count-like | 0.480769 | 0.696993 |
| python_string | state-like | 0.463487 | 0.672303 |
| table_column | count-like | 0.466002 | 0.680650 |
| table_role | state-like | 0.467042 | 0.678588 |
| table_row | count-like | 0.435226 | 0.653205 |
| table_status | semantic | 0.467286 | 0.678942 |
