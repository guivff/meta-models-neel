# E68 ready handoff to W-mechanism and Integrator — 2026-10-27

Authority: §185 deviations 1 and 2, ratification 7e6ea0cc. Position seal SHA256: 6b706209fb0f785eedec48d3d70a70f7dc2269fe9261797a6b8293782f9348c2.

Ready: container_after_move 84 (gap 14), holder_after_handovers 84 (gap 26), topic_twin 84 (gap 5, no minimum for control). arith_compare's 84 items are listed as INFEASIBLE, not failed reader outcomes. All ratified token indices are copied unchanged from the reviewed draft. Only the holder input appends the authorised question. 252 items, 756 item-position combinations, two readers, one greedy readout per reader/position.

W-mechanism: bind POSITION_SEAL.json and LAUNCH_REQUEST.json into the runner. Check hashes before reading inputs. INPUTS.json is label-free; LABELS.PRIVATE.json stays on CPU. Token indices are zero-based and inclusive; capture only P_far/P_mid/P_pre, readers receive activations, not item text. Oracle block 44/128 tokens; NLA block 42/512 tokens with closing-tag stop. Use the registered blind §172 judge and report probe AUROC per position. No probe fits are supplied by this position-only package; preserve the registered protocol, without fitting on test labels.

Integrator: exact local archive/input/private-label paths and hashes are in LAUNCH_REQUEST.json. Total GPU cap 2,160 seconds. Ready for your binding and launch; W-text did not push or launch. Private files in the local archive must not be transferred to a pod. No change to previous experiment banks or seals.

R-O1 now requires S(P_pre) − S(P_far) ≥0.30 on BOTH remaining state rows, for each reader, plus the unchanged topic control criterion (<0.15 change). Falsifier: <0.10 on BOTH state rows. Disclose the reduction from three state rows to two and arithmetic infeasibility. The original draft remains preserved with its historical drop flags; only POSITIONS.json is authoritative for production, retaining the topic row.

Four CPU tests pass: all sealed hashes/archive, unchanged ratified anchors, complete balanced item grid and valid indices, and request binding. The production seal is separate from the earlier audit seal. No E68 capture or readout was opened or run by W-text.
