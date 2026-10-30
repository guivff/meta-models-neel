# Shared file formats (every module reads/writes exactly these)

All JSON/JSONL is UTF-8, `ensure_ascii=False`. Paths are relative to the repo root
`/Users/guivff/Documents/Neel_Exploration/mats-minis` (on the pod: `/workspace/mats-minis`).
Python: `from projects.g_agreement.core import config` etc. (repo root on `PYTHONPATH`).
`third_party/workspace-bench/src` and `third_party/jacobian-lens` are importable (`wsbench`, `jlens`).

## 1. Dataset — `projects/g_agreement/dataset/items.json`

```json
{"meta": {"created": "2026-10-07T..", "seed": 20261007, "n_pairs": 20, "families": ["language","tense","ownership","mapping"],
          "sha256_items": "<sha of the canonical json of items>", "frozen": false},
 "items": [
  {"item_id": "own-03A", "pair_id": "own-03", "version": "A", "family": "ownership", "split": "test",
   "template_id": "own-t2", "prompt_text": "Mira has the red key. Leo has the blue key. Who has the red key? Answer with the name only.",
   "render": "chat", "system": null,
   "primary": {"name": "red_key_owner", "question": "Who has the red key?", "candidates": ["Mira", "Leo"], "answer": "Mira",
               "answer_aliases": ["mira"]},
   "secondary": {"entities": ["Mira", "Leo"], "objects": ["red key", "blue key"],
                 "relation": {"type": "has", "subject": "Mira", "object": "red key"}},
   "target_answer_regex": "(?i)\\bmira\\b",
   "notes": ""}
 ]}
```
Rules: both versions of a pair share `pair_id`, `family`, `split`, `template_id` and the
candidate set; they differ only in which candidate is correct. `primary.candidates` has exactly
two entries, ordered the same in A and B. Over the test set each candidate position is correct
equally often (balanced), and template wording varies across pairs; dev pairs use templates not
reused for test where feasible. `split`: exactly 1 dev pair + 4 test pairs per family.
Family-specific `primary.name`: language → `response_language` (candidates two language names);
tense → `response_tense` (`past`/`future`); ownership → `<object>_owner`; mapping → `two_step_result`.

## 2. Donors — `dataset/donors.json`
`{"seed": .., "assignments": {"<recipient item_id>": "<donor item_id>", ...}, "checks": {"same_family": true, "excludes_recipient_pair": true, "label_balance": {...}}}`
Only test items. Donor from a different `pair_id`, same family. Donor labels balanced (not forced opposite).

## 3. G4 selection — `dataset/g4_pairs.json`
`{"seed": .., "pairs": ["lang-02", "tense-04", "own-05", "map-03"], "item_ids": [8 ids], "chosen_before_test_outputs": true, "timestamp": ..}`

## 4. States — `cache/g_agreement/states/<item_id>.pt` (fp32 tensor [5120]) and
`cache/g_agreement/states_meta.jsonl`, one row per item:
```json
{"item_id": "own-03A", "model_id": "Qwen/Qwen3.6-27B", "model_sha": "6a9e13bd...", "layer": 42, "hook": "block_output",
 "hidden_states_index": 43, "pos": 57, "n_tokens": 58, "read_token": "\n\n", "prompt_ids_sha256": "...", "render": "chat",
 "enable_thinking": false, "dtype_capture": "bfloat16", "dtype_saved": "float32", "norm": 1234.5, "captured_at": "...", "pre_answer": true}
```
`pre_answer: true` asserts the position is the last prompt token (no answer token has been generated).

## 5. Generations — `cache/g_agreement/gens/<module>.jsonl`, one row per model call
```json
{"gen_id": "g1|nla|own-03A|s0", "module": "g1", "method": "nla|olens|jlens|target|prompt_only",
 "condition": "genuine|repeat|prompt_only", "item_id": "own-03A", "state_item_id": "own-03A", "sample_idx": 0, "seed": 1234567,
 "input": {"fixed_instruction": "...verbatim prompt text with marker...", "layer_in_prompt": 42, "visible_prompt": null,
           "prompt_ids_sha256": "...", "injection": "olens_replace_alpha16000_unit|nla_add_normmatched_block1|none",
           "activation_norm": 1234.5},
 "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 64, "max_new_tokens": 128, "do_sample": true},
 "raw_output": "...full decoded text incl. any tags...",
 "native": {"samples": ["...stripped explanation..."]}  // or {"tokens": [..10..], "scores": [..10..]} for jlens
 ,"n_prompt_tokens": 61, "n_new_tokens": 97, "finish_reason": "eos|length", "wall_s": 6.3, "peak_mem_gb": 58.1,
 "model_sha": "...", "adapter": "av_rl_adapters/iter_000400|olens_s3d_rl600|none", "created_at": "..."}
```
Shuffled readouts are NOT new rows: G3 builds them by reassigning cached rows via donors.json
(`condition: "shuffled_cached"` in G3's own derived table). Target answers: `method: "target"`,
`native: {"text": "..."}`. Prompt-only: `method: "prompt_only"`, `input.visible_prompt` = the
frozen question prompt (contains the item prompt text, never a readout or target answer).

## 6. Claims — `results/g_agreement/claims/<module>.jsonl`, one row per (gen_id)
```json
{"gen_id": "...", "method": "nla", "item_id": "own-03A", "extractor": "rule-v1|model:<id>|human:<name>",
 "primary": {"status": "supports|contradicts|unclear|self_contradictory", "value": "Mira"|null, "evidence": "verbatim span"},
 "entities_mentioned": ["Mira","Leo"], "objects_mentioned": ["red key"],
 "relation": {"status": "correct|wrong|unbound|absent", "evidence": "..."},
 "truncated": false, "blind": true}
```
`status` semantics (rubric.md is authoritative): `supports` = exactly one candidate is asserted
as the value of the primary property; `contradicts` = the other candidate is asserted;
`self_contradictory` = both asserted; `unclear` = neither (abstention). Two `unclear` never
count as agreement. Relation `unbound` = both entities/objects named without a binding.
Blinded sheet for human/model annotation: `results/g_agreement/claims/<module>_sheet.jsonl`
with `gen_id`, `method` (format reveals it anyway), `text` only — no item_id, no answer key.

## 7. Compute ledger — `results/g_agreement/compute.jsonl`
`{"step": "load_target|capture|target_gen|olens|nla|jlens|prompt_only|r0_k0|bench_repro", "module": "...", "n_calls": .., "prompt_tokens": .., "new_tokens": .., "wall_s": .., "peak_mem_gb": .., "gpu": "H100 80GB", "started": .., "ended": ..}`

## 8. Frozen config — `projects/g_agreement/manifest/frozen_config.json`
Written once by `core/config.py --freeze` after development: asset ids+shas, caps, sampling,
seeds, dataset sha, rubric sha, donors sha, g4 selection sha, code git/sha of this directory.
Test collection scripts refuse to run if `frozen` is false or any sha mismatches.
