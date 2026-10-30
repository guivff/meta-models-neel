# Literature review: what activation readers say, what probes find, and what readers leave out

Written 2026-10-26 for the Qwen3.6-27B activation-readers project. Inputs: `scope_brief.md`, `hypothesis_brief.md`.

**Tags.** **[V]** means I fetched the paper or post in this session and checked the claim against its text or a faithful summary of it. **[R]** means I recalled the claim from memory and did not re-check it. Treat [R] numbers as approximate and confirm them before you cite them in the writeup.

---

## 0. Summary

1. **Other readers fail in the same way.** No published reader evaluation includes this project's row type: a binary, lexically controlled syntactic state with a probe ceiling. The nearest results all show the same pattern, though. Reconstruction-trained and QA-trained verbalizers recover the **gist and content concepts** of an activation. They lose or confabulate **specifics that depend on order, composition or exact value**: role bindings, multi-digit numbers, intermediate values and missing-information states. WorkspaceBench, which uses this same model, lists "thief chases policeman" role bindings, multi-digit numbers, conjunctive states and buggy-code consequences as things single-token readers miss [V]. Dingeto (2026) finds the released Qwen-2.5-7B NLA reconstructs at about 0.84. Yet only about 2% of its salient specific claims are grounded, and the reconstruction score collapses to 0.04 when content words are masked [V]. That is direct evidence that reconstruction reward is carried by content words.
2. **Probes show "known but not said" for many consequential properties.** Examples: user traits (probe 0.94–0.98 vs prompting 0.45–0.86) [V], response plans (probe far above self-prediction) [V], facts (+40% relative internal over external) [V], syntax (probe ≥ LM-head ≥ behaviour on all 14 conditions) [V], and CoT hint use (verbalized 25–39%) [R/V-snippet]. Two 2026 reader papers localise the failure in the reader's mapping to words, not in the representation. Bersia et al. ("anti-reading") can probe the concept from the oracle's middle layers, while late layers suppress the answer [V]. Dingeto finds the probe-vs-verbalizer gap survives reconstructor scale, a direct truth reward and extra injection bandwidth [V]. This matches your facts 4 and 5.
3. **A sharper framing than "syntactic state."** Your blind spot may be a sample of a larger class: **properties that are not identifiable from the multiset of content words**. That class covers order, binding, nesting, counts and exact values. The literature above predicts the reader is blind to the whole class, not just to punctuation. Your sayable exceptions fit this framing only partly; see the tension note in §4.
4. **The most informative additions (§4) hold the bag of words fixed and flip only the relation.** In order:
   - (A) role binding / coreference with the same names in both arms;
   - (B) world state after an update (object location after a move);
   - (C) arithmetic state such as carry or comparison;
   - (D) code *semantic* state, such as whether a branch is taken, as opposed to code syntax;
   - (E) a consequential *sayable* control: a user-model trait.

   If A–D fail like parenthesis while E passes, the result is no longer a curiosity about punctuation. It becomes "the verbalizer cannot report relational and computational state."

---

## 1. What activation-to-text readers recover, and where they fail

| Reader / eval | Recovered | Failed / omitted | Tag |
|---|---|---|---|
| **Activation Oracles** (Karvonen et al., arXiv 2512.15674, Dec 2025; ICML 2026 oral). Llama-3.3-70B, Gemma-2-9B, Qwen3-8B, Haiku 3.5. Trained on SPQA + 7 binary classification tasks + context prediction, about 1M examples. | Secret words (Taboo 21% vs 4% best white-box baseline), secret side constraint (59% vs 52%), user gender, base64-hidden instructions, fine-tuned bio facts, narrow-misalignment domain. Generalises to 7 held-out classification tasks. | Often wrong and poorly calibrated. Prompting beat it on hallucination detection. PersonaQA was brittle (>80% open-ended, near chance on reformulated yes/no). No probe comparison. | V |
| **"Current activation oracles are hard to use"** (Aryaj, Rajamanoharan, Nanda, LW, Mar 2026). Qwen3-8B/32B AOs, 50% layer. | Next/previous CoT token F1 0.38/0.45 (text-only baseline 0.30/0.20). Multiple-choice backtracking reason 66% vs 47%. Detected low-strength steering. | **Number prediction**: same guesses ("10", "12") whatever the problem. **Missing information**: 0/54 named, and the same label for complete and incomplete prompts in 53/54. Sycophancy AUC about 0.55–0.60 vs dense probe 0.77 (in-sample). Generic answers on 49% of probes. They argue AOs mostly invert nearby text. | V |
| **Concept-specific anti-reading** (Bersia & Atmyre, LW/BlackboxNLP 2026). Qwen3-8B Taboo. | Base AOs recover secret words on hint prompts. | AOs trained on a subject that hides a concept stop reporting it confidently. **A linear probe on the oracle's own middle layers still decodes it; late layers suppress it; ablating mid-layer LoRA partially restores it.** This is the closest published analogue to your fact 4. | V |
| **LatentQA / LIT** (Pan et al., arXiv 2412.08686; ICLR 2026). Llama-3-8B. | System-prompt persona QA. Steering via the decoder's gradient. | Evaluated mainly on persona/SPQA-style content. | V (existence), R (details) |
| **"Do NL descriptions of activations convey privileged information?"** (Li, Ceballos Arroyo, Rogers, Saphra, Wallace, arXiv 2509.13316). Llama-3.1-8B, Ministral-8B. | — | Text-only zero-shot matches or beats verbalizers on feature-extraction benchmarks (0.64 vs LIT 0.64 vs Patchscopes 0.38). An inverter (activation → text → LLM) recovers more than half of verbalizer performance. Verbalizers answer from their **own** knowledge when it conflicts with the target's. | V |
| **Patchscopes** (Ghandeharioun et al., ICML 2024). | Entity resolution across layers, next-token/attribute extraction, multi-hop correction by patching. | Weakest in Li et al.'s comparison above (0.27–0.38). | R (+V via Li et al.) |
| **SelfIE** (Chen et al., 2024). | Self-interpretation of embeddings: ethical-reasoning content, prompt-injection traces, implicit knowledge. Supervised control / RLHF-style edits. | Qualitative evaluation only. | R |
| **Predictive Concept Decoders** (Transluce, arXiv 2512.15712). Llama-3.1-8B layer 15, top-k=16 of 32k concepts. | User attributes (matches LatentQA), jailbreak awareness about 50% vs <30% for others, secret-hint use, implanted concepts better than self-report. | Plateau after about 100M tokens. Phrasing-sensitive. The bottleneck hurts complex tasks. | V |
| **NLAs** (Anthropic, May 2026). AV + AR jointly RL-trained; open NLAs for Qwen2.5-7B, Gemma-3-27B, Llama-3.3-70B. | Rhyme planning ("rabbit"), unverbalized eval awareness (16% / 26% vs <1% real usage), hidden motives in an auditing game (12–15% vs <3%), training-data debugging. | Authors: useful for **themes, not specific claims**. Numbers come out in "the right ballpark", and a multi-hop **intermediate did not appear** in explanations. Invented transcript details. | V |
| **NLA chain-of-thought test** (oakhu & Greenblatt, LW, Jun 2026). Gemma-3-27B, Llama-3.3-70B, Qwen2.5 NLAs, single-forward-pass math. | Answer mentioned in about 84% of cases (Gemma). Some cognition visible in 76%. | Coherent chain in only 16%. Mistake explaining a wrong output in 2/763. NLAs were too noisy to track changed problem constants. For Qwen, a mean-direction "rock" beat the NLA on reconstruction. Sonnet confabulations matched AV reconstruction loss. | V |
| **Dingeto, "Train the model, not the reader"** (arXiv 2607.20379, Aug 2026). | Gist (mean-pooled about 50% chance-corrected). | Specifics about 6% chance-corrected (3× worse). About 2% of salient specific claims grounded in the released Qwen-2.5-7B NLA. **Score 0.04 with content words masked.** Co-trained AV/AR pairs develop private codes in 5/5 runs. Even when content is made decodable by design, the verbalizer's precision is 0.56–0.63 vs about 0.80 for a probe, and changing reconstructor scale, adding a truth reward or adding bandwidth does not close that gap. | V |
| **WorkspaceBench** (Blank, Bhatia, Ong, Nanda, LW/AF, 23 Sep 2026). **Qwen-3.6-27B**; 3,356 questions, 27 families. Readers: logit/J/R/tuned lens, NLA, SAE, Patchscopes, template lens, Oracle Lens. | Facts, multihop, multilingual, rhymes, typos, safety scenarios, user modelling, moral reasoning. Single-token readers + summariser surface some workspace content. | Single-token readers miss **order-dependent / compositional content: multi-digit numbers, "thief chases policeman" role bindings, conjunctive emotional states, buggy-code consequences**. Nearly every NLA readout has ≥1 claim contradicted by the model's own output. Prompt-only baselines are strong. **No probe comparison and no syntax family.** The fetched text gives no score table. | V |
| **Universal Activation Verbalizer** (arXiv 2605.25903) | Could not read (PDF had no text). | — | unverified |

**Takeaway for Q1.** Across reader families, published successes are almost all **content or concept identity**: a word, persona, topic, fact, attribute or plan target. Published failures are **exact values, intermediates, bindings, absence of information, and anything order-dependent**. Every paper above that compared a reader with a probe found the probe higher. None tested a lexically controlled syntactic state, so your result is new and is consistent with that pattern.

---

## 2. Which properties are linearly present in mid-layer residuals of large LMs

| Property | Key results | Tag |
|---|---|---|
| **Syntax: tree distance and depth** | Hewitt & Manning 2019 structural probe. BERT-large best around layers 15–16 of 24; UUAS about 0.82, distance Spearman about 0.87 on PTB; depth recoverable. Tenney et al. 2019: syntax peaks earlier than semantics. | R |
| Syntax: probe vs use | Agarwal, Jian, Manning, Murty 2025 (EMNLP), 32 models ≤8B: probe UUAS does **not** predict BLiMP performance (structural probe adj. R² ≈ 0.05, p ≈ 0.12); best layers are in the middle or first half. | V |
| Syntax: encoded but not deployed | "Encoded but Not Decoded" (arXiv 2609.29848, 2026), 7 models incl. Qwen3-0.6B/14B, control dependencies in EN/ZH/DE: probe ≥ LM-head ≥ behaviour on all 14 conditions; gap up to 0.653. Instruction tuning hurts deployment more than encoding. The LM-head-decodable layer sits about 10 layers after the probe-decodable layer. | V |
| Bracket / Dyck state | Transformers trained on Dyck-k languages represent stack depth (Ebrahimi et al. 2020; Yao et al. 2021). In pretrained LMs, nesting depth is linearly readable. Your own probes (≈1.00) are stronger evidence for Qwen3.6 than anything published. | R |
| **Counters / position** | Anthropic "When Models Manipulate Manifolds" (Gurnee et al., arXiv 2601.04480), Claude 3.5 Haiku linebreaking. Character count sits on a curved 1-D manifold in about 6 dims (95% of variance). Layer-1 linear probe R² = 0.985. Characters remaining is computed by twisting the count manifold against a line-width manifold. Newline decision AUC 0.91. A rank-6 intervention changes behaviour. **No test of verbalization.** | V |
| **Entity / coreference / binding** | Feng & Steinhardt 2024 (ICLR), LLaMA: binding-ID vectors, additive and swappable. Kim & Schuster 2023 box-tracking benchmark. Tang, …, Mueller, Schuster, Kim 2026 (ICML, arXiv 2605.30233), CodeLlama-13B: a **local** probe for the queried box reaches about 0.9 (chance 0.5), but a global-state probe is <0.3. State is assembled at the query, not built incrementally. Binding subspace around layers 15–25. Prakash et al. 2024: fine-tuning reuses the same entity-tracking circuit. | V (Tang), R (others) |
| **World / narrative state** | Li, Nye, Andreas 2021: entity states in Alchemy/TextWorld linearly decodable from BART/T5. Othello-GPT (Li et al. 2023; Nanda 2023): linear "mine/theirs" board probe about 99%. Gurnee & Tegmark 2024: space and time in Llama-2 (mid layers, linear R² high for place and year). | V (existence of space/time), R (numbers) |
| **Arithmetic intermediates** | Yu 2024/25 ("Do LLMs really think step-by-step in implicit reasoning?"): prompted Qwen2.5-72B with direct answers decodes first and final values in late layers, intermediates **rarely**. A Mistral-7B trained for implicit CoT computes intermediates sequentially and runs out of depth by 5 steps. Prior work [R]: Stolfo 2023 (attention routes operands, MLPs compute); Nikankin 2024 ("bag of heuristics"); Kantamneni & Tegmark 2025 (numbers on a helix); Ye et al. "Physics of LMs 2.1" (probes read which variables are needed at about 99% in GSM-style synthetic tasks). | V (Yu), R |
| **Code state** | Jin & Rinard 2023/24 (arXiv 2305.11169): Karel program semantics (future/current robot state) become linearly decodable during training. Silva, Tu, Monperrus 2026 (arXiv 2607.05188), Qwen-35B coding agent: probes predict parse / tests-pass / regression, AUC up to 0.83 at middle layers 21–31 of 40, and up to about 25 edits ahead. | V |
| **Planning / lookahead** | Dong et al. 2025 (ICML) "Emergent response planning": prompt-final hidden states predict response length, reasoning-step count, chosen character and MC answer; structure peaks mid-layer. **Models asked to predict their own outputs are near chance; probes are far above.** Pal et al. 2023 Future Lens (GPT-J, about half of tokens N+2/N+3 recoverable). Lindsey et al. 2025 "Biology of an LLM": rhyme target planned at the line break. Wu et al. 2024: pre-caching vs breadcrumbs. | V (Dong), R |
| **Truthfulness / uncertainty** | Marks & Tegmark 2023 (Geometry of Truth, LLaMA-2-13B mid layers, generalising truth direction). Burns et al. 2022 CCS. Azaria & Mitchell 2023 (SAPLMA). Kadavath 2022 P(IK). Orgad et al. 2025 (ICLR) "LLMs know more than they show": truth signal concentrated in exact-answer tokens; the model sometimes encodes the right answer while generating a wrong one. Gekhman et al. 2025 "Inside-Out": probe vs token-probability knowledge gap +40% relative (Gemma-2-9B 57%, Mistral-7B 49%, Llama-3-8B 14%); in 9% of questions the correct answer is never sampled in 1,000 tries but the probe ranks it top. Ferrando et al. 2025: known- vs unknown-entity directions (Gemma-2). | V (Orgad existence, Gekhman), R (rest) |
| **User-model traits** | Chen et al. 2024 TalkTuner (arXiv 2406.07882), LLaMa2Chat-13B: best-layer reading probes for age 0.98, gender 0.94, education 0.96, SES 0.97. **Prompting reaches only 0.60 (age), 0.86 (gender), 0.45 (education)**; the model refuses gender in 88% of cases; "overridden by final layers". | V |

---

## 3. Prior evidence that verbalizers or explanations systematically omit decodable information

**About activation readers specifically:**
- **Bersia & Atmyre 2026** [V]. The concept is decodable inside the oracle, yet the output is suppressed in late layers. This is a mapping failure, and the oracle is confident while making it. It matches your facts 4 and 5 (state reaches the answering position; light supervised training unlocks it).
- **Dingeto 2026** [V]. The verbalizer stays lossy relative to a probe even when the content is made decodable by design. The gap survives larger reconstructors, a direct truth reward, more bandwidth and negative supervision. The author's explanation is the cost of turning superposed features into text. The reconstruction reward tracks content words: masking them collapses the score to 0.04. This is the strongest outside support for the mechanism "reconstruction RL rewards whatever is carried by which content words appear."
- **Aryaj et al. 2026** [V]: number guesses that ignore the problem, and 0/54 on missing information. **NLA authors** [V]: intermediates missing, numbers only approximate. **WorkspaceBench** [V]: order-dependent and compositional content missed.
- **Ji-An et al. 2025** (NeurIPS, arXiv 2505.13763) [V]. With in-context neurofeedback, Llama/Qwen models can report and control only a low-dimensional "metacognitive space". Label-aligned (LR) axes and high-variance PCs are reported well; later PCs, though linearly defined, are reported poorly. **Directly testable here:** compute the share of block-44 variance along each row's probe direction. Do structure directions sit lower than sentiment, topic and sentence-type directions? This is a CPU-only check on existing activations.

**About self-report and explanations more generally:**
- **Behavioural self-report vs internals**
  - Dong et al. 2025: models cannot self-predict plans that probes read [V].
  - TalkTuner: prompting reads user traits far worse than probes [V].
  - Gekhman 2025: hidden factual knowledge [V].
  - Song, Hu, Mahowald 2025: metalinguistic prompts show no privileged self-access to the model's own grammaticality judgements; Meta–Direct κ ≈ 0.25 across 21 models [V]. This is relevant because it is syntax specifically.
  - "Encoded but Not Decoded" 2026: syntax is encoded but not deployed [V].
- **CoT unfaithfulness**
  - Turpin et al. 2023: biasing features such as "answer is always A" change answers but are almost never mentioned [R].
  - Lanham et al. 2023: truncation and corruption tests [R].
  - Chen et al. 2025, "Reasoning models don't always say what they think": hint use verbalized about 25% of the time (Claude 3.7 Sonnet) and about 39% (DeepSeek-R1) [R; search snippets consistent].
  - Arcuschin et al. 2025: unfaithful CoT in the wild [R].
- **Explanations of units**
  - Huang et al. 2023, "Rigorously assessing NL explanations of neurons": GPT-4 neuron explanations have low precision and recall against activations [R].
  - Auto-interp generally struggles with positional and syntactic features [R, folklore; no clean citation].
- **Introspection**
  - Lindsey 2025, "Emergent introspective awareness": Claude Opus 4/4.1 detect injected concepts only about 20% of the time, and better for abstract or salient concepts [R].
  - Binder et al. 2024, "Looking inward" [R].

**Gap in the literature.** No paper reports a **systematic class** of decodable information that a trained verbalizer omits, measured against a same-item probe ceiling with matched content controls. The closest are Bersia (one concept family, caused by training), Dingeto (designated tokens, small models) and WorkspaceBench (no probe ceiling). Your result fills that gap, provided you show the class extends beyond punctuation.

---

## 4. Recommended additions to the banks (3–5 families)

**Selection criteria.** Each family must:
- fit a single read token and a raw-text prefix;
- be labelled automatically from the template definition;
- be length-matchable;
- have a literature-backed probe signal;
- most importantly, **keep the same multiset of content words in arms A and B**, so that the lens cannot answer from gist.

That last criterion is the discriminating move. It tests "not identifiable from content words" against "syntactic state as such." Name every row so it is clearly *semantic or computational*, not syntactic.

### A. Role binding / coreference with swapped names (highest priority)
- **Literature:** WorkspaceBench's "thief chases policeman" miss [V]; binding IDs (Feng & Steinhardt) [R]; local binding probe about 0.9 (Tang et al. 2026) [V].
- **Rows:**
  - (A1) "*Mara handed Tom the keys because* **she**…" with the clause order swapped ("Tom handed Mara…"). Read at the pronoun. Property: is the referent the giver or the recipient?
  - (A2) "*The thief chased the policeman / The policeman chased the thief. The one running away was the*". Read at "the". Property: is the pursuer the thief or the policeman?
- **Controls:** same tokens across arms, so length-matched for free.
- **Prediction:**
  - If lens is ≤0.65 while probe and base-Qwen-reading-text are high, the blind spot covers **semantic relations** and the result stops being about punctuation.
  - If the lens passes, the blind spot is narrowly format and syntax. That also matters.
- **Feasibility:** 2–3 template families × name and verb fillers. Gender-matched names keep pronoun cues from leaking.

### B. World / narrative state after an update
- **Literature:** Li et al. 2021 [R], Tang et al. 2026 box tracking [V].
- **Row:** "*The coin is in the cup. Ana moves the coin to the bowl.* [or: *Ana moves the bowl next to the cup.*] *Now the coin is in the*". Read at the final "the". Property: is the object's current location the original container or the new one?
- **Controls:** both containers named in both arms. The arms differ by one verb-phrase frame; keep the token ratio ≤1.10.
- **Why include:** this is a state the model must compute, a direct analogue of "inside parenthesis", but semantic. It is also consequential for agent monitoring.

### C. Arithmetic computational state
- **Literature:** Yu 2025 [V] (finals decodable, intermediates not); WorkspaceBench and NLA and AO number failures [V]; Stolfo / Nikankin [R].
- **Rows:**
  - (C1) "*47 + 38 =*" vs "*42 + 36 =*", read at "=". Property: does the sum carry into the tens / is it ≥ 80?
  - (C2) "*Is 6 × 7 more than 40? Answer:*", read at ":". Property: is the planned answer yes or no?
- **Controls:** match digit counts. Balance operand surface statistics so a single operand digit does not give the label away; a check against the base-Qwen text-reading control covers this.
- **Prediction:** NLA and AO literature predicts failure. The probe should be high at block 44 for 2-digit addition.
- **Why include:** "the model has computed X but the reader can't say X" is the monitoring-relevant version of your result.

### D. Code semantic state (as opposed to code syntax)
- **Literature:** Jin & Rinard [V]; Silva et al. 2026 middle-layer AUC 0.83 [V]; WorkspaceBench "buggy-code consequences" miss [V].
- **Row:** "*x = 3\nx = x * 2\nif x > 5:*" vs "*x = 3\nx = x + 2\nif x > 5:*". Read at ":". Property: will the branch be taken?
  - Variant: the type a variable holds at its use site (list vs dict assigned earlier, same names).
- **Why include:** you already have python string, argument and indent rows, which fail. This row separates "code syntax" from "program semantics" on the same surface genre. Your content row "error" is answered near ceiling, so a semantic code row that fails would show the boundary is relational/computational, not code vs prose.

### E. User-model trait as a consequential sayable control
- **Literature:** TalkTuner probes 0.94–0.98 vs prompting 0.45–0.86 [V]; AO user gender [V]; WorkspaceBench user modelling [V].
- **Row:** a first-person raw-text message whose style implies a child vs an adult, or an expert vs a novice (e.g., "*my teacher said…*" vs "*my manager said…*" frames, with matched topic words). Read at the last token. Avoid gender.
- **Prediction:** sayable at ≥0.85, like your other content rows. This shows the lens *can* report consequential latent inferences, which rules out "the lens can't say anything not in the text."
- **Alternative:** if you want a row that might *fail*, phrase it as an **absence** property ("has the user stated their goal or not"). Aryaj et al. found 0/54 on missing information [V].

### Lower priority or not recommended
- **Truthfulness (true vs false statement):** strong probe literature, but base Qwen reading the text will also be at ceiling, so it does not separate reading activations from reading text. It also risks overlapping the eval-awareness team. Use it only as a content-row positive.
- **Planning targets such as rhyme:** the target word is content, so it is probably sayable (NLAs surfaced "rabbit"). Response-length or step-count plans (Dong 2025) are interesting, but they need generated responses to label, which violates "authored from definition only."
- **Counters (character count in line):** probes are strong (R² 0.985) [V], but this is the same family as column and list index. It adds no new class.

### How to read the outcome (pre-register)
Use the same thresholds as the existing banks: lens ≤0.65 means unsayable, ≥0.85 means sayable, and the probe ceiling must be ≥0.90.

| Outcome | Interpretation |
|---|---|
| A–D fail and E passes | The blind spot is **relational/computational state not carried by content words**. This matches Dingeto's masked-content-word collapse and WorkspaceBench's order-dependent misses. Headline: a reconstruction-trained verbalizer systematically cannot report bindings, updated states or computed values that a probe reads at ≈1. |
| A–D pass | The blind spot is specific to formatting and syntax. The paper is narrower but cleaner. |
| Mixed result | Cross the families with your E46 long-lived vs short-lived 2×2 before interpreting. |

**Tension to flag.** Sentence type (0.98) and paragraph position (0.82–0.85) are sayable but are not obviously content-word properties. Sentence type does have lexical cues (wh-words, "?"), and paragraph position may load on discourse-marker vocabulary. The content-word framing therefore predicts that paragraph-position sayability drops on items where discourse markers are scrubbed. That is a cheap rescoring check if those items exist.

---

## Sources (fetched this session)
- Karvonen et al., Activation Oracles: https://arxiv.org/abs/2512.15674
- Li et al., Do NL descriptions of activations convey privileged information?: https://arxiv.org/html/2509.13316v3
- WorkspaceBench: https://www.lesswrong.com/posts/Zeg2JztbdhguL48uH/workspacebench-evaluating-interpretability-methods-for-the
- Anthropic NLAs: https://anthropic.com/research/natural-language-autoencoders ; discussion https://www.greaterwrong.com/posts/oeYesesaxjzMAktCM/natural-language-autoencoders-produce-unsupervised
- oakhu & Greenblatt, Can activation verbalizers surface an internal CoT?: https://www.lesswrong.com/posts/QQQAcKuWK6k98FivY/can-activation-verbalizers-surface-an-internal-chain-of-1
- Dingeto, Train the Model, Not the Reader: https://www.alphaxiv.org/abs/2607.20379
- Aryaj, Rajamanoharan, Nanda, Current activation oracles are hard to use: https://www.lesswrong.com/posts/LXQBcztrWKhtcgQfJ/current-activation-oracles-are-hard-to-use
- Bersia & Atmyre, When activation oracles learn not to read: https://www.lesswrong.com/posts/9yETjcrbH7p8x2tLT/when-activation-oracles-learn-not-to-read-concept-specific-2
- Predictive Concept Decoders: https://arxiv.org/html/2512.15712v1
- LatentQA: https://arxiv.org/abs/2412.08686
- Ji-An et al., Metacognitive monitoring: https://arxiv.org/html/2505.13763v2
- Song, Hu, Mahowald, LMs fail to introspect about language: https://arxiv.org/html/2503.07513v2
- When Models Manipulate Manifolds: https://arxiv.org/html/2601.04480v1
- Encoded but Not Decoded (syntax): https://www.emergentmind.com/papers/2609.29848
- Agarwal et al., Mechanisms vs Outcomes: https://arxiv.org/html/2506.16678v2
- Dong et al., Emergent Response Planning: https://arxiv.org/html/2502.06258v3
- Silva et al., Latent Programming Horizons: https://www.alphaxiv.org/abs/2607.05188
- Tang et al., Do LMs track entities across state changes?: https://arxiv.org/pdf/2605.30233
- Yu, Do LLMs really think step-by-step in implicit reasoning?: https://arxiv.org/html/2411.15862v4
- Gekhman et al., Inside-Out: https://alphaxiv.org/abs/2503.15299
- Chen et al., TalkTuner dashboard: https://arxiv.org/html/2406.07882v1
- Orgad et al., LLMs Know More Than They Show: https://arxiv.org/html/2410.02707v2 (existence only)
- Chen et al., Reasoning models don't always say what they think: https://arxiv.org/pdf/2505.05410 (search snippet only)
- Jin & Rinard, Program semantics: https://arxiv.org/abs/2305.11169 (existence only)
- Gurnee & Tegmark, Space and Time: https://arxiv.org/abs/2310.02207 (existence only)
