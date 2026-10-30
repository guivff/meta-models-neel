# E136 — prospective four prompt-stated cue bank (§247)

W-text bank; W-mechanism-C runner; I-2 integration after E135; W-mech2 probes/behavior; W-text words classifier; W-internals-C judging; R-2 review. Four hundred matched pairs /800 prompts:25 base tasks×4 shared task paraphrases×4 cues. Each cue has20DEV pairs from5whole base tasks and80TEST pairs from20held-out tasks. Both members of every pair share identical user text; all cues are in the system turn. DEV is for probes/vocabulary only; readers run on all800 as registered by the2400readout budget (three layers); word headline uses held-out TEST only. If owner interprets that budget differently, preserve this bank and disclose reader scope, never relabel split.

Cue1 is the registered tool sentence vs absence; cue2 attributes the user's confidently wrong fixed distractor vs neutral question to the system; cue3 states cheating vs studying; cue4 says not to disclose the task's benign true fact vs absence. Benign questions only; no harmful request. Exact authoring conventions, logged before generation, are in understand/e136/WTEXT_CONVENTIONS_PREAUTHOR.json (PROVISIONAL under direct standing order). No model behavior was used to choose questions/answers. Initial unsealed tokenizer QA rejected a two-token distractor/answer; those task definitions were revised before this first complete bank seal. No output exists or was opened by W-text.

`INPUT_BINDING.json` gives immutable public archive and CPU-only labels. Only PUBLIC_INPUTS.tar.gz goes to pods. `items.json` contains exactly id,ids,read_index,candidate_ids; no condition/group/split/sign labels. `candidate_ids` has one pair of ascending token IDs, one token per candidate. C must preserve ids/read_index verbatim; no re-rendering, crop or guessed truth sign. Pinned tokenizer revision and all tokenizer/template hashes are recorded. Chat template add_generation_prompt=true, enable_thinking=false; special tokens added only by the template, add_special_tokens=false at encode. Read at last exact rendered token271, shared by all800. Raw system/user messages, task/pair/cue/split/truth fields are private CPU labels. Bank authoring source/test files contain answer definitions and MUST NOT be included in a pod runtime source archive. C packages its runtime independently; public sorted candidates have no correctness sign.

CPU tests:

```
python -m unittest projects.g_agreement.e136.test_bank -v
```

Never rerun/rebuild the frozen bank to get different items after a score. I-2 must bind exact input seal and original creation clock/cap3600s/10Zcreate/12:50Zhardstop. Bank seal before06Z (07CET); otherwise NOTRUN, no partial reporting. Source readiness does not authorize a pod or paid calls. No BOW build exclusion gate is introduced: explicit cues are in input by design. R-SW1/probe gates/thresholds unchanged; this studies prompt-stated cue breadth, not hidden/private state, causality or repair.
