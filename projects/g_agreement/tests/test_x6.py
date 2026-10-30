"""X6 tests, CPU only, on synthetic data: the sign / majority / leave-one-out logic, the rate table, the
shared-error statistic, the probe scoring conventions (D1 version A / B, D2 source A / B), the k-fold logistic
probes on separable random data, and analyze.py end to end on a synthetic world written to tmp_path (items,
X1/X2/X3 LO rows, behaviour rows, fp32 states, bf16 read-back vectors). Never reads the real cache; results/ and
cache/ are asserted untouched.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_x6.py -q``
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")

from projects.g_agreement.x6_majority import analyze as X6  # noqa: E402

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
D = 16


# ------------------------------------------------------------------ unit: signs and majorities
def test_sign_and_majority():
    assert X6.sign(0.3) == 1 and X6.sign(-0.3) == -1 and X6.sign(0.0) == -1 and X6.sign(None) is None and X6.sign(float("nan")) is None
    assert X6.majority([1, 1, -1]) == 1 and X6.majority([1, -1]) is None and X6.majority([None, -1]) == -1 and X6.majority([None, None]) is None and X6.majority([]) is None


def test_loo_majority_excludes_self_and_handles_one_member():
    s = {"jlens": 1, "olens": -1, "nla": -1, "probe": 1}
    assert X6.loo_majority(s, X6.MAJ_DEFS["all"], "jlens") == -1          # others: -1, -1, +1
    assert X6.loo_majority(s, X6.MAJ_DEFS["all"], "olens") == 1           # others: +1, -1, +1
    assert X6.loo_majority(s, X6.MAJ_DEFS["siblings"], "olens") == -1     # the other sibling alone
    assert X6.loo_majority(s, X6.MAJ_DEFS["siblings"], "jlens") == -1     # siblings agree -> defined
    s2 = dict(s, nla=1)
    assert X6.loo_majority(s2, X6.MAJ_DEFS["siblings"], "jlens") is None  # siblings disagree -> undefined
    assert X6.loo_majority(s, X6.MAJ_DEFS["nonsib"], "olens") == 1


def _rows(n, lo_fn, cluster_fn=lambda i: f"c{i}"):
    return [{"state": f"s{i}", "cluster": cluster_fn(i), "family": "f", "key": "k", "lo": lo_fn(i)} for i in range(n)]


def test_rate_table_perfect_and_anti_readers():
    # jlens always right, olens always right, nla always wrong, probe right on even states
    rows = _rows(20, lambda i: {"jlens": 1.0, "olens": 2.0, "nla": -1.0, "probe": 1.0 if i % 2 == 0 else -1.0})
    t = X6.rate_table(rows, 50, 0)
    R = t["readers"]
    assert R["jlens"]["A_key"]["p"] == 1.0 and R["nla"]["A_key"]["p"] == 0.0 and R["probe"]["A_key"]["p"] == 0.5
    # ALL LOO majority for nla = (jlens, olens, probe) = always +1 -> nla agrees 0%
    assert R["nla"]["A_maj"]["all"]["p"] == 0.0 and R["nla"]["A_maj"]["all"]["n"] == 20
    # for jlens, others = (olens +, nla -, probe ±): three votes never tie; majority + on even states, - on odd -> jlens agrees on half
    assert R["jlens"]["A_maj"]["all"]["n"] == 20 and R["jlens"]["A_maj"]["all"]["p"] == 0.5
    # siblings: olens vs nla always disagree -> jlens's sibling majority never defined; olens's = nla alone -> 0 agreement
    assert R["jlens"]["A_maj"]["siblings"]["n"] == 0 and R["olens"]["A_maj"]["siblings"]["p"] == 0.0
    M = t["majority"]
    assert M["siblings"]["n_defined"] == 0 and M["nonsib"]["n_defined"] == 10 and M["nonsib"]["M_acc"]["p"] == 1.0
    assert M["all"]["n_defined"] == 10 and M["all"]["M_acc"]["p"] == 1.0  # 4 votes: 3-1 on even states, 2-2 tie on odd
    for rd in X6.READERS:
        assert set(R[rd]["A_key"]) >= {"k", "n", "p", "lo", "hi"}


def test_rate_table_unscorable_votes_excluded():
    rows = _rows(6, lambda i: {"jlens": None, "olens": 1.0, "nla": 1.0, "probe": -1.0})
    t = X6.rate_table(rows, 20, 0)
    assert t["readers"]["jlens"]["A_key"]["n"] == 0 and t["readers"]["jlens"]["n_unscorable"] == 6
    assert np.isnan(t["readers"]["jlens"]["A_maj"]["all"]["p"])
    # probe's LOO ALL majority = (None, +1, +1) -> +1; probe disagrees always
    assert t["readers"]["probe"]["A_maj"]["all"]["p"] == 0.0 and t["readers"]["probe"]["A_maj"]["all"]["n"] == 6


def test_spearman_and_shared_error():
    rng = np.random.default_rng(0)
    # independent coin-flip readers around p = 0.5: shared-error observed should be near the independence product
    rows = _rows(4000, lambda i: {"jlens": rng.choice([-1.0, 1.0]), "olens": rng.choice([-1.0, 1.0]), "nla": rng.choice([-1.0, 1.0]), "probe": rng.choice([-1.0, 1.0])})
    se = X6.shared_error(rows, 50, 0)
    assert se["n"] == 4000 and abs(se["all_same_wrong"]["observed"]["p"] - se["all_same_wrong"]["expected_independent"]) < 0.03
    assert abs(se["all_same_wrong"]["expected_independent"] - 0.125) < 0.03
    # perfectly correlated siblings: observed shared error = marginal, far above the product
    rows2 = _rows(400, lambda i: {"jlens": -1.0 if i % 2 else 1.0, "olens": -1.0 if i % 2 else 1.0, "nla": -1.0 if i % 2 else 1.0, "probe": 1.0})
    se2 = X6.shared_error(rows2, 50, 0)
    assert se2["all_same_wrong"]["observed"]["p"] == 0.5 and abs(se2["all_same_wrong"]["expected_independent"] - 0.125) < 1e-9 and se2["all_same_wrong"]["ratio"] == 4.0
    t = X6.rate_table(rows2, 20, 0)
    sp = X6.spearman_readers(t)
    assert set(sp) == set(X6.MAJ_DEFS) and sp["all"]["n"] == 4 and (np.isnan(sp["all"]["rho"]) or -1 <= sp["all"]["rho"] <= 1)
    # a clean monotone case gives rho = 1: A_maj and A_key ranked identically
    t3 = {"readers": {r: {"A_key": {"p": v}, "A_maj": {d: {"p": v / 2} for d in X6.MAJ_DEFS}} for r, v in zip(X6.READERS, (0.9, 0.8, 0.7, 0.6))}}
    assert X6.spearman_readers(t3)["all"]["rho"] == 1.0


# ------------------------------------------------------------------ unit: probes
def test_probe_direction_and_sign_conventions():
    rng = np.random.default_rng(1)
    u_true = np.zeros(D); u_true[0] = 1.0
    H, pairs = {}, []
    for p in range(6):
        base = rng.normal(size=D)
        H[f"p{p}A"], H[f"p{p}B"] = base + 2 * u_true, base - 2 * u_true
        pairs.append({"pair_id": f"p{p}", "family": "f", "A": f"p{p}A", "B": f"p{p}B"})
    dirs = X6.loo_directions(pairs, H)
    assert set(dirs) == {p["pair_id"] for p in pairs}
    u, m = dirs["p0"]
    assert abs(float(u @ u_true)) > 0.95 and np.allclose(m, (H["p0A"] + H["p0B"]) / 2)
    # D1: both versions of a pair are scored toward their own answer -> positive for both
    assert X6.probe_toward_key_d1(dirs, "p0", "A", H["p0A"]) > 0 and X6.probe_toward_key_d1(dirs, "p0", "B", H["p0B"]) > 0
    assert X6.probe_toward_key_d1(dirs, "p0", "A", H["p0B"]) < 0  # the wrong state for version A
    # D2: planted from A toward B lands near h_B -> positive toward the other (= B); and the mirror
    assert X6.probe_toward_other_d2(dirs, "p0", "A", H["p0B"]) > 0 and X6.probe_toward_other_d2(dirs, "p0", "B", H["p0A"]) > 0
    assert X6.probe_toward_other_d2(dirs, "p0", "A", H["p0A"]) < 0
    assert X6.probe_toward_key_d1(dirs, "unknown", "A", H["p0A"]) is None
    # missing states are skipped, not crashed
    assert "p0" not in X6.loo_directions(pairs, {k: v for k, v in H.items() if k != "p0A"})


def test_kfold_probes_on_separable_data():
    rng = np.random.default_rng(2)
    n = 60
    labels = [("A", "B", "C")[i % 3] for i in range(n)]
    X = rng.normal(size=(n, D)) * 0.3
    for i, l in enumerate(labels):
        X[i, "ABC".index(l)] += 3.0
    cands = [(l, ("A", "B", "C")[(i + 1) % 3]) for i, l in enumerate(labels)]
    sc = X6.probe_multinomial_kfold(X, labels, cands, n_folds=5, seed=0)
    assert all(s is not None for s in sc) and np.mean([s > 0 for s in sc]) >= 0.9
    # a candidate never seen in training is unscorable
    sc2 = X6.probe_multinomial_kfold(X, labels, [("A", "Z")] * n, n_folds=5, seed=0)
    assert all(s is None for s in sc2)
    y = [int(l == "A") for l in labels]
    z = X6.probe_binary_kfold(X, y, n_folds=5, seed=0)
    assert all(v is not None for v in z) and np.mean([(v > 0) == bool(t) for v, t in zip(z, y)]) >= 0.9
    # binary multinomial path (2 classes) returns a consistent sign
    sc3 = X6.probe_multinomial_kfold(X, ["A" if t else "B" for t in y], [("A", "B") if t else ("B", "A") for t in y], n_folds=5, seed=0)
    assert np.mean([s is not None and s > 0 for s in sc3]) >= 0.9


def test_rate_table_field_variant():
    rows = _rows(10, lambda i: {"jlens": 1.0, "olens": 1.0, "nla": 1.0, "probe": 1.0})
    for r in rows:
        r["lo_centred"] = {"jlens": -1.0, "olens": 1.0, "nla": None, "probe": 1.0}
    raw, cen = X6.rate_table(rows, 20, 0, field="lo"), X6.rate_table(rows, 20, 0, field="lo_centred")
    assert raw["readers"]["jlens"]["A_key"]["p"] == 1.0 and cen["readers"]["jlens"]["A_key"]["p"] == 0.0 and cen["readers"]["nla"]["A_key"]["n"] == 0
    res = X6.analyse_tables({"d": rows}, 20, 0)
    assert set(res) == set(X6.VARIANTS) and res["centred"]["d"]["readers"]["jlens"]["A_key"]["p"] == 0.0


def test_symbol_bias_kfold_removes_additive_bias():
    rng = np.random.default_rng(3)
    syms = "ABCDEFGH"
    bias = {s: b for s, b in zip(syms, (3.0, -2.0, 1.0, 0.0, -1.0, 2.0, -3.0, 0.5))}
    cands = [(syms[i % 8], syms[(i + 3) % 8]) for i in range(200)]
    true_signal = [0.4 if i % 3 else -0.4 for i in range(200)]
    lo = [bias[a] - bias[o] + sgn + rng.normal(scale=0.05) for (a, o), sgn in zip(cands, true_signal)]
    c = X6.symbol_bias_kfold(lo, cands, n_folds=5, seed=0)
    assert all(v is not None for v in c)
    assert np.mean([(v > 0) == (t > 0) for v, t in zip(c, true_signal)]) >= 0.95        # centred sign recovers the signal
    assert np.mean([(l > 0) == (t > 0) for l, t in zip(lo, true_signal)]) < 0.8         # the raw sign is dominated by the bias
    lo2 = list(lo); lo2[0] = None
    c2 = X6.symbol_bias_kfold(lo2, cands, n_folds=5, seed=0)
    assert c2[0] is None and sum(v is None for v in c2) == 1
    cands3 = list(cands); cands3[0] = ("Z", "B")  # 'Z' occurs only in item 0 -> unseen when item 0 is held out -> None, no crash
    c3 = X6.symbol_bias_kfold(lo, cands3, n_folds=5, seed=0)
    assert c3[0] is None and sum(v is None for v in c3) == 1


def test_alpha_star_and_readvec_path(tmp_path):
    beh = [{"site": "S2", "condition": "planted", "pair_id": "p", "source": "A", "alpha": a, "flipped_to_other": a >= 0.75, "coherent": a != 0.75} for a in (0.25, 0.5, 0.75, 1.0)]
    beh += [{"site": "S2", "condition": "planted", "pair_id": "p", "source": "B", "alpha": 1.0, "flipped_to_other": False, "coherent": True}]
    beh += [{"site": "S1", "condition": "planted", "pair_id": "p", "source": "B", "alpha": 4.0, "flipped_to_other": True, "coherent": True}]
    a = X6.alpha_star(beh, "S2")
    assert a == {("p", "A"): 1.0, ("p", "B"): None}  # 0.75 flipped but incoherent -> not a flipping dose
    assert X6.readvec_path(tmp_path, "xown-02|A|S2|planted|0.5|None").name == "xown-02__A__S2__planted__0.5__None.pt"


# ------------------------------------------------------------------ synthetic world + end to end
def synthetic_world(root: Path, n_pairs: int = 8, n_pz: int = 40, n_ch: int = 20, seed: int = 0):
    rng = np.random.default_rng(seed)
    root.mkdir(parents=True, exist_ok=True)
    states, readvecs = root / "states", root / "readvecs"
    states.mkdir(); readvecs.mkdir()
    items, x1, beh, x2, x3, selected = {}, [], [], [], [], []
    u = {f: np.eye(D)[i] for i, f in enumerate(X6.FAMILIES)}  # one planted axis per family: A = +, B = -
    names = {"ownership": ("Paul", "Mira"), "mapping": ("D", "E"), "language": ("Swedish", "Spanish"), "tense": ("past", "future")}
    for fam in X6.FAMILIES:
        for k in range(n_pairs):
            pid = f"x{fam[:3]}-{k + 1:02d}"
            split = "dev" if k == 0 else "test"
            base = rng.normal(size=D)
            c0, c1 = names[fam]
            for v, h, ans, oth in (("A", base + 2 * u[fam], c0, c1), ("B", base - 2 * u[fam], c1, c0)):
                iid = f"{pid}{v}"
                items[iid] = {"item_id": iid, "pair_id": pid, "version": v, "family": fam, "split": split, "template_id": f"{fam}-t1", "prompt_text": "p", "render": "chat", "system": None,
                              "primary": {"name": "x", "question": "q", "candidates": [c0, c1], "answer": ans, "answer_aliases": [ans.lower()]},
                              "construction": {"answer_is_first_mentioned": v == "A"}}
                torch.save(torch.tensor(h, dtype=torch.float32), states / f"{iid}.pt")
                # readers: jlens perfect; olens right except every 4th; nla random
                for rd, lo in (("jlens", 1.0), ("olens", -1.0 if k % 4 == 1 else 1.0), ("nla", float(rng.choice([-1.0, 1.0])))):
                    x1.append({"reader": rd, "item_id": iid, "pair_id": pid, "family": fam, "split": split, "version": v, "condition": "natural", "cand_A": ans, "cand_B": oth, "lo": lo, "unscorable": False})
            if fam in ("ownership", "mapping") and split == "test":
                for src, other_v in (("A", "B"), ("B", "A")):
                    hs = base + (2 if src == "A" else -2) * u[fam]
                    key = f"{pid}|{src}|nat|natural|0.0|None"
                    beh.append({"key": key, "pair_id": pid, "family": fam, "source": src, "state_item_id": f"{pid}{src}", "site": "nat", "alpha": 0.0, "condition": "natural",
                                "cand_A": names[fam][0] if src == "A" else names[fam][1], "cand_B": names[fam][1] if src == "A" else names[fam][0], "kept_original": k != 3, "flipped_to_other": False, "coherent": True})
                    for rd in X6.LO_READERS:  # natural-state LO toward the other candidate (the baseline of the CENTRED shift)
                        x2.append({"reader": rd, "entry_key": key, "pair_id": pid, "family": fam, "source": src, "site": "nat", "alpha": 0.0, "condition": "natural", "lo_toward_other": 0.5, "unscorable": False})
                    for a in (0.25, 0.5, 0.75, 1.0):
                        key = f"{pid}|{src}|S2|planted|{a}|None"
                        v = hs + a * ((base + (-2 if src == "A" else 2) * u[fam]) - hs)
                        torch.save(torch.tensor(v, dtype=torch.bfloat16), readvecs / (key.replace("|", "__") + ".pt"))
                        flipped = a >= 0.75 or (a == 0.5 and k % 2 == 0)
                        beh.append({"key": key, "pair_id": pid, "family": fam, "source": src, "site": "S2", "alpha": a, "condition": "planted", "cand_A": "own", "cand_B": "other",
                                    "flipped_to_other": flipped, "coherent": True, "lo_model": 10 * a - 5})
                        for rd, lo in (("jlens", 1.0), ("olens", 1.0 if k % 3 else -1.0), ("nla", float(rng.choice([-1.0, 1.0])))):
                            x2.append({"reader": rd, "entry_key": key, "pair_id": pid, "family": fam, "source": src, "site": "S2", "alpha": a, "condition": "planted", "lo_toward_other": lo, "unscorable": False})
    # X3: puzzles with the actual symbol planted on axis 8 + symbol index; choice with first-listed planted on axis 15
    syms = "ABCDEFGH"
    for i in range(n_pz):
        iid = f"xpz-{i + 1:04d}"
        act, oth = syms[i % 8], syms[(i + 3) % 8]
        h = rng.normal(size=D) * 0.3; h[8 + (i % 8) % 7] += 3.0
        torch.save(torch.tensor(h, dtype=torch.float32), states / f"{iid}.pt")
        selected.append({"item_id": iid, "pair_id": iid, "version": "A", "family": "puzzle", "set": "error" if i % 2 == 0 else "error_control", "split": "test",
                         "primary": {"name": "model_actual_answer", "question": "q", "candidates": [act, oth], "answer": act, "answer_aliases": [act.lower()]}, "text_key": oth, "source": {"correct": oth, "trace": []}})
        for rd, lo in (("jlens", 1.0 if i % 5 else -1.0), ("olens", -1.0 if i % 2 == 0 else 1.0), ("nla", -1.0 if i % 2 == 0 else 1.0)):
            x3.append({"reader": rd, "item_id": iid, "family": "puzzle", "set": selected[-1]["set"], "cand_actual": act, "cand_other": oth, "lo_actual": lo, "unscorable": False})
    for i in range(n_ch):
        iid = f"xch-{i + 1:04d}"
        first = i % 2 == 0
        act, oth = (f"w{i}a", f"w{i}b")
        h = rng.normal(size=D) * 0.3; h[15] += 3.0 if first else -3.0
        torch.save(torch.tensor(h, dtype=torch.float32), states / f"{iid}.pt")
        selected.append({"item_id": iid, "pair_id": iid, "version": "A", "family": "choice", "set": "disagree" if i % 2 == 0 else "agree_control", "split": "test",
                         "primary": {"name": "model_actual_answer", "question": "q", "candidates": [act, oth], "answer": act, "answer_aliases": [act]}, "text_key": oth,
                         "source": {"first_listed": act if first else oth, "self_guess": oth}})
        for rd in X6.LO_READERS:
            x3.append({"reader": rd, "item_id": iid, "family": "choice", "set": selected[-1]["set"], "cand_actual": act, "cand_other": oth, "lo_actual": 1.0, "unscorable": rd == "jlens" and i == 0})
    (root / "items.json").write_text(json.dumps({"meta": {}, "items": list(items.values())}))
    (root / "selected.json").write_text(json.dumps({"meta": {}, "items": selected}))
    for name, rows in (("x1.jsonl", x1), ("beh.jsonl", beh), ("x2.jsonl", x2), ("x3.jsonl", x3)):
        (root / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return root


def _args(root: Path, out: Path, extra=()):
    return ["--items", str(root / "items.json"), "--selected", str(root / "selected.json"), "--x1-lo", str(root / "x1.jsonl"), "--x2-behaviour", str(root / "beh.jsonl"),
            "--x2-lo", str(root / "x2.jsonl"), "--x3-lo", str(root / "x3.jsonl"), "--states", str(root / "states"), "--readvecs", str(root / "readvecs"),
            "--frozen", str(root / "missing_frozen.json"), "--out", str(out), "--allow-unfrozen", "--n-boot", "60", *extra]


def test_analyze_end_to_end(tmp_path):
    root = synthetic_world(tmp_path / "world")
    out = tmp_path / "out"
    s = X6.main(_args(root, out))
    for f in ("summary.json", "x6.csv", "fig_main.png", "x6.md", "log.md"):
        assert (out / f).exists(), f
    assert s["frozen"] is False
    D1 = s["datasets"]["D1"]["raw"]
    assert D1["n_states"] == 4 * 7 * 2 and D1["n_clusters"] == 28
    # readers: jlens perfect on D1, the probe recovers the planted axis (LOO), olens wrong on every 4th pair
    assert D1["readers"]["jlens"]["A_key"]["p"] == 1.0 and D1["readers"]["probe"]["A_key"]["p"] >= 0.9
    assert abs(D1["readers"]["olens"]["A_key"]["p"] - 5 / 7) < 1e-9
    assert D1["majority"]["siblings"]["n_defined"] + D1["majority"]["siblings"]["n_undefined"] == D1["n_states"]
    # centred D1 = pair mean of the two own-LOs: olens (-1, -1) on every 4th pair stays wrong, jlens stays right, probe identical
    C1 = s["datasets"]["D1"]["centred"]
    assert C1["readers"]["jlens"]["A_key"]["p"] == 1.0 and abs(C1["readers"]["olens"]["A_key"]["p"] - 5 / 7) < 1e-9
    assert C1["readers"]["probe"]["A_key"]["p"] == D1["readers"]["probe"]["A_key"]["p"]
    assert set(s["D1_by_family"]) == set(X6.FAMILIES) and s["D1_by_family"]["tense"]["raw"]["n_states"] == 14
    assert s["D1_key_check"]["n_x2_natural_states"] == 2 * 7 * 2 and len(s["D1_key_check"]["states_where_model_disagrees"]) == 4
    # D2: alpha* = 0.5 on even test pairs (k = 2, 4, 6: 3 pairs x 2 families x 2 sources), 0.75 on odd (k = 1, 3, 5, 7); rows at alpha* and at alpha 1
    D2 = s["D2"]
    assert D2["n_items"] == 28 and D2["n_items_with_alpha_star"] == 28 and D2["alpha_star_counts"] == {"0.5": 12, "0.75": 16} and D2["n_missing_readvecs"] == 0
    assert s["datasets"]["D2_astar"]["raw"]["n_states"] == 28 and s["datasets"]["D2_alpha1"]["raw"]["n_states"] == 28
    assert s["datasets"]["D2_alpha1"]["raw"]["readers"]["probe"]["A_key"]["p"] >= 0.9   # at alpha 1 the read vector is the other state
    assert s["datasets"]["D2_astar"]["raw"]["readers"]["jlens"]["A_key"]["p"] == 1.0
    # centred D2 = shift from the natural LO (0.5): jlens 1.0 - 0.5 > 0 always; olens -1.0 - 0.5 < 0 on pairs with k % 3 == 0 (k = 3, 6: 2 pairs x 2 fam x 2 src = 8 of 28)
    C2 = s["datasets"]["D2_astar"]["centred"]["readers"]
    assert C2["jlens"]["A_key"]["p"] == 1.0 and C2["jlens"]["A_key"]["n"] == 28 and C2["olens"]["A_key"]["k"] == 20 and s["D2"]["n_entries_without_natural_lo"] == 0
    # D3: puzzle probe recovers the planted symbol; choice probe recovers first-listed; sets have the right sizes
    assert s["datasets"]["D3_error"]["raw"]["n_states"] == 20 and s["datasets"]["D3_disagree"]["raw"]["n_states"] == 10
    assert s["probe"]["D3"]["puzzle"]["status"] == "ok" and s["probe"]["D3"]["choice"]["status"] == "ok"
    assert s["datasets"]["D3_error"]["raw"]["readers"]["probe"]["A_key"]["p"] >= 0.8 and s["datasets"]["D3_disagree"]["raw"]["readers"]["probe"]["A_key"]["p"] >= 0.8
    assert s["probe"]["D3"]["choice"]["multinomial_n_scorable"] == 0  # every choice word is unique -> never in a training fold
    # siblings on ERROR always agree with each other (both -1) and never with the key: the sibling self-agreement vs key contrast
    E = s["datasets"]["D3_error"]["raw"]
    assert E["readers"]["olens"]["A_maj"]["siblings"]["p"] == 1.0 and E["readers"]["olens"]["A_key"]["p"] == 0.0 and E["majority"]["siblings"]["M_acc"]["p"] == 0.0
    se = E["shared_error_three_lo_readers"]
    assert se["n"] == 20 and se["all_same_wrong"]["observed"]["p"] == pytest.approx(4 / 20) and se["all_same_wrong"]["expected_independent"] == pytest.approx(0.2 * 1.0 * 1.0)
    # choice sets cannot be centred: centred == raw there; puzzle centred rows exist for every reader
    Dd = s["datasets"]["D3_disagree"]
    assert Dd["centred"]["readers"]["olens"]["A_key"]["p"] == Dd["raw"]["readers"]["olens"]["A_key"]["p"]
    assert s["datasets"]["D3_error"]["centred"]["readers"]["olens"]["A_key"]["n"] == 20
    # the unscorable jlens row is excluded, not counted as a vote
    assert Dd["raw"]["readers"]["jlens"]["n_unscorable"] == 1
    # csv: variant x reader x dataset x definition
    import csv

    rows = list(csv.DictReader(open(out / "x6.csv")))
    assert len(rows) == 2 * 7 * 4 * 3 and {r["majority_def"] for r in rows} == set(X6.MAJ_DEFS) and {r["variant"] for r in rows} == set(X6.VARIANTS)
    md = (out / "x6.md").read_text()
    assert md.count("\n") <= 40 and "ORDER-CONFOUNDED" in md and "Conclusion" in md


def test_analyze_skip_probe_and_no_fig(tmp_path):
    root = synthetic_world(tmp_path / "world", n_pairs=3, n_pz=12, n_ch=10)
    out = tmp_path / "out"
    s = X6.main(_args(root, out, ["--skip-probe", "--no-fig"]))
    assert not (out / "fig_main.png").exists() and (out / "summary.json").exists()
    assert s["datasets"]["D1"]["raw"]["readers"]["probe"]["A_key"]["n"] == 0
    # with no probe votes, the NONSIB majority for olens is J-lens alone and the ALL LOO majority has 2 voters (ties possible)
    assert s["datasets"]["D1"]["raw"]["readers"]["olens"]["A_maj"]["nonsib"]["n"] == s["datasets"]["D1"]["raw"]["n_states"]


def test_nothing_written_under_results_or_cache():
    assert sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*")) == RESULTS_SNAPSHOT
    if CACHE_SNAPSHOT is not None:
        assert sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) == CACHE_SNAPSHOT
