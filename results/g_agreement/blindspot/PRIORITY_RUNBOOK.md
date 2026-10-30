# W1 execution order — frozen whole bank

The bank from `fe7c7513` is unchanged. `w1/EXECUTION_PLAN.json` binds its original
manifest/input seal to the updated executable source. This is an execution partition,
not a staged scientific decision. W1 is evaluated once on every row at the end.

| Unit | Items | Rows | Serial pod | Parallel pod |
|---|---:|---|---|---|
| priority | 840 | table_column, prose_paren, prose_sentiment, python_effect, latex_subject | A, first | A, first |
| remainder_a | 2,808 | Frozen plan lists exact rows | A, second | A, second |
| remainder_b | 3,648 | Frozen plan lists exact rows | A, third | B |

Each parallel pod has 3,648 items. The integrator may assign two pods only after
confirming concurrent reads from the weights volume. Otherwise start one immediately.
If a second pod arrives after priority capture, reassign only untouched remainder units
under a replacement fleet receipt that accounts for all prior custody. Do not repeat work.
The shared W1 reservation plus previous GPU seconds must stay at or below 7,200.
Serial assignment: `allocation_group.mode=serial`, one allocation with all three units.
Parallel assignment: `mode=parallel`, A owns priority/remainder_a, B owns remainder_b.
Every allocation records exact pod ID, provider creation, deadline, seconds and units;
each worker gets the complete group receipt. Retrieval reserves 180 seconds per pod.

Use the source commit and archive in the updated request, not the original bank source.
Stage `w1-stage-v2` and the execution plan; retain all labels on the analysis machine.
The integrator's passed volume load test is the final provisioning prerequisite.

```bash
export BLINDSPOT_EXECUTION_PLAN="$PWD/results/g_agreement/blindspot/w1/EXECUTION_PLAN.json"
export BLINDSPOT_UNIT=priority
export BLINDSPOT_PRIORITY_ROOT="$PWD/cache/g_agreement/blindspot/w1-units/priority"
# ASSIGNMENT, BANK and ASSETS are supplied paths; BANK is label-free w1-stage-v2.
OUT="$PWD/cache/g_agreement/blindspot/w1-units/$BLINDSPOT_UNIT"
projects/g_agreement/blindspot/pod_run.sh target "$ASSIGNMENT" "$BANK" "$ASSETS" "$OUT/target"
projects/g_agreement/blindspot/pod_run.sh nla "$ASSIGNMENT" "$BANK" "$ASSETS" "$OUT/nla" "$OUT/target"
```

These commands seal all four readers' true and mismatched asked scores for the unit.
Immediately retrieve priority target/NLA outputs to the analysis machine. Before any
whole-bank analysis, run locally:

```bash
python -m projects.g_agreement.blindspot.early_export \
  --bank cache/g_agreement/blindspot/w1-bank-v2 \
  --execution-plan results/g_agreement/blindspot/w1/EXECUTION_PLAN.json \
  --target cache/g_agreement/blindspot/w1-units/priority/target \
  --nla cache/g_agreement/blindspot/w1-units/priority/nla \
  --training-labels cache/g_agreement/blindspot/w1-priority-training-launch/priority.dev.DO_NOT_STAGE.jsonl \
  --out results/g_agreement/blindspot/w1/priority_training
```

Commit `probe_directions.npz`, `probe_directions.json`, `TRAINING_EXPORT_SEAL.json`
immediately after validation and secret scan, with `git pull --rebase` before push.
They contain dev-only directions and both class means at blocks 42/44. Export no test
IDs, scores, metrics, means, projection gaps or activation paths at this early stage.
Notify W-mechanism, W6 and W7 through the repository HANDOFF with the commit/path.

Run the same target/NLA commands for assigned remainder units, changing BLINDSPOT_UNIT
and OUT. The priority pod must supply its sealed priority root before remainder work.
Pod B can start its assigned remainder_b independently. Collect registered free readouts
with `pod_run.sh free-target` and `free-nla` on each unit's same directories, within cap.
Canonical batch intersections freeze sampled seeds independently of allocation mode.
Retrieve arrays and all seals before release; missing free judgments remain NOT RUN.

After every asked grid is sealed and retrieved, assemble canonical whole-bank order:

```bash
python -m projects.g_agreement.blindspot.assemble \
  --bank cache/g_agreement/blindspot/w1-bank-v2 \
  --execution-plan results/g_agreement/blindspot/w1/EXECUTION_PLAN.json \
  --units-root cache/g_agreement/blindspot/w1-units \
  --out cache/g_agreement/blindspot/w1-assembled
```

Run the registered `run analyse` once against these assembled target/NLA directories
and the original bank. Commit the complete analysis, including rule-(i) successful-row
list, directions, and activation path/hash/order receipts. Append one HANDOFF line:
`W1: (i) PASS/FAIL; (ii) PASS/FAIL; (iii) PASS/FAIL; verdict <registered status>.`
Use NOT EVALUABLE instead of inventing pass/fail when a registered denominator is empty.

Proceed immediately to W5 on the same pod when integrator custody/time permits, with
a separate W5 assignment capped at 1,800 GPU seconds. Reuse the loaded volume; charge
each custody second once. Set `BLINDSPOT_W1_ANALYSIS` to the complete sealed W1 analysis
directory, keep BLINDSPOT_EXECUTION_PLAN, and run `pod_run.sh sweep`. All six registered
blocks (20,28,36,44,52,60) are required; analyse-sweep follows retrieval. No cap increase.
Every operation is logged to log.md and compute.jsonl. §84 remains selection-dependent.
