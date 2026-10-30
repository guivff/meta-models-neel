# §107 Q1/Q2 descriptive follow-ups

**Registered after the rater-1 tables were seen**, cf19c2e8. No verdict changes, new coding calls, API or GPU. Existing codes/asked-score percentiles and original seals unchanged.

## 1. Item-cluster bootstrap intervals

2000resamples, seed20261024. Items resampled within sample/tier/reader; all4Q1 generations or all observed Q2b doses stay together. Ratios pool counts across drawn items. Wilson intervals retained for comparison; these bootstrap percentile intervals are not necessarily wider. A zero-observed event can have bootstrap[0,0], which is not proof its population probability is zero. Conditional-accuracy draws with no eligible mentions/enacts are undefined; the table counts them.

| Sample / tier / reader | Rate | k/n | Wilson95 | Item-cluster95 | Defined draws/2000 | Items |
|---|---|---:|---|---|---:|---:|
| q1 / content / nla L42 | mode.continues | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / content / nla L42 | mode.describes | 80/80 | [0.954, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / content / nla L42 | mode.mixed | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / content / nla L42 | mentions.rate | 80/80 | [0.954, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / content / nla L42 | mention_kind.quotes_token.rate | 35/80 | [0.334, 0.547] | [0.250, 0.625] | 2000 | 20 |
| q1 / content / nla L42 | mention_kind.states_property.rate | 45/80 | [0.453, 0.666] | [0.375, 0.750] | 2000 | 20 |
| q1 / content / nla L42 | mentions.accuracy | 70/80 | [0.785, 0.931] | [0.725, 1.000] | 2000 | 20 |
| q1 / content / nla L42 | mentions.resolved_accuracy | 70/71 | [0.924, 0.998] | [0.950, 1.000] | 2000 | 20 |
| q1 / content / nla L42 | enacts.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / content / nla L42 | enacts.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / content / nla L42 | enacts.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / content / nla L42 | hallucination | 80/80 | [0.954, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / content / nla L42 | extra | 75/80 | [0.862, 0.973] | [0.875, 0.988] | 2000 | 20 |
| q1 / content / oracle L44 | mode.continues | 78/80 | [0.913, 0.993] | [0.938, 1.000] | 2000 | 20 |
| q1 / content / oracle L44 | mode.describes | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / content / oracle L44 | mode.mixed | 2/80 | [0.007, 0.087] | [0.000, 0.062] | 2000 | 20 |
| q1 / content / oracle L44 | mentions.rate | 15/80 | [0.117, 0.287] | [0.050, 0.338] | 2000 | 20 |
| q1 / content / oracle L44 | mention_kind.quotes_token.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / content / oracle L44 | mention_kind.states_property.rate | 15/80 | [0.117, 0.287] | [0.050, 0.338] | 2000 | 20 |
| q1 / content / oracle L44 | mentions.accuracy | 15/15 | [0.796, 1.000] | [1.000, 1.000] | 1998 | 20 |
| q1 / content / oracle L44 | mentions.resolved_accuracy | 15/15 | [0.796, 1.000] | [1.000, 1.000] | 1998 | 20 |
| q1 / content / oracle L44 | enacts.rate | 76/80 | [0.878, 0.980] | [0.887, 1.000] | 2000 | 20 |
| q1 / content / oracle L44 | enacts.accuracy | 75/76 | [0.929, 0.998] | [0.957, 1.000] | 2000 | 20 |
| q1 / content / oracle L44 | enacts.resolved_accuracy | 75/75 | [0.951, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / content / oracle L44 | hallucination | 6/80 | [0.035, 0.154] | [0.000, 0.175] | 2000 | 20 |
| q1 / content / oracle L44 | extra | 28/80 | [0.255, 0.459] | [0.225, 0.475] | 2000 | 20 |
| q1 / earlier_state / nla L42 | mode.continues | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / earlier_state / nla L42 | mode.describes | 80/80 | [0.954, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / earlier_state / nla L42 | mode.mixed | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / earlier_state / nla L42 | mentions.rate | 80/80 | [0.954, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / earlier_state / nla L42 | mention_kind.quotes_token.rate | 65/80 | [0.713, 0.883] | [0.675, 0.925] | 2000 | 20 |
| q1 / earlier_state / nla L42 | mention_kind.states_property.rate | 15/80 | [0.117, 0.287] | [0.075, 0.325] | 2000 | 20 |
| q1 / earlier_state / nla L42 | mentions.accuracy | 20/80 | [0.168, 0.355] | [0.113, 0.400] | 2000 | 20 |
| q1 / earlier_state / nla L42 | mentions.resolved_accuracy | 20/23 | [0.679, 0.955] | [0.667, 1.000] | 2000 | 20 |
| q1 / earlier_state / nla L42 | enacts.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / earlier_state / nla L42 | enacts.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / earlier_state / nla L42 | enacts.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / earlier_state / nla L42 | hallucination | 80/80 | [0.954, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / earlier_state / nla L42 | extra | 72/80 | [0.815, 0.948] | [0.850, 0.950] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | mode.continues | 80/80 | [0.954, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | mode.describes | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | mode.mixed | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | mentions.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | mention_kind.quotes_token.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | mention_kind.states_property.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | mentions.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / earlier_state / oracle L44 | mentions.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / earlier_state / oracle L44 | enacts.rate | 39/80 | [0.381, 0.595] | [0.287, 0.700] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | enacts.accuracy | 5/39 | [0.056, 0.267] | [0.000, 0.315] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | enacts.resolved_accuracy | 5/8 | [0.306, 0.863] | [0.000, 1.000] | 1974 | 20 |
| q1 / earlier_state / oracle L44 | hallucination | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / earlier_state / oracle L44 | extra | 21/80 | [0.179, 0.368] | [0.188, 0.338] | 2000 | 20 |
| q1 / local_form / nla L42 | mode.continues | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / local_form / nla L42 | mode.describes | 80/80 | [0.954, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / local_form / nla L42 | mode.mixed | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / local_form / nla L42 | mentions.rate | 79/80 | [0.933, 0.998] | [0.963, 1.000] | 2000 | 20 |
| q1 / local_form / nla L42 | mention_kind.quotes_token.rate | 62/80 | [0.672, 0.853] | [0.600, 0.925] | 2000 | 20 |
| q1 / local_form / nla L42 | mention_kind.states_property.rate | 17/80 | [0.137, 0.314] | [0.062, 0.388] | 2000 | 20 |
| q1 / local_form / nla L42 | mentions.accuracy | 71/79 | [0.813, 0.948] | [0.769, 1.000] | 2000 | 20 |
| q1 / local_form / nla L42 | mentions.resolved_accuracy | 71/74 | [0.887, 0.986] | [0.870, 1.000] | 2000 | 20 |
| q1 / local_form / nla L42 | enacts.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / local_form / nla L42 | enacts.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / local_form / nla L42 | enacts.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / local_form / nla L42 | hallucination | 80/80 | [0.954, 1.000] | [1.000, 1.000] | 2000 | 20 |
| q1 / local_form / nla L42 | extra | 49/80 | [0.503, 0.712] | [0.475, 0.738] | 2000 | 20 |
| q1 / local_form / oracle L44 | mode.continues | 79/80 | [0.933, 0.998] | [0.963, 1.000] | 2000 | 20 |
| q1 / local_form / oracle L44 | mode.describes | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / local_form / oracle L44 | mode.mixed | 1/80 | [0.002, 0.067] | [0.000, 0.037] | 2000 | 20 |
| q1 / local_form / oracle L44 | mentions.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / local_form / oracle L44 | mention_kind.quotes_token.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / local_form / oracle L44 | mention_kind.states_property.rate | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / local_form / oracle L44 | mentions.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / local_form / oracle L44 | mentions.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 20 |
| q1 / local_form / oracle L44 | enacts.rate | 49/80 | [0.503, 0.712] | [0.450, 0.775] | 2000 | 20 |
| q1 / local_form / oracle L44 | enacts.accuracy | 32/49 | [0.513, 0.771] | [0.423, 0.881] | 2000 | 20 |
| q1 / local_form / oracle L44 | enacts.resolved_accuracy | 32/36 | [0.747, 0.956] | [0.657, 1.000] | 2000 | 20 |
| q1 / local_form / oracle L44 | hallucination | 0/80 | [0.000, 0.046] | [0.000, 0.000] | 2000 | 20 |
| q1 / local_form / oracle L44 | extra | 23/80 | [0.200, 0.395] | [0.163, 0.412] | 2000 | 20 |
| q2a / content / nla L42 | mode.continues | 0/150 | [0.000, 0.025] | [0.000, 0.000] | 2000 | 150 |
| q2a / content / nla L42 | mode.describes | 150/150 | [0.975, 1.000] | [1.000, 1.000] | 2000 | 150 |
| q2a / content / nla L42 | mode.mixed | 0/150 | [0.000, 0.025] | [0.000, 0.000] | 2000 | 150 |
| q2a / content / nla L42 | mentions.rate | 150/150 | [0.975, 1.000] | [1.000, 1.000] | 2000 | 150 |
| q2a / content / nla L42 | mention_kind.quotes_token.rate | 92/150 | [0.533, 0.688] | [0.540, 0.693] | 2000 | 150 |
| q2a / content / nla L42 | mention_kind.states_property.rate | 58/150 | [0.312, 0.467] | [0.307, 0.460] | 2000 | 150 |
| q2a / content / nla L42 | mentions.accuracy | 93/150 | [0.540, 0.694] | [0.540, 0.700] | 2000 | 150 |
| q2a / content / nla L42 | mentions.resolved_accuracy | 93/93 | [0.960, 1.000] | [1.000, 1.000] | 2000 | 150 |
| q2a / content / nla L42 | enacts.rate | 0/150 | [0.000, 0.025] | [0.000, 0.000] | 2000 | 150 |
| q2a / content / nla L42 | enacts.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 150 |
| q2a / content / nla L42 | enacts.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 150 |
| q2a / content / oracle L44 | mode.continues | 150/150 | [0.975, 1.000] | [1.000, 1.000] | 2000 | 150 |
| q2a / content / oracle L44 | mode.describes | 0/150 | [0.000, 0.025] | [0.000, 0.000] | 2000 | 150 |
| q2a / content / oracle L44 | mode.mixed | 0/150 | [0.000, 0.025] | [0.000, 0.000] | 2000 | 150 |
| q2a / content / oracle L44 | mentions.rate | 6/150 | [0.018, 0.085] | [0.013, 0.073] | 2000 | 150 |
| q2a / content / oracle L44 | mention_kind.quotes_token.rate | 0/150 | [0.000, 0.025] | [0.000, 0.000] | 2000 | 150 |
| q2a / content / oracle L44 | mention_kind.states_property.rate | 6/150 | [0.018, 0.085] | [0.013, 0.073] | 2000 | 150 |
| q2a / content / oracle L44 | mentions.accuracy | 6/6 | [0.610, 1.000] | [1.000, 1.000] | 1992 | 150 |
| q2a / content / oracle L44 | mentions.resolved_accuracy | 6/6 | [0.610, 1.000] | [1.000, 1.000] | 1992 | 150 |
| q2a / content / oracle L44 | enacts.rate | 113/150 | [0.679, 0.815] | [0.687, 0.820] | 2000 | 150 |
| q2a / content / oracle L44 | enacts.accuracy | 99/113 | [0.803, 0.925] | [0.812, 0.933] | 2000 | 150 |
| q2a / content / oracle L44 | enacts.resolved_accuracy | 99/108 | [0.849, 0.956] | [0.862, 0.964] | 2000 | 150 |
| q2b / earlier_state / oracle L44 | mode.continues | 320/320 | [0.988, 1.000] | [1.000, 1.000] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | mode.describes | 0/320 | [0.000, 0.012] | [0.000, 0.000] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | mode.mixed | 0/320 | [0.000, 0.012] | [0.000, 0.000] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | mentions.rate | 0/320 | [0.000, 0.012] | [0.000, 0.000] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | mention_kind.quotes_token.rate | 0/320 | [0.000, 0.012] | [0.000, 0.000] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | mention_kind.states_property.rate | 0/320 | [0.000, 0.012] | [0.000, 0.000] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | mentions.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 80 |
| q2b / earlier_state / oracle L44 | mentions.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 80 |
| q2b / earlier_state / oracle L44 | enacts.rate | 185/320 | [0.523, 0.631] | [0.489, 0.662] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | structure_named | 0/320 | [0.000, 0.012] | [0.000, 0.000] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | enacts.source_B_agreement | 0/185 | [0.000, 0.020] | [0.000, 0.000] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | enacts.target_A_alignment | 32/185 | [0.125, 0.234] | [0.109, 0.263] | 2000 | 80 |
| q2b / earlier_state / oracle L44 | enacts.resolved_target_A_alignment | 32/32 | [0.893, 1.000] | [1.000, 1.000] | 2000 | 80 |
| q2c / earlier_state / nla L42 | mode.continues | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / earlier_state / nla L42 | mode.describes | 168/168 | [0.978, 1.000] | [1.000, 1.000] | 2000 | 168 |
| q2c / earlier_state / nla L42 | mode.mixed | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / earlier_state / nla L42 | mentions.rate | 2/168 | [0.003, 0.042] | [0.000, 0.030] | 2000 | 168 |
| q2c / earlier_state / nla L42 | mention_kind.quotes_token.rate | 2/168 | [0.003, 0.042] | [0.000, 0.030] | 2000 | 168 |
| q2c / earlier_state / nla L42 | mention_kind.states_property.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / earlier_state / nla L42 | mentions.accuracy | 1/2 | [0.095, 0.905] | [0.000, 1.000] | 1726 | 168 |
| q2c / earlier_state / nla L42 | mentions.resolved_accuracy | 1/1 | [0.207, 1.000] | [1.000, 1.000] | 1254 | 168 |
| q2c / earlier_state / nla L42 | enacts.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / earlier_state / nla L42 | enacts.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / earlier_state / nla L42 | enacts.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / earlier_state / nla L42 | structure_tokens | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | mode.continues | 163/168 | [0.932, 0.987] | [0.940, 0.994] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | mode.describes | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | mode.mixed | 5/168 | [0.013, 0.068] | [0.006, 0.060] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | mentions.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | mention_kind.quotes_token.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | mention_kind.states_property.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | mentions.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / earlier_state / oracle L44 | mentions.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / earlier_state / oracle L44 | enacts.rate | 78/168 | [0.391, 0.540] | [0.393, 0.542] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | enacts.accuracy | 14/78 | [0.110, 0.279] | [0.100, 0.266] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | enacts.resolved_accuracy | 14/25 | [0.371, 0.733] | [0.360, 0.750] | 2000 | 168 |
| q2c / earlier_state / oracle L44 | structure_tokens | 86/168 | [0.437, 0.586] | [0.435, 0.589] | 2000 | 168 |
| q2c / local_form / nla L42 | mode.continues | 0/84 | [0.000, 0.044] | [0.000, 0.000] | 2000 | 84 |
| q2c / local_form / nla L42 | mode.describes | 84/84 | [0.956, 1.000] | [1.000, 1.000] | 2000 | 84 |
| q2c / local_form / nla L42 | mode.mixed | 0/84 | [0.000, 0.044] | [0.000, 0.000] | 2000 | 84 |
| q2c / local_form / nla L42 | mentions.rate | 1/84 | [0.002, 0.064] | [0.000, 0.036] | 2000 | 84 |
| q2c / local_form / nla L42 | mention_kind.quotes_token.rate | 1/84 | [0.002, 0.064] | [0.000, 0.036] | 2000 | 84 |
| q2c / local_form / nla L42 | mention_kind.states_property.rate | 0/84 | [0.000, 0.044] | [0.000, 0.000] | 2000 | 84 |
| q2c / local_form / nla L42 | mentions.accuracy | 0/1 | [0.000, 0.793] | [0.000, 0.000] | 1284 | 84 |
| q2c / local_form / nla L42 | mentions.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 84 |
| q2c / local_form / nla L42 | enacts.rate | 0/84 | [0.000, 0.044] | [0.000, 0.000] | 2000 | 84 |
| q2c / local_form / nla L42 | enacts.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 84 |
| q2c / local_form / nla L42 | enacts.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 84 |
| q2c / local_form / nla L42 | structure_tokens | 0/84 | [0.000, 0.044] | [0.000, 0.000] | 2000 | 84 |
| q2c / local_form / oracle L44 | mode.continues | 79/84 | [0.868, 0.974] | [0.881, 0.988] | 2000 | 84 |
| q2c / local_form / oracle L44 | mode.describes | 0/84 | [0.000, 0.044] | [0.000, 0.000] | 2000 | 84 |
| q2c / local_form / oracle L44 | mode.mixed | 5/84 | [0.026, 0.132] | [0.012, 0.119] | 2000 | 84 |
| q2c / local_form / oracle L44 | mentions.rate | 0/84 | [0.000, 0.044] | [0.000, 0.000] | 2000 | 84 |
| q2c / local_form / oracle L44 | mention_kind.quotes_token.rate | 0/84 | [0.000, 0.044] | [0.000, 0.000] | 2000 | 84 |
| q2c / local_form / oracle L44 | mention_kind.states_property.rate | 0/84 | [0.000, 0.044] | [0.000, 0.000] | 2000 | 84 |
| q2c / local_form / oracle L44 | mentions.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 84 |
| q2c / local_form / oracle L44 | mentions.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 84 |
| q2c / local_form / oracle L44 | enacts.rate | 55/84 | [0.548, 0.748] | [0.560, 0.750] | 2000 | 84 |
| q2c / local_form / oracle L44 | enacts.accuracy | 54/55 | [0.904, 0.997] | [0.939, 1.000] | 2000 | 84 |
| q2c / local_form / oracle L44 | enacts.resolved_accuracy | 54/54 | [0.934, 1.000] | [1.000, 1.000] | 2000 | 84 |
| q2c / local_form / oracle L44 | structure_tokens | 65/84 | [0.674, 0.850] | [0.690, 0.857] | 2000 | 84 |
| q2c / unassigned_by_Q1 / nla L42 | mode.continues | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | mode.describes | 168/168 | [0.978, 1.000] | [1.000, 1.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | mode.mixed | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | mentions.rate | 4/168 | [0.009, 0.060] | [0.006, 0.048] | 2000 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | mention_kind.quotes_token.rate | 3/168 | [0.006, 0.051] | [0.000, 0.036] | 2000 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | mention_kind.states_property.rate | 1/168 | [0.001, 0.033] | [0.000, 0.018] | 2000 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | mentions.accuracy | 0/4 | [0.000, 0.490] | [0.000, 0.000] | 1960 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | mentions.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | enacts.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | enacts.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | enacts.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / unassigned_by_Q1 / nla L42 | structure_tokens | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | mode.continues | 165/168 | [0.949, 0.994] | [0.958, 1.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | mode.describes | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | mode.mixed | 3/168 | [0.006, 0.051] | [0.000, 0.042] | 2000 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | mentions.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | mention_kind.quotes_token.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | mention_kind.states_property.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | mentions.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | mentions.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | enacts.rate | 0/168 | [0.000, 0.022] | [0.000, 0.000] | 2000 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | enacts.accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | enacts.resolved_accuracy | 0/0 | UNAVAILABLE | UNAVAILABLE | 0 | 168 |
| q2c / unassigned_by_Q1 / oracle L44 | structure_tokens | 86/168 | [0.437, 0.586] | [0.429, 0.589] | 2000 | 168 |

All additional rate leaves (composition, known-truth and subtype denominators) are in FOLLOWUP.json. Q2b nonzero edited-state accuracy remains unavailable; source agreement/target alignment are separate references.

## 2. Mention accuracy by kind

Correct/all keeps unclear in the denominator as unresolved. Correct/resolved includes only codedA/B. No code reassignment between quoting a token and stating a property.

| Sample / tier / reader | Kind | Correct/all; Wilson95; cluster95 | Correct/resolved; Wilson95; cluster95 | Unclear |
|---|---|---|---|---:|
| q1 / content / nla | quotes_token | 27/35; [0.610, 0.879]; [0.500, 1.000] | 27/27; [0.875, 1.000]; [1.000, 1.000] | 8 |
| q1 / content / nla | states_property | 43/45; [0.852, 0.988]; [0.846, 1.000] | 43/44; [0.882, 0.996]; [0.917, 1.000] | 1 |
| q1 / content / oracle | quotes_token | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q1 / content / oracle | states_property | 15/15; [0.796, 1.000]; [1.000, 1.000] | 15/15; [0.796, 1.000]; [1.000, 1.000] | 0 |
| q1 / earlier_state / nla | quotes_token | 9/65; [0.075, 0.243]; [0.037, 0.262] | 9/11; [0.523, 0.949]; [0.500, 1.000] | 54 |
| q1 / earlier_state / nla | states_property | 11/15; [0.480, 0.891]; [0.333, 1.000] | 11/12; [0.646, 0.985]; [0.600, 1.000] | 3 |
| q1 / earlier_state / oracle | quotes_token | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q1 / earlier_state / oracle | states_property | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q1 / local_form / nla | quotes_token | 55/62; [0.785, 0.944]; [0.735, 1.000] | 55/57; [0.881, 0.990]; [0.875, 1.000] | 5 |
| q1 / local_form / nla | states_property | 16/17; [0.730, 0.990]; [0.714, 1.000] | 16/17; [0.730, 0.990]; [0.714, 1.000] | 0 |
| q1 / local_form / oracle | quotes_token | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q1 / local_form / oracle | states_property | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2a / content / nla | quotes_token | 36/92; [0.298, 0.493]; [0.293, 0.490] | 36/36; [0.904, 1.000]; [1.000, 1.000] | 56 |
| q2a / content / nla | states_property | 57/58; [0.909, 0.997]; [0.940, 1.000] | 57/57; [0.937, 1.000]; [1.000, 1.000] | 1 |
| q2a / content / oracle | quotes_token | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2a / content / oracle | states_property | 6/6; [0.610, 1.000]; [1.000, 1.000] | 6/6; [0.610, 1.000]; [1.000, 1.000] | 0 |
| q2b / earlier_state / oracle | quotes_token | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2b / earlier_state / oracle | states_property | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2c / earlier_state / nla | quotes_token | 1/2; [0.095, 0.905]; [0.000, 1.000] | 1/1; [0.207, 1.000]; [1.000, 1.000] | 1 |
| q2c / earlier_state / nla | states_property | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2c / earlier_state / oracle | quotes_token | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2c / earlier_state / oracle | states_property | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2c / local_form / nla | quotes_token | 0/1; [0.000, 0.793]; [0.000, 0.000] | 0/0; UNAVAILABLE; UNAVAILABLE | 1 |
| q2c / local_form / nla | states_property | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2c / local_form / oracle | quotes_token | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2c / local_form / oracle | states_property | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2c / unassigned_by_Q1 / nla | quotes_token | 0/3; [0.000, 0.562]; [0.000, 0.000] | 0/0; UNAVAILABLE; UNAVAILABLE | 3 |
| q2c / unassigned_by_Q1 / nla | states_property | 0/1; [0.000, 0.793]; [0.000, 0.000] | 0/0; UNAVAILABLE; UNAVAILABLE | 1 |
| q2c / unassigned_by_Q1 / oracle | quotes_token | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |
| q2c / unassigned_by_Q1 / oracle | states_property | 0/0; UNAVAILABLE; UNAVAILABLE | 0/0; UNAVAILABLE; UNAVAILABLE | 0 |

## 3. Asked percentile versus majority-correct free output

Q1 only. Asked high means signed-score percentile≥0.5 within the original row/test/native-reader population. Oracle free success = at least3of4correct enactments; NLA = at least3of4correct mentions. Unclear/absent codes are not correct;2of4is a tie and not a majority. High percentile is a relative signed score, not itself an asked-answer correctness classification. Counts cover all20items per tier/reader.

| Tier / reader | Asked low: no majority | Asked low: majority | Asked high: no majority | Asked high: majority | 2/4ties |
|---|---:|---:|---:|---:|---:|
| content / nla | 2 | 6 | 1 | 11 | 0 |
| content / oracle | 1 | 8 | 0 | 11 | 0 |
| earlier_state / nla | 8 | 1 | 9 | 2 | 4 |
| earlier_state / oracle | 8 | 1 | 11 | 0 | 1 |
| local_form / nla | 1 | 8 | 1 | 10 | 0 |
| local_form / oracle | 5 | 3 | 9 | 3 | 3 |

### content / nla: discordant item IDs

Asked high, no free majority: `b13af21548c7ef62bd2ed030`.

Asked low, free majority: `4a0c11aa01b4353b2e27bbe2`, `5a57112bb8b61ef6f23cfec6`, `748c790e00795dbdb522e0dc`, `84fa0449d3d95184c7b64ffc`, `d637688e18e681df74863511`, `f3aca7d88f6c13188ede4b5d`.

### content / oracle: discordant item IDs

Asked high, no free majority: none.

Asked low, free majority: `4a0c11aa01b4353b2e27bbe2`, `77ebdc719f77a34d24b6d4a1`, `84fa0449d3d95184c7b64ffc`, `a06da19472625c9e949c0fc2`, `aad09b0812f29cdc7a20ad4e`, `bfb0d6e52b0fcb3d1b9ca738`, `d637688e18e681df74863511`, `e2006458b3ec03eb5196497f`.

### earlier_state / nla: discordant item IDs

Asked high, no free majority: `23e8847350e04065e8ab4c23`, `2ec842897432ebd93a611abc`, `598ee8ac6239d7a1de9856c3`, `6798421f103ed96620ebcf25`, `87a06d9c839a40ccfc2b6328`, `894fcc574f6c88208e8bad9d`, `b72cb3943759920e06d19c3c`, `d5143f4c70bbd116c8a76d7f`, `ddc33043b235e18ffb4a127a`.

Asked low, free majority: `52b8f9ce37419909623e220f`.

### earlier_state / oracle: discordant item IDs

Asked high, no free majority: `23e8847350e04065e8ab4c23`, `2ec842897432ebd93a611abc`, `56ce962fb4c80538be9a9435`, `598ee8ac6239d7a1de9856c3`, `6798421f103ed96620ebcf25`, `87a06d9c839a40ccfc2b6328`, `894fcc574f6c88208e8bad9d`, `b03366847f640dc062424971`, `b72cb3943759920e06d19c3c`, `d5143f4c70bbd116c8a76d7f`, `ddc33043b235e18ffb4a127a`.

Asked low, free majority: `df2cbc820f4bff124cf5f130`.

### local_form / nla: discordant item IDs

Asked high, no free majority: `3ef2302a88cfbefa6d9c7963`.

Asked low, free majority: `2022e4607d2c8147ed4ef875`, `2083dfe5d7984f9fd837e966`, `3e698f50c53445723ed7b717`, `4b2cc0ad33cd9bc372e98521`, `6d772be96f6fb4d52bd062d6`, `9883ae655ef15b2f72a08582`, `f4eb8d63158eed0096deea35`, `fe0b646fde7ae0e3597ddfd7`.

### local_form / oracle: discordant item IDs

Asked high, no free majority: `3ef2302a88cfbefa6d9c7963`, `44fb3b4571edcfdad8b36053`, `4b2cc0ad33cd9bc372e98521`, `59ae203d10bbce85ba5515b2`, `613c6f1b37b52034ef8a4b55`, `e2a8407937ba1e9a39641605`, `f46c0e11152ecb87cda8645f`, `fd5fe0d46f207a44e2f186c0`, `fe0b646fde7ae0e3597ddfd7`.

Asked low, free majority: `02807a2148ff10f1b64ff61c`, `2022e4607d2c8147ed4ef875`, `3e698f50c53445723ed7b717`.

## Pending inputs

Rater2 JSONLs exist, but no code/input-hash seal is present: κ is pending; unsealed codes are not used. Q2d is NOT DONE CURRENTLY: no finished sample/codes are present in sharedcache. DeadlineSunday25October2026,23:59CET; this is not a claim the deadline has elapsed. No API/GPU/coding calls or recurring checks were started.

## Rater2 agreement (arrived during this run)

Rater2 code-hash seal verified; it omits input hashes. Local verification additionally binds canonical sealed input hashes, full unique-ID sets and per-ID exact evidence. The prior pending statement above records the earlier preflight and is superseded by this section. No codes were repaired or excluded. Kappa uses categorical codes as delivered; NONE and unclear are separate. About/evidence/free extra prose has no meaningful semantic kappa without new coding; extra presence is compared instead. Structure-token agreement uses presence and the exact unordered set, with no new wrapper normalization.

Kappa is not a proportion; Wilson95 below is for raw agreement. Undefined kappa means a degenerate category distribution or no eligible records, not zero agreement.

| Sample | Field | n | Kappa | Raw agreement k/n [Wilson95] |
|---|---|---:|---:|---|
| q1 | mode | 480 | 0.948 | 467/480 [0.954, 0.984] |
| q1 | mentions | 480 | 0.962 | 471/480 [0.965, 0.990] |
| q1 | mention_kind | 480 | 0.703 | 394/480 [0.784, 0.853] |
| q1 | value | 480 | 0.848 | 430/480 [0.865, 0.920] |
| q1 | value_both_mention | 249 | 0.755 | 208/249 [0.784, 0.876] |
| q1 | enacts | 480 | 0.740 | 421/480 [0.845, 0.903] |
| q1 | enact_value | 480 | 0.588 | 368/480 [0.727, 0.802] |
| q1 | enact_value_both_enact | 152 | 0.471 | 99/152 [0.573, 0.723] |
| q1 | hallucination | 480 | 0.992 | 478/480 [0.985, 0.999] |
| q1 | extra_presence | 480 | 0.570 | 375/480 [0.742, 0.816] |
| q2a | mode | 300 | 0.948 | 292/300 [0.948, 0.986] |
| q2a | mentions | 300 | 0.755 | 263/300 [0.835, 0.909] |
| q2a | mention_kind | 300 | 0.654 | 237/300 [0.740, 0.832] |
| q2a | value | 300 | 0.806 | 262/300 [0.831, 0.906] |
| q2a | value_both_mention | 124 | 0.988 | 123/124 [0.956, 0.999] |
| q2a | enacts | 300 | 0.863 | 281/300 [0.903, 0.959] |
| q2a | enact_value | 300 | 0.850 | 276/300 [0.884, 0.946] |
| q2a | enact_value_both_enact | 99 | 0.904 | 94/99 [0.887, 0.978] |
| q2b | mode | 320 | UNDEFINED | 320/320 [0.988, 1.000] |
| q2b | mentions | 320 | UNDEFINED | 320/320 [0.988, 1.000] |
| q2b | mention_kind | 320 | UNDEFINED | 320/320 [0.988, 1.000] |
| q2b | value | 320 | UNDEFINED | 320/320 [0.988, 1.000] |
| q2b | value_both_mention | 0 | UNDEFINED | UNAVAILABLE |
| q2b | enacts | 320 | 1.000 | 320/320 [0.988, 1.000] |
| q2b | enact_value | 320 | 1.000 | 320/320 [0.988, 1.000] |
| q2b | enact_value_both_enact | 185 | 1.000 | 185/185 [0.980, 1.000] |
| q2b | structure_named | 320 | UNDEFINED | 320/320 [0.988, 1.000] |
| q2c | mode | 840 | 0.967 | 826/840 [0.972, 0.990] |
| q2c | mentions | 840 | 0.000 | 833/840 [0.983, 0.996] |
| q2c | mention_kind | 840 | 0.000 | 833/840 [0.983, 0.996] |
| q2c | value | 840 | 0.000 | 833/840 [0.983, 0.996] |
| q2c | value_both_mention | 0 | UNDEFINED | UNAVAILABLE |
| q2c | enacts | 840 | 0.602 | 729/840 [0.843, 0.889] |
| q2c | enact_value | 840 | 0.570 | 711/840 [0.820, 0.869] |
| q2c | enact_value_both_enact | 118 | 0.732 | 100/118 [0.772, 0.901] |
| q2c | structure_tokens_present | 840 | 0.564 | 657/840 [0.753, 0.809] |
| q2c | structure_token_set | 840 | 0.220 | 420/840 [0.466, 0.534] |

Per-tier/reader kappa for every categorical field is included in FOLLOWUP.json and RATER2_KAPPA.json. Kappa measures coder agreement, not validity; rater1/rater2 structural/quote conventions remain as delivered.

## 4. Asked-score sign versus free-text majority (44ff2b5f)

DESCRIPTIVE, registered after the previous follow-up was seen. Same signed mean paired log-odds s and unchanged≥3/4 free-majority rule. Asked favours the true value iff s>0. Nonpositive includes zero/ties; it is labelled does-not-favour-truth rather than necessarily wrong. A low within-row percentile alone is not an asked-score failure. Original percentile cross-tabs are retained separately.

| Tier / reader | s≤0: no free majority | s≤0: free majority | s>0: no free majority | s>0: free majority | s=0 |
|---|---:|---:|---:|---:|---:|
| content / nla | 2 | 1 | 1 | 16 | 0 |
| content / oracle | 1 | 5 | 0 | 14 | 0 |
| earlier_state / nla | 8 | 1 | 9 | 2 | 0 |
| earlier_state / oracle | 8 | 1 | 11 | 0 | 0 |
| local_form / nla | 1 | 7 | 1 | 11 | 0 |
| local_form / oracle | 4 | 3 | 10 | 3 | 0 |

### content / nla: sign-discordant IDs

s>0, no free majority: `b13af21548c7ef62bd2ed030`.

s≤0, free majority: `4a0c11aa01b4353b2e27bbe2`.

### content / oracle: sign-discordant IDs

s>0, no free majority: none.

s≤0, free majority: `4a0c11aa01b4353b2e27bbe2`, `77ebdc719f77a34d24b6d4a1`, `84fa0449d3d95184c7b64ffc`, `a06da19472625c9e949c0fc2`, `aad09b0812f29cdc7a20ad4e`.

### earlier_state / nla: sign-discordant IDs

s>0, no free majority: `23e8847350e04065e8ab4c23`, `2ec842897432ebd93a611abc`, `598ee8ac6239d7a1de9856c3`, `6798421f103ed96620ebcf25`, `87a06d9c839a40ccfc2b6328`, `894fcc574f6c88208e8bad9d`, `b72cb3943759920e06d19c3c`, `d5143f4c70bbd116c8a76d7f`, `ddc33043b235e18ffb4a127a`.

s≤0, free majority: `52b8f9ce37419909623e220f`.

### earlier_state / oracle: sign-discordant IDs

s>0, no free majority: `23e8847350e04065e8ab4c23`, `2ec842897432ebd93a611abc`, `56ce962fb4c80538be9a9435`, `598ee8ac6239d7a1de9856c3`, `6798421f103ed96620ebcf25`, `87a06d9c839a40ccfc2b6328`, `894fcc574f6c88208e8bad9d`, `b03366847f640dc062424971`, `b72cb3943759920e06d19c3c`, `d5143f4c70bbd116c8a76d7f`, `ddc33043b235e18ffb4a127a`.

s≤0, free majority: `df2cbc820f4bff124cf5f130`.

### local_form / nla: sign-discordant IDs

s>0, no free majority: `3ef2302a88cfbefa6d9c7963`.

s≤0, free majority: `2022e4607d2c8147ed4ef875`, `2083dfe5d7984f9fd837e966`, `3e698f50c53445723ed7b717`, `4b2cc0ad33cd9bc372e98521`, `6d772be96f6fb4d52bd062d6`, `9883ae655ef15b2f72a08582`, `f4eb8d63158eed0096deea35`.

### local_form / oracle: sign-discordant IDs

s>0, no free majority: `3ef2302a88cfbefa6d9c7963`, `44fb3b4571edcfdad8b36053`, `4b2cc0ad33cd9bc372e98521`, `59ae203d10bbce85ba5515b2`, `613c6f1b37b52034ef8a4b55`, `803d8954a1a7e6b6eb88ae84`, `e2a8407937ba1e9a39641605`, `f46c0e11152ecb87cda8645f`, `fd5fe0d46f207a44e2f186c0`, `fe0b646fde7ae0e3597ddfd7`.

s≤0, free majority: `02807a2148ff10f1b64ff61c`, `2022e4607d2c8147ed4ef875`, `3e698f50c53445723ed7b717`.

Rater2 local input binding is accepted by44ff2b5f; κ stands unchanged. Q2d status is unchanged. Original gallery narrative contained no asked-failure claim. Original sealed gallery is preserved; `GALLERY_SIGN_ANNOTATED.md` adds the signed margins without changing the selection or verbatim readouts.
