# E96 one-item reconstructor check — I-4 / W-mechanism

**PASS for both readers.** On 28 October 2026, the exact Oracle activation reconstructor and NLA reconstruction head each reconstructed one saved, sealed greedy readout into a finite, nonzero `[1,5120]` native activation. Aggregator (b) is available for both readers. This is an operational check, not evidence of reconstruction quality or an E96 scaffold effect.

| Reader | Pinned checkpoint | Native output | Result |
|---|---|---|---|
| Oracle | `agu18dec/olens_and_ar@c95215d5d2f6250f20c305ae55c6e4d7569f92dc/ar_ptag_pooled` | block 44 | PASS; 992/992 adapter tensors live |
| NLA | `ceselder/qwen3.6-27b-nla-rl@5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f/ar_reconstructor` | block 42 | PASS; trained value head loaded |

The label-free item was `asserted_vs_hypothetical:6:0:0`, using its existing Oracle greedy text, corrected sealed 512-token NLA supplement, and matching block-44/block-42 capture vectors. Four upstream seals were fully verified. No baseline was regenerated; no samples or judgments were made. Input provenance is in `SMOKE_INPUT_PROVENANCE.json`; the input and exact executed sources are included in `smoke/`.

Oracle used official source `a32590085a6070d75f950155d3c2b3db3eec97ef` and the byte-verified pooled L44 whitener `178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a`. Both full checkpoint manifests and all head hashes were checked. NLA's loader warning about unused final norm/LM-head tensors is expected: this path uses the frozen residual backbone and trained reconstruction value head. Outputs remain raw, unwhitened native activations.

Guiv directly admitted one H200 for ≤1,800 seconds, including staging and loading. Pod `quw9yht7chipgj` ran from 2026-10-28T10:53:52.741000+00:00 to first observed EXITED 2026-10-28T11:14:53.442004+00:00: **1260.701 seconds / 0.350195 GPU-h / USD 1.852530 rate-based upper bound**, not an invoice. Both guards retained the original allocation deadline. A CPU-oversubscribed first attempt was stopped before producing any reconstruction; the unchanged code succeeded with eight CPU threads in 338.269 seconds. All attempts and staging count in custody. Outputs were retrieved and hash-verified before shutdown; the pod is terminated. Judging USD 0.

**first_output_utc: `2026-10-28T11:11:25.132304+00:00`**, from the Oracle reconstruction file mtime on the pod, preserved by the PAX archive. The original worker seal is preserved verbatim as `smoke/output/RAW_SCORE_SEAL.json`; the enriched output seal and package seal record this timestamp. The original execution source commit was `c1ba373e`, before either output. `smoke/SMOKE_SEAL.json` binds inputs, predictions, report, manifests, logs, exact sources and custody. There are no earlier completed E96 result seals requiring backfill.

Next: freeze the three aggregators in a separate commit before any sample exists. E62's original NLA greedy baseline remains sealed NOT RUN; no paired delta may be manufactured. Full E96 sampling, judging, analysis and R-4 review are pending.
