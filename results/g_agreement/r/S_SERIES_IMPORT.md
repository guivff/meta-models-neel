# Four earlier results for the main project (report only, no new compute)

Written 2026-10-21 for the Phase R integrator. Everything below is read from files already on `origin/main` (snapshot
`56565fc4`, extracted from `guivff/mats-minis`; the original commits there are cited as *mm:<sha>*). Rates are k/n; F2-2
"follow" intervals are the pre-registered pair bootstrap (32 pairs, 1,000 resamples, seed 0) — recompute Wilson from k/n if
preferred. Target Qwen3.6-27B bf16, chat template, thinking off, last prompt token unless stated.

## 1. J-space vs ⊥J decomposition of the ownership edit

**Pre-registered.** Phase W (unscaled pieces): `projects/g_agreement/PREREG_WV.md` (*mm:5faacdd*, 2026-10-11, before the W pod
session of 2026-10-12; deviations in *mm:b5bd9ef*). F2-2 (norm-matched pieces, α sweep): `BRIEF_Z.md` "Agam follow-ups 2"
(*mm:7c625ae*, 2026-10-14, before GPU work). Oracle on-grid rerun at block 44: `PREREG_WV.md` (*mm:3190079*).

**Registered rule and verdict (for the ledger).** F2-2, `projects/g_agreement/BRIEF_Z.md` at *mm:7c625ae*, verbatim: "Rule: if flip(J_scaled, α 1) ≥ flip(full, α 1) − 10 points, state plainly that \"readers read what the model doesn't use\" reduces to readers being more sensitive to the J-space component; otherwise report the dose at which J_scaled first flips ≥ 50% (if any) next to the readers' follow at α 1 unscaled." Outcome: flip(J_scaled, α 1) = 0/64 vs flip(full, α 1) = 64/64, so the condition fails and the **otherwise** branch applies; that branch has **no verdict word** — it only asks for the dose, which is **α 2.0 (33/64 = 52%)**. The headline "DOES NOT reduce to sensitivity" in `f2/t2/t2.md` (*mm:f5fd644*, 2026-10-14) is the analysis script's wording of the failed condition, not a registered verdict; no F2-2 deviation was ever recorded. Phase W (`PREREG_WV.md`, *mm:5faacdd*) registered rules only for d_cm and d_pw (P1–P3): the Δ_J and Δ_⊥ rows have **no registered rule and no verdict** (descriptive).

**Construction.** 32 X2 ownership pairs (`dataset/items_x.json`, test, first 32 by index) × both directions = 64 states.
Edit at the output of block 38, all prompt positions, prefill only: h' = h + α·v. Full edit Δ = h_other − h_own per position.
J-space = top-384 right singular vectors of W_U·J₃₈ (`cache/g_agreement/y/jspace_L38_r384.pt`, `core/edit.jspace_basis`);
Δ_J = projection of Δ onto it, Δ_⊥ = Δ − Δ_J. Energy of the swap (Phase W): Δ_J 8%, Δ_⊥ (remainder) 81%.
**Norm matching (F2-2):** J_scaled and perp_scaled = Δ_J and Δ_⊥ each rescaled *per position* to ‖Δ(p)‖; random control =
a seeded Gaussian direction per position rescaled to ‖Δ(p)‖ (K = 2 seeds, 128 states); J_only = Δ_J unscaled (the Y2 arm).
Model flip = greedy 8-token answer parsed as the other version's name. Reader follow = the reader's native log-odds moves
toward the other name relative to the natural state (sign test per state). Reads at blocks 42 and 44 (F2-2: re-read from
the edited forward pass); NLA at 42.

### F2-2 — model flips and model log-odds by dose (64 states; random 128)

| arm | α 0.25 | α 0.5 | α 1 | α 1.5 | α 2 | Δ answer log-odds at α 1 (nats) |
|---|---|---|---|---|---|---|
| full Δ | 0/64 | 32/64 | 64/64 | 64/64 | 64/64 | +25.0 [24.0, 26.1] |
| J_scaled (norm-matched) | 0/64 | 0/64 | **0/64** | **15/64** | **33/64** | +3.9 [3.3, 4.6] (α 1.5 +9.5, α 2 +14.2) |
| perp_scaled (norm-matched) | 0/64 | 0/64 | 64/64 | 64/64 | 64/64 | +24.8 [23.8, 25.9] |
| random at ‖Δ‖ | 0/128 | 0/128 | 0/128 | 0/128 | 0/128 | −0.0 [−0.1, +0.1] |
| J_only (unscaled) | 0/64 | 0/64 | 0/64 | 0/64 | 0/64 | +0.3 [0.2, 0.4] (α 2 +1.9) |

The "split" at higher J-space strength: J_scaled first flips at α 1.5 (15/64) and reaches half at α 2 (33/64); the model
moves its answer log-odds ~6× less per unit norm for the J piece than for the ⊥J piece (+3.9 vs +24.8 nats at α 1).

### F2-2 — reader follow at α 1 (k/64; random k/128) [pair-bootstrap %]

| arm | Oracle@44 | Oracle@42 | J-lens@42 | J-lens@44 | NLA@42 |
|---|---|---|---|---|---|
| full Δ | 60/64 [84, 100] | 54/64 [69, 97] | 60/64 [84, 100] | 62/64 [91, 100] | 45/64 [55, 84] |
| J_scaled | 57/64 [78, 98] | 58/64 [81, 98] | 54/64 [72, 97] | 51/64 [67, 91] | 53/64 [70, 94] |
| perp_scaled | 59/64 [83, 100] | 54/64 [69, 97] | 54/64 [72, 94] | 54/64 [72, 97] | 41/64 [48, 80] |
| random at ‖Δ‖ | 58/128 [38, 55] | 63/128 [40, 59] | 60/128 [38, 55] | 63/128 [40, 58] | 76/128 [52, 66] |
| J_only (unscaled) | 57/64 [78, 97] | 57/64 [80, 97] | 54/64 [72, 95] | 52/64 [69, 92] | 51/64 [67, 91] |

Readers follow J_scaled already at α 0.25 (Oracle@42 58/64, J-lens@42 56/64, NLA 51/64) where the model moves +0.3 nats;
every α row is in `t2.csv`.

### Phase W — unscaled pieces at α 1 (ownership, 64 states; random = K pooled, 640 states)

| direction | model flips | J-lens | Oracle@42 | Oracle@44 (on-grid rerun) | NLA | skip-lens A | probe (ref.) |
|---|---|---|---|---|---|---|---|
| Δ_J (top-384 J-space) | 0/64 | 84% [72, 95] | 94% [86, 100] | 91% [80, 98] | 80% [64, 94] | 89% [78, 98] | 100% |
| Δ_⊥ (remainder) | 0/64 | 80% [66, 94] | 88% [75, 97] | 94% [86, 100] | 67% [52, 83] | 86% [73, 95] | 45% [30, 61] |
| random (pooled) | 0/640 | 49% [47, 50] | 48% [47, 50] | 47% [45, 50] | 48% [45, 52] | 48% [45, 50] | 50% |

Random band (p95 over directions / pooled), ownership: J-lens 52/49, Oracle 53/48, NLA 52/48. Fraction of each reader's own
natural separation recovered (median): Oracle Δ_J +1.28 / Δ_⊥ +0.48; J-lens +0.93 / +0.53; NLA +1.11 / +0.48.

**Caveats.** (i) In the 29-name rescoring (§3) readers pick the planted name for J_scaled at α 1 only 1–4/64, about the same as for
the full edit (2–4/64): "follow" is a two-candidate, relative measure. (ii) Following at α 0.25 shows the readers respond at
a dose ≥ 8× smaller than the one that moves the model (agreed sensitivity caveat). (iii) S3 (CPU, pre-registered) found the
J-space is *not* the output-token subspace at block 38 (overlap 1.19× random p99; `results/g_agreement/s3/s3.md`).

**Files.** `results/g_agreement/f2/t2/{t2.md, t2.csv, t2_summary.json, fig_t2.png}` (code `projects/g_agreement/f2/t2_normsplit.py`,
`t2_analyze.py`); `results/g_agreement/w/w1/{w1.md, matrix.csv, fig_matrix.png}`; `results/g_agreement/w/o44/{o44.md, o44.csv, fig_o44.png}`;
raw rows `cache/g_agreement/f2/t2/{behaviour,lo}.jsonl`, `readvecs.pt` (Mac and the pod volume; not in git).

## 2. The NLA "resolver" case (Sweden → Volvo) — Suraj's experiment, not ours

Source: Suraj's `mats-nla-workspace-main/experiments/05_planted_intermediates/` (dated 2026-10-06; not in this repo, at
`third_party/mats-nla-workspace-main/` on the Mac and the pod volume). Not pre-registered as a reader test (a feasibility pass
of his K4 yield check). Setup: bridge-country swap planted at **block 38** with the centred clamp (per-item minimal α ≤ 4,
selected on the model's answer flipping and staying coherent), readers at **block 42**. Prompts: `"Fact: The capital of the
country famous for {clue} is"`; France clues = the Eiffel Tower, the Louvre museum, croissants and baguettes, the Palace of
Versailles, Mont Saint-Michel. The planted partner was Sweden (clues IKEA, ABBA, Volvo cars, the Nobel Prize banquet, the
Icehotel).

- **Exact prompt: not recorded.** `results/readers.json` stores only the pair (`names: ["Sweden", "France"]`), not the item id.
  The unplanted NLA readout paraphrases "The capital of the country where the Louvre Museum is located is", so it is most likely
  `"Fact: The capital of the country famous for the Louvre museum is"`; Suraj's notes describe it as "Eiffel Tower" → Volvo.
- **NLA output (planted, k = 1, verbatim excerpt):** "The phrase 'a Nobel Prize institute is located in the capital of the
  country whose CEO designed adopted Volvo' references Sweden, constraining the expected answer to 'Stockholm' … 'The capital
  city of the country where Amer Awards Nordiska modepriset headquarters is located is'". Unplanted: names the Louvre and Paris.
- **J-lens top-100 at block 42: not available.** Suraj saved only native log-odds summaries; the planted vectors were on his
  Modal volume (`*.pt`, git-ignored) and no top-k list was stored. Producing it would need new compute.
- **Other cases like it:** all 12 free-form NLA examples (`readers.json` → `nla_examples`) name the planted country (12/12) and
  rewrite the clue to fit it: Canada ("maple leaves", "beaver"), Russia ("the Bear", USSR), India ("Himalayan"), Argentina
  ("Messi"), Brazil (a "Ronaldo" footballer), Australia ("kangaroo"), China ("Great Wall", "Yangtze"), Spain ("football"), Peru
  ("Peruvian writer"). Native LO on 200 planted items: Oracle P(reads planted) 1.00, NLA 0.98, J-lens 1.00 (unplanted 0.01–0.03).
- **Caveat (his):** the swap direction is strongly J-enriched (enrichment 6.5), and by block 42 the model already encodes the
  planted *answer* (e.g. "Stockholm"), so the NLA may back-infer the country from the answer rather than read a bridge.

## 3. Two candidates vs all 29 names (ownership, natural states)

**Pre-registered:** `BRIEF_S.md` §S8 (*mm:8cc1a0a*, 2026-10-16 11:35 CEST) and its amendment (*mm:bc1bf4f*); run twice
independently (this chat: `s8/fullcand/`, *mm:69cd49e*; the S7 chat: `s8/s8.md` + `s8a_table.md`, *mm:1791224*) — identical
numbers. Same 64 F2-2 natural read vectors; native scores over all 29 names of the 32 pairs (chance 3.4%). Counts below are
tabulated from `cache/g_agreement/s8_fullcand/scores.jsonl` (existing rows).

| reader | two candidates, per state (own > other) | two candidates, within pair (lo_A + lo_B > 0) | 29 names: picks the owner | default name (share of the 64 states) |
|---|---|---|---|---|
| J-lens@42 | 32/64 | 30/32 | 2/64 | Nora 34/64 (Iris 14, Emma 13) |
| J-lens@44 | 34/64 | 31/32 | 3/64 | Zara 61/64 |
| Oracle@42 | 42/64 | 27/32 | 3/64 | Leo 21/64 (Tom 19, Sara 19) |
| Oracle@44 | 46/64 | 30/32 | 4/64 | Leo 36/64 (Emma 12, Sara 10) |
| NLA@42 | 35/64 | 22/32 | 4/64 | Tom 41/64 (Emma 13, Leo 10) |

The two-candidate figures quoted in the write-ups (72–94%) are the within-pair statistic: it cancels each reader's name bias,
which the per-state and 29-way numbers expose. Under the planted edits (k = 29): full Δ at α 1 picked 2–4/64 per reader;
J_scaled 1–4/64; random 2–7/128 (`s8/fullcand/s8.md`). An exploratory (not pre-registered) prior-centred argmax gives the owner
on natural states 8–17/64 and the planted name for the full edit 8–16/64. **Follow-up frozen but not run:** S10 (`BRIEF_S.md`
§S10, branch `s/s10-four-names`, pre-registration commit `63efd66`) puts four names in the prompt with the name prior
cancelled by design; pod E refused to start (no free GPU), so there are no S10 numbers.

## 4. Probe vs reader lag on the 297 arrow-chain mistakes

**Pre-registered:** V1, `PREREG_WV.md` Part V (*mm:5faacdd*; analysis *mm:b5bd9ef*, 2026-10-12). 297 X3 ERROR puzzles
(`dataset/items_x3_selected.json`, set `error`): the model's greedy answer is wrong. Metric: P(native LO favours the model's
actual answer over the correct one), two candidates; probe = E10 held-out difference-of-means probe. Threshold 0.75.
Item bootstrap 1,000 (seed 0); counts give Wilson directly.

| block | probe (E10) | J-lens | Oracle (nearest grid) | NLA (transfer) | logit lens |
|---|---|---|---|---|---|
| 42 | 205/297 (69%) | 170/297 (57%) | 141/297 (47%) | 175/297 (59%) | 58% |
| 44 | 218/297 (73%) | 173/297 (58%) | 136/297 (46%) | – | 52% |
| 48 | **234/297 (79%)** | 123/297 (41%) | 145/297 (49%) | 168/297 (57%) | 52% |
| 50 | 233/297 (78%) | 145/297 (49%) | 147/297 (49%) | – | 51% |
| 52 | 273/297 (92%) | **229/297 (77%)** | **242/297 (81%)** | – | 75% |
| 56 | 278/297 (94%) | 233/297 (78%) | 250/297 (84%) | – | 66% |
| 60 | 277/297 (93%) | 231/297 (78%) | 256/297 (86%) | – | 67% |

**First block ≥ 0.75:** probe **48**; J-lens **52** (CI lower bound ≥ 0.75 first at 58); Oracle **52** (lower bound at 52);
lag 4 blocks for both. NLA below 0.75 at both scored blocks (42, 48; other blocks never run). Control set (103 puzzles the
model gets right) at 48: J-lens 84/103, Oracle 80/103. Three-way check (amended S8b, `s8/s8.md`, Y1 captures, chance 1/3, m =
model's answer, c = correct, d = off-chain symbol): m-share at 42 / 48 / 52 / 56 = J-lens 37 / 30 / 74 / 76%, Oracle 31 / 35 /
82 / 86%, probe 57 / 69 / 91 / 93%; no reader ever favours c.

**Files.** `results/g_agreement/v/{v1.md, v1.csv, v1_summary.json, fig_v1.png}` (code `projects/g_agreement/v12_readers/v1_sweep.py`);
`results/g_agreement/s8/{s8.md, s8.csv, s8_summary.json}`; raw rows `cache/g_agreement/{x/x3_lo.jsonl, y/y1_lo.jsonl, w/s3v1_lo.jsonl}`.
