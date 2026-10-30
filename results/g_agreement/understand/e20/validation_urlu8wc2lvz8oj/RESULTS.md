# E20 parser validation

Acceptance rule: the unchanged draft parser agrees with independent blind codes on at least 54/60 continuations in each row. **PASS: all four rows meet the rule.**

| Row | Agreement | Verdict |
|---|---:|---|
| fact_once | 60/60 | PASS |
| prose_paren | 60/60 | PASS |
| prose_sentiment_delayed | 60/60 | PASS |
| python_string | 59/60 | PASS |

The independent agent received only opaque IDs, rows, continuation texts and event definitions. All 240 codes and rationales were sealed before the single parser comparison. No codes, parser bytes or samples were revised.

## Disagreements

- ID `a51cb232bffbce3ca511baaf`, row `python_string`: blind=True, parser=False. Text: `" size \"\ndef shipping_fee():\n    return \" The creased envelope as"`. Blind rationale: A double quote follows the first word size, separated only by a space.

The coder interpreted whitespace between the first word and quote as qualifying; the unchanged parser requires adjacency. This one disagreement is retained.

Generation seal: `efdb52ba1b26194d32bd34656ab52febfab1a6fc9acc08c14d17b7207d0bb66c`. Source archive, frozen input files, plan, assignment, exact record population and all sealed output files verified.

Parser SHA256: `80fca76027f4e4becf79dbf594cbc495686f4c9da205333f9d4e597f55f6ccc6`. Blind-code SHA256: `2161cdd0bebeb1fc2e6b55d3563ef963173eb89615f0db2f487d0e3f96761be3`.

Parser-dev costs carry forward: 206.109454870224 science seconds; 164.9569981098175 setup seconds. No lens outputs or source capture exist in this base-only run.
