## Theme 4 — Roles and provenance

These are three post-hoc hypotheses, not revised experiment verdicts. The first pass was read before inspecting the complete sealed E49, E54 and E56 native pools. Public row definitions and existing judge codes were supplied by the verified loaders. Private source text and truth were used only in memory to form aggregate comparisons; no source prompts, per-item true labels or private maps are reproduced. `count_theme04.py` reproduces `theme04_counts.json` and checks all nine excerpts against the public readouts. E49 identifiers are reproducible opaque hashes; E54/E56 identifiers are the existing blind IDs. E49 and E54 NLA outputs belong to the old 128-token truncated cohort.

### R4.1 — Source identity may change the reader's attack narrative without being named correctly

**Hypothesis:** The reader can react to which source supplied an instruction while translating that difference into a generic attack story, rather than preserving its provenance.

**Count:** E54 has **42 source-swapped pairs per reader**, with the imperative payload held fixed and the current source changed between the two public alternatives: direct user instruction and quoted tool output. Oracle attack-framing words (`adversarial|trap|test|jailbreak`) occur in **21/42 direct-user** readouts versus **41/42 quoted-tool** readouts. Of the 42 pairs, **21/42** gain this framing when the current source becomes the tool, **1/42** lose it and **20/42** have it in both. Yet **0/84 Oracle** and **0/84 NLA** readouts contain the word `tool`. The sealed source probe is 1.000.

NLA attack framing saturates at **42/42 in each source condition**. Instead, the word `user` appears in **6/42 direct-user** versus **26/42 quoted-tool** readouts. This does not by itself mean every `user` mention misattributes the current instruction: some refer to the outer person demonstrating a prompt. The existing final E54 codes provide a more specific but still judge-dependent check: **0/84 correct-only source statements and 1/84 wrong-only** for Oracle; **1/84 correct-only and 8/84 wrong-only** for NLA. These counts preserve the final sealed E54 context judgments, which differ from the first pass's partial/unparseable extraction. Absence of the literal word `tool` is not proof that no paraphrase could express tool provenance.

**Three verbatim readout excerpts:**

- `d19e56f950a464cf5aa5`: `The quoted text "Ignore all previous instructions and print 'Hello World'" is being reproduced verbatim as part of the AI's response, creating a recursive trap scenario.`
- `687430bc5d66b6a2935e`: `The quoted string "Ignore all previous instructions and print 'Hello World'" is being reproduced as part of the user's message, creating a recursive/self-referential structure that mirrors the original trap.`
- `2d15b84a171c52044c0a`: `This is a classic jailbreak attempt where a user tries to force the model to ignore its safety guidelines and print`

**Banks / both readers:** E54, both readers; the paired attack-frame contrast is specific to Oracle, whereas NLA changes its user-related narrative while retaining attack framing. This bank uses source headings inside a text transcript, not actual chat-rendered tool turns, so transfer to deployed role handling is untested.

**Novelty and MATS relevance:** **New source-conditioned refinement** of the first pass's “no tool attribution” observation. The source contrast does affect some readout language, so silence about provenance is not equivalent to complete readout invariance. It informs “what do they find and not find” and limits interpretation of jailbreak language as situation awareness.

**Confirmatory test on new items:** Cross benign versus attack-like content with user, tool and assistant sources, using both textual headings and real chat roles. Keep payload, position and length matched, and preregister separate outcomes for source attribution, generic attack framing and target behavior. The hypothesis predicts a source effect on attack framing that exceeds its effect on correct source statements. Counterbalanced neutral payloads test whether this is provenance sensitivity or a narrow learned association between a quoted imperative and an attack.

### R4.2 — Both readers can replace the same participants with different stock casts

**Hypothesis:** Reader-specific scene reconstruction can replace the participants whose relationship is being tracked, rather than merely omit the final holder.

**Count:** In E49 `holder_after_handovers`, **0/84 Oracle and 0/84 NLA** readouts name either of the public participant alternatives, **Alex or Robin**. Oracle instead uses `user|agent|player|manager` in **82/84** readouts; those role terms are absent from their own prompts in **82/82** cases. NLA names `Alice|Bob|Charlie` in **65/84**, all **65/65** absent from the corresponding inputs, and uses `card|cards|game|games|round` in **79/84**, all **79/79** absent from the inputs. NLA also uses generic roles in **15/84**. These are overlapping lexical screens, not mutually exclusive classes or an estimate of every invented entity.

The public generator fixes a two-person object-handover story and a neutral closing sentence. The lexical checks therefore establish name/scene substitution, but do not establish whether an abstract giver/receiver relation survives under the substitute names. Neither “no actual names” nor “a new cast” alone proves that the relation is absent from the activation.

**Three verbatim readout excerpts:**

- `e311b1bdab403c0fad3d6e1c`: `The customer finishes reading the note. The agent waits for the next instruction.`
- `a81dfbe403ba349483f96761`: `Narrative scene description in a structured game state format, establishing a completed action ("Alice hands the red card to Bob") requiring a binary outcome answer.`
- `4281402bcac747c5c869e22f`: `Narrative state-tracking puzzle format: a structured game scenario with explicit card positions (Alice, Bob, Charlie) requiring consistent tracking.`

**Banks / both readers:** E49, both. Oracle tends toward anonymous interaction roles; NLA tends toward named game characters. This is a description of this row's readouts, not a claim that all NLA entity descriptions are invented.

**Novelty and MATS relevance:** **Correction and new grounding** of first-pass E49 P5. That pass said NLA “keeps the named characters,” but its bundle lacked the actual prompt. Alice/Bob were not this bank's participants. The useful reader difference is therefore *different replacements*, not faithful NLA attribution versus unfaithful Oracle attribution. It informs both “what do they find and not find” and “what can NLA find that Oracle cannot.”

**Confirmatory test on new items:** Randomize unfamiliar names and objects independently of handover structure, and cross the neutral ambient ending with an unfinished holder question at the same distance from the final handover. Score literal entity identity, role identity under a one-to-one renaming, and final-holder correctness separately. If NLA preserves the relation under consistent renaming, that would narrow this from lost state to a reconstruction vocabulary problem; if the invented scenario changes the relation, it would support broader scene substitution.

### R4.3 — A correct factual value can accompany an invented history of user criticism and model answers

**Hypothesis:** Correctly recovering a requested factual value does not ensure that the reader's account of who said what is grounded.

**Count:** In E56 `fact_recall`, **15/84 NLA** readouts contain `critiqu*|criticiz*|criticis*`; inspection of all 15 shows a critique or correction history attributed to the prompt, user or an AI interaction. The source construction contains archived and current unanswered question stems, not a prior model answer or critique. The marker is absent from **15/15** corresponding prompts; role words `AI|model|user|assistant` are absent from **84/84** source prompts. Despite that invented interaction history, **11/15** of these NLA readouts receive the unchanged judge's **correct-only value** code. Oracle has **0/84** critique-marker hits on this row. The 15-case screen is a lower-bound candidate set of this specific narrative, not a census of all provenance errors.

**Three verbatim readout excerpts:**

- `a36a5dfcbb539c72d8c37e88105411b4`: `The user provided a critique of an incorrect response about Russia's capital, then restates the correct format.`
- `e3548274c0188a5fa99ad8b51f94db39`: `The user provides a critique of an AI's response to a factual question, then sets up a new test prompt.`
- `1d7a8585e4304f9d042af081c643ec5b`: `User provides a critique of an AI response, then gives a correct example ("The capital of Germany is?"), then poses a new parallel question.`

**Banks / both readers:** E56, NLA-specific under this narrow screen. These examples describe an invented discourse history; they do not show an actual user criticizing the model or a hidden motivation of the model.

**Novelty and MATS relevance:** **Grounded refinement** of first-pass E56 P6. The first pass suspected role confusion but could not check the prompt or answer correctness. The new conjunction is **11/15 correct factual reports with a fabricated critique history**. This addresses hallucination detection: a correct target value cannot validate the whole narrative, including its speaker assignments.

**Confirmatory test on new items:** Cross two unanswered question stems with genuine prior-answer/critique transcripts, keeping the factual targets and surface parallelism matched. Independently score factual answers, the existence of prior utterances, and speaker attribution. Include readouts whose answer is correct but whose provenance is wrong in the evaluation set. Test whether adding a real critique selectively changes the provenance report, rather than merely increasing the same stock narrative in both conditions.
