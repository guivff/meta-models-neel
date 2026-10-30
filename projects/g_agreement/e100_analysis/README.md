# E100 once-only analysis — §208

Original authority f425a5e2; all-84 clarification fd07c12a; production withdrawal
69f8c08e4. CPU only. The original c/d rules remain pure functions with synthetic
tests, but production labels R-C4, R-D1, H-T and H-U WITHDRAWN. Their data are
never inferred from E79 or silently substituted. E79 Arm A's null appears first.

Commit every file here and its pinned dependencies before running either
production command. Both commands verify that all source/tests/documentation
match HEAD before opening an E100 readout. No real analysis was run in preparing
this adapter. This source gate is a preventive custody control, not proof of a
historical freeze date; retain the source commit in the Integrator receipt.

```
python3 projects/g_agreement/e100_analysis/adapter.py export --spec /CPU/E100_SPEC.json
# W-internals runs the existing E56 blind route and signs JUDGMENT_SEAL.json.
python3 projects/g_agreement/e100_analysis/adapter.py analyze --spec /CPU/E100_SPEC.json
```

The JSON spec has these required keys:

- authority: `69f8c08e4`; stage: `ab`.
- targets_seal: absolute CPU TARGET_SEAL.json; targets_sha256: full hash.
- runner_source_sha256: frozen E100 runner SOURCE_SEAL.json hash.
- shards: object with reported and missed entries, each containing seal (absolute
  OUTPUT_SEAL.json), sha256 and input_sha256. Both shards must be COMPLETE.
- blind: new public packet directory; private: new private join file outside it.
- judgments: W-internals judgment directory, binding the exact BLIND_SEAL.json.
- analysis: new output directory; the guard is not configurable. Its fixed path is
  `/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e100/ANALYSIS_ONCE.json`.
- e79_seal and e79_sha256: historical Arm A ANALYSIS_SEAL.json and its full digest
  `eb8367a52f0a8d5577aed2c48ed74dd29260e3172e6fe66dd12815d48bc6e2d9`, verified against commit `23ed827a`. The saved RESULTS.json must match its sealed digest. Other historical files need not be materialized.

TARGET_SEAL.json must bind TARGETS.json with experiment E100, labels_cpu_only
true and mapping `donor_family_registered_values`. Each of the 672 unique opaque
items has id, row, source_item_id, donor_id, donor_source_item_id, property,
values {A,B}, target A/B. These are donor-family registered value pairs, including
per-item digit pairs. Do not invent labels from a text or coarsen a value family.
Keep this bundle, all labels, and the private blind join CPU-side. No private
metadata goes into WIRE_PACKET.json, only property, two values and readout.

The adapter verifies the complete 6,720-cell acquisition, every sealed job,
all-84 row grids, native layer contract, norm flags and per-shard GPU types. One
item bootstrap (2,000 draws, seed 20261027) is shared across conditions/readers
within each row; different rows use independent draws. UNPARSEABLE is missing,
both/neither is zero. Missing masks retain separate denominators and undefined
bootstrap draws invalidate the interval; no complete-case filtering. Missingness
over 5% is flagged. Redaction sensitivity repeats frozen calculations with the
same item grid. Oracle alone bears rules; NLA is exploratory.

R-PC's falsifier (three reported rows below .20), rather than failure to pass
R-PC, gates b–d. Unresolved falsifiers fail closed. H-C3b lists dominance for the
R-C3 qualifying rows and the registered complement alternative. Archived H-T
and H-U report each registered dose separately: §208 supplies no dose pooling
rule. Alpha 4 cannot rescue a rule-bearing original c result. R-D1 tests both
its paired-bootstrap group contrast and the reported/missed mean dev-probe
shift ratio; missing checks are NOT EVALUABLE. No original c/d function is
called by production.

FIGURE.png shows all eight rows, Oracle and exploratory NLA with intervals,
and copies the three missed rows' saved E79 estimates and intervals. E79 is
never re-scored or re-bootstrapped. Historical alpha 4 is labeled descriptive.
The output seal binds results, redaction sensitivity, per-cell manipulation
ratios, figure, source commit, E100 outputs, target seal, judgments and E79 seal.

Synthetic verification:
```
python3 -m pytest -q projects/g_agreement/e100_analysis/test_analysis.py
```
Requires numpy, pytest (tests), matplotlib (figure); no model or GPU library.
The once-only guard is consumed only after validating custody and plotting
availability. A failed analysis after claim is not retried without an explicit
registered disposition from the Integrator; never remove the guard silently.
