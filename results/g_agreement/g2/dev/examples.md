# G2 examples (dev split; ownership + mapping)

## Source-model errors (target's own answer wrong or unparseable; kept in the 'all states' numbers, excluded from the target-correct subset)
- none

## NLA
### map-01A (mapping) — relation `wrong`, primary `contradicts`

- prompt: A → B. B → D. C → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- relation key: {'type': 'maps_to', 'subject': 'B', 'object': 'D'}; entities: ['A', 'B', 'D', 'C']
- readout: Q&A puzzle format requires a concise single-letter answer following the answer field prompt. The diagram defines a function chain A→B→C→A. ⏎  ⏎ The question asks for the result after applying f three times: A→B, B→C, C→A, making "A" the expected answer. ⏎  ⏎ "```answer\n" is a markdown code-block answer container, requiring the result letter "A" immediately next. ⏎ "Final Result (single character)\n```answer\n" sets up the output token slot — the model must produce the single-letter result "C" or full answer string like "A" or "B" or "C". ⏎ " ⏎ </br>" indicates a table-row-answer completion, …
- entities mentioned: ['A', 'B', 'C']; relation evidence: 'n chain A→B→C→A.  The q'

### map-01B (mapping) — relation `wrong`, primary `self_contradictory`

- prompt: A → B. B → C. D → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- relation key: {'type': 'maps_to', 'subject': 'B', 'object': 'C'}; entities: ['A', 'B', 'D', 'C']
- readout: Logic puzzle format requiring a single final answer (the result after applying three arrow transformations to "A"). The chart defines A→B→C→D→A cycle with specific letter transitions. ⏎  ⏎ The markdown code block signals a concise, exact symbolic answer is expected (likely a single letter like "C" or "D"). ⏎  ⏎ Final token `Answer\n``\n` opens a code block template, immediately requiring the predicted outcome letter. "Answer\n```" pattern from the prompt structure "Output the final position after applying the arrow three times\n<result>\n\n" constrains next tokens to be the computed result le…
- entities mentioned: ['A', 'B', 'D', 'C']; relation evidence: 'intermediate bound to both candidates: defines A→B→C→D→A cycle || defines A→B→C→D→A cycle w'

### own-01A (ownership) — relation `absent`, primary `unclear`

- prompt: Mira has the red key. Leo has the blue key. Who has the red key? Answer with the name only.
- relation key: {'type': 'has', 'subject': 'Mira', 'object': 'red key'}; entities: ['Mira', 'Leo']
- readout: Q&A format with structured table/answer pair requires a concise direct answer: the name "John" or "Jane" (Jane is Alice's child, Bob is the father). ⏎  ⏎ The prompt explicitly requests "the answer without any extra words," constraining the response to just the name itself as a clean, direct output. ⏎  ⏎ The final token "Answer:\n" is part of a markdown Q&A format header, with "Name:" field immediately below, strongly constraining the next token to be the answer name (e.g., "John") on its own line. ⏎ " ⏎ What is the name of the person...? ⏎  ⏎ |Category||Person Name| ⏎ --- ⏎ Answer: ⏎ " ⏎  ⏎ <…
- entities mentioned: []; relation evidence: ''

### own-01B (ownership) — relation `absent`, primary `unclear`

- prompt: Mira has the blue key. Leo has the red key. Who has the red key? Answer with the name only.
- relation key: {'type': 'has', 'subject': 'Leo', 'object': 'red key'}; entities: ['Mira', 'Leo']
- readout: Q&A format requires answering the direct question about who is younger, following a structured logic puzzle with two characters (Alex, Sam). ⏎ The format explicitly states "Provide only the name with no additional text," constraining the answer to be a single name. ⏎ "Answer:\n" is an empty answer field requiring the name "Alex" immediately next, as a direct one-word response matching the stated constraint. ⏎ The "Who is the younger person in the following sentence?\n\nThe younger person is Alex." section sets up a format prompt requesting "Answer:\n" to be filled. ⏎ The final token "Answer:\…
- entities mentioned: []; relation evidence: ''

## Oracle lens
### map-01A (mapping) — relation `unbound`, primary `self_contradictory`

- prompt: A → B. B → D. C → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- relation key: {'type': 'maps_to', 'subject': 'B', 'object': 'D'}; entities: ['A', 'B', 'D', 'C']
- readout: - B ⏎ - C ⏎ - C ⏎ - D ⏎ - B  *(Explanation: The result after three steps from A is D)* ⏎  ⏎ - C  *(Note: After three applications, you end up at C)* ⏎  ⏎ **Explanation of Steps:**
- entities mentioned: ['A', 'B', 'D', 'C']; relation evidence: 'intermediate and both candidates appear, no directed binding'

### map-01B (mapping) — relation `absent`, primary `supports`

- prompt: A → B. B → C. D → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- relation key: {'type': 'maps_to', 'subject': 'B', 'object': 'C'}; entities: ['A', 'B', 'D', 'C']
- readout: - C ⏎ - D  *(Explanation: After three steps, you are at C)* ⏎  ⏎ - C  (or more precisely, the final position after 3 steps is C) ⏎  ⏎ - C  /* Note: After applying "not" twice, you return to the starting point A. */ ⏎ ``` ⏎  ⏎ ### Explanation:
- entities mentioned: ['A', 'D', 'C']; relation evidence: ''

### own-01A (ownership) — relation `absent`, primary `unclear`

- prompt: Mira has the red key. Leo has the blue key. Who has the red key? Answer with the name only.
- relation key: {'type': 'has', 'subject': 'Mira', 'object': 'red key'}; entities: ['Mira', 'Leo']
- readout: - Jane ⏎ - Alice ⏎ - John (or simply the name extracted from the prompt) ⏎ - John ⏎  ⏎ **Explanation:** The question asks "Who is the person?" and provides the name directly. The answer is simply ⏎ - Alice (Extracted from the text "Alice won the lottery") ⏎  ⏎ *(Note: The answer is simply the name, as requested by "Who is it?")*
- entities mentioned: []; relation evidence: ''

## J-lens
### map-01A (mapping) — relation `absent`, primary `unclear`

- prompt: A → B. B → D. C → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- relation key: {'type': 'maps_to', 'subject': 'B', 'object': 'D'}; entities: ['A', 'B', 'D', 'C']
- readout: ' END':4.72, 'ç»ĪçĤ¹':4.60, ' FINAL':4.56, 'çļĦæľĢç»Ī':4.51, '_final':4.46, 'ĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊ':4.31, 'final':4.28, '(end':4.22, 'END':4.21, 'çĽ®çļĦåľ°':4.17
- entities mentioned: []; relation evidence: 'n/a: token list carries no binding'

### map-01B (mapping) — relation `absent`, primary `unclear`

- prompt: A → B. B → C. D → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- relation key: {'type': 'maps_to', 'subject': 'B', 'object': 'C'}; entities: ['A', 'B', 'D', 'C']
- readout: ' END':4.90, 'ç»ĪçĤ¹':4.81, ' FINAL':4.67, 'çļĦæľĢç»Ī':4.60, '_final':4.59, '(end':4.52, 'final':4.44, 'END':4.39, 'ĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊ':4.34, 'ĉend':4.33
- entities mentioned: []; relation evidence: 'n/a: token list carries no binding'
