# Excluded from the vendored copy

This directory is `git archive` of [Jarus77/mats-nla-workspace@10d495f12fd63c434e8d9752f4a223ea59fa9d95](https://github.com/Jarus77/mats-nla-workspace/tree/10d495f12fd63c434e8d9752f4a223ea59fa9d95): tracked files only, so nothing untracked in Suraj's checkout (including the unpublished exp 19 item bank) can be here. The 11 tracked files below were then removed under this repository's rules (no file above 5,000,000 bytes; no raw activations, weights or tensors). Together they are 141,034,492 bytes. Nothing was removed for a secret or an IP/SSH endpoint: the scan found none (see `docs/provenance/mats-nla-workspace.md`).

Every file stays available at the same path in Suraj's public repository at the pinned commit:

```sh
git clone https://github.com/Jarus77/mats-nla-workspace && git -C mats-nla-workspace checkout 10d495f12fd63c434e8d9752f4a223ea59fa9d95
# or one file: https://github.com/Jarus77/mats-nla-workspace/raw/10d495f12fd63c434e8d9752f4a223ea59fa9d95/<path>
```

The `.pt` inputs are also the files `experiments/handoff_inputs/upload_to_modal.sh` puts on the Modal results volume (`rfm-results`, same relative layout) that exps 15 and 16 read; that volume is in Suraj's Modal workspace, not public.

| Path (relative to this directory) | Bytes | Reason |
|---|---:|---|
| `experiments/06_resolving_decomposition/data/qwen_gen.json` | 8,646,943 | over 5,000,000 bytes |
| `experiments/27_random_2000/results/items_base.json` | 6,428,491 | over 5,000,000 bytes |
| `experiments/handoff_inputs/03_pipeline_smoke/jspace_basis_L42.pt` | 41,961,453 | PyTorch tensor (activations / reconstructions / basis); weights-and-activations rule; also over 5,000,000 bytes |
| `experiments/handoff_inputs/07_template_mining/acts_bk_listidx.pt` | 12,293,737 | PyTorch tensor (activations / reconstructions / basis); weights-and-activations rule; also over 5,000,000 bytes |
| `experiments/handoff_inputs/07_template_mining/acts_ij2_lang.pt` | 12,294,167 | PyTorch tensor (activations / reconstructions / basis); weights-and-activations rule; also over 5,000,000 bytes |
| `experiments/handoff_inputs/13_new_rows/acts_tb_paren.pt` | 12,294,679 | PyTorch tensor (activations / reconstructions / basis); weights-and-activations rule; also over 5,000,000 bytes |
| `experiments/handoff_inputs/13_new_rows/acts_tb_tablecol.pt` | 12,293,490 | PyTorch tensor (activations / reconstructions / basis); weights-and-activations rule; also over 5,000,000 bytes |
| `experiments/handoff_inputs/14_ar_blindspot/recon14_nla_bk_listidx.pt` | 8,694,621 | PyTorch tensor (activations / reconstructions / basis); weights-and-activations rule; also over 5,000,000 bytes |
| `experiments/handoff_inputs/14_ar_blindspot/recon14_nla_ij2_lang.pt` | 8,725,197 | PyTorch tensor (activations / reconstructions / basis); weights-and-activations rule; also over 5,000,000 bytes |
| `experiments/handoff_inputs/14_ar_blindspot/recon14_nla_tb_paren.pt` | 8,712,461 | PyTorch tensor (activations / reconstructions / basis); weights-and-activations rule; also over 5,000,000 bytes |
| `experiments/handoff_inputs/14_ar_blindspot/recon14_nla_tb_tablecol.pt` | 8,689,253 | PyTorch tensor (activations / reconstructions / basis); weights-and-activations rule; also over 5,000,000 bytes |

Kept on purpose: `experiments/10_main/power/pilot_inputs.npz` (107,802 bytes) and `pilot_inputs_nla.npz` (87,018 bytes) hold small float tables of pilot scores and null draws (60 x 4-5 arrays), not activations.

Code that loads the excluded files will not run from this copy alone; it is read-only evidence here, as is the rest of `external/`.
