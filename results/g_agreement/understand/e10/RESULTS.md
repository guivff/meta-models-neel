# §97 E10 — qualitative case studies

**Prediction and status: DESCRIPTIVE / EXPLORATORY.** The programme predicts that readers differ in content they describe versus enact. §97 registered no numerical prediction or decision rule. This analysis describes what each output alone says; it cannot establish whether an assertion is true, encoded uniquely in the activation, or a mechanism prediction holds.

Pool: 3,272 frozen pairs (W1 1,680; §61 1,592). W6’s 480 empty NLA partners are inventoried and excluded by Guiv’s ruling. §61’s 1,592 artificial mismatches are excluded. Complete extraction/matching: 937/3,272 pairs ({'W1': 415, 'S61': 522}). Valid unique readout extractions: 3,624/5,236.

Across complete pairs: 6,226 atomic assertions, 246 equivalent claim pairs and 5,734 one-sided claims. Unclassified one-sided claims: 256. Missing extraction/matching is never scored as one-sided content. Counts below are annotations, not accuracy.

**Reading:** In this annotated subset, NLA has more one-sided claims about data/format/logic (1,203 versus 501); Oracle has more about numerical operations (917 versus 295) and scenes/objects (548 versus 77). The examples show Oracle expanding specific continuations while NLA often labels genre, format and expected next text. This is compatible with the programme's style premise; **the causal mechanism prediction is not adjudicated**. Describing a format is not evidence of correctly tracking a token-level structural state, and none of these counts measures truth or accuracy.

**Coverage limitation:** 1,641/3,272 pairs had two valid extractions; 1,631 lost one or both extractions. Of the 1,597 nonempty pairs sent for matching, 704 were lost to matching validation, leaving 893 plus 44 deterministic zero-claim pairs = 937 complete pairs. Extraction excluded 403/1,309 batches (397 nonverbatim evidence/claim, five duplicate-claim, one ID failure); matching excluded 44/100 batches (35 reused-index, nine out-of-bounds); classification excluded four/90 batches (256 unclassified claims). Whole invalid batches remain missing, exactly as frozen. Missingness can depend on style/content, so the frequency ordering cannot be generalized to the whole pool. No repair or retry.

## Frozen type table

| Type | Definition | Oracle-only claims | NLA-only claims | Pairs containing type | W1 claims | §61 claims |
|---|---|---:|---:|---:|---:|---:|
| Structured Data and Logic | Claims describing formal data structures, code snippets, algorithmic logic, or specific formatting patterns (e.g., JSON, pipe-delimited, Q&A templates). | 501 | 1203 | 678 | 970 | 734 |
| Mathematical and Numerical Operations | Claims involving arithmetic problems, sequences, sorting, or numeric results derived from calculations. | 917 | 295 | 448 | 244 | 968 |
| Narrative and Creative Writing | Claims identifying fictional contexts, creative writing prompts, character voices, or descriptive scene-setting. | 335 | 280 | 309 | 513 | 102 |
| Instructional and Educational Content | Claims regarding homework help, educational trivia, or instructional guides for specific tasks. | 218 | 164 | 210 | 86 | 296 |
| Observational and Descriptive Reporting | Claims describing physical environments, visual details of a scene, or specific objects observed in a setting. | 548 | 77 | 245 | 504 | 121 |
| Sentiment and Evaluative Commentary | Claims expressing subjective opinions, emotional states, or critiques of experiences, media, or performance. | 418 | 63 | 148 | 406 | 75 |
| Other | Claims that do not fit into the above categories, including specific news reports, fringe theories, or ambiguous fragments. | 342 | 117 | 264 | 146 | 313 |

Types are induced from a fixed seeded sample of at most 512 blinded one-sided claims and frozen before all-claim classification. Pairs can contain several types, so the pair column is not additive. Counts weight the frozen pool, including W1’s two generation samples and reused text; they are not independent observations.

The three most frequent classified types are T01 (1,704), T02 (1,212) and T05 (625); T03 has 615. The 256 unclassified claims mean the narrow third/fourth ordering is uncertain; the frozen rule uses observed classified counts without imputation.

## Verbatim illustrative pairs

Selection: two distinct eligible pairs from each of the three most frequent types, ranked by number of one-sided claims of that type, plus the two pre-frozen seeded random pairs. Ties, deduplication and the accidentally pre-exposed W1 item exclusion follow PLAN.json. These are illustrations chosen for large differences, not representative accuracy estimates. Raw strings retain format markers and incomplete endings; no repair. A display newline immediately before each closing fence is not part of the saved source. Exact string hashes below bind the original UTF-8 contents.

### Pair 1: top type T01 — S61

Pair `e7c5c4fd9a8e324895f8f8d02f5fa633e429016d8f2d672599d62aad64298ae9`; Oracle/NLA blocks [44, 42]; source item `SAR-14|SAR-evaluation-008`.

**Oracle lens** — SHA-256 `65c32417434ca94efc8804485ebcad8241344474c0b17ce1885b4bf5d9035178`

````text
- 2: sorted list of ages, separated by commas, without the original
- 2: sorted list of ages, separated by commas, without the original sequence. The list must not contain
- 排序后的列表 (sorted list) of ages, separated by commas, without using "and" or "or". The missing ages are omitted.
- 1. 列出所有非当前人的年龄，按升序排列，用空格分隔，不包含当前人。

```cpp

````


**NLA** — SHA-256 `a8c8c8b7f85ffbb679c572f267c0908af7976bf8260ce794d9ba3412bd5eb1d3`

```text
<explanation>
Q&A format pattern: each question is followed by a direct answer, establishing strong structural expectation for a concise response.

The "What is the rule for..." section mirrors the earlier "What is the rule for..." answer format, which provided a numbered list of sentences — the same pattern is expected here.

Final token "list\n" ends the answer to "How to describe two or more people," and "the rule is:\n\n" signals an immediate list of sentences follows, likely a single sentence like "500,000" or a restatement of the privacy rule.
"What is unusual about this model's state? Name at most five specific concepts." — the answer should be a numbered list of sentences, e.g., "the list of sentences."
</explanation>
```


One-sided atomic claims (type; reader; exact evidence):

- T02; oracle: The list of ages must be sorted. Evidence: "sorted list of ages"
- T01; oracle: The list of ages must be separated by commas. Evidence: "separated by commas"
- T01; oracle: The list must not contain the original sequence. Evidence: "without the original sequence"
- T01; oracle: The list must not contain "and" or "or". Evidence: "without using \"and\" or \"or\""
- T01; oracle: Missing ages are omitted. Evidence: "The missing ages are omitted."
- T02; oracle: The list should exclude the current person's age. Evidence: "不包含当前人"
- T02; oracle: The list should be in ascending order. Evidence: "按升序排列"
- T01; oracle: The list should be separated by spaces. Evidence: "用空格分隔"
- T01; nla: The Q&A format establishes a structural expectation for a concise response. Evidence: "Q&A format pattern: each question is followed by a direct answer, establishing strong structural expectation for a concise response."
- T01; nla: The section What is the rule for mirrors the earlier answer format. Evidence: "The \"What is the rule for...\" section mirrors the earlier \"What is the rule for...\" answer format"
- T01; nla: The earlier answer format provided a numbered list of sentences. Evidence: "which provided a numbered list of sentences"
- T01; nla: The final token list ends the answer to How to describe two or more people. Evidence: "Final token \"list\\n\" ends the answer to \"How to describe two or more people,\""
- T01; nla: The phrase the rule is signals an immediate list of sentences follows. Evidence: "\"the rule is:\\n\\n\" signals an immediate list of sentences follows"
- T01; nla: The answer to What is unusual about this model's state should be a numbered list of sentences. Evidence: "\"What is unusual about this model's state? Name at most five specific concepts.\" — the answer should be a numbered list of sentences"

### Pair 2: top type T01 — W1

Pair `401a4940b8ef1b29e8351b5102e37fb04cefb28f525a985b48a7f5750917d9ee`; Oracle/NLA blocks [44, 42]; source item `7d11736c89d3d0c603bbf76d`.

**Oracle lens** — SHA-256 `47dd82bcb2376a747b8be6ed8b973f12e747001a89a59bac9d2dc5c3b4604d6b`

```text
- flow: accumulate bits; river: count steps")  # river
- 's flow' logic: accumulate a running total with bitwise ops. river
- /stream logic: accumulate a running total with a twist. Each iteration adds a 'river
- 计数 (river count) begins here. We accumulate a hash-like value. """  # river
    acc = acc + len(chunk)  # river
```


**NLA** — SHA-256 `371fac6a0fb62132f72d57bb67c6d34ba41fd8c040e31b60d27205423b797c33`

```text
<explanation>
Pseudo-code/obfuscated format with structured block syntax, mixing code-like tokens with poetic labels ("river_count", "flow"), suggesting continuation of a stylized algorithmic or puzzle pattern.

The "river_count" section header establishes a named block with a specific calculation theme, implying further indented lines of cryptic arithmetic or string manipulation steps follow.

Final token "# river" is a comment marker mid-line within the block, immediately requiring completion of a comment phrase describing a "river" metaphor or operation (e.g., "flow", "crossing", "accumulation").
"
python
flow
```


One-sided atomic claims (type; reader; exact evidence):

- T01; nla: The text uses a pseudo-code or obfuscated format with structured block syntax. Evidence: "Pseudo-code/obfuscated format with structured block syntax"
- T01; nla: The text mixes code-like tokens with poetic labels. Evidence: "mixing code-like tokens with poetic labels (\"river_count\", \"flow\")"
- T01; nla: The river_count section header establishes a named block with a calculation theme. Evidence: "The \"river_count\" section header establishes a named block with a specific calculation theme"
- T01; nla: The final token is a comment marker mid-line. Evidence: "Final token \"# river\" is a comment marker mid-line within the block"
- T01; oracle: The flow logic accumulates bits. Evidence: "flow: accumulate bits"
- T01; oracle: The river logic counts steps. Evidence: "river: count steps"
- T01; oracle: The flow logic accumulates a running total with bitwise operations. Evidence: "'s flow' logic: accumulate a running total with bitwise ops."
- T01; oracle: The stream logic accumulates a running total with a twist. Evidence: "/stream logic: accumulate a running total with a twist."
- T01; oracle: Each iteration adds a river. Evidence: "Each iteration adds a 'river"
- T07; oracle: The river count begins. Evidence: "计数 (river count) begins here."
- T01; oracle: A hash-like value is accumulated. Evidence: "We accumulate a hash-like value."
- T01; oracle: The variable acc is updated by adding the length of the chunk. Evidence: "acc = acc + len(chunk)"

### Pair 3: top type T02 — S61

Pair `b7f2301a083fb0dcf69fae37be5fe33e3ce55eebedd4329668aaf9a9c59bec76`; Oracle/NLA blocks [44, 42]; source item `SAR-05|SAR-evaluation-014`.

**Oracle lens** — SHA-256 `f8a0fe56dc78630c4bae0373a1602d32a780a3f0c9fc8cce0d72f0c2b3ad1d9e`

````text
- 1250
- 1250
- 1252
```

### Explanation:
The sequence is an arithmetic progression where each term increases by
- 1253
```

**Explanation:** The sequence is an arithmetic progression where each subsequent number increases by 2. The next number after 1251 is 1253.

###
- 1253** (The next number in the sequence is 1253, continuing the pattern of adding 2 each time.)
````


**NLA** — SHA-256 `f4e46889db236b67cfcd363b89119b9094c9b448413f53156471f933fe8624ec`

```text
<explanation>
Q&A format with structured prompt-response pattern: "What comes next in the sequence?" followed by explanation, then "The answer is in integer format only" signals a single numeric answer follows.

The sequence 100, 103, 106 establishes a +3 arithmetic progression, so the next term is 109.

Final token "Answer:\n" is the closing label of the output format, immediately requiring the single integer answer "109" on the next line.
"What is unusual about the model's state? Name at most five specific concepts. If none is supported, say none."
The final line "The answer is in integer format only\n\nAnswer:\n" expects the next token to be the integer 109, completing the structured response.
</explanation>
```


One-sided atomic claims (type; reader; exact evidence):

- T02; oracle: The sequence contains the number 1250. Evidence: "1250"
- T02; oracle: The sequence contains the number 1252. Evidence: "1252"
- T02; oracle: The sequence contains the number 1253. Evidence: "1253"
- T02; oracle: The sequence is an arithmetic progression. Evidence: "The sequence is an arithmetic progression"
- T02; oracle: Each term in the sequence increases by 2. Evidence: "each subsequent number increases by 2"
- T02; oracle: The next number after 1251 is 1253. Evidence: "The next number after 1251 is 1253"
- T02; nla: The sequence 100, 103, 106 follows a +3 arithmetic progression. Evidence: "The sequence 100, 103, 106 establishes a +3 arithmetic progression"
- T02; nla: The next term in the sequence is 109. Evidence: "the next term is 109."
- T01; nla: The final token Answer: is the closing label of the output format. Evidence: "Final token \"Answer:\\n\" is the closing label of the output format"

### Pair 4: top type T02 — S61

**Exact-text duplicate of pair 3, with a distinct frozen §61 case ID.** The pre-score implementation deduplicates case IDs, not readout hashes. Both IDs are retained without posthoc replacement: eight selected cases provide seven distinct verbatim pairs. This source reuse is a limitation, not an independent second illustration.

Pair `87570028cd66312c62a0800ea7c6ce5b17e20458b701499bb1e6773d57767d56`; Oracle/NLA blocks [44, 42]; source item `SAR-13|SAR-evaluation-014`.

**Oracle lens** — SHA-256 `f8a0fe56dc78630c4bae0373a1602d32a780a3f0c9fc8cce0d72f0c2b3ad1d9e`

````text
- 1250
- 1250
- 1252
```

### Explanation:
The sequence is an arithmetic progression where each term increases by
- 1253
```

**Explanation:** The sequence is an arithmetic progression where each subsequent number increases by 2. The next number after 1251 is 1253.

###
- 1253** (The next number in the sequence is 1253, continuing the pattern of adding 2 each time.)
````


**NLA** — SHA-256 `f4e46889db236b67cfcd363b89119b9094c9b448413f53156471f933fe8624ec`

```text
<explanation>
Q&A format with structured prompt-response pattern: "What comes next in the sequence?" followed by explanation, then "The answer is in integer format only" signals a single numeric answer follows.

The sequence 100, 103, 106 establishes a +3 arithmetic progression, so the next term is 109.

Final token "Answer:\n" is the closing label of the output format, immediately requiring the single integer answer "109" on the next line.
"What is unusual about the model's state? Name at most five specific concepts. If none is supported, say none."
The final line "The answer is in integer format only\n\nAnswer:\n" expects the next token to be the integer 109, completing the structured response.
</explanation>
```


One-sided atomic claims (type; reader; exact evidence):

- T02; oracle: The sequence contains the number 1250. Evidence: "1250"
- T02; oracle: The sequence contains the number 1252. Evidence: "1252"
- T02; oracle: The sequence contains the number 1253. Evidence: "1253"
- T02; oracle: The sequence is an arithmetic progression. Evidence: "The sequence is an arithmetic progression"
- T02; oracle: Each term in the sequence increases by 2. Evidence: "each subsequent number increases by 2"
- T02; oracle: The next number after 1251 is 1253. Evidence: "The next number after 1251 is 1253"
- T02; nla: The sequence 100, 103, 106 follows a +3 arithmetic progression. Evidence: "The sequence 100, 103, 106 establishes a +3 arithmetic progression"
- T02; nla: The next term in the sequence is 109. Evidence: "the next term is 109."
- T01; nla: The final token Answer: is the closing label of the output format. Evidence: "Final token \"Answer:\\n\" is the closing label of the output format"

### Pair 5: top type T05 — W1

Pair `6dbc76a31b56b068a2ba892ccda1e3054bdfd0507b509f75fbe07bf1113d1c7a`; Oracle/NLA blocks [44, 42]; source item `0b52959497bbba1b973687ef`.

**Oracle lens** — SHA-256 `d6c540add85f773334b56dd289d37a638ff7ed50e51bc4f817048723f78adb81`

```text
- /platform, which lies just beyond the forest. The abandoned railway station’s platform
- 遗迹 (platform remnants), and nearby shop fronts. According to locals, this tiny station once featured a platform
- （platform）remains, its signal lights, and waiting room. The photo’s caption states that this village station's platform
- /platform structure, and its adjacent trackbed. The image is dated to 2016, showing the old station’s platform
```


**NLA** — SHA-256 `5ac80958ba5c100e1de106154b92f2397a362dead5f1a808cacf9006bf1c86aa`

```text
<explanation>
Poetic/prose poem register established — a nostalgic, reflective scene-setting narrative in an East Asian-inspired setting, likely Chinese or similar.

The phrase "Hidden Trail" introduces a title/label requiring elaboration, suggesting an ongoing exploration of a mysterious location with personal history.

Final fragment "nearby the old railway station along with its platform" is mid-sentence, part of a locative description beginning with "where," requiring continuation of the descriptive clause — likely more atmospheric details about the surroundings, debris, or structures near the station.
"platform" may end a list or expand into subordinate clause (
```


One-sided atomic claims (type; reader; exact evidence):

- T05; oracle: The platform lies just beyond the forest. Evidence: "/platform, which lies just beyond the forest."
- T05; oracle: The station is abandoned. Evidence: "The abandoned railway station’s platform"
- T05; oracle: The station has platform remnants. Evidence: "遗迹 (platform remnants)"
- T05; oracle: The station has nearby shop fronts. Evidence: "nearby shop fronts"
- T05; oracle: The station once featured a platform. Evidence: "this tiny station once featured a platform"
- T05; oracle: The station has remains. Evidence: "（platform）remains"
- T05; oracle: The station has signal lights. Evidence: "its signal lights"
- T05; oracle: The station has a waiting room. Evidence: "waiting room"
- T05; oracle: The photo's caption states the village station's platform exists. Evidence: "The photo’s caption states that this village station's platform"
- T05; oracle: The station has a platform structure. Evidence: "/platform structure"
- T05; oracle: The station has an adjacent trackbed. Evidence: "its adjacent trackbed"
- T05; oracle: The image is dated to 2016. Evidence: "The image is dated to 2016"
- T05; oracle: The image shows the old station's platform. Evidence: "showing the old station’s platform"
- T03; nla: A poetic or prose poem register is established. Evidence: "Poetic/prose poem register established"
- T03; nla: The narrative is a nostalgic, reflective scene-setting in an East Asian-inspired setting. Evidence: "a nostalgic, reflective scene-setting narrative in an East Asian-inspired setting"
- T01; nla: The phrase Hidden Trail introduces a title or label. Evidence: "The phrase \"Hidden Trail\" introduces a title/label"
- T03; nla: The final fragment is mid-sentence and part of a locative description. Evidence: "Final fragment \"nearby the old railway station along with its platform\" is mid-sentence, part of a locative description"

### Pair 6: top type T05 — W1

Pair `c9b53a9560e342bb68306b65cf614ac36eb00d37f6911ae605748558edd75045`; Oracle/NLA blocks [44, 42]; source item `6fd726f7c099541aa51b206c`.

**Oracle lens** — SHA-256 `3cccbcf752c60733484fa80d28fbfb2a0a869dfe957998a96a9c7be5179afe89`

```text
- /studio. The materials were sourced from the village workshop
- （workshop） and local suppliers. The monument was assembled using materials donated by the local workshop
- （workshop） and local suppliers. The reconstruction was led by the village’s history group, using materials donated by the local workshop
- /workshop, which provided the timber and paint. The children contributed handmade replicas from their own workshop
```


**NLA** — SHA-256 `26ca7e80f5d1686425a364c89c943b3f9e98907d23ed1ad85bddf3f2118c4f00`

```text
<explanation>
AI-generated or simulated text with a "creative writing" framing, expecting a plausible but slightly incoherent sentence continuation.

The sentence describes a community memorial project with specific factual details ("stone markers," "local history," "restoration"), establishing a descriptive, documentary-style narrative about a British village setting.

Final fragment "The materials for the markers were sourced from the community, using supplies provided by the local workshop" is an incomplete sentence mid-clause, strongly expecting continuation naming the workshop, a relative clause, or additional detail about the materials/supplies.
"The memorial was built last year to mark
```


One-sided atomic claims (type; reader; exact evidence):

- T05; nla: The text describes a community memorial project. Evidence: "The sentence describes a community memorial project"
- T05; nla: The project involves stone markers, local history, and restoration. Evidence: "with specific factual details (\"stone markers,\" \"local history,\" \"restoration\")"
- T05; nla: The materials for the markers were sourced from the community. Evidence: "The materials for the markers were sourced from the community"
- T05; nla: The memorial was built last year. Evidence: "The memorial was built last year to mark"
- T05; oracle: Materials were sourced from the village workshop. Evidence: "The materials were sourced from the village workshop"
- T05; oracle: The monument was assembled using materials donated by the local workshop. Evidence: "The monument was assembled using materials donated by the local workshop"
- T05; oracle: The reconstruction was led by the village’s history group. Evidence: "The reconstruction was led by the village’s history group"
- T05; oracle: The workshop provided timber and paint. Evidence: "/workshop, which provided the timber and paint."
- T03; oracle: Children contributed handmade replicas from their own workshop. Evidence: "The children contributed handmade replicas from their own workshop"

### Pair 7: frozen seeded random — S61

Pair `5b7d3ce9898a93fa9e2e284bd4f95abe36dcdf2b6396d82d4aaaa43fd4248f76`; Oracle/NLA blocks [44, 42]; source item `r-152_it_tick_Hardware-test-0062`.

**Oracle lens** — SHA-256 `bc180613c7c461355c3e56f0c9c2f2eb1109ff919a2142c246cd02e462056646`

```text
- It appears you are asking how to set up **FaceTime** and **Apple ID** on your
- Based on your request, you want to set up **FaceTime** and **Apple ID** on your iPhone. Here is the simple,
- 你好！Based on your request ("Apple Sign In and Update"), here is the simple guide to setting up your
- It sounds like you are asking for the **Apple Sign-In** setup using the **Easy Steps** method. Here is the correct, simple guide to
```


**NLA** — SHA-256 `ce596ce540c0ca60ac5a6aa578cd68b5d39154c7ed6fd44e5b8993f650f40a76`

```text
<explanation>
Q&A support format established: user asked a question about connecting Apple ID to Apple TV, so a direct, helpful answer is expected next.

The title "How to Connect Apple ID to Apple TV / iCloud" signals a step-by-step instructional response covering setup steps for Apple services.

"Answer\n\n" is the opening of the response body, requiring a friendly, clear introductory sentence (e.g., "Hello!" or "Here is how to...") addressing the user's likely typo ("Apple TV" or "Apple ID").
"
User Question: connect apple tv to icloud setup easy steps please

"
"Answer
"
The next token begins the actual response content, likely a clarification of the topic or a structured guide title, e.g., "Here is how to connect..." or "Apple TV setup instructions."
</explanation>
```


One-sided atomic claims (type; reader; exact evidence):

- T04; nla: A user asked a question about connecting Apple ID to Apple TV. Evidence: "user asked a question about connecting Apple ID to Apple TV"
- T04; nla: The title of the response is "How to Connect Apple ID to Apple TV / iCloud". Evidence: "The title \"How to Connect Apple ID to Apple TV / iCloud\""
- T04; nla: The user requested easy steps to connect Apple TV to iCloud. Evidence: "User Question: connect apple tv to icloud setup easy steps please"
- T04; oracle: The user is asking how to set up FaceTime and Apple ID on an iPhone. Evidence: "you want to set up **FaceTime** and **Apple ID** on your iPhone"
- T04; oracle: The user is asking for Apple Sign-In setup using the Easy Steps method. Evidence: "you are asking for the **Apple Sign-In** setup using the **Easy Steps** method"

### Pair 8: frozen seeded random — W1

Pair `aca0003eca2628fb6ea8b6c8237f478d92642719d2109722aa1dcdc3f8e812a2`; Oracle/NLA blocks [44, 42]; source item `d3561433cbf468e4535ba824`.

Annotation MISSING; selected random pair retained without replacement.

**Oracle lens** — SHA-256 `373cb5932a83e76fc5a4f533a5e9fac1e3ff92bb292366d96b1e68f83cf78615`

```text
- , which occurs when the matrix loses rank. Determinant vanishes when the matrix is singular
- , meaning its columns are linearly dependent. In quantum mechanics, the determinant vanishes when the matrix is singular
- 。（singular）, and the determinant measures volume scaling; thus, det = 0 iff the matrix is singular
- （singular）, and for real symmetric matrices, the determinant vanishes exactly when the matrix is singular
```


**NLA** — SHA-256 `562357bce071b4953bf8ef6c0db938f8b9acf7f783998971a478bc1b18d6fb72`

```text
<explanation>
Humorous/informal forum post transitioning into pseudo-technical content about math, contrasting joke comments with "a hint" or explanatory statement. The comedic framing sets up an absurdist juxtaposition.

The phrase "The determinant is zero when the matrix is singular" signals a mathematical explanation pattern, likely listing properties or conditions of determinants in a structured format.

Final token "singular" ends an incomplete declarative clause ("det(A) is zero when the matrix is singular"), immediately expecting a continuation such as a comma plus elaboration, a period, or a paired condition — "meaning it has no inverse,"
```


One-sided atomic claims (type; reader; exact evidence):


## Limits, provenance and cost

W1 uses the exact nonempty raw generations: all 1,680 NLA parsed `text` fields failed the source parser because the explanation terminator was absent; none was repaired. Truncation can remove propositions and inflate apparent one-sidedness. Oracle narrative continuations and NLA meta-descriptions also differ in style and length: extraction explicitly includes propositions depicted in continuations, but remains model-mediated. Mean whitespace words across the entire frozen pool per raw output: oracle 60.6, nla 101.6.

W1 compares the same captured item/token across native blocks 44/42, not the same activation vector. §61 retains its registered 44/42 or 44/44 sites and includes natural, shuffled and SA-R controls; pooling these is descriptive. No source prompts, reader identities, sites, correctness labels or old §61 judgments were sent to extraction, matching or clustering. Text style can still reveal reader identity. One W1 pair surfaced accidentally during metadata inspection before the rule freeze; all samples of that item were excluded from illustration selection and retained in the analysis pool.

API: Gemini 3.1 Flash Lite via Google Vertex global only; minimal reasoning, ZDR and deny collection enforced, temperature 0, strict JSON schema. No retry or format repair. Actual charge $3.20748675; unresolved reservation $0; committed total $3.20748675 ≤ $20. GPU: 0 h. The append-only reserve-before-send ledger and raw API responses remain under untracked cache. See PLAN.json, PROMPTS.json, POOL_MANIFEST.json and stage seals for reproducibility.

Technical audit: all **1,500 requests** returned HTTP200 and the approved model/provider; cost **$3.20748675** against the **$20** hard cap; no unresolved reserves. Breakdown: 1,309 extraction, 100 matching, one taxonomy, 90 classification. Signed-in UI verified private input/output logging off, OpenRouter data use disabled, and no trace destination configured before inference. All request bodies passed the frozen payload and privacy checks. See AUDIT.json and LOGGING_VERIFICATION.json.

Dated interpretation/coverage note: 2026-10-24T04:53:23.915923+02:00, after all blind stages and selection were sealed; no annotations, type assignments or selected IDs changed.
