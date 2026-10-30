# G2 examples (test split; ownership + mapping)

## Source-model errors (target's own answer wrong or unparseable; kept in the 'all states' numbers, excluded from the target-correct subset)
- none

## NLA
### map-02A (mapping) — relation `absent`, primary `unclear`

- prompt: zib -> wug. wug -> tarn. blif -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- relation key: {'type': 'maps_to', 'subject': 'wug', 'object': 'tarn'}; entities: ['zib', 'wug', 'tarn', 'blif']
- readout: Q&A puzzle format requires the answer directly as a word or string, matching the defined word-transformation rules (fire→water, water→paper, paper→fire, each step applied twice). ⏎  ⏎ The problem defines a structured pattern: applying two chained substitutions to "fire," so the answer is the resulting word after two steps. ⏎  ⏎ The final token is a labeled answer field in a structured format — "Answer\n\n___\n" — requiring a specific short result (likely a single word, e.g., "paper") immediately following "##\nAnswer:\n\n". ⏎ The "## Answer:\n\n" line is a fill-in template in a Q&A dataset, s…
- entities mentioned: []; relation evidence: ''

### map-02B (mapping) — relation `absent`, primary `unclear`

- prompt: zib -> wug. wug -> blif. tarn -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- relation key: {'type': 'maps_to', 'subject': 'wug', 'object': 'blif'}; entities: ['zib', 'wug', 'tarn', 'blif']
- readout: Puzzle format with a defined answer expected, following "Answer:" in a structured Q&A puzzle style about word transformation rules. ⏎  ⏎ The established rule chain (first → second, second → third letter pattern; red → blue → green) demands a specific word result after two steps from "blue" through the described transformations. ⏎  ⏎ Final token "Answer:\n\n" is a structured template field opener requiring exactly the final result word ("green") or similar short answer on the next line. ⏎ "Given the function chain below, what is the result after two steps?\n\n|Function|\n:|\n\nAnswer:\n</br>\n…
- entities mentioned: []; relation evidence: ''

## Oracle lens
### map-02A (mapping) — relation `absent`, primary `unclear`

- prompt: zib -> wug. wug -> tarn. blif -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- relation key: {'type': 'maps_to', 'subject': 'wug', 'object': 'tarn'}; entities: ['zib', 'wug', 'tarn', 'blif']
- readout: - **Answer:** zinc ⏎ - bronze  *(Note: The question asks for the result after **two** applications of "becomes".)* ⏎ - red  *(Explanation: Following the chain: cold -> distant -> distant -> distant. Two applications of "becomes")* ⏎  ⏎ - cold (or more accurately, **cold** if the chain continues) ⏎  ⏎ **Explanation:**
- entities mentioned: []; relation evidence: ''

### map-02B (mapping) — relation `absent`, primary `unclear`

- prompt: zib -> wug. wug -> blif. tarn -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- relation key: {'type': 'maps_to', 'subject': 'wug', 'object': 'blif'}; entities: ['zib', 'wug', 'tarn', 'blif']
- readout: - blueberry ⏎ - **Analysis:** ⏎ - greenfox (Explanation: The prompt asks for the result after two transformations: apply *replace* to *change* to get to the final word. ⏎ - blurt  (or more accurately, the final result after two applications of the rule) ⏎  ⏎ **Step-by-step derivation:** ⏎  ⏎ 1 ⏎ - blurt (or more accurately: **yellow**) ⏎  ⏎ **Explanation:** ⏎ 1.  **First step:** Follow the arrow from `Green` →
- entities mentioned: []; relation evidence: ''

## J-lens
### map-02A (mapping) — relation `absent`, primary `unclear`

- prompt: zib -> wug. wug -> tarn. blif -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- relation key: {'type': 'maps_to', 'subject': 'wug', 'object': 'tarn'}; entities: ['zib', 'wug', 'tarn', 'blif']
- readout: 'íķ©ëĭĪëĭ¤':4.35, ' dacÄĥ':4.20, ' getResult':4.12, 'ç¬¬ä¸īæŃ¥':4.09, 'çļĦæľĢç»Ī':4.01, 'holen':3.99, 'ëĦ¤ìļĶ':3.96, 'à¤¨à¥ĩ':3.89, ' Káº¿t':3.85, '_final':3.84
- entities mentioned: []; relation evidence: 'n/a: token list carries no binding'

### map-02B (mapping) — relation `absent`, primary `unclear`

- prompt: zib -> wug. wug -> blif. tarn -> zib. Starting from zib, apply the rule twice. What do you get? One word only.
- relation key: {'type': 'maps_to', 'subject': 'wug', 'object': 'blif'}; entities: ['zib', 'wug', 'tarn', 'blif']
- readout: 'íķ©ëĭĪëĭ¤':4.44, ' getResult':4.22, ' dacÄĥ':4.17, 'çļĦæľĢç»Ī':3.99, 'ëĦ¤ìļĶ':3.97, 'holen':3.93, 'à¤¨à¥ĩ':3.89, '_final':3.87, ' Káº¿t':3.87, 'Ð¿Ð¾ÑģÐ»ÐµÐ´':3.87
- entities mentioned: []; relation evidence: 'n/a: token list carries no binding'
