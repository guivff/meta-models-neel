# Z5 — identity-binding factorial bank (`banks/binding_factorial`)

Pre-registered in `projects/g_agreement/BRIEF_Z.md` §Z5. Generation is CPU-only (no model calls); capture reuses
the X1 protocol. Written 2026-10-09, before any capture.

## Why a new bank

R2R4 (`results/g_agreement/x/friday/R2R4.md`) showed that the Phase X ownership bank is order-confounded: a
contrast probe on *answer first-mentioned* wins 47/47 under LOO while the identity probe is at ceiling-level
chance, and PC1 of `h_B − h_A` carries 66% of the within-pair variance. In that bank the within-pair contrast
(binding swap) always also flipped the answer's mention position, and names/positions were random rather than
crossed. Here every nuisance is a crossed, balanced factor, so the within-pair difference can be regressed on it
before any reader is scored.

## Design (full factorial; 64 cells × 2 pairs = 128 pairs = 256 items; seed 20261010)

| factor | levels | pairs per level | meaning |
|---|---|---|---|
| `name_set` | ns0 Emma/Anna, ns1 Adam/Paul, ns2 Lisa/Kate, ns3 Eric/Luke | 32 | the two names (X, Y) of a cell |
| `template` | pos0, pos1 | 64 | pos1 prepends the fixed lead-in "Consider the following two statements." so both ownership statements sit at a different absolute position; the statements' token multiset is unchanged |
| `mention_order` | x_first, y_first | 64 | which name of the set is in the first statement |
| `pairing` | x_o1, x_o2 | 64 | the binding of **version A**: X holds O1 (Y holds O2) or X holds O2. Version B has the other binding, so A and B differ ONLY in pairing and are token permutations |
| `query_direction` | object_to_name, name_to_object | 64 | "Who has the O1? Answer with the name only." (candidates = the names) vs "What does X have? Answer with the object only." (candidates = the objects) |

Cell index = mixed radix over (name_set, template, mention_order, pairing, query_direction), name_set outermost;
ids `zb-<cell 00..63>-<k 1..2><A|B>`, pair_id `zb-<cell>-<k>`, family `ownership`, split `test`,
`template_id` `zb-pos0`/`zb-pos1`. Every factor level is recorded in `construction` together with `names`,
`object_pair` [O1, O2], `binding`, `asked_object`/`asked_name`, `first_mentioned_candidate`, `answer_position`,
`answer_is_first_mentioned`. `primary.candidates[0]` is the answer of version A (INTERFACES §1 convention).

**Name sets.** Token-length matched under the whitespace heuristic (one whitespace-delimited word per name) with
equal character length (4) as the tie-break; recorded in `meta.name_sets` / `meta.name_token_heuristic`.
Supplementary observation (not a dependency of the build): with the locally cached Qwen2.5 tokenizer all eight
names are one token both with and without a leading space, so the first-mentioned name (sentence-initial in pos0)
and the second one tokenise alike.

**Objects.** The 16 Phase X objects (`build_dataset_x.OBJECTS_X`, all "colour noun") are matched by seed into 8
disjoint pairs with distinct colour and noun words:
green hat | purple book, gold coin | white pen, blue rope | silver ring, blue cup | orange lamp,
black bag | brown coat, grey ball | pink scarf, red flag | yellow box, green bottle | red key.
Each object pair is used 16 times (128 pair slots / 8), and exactly equally often within every level of every
factor (4 uses per name set, 8 per level of each binary factor) via a balanced block assignment
(`build_bank.object_block`) plus a seeded rotation; which object is O1 is balanced 8/8 per object pair, so each
object is the asked object (object_to_name) or X's object under x_o1 equally often. Within a cell the two pairs
share everything except the object pair (checked: the word multisets agree after removing the object words).

**Counterbalancing counts** (from `meta.balance_checks`): every binary factor 64/64 pairs, name sets 32 each;
answer first-mentioned in A: object_to_name 32 true / 32 false, name_to_object 32 / 32. Note that in the
name_to_object direction the answer's statement is the asked name's statement in *both* versions, so the A/B
difference is never carried by an "answer is in statement 1 vs 2" code there; in object_to_name it flips, as in
Phase X, but now balanced in sign over the cells (`check_variance.order_flip`).

**Answers** are re-derived from the prompt text: `build_dataset.solve_prompt` for object_to_name (the existing
solver, unchanged) and `build_bank.solve_name_to_object` for name_to_object (additive; the existing solver only
supports name candidates). The build fails on any disagreement.

Example prompts (version A / version B):

- object_to_name, pos0 — `zb-00-1A`: "Emma has the green hat. Anna has the purple book. Who has the green hat?
  Answer with the name only." → Emma; `zb-00-1B`: "Emma has the purple book. Anna has the green hat. Who has the
  green hat? Answer with the name only." → Anna
- name_to_object, pos0 — `zb-01-1A`: "Emma has the blue rope. Anna has the silver ring. What does Emma have?
  Answer with the object only." → blue rope; `zb-01-1B`: "Emma has the silver ring. Anna has the blue rope.
  What does Emma have? Answer with the object only." → silver ring
- object_to_name, pos1 — `zb-08-1A`: "Consider the following two statements. Emma has the grey ball. Anna has the
  pink scarf. Who has the grey ball? Answer with the name only." → Emma
- name_to_object, pos1 — `zb-09-1A`: "Consider the following two statements. Emma has the yellow box. Anna has
  the red flag. What does Emma have? Answer with the object only." → yellow box

## Files

- `build_bank.py` — generator (`--seed 20261010`, `--print`, `--no-write`); validates every invariant and
  refuses to overwrite a frozen bank.
- `items_binding_factorial.json` — the bank (items.json schema + `construction`), `meta.sha256_items` =
  `58052b1d5d41afece93226c24578ffb67cceabebad92c97a59792523df3591aa`.
- `check_variance.py` — the verify-before-scoring check on captured states (below).
- Tests: `projects/g_agreement/tests/test_z5_bank.py`.

## Capture (X1 protocol; ≈ 30 min pod)

```
python -m projects.g_agreement.x1_bank.collect --phase A --items-file projects/g_agreement/banks/binding_factorial/items_binding_factorial.json --split all --allow-unfrozen
python -m projects.g_agreement.x1_bank.collect --phase B --items-file projects/g_agreement/banks/binding_factorial/items_binding_factorial.json --split all --allow-unfrozen
```

Phase A captures the block-42 last-token state of all 256 items into `cache/g_agreement/states/<item_id>.pt`
and scores J-lens and the Oracle lens; phase B scores NLA. `--allow-unfrozen` is required because
`manifest/frozen_config_x.json` records the Phase X item file; the bank's own sha is recorded per LO row
(`items_file_sha256`). Rows land in `cache/g_agreement/x/x1_lo.jsonl` under module `x1` (keys `<reader>|zb-…`).

Caveats for the capture: (i) the NLA templates are keyed on family (`scoring_lo.NLA_TEMPLATES["ownership"]`
says "the name"); for name_to_object pairs the candidates are objects, so a dedicated template key would be
needed in `core/scoring_lo.py` before NLA scores of that half are interpreted (J-lens and the Oracle lens score
the candidate tokens directly). (ii) The E3 mean-state rows average all 256 states, mixing both query directions;
treat them as descriptive.

## Verify before reader scoring (pre-registered stop rule)

```
python -m projects.g_agreement.banks.binding_factorial.check_variance            # after phase A
#   --items … --states-dir cache/g_agreement/states --out-dir results/g_agreement/z5 --threshold 0.25 --n-relabel 20
```

Writes `results/g_agreement/z5/variance_check.{json,md}`; exit code 2 when the stop rule fires.

1. `d = h_B − h_A` per pair; centred PCA (uncentred energy share also reported, R2R4 convention).
2. R² of the PC1 (and PC2, PC3) scores on each factor's one-hot dummies, plus η² in the full difference space;
   repeated within each query direction.
3. **Stop rule**: any stop-rule factor with R²(PC1) > 0.25 → report and stop (no reader scoring). Stop-rule
   factors = the five design factors + `order_flip` (the pair-level parametrisation of mention order that R2R4
   found: first_to_second / second_to_first / none). `answer_identity` (A's answer) is a diagnostic row only; it is
   the signal, not a confound.
4. **Hewitt–Liang control**: a leave-one-pair-out difference-in-means probe trained on a randomly relabelled
   pairing (20 relabellings) must be at chance: mean LOO accuracy ≤ 0.55. The probe on the true pairing label and
   on order_flip (object_to_name half) is reported descriptively.

Tested on synthetic states (`tests/test_z5_bank.py`): a planted single-factor direction (template, or order_flip)
triggers the stop with R² ≈ 0.95 on that factor alone; balanced noise gives R² ≈ 0.01–0.02 per factor and passes
the Hewitt–Liang control.

## Deviations
(none)
