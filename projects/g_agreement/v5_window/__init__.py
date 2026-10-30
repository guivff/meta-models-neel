"""V5 (PREREG_WV.md, BRIEF_WV §V5): behaviour-trained window reader on cached activations (Mac, MPS/CPU).

models.py  the four readers (last-token linear, mean-pooled linear, attention-pooled linear, attention-pooled MLP), the
           standardiser, the torch training loop with early stopping and the inner-CV fit (L2 strength from a fixed grid).
folds.py   outer folds: pairs -> 8 pair-family folds (Z1 recipe), error items -> 8 folds of whole (k, start) groups.
data.py    loaders for the Y1 error captures (last-12-position windows), the X2 full captures (full-prompt windows) and the
           X2 last-token read-back vectors with flip labels.
run.py     the experiment: fits, held-out metrics with bootstraps, v5.csv / v5.md / fig_v5.png, saved weights.
"""
