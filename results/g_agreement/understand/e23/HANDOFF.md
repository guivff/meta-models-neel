# E23 build and launch handoff

E21 was analysed once in `189f6efb`; its report and seal are unchanged. E23 Step 0 was posted in `a76c1cad`: following1–32 tokens target the single preceding activation. F16 is in-contract; P32/Pfull are off-contract.

The §117 09:10 correction `e347b86a` was read in full. The six-file source gate now exits0. `SURAJ_FILES.e347b86a.json` uses the corrected full exp07 hash. The old blocked receipt is preserved in `SURAJ_FILES.json`, the prior handoff in `HANDOFF.blocked.4e084086.md`, and commit `4e084086` preserves the complete original seal state.

The input packet contains840 O items (420dev/420test) and600 S items (120mine/480select). All600 S items receive fresh own-hook captures at40/42/44. Every item/layer must pass cosine>=.999 against the stored parity-only tensors. O uses its existing sealed42/44 activations; no O recapture. The exact840 O F16 continuations are reused from sealed E1b; only600 S F16 continuations are generated, greedy16 with the E1b code and no heterogeneous-prefix padding.

All1440 continuations are sealed before the first AR forward, including neutral warm-ups. Unique F16/P32/Pfull are reconstructed at44(primary) and40(secondary):8640 outputs. Mis and secondary Swap reference the exact frozen donor F16 output instead of recomputing an identical text. Donors are seeded20261025 within row/set; Mis ignores value and permits self draws; Swap conditions only on the opposite value. The pool contains both frozen splits. M2 controls use each recipient's F16 fold model without refitting, even when a donor is in that model's training pool. That registered design is disclosed; no extra donor restriction was added.

M1 remains raw, with frozen W1 dev44 directions for O and W1-recipe directions fit on S mine40 true44 captures for primary S. W1->S transfer is secondary. M2 uses O84test grouped folds and S all200 grouped folds; T uses O matching folds and S mine->select. T is fitted separately on each span arm. Bootstrap is2000/seed20261025, shared-item paired within set and independent across O/S; the S160-versus200 denominators are retained. No sign flips or whitening. E23b has976 item-cells: table column O/S x W1mean2/Surajfixedpair x42/44. Factor contrasts retain signs; rule6 ranks their absolute magnitude. All six decision rules, validity flags and secondary Swap/transfer measures are implemented in the once-only CPU analyser.

## Timing and models

One H200 with>=120GiB usable GPU memory is required for simultaneous residency of two backbones. The AR loads once and the target+Oracle backbone loads once during setup, in the same process as their later warm-up and science. Setup allowance1500s. No NLA and no reload/offload fallback.

There are12 timing paths and1476 production units: capture75, generation197, four asked paths31each, six AR paths180each. Six target paths each receive one unscored dev warm-up in setup and3 discarded timed units after the science clock starts. Prefix-only admission checks capture+generation against the5400s reservation; all AR paths remain UNKNOWN, never zero. Only capture/generation may produce retained output at this stage. This staging is necessary to obey the full-F16-before-any-AR requirement.

After capture parity and continuation sealing, each AR path receives one unscored neutral warm-up and3 timed units. These late warm-ups count as science. Timing-only text covers each path's production length; the F16 timing bound is64 re-tokenized tokens and is checked after sealing. An exceeded bound stops the run without truncation or a substitute forecast.

The full warmed forecast is then sealed: F = elapsed science (including prefix production and all pilots/warm-ups since first science) + sum of remaining units x each path's median3 timing. Cap=min(1.5F+360,5400,reserved), measured from the original first science. Admission requires elapsed+remaining+180s retrieval<=cap. No clock reset, unmeasured-zero estimate, automatic retry or owner GPU work. NO_FIT/INCOMPLETE retains a sealed partial tree.

The measured F is pending integrator execution; it is not fabricated from CPU tests. The launch request and source/input archive pins are supplied separately after validation.

## Post-pull

Run the registered E23 CPU analyser once, only after a COMPLETE collection, valid source/input/continuation/forecast seals and all-item parity. Supply the original bound assignment. The analyser verifies the assignment's source files and uses an exclusive once guard before any fit or metric. Labels remain in the private cache and must not be staged on the pod. See POST_PULL.json for exact commands.

## Git transport

The requested push of189f6efb and4e084086 was attempted with local git but failed: shell DNS cannot resolve github.com. Both commits remain on r/blindspot-mech; the remote branch was independently observed at e420b3bf. The correction was fetched from the local mirror at exact e347b86a and its brief checked against GitHub blob4909ca948ea7e5f00205f38fb2c7c8d11ce86b4d. The owner branch was pulled/rebased from its matching local-mirror upstream without rewriting the requested commits. Integrator must push the owner branch; no GitHub API replacement commits were created.

## Ready request

`LAUNCH_REQUEST.json` is ready for integrator assignment. Executable source `cd402e2cfcaf5d2b9885fa0baa47b14da621268f`; request SHA256 `ef8726a657201c33f95c27a60f335a24e0a38d33929a702b5189368dbd97804d`. Source archive SHA256 `1de572c89c4a94143ae366d319bc8b794e0681101a5cd582c1b59e4ccb7cf24b`; input archive SHA256 `7c36bdf50262434f4fff3993297e257bf6c641f29ebc644851c5faf63c170fc3`. All169 source pins match the committed source and isolated tested files;45 CPU tests and both CLI imports pass. Exact local archive paths are in the request. Stage only the public input archive. Expected sealed output: `/workspace/e23/out/E23_NEW_RUN/SCORE_SEAL.json`; continuations: `/workspace/e23/out/E23_NEW_RUN/continuations/SCORE_SEAL.json`. These output seals do not exist yet.
