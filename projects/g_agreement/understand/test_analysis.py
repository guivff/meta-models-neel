"""Offline checks of the E3/E4 statistical estimands and leakage boundaries."""
import json
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from projects.g_agreement.understand import analysis as A


def paired_data():
    rng = np.random.default_rng(12)
    groups = np.repeat(np.arange(12), 14)
    y = np.tile([0, 1], 84)
    x = rng.normal(size=(168, 5)).astype(np.float32)
    x[:, 0] += 5*(2*y-1)
    # Distinct group offset allows verification of training-only scaling.
    x[:, 1] += groups*30
    return x, y, groups


def test_grouped_cv_leakage_and_training_only_standardisation(monkeypatch):
    from mats import probes
    x, y, groups = paired_data()
    calls = []
    fit = probes.fit_logreg

    def record_fit(train_x, train_y, **kwargs):
        model = fit(train_x, train_y, **kwargs)
        np.testing.assert_allclose(model.mu.numpy(), train_x.numpy().mean(axis=0), rtol=1e-6, atol=1e-6)
        calls.append(train_x.numpy().copy())
        return model

    monkeypatch.setattr(probes, "fit_logreg", record_fit)
    result = A.grouped_cv_probe(x, y, groups)
    assert result["n"] == 168 and result["auroc"] > .99
    assert result["standardisation"] == "training_fold_only"
    assert result["positive_label"] == "value_A"
    assert not result["orientation_flipped"]
    seen = []
    for train_x, fold in zip(calls, result["folds"]):
        tr, te = fold["train_indices"], fold["test_indices"]
        assert set(groups[tr]).isdisjoint(groups[te])
        np.testing.assert_array_equal(train_x, x[tr])
        assert set(tr).isdisjoint(te)
        seen.extend(te)
    assert sorted(seen) == list(range(168))
    for group in np.unique(groups):
        assert len(set(np.array(result["fold_assignment"])[groups == group])) == 1
    json.dumps(result, allow_nan=False)


def test_deterministic_folds_and_invalid_grouping():
    x, y, groups = paired_data()
    a = A.grouped_cv_probe(x, y, groups)
    b = A.grouped_cv_probe(x, y, groups)
    assert a == b
    with pytest.raises(ValueError, match="distinct template"):
        A.grouped_cv_probe(x, y, np.zeros(len(y)))
    with pytest.raises(ValueError, match="one-class"):
        A.grouped_cv_probe(x[:10], np.repeat([0,1],5), np.arange(10), n_splits=10)


def test_no_posthoc_auroc_flips(monkeypatch):
    from mats import probes
    x, y, groups = paired_data()
    # The fake fitted rule is deliberately wrong on every held-out item.
    monkeypatch.setattr(probes, "fit_logreg", lambda *args, **kwargs:
                        SimpleNamespace(decision=lambda z: -z[:,0]))
    result = A.grouped_cv_probe(x, y, groups)
    assert result["auroc"] == 0.0
    assert result["orientation_flipped"] is False


def test_e3_full_grid_including_nonfinite_cell_and_w1_comparator():
    x, y, groups = paired_data()
    h = np.broadcast_to(x[:,None,None,:],(168,2,2,5)).copy()
    h[0,1,1,0] = np.nan
    rows = A.analyze_e3_cell(h,y,groups,reader="olens",row="example",row_class="state-like",
                            layers=[0,1],asked_auroc=.45)
    assert len(rows) == 4
    assert [r["status"] for r in rows].count("COMPLETE") == 3
    assert rows[-1]["status"] == "NOT_EVALUABLE"
    assert rows[-1]["auroc"] is None
    assert all(r["w1_asked_auroc"] == .45 for r in rows)
    assert all(r["probe_population"] == "W1 dev+test" for r in rows)
    with pytest.raises(ValueError,match="168"):
        A.analyze_e3_cell(h[:167],y[:167],groups[:167],reader="olens",row="x",row_class="state-like")


def test_gradient_alignment_analytic_and_random_baseline():
    g = np.zeros((20,100)); g[:,0] = np.arange(1,21)
    u = np.eye(100)[0]
    result = A.summarize_gradients(g,u,n_boot=40,seed=3)
    assert result["mean_abs_cos"] == 1
    assert result["mean_abs_cos_ci95"] == [1,1]
    # Isotropic expectation is approximately sqrt(2/(pi*d)).
    assert .05 < result["random_mean_abs_cos"] < .11
    assert result["alignment_minus_random"] > .8
    assert result["zero_gradient_n"] == 0
    assert result == A.summarize_gradients(g,u,n_boot=40,seed=3)
    orthogonal = A.summarize_gradients(g,np.eye(100)[1],n_boot=0)
    assert orthogonal["mean_abs_cos"] == 0
    json.dumps(result,allow_nan=False)


def test_zero_gradient_reporting_and_shape_failures():
    result = A.summarize_gradients(np.zeros((3,5)),np.ones(5),n_boot=10)
    assert result["zero_gradient_n"] == 3
    assert result["mean_abs_cos"] == result["random_mean_abs_cos"] == 0
    assert result["mean_abs_cos_nonzero"] is None
    with pytest.raises(ValueError,match="nonzero"):
        A.summarize_gradients(np.ones((3,5)),np.zeros(5))
    with pytest.raises(ValueError,match="finite"):
        A.summarize_gradients(np.full((3,5),np.nan),np.ones(5))


def test_uncentered_receptive_subspace_and_rank_limiting():
    # A constant gradient component must remain: centering would erase e0.
    g = np.zeros((7,6));g[:,0] = 2;g[:,1] = np.arange(-3,4)
    result = A.receptive_subspace(g,{"constant":np.eye(6)[0],"varying":np.eye(6)[1],"outside":np.eye(6)[2]})
    assert result["centered"] is False
    assert result["gradients_normalized"] is False
    assert result["numerical_rank"] == 2
    assert len(result["rows"]) == 9
    for row in result["rows"]:
        assert row["k_effective"] == 2 and row["rank_limited"]
        assert row["isotropic_expected_fraction"] == pytest.approx(2/6)
        assert row["fraction_inside"] == pytest.approx(0 if row["row"] == "outside" else 1)
    json.dumps(result,allow_nan=False)


def test_receptive_svd_uses_raw_gradient_magnitudes_and_no_nullspace():
    g = np.zeros((4,5));g[0,0] = 100;g[1:,1] = 1
    result = A.receptive_subspace(g,{"large":np.eye(5)[0],"many_small":np.eye(5)[1]},ks=(1,2))
    rows = {(r["row"],r["k_requested"]):r for r in result["rows"]}
    assert rows["large",1]["fraction_inside"] == 1
    assert rows["many_small",1]["fraction_inside"] == 0
    zero = A.receptive_subspace(np.zeros((4,5)),{"arbitrary":np.ones(5)})
    assert zero["numerical_rank"] == 0
    assert all(r["k_effective"] == r["fraction_inside"] == 0 for r in zero["rows"])


def test_plot_reports_failed_cells_and_frozen_class_curves(tmp_path):
    cells=[]
    for reader in ["olens","nla"]:
        for row,cls in [("structure","state-like"),("meaning","semantic")]:
            for layer in [0,1]:
                for pos in ["injection","preanswer"]:
                    cells.append(dict(reader=reader,row=row,**{"class":cls},layer=layer,position=pos,
                                      auroc=None if layer==1 and row=="structure" else .7,
                                      w1_asked_auroc=.45))
    paths=A.plot_e3(cells,tmp_path)
    assert len(paths)==8
    for path in paths:
        assert __import__("pathlib").Path(path).stat().st_size > 1000


def test_receptive_basis_saved_without_arbitrary_rank_completion(tmp_path):
    path=tmp_path/"basis.npz"
    g=np.zeros((5,9)); g[:,2]=np.arange(5)
    result=A.receptive_subspace(g,{"row":np.eye(9)[2]},basis_out=path)
    with np.load(path,allow_pickle=False) as saved:
        assert saved["right_singular_vectors"].shape == (1,9)
        assert abs(saved["right_singular_vectors"][0,2]) == 1
    assert result["basis_file"] == str(path)
    with pytest.raises(FileExistsError):
        A.receptive_subspace(g,{"row":np.eye(9)[2]},basis_out=path)
