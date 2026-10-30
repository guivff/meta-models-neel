
Score the fixed A-event in BOTH states; do not infer correctness against an
unknown source-state label. Treat each provided continuation as one output.

- prose_paren: positive if there is an unmatched closing parenthesis `)` in the
  continuation (a close without an earlier available opening parenthesis).
- python_string: positive for a double quote straight after the first word, as
  in the registered discovery-study rule, OR an unmatched double quote `"`.
  A native leading bullet marker is formatting, not the first word.
- prose_sentiment_delayed: positive if a word from the frozen A-polarity lexicon
  appears. A lexicon: `wonderful`; B lexicon: `terrible`. B alone is not positive.
- fact_once: positive if the exact frozen A-number `1234` occurs, not merely as
  digits inside a longer number. B-number: `5678`. B alone is not positive.

These are event definitions, not access to the candidate parser's implementation.
