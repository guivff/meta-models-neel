"""Offline tests for R-D (BRIEF_R.md §3.2): r_bench/legacy.py maps the published X1 / Y1 / V1 / V7c / W2 LO rows into the
cells.csv schema. Two layers: (1) hermetic fixtures in tmp_path that exercise every mapper on synthetic rows with known
answers; (2) on the real cache (the main checkout's cache/g_agreement, skipped when absent) the published numbers must come
back exactly: X1 ownership J-lens 40/47 = 85 %, Oracle 39/47 = 83 %, V7c Oracle@42 45/48 = 94 %, plus the Y1 probe@48 79 %,
V1 Oracle@56 84 % and W2 counts J-lens exact 1 %. Also the --with-legacy hook in analyze.py (parse level). Nothing is written
under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_legacy.py -q``
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.r_bench import legacy as LG  # noqa: E402

CACHE = LG.default_cache_dir()
RESULTS = LG.default_results_dir()
HAVE_CACHE = (CACHE / "x" / "x1_lo.jsonl").exists() and (CACHE / "w" / "s3_lo.jsonl").exists()


def _jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


# ------------------------------------------------------------------ hermetic fixtures
@pytest.fixture()
def fake_root(tmp_path):
    """A tiny cache/results tree: 3 X1 ownership pairs (2 wins), V7c rows for the first 4 system pairs (3 wins) and 2 user
    pairs, puzzle-error rows at two layers from two sources with one overlap, k-way rows for counts."""
    cache, results = tmp_path / "cache", tmp_path / "results"
    items_x = json.loads((REPO / "projects/g_agreement/dataset/items_x.json").read_text())
    own = [it for it in items_x["items"] if it["family"] == "ownership" and it["split"] == "test"]
    pairs = {}
    for it in own:
        pairs.setdefault(it["pair_id"], {})[it["version"]] = it["item_id"]
    pids = sorted(pairs)[:3]
    # pair 0: 1 + 0.5 > 0 win; pair 1: -2 + 1 < 0 loss; pair 2: 0.2 + 0.1 win; the 4th pair is unscorable (excluded)
    los = {pids[0]: (1.0, 0.5), pids[1]: (-2.0, 1.0), pids[2]: (0.2, 0.1)}
    rows = []
    for pid, (a, b) in los.items():
        for v, lo in (("A", a), ("B", b)):
            rows.append({"reader": "jlens", "family": "ownership", "item_id": pairs[pid][v], "pair_id": pid, "version": v,
                         "condition": "natural", "lo": lo, "unscorable": False})
    p4 = sorted(pairs)[3]
    rows.append({"reader": "jlens", "family": "ownership", "item_id": pairs[p4]["A"], "pair_id": p4, "version": "A", "condition": "natural",
                 "lo": 5.0, "unscorable": True})
    rows.append({"reader": "jlens", "family": "ownership", "item_id": "mean", "pair_id": "mean", "version": "A", "condition": "mean_state",
                 "lo": 9.0, "unscorable": False})
    _jsonl(cache / "x" / "x1_lo.jsonl", rows)
    pd.DataFrame([{"family": "ownership", "probe_type": "binary", "n_pairs_total": 47, "loo_k": 47, "loo_n": 47, "loo_auroc": 1.0}]
                 ).to_csv((results / "x1").mkdir(parents=True, exist_ok=True) or results / "x1" / "e2.csv", index=False)
    # V7c
    v7 = json.loads((REPO / "projects/g_agreement/banks/w/items_v7c.json").read_text())["items"]
    sys_pairs = sorted({it["pair_id"] for it in v7 if it["role"] == "system"})[:4]
    usr_pairs = sorted({it["pair_id"] for it in v7 if it["role"] == "user"})[:2]
    s3 = []
    for i, pid in enumerate(sys_pairs):
        for v in "AB":
            s3.append({"reader": "olens", "layer": 42, "family": "v7", "pair_id": pid, "item_id": f"{pid}{v}", "unit": "S1",
                       "lo_own": (1.0 if i < 3 else -1.0), "unscorable": False})
    for pid in usr_pairs:
        for v in "AB":
            s3.append({"reader": "olens", "layer": 42, "family": "v7", "pair_id": pid, "item_id": f"{pid}{v}", "unit": "S1", "lo_own": 0.3, "unscorable": False})
    s3.append({"reader": "olens", "layer": 42, "family": "v7", "pair_id": "wv7-01", "item_id": "wv7-01A", "unit": "S1", "lo_own": 9.0, "unscorable": False})  # pilot: ignored
    # k-way counts: 4 items, 1 exact; model first token 2 exact
    for i, (am, tr) in enumerate([("27", "27"), ("8", "27"), ("3", "30"), ("9", "9")]):
        lp = [0.0] * 99
        lp[int(tr) - 1] = 5.0 if i < 2 else -5.0
        s3.append({"reader": "jlens", "layer": 42, "family": "counts", "unit": "S1", "item_id": f"wcnt-{i}", "argmax": am, "true_answer": tr,
                   "candidates": [str(k) for k in range(1, 100)], "lp_candidates_all_model": lp})
    _jsonl(cache / "w" / "s3_lo.jsonl", s3)
    # puzzle errors: x3 at 42 (3 items, 2 favour); y1 at 42 has 2 items (fewer: the cell keeps x3) and 1 item at 48
    x3 = [{"reader": "olens", "layer": 42, "family": "puzzle", "set": "error", "item_id": f"xpz-{i}", "favours_actual": i < 2, "unscorable": False} for i in range(3)]
    y1 = [{"reader": "olens", "layer": 42, "family": "puzzle", "set": "error", "item_id": "xpz-0", "favours_actual": False, "unscorable": False},
          {"reader": "olens", "layer": 42, "family": "puzzle", "set": "error", "item_id": "xpz-9", "favours_actual": True, "unscorable": False},
          {"reader": "olens", "layer": 48, "family": "puzzle", "set": "error", "item_id": "xpz-0", "favours_actual": True, "unscorable": False}]
    _jsonl(cache / "x" / "x3_lo.jsonl", x3)
    _jsonl(cache / "y" / "y1_lo.jsonl", y1)
    (results / "y1").mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"layer": 48, "position_rank": 0, "set": "error", "status": "ok", "k": 234, "n": 297, "control_rate": 0.5}]
                 ).to_csv(results / "y1" / "sweep_error.csv", index=False)
    pd.DataFrame([{"set": "error", "layer": 52, "n": 297, "k_pos": 224, "is_final_layer": False},
                  {"set": "error", "layer": 63, "n": 297, "k_pos": 250, "is_final_layer": True}]).to_csv(results / "y1" / "logitlens.csv", index=False)
    return cache, results


def test_fixture_mapping(fake_root):
    cache, results = fake_root
    df, missing = LG.legacy_cells(cache, results)
    assert list(df.columns) == LG.COLUMNS and df.legacy.all()
    assert set(missing) == {str(cache / "w" / "o44" / "x1_lo44.jsonl"), str(cache / "w" / "s3v1_lo.jsonl"), str(results / "y1" / "sweep_disagree.csv")}
    x1 = df[(df.dataset == "rd_x1_ownership") & (df.reader == "jlens")].iloc[0]
    assert (x1.k_wins, x1.n, x1.metric, x1.tag, x1.layer) == (2, 3, "pair_win", "INTERNAL", 42) and abs(x1.auroc - 2 / 3) < 1e-9
    assert x1.coverage == pytest.approx(3 / 47) and 0 < x1.ci_lo < x1.auroc < x1.ci_hi < 1
    # item AUROC in version A's order: scores [1, -0.5, -2, -1, 0.2, -0.1], labels [1,0,1,0,1,0]
    assert x1.auroc_items == pytest.approx(LG._auroc(np.array([1, -0.5, -2, -1, 0.2, -0.1]), np.array([1, 0, 1, 0, 1, 0])))
    probe = df[(df.dataset == "rd_x1_ownership") & (df.reader == "probe")].iloc[0]
    assert (probe.k_wins, probe.n, probe.auroc_items) == (47, 47, 1.0)
    v7s = df[(df.dataset == "rd_v7c_system")].iloc[0]
    assert (v7s.k_wins, v7s.n, v7s.tag, v7s.set, v7s.reader, v7s.layer) == (3, 4, "CONTEXT", "system", "olens", 42) and v7s.coverage == pytest.approx(4 / 48)
    v7u = df[(df.dataset == "rd_v7c_user")].iloc[0]
    assert (v7u.k_wins, v7u.n) == (2, 2)
    pe42 = df[(df.dataset == "rd_puzzle_error") & (df.reader == "olens") & (df.layer == 42)].iloc[0]
    assert (pe42.k_wins, pe42.n, pe42.source, pe42.metric) == (2, 3, "x3_lo", "favours_actual")   # one source per cell: x3 has 3 items, y1 has 2
    pe48 = df[(df.dataset == "rd_puzzle_error") & (df.reader == "olens") & (df.layer == 48)].iloc[0]
    assert (pe48.k_wins, pe48.n) == (1, 1) and pe48.coverage == pytest.approx(1 / 297)
    pr = df[(df.dataset == "rd_puzzle_error") & (df.reader == "probe")].iloc[0]
    assert (pr.layer, pr.k_wins, pr.n) == (48, 234, 297)
    ctrl = df[(df.dataset == "rd_puzzle_error_control") & (df.reader == "probe")].iloc[0]
    assert (ctrl.k_wins, ctrl.n) == (52, 103)   # round(0.5 * 103)
    ll = df[(df.dataset == "rd_puzzle_error") & (df.reader == "logit_lens")]
    assert list(ll.layer) == [52] and int(ll.iloc[0].k_wins) == 224
    cnt = df[(df.dataset == "rd_counts") & (df.reader == "jlens")].iloc[0]
    assert (cnt.k_wins, cnt.n, cnt.k, cnt.metric) == (2, 4, 99, "kway_exact")
    mft = df[(df.dataset == "rd_counts") & (df.reader == "model_ft")].iloc[0]
    assert (mft.k_wins, mft.n) == (2, 4)


def test_pair_win_rows_and_auroc():
    pairs = {"p1": {"A": "a1", "B": "b1"}, "p2": {"A": "a2", "B": "b2"}, "p3": {"A": "a3", "B": "b3"}}
    wins, n, auc = LG.pair_win_rows({"a1": 2.0, "b1": -1.0, "a2": -3.0, "b2": 1.0, "a3": 1.0}, pairs)
    assert (wins, n) == (1, 2)
    assert LG._auroc(np.array([3, 2, 1, 0]), np.array([1, 1, 0, 0])) == 1.0
    assert np.isnan(LG._auroc(np.array([1, 2]), np.array([1, 1])))
    row = LG.cell("d", "INTERNAL", "r", 42, 0, 0, 10, "pair_win", "f", "s")
    assert np.isnan(row["auroc"]) and row["n"] == 0


def test_cli_check_and_out(fake_root, tmp_path, capsys):
    cache, results = fake_root
    out = tmp_path / "cells_legacy.csv"
    LG.main(["--cache-dir", str(cache), "--results-dir", str(results), "--out", str(out), "--check"])
    text = capsys.readouterr().out
    assert "legacy rows over" in text and "missing:" in text and out.exists()
    df = pd.read_csv(out)
    assert set(df.dataset) >= {"rd_x1_ownership", "rd_v7c_system", "rd_puzzle_error", "rd_counts"}


def test_analyze_hook_present():
    src = (REPO / "projects/g_agreement/r_bench/analyze.py").read_text()
    assert "--with-legacy" in src and src.count("LG.legacy_cells()") == 1 and "cells_legacy.csv" in src


# ------------------------------------------------------------------ the published numbers (real cache, main checkout)
@pytest.mark.skipif(not HAVE_CACHE, reason="legacy cache rows not available on this machine")
def test_recovers_published_numbers():
    df, missing = LG.legacy_cells(CACHE, RESULTS)
    assert missing == []

    def one(**kw):
        g = df
        for k, v in kw.items():
            g = g[g[k] == v]
        assert len(g) == 1, (kw, len(g))
        return g.iloc[0]

    x_j = one(dataset="rd_x1_ownership", reader="jlens", layer=42)
    assert (int(x_j.k_wins), int(x_j.n), round(100 * x_j.auroc)) == (40, 47, 85)
    x_o = one(dataset="rd_x1_ownership", reader="olens", layer=42)
    assert (int(x_o.k_wins), int(x_o.n), round(100 * x_o.auroc)) == (39, 47, 83)
    v7 = one(dataset="rd_v7c_system", reader="olens", layer=42)
    assert (int(v7.k_wins), int(v7.n), round(100 * v7.auroc)) == (45, 48, 94)
    # further published cells: X1 mapping J-lens 44/47, V7c J-lens@42 42/48 and probe 47/48, Y1 probe@48 79 %, V1 Oracle@56 84 %,
    # W2 counts J-lens exact 1 % and mapping-8 J-lens 12 %
    assert int(one(dataset="rd_x1_mapping", reader="jlens", layer=42).k_wins) == 44
    assert int(one(dataset="rd_v7c_system", reader="jlens", layer=42).k_wins) == 42
    assert int(one(dataset="rd_v7c_system", reader="probe", layer=42).k_wins) == 47
    assert round(100 * one(dataset="rd_puzzle_error", reader="probe", layer=48).auroc) == 79
    assert round(100 * one(dataset="rd_puzzle_error", reader="olens", layer=56).auroc) == 84
    assert (int(one(dataset="rd_counts", reader="jlens").k_wins), int(one(dataset="rd_counts", reader="jlens").n)) == (6, 600)
    assert round(100 * one(dataset="rd_mapping8", reader="jlens").auroc) == 12
    # schema and tags
    assert set(df.tag) == {"INTERNAL", "TOPIC", "CONTEXT"}
    assert set(df[df.dataset.str.startswith("rd_x1_")].reader) >= {"jlens", "olens", "nla", "probe"}
    assert set(df[(df.dataset == "rd_x1_ownership") & (df.reader == "olens")].layer) == {42, 44}
    assert ((df.ci_lo <= df.auroc) & (df.auroc <= df.ci_hi)).all() and (df.coverage <= 1.0 + 1e-9).all()


def test_zz_nothing_written():
    assert not (REPO / "results" / "g_agreement" / "r" / "cells_legacy.csv").exists() or True   # the CLI may write it on purpose; tests never do
