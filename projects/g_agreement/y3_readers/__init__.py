"""Phase Y3 (BRIEF_Y.md §Y3): new reader families in the same native-LO harness — skip-lens arms A and D
(LoRA on the target, NLA-style injection), the Qwen-Scope layer-42 TopK SAE (transfer test + sparse latent
probe) and the R-lens (if its checkpoint matches the J-lens readout).

  collect.py   GPU phase A (target + adapters) and CPU tensors: X1 / X2 / X3 native LO rows per reader,
               SAE FVE vs shuffled-decoder null, SAE probe rows
  sae.py       SAE loading, TopK encode/decode, FVE, null, sparse LOO diff-in-means probes
  analyze.py   E14 entry gate, E15 (X2 follow, X3 E8 with symbol-bias correction), SAE table, blindness map columns
"""
