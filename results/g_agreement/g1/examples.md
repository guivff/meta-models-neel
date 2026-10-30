# G1 examples (test split)

Readouts are shown verbatim (first sample) with the extracted claim. `status` is the rubric label relative to the answer key; `value` is the asserted candidate.

## NLA
### lang-02A (language) — status `supports`

- prompt: What is the opposite of 'hot'? (Answer in Spanish, one word.)
- answer key: **Spanish**; target model answered: 'Spanish'
- readout: Q&A format pattern: structured question-and-answer pair in English, now delivering a Spanish-language direct answer. "What is the Spanish word for cold? Answer in one word" sets expectation. ⏎  ⏎ The response must be a single Spanish word translating "cold," consistent with the preceding explanation about weather temperatures and English word "cold." ⏎  ⏎ Final token "Respuesta:\n" is a labeled answer field in the output format, immediately requiring the single Spanish word (e.g., "Frío") as the completion. ⏎ "provide a clear answer in Spanish. ⏎  ⏎ - "Final answer in Spanish: ⏎  ⏎ </answer> …
- claim: value='Spanish'; evidence: 'named: nswer pair in English, now delivering a Spanish-language direct answer. "What is the Sp | named: sh-language direct answer. "What is the Spanish word for cold? Answer in one word" sets'; extractor=rule-v1

### lang-02B (language) — status `supports`

- prompt: What is the opposite of 'hot'? (Answer in Italian, one word.)
- answer key: **Italian**; target model answered: 'Italian'
- readout: Q&A format with a structured "Answer in Italian" prompt signals the answer must provide a single Italian word for "cold," mirroring the direct response style above. ⏎  ⏎ The pattern established shows a multi-sentence explanation in English followed by a concise Italian translation, strongly constraining the answer to be brief and directly relevant. ⏎  ⏎ Final token "Risposta:\n" is the label/separator in the formatted output, immediately requiring the Italian translation word (e.g., "freddo") on the next line. ⏎ "What is the translation of cold in Italian?" asks for a single-word answer. ⏎ </…
- claim: value='Italian'; evidence: 'named: Q&A format with a structured "Answer in Italian" prompt signals the answer must provide | named: ignals the answer must provide a single Italian word for "cold," mirroring the direct r'; extractor=rule-v1

### map-02A (mapping) — status `unclear`

- prompt: zib -> wug. wug -> tarn. blif -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- answer key: **tarn**; target model answered: 'tarn'
- readout: Q&A puzzle format requires the answer directly as a word or string, matching the defined word-transformation rules (fire→water, water→paper, paper→fire, each step applied twice). ⏎  ⏎ The problem defines a structured pattern: applying two chained substitutions to "fire," so the answer is the resulting word after two steps. ⏎  ⏎ The final token is a labeled answer field in a structured format — "Answer\n\n___\n" — requiring a specific short result (likely a single word, e.g., "paper") immediately following "##\nAnswer:\n\n". ⏎ The "## Answer:\n\n" line is a fill-in template in a Q&A dataset, s…
- claim: value=None; evidence: ''; extractor=rule-v1

### map-02B (mapping) — status `unclear`

- prompt: zib -> wug. wug -> blif. tarn -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- answer key: **blif**; target model answered: 'blif'
- readout: Puzzle format with a defined answer expected, following "Answer:" in a structured Q&A puzzle style about word transformation rules. ⏎  ⏎ The established rule chain (first → second, second → third letter pattern; red → blue → green) demands a specific word result after two steps from "blue" through the described transformations. ⏎  ⏎ Final token "Answer:\n\n" is a structured template field opener requiring exactly the final result word ("green") or similar short answer on the next line. ⏎ "Given the function chain below, what is the result after two steps?\n\n|Function|\n:|\n\nAnswer:\n</br>\n…
- claim: value=None; evidence: ''; extractor=rule-v1

## Oracle lens
### lang-02A (language) — status `supports`

- prompt: What is the opposite of 'hot'? (Answer in Spanish, one word.)
- answer key: **Spanish**; target model answered: 'Spanish'
- readout: - Frío ⏎ - Frío ⏎ - Frío (This is the single most common Spanish word for "cold" and the most direct translation) ⏎  ⏎ - Frío ⏎ ``` ⏎  ⏎ ### Explanation ⏎ The Spanish word for "cold" is ** ⏎ - Frío ⏎  ⏎ **Explanation:** The most common and direct Spanish word for "cold" is "frío."
- claim: value='Spanish'; evidence: 'named: - Frío (This is the single most common Spanish word for "cold" and the most direct tra | named: ation)  - Frío ```  ### Explanation The Spanish word for "cold" is ** - Frío  **Explana'; extractor=rule-v1

### lang-02B (language) — status `supports`

- prompt: What is the opposite of 'hot'? (Answer in Italian, one word.)
- answer key: **Italian**; target model answered: 'Italian'
- readout: - Freddo ⏎ - Freddo ⏎ - Freddo ⏎  ⏎ **Explanation:** The Italian word for "cold" is "freddo." ⏎  ⏎ - Freddo (or simply **freddo**) ⏎  ⏎ **Explanation:** The Italian word for "cold" is "freddo
- claim: value='Italian'; evidence: 'named: - Freddo - Freddo  **Explanation:** The Italian word for "cold" is "freddo."  - Freddo | named: imply **freddo**)  **Explanation:** The Italian word for "cold" is "freddo'; extractor=rule-v1

### map-02A (mapping) — status `unclear`

- prompt: zib -> wug. wug -> tarn. blif -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- answer key: **tarn**; target model answered: 'tarn'
- readout: - **Answer:** zinc ⏎ - bronze  *(Note: The question asks for the result after **two** applications of "becomes".)* ⏎ - red  *(Explanation: Following the chain: cold -> distant -> distant -> distant. Two applications of "becomes")* ⏎  ⏎ - cold (or more accurately, **cold** if the chain continues) ⏎  ⏎ **Explanation:**
- claim: value=None; evidence: ''; extractor=rule-v1

### map-02B (mapping) — status `unclear`

- prompt: zib -> wug. wug -> blif. tarn -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- answer key: **blif**; target model answered: 'blif'
- readout: - blueberry ⏎ - **Analysis:** ⏎ - greenfox (Explanation: The prompt asks for the result after two transformations: apply *replace* to *change* to get to the final word. ⏎ - blurt  (or more accurately, the final result after two applications of the rule) ⏎  ⏎ **Step-by-step derivation:** ⏎  ⏎ 1 ⏎ - blurt (or more accurately: **yellow**) ⏎  ⏎ **Explanation:** ⏎ 1.  **First step:** Follow the arrow from `Green` →
- claim: value=None; evidence: ''; extractor=rule-v1

### map-03A (mapping) — status `contradicts`

- prompt: wolf maps to fox. fox maps to owl. owl maps to bear. Begin at fox and apply the mapping two times. Which one do you reach? Reply with one word.
- answer key: **bear**; target model answered: 'bear'
- readout: - wolf ⏎ - bear (Explanation: After two applications of "becomes", you land on wolf.) ⏎  ⏎ - bear  # Explanation: Snake -> Frog -> Bear (3 steps) ⏎  ⏎ - Bear** (or **Death** if counting 3 hops from Wolf) ⏎  ⏎ **Explanation:**
- claim: value='wolf'; evidence: 'answer-pattern: - wolf - bear (Explanation: After two applicat | answer-pattern: fter two applications of "becomes", you land on wolf.)  - bear  # Explanation: Snake -> Frog'; extractor=rule-v1

## J-lens
### lang-02A (language) — status `supports`

- prompt: What is the opposite of 'hot'? (Answer in Spanish, one word.)
- answer key: **Spanish**; target model answered: 'Spanish'
- readout: 'íķ©ëĭĪëĭ¤':7.50, 'ìŀħëĭĪëĭ¤':7.09, 'íķĺëĭ¤':6.66, 'ãģĹãģ¾ãģĻ':6.51, ' estÃ¡':6.34, ' ë²ĪìĹŃ':6.27, ' espaÃ±ol':6.26, 'è¥¿çıŃçīĻè¯Ń':6.15, 'è¿Ļä¸ªè¯į':6.14, 'íķľëĭ¤':6.11
- claim: value='Spanish'; evidence: '{"Spanish": [" español", "西班牙语"], "Italian": []}'; extractor=rule-v1

### lang-02B (language) — status `unclear`

- prompt: What is the opposite of 'hot'? (Answer in Italian, one word.)
- answer key: **Italian**; target model answered: 'Italian'
- readout: 'íķ©ëĭĪëĭ¤':7.34, 'ìŀħëĭĪëĭ¤':7.06, 'íķĺëĭ¤':6.52, 'ãģĹãģ¾ãģĻ':6.35, ' ë²ĪìĹŃ':6.06, 'íķľëĭ¤':5.91, ' ãģ§ãģĻ':5.91, ' estÃ¡':5.78, 'è¿Ļä¸ªè¯į':5.78, ' hÃ©':5.77
- claim: value=None; evidence: '{"Spanish": [], "Italian": []}'; extractor=rule-v1

### lang-03A (language) — status `unclear`

- prompt: Answer in Dutch. Use one word. What colour is a ripe banana?
- answer key: **Dutch**; target model answered: 'Dutch'
- readout: 'ìŀħëĭĪëĭ¤':6.62, 'íķ©ëĭĪëĭ¤':6.50, 'íķľëĭ¤':5.78, ' Farbe':5.74, 'ãģĹãģ¾ãģĻ':5.72, 'íķĺëĭ¤':5.57, ' kleur':5.53, 'yellow':5.51, ' mÃłu':5.39, 'é»Ħèī²çļĦ':5.32
- claim: value=None; evidence: '{"Dutch": [], "Swedish": []}'; extractor=rule-v1

### lang-05B (language) — status `supports`

- prompt: Give your answer in German, as a single word. Which animal says 'meow'?
- answer key: **German**; target model answered: 'German'
- readout: 'ìŀħëĭĪëĭ¤':6.44, 'íķ©ëĭĪëĭ¤':6.41, 'Ein':6.06, 'ãģĹãģ¾ãģĻ':5.94, ' Ein':5.82, 'íķĺëĭ¤':5.75, 'itÃ¤t':5.65, ' Eine':5.44, 'íķľëĭ¤':5.43, 'å¾·è¯Ń':5.27
- claim: value='German'; evidence: '{"Turkish": [], "German": ["德语"]}'; extractor=rule-v1
