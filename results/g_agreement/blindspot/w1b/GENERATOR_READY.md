# §84 generator ready — no production selection or bank yet

`projects/g_agreement/blindspot/w1b_items.py` covers all 138 frozen §79 features.
The local lens-owned `screens/features.py` was older, so W-core preserved it and
stored a byte-identical snapshot of the current published registry in
`w1b/registry_features.py`. Its origin, Git blob SHA and byte hash are recorded
in `w1b/REGISTRY_ORIGIN.json`. The difference from the old local copy is the
explicit lexical word lists in frozen scoring phrases; predicates are unchanged.
Nothing in Suraj's external subtree or the lens-owned source was modified.

Before selection, only generator recipes and synthetic/prototype validation run.
No actual §84 bank, selected-item manifest, probe or reader output exists yet.
Every frozen feature has a deterministic fresh recipe; twelve authored carrier
grammars are fixed before the top-ten ranking arrives. Production uses seven
opposite-value pairs per carrier (168 items/feature), with six dev and six test
template clusters and 42 items per value in each split, as in W1.

Each pair is matched to exactly the same number of native Qwen tokens. Crucially,
the frozen extractor checks the *entire final padded prefix*, for both values.
Padding cannot silently change line/word counts, lexical membership or parser
state. The pinned tokenizer JSON hash and native true/false + yes/no candidates
are checked. `verify_lengths` retokenizes every final item, rechecks labels, and
requires per-row/per-split KS p > 0.2 and mean token difference ≤ 1.

Before any production item is built, supply the normal selection receipt:
`source_commit`, repository-relative `selection_file`, `selection_sha256`,
`section79_features` (the exact ordered selected list), `section81_features=[]`.
The selection commit must exist locally; `git show COMMIT:FILE` must match the
receipt hash and the exact feature list. Unknown features, absent commits,
ambiguous lists, altered bytes and list mismatches are rejected before building.
§81 candidates require their own committed evidence and are not guessed from §79.

Once the committed top ten arrives, run:

```bash
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
python -m projects.g_agreement.blindspot.w1b_items \
  --selection-receipt COMMITTED_SELECTION_RECEIPT.json \
  --tokenizer LOCAL_PINNED_QWEN_TOKENIZER_DIRECTORY \
  --out cache/g_agreement/blindspot/w1b-bank-v1 \
  --freeze-out results/g_agreement/blindspot/w1b/freeze \
  --stage-out cache/g_agreement/blindspot/w1b-stage-v1
```

The command uses the existing W1 `write_bank`, `export_freeze`, `stage_bank`,
input/label seals and manifest format, with an explicit feature-registry parameter
(default W1 behaviour is unchanged). Full labels stay local and out of the stage.
It freezes two phrasings per reader, row class/domain, donors, split assignments,
registry/generator source hashes, tokenizer pin and committed selection receipt.
Since §79 definitions are whole statements, the two frozen wrappers use those
statements directly (Oracle bullet/read-position forms; NLA statement/read-position
forms), rather than inserting a sentence into W1's nominal "has X" grammar.
Positive/negative definitions and the score orientation remain exactly §79's.
The main §84 bank has no ordinal binarisation or post-score selection.

Commit the small freeze files locally **before capture**, then create the ordinary
W1b launch request via `stage request --experiment W1b`. W1b retains its separate
3,600 s science cap, integrator assignment and first-science clock. The integrator
pushes and operates; W-core performs no launch. This work does not change W1's
NOT MET verdict, sealed outputs, existing directions or the archived W5 source.
