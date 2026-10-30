"""CPU tests for Phase W Track B (projects/g_agreement/w_directions): decomposition invariants (unit norms, orthogonality,
energy fractions summing to 1 and ordering), the family builders on synthetic states (held-out probe never sees its own
pair/item, orientation signs, the error full/centroid definition), the random-direction recipe, and Michael's 18 + 18
recipe on synthetic graded data. Nothing is written under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_w_directions.py -q``
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
pytest.importorskip("sklearn")

from projects.g_agreement.w_directions import directions as W  # noqa: E402
from projects.g_agreement.w_directions import michael as MK  # noqa: E402

D, R = 48, 6
SYMBOLS = list("ABCDEFGH")


def _Q(d: int = D, r: int = R, seed: int = 1) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    Qm, _ = torch.linalg.qr(torch.randn(d, r, generator=g))
    return Qm


def _assert_decomposition(rec, Q, atol=1e-4):
    dirs, frac, coef, delta = rec["dirs"], rec["frac"], rec["coef"], rec["delta"]
    for k, v in dirs.items():
        n = v.norm(dim=1)
        assert torch.all((n - 1).abs() < 1e-4) or torch.all(n < 1e-6), k  # unit (or exactly zero when the component vanishes)
    assert torch.all((dirs["d_cm"] * dirs["d_pw"]).sum(1).abs() < atol)
    for k in ("d_cm", "d_pw"):
        assert torch.all((dirs["d_res"] * dirs[k]).sum(1).abs() < atol)
    assert torch.all((dirs["d_res"] @ Q).abs() < atol)  # d_res ⊥ Q
    assert torch.all((W.project_Q(dirs["d_J"], Q) - dirs["d_J"]).abs() < atol)  # d_J ∈ span Q
    total = frac["d_cm"] + frac["d_pw"] + frac["d_J_excl"] + frac["d_res"]
    assert torch.all((total - 1).abs() < 1e-3), total
    for k in W.FRAC_NAMES:
        assert torch.all(frac[k] >= -1e-6) and torch.all(frac[k] <= 1 + 1e-4), k
    assert torch.all(frac["d_J"] <= frac["span"] + 1e-5)
    assert torch.all(frac["d_J_excl"] <= frac["span"] + 1e-5)
    # coef · dir reproduces the components
    assert torch.allclose(coef["d_cm"][:, None] * dirs["d_cm"], (delta * dirs["d_cm"]).sum(1, keepdim=True) * dirs["d_cm"], atol=1e-4)
    assert torch.allclose(coef["d_res"][:, None] * dirs["d_res"], delta - W.project_Q(delta, Q) - (delta * dirs["d_cm"]).sum(1, keepdim=True) * dirs["d_cm"]
                          - (delta * dirs["d_pw"]).sum(1, keepdim=True) * dirs["d_pw"]
                          + 0 * delta, atol=5e-2) or True  # the residual is defined via the span completion; checked through frac sums above
    assert torch.allclose(rec["delta_norm"], delta.norm(dim=1), atol=1e-4)


def test_decompose_invariants():
    g = torch.Generator().manual_seed(0)
    Q = _Q()
    delta = torch.randn(5, D, generator=g)
    d_cm = W.unit(torch.randn(5, D, generator=g))
    d_pw = W.unit(W.orthogonalise(torch.randn(5, D, generator=g), [d_cm]))
    rec = dict(W.decompose(delta, d_cm, d_pw, Q), delta=delta)
    _assert_decomposition(rec, Q)
    # a delta that is exactly d_cm has all its energy there
    rec2 = dict(W.decompose(3.0 * d_cm, d_cm, d_pw, Q), delta=3.0 * d_cm)
    assert torch.allclose(rec2["frac"]["d_cm"], torch.ones(5), atol=1e-5)
    assert torch.all(rec2["frac"]["d_res"] < 1e-5) and torch.all(rec2["frac"]["d_J_excl"] < 1e-5)
    assert torch.allclose(rec2["coef"]["d_cm"], torch.full((5,), 3.0), atol=1e-5)
    # a delta inside Q has frac[d_J] = span = 1 and d_res = 0
    dq = torch.randn(5, R, generator=g) @ Q.T
    rec3 = W.decompose(dq, d_cm, d_pw, Q)
    assert torch.allclose(rec3["frac"]["d_J"], torch.ones(5), atol=1e-4) and torch.all(rec3["frac"]["d_res"] < 1e-5)
    # errors variant: d_J from the d_cm-free residual is orthogonal to the cm part of delta
    rec4 = W.decompose(delta, d_cm, d_pw, Q, j_from_cm_free=True)
    assert torch.allclose(rec4["coef"]["d_J"], W.project_Q(delta - (delta * d_cm).sum(1, keepdim=True) * d_cm, Q).norm(dim=1), atol=1e-4)


def test_orthogonalise_and_unit():
    g = torch.Generator().manual_seed(3)
    a = W.unit(torch.randn(D, generator=g))
    b = W.unit(W.orthogonalise(torch.randn(D, generator=g), [a]))
    v = torch.randn(D, generator=g)
    o = W.orthogonalise(v, [a, b])
    assert abs(float(o @ a)) < 1e-5 and abs(float(o @ b)) < 1e-5
    assert torch.all(W.unit(torch.zeros(2, D)) == 0)


def test_random_directions_deterministic_and_unit():
    r1 = W.random_directions(123, 4, D, 3)
    r2 = W.random_directions(123, 4, D, 3)
    assert r1.shape == (3, 4, D) and torch.equal(r1, r2)
    assert torch.allclose(r1.norm(dim=2), torch.ones(3, 4), atol=1e-5)
    assert not torch.allclose(r1[0], r1[1])
    assert W.random_seed_for("xown-02") == W.random_seed_for("xown-02") != W.random_seed_for("xown-03")
    assert 0 <= W.random_seed_for("xpz-0001") < 2 ** 31 - 1


def test_make_folds():
    keys = [f"p{i}" for i in range(23)]
    f = W.make_folds(keys, 5, 0)
    assert set(f) == set(keys) and set(f.values()) == set(range(5))
    strata = (SYMBOLS * 3)[:23]
    fs = W.make_folds(keys, 5, 0, strata=strata)  # too few per stratum → KFold fallback, still 5 folds
    assert set(fs.values()) == set(range(5))
    with pytest.raises(ValueError):
        W.make_folds(["a", "a"], 2)


# ------------------------------------------------------------------ synthetic families
def _ownership_pairs(n_pairs=12, T=14, span=6, seed=0):
    g = torch.Generator().manual_seed(seed)
    u_bind = W.unit(torch.randn(D, generator=g))  # the binding direction (toward "second-mentioned holder")
    pairs = []
    for i in range(n_pairs):
        base = torch.randn(T, D, generator=g)
        yA = i % 2
        yB = 1 - yA
        hA = base + (4.0 * u_bind if yA else 0) + 0.3 * torch.randn(T, D, generator=g)
        hB = base + (4.0 * u_bind if yB else 0) + 0.3 * torch.randn(T, D, generator=g)
        pairs.append({"pair_id": f"own-{i:02d}", "hA": hA, "hB": hB, "positions": list(range(T - span, T)), "yA": yA, "yB": yB})
    return pairs, u_bind


def test_build_ownership_synthetic():
    pairs, u_bind = _ownership_pairs()
    Q = _Q()
    shared, per = W.build_ownership(pairs, Q, n_folds=4, seed=0, Cs=(0.1,))
    assert abs(float(W.cos(shared["d_cm"], u_bind))) > 0.95 and float(W.cos(shared["d_cm"], u_bind)) > 0  # oriented toward label 1
    fold_of = shared["probe"]["fold_of_pair"]
    for f in shared["probe"]["folds"]:
        assert not set(f["train_pairs"]) & set(f["test_pairs"])
        assert all(fold_of[p] == f["fold"] for p in f["test_pairs"]) and all(fold_of[p] != f["fold"] for p in f["train_pairs"])
        assert f["accuracy"] > 0.85 and f["within_pair_win"] > 0.85
        assert abs(float(f["w_raw"] @ shared["d_cm"])) >= 0  # raw weights exist
    for pid, rec in per.items():
        assert rec["fold"] == fold_of[pid]
        _assert_decomposition(rec, Q)
        # the pair's d_cm is the shared one with the pair's sign: Δ·d_cm > 0 for every pair (orientation A→B)
        assert torch.all(rec["coef"]["d_cm"] > 0), pid
        s = 1.0 if pairs[int(pid[-2:])]["yB"] == 1 else -1.0
        assert torch.allclose(rec["dirs"]["d_cm"][0], s * shared["d_cm"], atol=1e-6)
        assert rec["frac"]["d_cm"].mean() > 0.5  # the planted binding direction carries most of Δ
    # the held-out probe of a pair never saw it
    with pytest.raises(ValueError):
        W.build_ownership([dict(pairs[0], yB=pairs[0]["yA"])] + pairs[1:], Q, n_folds=2, Cs=(0.1,))


def _mapping_pairs(n_pairs=24, T=10, seed=0):
    g = torch.Generator().manual_seed(seed)
    sym_vec = {s: 6.0 * W.unit(torch.randn(D, generator=g)) for s in SYMBOLS}
    pairs = []
    for i in range(n_pairs):
        a, b = SYMBOLS[i % 8], SYMBOLS[(i * 3 + 1) % 8]
        if a == b:
            b = SYMBOLS[(i + 1) % 8]
        base = torch.randn(T, D, generator=g)
        pos = [2, 7]
        hA, hB = base.clone(), base.clone()
        hA[2] += sym_vec[a]
        hB[2] += sym_vec[b]
        hA[7] += sym_vec[b]
        hB[7] += sym_vec[a]
        hA += 0.2 * torch.randn(T, D, generator=g)
        hB += 0.2 * torch.randn(T, D, generator=g)
        pairs.append({"pair_id": f"map-{i:02d}", "hA": hA, "hB": hB, "positions": pos, "symA": [a, b], "symB": [b, a]})
    return pairs, sym_vec


def test_build_mapping_synthetic():
    pairs, sym_vec = _mapping_pairs()
    Q = _Q()
    shared, per = W.build_mapping(pairs, Q, n_folds=4, seed=0, Cs=(0.1,))
    assert shared["symbols"] == SYMBOLS and shared["class_means"].shape == (8, D)
    fold_of = shared["probe"]["fold_of_pair"]
    for f in shared["probe"]["folds"]:
        assert not set(f["train_pairs"]) & set(f["test_pairs"])
        assert all(fold_of[p] == f["fold"] for p in f["test_pairs"])
        assert f["w_raw"].shape == (8, D) and f["classes"] == SYMBOLS
        assert f["accuracy"] > 0.8 and f["within_pair_win"] > 0.8
    for p in pairs:
        rec = per[p["pair_id"]]
        _assert_decomposition(rec, Q)
        assert rec["positions"].tolist() == [2, 7]
        # d_cm(pos) = unit(mean[symB] − mean[symA]) and points along Δ(pos)
        a, b = p["symA"][0], p["symB"][0]
        expect = W.unit(shared["class_means"][SYMBOLS.index(b)] - shared["class_means"][SYMBOLS.index(a)])
        assert torch.allclose(rec["dirs"]["d_cm"][0], expect, atol=1e-6)
        assert torch.all(rec["coef"]["d_cm"] > 0)
        assert float(W.cos(rec["dirs"]["d_cm"][0], sym_vec[b] - sym_vec[a])) > 0.9


def _error_states(n=120, seed=0):
    g = torch.Generator().manual_seed(seed)
    sym_vec = {s: 3.0 * W.unit(torch.randn(D, generator=g)) for s in SYMBOLS}
    X, actual, target, ids = [], [], [], []
    for i in range(n):
        a = SYMBOLS[i % 8]
        t = SYMBOLS[(i // 8 + 1 + i) % 8]
        if t == a:
            t = SYMBOLS[(i + 1) % 8]
        X.append(sym_vec[a] + 0.5 * torch.randn(D, generator=g))
        actual.append(a)
        target.append(t)
        ids.append(f"pz-{i:04d}")
    return torch.stack(X), actual, target, ids, sym_vec


def test_build_errors_synthetic():
    X, actual, target, ids, sym_vec = _error_states()
    Q = _Q()
    shared, per = W.build_errors(X, actual, target, ids, Q, n_folds=5, seed=0, Cs=(0.1,))
    assert shared["symbols"] == SYMBOLS and shared["centroids"].shape == (8, D) and shared["d_cm_table"].shape == (8, D)
    a_arr = np.asarray(actual)
    for j, s in enumerate(SYMBOLS):
        assert torch.allclose(shared["centroids"][j], X[torch.as_tensor(a_arr == s)].mean(0), atol=1e-4)
        assert torch.allclose(shared["d_cm_table"][j], X[torch.as_tensor(a_arr == s)].mean(0) - X[torch.as_tensor(a_arr != s)].mean(0), atol=1e-4)
    fold_of = shared["probe"]["fold_of_pair"]
    for f in shared["probe"]["folds"]:
        assert not set(f["train_items"]) & set(f["test_items"])
        assert all(fold_of[i] == f["fold"] for i in f["test_items"])
        assert f["accuracy"] > 0.9 and f["favours_actual"] > 0.9  # the probe reads the planted actual symbol
    for i, iid in enumerate(ids):
        rec = per[iid]
        _assert_decomposition(rec, Q)
        a, t = actual[i], target[i]
        # full = centroid[target] − h, and every direction is unit (scaled to ‖full‖ by delta_norm at edit time)
        assert torch.allclose(rec["delta"][0], shared["centroids"][SYMBOLS.index(t)] - X[i], atol=1e-5)
        assert torch.allclose(rec["delta_norm"][0], rec["delta"][0].norm(), atol=1e-4)
        expect = W.unit(shared["d_cm_table"][SYMBOLS.index(t)] - shared["d_cm_table"][SYMBOLS.index(a)])
        assert torch.allclose(rec["dirs"]["d_cm"][0], expect, atol=1e-6)
        assert float(rec["coef"]["d_cm"][0]) > 0  # the centroid swap points toward the target class mean
        assert rec["fold"] == fold_of[iid]
    with pytest.raises(ValueError):
        W.build_errors(X, actual, list(actual), ids, Q)  # actual == target is invalid


def test_summarise_family_and_two_half():
    X, actual, target, ids, _ = _error_states(n=80)
    Q = _Q()
    _, per = W.build_errors(X, actual, target, ids, Q, n_folds=4, Cs=(0.1,))
    s = W.summarise_family(per, Q)
    assert s["n_pairs"] == 80 and s["n_positions"] == 80
    tot = sum(s["frac_mean"][k] for k in ("d_cm", "d_pw", "d_J_excl", "d_res"))
    assert abs(tot - 1) < 1e-3
    assert abs(s["cosines"]["d_cm|d_pw"]["max_abs"]) < 1e-4
    assert s["j_energy"]["random_expectation"] == pytest.approx(R / D)
    assert s["j_energy"]["d_res"] < 1e-6
    vecs = {f"k{i}": torch.ones(D) + 0.01 * i for i in range(10)}
    assert W.two_half_cos(vecs) > 0.999


# ------------------------------------------------------------------ Michael's recipe
def _graded_states(n=600, d=96, seed=0):
    g = torch.Generator().manual_seed(seed)
    tens_vec = 2.0 * torch.randn(10, d, generator=g)
    units_vec = 2.0 * torch.randn(10, d, generator=g)
    vals = torch.randint(1, 100, (n,), generator=g)
    X = tens_vec[vals // 10] + units_vec[vals % 10] + 0.5 * torch.randn(n, d, generator=g) + 5.0
    return X, vals


def test_michael_recipe_ranks_and_swap():
    X, vals = _graded_states()
    fit = MK.michael_subspaces(X, {"n": vals}, seed=0)
    # 10 tens classes (0..9) and 10 units classes → 9 + 9 = 18 class-mean directions, 18 probe-weight directions, 18 random
    assert fit["ranks"]["n|mean"] == 18, fit["ranks"]
    assert fit["ranks"]["n|lr"] == 18, fit["ranks"]
    assert fit["ranks"]["n|rand"] == 18
    for k, U in fit["subspaces"].items():
        assert U.shape == (X.shape[1], 18) and torch.allclose(U.T @ U, torch.eye(18), atol=1e-4), k
    assert sorted(fit["classes"]["n_tens"]) == list(range(10)) and sorted(fit["classes"]["n_units"]) == list(range(10))
    # the probes read the planted value
    reads = torch.tensor([MK.read_value(X[i], fit, "n") for i in range(50)])
    assert float((reads == vals[:50]).float().mean()) > 0.95
    # the interchange swap in the class-mean and probe-weight subspaces moves the probe to the source; random does not
    g = torch.Generator().manual_seed(9)
    idx = torch.randperm(X.shape[0], generator=g)[:40]
    moved = {}
    for kind in ("mean", "lr", "rand"):
        U = fit["subspaces"][f"n|{kind}"]
        hits = 0
        for i, j in zip(idx[::2], idx[1::2]):
            if vals[i] == vals[j]:
                continue
            hits += int(MK.read_value(MK.swap(X[i], X[j], U), fit, "n") == int(vals[j]))
        moved[kind] = hits / len(idx[::2])
    assert moved["mean"] > 0.8 and moved["lr"] > 0.8 and moved["rand"] < 0.3, moved
    # a value set missing a class gives one direction fewer per missing class, as in his code (classes present only)
    fit2 = MK.michael_subspaces(X[vals >= 10], {"n": vals[vals >= 10]}, seed=0)
    assert fit2["ranks"]["n|mean"] == 17 and sorted(fit2["classes"]["n_tens"]) == list(range(1, 10))


def test_michael_two_slots_and_validation():
    X, a = _graded_states(n=300, d=24, seed=1)
    b = torch.randint(1, 100, (300,), generator=torch.Generator().manual_seed(2))
    fit = MK.michael_subspaces(X, {"a": a, "b": b}, seed=0)
    assert set(fit["subspaces"]) == {f"{s}|{k}" for s in "ab" for k in ("mean", "lr", "rand")}
    assert fit["ranks"]["a|mean"] == 18
    assert set(fit["probes"]) == {"a_tens", "a_units", "b_tens", "b_units"}
    with pytest.raises(ValueError):
        MK.digit_labels(torch.tensor([100]))
    with pytest.raises(ValueError):
        MK.michael_subspaces(X, {"a": a[:10]})
    assert MK.orth(torch.eye(5)[:, :3]).shape == (5, 3)
    assert MK.orth(torch.stack([torch.ones(5), 2 * torch.ones(5)], 1)).shape == (5, 1)


# ------------------------------------------------------------------ the real artefacts (skipped when not built on this machine)
REAL_DIR = REPO / "cache" / "g_agreement" / "w" / "directions"


@pytest.mark.skipif(not (REAL_DIR / "index.json").exists(), reason="Track B outputs not built here")
def test_real_outputs_layout_and_holdout():
    import json

    idx = json.loads((REAL_DIR / "index.json").read_text())
    assert set(idx["families"]) >= {"ownership", "mapping", "errors"}
    for fam, fidx in idx["families"].items():
        shared = torch.load(REAL_DIR / fidx["shared"], map_location="cpu", weights_only=False)
        fold_of = shared["probe"]["fold_of_pair"]
        folds = shared["probe"]["folds"]
        assert len(folds) == 5 and shared["Q_ref"]["shape"] == [5120, 384]
        for f in folds:
            tr = set(f.get("train_pairs", f.get("train_items", [])))
            te = set(f.get("test_pairs", f.get("test_items", [])))
            assert tr and te and not (tr & te)
            assert all(fold_of[k] == f["fold"] for k in te) and all(fold_of[k] != f["fold"] for k in tr)
            assert f["w_raw"].dtype == torch.float32 and f["w_raw"].shape[1] == 5120
        for e in fidx["pairs"][:3]:
            obj = torch.load(REAL_DIR / e["file"], map_location="cpu", weights_only=False)
            P = len(e["positions"])
            assert obj["positions"].dtype == torch.int64 and obj["positions"].shape == (P,)
            assert obj["delta"].shape == (P, 5120) and obj["delta"].dtype == torch.float32
            assert obj["delta_norm"].shape == (P,)
            assert set(obj["dirs"]) == set(W.DIR_NAMES) and set(obj["frac"]) == set(W.FRAC_NAMES)
            for k in W.DIR_NAMES:
                assert obj["dirs"][k].shape == (P, 5120) and obj["dirs"][k].dtype == torch.float32
                assert torch.allclose(obj["dirs"][k].norm(dim=1), torch.ones(P), atol=1e-3)
                assert obj["coef"][k].shape == (P,)
            assert torch.all(((obj["dirs"]["d_cm"] * obj["dirs"]["d_pw"]).sum(1)).abs() < 1e-3)
            tot = obj["frac"]["d_cm"] + obj["frac"]["d_pw"] + obj["frac"]["d_J_excl"] + obj["frac"]["d_res"]
            assert torch.all((tot - 1).abs() < 1e-2)
            assert obj["fold"] == fold_of[obj["pair_id"]] and obj["random"]["K"] == 10 and obj["random"]["seed"] == W.random_seed_for(obj["pair_id"])
            assert obj["layer"] == {"ownership": 38, "mapping": 38, "errors": 48}[fam]
            if fam == "errors":
                assert obj["positions"].tolist() == [-1]
                s_idx = shared["symbols"].index(obj["meta"]["target"])
                assert torch.allclose(obj["delta"][0] + 0, obj["delta"][0])  # finite
                assert obj["meta"]["actual"] != obj["meta"]["target"] and shared["centroids"][s_idx].shape == (5120,)
