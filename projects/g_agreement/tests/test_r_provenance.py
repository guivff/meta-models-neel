"""analyze.provenance_filter: pod-D / WS13 rows are dropped and counted; every kept row must be an allowed pod at the
frozen git sha (WS3, 2026-10-18)."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))

from projects.g_agreement.r_bench import analyze as A  # noqa: E402


def _write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def _row(ds, pod="A1", sha=A.FROZEN_GIT_SHA + "abc", key=None):
    return {"dataset": ds, "pod": pod, "git_sha": sha, "key": key or f"{ds}|{pod}", "item_id": "i", "lo": 0.0}


@pytest.fixture(autouse=True)
def _strict():
    A.PROVENANCE.update(strict=True, extra_pods=set(), dropped={}, off_bank={})
    yield
    A.PROVENANCE.update(strict=True, extra_pods=set(), dropped={}, off_bank={})


def test_drops_pod_d_and_ws13_rows(tmp_path):
    _write(tmp_path / "reader_lo.jsonl", [{"dataset": "rf_hometown_fwd@sft", "key": "x", "item_id": "i", "lo": 1.0}])  # no pod / sha
    _write(tmp_path / "reader_lo.D.jsonl", [{"dataset": "rf_hometown_fwd@sft", "key": "y", "item_id": "i", "lo": 1.0}])
    _write(tmp_path / "reader_lo.1.jsonl", [_row("92_glue_sst2"), _row("rf_x@base", key="z"), _row("92_glue_sst2", pod="D", key="w")])
    _write(tmp_path / "reader_lo.B.jsonl", [_row("66_living-room", pod="B")])
    df = A.read_jsonl_shards(tmp_path, "reader_lo")
    assert sorted(df.dataset) == ["66_living-room", "92_glue_sst2"]
    assert A.PROVENANCE["dropped"] == {"reader_lo.jsonl": 1, "reader_lo.D.jsonl": 1, "reader_lo.1.jsonl": 2}


def test_asserts_pod_and_sha(tmp_path):
    _write(tmp_path / "prompt_only.1.jsonl", [_row("92_glue_sst2", pod="Z")])
    with pytest.raises(AssertionError, match="pods"):
        A.read_jsonl_shards(tmp_path, "prompt_only")
    A.PROVENANCE["extra_pods"] = {"Z"}
    assert len(A.read_jsonl_shards(tmp_path, "prompt_only")) == 1
    _write(tmp_path / "prompt_only.2.jsonl", [_row("92_glue_sst2", sha="deadbee", key="k2")])
    with pytest.raises(AssertionError, match="git_sha"):
        A.read_jsonl_shards(tmp_path, "prompt_only")
    _write(tmp_path / "prompt_only.2.jsonl", [{"dataset": "92_glue_sst2", "key": "k3", "item_id": "i"}])  # no pod at all
    with pytest.raises(AssertionError):
        A.read_jsonl_shards(tmp_path, "prompt_only")


def test_ledger_drops_ws13(tmp_path):
    _write(tmp_path / "compute.jsonl", [{"module": "r_bench.collect", "step": "capture", "pod": "A1"},
                                        {"module": "r_bench.planted_facts", "step": "sft"}, {"module": "x", "step": "y", "pod": "D"}])
    df, n = A.phase_r_ledger(tmp_path)
    assert n == 2 and len(df) == 1


def test_partial_last_line_is_skipped_only_at_the_end(tmp_path):
    good = json.dumps(_row("92_glue_sst2"))
    (tmp_path / "a.jsonl").write_text(good + "\n" + good[:40])
    assert len(A.read_jsonl(tmp_path / "a.jsonl")) == 1
    (tmp_path / "b.jsonl").write_text(good[:40] + "\n" + good + "\n")
    with pytest.raises(json.JSONDecodeError):
        A.read_jsonl(tmp_path / "b.jsonl")


def test_unknown_condition_fails(tmp_path):
    A.assert_conditions(A.pd.DataFrame({"condition": ["natural", "shuf", "pool_eval", "state_free"]}), "ok")
    with pytest.raises(AssertionError, match="text"):
        A.assert_conditions(A.pd.DataFrame({"condition": ["natural", "text"]}), "reader_lo")
    with pytest.raises(AssertionError, match="condition column"):
        A.assert_conditions(A.pd.DataFrame({"x": [1]}), "reader_lo")


def test_other_bank_rows_are_set_aside_before_the_condition_check(tmp_path):
    items = A.pd.DataFrame({"dataset": ["92_glue_sst2"]})
    df = A.pd.DataFrame({"dataset": ["92_glue_sst2", "rc2_planted"], "condition": ["natural", "planted"]})
    kept = A._bank_only(df, items, "reader_lo")
    A.assert_conditions(kept, "reader_lo")
    assert len(kept) == 1 and A.PROVENANCE["off_bank"] == {"reader_lo": 1}
    _write(tmp_path / "reader_lo.E.jsonl", [_row("re_count_long", pod="E")])
    _write(tmp_path / "reader_lo.RB.jsonl", [_row("rb_context_earlier_turn", pod="RB")])
    assert len(A.read_jsonl_shards(tmp_path, "reader_lo")) == 2


def test_replication_153_verdict(tmp_path):
    import numpy as np

    from projects.g_agreement.r_bench import interim as I

    ds = I.REP153
    rng = np.random.default_rng(0)
    y = np.r_[np.ones(100, int), np.zeros(100, int)]
    ids = [f"r-{ds}-pool-{i:04d}" for i in range(200)]
    items = A.pd.DataFrame({"item_id": ids, "dataset": ds, "label": y, "sided": "one", "split": "pool"})
    P = A.Paths(tmp_path)
    (P.results / "h2_replication_153.json").write_text(json.dumps({"item_ids": ids}))
    (P.cache / "text_arm").mkdir(parents=True)
    for strong, want in ((2.0, "REPLICATED"), (0.0, "NOT REPLICATED")):
        rows = [{"key": f"o|{i}", "reader": "olens", "layer": 44, "render": "chat", "condition": "natural", "dataset": ds, "item_id": iid,
                 "label": int(l), "lp_A": float(strong * l + rng.normal()), "lo": 0.0, "pod": "REP-d6lq9yaejceqxv", "git_sha": A.FROZEN_GIT_SHA}
                for i, (iid, l) in enumerate(zip(ids, y))]
        _write(P.cache / "text_arm" / "h2_replication_153_lo.jsonl", rows)
        _write(P.cache / "prompt_only.1.jsonl", [{"key": f"p|{iid}", "dataset": ds, "item_id": iid, "label": int(l), "lo": float(rng.normal()),
                                                  "pod": "A1", "git_sha": A.FROZEN_GIT_SHA} for iid, l in zip(ids, y)])
        v, lines = I.replication_153(P, items, n_boot=300)
        assert v == want, (v, lines)


def test_cells_table_checks_conditions_only_when_asked():
    items = A.pd.DataFrame({"dataset": ["d"], "tag": ["T"], "split": ["test"], "item_id": ["i"]})
    lo = A.pd.DataFrame({"dataset": ["d"] * 4, "reader": "r", "layer": 42, "render": "chat", "condition": "rot0", "split": "test",
                         "item_id": list("abcd"), "label": [0, 1, 0, 1], "score": [0.1, 0.9, 0.2, 0.8]})
    assert len(A.cells_table(lo, items, n_boot=20)) == 1                      # r_gemma's rotation readouts
    with pytest.raises(AssertionError, match="rot0"):
        A.cells_table(lo, items, n_boot=20, allowed_conditions=A.MAIN_CONDITIONS)


def test_provenance_filter_without_dataset_column(tmp_path):
    _write(tmp_path / "reader_lo.1.jsonl", [{"key": "k", "item_id": "i", "pod": "A1", "git_sha": A.FROZEN_GIT_SHA}])
    assert len(A.read_jsonl_shards(tmp_path, "reader_lo")) == 1


def test_r1b_clause_and_imbalance_draw():
    import numpy as np

    from projects.g_agreement.r_bench import interim as I
    from projects.g_agreement.r_bench import regimes as RG

    assert I._r1b_clause((0.03, 0.005, 0.06, 0.01, 0.05)) == "SUPPORTED"
    assert I._r1b_clause((0.00, -0.02, 0.015, -0.01, 0.01)) == "REFUTED"
    assert I._r1b_clause((0.02, 0.0, 0.04, 0.012, 0.028)) == "EQUIVALENT-NULL"
    y = np.r_[np.ones(50, int), np.zeros(50, int)]
    tr = RG._draw_pi(np.arange(100), y, 20, 0.10, np.random.default_rng(0))
    assert len(tr) == 20 and y[tr].sum() == 2
    assert RG._seed("a", 1) == RG._seed("a", 1) != RG._seed("a", 2)


def test_label_audit_flags_below_chance(tmp_path):
    from projects.g_agreement.r_bench import label_audit as LA

    P = A.Paths(tmp_path)
    items = [{"item_id": f"i{k}", "dataset": "d1", "tag": "TOPIC", "split": "test", "label": k % 2,
              "primary": {"sided": "two", "candidates": ["a", "b"]}} for k in range(40)]
    (P.dataset).mkdir(parents=True, exist_ok=True)
    (P.dataset / "items_r.json").write_text(json.dumps({"items": items, "meta": {}}))
    po = A.pd.DataFrame([{"item_id": f"i{k}", "dataset": "d1", "label": k % 2, "lo": -(k % 2) + 0.01 * k, "model_says_pos": k % 2 == 0}
                         for k in range(40)])
    d = LA.audit(P, po)
    assert d.loc[d.dataset == "d1", "flagged"].item() is True


def test_analysed_datasets_keyed_on_dataset_dir(tmp_path, monkeypatch):
    real = A.analysed_datasets()
    monkeypatch.setattr(A.C, "DATASET_DIR", tmp_path)          # an empty bank directory: no scoping, not "set everything aside"
    assert A.analysed_datasets() is None
    monkeypatch.undo()
    assert A.analysed_datasets() == real                        # the real bank set is not poisoned by the patched call
