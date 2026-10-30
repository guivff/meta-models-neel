## §118 E24. Every core Oracle-lens claim, across its trained layers (Neel's "what layer X finds that layer Y doesn't")

**Registered 2026-10-25 08:55 CET, before any E24 item, activation or score exists. EXPLORATORY.**

**Why.** Every Oracle-lens result so far is at block 44. Suraj's widest sweep (40/42/44) is within 2 layers. Neel asked
for far-apart layers. The lens was trained on layers 20–60 in steps of 4 (11 layers of the model's 64), so every grid
layer is in-contract. The objective account predicts that the blind spot is a property of the lens's *reward*, not of
the layer: structure is carried but never stated at every layer where a probe finds it. One hint against this:
WorkspaceBench's best single Oracle-lens layer was mostly 56 (S01).

**Owner:** W-core (owns W1 and E15 scoring); a new chat "W-layers" if W-core is busy with E20 or W12. **Seed:** 20261025.

**Layers and order.** All 11 grid layers, run in this priority order so that far-apart coverage comes first if compute
runs short: **44 (anchor), 20, 60, 32, 52, 28, 36, 40, 48, 56, 24.** Split across up to 4 pods by layer, with the anchor
on every pod.

**Activations.** One forward pass of the target model on W1's 2,100 test items, plus its dev items, captures the residual
at every grid layer at W1's read position, using W1's frozen hook and sealed per layer before any scoring. Parity gate:
the recaptured block-44 activations match W1's sealed ones (cos ≥ 0.999 on every item).

**Claims and channels (C1–C7), per layer.**
- **C1, asked (W1):** the Oracle lens's asked AUROC on all 25 rows, with W1's frozen phrasings, candidates and scoring.
  *Claim:* near chance on structure, near ceiling on content.
- **C2, continuation (E15):** continuation-likelihood AUROC on E15's valid rows, with E15's frozen pairs. **Swap
  control:** the same scoring with E15's opposite-state donor activation taken from the same layer. *Claim:* carries
  the state, and the swap reverses it.
- **C3, presence (probe):** a logistic probe per row trained on dev activations at that layer with W1's recipe, scored
  on test. *Claim:* the state is present. Its role is gating (see rules).
- **C4, free text (E13/Q1):** one greedy free readout per test item with the lens's native prompt and W1's generation
  settings, scored by a frozen regex of structure statements per row, written and committed before generation.
  20 readouts per layer are blind-checked by a judge, with the layer label hidden. *Claim:* never states structure.
- **C5, window (E1b):** the reconstructor (tag = that layer) on E1b's frozen greedy next-16 continuations, projection
  AUROC on the C3 direction (raw space, as E1b). *Claim:* states visible in the next tokens survive; positions do not.
- **C6, statements (S14):** the reconstructor shift per class gap for E23's fixed statement pairs on `table_column`,
  `prose_paren` and a language control, at 4 layers (20, 36, 44, 60). *Claim:* statements barely move it at any layer.
- **C7, best wording (E16), tier 2:** E16's 8 phrasings, best chosen on dev, at 3 layers (20, 44, 60). This runs only if
  the tier-1 forecast leaves room.

Tier 1 is C1–C5 at every layer that fits; tier 2 is C6–C7.

**Decision rules (frozen; structure rows = W1's 19; Holm over the 19 × 10 non-anchor cells for R2).**
- **R0 (anchor validity):** at layer 44, C1 and C2 reproduce W1 and E15 within ±0.03 AUROC on every row. If a row
  fails, that row's results are uninterpretable at every layer.
- **R1 (blind spot, per layer):** W1's frozen near-chance rule applied unchanged to each layer's C1, among rows where
  C3 ≥ 0.80 at that layer. *"Holds across layers"* if it passes at ≥ 9 of the 11 layers run.
- **R2 (a layer finds what 44 doesn't):** a structure row × layer cell with C1 ≥ 0.70, Holm-adjusted bootstrap p < 0.05
  against 0.5, while layer 44 is ≤ 0.60 on that row. Every such cell is reported by name. Any cell that passes is the
  headline "layer X says what layer 44 can't".
- **R3 (carried, per layer):** C2 ≥ 0.70 on a majority of valid rows, *and* the swap control is ≤ 0.50 on those rows.
- **R4 (never stated, per layer):** pooled over structure rows, the Wilson 95% upper bound on the correct-statement
  rate is < 5%.
- **R5 (dissociation):** C2 − C1 > 0 with CI excluding 0 on a majority of valid rows, at every layer where R3 holds.
- **R6 (window):** C5 on count/position rows ≤ 0.65 at every layer.

**Predictions.** R1, R3, R4, R5 and R6 hold at all or almost all layers. No R2 cells pass. Probes (C3) are high at mid
and late layers and may be lower at layer 20. **Alternatives worth naming:** early layers state syntax (R2 cells at
20–28), or late layers lose the carried state (R3 fails at 56–60).

**Budget.**
- Warmed forecast per pod; cap min(1.5F + 360, 10,800) s per pod, setup 2,400 s.
- Total at most 12 GPU-h. If the tier-1 forecast for all 11 layers exceeds this, drop layers from the end of the
  priority list. Never drop a claim within a layer that runs.
- Results go to `results/g_agreement/understand/e24/`.

**NLA (not swept).** The NLA exists only at block 42. An off-layer NLA read is out of contract, and Suraj flagged his
off-layer NLA reads (16/28/36/56) as a problem. So E24 does not sweep the NLA. If another NLA checkpoint exists (to ask
Agam or Camila), a later registration can add it. The probe (C3) gives the across-layer ceiling the NLA would be
compared against.


**Dated clarification 1, 2026-10-25 09:20 CET (answers W-core's two questions, before anything is frozen or run).**
1. **Rows.** §118's "19 structure rows" assumed W1's full structure set. The 2,100 registered test items and E1b
   continuations cover 25 rows (16 structure, 9 semantic). The three others (`latex_fraction`, `latex_item`,
   `latex_math`) are handled as follows, decided now by what exists:
   - **If** W1 has sealed block-44 test items *and* asked scores for these three rows: they join C1, C3 and C4 at every
     layer, and R0 anchors them against those sealed scores.
     - C2 covers them only if E15 had a valid pair for them (it didn't register any, so it doesn't).
     - C5 does not cover them: no new continuations are authorised.
     - R1 and R2 then range over all 19 structure rows (Holm over 19 × 10).
   - **Otherwise** the scope is the 25 rows: R1 applies W1's frozen near-chance rule to the 16 structure rows, and R2's
     Holm family is 16 × 10.
   - W-core records which branch applies, with the evidence, in `e24/SCOPE.json` before any capture.
2. **C6 statement source.** "E23's fixed statement pairs" was wrong: E23 has none. C6 uses **S14's** statement pairs
   and gap measure, unchanged, from `Jarus77/mats-nla-workspace@a8e41f4a31d654ccc29e2d9105abb2aac38ad5eb`.
   - **Pairs:** `experiments/14_ar_blindspot/modal14.py::_pairs(feature, "ol")` (sha256 `339be5ba…a8de8fc`), i.e. the
     frozen fixed label plus the selected mined templates from the feature's `templates_frozen.json`:
     - exp 13 `d9046206…837d16` for `tb_tablecol` and `tb_paren`;
     - exp 07 `09156722…3e923b` for `ij2_lang`.
   - **Shift:** `ar_lib.py::statement_shift` (sha256 `83486f27…11006e6e6`). It is the reconstruction of statement A
     minus statement B, projected on the true class-mean direction, as a fraction of the true class-mean gap.
   - **Banks and class-gap reference:** Suraj's three 200-item banks, `tb_tablecol`, `tb_paren` and the language
     control `ij2_lang` (French vs German; `handoff_inputs/07_template_mining/gen_ol_ij2_lang.json`, sha256
     `f8f9e2d3…a9e214f6`, 40 mine + 160 select). The true class-mean gap is computed from E24's own fresh captures of
     these banks at each C6 layer (20, 36, 44, 60), over all 200 items, as S14 does. One extra forward pass over the
     600 items captures those layers.
   - **Parity:** at layer 44, Suraj's stored `acts_*.pt` must match the fresh capture (cos ≥ 0.999). His
     `acts_ij2_lang.pt` has sha256 `d557c3d4…33486189`.
   - **Reconstructor:** the reconstructor tag for each layer, which exists for 20–60 in steps of 4.
   - **Cross-check:** at layer 44, C6 reproduces S14's published OL shifts (`analysis14_*.json`) within ±0.05. If it
     doesn't, C6 is reported as not reproduced.

---

