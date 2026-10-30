"""Phase Z1 (BRIEF_Z.md §Z1): intervention-response benchmark on the frozen X2 artefacts — CPU only, zero forward passes.

  analyze.py   per planted entry: Δs_r, f_r (fraction of the reader's own natural separation), Δ_model, flip;
               E1 flip AUROC (8 pair-family folds), E2 magnitude correlations with dose partialled out,
               E3 held-out family / site, E4 paired reader differences (threshold rule + TOST), E5 permutation null.
"""
