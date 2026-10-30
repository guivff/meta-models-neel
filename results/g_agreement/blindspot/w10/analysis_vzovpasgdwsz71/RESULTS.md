# W10 §86 results

Prediction: Oracle misses operating mode while NLA reads more.

HANDOFF W10 §86: H1 NOT MET 5/7 (0.714); H2 NOT MET 3/7 (0.429)

| Row | Active | Probe42 | Probe44 | Oracle | NLA | J-lens | Oracle gate | NLA gate |
|---|---:|---:|---:|---:|---:|---:|---|---|
| audience_far | 10/20 | 0.978 | 0.998 | 0.744 | 0.971 | 0.557 | NOT EVALUABLE | NOT EVALUABLE |
| audience_near | 7/20 | 0.972 | 0.996 | 0.734 | 0.959 | 0.600 | NOT EVALUABLE | NOT EVALUABLE |
| format_far | 14/20 | 1.000 | 0.972 | 0.977 | 0.917 | 0.779 | EVALUABLE | EVALUABLE |
| format_near | 14/20 | 1.000 | 0.972 | 0.960 | 0.870 | 0.784 | EVALUABLE | EVALUABLE |
| language_far | 20/20 | 1.000 | 1.000 | 0.716 | 0.362 | 0.368 | EVALUABLE | EVALUABLE |
| language_near | 20/20 | 1.000 | 1.000 | 0.637 | 0.437 | 0.364 | EVALUABLE | EVALUABLE |
| length_far | 10/20 | 1.000 | 1.000 | 1.000 | 0.876 | 0.856 | NOT EVALUABLE | NOT EVALUABLE |
| length_near | 10/20 | 1.000 | 1.000 | 1.000 | 0.873 | 0.838 | NOT EVALUABLE | NOT EVALUABLE |
| persona_far | 20/20 | 1.000 | 1.000 | 0.619 | 0.946 | 0.416 | EVALUABLE | EVALUABLE |
| persona_near | 17/20 | 1.000 | 1.000 | 0.628 | 0.941 | 0.423 | NOT EVALUABLE | EVALUABLE |
| register_far | 8/20 | 0.920 | 1.000 | 0.892 | 0.806 | 0.561 | NOT EVALUABLE | NOT EVALUABLE |
| register_near | 6/20 | 0.963 | 1.000 | 0.879 | 0.769 | 0.552 | NOT EVALUABLE | NOT EVALUABLE |
| surprisal_prose | n/a | 0.886 | 0.899 | 0.266 | 0.675 | 0.353 | NOT EVALUABLE | NOT EVALUABLE |
| surprisal_python | n/a | 1.000 | 1.000 | 0.639 | 0.673 | 0.518 | EVALUABLE | NOT EVALUABLE |
| topic_far | 18/20 | 0.941 | 0.944 | 0.444 | 0.644 | 0.431 | EVALUABLE | EVALUABLE |
| topic_near | 18/20 | 0.897 | 0.934 | 0.431 | 0.647 | 0.470 | EVALUABLE | EVALUABLE |

All signed reader AUROCs, CIs, phrasings, random controls and failure reasons are in metrics.json.

| Mode | Far − near (probe − Oracle) | 95% CI |
|---|---:|---|
| language | -0.079 | [-0.22666666666666668, 0.085666666666666] |
| register | -0.013 | [-0.026666666666666727, 0.01777777777777778] |
| audience | -0.008 | [-0.24555555555555553, 0.2544722222222221] |
| format | -0.017 | [-0.07666666666666666, 0.0] |
| length | 0.000 | [0.0, 0.0] |
| persona | 0.009 | [-0.026666666666666616, 0.07000000000000006] |
| topic | -0.003 | [-0.0444444444444444, 0.04555555555555546] |

Surprisal rows are DESCRIPTIVE and excluded from H1/H2. The reconstructor window remains unresolved.
