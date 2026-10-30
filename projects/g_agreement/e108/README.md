# E108 native acquisition binding (§219)

This wrapper reuses late198.Runtime capture/native, E56's unchanged Oracle128 and NLA512/closing-tag implementations, and E76 common76.norm_match. Runtime108 adds only raw unpadded greedy64 continuation generation, using the same base subject and terminal-EOS trimming. Original frozen prompts/token IDs/final read indices are unchanged. Text batches are equal length, up to32; three full32-item retained pilots lead. The complete grid is1008continuations plus1092readouts per reader (1008native+84placebo). No choice/category labels or CPU inventory go to the pod.

Placebos use one seeded20261029 Gaussian84×5120 fp32 array, with E76 norm_match separately matching each vector to the corresponding preselected reference prompt's native42/44 norm. Capture and placebo seals precede all reader calls. Outputs retain raw continuation token IDs and exact per-reader raw/text fields. Early delayed choices are not filtered; blind CPU extraction measures their actual offsets later.

One production pod: base load/capture and three retained base64 pilots, Oracle pilot, NLA pilot. Only then admit the whole remaining grid from actual work timings and maximum own setup including creation-through-staging. Continue NLA, reload base for remaining continuations, reload Oracle for remaining readouts. All pilot results are retained without duplicate jobs. Reloads, discarded warm-ups, staging and elapsed custody remain charged. The first complete forecast freezes a tighter creation-based cap (never beyond5400s); later NO_FIT stops. Timing and production share this pod. No new reader implementation, parity gate, choice extraction or scientific analysis is introduced.

The operator supplies an exact-source/inputs/assets assignment with original provider creation, own pod ID matching RUNPOD_POD_ID, one H200, guards and incremental backup armed, fresh ledger/quote admission and the committed analysis-adapter binding. Assignment uses the existing late198 contract fields; cap_seconds+prior_seconds<=5400, custody_start_epoch=pod_created_epoch, absolute_deadline_epoch=pod_created_epoch+cap_seconds. Source/input/assets SHA256 must match. No labels on pods. External guards remain operator-owned; the process also arms an absolute timer and tightens it after measurement. Retrieve every failure and reconcile original custody; pre-load failures do not consume a restart under§217, but remain charged. No automatic retries.

Run from extracted source root:

```sh
python -m projects.g_agreement.e108.worker --inputs /PATH/inputs --input-sha INPUT_SHA --assets ASSETS.json --assignment ASSIGNMENT.json --source-seal results/g_agreement/understand/e108/runner/SOURCE_SEAL.json --source-sha SOURCE_SHA --out FRESH_OUTPUT
```

Packaging: `python -m projects.g_agreement.e108.package --public FROZEN_WTEXT_DIRECTORY --out FRESH_CACHE_DIRECTORY`. Verify fresh exact-source imports including actual Runtime/worker56/native_nla512/mats readers and run the synthetic tests before CREATE. Source/input hashes and CPU rehearsal belong in the owner E108 HANDOFF. I-3 owns allocation/admission and once-only analysis; W-internals-C owns blind judging under the registered$8 cap. B performs no GPU allocation. Nothing here promotes a paid-call bank or runs the analysis guard.
