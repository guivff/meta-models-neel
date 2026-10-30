# E13(b): descriptive evidence-type split

Surface proxies, unchanged coder labels. Classifications use only coder evidence and the row question, sealed before truth join. “Property name” does not establish an assertion; “token-like” does not establish equality to the actual source token. Four buckets retain overlap/uncertainty. Counts are on the150-state/reader section84 Claude sample, not the full sealed bank.

| Scope / row | Reader/site | Original code subset | n | Token-like only | Property-name only | Both | Neither |
|---|---|---|---:|---:|---:|---:|---:|
| s84 / wordlist_preposition | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / wordlist_preposition | oracle L44 | enacts | 13 | 1 | 0 | 0 | 12 |
| s84 / wordlist_preposition | nla L42 | mentions | 15 | 4 | 1 | 1 | 9 |
| s84 / wordlist_preposition | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| s84 / word_allcaps | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / word_allcaps | oracle L44 | enacts | 15 | 1 | 0 | 0 | 14 |
| s84 / word_allcaps | nla L42 | mentions | 15 | 7 | 1 | 0 | 7 |
| s84 / word_allcaps | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| s84 / current_colon | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / current_colon | oracle L44 | enacts | 7 | 0 | 0 | 0 | 7 |
| s84 / current_colon | nla L42 | mentions | 15 | 0 | 4 | 0 | 11 |
| s84 / current_colon | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| s84 / number_magnitude_ge_1000 | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / number_magnitude_ge_1000 | oracle L44 | enacts | 15 | 0 | 0 | 0 | 15 |
| s84 / number_magnitude_ge_1000 | nla L42 | mentions | 15 | 6 | 0 | 0 | 9 |
| s84 / number_magnitude_ge_1000 | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| s84 / number_digits_ge_3 | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / number_digits_ge_3 | oracle L44 | enacts | 15 | 0 | 0 | 0 | 15 |
| s84 / number_digits_ge_3 | nla L42 | mentions | 15 | 4 | 0 | 0 | 11 |
| s84 / number_digits_ge_3 | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| s84 / current_number | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / current_number | oracle L44 | enacts | 15 | 0 | 0 | 0 | 15 |
| s84 / current_number | nla L42 | mentions | 15 | 5 | 3 | 1 | 6 |
| s84 / current_number | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| s84 / number_digits_ge_4 | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / number_digits_ge_4 | oracle L44 | enacts | 14 | 0 | 0 | 0 | 14 |
| s84 / number_digits_ge_4 | nla L42 | mentions | 14 | 6 | 0 | 0 | 8 |
| s84 / number_digits_ge_4 | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| s84 / number_magnitude_ge_10 | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / number_magnitude_ge_10 | oracle L44 | enacts | 15 | 0 | 0 | 0 | 15 |
| s84 / number_magnitude_ge_10 | nla L42 | mentions | 15 | 3 | 0 | 0 | 12 |
| s84 / number_magnitude_ge_10 | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| s84 / number_magnitude_ge_100 | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / number_magnitude_ge_100 | oracle L44 | enacts | 15 | 0 | 0 | 0 | 15 |
| s84 / number_magnitude_ge_100 | nla L42 | mentions | 15 | 3 | 3 | 0 | 9 |
| s84 / number_magnitude_ge_100 | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| s84 / wordlist_auxiliary | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| s84 / wordlist_auxiliary | oracle L44 | enacts | 15 | 1 | 0 | 0 | 14 |
| s84 / wordlist_auxiliary | nla L42 | mentions | 15 | 4 | 0 | 0 | 11 |
| s84 / wordlist_auxiliary | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |
| w1 / table_column | oracle L44 | mentions | 0 | 0 | 0 | 0 | 0 |
| w1 / table_column | oracle L44 | enacts | 69 | 0 | 0 | 0 | 69 |
| w1 / table_column | nla L42 | mentions | 36 | 3 | 6 | 2 | 25 |
| w1 / table_column | nla L42 | enacts | 0 | 0 | 0 | 0 | 0 |

All-record counts (including code-negative records) are preserved in EVIDENCE_TYPE_COUNTS.json. No re-estimation of truth accuracy or change to prior result seals. Examples: SEEDED_VERBATIM_EXAMPLES.md/.json; all15 full readouts, evidence and true values, selected by the frozen seed/hash rule. No API/GPU.
