# E82 grouped judging: source-bound renderer intake

E82 scientific acquisition is sealed and closed. The CPU inventory contains all 209 items × two readers = 418 groups and all 13,580 native outputs. The original W-text export requires every knowledge_cutoff position to remain grouped by item for judging, separate belief/truth judgments, and a seeded 25% original-rubric comparison. Ten source items have no canonical truth: retain belief-mention reporting and exclude their truth contrast.

The inventory is at `cache/g_agreement/i2/e82_judge_cpu_v1` on I-2. Public verification is `results/g_agreement/i2/E82_JUDGE_CPU_INVENTORY.json`; private target hash is 9ff51079b6327439f67e5940ccf1382d34947d989ebc273807229ce8a8cc6652. Private targets and joins remain local.

The existing `channels81_86.py` accepts one string readout with exactly two candidate values. The existing E87 grouped adapter has a bank-specific maximum of 16 positions, offsets -15 through 0, and a first-position schema. It cannot be used unchanged for E82's complete all-prompt-position groups. Neither adapter supplies an explicit belief-only schema for the ten missing-truth items. Reusing E87's admission or silently taking the final token would violate E82's source contract.

Before paid dispatch, bind a reviewed E82-specific renderer that:

- Retains every chronological position and native text, with exact opaque group/position bindings.
- Implements the registered separate belief and truth judgments without exposing correct-value labels or inferring missing truth.
- Retains original source target strings and aliases, with no arbitrary substitute distractor for a missing truth.
- Defines the grouped judgment's output and evidence validation without importing E87's first-position scientific interpretation.
- Retains the frozen §172/§202 rubric versions, model, route and output limits, including seeded original-rubric comparison and terminal missingness handling.

Then render every actual wire and calculate the full first-pass upper bound against E82's registered USD 3 cap. This intake is not a cap proposal, allocation, dispatch admission, scientific verdict or authorization to message another chat. No API calls or reservations have been made. The existing E86/E99 cap questions are unrelated and remain pending actual human replies.

## Resolved CPU implementation — 2026-10-29T01:49:13.964097+00:00

The E82-specific adapter is now implemented in `e82_grouped_judge.py` and passes eight synthetic tests. Every native position remains in a structured group; metadata is outside native text and no E87 first-position rule is used. Belief and truth receive separate opaque records with label-independent, shared frozen candidate order. The ten missing-truth items have only belief records; their unused B description is empty, and any B code is rejected as undefined rather than inventing a truth target. All canonical strings/aliases are retained. The original rubric sample is regenerated under E82 seed20261028. Exact full-wire preflight is17.349821875USD/1020requests, above registered3; total18proposal requires actualhuman authority. No sends/reservations.
