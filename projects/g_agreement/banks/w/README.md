# W Track A — graded bank (`banks/w`)

Pre-registered in `projects/g_agreement/PREREG_WV.md` §Track A (brief: `manifest/brief_wv.md`, "Track A: graded
bank"). Generation is CPU-only, no model calls, deterministic from **seed 20261011**. Written 2026-10-11 before the
pod start. Every file carries a `meta` block with seed, counts and `sha256_items` (canonical JSON of the items, as in
`build_dataset.sha256_items`).

| file | what | items | sha256_items |
|---|---|---|---|
| `items_w.json` | counts 600 + ownership4 128 (64 pairs) + arith 100 | 828 | `ec8e83637e723157f4fc6596131de2a81040b00311386f4d9654144ed3d5f46e` |
| `items_v7.json` | V7 target-private ownership pairs (16 pairs) | 32 | `253070eb1b5074ff9820d4fd87bd9b396a78082a1a761ed2951e43cc676ba878` |
| `mapping8_index.json` | index of the 47 X mapping test pairs scored over all 8 symbols (no new prompts) | 94 | `c8ed451ab925e7893cd3c029ec93ae0b22cdae687368fe93745dd746e0c8391e` |

Schema: the items.json schema (INTERFACES §1: `item_id, pair_id, version, family, split, template_id, prompt_text,
render, system, primary{name, question, candidates, answer, answer_aliases}, secondary, target_answer_regex, notes`)
plus `construction` (every design factor), and for the graded families `primary.candidates_all` (the full value set
for graded scoring). `split` is `test` everywhere. counts and arith are **singletons**: `pair_id = item_id`,
`version = "A"`, `construction.singleton = true`. Ids are disjoint from `items.json`, `items_x.json`, `items_g6.json`
and the Z5 bank (`zb-`): `wcnt-0001…0600`, `wown-00A…63B`, `warith-001…100`, `wv7-01A…16B`.

## Families

### counts (600, `wcnt-`)
"There are N `<object>` in the `<place>`. … How many `<object>`?", N = 1…99, answer `str(N)`,
`candidates = [str(N)]`, `candidates_all = ["1", …, "99"]`, `primary.name = "<object>_count"`, render `chat`.

| factor | levels | per level |
|---|---|---|
| value N | 1…99 | 6 uses each; six values (2, 19, 38, 64, 68, 88; one per sixth of the range, seeded) get a 7th |
| template | t1 "There are N O in the P. How many O are in the P? Answer with the number only." / t2 "In the P there are N O. … Reply with the number only." / t3 "The P contains N O. How many O does the P contain? Answer with the number only." / t4 "Someone counted the O in the P: there are N. … Give just the number." | 150 |
| object | marbles, apples, coins | 200 |
| template × object | 12 cells | exactly 50 |
| place | jar, basket, box, drawer, bag, bowl, crate, bucket, tray, chest, sack, bin | exactly 50 (4–5 per cell) |

Per value: each object exactly twice, every template at least once and at most twice (pattern 2,2,1,1; which two
templates are doubled varies by a seeded template permutation). Construction (`build_w_bank.counts_design`): the 99
values and one "extras" group (the 6 seventh uses) are paired **within a decade**; the two groups of a pair take the
complementary 6-cell windows of a 12-cycle over the (template, object) cells, so every cell is hit exactly 50 times
and each decade of ten values has each template exactly 15 times. N = 1 is rendered grammatically ("There is 1
marble …"; the question stays plural); `construction.singular` records it. The number is always in digits.

### ownership4 (64 pairs = 128, `wown-`)
The Z5 factorial machinery (`banks/binding_factorial`) with **four** names each holding a distinct object. Statement
wording and questions are Z5's (`"{N} has the {o}."`, "Who has the O? Answer with the name only." / "What does X
have? Answer with the object only."). A and B of a pair differ only in that the two holders exchange their objects
(token permutations; checked by word multiset).

| factor | levels | pairs per level |
|---|---|---|
| `name_set` | ns0 Emma/Anna/Lisa/Kate, ns1 Adam/Paul/Eric/Luke, ns2 Mira/Nora/Rosa/Vera, ns3 Hugo/Noah/Finn/Theo (one whitespace token, 4 characters each) | 16 |
| `template` | pos0 / pos1 (pos1 prepends "Consider the following four statements.") | 32 |
| `mention_order` | m0…m3: statement position p shows name p XOR c (Klein Latin square: every name at every position once) | 16 |
| `holder` | n0…n3: which name of the set holds the asked object in version A; holder = block XOR (ω·c) over GF(4) | 16 |
| `query_direction` | object_to_name (candidates = the 4 names) / name_to_object (candidates = the 4 objects; asked name = A's holder) | 32 |
| `holder_b_shift` | 1/2/3: B's holder is the name mentioned `shift` statements after A's holder (cyclic) | 22/21/21 |

Cell `i = 16·name_set + 4·block + c`, template = block // 2, query_direction = block % 2. Within every name set all
pairs of design factors are fully crossed and balanced, **and the statement position of A's answer
(`construction.answer_mention_position`, 0–3) is balanced (8/8 or 4/4) against every design factor** — this is why
the mention orders are the Klein square and the holder is `block XOR ω·c` rather than cyclic rotations: with
rotations the answer's position would be a deterministic function of template × query_direction (caught by the
synthetic test of `check_w_variance`). B's position is A's + shift; the shift pattern is stratified by name set ×
pos_A (6/5/5 per name set) and its doubled level goes to one cell of each template.

Objects: the 16 Phase X objects in 4 seeded quadruples with distinct colour and noun words
(brown coat | orange lamp | silver ring | yellow box; blue rope | green bottle | purple book | white pen;
gold coin | green hat | grey ball | red flag; black bag | blue cup | pink scarf | red key); quad = (c + name_set) % 4,
each used 16 times, every object asked 4 times. `primary.candidates` has 4 entries in the same order in A and B with
`[0]` = A's answer and `[1]` = B's answer (the two-candidate convention extended); `construction.other_candidates`
lists the three distractors. Answers are re-derived from the prompt text (`build_dataset.solve_prompt` for
object_to_name, `binding_factorial.solve_name_to_object` for name_to_object).

Example (cell 00, object_to_name, pos0): `wown-00A` "Emma has the silver ring. Anna has the yellow box. Lisa has the
orange lamp. Kate has the brown coat. Who has the silver ring? Answer with the name only." → Emma; `wown-00B` "Emma
has the yellow box. Anna has the silver ring. Lisa has the orange lamp. Kate has the brown coat. Who has the silver
ring? …" → Anna. (cell 04, name_to_object): `wown-04A` "… Anna has the silver ring. … What does Anna have? Answer with
the object only." → silver ring; `wown-04B` → brown coat.

### arith (100, `warith-`) — Michael Kenney's format, for the bridge only
Text `f"{a} {op} {b} ="` exactly as `nla-consistency/scripts/thread12_pod.py::arith_prompts` (and
`data/arithmetic.jsonl`, 600 rows, sha256 `1dbfd7a4…`): op alternates `-` (even index) / `+` (odd) → 50/50;
`a ~ U{2..99}`; `b ~ U{1..a−1}` for `-` (answer ≥ 1) and `U{1..99}` for `+`; our seed, triples that occur in his 600
excluded, every decade 0–9 of a and of b covered (the whole set is re-drawn until it is; deterministic). Fields:
`operands {a, b, op}` (top level and in `construction`, with tens/units digits for the digit probes), answer
`str(a ± b)`, `candidates_all = ["0", …, "198"]`, `primary.name = "arith_result"`.

**Render note (`render: "plain"`, `render_note` on every item).** Michael feeds the raw text with **no chat
template and no special tokens**: `ids = tok(text, add_special_tokens=False)["input_ids"]`, captures the layer-42
activation at the **last token `=`** (`b.capture(ids, [LAYER], [len(ids) - 1])`) and takes the greedy next token as
`argmax logits[-1]` (`thread12_pod.py capture()`). The S1 capture must do the same for this family — not
`core.model.render_item`. Caveat from his data: in this plain format the base model's greedy next token is mostly
`" ?"` (483/600) or `" "` (114/600), i.e. it does not answer; his steering test therefore used a few-shot prefix
(`steer_pod.py FEW = "12 + 7 = 19\n45 - 13 = 32\n8 + 26 = 34\n71 - 9 = 62\n"`). The bridge numbers (probe
exact-match for a and b, NLA exact-match, Spearman) are read from the activation and do not need the model to
answer; first-token log-odds over `candidates_all` are still well defined. If the pod also wants a model answer for
this family, prepend `FEW` as a separate, recorded variant — do not change the plain render.

### mapping8 (`mapping8_index.json`, no new prompts)
The 47 X mapping test pairs (`xmap-02…48`, 94 items; `items_x.json` `sha256_items dee9467a…`, recorded in the
index) scored natively over all 8 symbols `A…H` (`candidates_all`). Per item: `answer`, the pair's two `candidates`,
`k`, `start`, `intermediates`, `k_minus_1_symbol` (the "stops one step early" symbol for V2). The prompts and states
are the X1/X2 ones; S1 re-captures them at the W layers from `items_x.json` using this index to select items.

## V7 target-private pairs (`items_v7.json`, `wv7-`)
16 ownership pairs, `family = "ownership"`, object_to_name. The binding is stated **only** in `preamble`
("Background: Ivan has the yellow box and Paul has the gold coin." — template p0 — or "Context for this
conversation: N1 has the o1. N2 has the o2." — p1; 8/8), shown to the target at capture time as a **system turn**
(`preamble_role = "system"`; `capture_messages = [{"role": "system", "content": preamble}, {"role": "user",
"content": prompt_text}]` is spelled out on every item, to be passed to `apply_chat_template` with thinking off and
the generation prompt appended, as `core.model.chat_ids` does). `prompt_text` is the **visible prompt**, identical
within the pair ("Who has the yellow box? Answer with the name only."); the two versions differ only in the
preamble's binding (token permutations). The names are never in the visible prompt, so no prompt-only method can
separate A from B: `prompt_only_text` = `core.config.PROMPT_ONLY_TEMPLATE` over the visible prompt and the primary
question only (sha of the template recorded in `meta`), identical for A and B → the prompt-only baseline is 50% by
construction. `system` stays `null` in the schema (the preamble is not a dataset system prompt; it is the
target-private context). Names from `build_dataset_x.NAMES_X` (16 distinct pairs; two names reused once), objects the
8 Z5-style colour/noun-distinct pairs each used twice (asked object alternating), answer first-mentioned in the
preamble 8/8. Capture at layers 38 and 42, last token and the post-statement span (the span is inside the system turn
here; record the positions).

## Checks

**Before the pod (done 2026-10-11):** `python -m projects.g_agreement.banks.w.check_prompt_balance` → 
`results/g_agreement/w/bank_checks.json` (45 checks, all pass): counts value/template/object/cell/place balance,
per-value coverage, decade × template and decade × object near-uniform; ownership4 factor and pairwise balance,
A/B token permutation and holder swap, solvers; arith ops, decades, Michael's regex, plain render, no shared triple;
mapping8 against `items_x.json`; V7 identical visible prompt, preamble permutation, no candidate in the visible
prompt, prompt-only text; id/prompt disjointness.

**On the S1 captures (pre-registered stop rule, 25%):** `python -m projects.g_agreement.banks.w.check_w_variance
--states-dir <dir with <item_id>.pt fp32 [d] for one layer/position> [--family ownership4|counts|arith|all]`
→ `results/g_agreement/w/variance/variance_check_<family>.{json,md}`, exit 2 on STOP. ownership4: `d = h_B − h_A`,
PCA, R² of PC1 on each stop-rule factor (the six design factors + `mention_pos_A`, `mention_pos_B`), η² in the full
space, by query direction, Hewitt–Liang control (LOO difference-in-means probe on a relabelled binary label ≤ 0.55),
`answer_identity` as diagnostic. counts: family-centred states (`h_i − mean`), stop-rule factors decade, template,
object, place; the linear R² of PC1 on N as diagnostic. **Note:** decade is the graded *signal* of the counts family;
the pre-registered rule nevertheless lists it, so a decade-dominated PC1 is reported as STOP and left to the operator
(a dated deviation would be needed to proceed). arith (optional): op, a_decade, b_decade. Tested on synthetic states
(`tests/test_w_bank.py`): a planted factor direction → STOP on that factor alone (R² > 0.6–0.9); balanced noise →
PASS (R² < 0.1 per factor). The counts accuracy gate (≥ 95% greedy correct, keep only values the model gets right)
is applied by the pod from S1's greedy answers.

## Capture (S1; the pod builder's `w_pod.s1_capture` — intended interface)

```
python -m projects.g_agreement.w_pod.s1_capture --items projects/g_agreement/banks/w/items_w.json \
    --v7-items projects/g_agreement/banks/w/items_v7.json --mapping8-index projects/g_agreement/banks/w/mapping8_index.json \
    --x-items projects/g_agreement/dataset/items_x.json --layers 20 28 38 42 48 52 --out cache/g_agreement/w/states
```

Per item, one forward pass, all positions at the six layers, greedy answer (32 new tokens) and first-token log-odds
over `primary.candidates_all` (counts, arith, mapping8) or `primary.candidates` (ownership4: 4 candidates; V7: 2).
Render by `item["render"]`: `chat` → `core.model.render_item(tokenizer, prompt_text, None)`; `plain` (arith) → raw
text, `add_special_tokens=False`, no template; V7 → `capture_messages` (system preamble + user visible prompt).
States for the variance check: `<out>/L<layer>/<pos-tag>/<item_id>.pt`, fp32 `[d]`. Other things the pod code has to
add before scoring: `core/scoring_lo.NLA_TEMPLATES` has no entries for `counts`, `arith`, `ownership4` (the
`ownership` template says "the name", wrong for name_to_object) — add graded-value templates ("The answer must be the
number \"{X}\".") and object templates; the NLA on counts is in S3/S4 per the pre-registration.

## Files
- `build_w_bank.py` — generator (`--seed 20261011`, `--print`, `--no-write`, `--out-dir`); validates every invariant,
  refuses to overwrite a frozen file. `build(seed)` returns the three documents.
- `check_prompt_balance.py` — prompt-level checks → `results/g_agreement/w/bank_checks.json` (`run()` for tests).
- `check_w_variance.py` — the S1 activation check (reuses `binding_factorial.check_variance` statistics).
- Tests: `projects/g_agreement/tests/test_w_bank.py` (23 tests).

## Deviations
(none)
