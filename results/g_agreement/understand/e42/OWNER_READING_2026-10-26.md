# E42 pre-compute definition audit — HOLD

No persistence value, new continuation, score join, or GPU call has been computed. No state-function seal is claimed. The earlier experiments' outcomes are already present in this chat; E42 preserves procedural separation by not opening or joining their score files before the persistence seal.

Required coordinator rulings, requested in chat:

1. Supply the exact 19 W1 structure row IDs and frozen bank/checker/input-seal paths. Do not select rows by reading score values. The 16 shared E36 structure definitions are inventoried in DEFINITION_AUDIT_2026-10-26.json; W1 bins must not be inferred from v2 bins.
2. Define OUT_OF_DOMAIN versus UNRESOLVED behavior at every token extension. Example: python_depth depth 2 lies outside {1,3}; python_indent uses ast.parse and rejects incomplete syntax; table_column rejects delimiter endpoints and intermediate columns; prose checkers reject closing delimiters at the endpoint. Treating every exception as state loss would measure parser acceptance, not registered persistence. No exception is silently converted to a label.
3. W12 syntax_role, sentence_type and clause_embedding lack deterministic general state checkers in the frozen builder. Syntax_role also needs a ruling on original noun versus new endpoint. Do not invent a grammar or freeze label-constant functions. Sentence/paragraph counting needs explicit boundary and gap semantics (e.g. sentence_position words 4–12; paragraph_index paragraph 2).
4. §102's E1b next16 is generated greedily, not source continuation. E36/W12 builders retain prefixes ending at the read token, not authored post-read text. Clarify generated-next16 reuse/extension versus fresh greedy32 and treatment of unavailable source tails or EOS before 32; never relabel generated material as true text.

Independent completed work: a loader-free persistence primitive implements the largest uninterrupted matching prefix, validates the original label and stops on unresolved states or missing horizon. Five synthetic CPU tests cover 0/32 endpoints, first failure despite later recovery, checker errors, missing tokens and label mismatch. This primitive is not a sealed row-state implementation.

The once-only scientific analysis command and any ≤1,080-second GPU request must remain unready until the definition and following-text policies are resolved. No previously sealed result or definition is changed. Await a dated §151 clarification before generating or measuring anything.
