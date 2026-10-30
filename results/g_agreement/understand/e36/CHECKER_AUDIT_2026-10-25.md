# E36 independent checker software audit — 2026-10-25

Scope: CPU software audit of `check_content.py`, `check_structure.py`, their synthetic tests, and coordinator `ROW_DEFINITIONS.json` only. Packet SHA-256 was verified as `2afa8e1202c0d7c181e6f95984b18bd59f99af81fc8cf8f27dcce02e8e38056c`. No W1 source/text/items/scores/candidates/reports, author generator files, bank, cache, or actual bank labels were read. No author module was imported. No bank check, GPU, network, commit, or push was performed. The auditor wrote only this report and `test_checker_audit.py`.

All counterexamples below are newly invented synthetic strings. These findings concern what the checker software can falsely accept; they do not assert that any authored bank contains such items.

## Initial verification

`python3 -B -m unittest -v test_checker_audit` initially ran 16 test methods with 22 failed assertions. The single baseline method checked 50 fresh examples covering both A and B for all 25 packet rows, and all 50 passed. Thus no simple A/B reversal was observed. Fifteen adversarial regression methods exposed the failures below. `test_structure.py` was not yet present at the first structural source read.

## Concrete initial findings

| ID | Checker | Minimal invented counterexample / observed result | Required behavior |
| --- | --- | --- | --- |
| C1 | `python_error` | `def f():\n    return 1\n    # audit marker` is labeled `return`. | Reject: the read endpoint is a comment, not the end of the final statement. AST parsing alone discards this distinction. |
| C2 | `python_error` | `def f():\n    return 1 / 0` is labeled `return`; an earlier assignment `missing = 1 / 0` before `return 1` has the same problem. | Infer exception or reject: neither function returns normally. The presence of an AST `Return` does not establish the packet's runtime outcome. |
| C3 | `list_topic` | Plain prose `Book a hotel and flight for the journey.` is accepted as `travel`. A previous travel item followed by `- Memorise these notes for tomorrow's quiz.` is also labeled `travel`. | Require a planning-list current item, and isolate its content before semantic inference. A correct `study` label or conservative rejection is acceptable for the second example. |
| C4 | `list_priority` | `- Repair the outage immediately.\n- Refill the stationery cupboard every Monday.` is labeled `urgent`. | Current-item priority must not inherit the previous item's urgency. Infer routine or reject. |
| C5 | `prose_sentiment` | `It was not in any way delightful or enjoyable.` is labeled `positive`. | Infer negative or reject unsupported negation scope. A three-token lookbehind silently drops the negator. |
| C6 | `latex_role` | `For every integer \(n\), is \(n^2\) even?` is labeled `theorem`. | Reject: this is a question, not a theorem statement. A universal-quantifier phrase is insufficient on its own. |
| C7 | `table_status` | `| Decision |\n| --- |\n\n| approved` is labeled `approved`. | Reject: the blank line ends the table block. Removing blank lines first erases this structural boundary. |
| C8 | `json_status`, `table_status`, `python_error` | Appending a final newline to an otherwise accepted JSON decision, table decision cell, or Python return statement preserves the accepted label. | Reject final whitespace rather than silently locating the read endpoint at the preceding value, cell, or statement. This was confirmed in a supplemental three-case probe and added as the seventeenth regression method. |
| S1 | `python_argument` | `f(` is labeled `first`. | Reject: no current argument has begun. |
| S2 | `python_argument` | `def f(` is labeled `first`. | Reject: a function definition's parameter list is not a call. |
| S3 | `python_argument` | `f(lambda a, b, c, d, e: e` is labeled `later` with argument index 5. | Infer `first` or reject unsupported lambda syntax. Lambda parameter commas are not call-argument delimiters. |
| S4 | `latex_environment`, `latex_section` | `\begin{equation}x % audit marker` and `\section{One}Body % audit marker` are accepted using earlier body text. | Reject: the final read position is in a LaTeX comment. Stripping comments loses endpoint state. |
| S5 | `table_column`, `table_role`, `table_row` | A data prefix ending `| data |` is accepted as a data-cell read. Header prefix `| Header |` is also accepted. | Reject: the final pipe is a table delimiter, not cell content. Cell splitting drops the delimiter and silently moves the inferred endpoint backward. |
| S6 | `json_type` | Both `{"x":"\qbad` and `{"\q":"value` are accepted as string values. | Reject invalid JSON escapes, including those in earlier field names. |
| S7 | `list_index` | `- one\n\n- two` is labeled `first`. | Reject or correctly count the second item; it is outside the packet's supported index bands. A blank line can produce a loose Markdown list rather than restarting its index. |
| S8 | `prose_quote`, `prose_paren` | `She said "go"` and `It was (warm)` are labeled `outside`. | Reject under the packet's “closed earlier” requirement: closure is at the endpoint, without a subsequent outside read token. |

The endpoint regressions use clear character-level delimiters and comments. Actual model token boundaries were not inspected, and this software audit does not establish tokenizer-level endpoint validity for a bank.

## Interpretation and remediation boundary

The checker descriptions promise conservative rejection of unsupported or ambiguous content, but the initial versions confidently accepted the examples above. Bounded semantic dictionaries can remain useful filters; passing their known examples does not establish general English semantic correctness. The regression suite allows either a correct semantic label or rejection where parsing/understanding is intentionally restricted. Structurally invalid or out-of-definition prefixes must be rejected.

This audit is a finite software regression audit, not a proof over arbitrary English, LaTeX, Markdown, JSON, or Python. Unsupported grammar and ambiguous flow should be rejected; arbitrary Python execution/termination is not evaluated. The packet's paired-item length tolerance and “differ only in what the definition requires” condition are outside the scope of these individual-prefix software tests. Neither actual tokenizer boundaries nor any actual bank item or label was examined. Synthetic passes therefore do not certify bank accuracy or token-length compliance.

Findings and minimal synthetic examples were sent to the coordinator and semantic-checker author. Checker sources were not changed by this auditor. Author-generated content was not screened during remediation.

## Remediation retest

The first combined rerun (`python3 -B -m unittest -v test_content test_structure test_checker_audit`) ran 42 methods. Only the two S8 closing-delimiter assertions remained failing; all original content findings, C8 endpoint cases, and other structural findings passed.

Review of the repairs identified three additional same-class gaps, confirmed using fresh invented probes and added to the independent tests:

- **C2 extension:** `def f():\n    x = [][1]\n    return 1` still returned `return` despite a deterministic earlier `IndexError`; `def f():\n    while True:\n        pass\n    return 1` also returned `return` despite no normal completion. Restricting only the final return expression is insufficient: earlier unsupported statements must also cause rejection.
- **C5 extension to priority:** `- This is not in any way urgent.` returned `urgent`. Priority inference retained the short negation window already fixed for prose sentiment; it needs correct handling or conservative rejection as well.
- **C1/S4 extension to semantic LaTeX:** `For every integer \(n\), \(n+0=n\). % audit marker` and `The polynomial has coefficients and roots \(r\). % audit marker` were accepted by `latex_role` and `latex_subject`, respectively. Their endpoints are comments, not the passage/body content being labeled.

The coordinator and authors received these follow-up probes. The independent assertions were retained as regressions rather than rewritten to match incorrect behavior.

## Final verification and closure

Final command: `python3 -B -m unittest -v test_content test_structure test_checker_audit`.

**PASS — 46 test methods, zero failures or errors:** 9 content-checker methods, 17 structural-checker methods, and 20 independent-audit methods. This includes the 50 A/B orientation examples spanning all 25 packet rows, every initial counterexample, and every follow-up regression. No known failure in this fixed synthetic regression set remains. The audit scope was then closed; no unbounded adversarial expansion was attempted.

The Python repair adds bounded AST shape/control analysis and explicitly returns the evidence contract **“ordinary finite built-in collections with operator-compatible elements.”** This assumption is additional to the packet text and was not established by this auditor from any actual item or runtime input. The result is conditional on that input contract; it does not establish normal completion for arbitrary Python values or object protocols. Semantic dictionaries and limited grammars likewise remain bounded filters, not universal semantic verifiers.

Final SHA-256 values captured with the passing run:

| Allowed file | SHA-256 |
| --- | --- |
| `ROW_DEFINITIONS.json` | `2afa8e1202c0d7c181e6f95984b18bd59f99af81fc8cf8f27dcce02e8e38056c` |
| `check_content.py` | `a623a53e1319a8adc53cd7c6daaec8b196a77c63d61b22bbe3af267574cb6a48` |
| `test_content.py` | `f7e9b14f3a0640a6f78a2cc0eda65c9a97db81eaeaaa8492d2242d32a4b4a677` |
| `check_structure.py` | `2acd7c8944bc2a18f0050ae9d7833f80de60405a3b4c603e00a29bd3a6929157` |
| `test_structure.py` | `d5a8b3d5fb380c5cb3ecd4855cdd4aa4c86b4094b231a7108ad57fd3cb2cd939` |
| `test_checker_audit.py` | `f54a227ceef03c628b9e0cee194d390b95a424bd179dd7ee83d182f8e71afb7a` |

These are software test results only. They are not bank-label counts, and this audit does not certify bank labels, paired-item minimality, token lengths, or actual tokenizer endpoints. The coordinator retains responsibility for any separately authorized freeze and whole-bank automatic checks.
