"""V5 (PREREG_WV.md §V5) tests, CPU only, synthetic windows: attention-pooling shapes and masking, a planted-position signal that the
attention-pooled reader (c) recovers and the last-token probe (a) cannot, fold assignment by pair family and by error group, the
dose-only out-of-fold reference, and the pooled (a)/(b) training views. Nothing under results/, cache/ or dataset/ is touched.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_v5.py -q``
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")

from projects.g_agreement.v5_window import data as D  # noqa: E402
from projects.g_agreement.v5_window import folds as F  # noqa: E402
from projects.g_agreement.v5_window import models as M  # noqa: E402
from projects.g_agreement.v5_window import run as R  # noqa: E402

CPU = torch.device("cpu")


def planted_windows(n: int = 240, T: int = 6, d: int = 16, signal_pos: int = 2, seed: int = 0, strength: float = 3.0) -> D.Windows:
    """Binary label written into ONE window position (not the last token). The other positions carry label-independent noise of
    the same magnitude along the same direction (so the mean pool is diluted) and every position has a fixed tag vector (so a
    query can find the planted position, as real activations carry positional information)."""
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    x = rng.standard_normal((n, T, d)).astype(np.float32)
    direction = rng.standard_normal(d).astype(np.float32)
    direction /= np.linalg.norm(direction)
    tags = 2.0 * rng.standard_normal((T, d)).astype(np.float32)
    x += tags[None]
    along = strength * rng.standard_normal((n, T)).astype(np.float32)  # label-independent noise along the signal direction
    along[:, signal_pos] = strength * (2 * y - 1)
    x += along[:, :, None] * direction[None, None, :]
    mask = np.ones((n, T), bool)
    return D.Windows(torch.tensor(x), torch.tensor(mask), y, [f"it{i:03d}" for i in range(n)], ["neg", "pos"],
                     {"pair_id": [f"p{i // 2:03d}" for i in range(n)]})


# ----------------------------------------------------------------------------------------------- shapes / masking
def test_attention_pool_shapes_and_mask():
    n, T, d, K = 5, 7, 11, 3
    x = torch.randn(n, T, d)
    mask = torch.ones(n, T, dtype=torch.bool)
    mask[0, 4:] = False  # row 0 has 4 valid positions
    mask[1, 2:] = False
    for kind in M.MODELS:
        m = M.Reader(kind, d, K)
        m.set_standardiser(x, mask)
        out = m(x, mask)
        assert out.shape == (n, K), kind
        assert torch.isfinite(out).all(), kind
    m = M.Reader("attn_linear", d, K)
    m.set_standardiser(x, mask)
    with torch.no_grad():
        m.q.normal_()
    a = m.attention(x, mask)
    assert a.shape == (n, T)
    assert torch.allclose(a.sum(1), torch.ones(n), atol=1e-5)
    a = a.detach()
    assert float(a[0, 4:].abs().max()) == 0.0 and float(a[1, 2:].abs().max()) == 0.0, "masked positions must get zero attention"
    # zero query == uniform attention over the valid positions == masked mean
    m0 = M.Reader("attn_linear", d, K)
    m0.set_standardiser(x, mask)
    a0 = m0.attention(x, mask)
    assert torch.allclose(a0[0, :4], torch.full((4,), 0.25), atol=1e-6)
    assert torch.equal(M.last_index(mask), torch.tensor([3, 1, 6, 6, 6]))


def test_pooled_views_match_window_models():
    """(a) on the pooled last token and (b) on the pooled mean with the all-position standardiser equal the window forward."""
    w = planted_windows(n=12, T=5, d=7)
    w.mask[0, 3:] = False
    for kind in ("last_linear", "mean_linear"):
        xp, mp, stats = R.pooled_view(w, kind)
        assert xp.shape == (12, 1, 7) and mp.all()
        m = M.Reader(kind, 7, 2)
        m.set_standardiser(w.x, w.mask)
        if stats is not None:
            assert torch.allclose(m.mu, stats[0]) and torch.allclose(m.sd, stats[1])
        with torch.no_grad():
            m.head.weight.normal_()
        full = m(w.x, w.mask)
        pooled = m(xp, mp)
        assert torch.allclose(full, pooled, atol=1e-4), kind


# ----------------------------------------------------------------------------------------------- planted signal
def test_attention_reader_recovers_planted_position_and_last_token_cannot():
    w = planted_windows()
    n = len(w)
    tr, te = np.arange(0, 160), np.arange(160, n)
    y = torch.tensor(w.y)
    res = {}
    for kind in ("last_linear", "attn_linear"):
        fit = M.fit_inner_cv(kind, w.x[tr], w.mask[tr], y[tr], 2, [(np.arange(0, 120), np.arange(120, 160))], (1e-3, 1e-2), max_epochs=300, lr=1e-2, patience=30)
        pred = M.predict_logits(fit.model, w.x[te], w.mask[te]).argmax(1)
        res[kind] = float((pred == w.y[te]).mean())
        if kind == "attn_linear":
            a = M.attention_weights(fit.model, w.x[te], w.mask[te])
            assert int(a.mean(0).argmax()) == 2, f"attention should concentrate on the planted position, got {a.mean(0)}"
    assert res["attn_linear"] >= 0.9, res
    assert res["last_linear"] <= 0.65, res


def test_mlp_on_single_vector_is_plain_mlp():
    """T = 1 window: attention is the identity, so (d) reduces to an MLP on that vector (the T2 last-token case)."""
    x = torch.randn(9, 1, 6)
    mask = torch.ones(9, 1, dtype=torch.bool)
    m = M.Reader("attn_mlp", 6, 2)
    m.set_standardiser(x, mask)
    with torch.no_grad():
        m.q.normal_()
    z = (x[:, 0] - m.mu) / m.sd
    assert torch.allclose(m(x, mask), m.head(z), atol=1e-5)


# ----------------------------------------------------------------------------------------------- folds
def test_pair_family_folds_keep_pairs_together_and_stratify():
    pairs = [f"xown-{i:02d}" for i in range(32)] + [f"xmap-{i:02d}" for i in range(32)]
    fam = {p: ("ownership" if p.startswith("xown") else "mapping") for p in pairs}
    fold = F.assign_folds(pairs, fam, 8, 0)
    assert set(fold.values()) == set(range(8))
    for f in range(8):
        members = [p for p in pairs if fold[p] == f]
        assert sum(fam[p] == "ownership" for p in members) == 4 and sum(fam[p] == "mapping" for p in members) == 4
    rows = [p for p in pairs for _ in ("A", "B")]
    rf = np.array([fold[p] for p in rows])
    for p in pairs:
        assert len(set(rf[[i for i, r in enumerate(rows) if r == p]].tolist())) == 1
    assert F.assign_folds(pairs, fam, 8, 0) == fold  # deterministic
    assert F.assign_folds(pairs, fam, 8, 1) != fold


def test_error_group_folds_hold_out_whole_groups():
    items = {}
    k = 0
    for hops in (3, 4):
        for start in "ABCDEFGH":
            for j in range(5):
                items[f"xpz-{k:04d}"] = {"source": {"k": hops, "start": start}, "template_id": "pz-t1"}
                k += 1
    ids = sorted(items)
    groups = F.error_groups(items, ids)
    assert len(set(groups.values())) == 16
    fold = F.group_folds(ids, groups, {g: g.split("|")[0] for g in groups.values()}, 8, 0)
    assert fold.shape == (len(ids),)
    for g in set(groups.values()):
        assert len(set(fold[[i for i, iid in enumerate(ids) if groups[iid] == g]].tolist())) == 1, g
    for f in range(8):
        gs = {groups[ids[i]] for i in np.where(fold == f)[0]}
        assert len(gs) == 2 and {g.split("|")[0] for g in gs} == {"k3", "k4"}
    # inner splits never split a group either
    tr = np.where(fold != 0)[0]
    unit = [groups[i] for i in ids]
    for itr, iva in F.inner_splits(tr, unit, 2, 7):
        assert not ({unit[tr[i]] for i in itr} & {unit[tr[i]] for i in iva})


def test_template_folds_would_be_degenerate_and_data_declares_it():
    """A template_id fold on the real selection is one fold (documented deviation): assert the real file has one template, when present."""
    if not D.Y1_SELECTED.exists():
        pytest.skip("no local Y1 selection")
    items = D.load_error_items()
    assert len({it.get("template_id") for it in items.values()}) == 1


# ----------------------------------------------------------------------------------------------- statistics helpers
def test_dose_only_oof_uses_training_cells_only():
    cells = np.array(["c1"] * 4 + ["c2"] * 4)
    y = np.array([1, 1, 0, 0, 1, 1, 1, 0])
    fold = np.array([0, 1, 0, 1, 0, 1, 0, 1])
    p = R.dose_only_oof(cells, y, fold)
    # fold 0 test rows (idx 0,2,4,6) use fold-1 training rows: c1 -> rows 1,3 -> rate 0.5; c2 -> rows 5,7 -> 0.5
    assert np.allclose(p[[0, 2, 4, 6]], 0.5)
    # fold 1 test rows use fold-0 training rows: c1 -> rows 0,2 -> 0.5; c2 -> rows 4,6 -> 1.0
    assert np.allclose(p[[1, 3]], 0.5) and np.allclose(p[[5, 7]], 1.0)


def test_pair_bootstrap_auroc_and_paired_diff():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 200)
    good = y + 0.3 * rng.standard_normal(200)
    pairs = [f"p{i // 4}" for i in range(200)]
    st = R.pair_boot_auroc(good, rng.standard_normal(200), y, pairs, 200, 0)
    assert st["auroc"] > 0.95 and st["delta_lo"] > 0 and st["n_pairs"] == 50
    d, lo, hi = R.boot_paired_diff([1, 1, 1, 0], [1, 0, 0, 0], 500, 0)
    assert abs(d - 0.5) < 1e-9 and lo <= d <= hi
    assert abs(R.auroc(np.array([0.1, 0.9]), np.array([0, 1])) - 1.0) < 1e-12


def test_flip_score_points_toward_the_edited_candidate():
    from projects.g_agreement.v5_window import t2_via_t1 as T

    classes = ["second_mentioned", "first_mentioned"]
    logits = np.array([[0.0, 2.0], [0.0, 2.0], [3.0, 1.0]])  # rows 0-1 favour 'first', row 2 favours 'second'
    f = T.flip_scores(logits, classes, other_is_first=[True, False, True])
    assert np.allclose(f, [2.0, -2.0, -2.0])  # positive only when the favoured class is the edited-in candidate
