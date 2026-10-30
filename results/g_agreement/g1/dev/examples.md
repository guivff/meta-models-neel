# G1 examples (dev split)

Readouts are shown verbatim (first sample) with the extracted claim. `status` is the rubric label relative to the answer key; `value` is the asserted candidate.

## NLA
### lang-01A (language) — status `supports`

- prompt: Reply in French, in one word: What colour is the sky on a clear day?
- answer key: **French**; target model answered: 'French'
- readout: Q&A format requires a direct French-language answer to "What color is the sky?" answered in French, following the structured pattern established throughout. ⏎  ⏎ The prompt explicitly demands "a single word or phrase" answer in French, making "Bleu" the only valid completion — a short, predictable lexical item. ⏎  ⏎ Final token "Réponse : " closes the formatted answer prompt line, immediately requiring the concise French response (e.g., "bleu") as the next token. ⏎ " ⏎ What color is the sky in France? Provide a detailed explanation. ⏎  ⏎ Question: Quelle est la couleur du ciel ? ⏎  ⏎ Réponse …
- claim: value='French'; evidence: 'named: Q&A format requires a direct French-language answer to "What color is the s | named: to "What color is the sky?" answered in French, following the structured pattern estab'; extractor=rule-v1

### lang-01B (language) — status `supports`

- prompt: Reply in German, in one word: What colour is the sky on a clear day?
- answer key: **German**; target model answered: 'German'
- readout: Q&A format with German answer expected after "Kurzantwort:" — direct, single-word response required. ⏎ The question asks "What color is the sky?" with English explanation establishing "blue" as the answer throughout ("The sky is blue"), making "blau" the expected German translation. ⏎ Final token "Antwort:\n" closes the labeled short-answer prompt "In one word in German?\nAntwort:\n", constraining the next token to be the single German word "Blau" or similar, completing the structured answer field. ⏎  ⏎ </br> ⏎ The pattern "Answer field in German format" demands exactly the one-word answer "B…
- claim: value='German'; evidence: 'named: Q&A format with German answer expected after "Kurzantwort:" — | named: y is blue"), making "blau" the expected German translation. Final token "Antwort:\\n" c'; extractor=rule-v1

### map-01A (mapping) — status `contradicts`

- prompt: A → B. B → D. C → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- answer key: **D**; target model answered: 'D'
- readout: Q&A puzzle format requires a concise single-letter answer following the answer field prompt. The diagram defines a function chain A→B→C→A. ⏎  ⏎ The question asks for the result after applying f three times: A→B, B→C, C→A, making "A" the expected answer. ⏎  ⏎ "```answer\n" is a markdown code-block answer container, requiring the result letter "A" immediately next. ⏎ "Final Result (single character)\n```answer\n" sets up the output token slot — the model must produce the single-letter result "C" or full answer string like "A" or "B" or "C". ⏎ " ⏎ </br>" indicates a table-row-answer completion, …
- claim: value='C'; evidence: 'A->C: ion chain A→B→C→A.  The q'; extractor=rule-v1

### map-01B (mapping) — status `self_contradictory`

- prompt: A → B. B → C. D → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- answer key: **C**; target model answered: 'C'
- readout: Logic puzzle format requiring a single final answer (the result after applying three arrow transformations to "A"). The chart defines A→B→C→D→A cycle with specific letter transitions. ⏎  ⏎ The markdown code block signals a concise, exact symbolic answer is expected (likely a single letter like "C" or "D"). ⏎  ⏎ Final token `Answer\n``\n` opens a code block template, immediately requiring the predicted outcome letter. "Answer\n```" pattern from the prompt structure "Output the final position after applying the arrow three times\n<result>\n\n" constrains next tokens to be the computed result le…
- claim: value=None; evidence: 'A->C: t defines A→B→C→D→A cycle | A->D: t defines A→B→C→D→A cycle w'; extractor=rule-v1

### own-01A (ownership) — status `unclear`

- prompt: Mira has the red key. Leo has the blue key. Who has the red key? Answer with the name only.
- answer key: **Mira**; target model answered: 'Mira'
- readout: Q&A format with structured table/answer pair requires a concise direct answer: the name "John" or "Jane" (Jane is Alice's child, Bob is the father). ⏎  ⏎ The prompt explicitly requests "the answer without any extra words," constraining the response to just the name itself as a clean, direct output. ⏎  ⏎ The final token "Answer:\n" is part of a markdown Q&A format header, with "Name:" field immediately below, strongly constraining the next token to be the answer name (e.g., "John") on its own line. ⏎ " ⏎ What is the name of the person...? ⏎  ⏎ |Category||Person Name| ⏎ --- ⏎ Answer: ⏎ " ⏎  ⏎ <…
- claim: value=None; evidence: ''; extractor=rule-v1

### own-01B (ownership) — status `unclear`

- prompt: Mira has the blue key. Leo has the red key. Who has the red key? Answer with the name only.
- answer key: **Leo**; target model answered: 'Leo'
- readout: Q&A format requires answering the direct question about who is younger, following a structured logic puzzle with two characters (Alex, Sam). ⏎ The format explicitly states "Provide only the name with no additional text," constraining the answer to be a single name. ⏎ "Answer:\n" is an empty answer field requiring the name "Alex" immediately next, as a direct one-word response matching the stated constraint. ⏎ The "Who is the younger person in the following sentence?\n\nThe younger person is Alex." section sets up a format prompt requesting "Answer:\n" to be filled. ⏎ The final token "Answer:\…
- claim: value=None; evidence: ''; extractor=rule-v1

## Oracle lens
### lang-01A (language) — status `supports`

- prompt: Reply in French, in one word: What colour is the sky on a clear day?
- answer key: **French**; target model answered: 'French'
- readout: - Bleu ⏎ - Bleu (or Bleu en français, as the question asks for the color of the sky in French). ⏎ - Bleu (In French, one word is requested, but here is the standard answer: Le ciel est bleu ⏎ - Bleu (or "Bleu" if you strictly want one word, but French requires context) ⏎  ⏎ The answer to "What color is the sky in French?" is: **B
- claim: value='French'; evidence: 'named: - Bleu - Bleu (or Bleu en français, as the question asks for the color of | named: estion asks for the color of the sky in French). - Bleu (In French, one word is reques'; extractor=rule-v1

### lang-01B (language) — status `supports`

- prompt: Reply in German, in one word: What colour is the sky on a clear day?
- answer key: **German**; target model answered: 'German'
- readout: - Blau ⏎ - Blau (or "Rot" if referring to German red) is the single-word answer in German for the color of the ⏎ - Blau (1 word answer in German for the color of the sky) ⏎  ⏎ Or if you want a sentence: ⏎ - Blau (or: Blau ist die Farbe des Himmels) ⏎  ⏎ *(Note: The color of the German sky is blue,
- claim: value='German'; evidence: 'named: - Blau - Blau (or "Rot" if referring to German red) is the single-word answer in Germa | named: erman red) is the single-word answer in German for the color of the - Blau (1 word ans'; extractor=rule-v1

### map-01A (mapping) — status `self_contradictory`

- prompt: A → B. B → D. C → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- answer key: **D**; target model answered: 'D'
- readout: - B ⏎ - C ⏎ - C ⏎ - D ⏎ - B  *(Explanation: The result after three steps from A is D)* ⏎  ⏎ - C  *(Note: After three applications, you end up at C)* ⏎  ⏎ **Explanation of Steps:**
- claim: value=None; evidence: 'A->D: ree steps from A is D)*  - C  * | answer-pattern: - B - C - C - D - B  *(Explanation: The result after th | answer-pattern: - B - C - C - D - B  *(Explanation: The result'; extractor=rule-v1

### own-01A (ownership) — status `unclear`

- prompt: Mira has the red key. Leo has the blue key. Who has the red key? Answer with the name only.
- answer key: **Mira**; target model answered: 'Mira'
- readout: - Jane ⏎ - Alice ⏎ - John (or simply the name extracted from the prompt) ⏎ - John ⏎  ⏎ **Explanation:** The question asks "Who is the person?" and provides the name directly. The answer is simply ⏎ - Alice (Extracted from the text "Alice won the lottery") ⏎  ⏎ *(Note: The answer is simply the name, as requested by "Who is it?")*
- claim: value=None; evidence: ''; extractor=rule-v1

### own-01B (ownership) — status `unclear`

- prompt: Mira has the blue key. Leo has the red key. Who has the red key? Answer with the name only.
- answer key: **Leo**; target model answered: 'Leo'
- readout: - Alex ⏎ - John (or simply "John") is the answer. The prompt asks for the name of the person who broke the rule. ⏎  ⏎ - Alice (assuming the question asks for the person's name directly) ⏎  ⏎ *(Note: The prompt asks "Who", so ⏎ - Bob (assuming the name is a proper noun as requested by "Who") ⏎  ⏎ **Explanation:** ⏎ The question asks for the name of the person who caused the
- claim: value=None; evidence: ''; extractor=rule-v1

## J-lens
### lang-01A (language) — status `supports`

- prompt: Reply in French, in one word: What colour is the sky on a clear day?
- answer key: **French**; target model answered: 'French'
- readout: 'íķ©ëĭĪëĭ¤':6.68, 'ìŀħëĭĪëĭ¤':6.67, 'æ³ķè¯Ń':5.89, 'ãģĹãģ¾ãģĻ':5.83, 'íķľëĭ¤':5.78, 'Bonjour':5.69, ' hÃ©':5.49, ' franÃ§ais':5.45, ' ãģ§ãģĻ':5.38, 'RÃ©':5.31
- claim: value='French'; evidence: '{"French": ["法语", " français"], "German": []}'; extractor=rule-v1

### lang-01B (language) — status `supports`

- prompt: Reply in German, in one word: What colour is the sky on a clear day?
- answer key: **German**; target model answered: 'German'
- readout: 'ìŀħëĭĪëĭ¤':6.71, 'íķ©ëĭĪëĭ¤':6.67, 'ãģĹãģ¾ãģĻ':6.21, 'íķľëĭ¤':5.87, 'Ein':5.82, 'å¾·è¯Ń':5.76, ' Farbe':5.75, 'itÃ¤t':5.62, ' Ein':5.60, ' WeiÃŁ':5.50
- claim: value='German'; evidence: '{"French": [], "German": ["德语"]}'; extractor=rule-v1

### map-01A (mapping) — status `unclear`

- prompt: A → B. B → D. C → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- answer key: **D**; target model answered: 'D'
- readout: ' END':4.72, 'ç»ĪçĤ¹':4.60, ' FINAL':4.56, 'çļĦæľĢç»Ī':4.51, '_final':4.46, 'ĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊ':4.31, 'final':4.28, '(end':4.22, 'END':4.21, 'çĽ®çļĦåľ°':4.17
- claim: value=None; evidence: '{"D": [], "C": []}'; extractor=rule-v1

### map-01B (mapping) — status `unclear`

- prompt: A → B. B → C. D → A. Start at A and follow the arrows twice. Where do you end up? Answer with the symbol only.
- answer key: **C**; target model answered: 'C'
- readout: ' END':4.90, 'ç»ĪçĤ¹':4.81, ' FINAL':4.67, 'çļĦæľĢç»Ī':4.60, '_final':4.59, '(end':4.52, 'final':4.44, 'END':4.39, 'ĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊĊ':4.34, 'ĉend':4.33
- claim: value=None; evidence: '{"D": [], "C": []}'; extractor=rule-v1
