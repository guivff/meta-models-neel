# E125 — NOT RUN (operational): space gate failed

All400 original TEST items were checked label-blind under §236 deviations1item2 (3e2572f17) and clarification2item1 (8e7b77506). Exactexp24li/ln/tag44 rebuilds were compared directly against true block44 vectors transformed once by the pinned official whitener/ridge.1. No fitted alignment or output rescaling.

| Registered criterion | Observed median | Bound | Result |
|---|---:|---|---|
| Per-dimension rebuild/whitened-true sample SD ratio | 0.6618076649795805 | [0.5,2.0] | PASS |
| Per-dimension absolute mean difference | 0.6171949198580114 | ≤0.5 | FAIL |
| Per-item cosine | 0.03339348549260705 | ≥0.20 | FAIL |

Cosine p05=0.02528145286894912, p95=0.044503517121540374; all400 defined, all5120 SD ratios defined, zero drops. These are coordinate-admission diagnostics, not a good-reconstruction requirement or a probe-performance result. Two failed bounds make E125 operationally NOT RUN under the frozen rule. No shuffle pass, addressed/genre probe fit, test scoring, alignment, new reader call or judging occurred. Do not infer that the readouts lack evaluation information from this failed coordinate gate.

Complete true/rebuild means and sampleSDs for all5120dimensions, differences/ratios/definedflags, all400itemcosines/definedflags, original400rebuilds, pinned-whitenedtrue vectors and TOKEN_ROWS are retained byte-identical in the readonly diagnostic packet named in BINDING.json. SPACE_PROOF.json reproduces all published moment/cosine summaries exactly. All19 outer-sealed members and15 inner-sealed members were hash-verified; diagnostics were not recalculated and no label files or author analysis guard were opened. Original DEVpartialSPACE_PROOF remains historical and unmodified.

Execution: TrackQ execution attempt2, original source7d2a4df99/CODE_SEALd7f6eba4 unchanged via TrackQ pinned-local-snapshot wrapper32b12a400 (15:08:32Z), before pod creation15:10:02.212Z. Rawseal68aace44, proof5751402b, sealed15:21:48.325951Z. The separately prepared Wlens offline-v2a20e39597 was not the executed code seal and is not substituted in this chronology. Prior attempt1 failed before model construction and stays excluded/immutable. Q's reported fullpod stop729.8s/custody already booked; no new cost booking here. Never rerun/reset/align to rescue this gate. R4 independent review of this operational closeout requested.

Publication note: derivative removes two infrastructure identifiers. Exact original report remains in the previously delivered private reviewer packet; original Git blob/SHA256 bound by this supplement.
