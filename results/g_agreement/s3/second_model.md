# S3: second-model feasibility (no compute; verified against the HF API on 2026-10-15)

Question: on which second model can we run the split edit (F2-2) and the majority-inversion test (X6) with ≥ 3 readers on
one GPU? Every ID below was listed or read through the HF API (`neuronpedia/jacobian-lens` @ `9fa267f8`); "not found" =
searched by name and author, nothing returned. "Layers" = layers the reader supports. The target in G1–F2 is
`Qwen/Qwen3.6-27B` (64 blocks; edit block 38, reads at 42/44).

## Readers per candidate

| Base model | J-lens (`neuronpedia/jacobian-lens`) | Oracle Lens / activation oracle | NLA (AV = verbalizer, AR = reconstructor) | SAE |
|---|---|---|---|---|
| **Qwen/Qwen3-4B** (36 blocks, d 2560) | `qwen3-4b/jlens/Salesforce-wikitext/Qwen3-4B_jacobian_lens.pt` (459 MB); also `jpp` | `neuronpedia/jacobian-lens` `qwen3-4b/oracle` (LoRA r16, 132 MB; copy of `andyx10/oracle-lens-qwen3-4b` @ `8172c302`); layers 12–34 step 2. Also `nluick/activation-oracle-multilayer` (AO, 0.5 GB) | `minnesotanlp/nla-qwen3-4b-L24-av` + `-ar` (full models, 8.1 + 5.9 GB; also `-sft` variants); `anicka/nla-qwen3-4b-universal-av` / `-ar` / `-av-grpo` (LoRA 0.1 GB, 13 depths 4–96 %) | community only: `hippotoday/sae-qwen3-4b-base`, `xzascc3944/SAEtopk_Qwen3-4B-Thinking-2507_Layer20`; no official Qwen SAE for 4B |
| Qwen/Qwen3-8B (36 blocks) | `qwen3-8b` (1.17 GB) | `nluick/activation-oracle-multilayer-qwen3-8b-*` (AO); `syvb/oracle-lens-qwen3-8b-*` listed but repo empty (only .gitattributes) | `marco-bazzani/Qwen3-8B-nla`, `asher577/nla-qwen-3-8b` (unverified quality) | `Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_{50,100}` (trained on **Base**), `adamkarvonen/qwen3-8b-saes` |
| Qwen/Qwen3.5-2B (24 blocks) | `qwen3.5-2b` (193 MB) | `qwen3.5-2b/oracle` (LoRA r16, 67 MB, GRPO step 230), layers 8–22 step 2 | none for this base. `adamjb111/nld27-*-qwen35-2b-from-nla-qwen36-27b-L42-*` are 2B students distilled from the 27B NLA, not an NLA of the 2B's own activations | `Qwen/SAE-Res-Qwen3.5-2B-Base-W32K-L0_{50,100}` (trained on Base) |
| Qwen/Qwen3.5-4B | `qwen3.5-4b` (406 MB) | not found | `Solshine/qwen3.5-4b-nla-L23-av-priordev-relabel-v2` (single community AV; no AR seen) | not found |
| Qwen/Qwen2.5-7B-Instruct (28 blocks, d 3584) | `qwen2.5-7b-it` (694 MB) | not found | `kitft/nla-qwen2.5-7b-L20-av` + `-ar` (15.2 + 10.9 GB, layer 20) | not found |
| google/gemma-3-12b-it (48 blocks, d 3840) | `gemma-3-12b-it` (1.39 GB) | not found | `kitft/nla-gemma3-12b-L32-av` + `-ar` (23.6 GB AV, layer 32) | `google/gemma-scope-2-12b-it` |
| google/gemma-3-27b-it (62 blocks) | `gemma-3-27b-it` (3.5 GB) | `annasoli/gemma-3-27b-activation-oracle` (LoRA 2.0 GB; AO, not Oracle Lens; many step checkpoints) | `kitft/nla-gemma3-27b-L41-av` (108 GB repo, full fine-tune) + `-ar` (37.6 GB), layer 41 | `google/gemma-scope-2-27b-it`, `google/gemma-scope-27b-pt-res` (2-it) |
| meta-llama/Llama-3.3-70B-Instruct | `llama3.3-70b-it` (10.6 GB) | not found as Oracle Lens (AO exists upstream; not verified here) | `kitft/Llama-3.3-70B-NLA-L53-av` + `-ar` | not verified |
| Llama-3.1-8B(-Instruct) | `llama3.1-8b`, `llama3.1-8b-it` (1.04 GB) | not found | not found | `EleutherAI/sae-llama-3.1-8b-32x` (and 64x), base model |

Notes on reliability. (i) Qwen3.6-27B (the current target) has all of: J-lens `qwen3.6-27b/jlens/.../Qwen3.6-27B_jacobian_lens_n1000.pt`,
Oracle `qwen3.6-27b/oracle` (blocks 20–60 step 4), NLA `ceselder/qwen3.6-27b-nla-rl` (block 42), SAE `Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_{50,100}`
(named Qwen3.5-27B; base-model match to Qwen3.6-27B not verified). (ii) Qwen "SAE-Res" for 2B/8B are trained on Base checkpoints, so applying them to
the post-trained model is an extra assumption. (iii) The Oracle/NLA checkpoints for Qwen3-4B were trained by third parties (Andy Xu; MinnesotaNLP; anicka),
not by the Neuronpedia/Agam–Camila pipeline of the 27B readers, so reader quality is itself unmeasured; G1's step-zero check (do readers read the key at all on natural states) must be re-run.

## Recommendation: Qwen/Qwen3-4B

It is the only candidate with **J-lens + Oracle Lens + NLA all on the same base**, and with a LoRA-only Oracle (132 MB) and either a full
(8 GB) or LoRA NLA, so the target, J-lens and three readers fit together on one 24–48 GB GPU, far below one H100.
Depth mapping from the 27B setup (64 blocks; edit 38 = 0.59, read 42 = 0.66): edit at block 21–22 (Oracle grid has 22), read at block 24
(= NLA `L24` = Oracle grid). Readers: J-lens (24), Oracle (24 and 22/26), NLA (`minnesotanlp` L24 AV; `anicka` universal AV as a second NLA).
That gives 4 readers (J-lens, Oracle, NLA×2) and an independent linear probe. Runner-up if a bigger model is wanted: Qwen2.5-7B-Instruct
(J-lens + NLA only, 2 readers, so it fails the ≥ 3 requirement); Gemma-3-27B-it has 3 readers (J-lens, AO, NLA) and a Gemma Scope 2 SAE but needs ≈ 54 GB for the target alone plus a 54 GB full-fine-tune NLA AV (swap sequentially; 1×H100 80 GB works only by reloading), so it is ~10× the cost for the same test.

## GPU-hour estimate (Qwen3-4B, 1× H100; estimates, not measurements)

Scaling from the 27B runs (F2-2 ≈ 64 states × 26 edit entries, 8 greedy tokens, then 3–4 reader passes; roughly 1–1.5 H100-h on the 27B, by parameter ratio ≈ 7×
cheaper; I did not find a per-run wall-clock in the cached ledgers locally, so the 27B figure is itself an estimate).

| Step | Estimate |
|---|---|
| Verify premises: readers load, J-lens/Oracle/NLA read natural states of the new model (G1-style step zero, 32 states × 4 readers) | 0.2 h |
| New X1/X2 item bank rendering + activation capture at blocks 22/24 (≈ 130 forward passes; probe, class-mean, J-space basis from `W_U·J`) | 0.2 h |
| F2-2 split edit (J_scaled, perp_scaled, random, 5 α) + read-backs by 4 readers | 0.4–0.6 h |
| Majority-inversion test (X6 analogue, CPU on the artefacts) | ~0 GPU |
| Margin for reruns / debugging | 0.3 h |
| **Total** | **≈ 1.1–1.4 H100-h (≈ 2–3 h on an A100 or a 24 GB card)** |

Blocking risk: the third-party Qwen3-4B readers may already fail the natural-state check (reader quality unknown); that check should run first and is 0.2 h.

## Addendum 2026-10-16 (S7 chat): NLA / Oracle for DeepSeek-V4-Flash (HF API, read only)

Searched by name (`deepseek-v4-flash`, `deepseek-v4`, `dsv4`, `easynla`, `activation-oracle`, `oracle-lens`, `olens`), by `base_model:{adapter,finetune}:`
for `deepseek-ai/DeepSeek-V4-Flash`, `-0731`, `-Base` and `DeepSeek-V4.1-Flash`, and by author (agu18dec, andyx10, nluick, annasoli, adamkarvonen,
ceselder, neuronpedia).

- **NLA: found.** `ceselder/easynla-dsv4-flash-nla-ckpts` @ `74d82f2e` (public, MIT, 65.7 GB, last modified 2026-09-07). Same author and EasyNLA recipe
  as our 27B NLA. AV and AR (critic with value head) LoRA r128 plus dense-over-MoE bypass LoRAs, on **`deepseek-ai/DeepSeek-V4-Flash-0731`**, layer 28 of 43,
  embedding-replacement injection (α 95.5). SFT warm starts (`sft/av_*`, `sft/ar_*`) and GRPO checkpoints `rl/iter_000050`…`iter_000550`. The card names
  `rl/iter_000525` as best, at 62.5% held-out FVE. Caveats from the card: the marker character is given inconsistently (U+320E vs U+33A1); serving needs
  merging the adapters into the base (vLLM cannot serve the bypass LoRAs unmerged); the example uses tensor_parallel 8.
- **Oracle Lens / activation oracle: not found.** `neuronpedia/jacobian-lens` @ `e166deb5` has oracle folders only for qwen3-4b, qwen3.5-0.8b, qwen3.5-2b and
  qwen3.6-27b. No DeepSeek hit among the 100 `activation-oracle`, 10 `oracle-lens` or 21 `olens` search results. ceselder's `*-oracle-*-v4` repos are Qwen3-8B/14B.
- **J-lens (for the record):** `neuronpedia/jacobian-lens` `deepseek-v4-flash/jlens/NeelNanda-pile-10k` (fit on **`deepseek-ai/DeepSeek-V4-Flash`**, target
  layer 41, only 25 prompts) and `jpp/Salesforce-wikitext` (target 42). Third-party `xiangchensong/jacobian-lens-deepseek-v4-flash-0731` is fit on -0731.
- **Checkpoint mismatch:** the NLA is on `-0731`, while the Neuronpedia J-lens is on the original `-Flash`. A matched pair is the NLA plus xiangchensong's
  -0731 J-lens, which gives 2 readers (J-lens, NLA) plus a probe. That is below the ≥ 3-reader requirement without an Oracle, so the Qwen3-4B
  recommendation above stands. DeepSeek-V4-Flash (~284B MoE) also needs multi-GPU in any case.
