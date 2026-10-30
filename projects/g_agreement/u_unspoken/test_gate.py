"""Synthetic check of the §63 U0 gate: one property read from the state but never said,
one answered from the question alone, one spoken."""
import numpy as np

from projects.g_agreement.u_unspoken.gate import auroc, run


def _rows(seed=0):
    rng = np.random.default_rng(seed)
    P, S, Q = [], [], []
    for prop, sig_m, sig_x, k_spont in [("sent_pos", 1.2, 0.0, 0), ("prior_only", 1.0, 1.0, 0), ("language", 3.0, 0.0, 250)]:
        for i in range(200):
            y = i % 2
            prior = rng.normal(0, 1)
            P.append(dict(property=prop, reader="nla", item_id=i, label=y, condition="matched",
                          score=sig_m * y + prior + rng.normal(0, 1)))
            P.append(dict(property=prop, reader="nla", item_id=i, label=y, condition="mismatched",
                          score=sig_x * y + prior + rng.normal(0, 1)))
            Q.append(dict(property=prop, item_id=i, label=y, score=3 * y + rng.normal(0, 1)))
        for j in range(320):
            S.append(dict(property=prop, reader="nla", item_id=j % 200, sample=j, stated=j < k_spont, exhibited=False))
    return P, S, Q


def test_auroc_basic():
    assert auroc(np.array([0, 1]), np.array([0.0, 1.0])) == 1.0
    assert auroc(np.array([0, 1]), np.array([1.0, 1.0])) == 0.5


def test_gate(tmp_path):
    P, S, Q = _rows()
    rows = {r["property"]: r for r in run(P, S, Q, tmp_path)}
    assert rows["sent_pos"]["verdict"] == "UNSPOKEN"
    assert rows["prior_only"]["verdict"] == "ANSWERED_FROM_QUESTION"
    assert rows["language"]["verdict"] == "SPOKEN_OR_WEAK"
    assert (tmp_path / "u0_gate.md").exists()


def test_cluster_bootstrap_runs(tmp_path):
    P, S, Q = _rows()
    item_rows = {r["property"]: r for r in run(P, S, Q, tmp_path / "items")}
    for r in P:
        r["cluster"] = r["item_id"] // 20  # 10 templates of 20 items
    clus_rows = {r["property"]: r for r in run(P, S, Q, tmp_path / "clusters")}
    w_items = item_rows["sent_pos"]["delta_hi"] - item_rows["sent_pos"]["delta_lo"]
    w_clus = clus_rows["sent_pos"]["delta_hi"] - clus_rows["sent_pos"]["delta_lo"]
    assert clus_rows["sent_pos"]["verdict"] in {"UNSPOKEN", "ANSWERED_FROM_QUESTION"}
    assert w_clus > 0 and w_items > 0
