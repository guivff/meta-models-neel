# E131 subject-text acquisition (§239)

Generation only, 840 cells on the original 84 fact_recall TEST items. No readers,
judging, cohort selection, answer parsing, old/new labels, fits or scientific metrics.
E104 steered/random alpha8 and unhooked (252); E128 steered/random alpha2/4
(336); E127 unchanged context_update/neutral_prefix/none (252). Unhooked and
E127 none remain separate registered cells even though their prompts match.

The packet copies full token sequences, final read positions, ordered candidate
token pairs and already-composed deltas from the three original input seals.
The original `intervene_forward(...,'U',1,observe=False)` runs at every greedy
full-prefix forward: original eight positions before the ORIGINAL read token at
block40 only. Never patch the read token or generated positions. No second dose
multiplier, new random draw, norm manipulation or extra observation pass.

Generation runs up to64 greedy tokens, stopping on original tokenizer EOS;
no cache/sampling, same full-prefix semantics as E127/E128. Preserve raw token IDs,
decoded text with and without special tokens, EOS/length reason. First-pass
`pairs_from_logits` records ordered raw logits/full-vocabulary logprobs and
mean(A-B), with no old/new orientation. It uses the SAME forward as the first
chosen token; no extra candidate forward or preference recomputation. CPU B
owns leading-whitespace stripping, unchanged parse_target_answer and R-TX1.

## Sole Track Q integration

1. Before any production output, require B's committed/tested prospective adapter,
   verify exact source/input/archive seals, empty label tree, actual runtime CPU
   imports from a fresh extract, and original whole-need clock/cap/once admission.
2. `python -m projects.g_agreement.e131.runner --input INPUT --input-sha HASH --validate-only`
   validates exactly840cells/504deltas without loading a model.
3. Load the ORIGINAL subject only (no Oracle/NLA/PEFT adapter): use the pinned
   E79 runtime subject setup/assets, Qwen revision in config, bfloat16, eval mode.
   `runtime.load_base(); model,tok,cm=runtime.subject()`; use `with cm:` below.
4. `items,deltas=runner.load(INPUT,HASH)` then
   `runner.acquire(model,tok,items,deltas,FRESH_OUT,check_work,gpu_type=ACTUAL,batch=8)`.
   Existing Track Q callback must include original staging/setup/warm-up elapsed,
   maximum measured setup, warm-up-discarded timing and conservative remaining
   global maximum batch time ×1.25 plus reserve. This helper supplies remaining
   batches/acquisition elapsed/global maximum completed batch duration; callback
   retains ORIGINAL pod clock and specific cap. Do not reset it at acquire.
5. Planning cap1440s/0.4GPUh; create by10ZFri, hardstop min(original cap,12:50Z).
   Q owns stock/priority/timing/launch/backstop/retry authority/custody/billing.
   No unregistered retry or cap increase follows from NO_FIT. Fresh attempt only;
   excluded partials cannot be resumed or stitched. Keep output sealed for B/R-Q.

Public input archive excludes cpu_only completely. CPU SOURCE_POINTERS and
LABEL_SOURCE map opaque E131 identities back to exact original IDs and existing
E127 sealed old/new candidate strings; never stage those files to a pod.
