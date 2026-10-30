# E127/E128 CPU model-answer binding

Authority: direct user correction and §236 clarification4, c271590cb. E104's
behaviour scorer is pair-logit preference; it has no greedy text parser. This
binding calls the existing `core.analysis_utils.parse_target_answer` unchanged,
pinned by full-file SHA256. No synonyms, normalization, negation parser, model,
reader or logit-based override is added. The unchanged parser matches candidates
case-insensitively at word boundaries and accepts exactly one candidate. Both,
no candidate, and an empty decoded answer are **neither**. A missing/malformed raw
record is an error, not a neither answer. All registered generated answers have
at most three tokens; early EOS remains allowed.

`classifier.classify_record(raw_answer, candidate_binding)` returns `answer_value`
old/new/neither and `flipped = answer_value == 'new'`. E127 selects context-update
NEW and no-prefix OLD, using those text results only. E128 new doses2/4 use the
same text rule. Original alpha8 pair-preference flags are preserved as historical
E104 measurements; no alpha8 greedy answer is inferred or rerun. Candidate-pair
logits, if present, yield a **separate descriptive** E104 `mean(A-B)` strict-target-
preference flip. A tie is not flipped. Never combine this field with text flips.

Candidate packet: `candidates.build(e127_input_root, e128_input_root, fresh_out)`
verifies the original input/label/pointer seals and copies all per-item old/new
strings from the sealed E127 CPU packet. E128 joins by its original E104 base ID.
No generated outputs are read. All588 cell bindings and source joins remain in a
private CPU-only packet. Never stage candidate bindings or labels to pods.

For B's existing adapter vocabulary only, literal `neither`→`other` is a name
alias; preserve the raw classification field. `none`→`no_prefix` is likewise a
condition-name alias. Neither alias changes a cohort or parser rule. Adapter
owner B binds source pointers before opening outcomes; no author analysis or
once guard is invoked here. R-Q reviews the committed source on arrival.
