# Direction review: "cross-reference interpretability techniques, agreement as tentative ground truth"

Date: 2026-10-07. Three independent reviewer passes (sceptical methodologist, experiment designer,
mentor-perspective) over results/g_agreement/writeup.md, BRIEF.md, BRIEF_G5G6.md, REVIEW.md, SURAJ_REPO_NOTES.md
and the figures. Synthesis first, raw reports below.

## Synthesis

Verdict (all three agree): promising only if reframed. "Rate each technique by agreement with the majority" should be
dropped as stated. Replace with "rate each technique by agreement with a causally established fact", and report a
blindness map: per feature class, (a) linearly present in the state (held-out probe vs two-half ceiling),
(b) causally load-bearing at the site (an edit there flips behaviour), (c) reported by each reader (native log-odds
primary, free text secondary). Agreement becomes a derived quantity.

Why the stated framing fails on our data:
- Sibling bias: NLA and Oracle are the same base model fine-tuned to verbalize its own activations; a 2-vs-1 majority
  over J-lens measures shared training signal. Shared blind spots (bindings) are invisible to kappa.
- Prompt leak: prompt-only hits 32/32, so every agreed fact is also in the text; G3 shows readers read the vector but
  not that the vector is more than a prompt summary.
- Ceiling: consensus - best single = 0 pp is a design artefact (100% accuracy on covered items), not a learned null.
- Site: block-42 last token is not causally used for the answer (0/16 flips), so reader numbers there are about
  prompt reconstruction.
- Untested clause: SAEs / Skip Lens / "non-workspace" were not run; say so in the first paragraph.

Strongest honest claim now: at this site the two verbalizers report, activation-dependently and in near-perfect
agreement, exactly the surface prompt properties a text reader recovers (language, tense), verbalize nothing about
bindings, and confabulate fillers; yet their native log-odds separate binding states and move with a planted
direction. Free text is a strictly lossier instrument than native log-odds.

Tempting but unsupported: "reader-vs-model dissociation" (site/intervention mismatch, and the planted direction is the
same axis the LO already separates, so Oracle following it is near-tautological; the isotropic null is too weak);
any reader ranking at n=16; anything about NLAs/SAEs finding non-workspace things.

Must-have controls for the next phase: (1) establish the causal site before any reader runs (edit at all positions or
upstream L38 until the answer flips >=75%); (2) a held-out linear probe with a two-half ceiling as the non-sibling
reference reader; (3) other-pair-direction nulls at matched norm instead of isotropic random directions;
(4) item selection on prompt-only-vs-actual disagreement, never on readers.

New assets found (HF, 2026-10-07): no SAE for Qwen3.6-27B; Qwen-Scope `Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50` has a
layer-42 TopK SAE with matching d_model 5120 (transfer test ~0.1 GPU-h); skip lenses
`ceselder/skip-lens-qwen36-27b-agreelens-{a,d,g,p}` are layer-42 LoRAs on the plain base with our NLA's injection
convention (free 4th reader family in phase A); `camilablank/workspace-lenses` ships J-lens and R-lens for this
model; `adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3.6-27B` is a QA-style activation oracle.

Ranked next experiments (designer; ~8-12 GPU-h total):
X1 scale bank to 48 pairs x 4 families, all readers scored by native LO, isotropic + state-free + prompt-only nulls (0.5 h)
X2 plant until the model flips (all positions, and L38 clamp per Suraj), minimal flip dose per item, readers' LO
   follow-rate and gain ratio at that dose; other-pair-direction nulls (3 h)   <- headline
X3 floor item sets: model-error mapping puzzles; self-choice disagreement items (0.7 h)
X4 add reader families: R-lens, template lens, Qwen-Scope SAE transfer, sparse probe (1.5 h, +3-4 if SAE must be trained)
X5 split planting: J-space component vs J-removed remainder, lenses as leak detectors (1.5 h)
X6 rate readers vs LOO majority with and without the sibling verbalizers, against the causal key (0.3 h)

Headline figure: x = dose as fraction of each item's behavioural flip dose (0..2); y = standardized LO shift toward the
planted candidate; one line per reader with pair-bootstrap bands; the model's own answer log-odds as the black
reference curve. Left: full swap direction. Right: J-removed component. Inset: agreement-with-majority vs
agreement-with-causal-key, one point per reader.

Mentor check-in questions: (1) how much of the Oracle LO shift is guaranteed by construction? (2) why is block-42
last token the right site if the answer is rebuilt from earlier positions? (3) what is the operational definition
of "non-workspace", and where are SAEs/skip lens?

---
## Raw report 1: sceptical methodologist

1. Agreement as tentative ground truth is sound only as a screen for shared variance, never as truth.
- Sibling readers: NLA and Oracle are the same Qwen3.6-27B, each fine-tuned to verbalize its own activations. A
  majority of {NLA, Oracle, J-lens} is two siblings outvoting one structurally different tool whose vote the rubric
  defines by fiat. kappa 0.88 detects shared wrong answers, not shared blind spots; the headline (joint silence on
  bindings) is exactly the uncontrolled failure mode.
- Prompt leak: G3 donor reassignment (17->4/32) shows the text is read from the vector; prompt-only 32/32 shows every
  agreed fact is also in the text. G3 controls "did the reader look at h", not "is h more than a prompt summary". G6
  failed for a predictable reason: the floor is the same model guessing its own preference.
- Shared extractor and label circularity: one rule-v1 extractor scores all readers; the key is the designer's label or
  the target's own output, i.e. truth is defined as text or behaviour, which is what readers need to add value over.
- Selection on coverage: "~100% accurate when they speak" conditions on speaking; G4 shows near-determinism, G5 shows
  abstention is not calibrated to absence.
- Forced ceiling: 0 pp consensus gain is a design artefact.
Controlled well: state-free prior, J-lens null, kappa, pair bootstrap, random-direction null, pre-registration.
Not controlled: sibling bias, prompt-vs-computation, extractor, site causality.

2. Honest claim: see synthesis. Unsupported: dissociation (site mismatch); "readers follow the binding" (u = h_B - h_A
contains every differing feature incl. token identity; isotropic null does not rule out name-correlated directions);
consensus adds nothing as a general claim; any ranking at n=16.

3. Promising only if reframed to a blindness map with a causal key (columns a/b/c in synthesis); the labelled probe is
the non-sibling fourth reader that breaks the 2-vs-1 structure.

4. Biggest risk: two more weeks at a site where nothing read is causally load-bearing. Control: establish the causal
(layer, position-set) before any reader runs. Also: held-out probe with two-half ceiling; select items on
prompt-only-vs-target disagreement.

---
## Raw report 2: mentor perspective

Informative: shared silence not contradiction; verbalizer free text gets the genre right and confabulates specifics
("Alice", "A->B->C"), underclaimed; G5 E1 (binding recoverable from native LO, Oracle 8/8) is a real methodological
lesson; G3 donor arm and J-lens noise ceiling did their job.
"Item set too easy": G1 primary contrast is a ceiling effect, rephrase as untestable here; G6 floor is the model's own
position bias.
Overclaimed: "reader-vs-model dissociation" (planted direction is the axis LO already separates, so Oracle following
it is near-tautological; isotropic null too weak; non-flip shows the site is not causally used, which is a point about
site choice); "binding IS linearly present" (AUROC 0.72, no probe baseline); coverage numbers are extractor numbers
with 136 blind rows unadjudicated.
Underclaimed: confabulated fillers; the SAE / Skip Lens / non-workspace clause is untouched.
Strong results: (A) negative "majority agreement is site-blind": kappa flat across sites ordered by patching flip
rate; (B) positive "native LO tracks the causal state": at the minimal flipping dose Oracle/NLA LO follow >=75%,
probe too, J-lens not, with other-pair-direction nulls; (C) "NLA/SAE report non-workspace features that are
behaviourally live": ablate a named SAE feature and move a non-answer output (format, length, language).
Verdict: moderately promising, because the infrastructure works and the pilot shows exactly why the framing fails;
drop majority rating, use agreement with a causally established fact (not prompt-recoverable, probe finds it, edit
changes behaviour). One experiment: redo G5 with edits at all positions / entity tokens until E3 >= 0.75, other-pair
nulls, 2-fold probe baseline, follow-rate per reader at that dose.

---
## Raw report 3: experiment designer (full text of X1-X6 and asset search is summarised in the synthesis)

Asset search details: Qwen3.6 SAEs exist only for 35B-A3B (d_model 2048, unusable). Qwen-Scope
`Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50` (TopK k=50, width 81920, one .pt per layer 0-63, d_model 5120): transfer test
of layer42.sae.pt on cached states ~0.1 GPU-h (FVE vs shuffled-decoder null); if FVE >= 0.5 refit decoder/bias on
~20M Qwen3.6 L42 tokens (~1 GPU-h); else train BatchTopK SAE ourselves (~3-4 GPU-h). Skip lens:
`ceselder/skip-lens-qwen36-27b-agreelens-{a,d,g,p}` (layer-42 future-lens LoRAs, same injection as our NLA; arm D
"learns non-J-space reading", arm A best wsbench surfacer); `ceselder/skip-lens-olens-pi0-100k-qwen36-27b` native L42
oracle lens; other ceselder skip-lens repos read layer 62. `camilablank/workspace-lenses`
qwen3.6-27b/{j-lens,r-lens}/lens.pt plus a 13k-word template lens. `adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3.6-27B`
(Activation Oracle, QA format). Gated: ceselder/qwen-36-27b-good-meta-models, camilablank/...penultimate-jacobians.

X2 specifics: 96 ownership+mapping pairs from X1 + 100 of Suraj's country-bridge items
(experiments/05_planted_intermediates/plant_lib.py, L38 clamp, 431/614 kept at alpha<=4); edit all positions from the
question's last content token through the chat-template suffix (~12 positions), and separately L38 centred clamp,
alpha in {0.5,1,1.5,2,3,4}; minimal flipping dose per item chosen on the model's answer only; keep criteria: flip,
neutral-prompt KL <= 0.1, prompt still self-retrieved at L42. Controls: 20 isotropic + 20 J-complement nulls at
matched norm; "away" sign. Metrics: paired win and z of LO shift at flip dose; gain ratio = reader LO shift / model
answer-LO shift across the ladder. Decisions: "tracks causal state" win >= 0.9 at minimal flip dose and null <= 0.25;
"reads-but-model-ignores" win >= 0.9 at sub-flip doses with model LO inside its null; "insensitive" win <= 0.5.
X3: model-error mapping puzzles (400 generated, keep wrong-answered, expect 60-120; candidates correct vs model's);
self-choice disagreement (300 prompts, keep prompt-only != greedy, expect ~60, plus size-matched agreeing control).
Decision: reader "reads the model, not the text" if P(LO favours actual answer) >= 0.75, CI excl. 0.5, >= 25 pp over
prompt-only.
X4: SAE native score = sparse diff-in-means probe over latents, leave-one-pair-out, <= 10 latents; dense probe on raw
states as ceiling; J-space enrichment of selected latents (basis from src/mats/jspace.py, r* = 384). "finds non-J
content" if enrichment <= 1.5 and lens AUROC inside null band.
X5: decompose swap direction into top-r* J component and J-removed remainder, plant each at the X2 flip dose; a reader
"reads non-J" if win >= 0.75 under the J-removed plant with lenses inside their band.
X6: majority recomputed with and without same-base LoRA verbalizers; usable proxy if Spearman(agreement with LOO
majority, agreement with causal key) >= 0.8 under both definitions.
