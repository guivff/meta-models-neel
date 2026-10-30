"""Synthetic CPU checks of the separately registered W4 aggregation rule."""
from copy import deepcopy
import json

import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot.w4_aggregate import aggregate_swap_scores, main


def per_row(blind_met=7, blind_n=10, semantic_met=7, semantic_n=10):
    rows = []
    for group, n_met, n in (("blind", blind_met, blind_n),
                            ("semantic", semantic_met, semantic_n)):
        for i in range(n):
            rows.append({
                "feature": f"{group}:{i}",
                "row_class": "semantic" if group == "semantic" else (
                    "count-like" if i % 2 == 0 else "state-like"),
                "rule_met": i < n_met,
                "n_pairs": 40,
                "arms": {"swap": {}, "self": {}, "random": {}, "ar_only": {}},
                "contrasts": {"synthetic": "retained"},
            })
    return {"rows": rows, "status": "PER_ROW_RULES_REPORTED",
            "aggregation_note": "superseded per-row-only note",
            "all_tested_rows_meet_rule": all(r["rule_met"] for r in rows),
            "site": "OFF-NATIVE", "construction_block": 44, "nla_native_block": 42,
            "inference_scope": "EXPLORATORY", "score_seal_sha256": "synthetic-seal"}


def test_inclusive_seventy_percent_in_both_groups_preserves_results():
    source = per_row()
    before = deepcopy(source)
    result = aggregate_swap_scores(source)
    assert result["status"] == "CONFIRMED"
    assert result["per_row_status"] == "PER_ROW_RULES_REPORTED"
    for group in ("blindspot", "semantic"):
        assert result["aggregation"][group] == {
            "n": 10, "n_met": 7, "fraction": .7, "rule_met": True,
        }
    for key in ("rows", "site", "construction_block", "nla_native_block",
                "inference_scope", "score_seal_sha256", "all_tested_rows_meet_rule"):
        assert result[key] == source[key]
    assert source == before
    result["rows"][0]["contrasts"]["synthetic"] = "changed copy"
    assert source == before


@pytest.mark.parametrize("blind,semantic", [(9, 6), (6, 9)])
def test_pooled_success_cannot_hide_a_failing_group(blind, semantic):
    assert (blind + semantic) / 20 > .7
    result = aggregate_swap_scores(per_row(blind_met=blind, semantic_met=semantic))
    assert result["status"] == "NOT MET"


@pytest.mark.parametrize("n_met,n,expected", [(2, 3, "NOT MET"), (3, 4, "CONFIRMED"),
                                           (69, 100, "NOT MET"), (70, 100, "CONFIRMED")])
def test_exact_fraction_without_rounding(n_met, n, expected):
    assert aggregate_swap_scores(per_row(n_met, n, n_met, n))["status"] == expected


@pytest.mark.parametrize("blind_n,semantic_n", [(0, 10), (10, 0), (0, 0)])
def test_absent_group_is_not_met(blind_n, semantic_n):
    result = aggregate_swap_scores(per_row(blind_n, blind_n, semantic_n, semantic_n))
    assert result["status"] == "NOT MET"
    for group, n in (("blindspot", blind_n), ("semantic", semantic_n)):
        if n == 0:
            assert result["aggregation"][group] == {
                "n": 0, "n_met": 0, "fraction": None, "rule_met": False,
            }


def test_every_tested_row_has_equal_weight_including_failures():
    source = per_row(3, 4, 3, 4)
    for row in source["rows"]:
        row["n_pairs"] = 1 if row["rule_met"] else 10000
    result = aggregate_swap_scores(source)
    assert result["status"] == "CONFIRMED"
    assert result["aggregation"]["blindspot"]["n"] == 4
    assert result["aggregation"]["semantic"]["n_met"] == 3


@pytest.mark.parametrize("bad_flag", [None, "true", "false", 0, 1])
def test_missing_or_nonboolean_rule_met_is_rejected(bad_flag):
    source = per_row()
    if bad_flag is None:
        del source["rows"][0]["rule_met"]
    else:
        source["rows"][0]["rule_met"] = bad_flag
    with pytest.raises(ValueError, match="boolean rule_met"):
        aggregate_swap_scores(source)


@pytest.mark.parametrize("bad_input", [None, [], {}, {"rows": {}}, {"rows": [None]},
                                       {"rows": [{"feature": "", "rule_met": True}]}])
def test_malformed_input_is_not_silently_excluded(bad_input):
    with pytest.raises(ValueError):
        aggregate_swap_scores(bad_input)


def test_duplicate_feature_and_unknown_class_are_rejected():
    source = per_row()
    source["rows"].append(deepcopy(source["rows"][0]))
    with pytest.raises(ValueError, match="unique"):
        aggregate_swap_scores(source)
    source = per_row()
    source["rows"][0]["row_class"] = "unknown"
    with pytest.raises(ValueError, match="row_class"):
        aggregate_swap_scores(source)


def test_cli_keeps_input_unchanged_and_seals_logged_output(tmp_path):
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    source = analysis / "metrics.swap.json"
    P.dump(source, per_row())
    P.seal(analysis, [source.name], "SCORES_SEALED_ANALYSIS_SWAP")
    before = source.read_bytes()
    out = tmp_path / "aggregate"
    args = ["--input", str(source), "--out", str(out)]
    main(args)
    result = json.loads((out / "metrics.swap_aggregate.json").read_text())
    assert result == aggregate_swap_scores(json.loads(before))
    assert source.read_bytes() == before
    provenance = json.loads((out / "provenance.json").read_text())
    assert provenance["input_sha256"] == P.sha(source)
    assert provenance["input_score_seal_sha256"] == P.sha(analysis / "SCORE_SEAL.json")
    run = json.loads((out / "run.json").read_text())
    assert run["status"] == "COMPLETE" and run["gpu_hours"] == run["model_forwards"] == 0
    assert run["seed"] == P.SEED and run["wall_s"] >= 0
    assert set(P.verify(out, "SCORE_SEAL.json")["files"]) == {
        "metrics.swap_aggregate.json", "provenance.json", "run.json",
    }
    with pytest.raises(FileExistsError):
        main(args)


def test_cli_rejects_changed_or_uncovered_sealed_input(tmp_path):
    source = tmp_path / "metrics.swap.json"
    P.dump(source, per_row())
    P.seal(tmp_path, [source.name], "SCORES_SEALED_ANALYSIS_SWAP")
    P.dump(source, per_row(blind_met=6))
    args = ["--input", str(source), "--out", str(tmp_path / "out")]
    with pytest.raises(ValueError, match="seal mismatch"):
        main(args)
    P.seal(tmp_path, [], "SCORES_SEALED_ANALYSIS_SWAP")
    with pytest.raises(ValueError, match="not covered"):
        main(args)
    assert not (tmp_path / "out").exists()


def test_cli_refuses_missing_upstream_analysis_seal(tmp_path):
    source = tmp_path / "metrics.swap.json"
    P.dump(source, per_row())
    with pytest.raises(ValueError, match="SCORE_SEAL.json is required"):
        main(["--input", str(source), "--out", str(tmp_path / "out")])
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("status", ["SCORES_SEALED_SWAP_BEFORE_LABEL_JOIN", "SCORES_SEALED_TEST", None])
def test_cli_refuses_other_or_missing_analysis_seal_status(tmp_path, status):
    source = tmp_path / "metrics.swap.json"
    P.dump(source, per_row())
    P.dump(tmp_path / "SCORE_SEAL.json", {"status": status, "files": {source.name: P.sha(source)}})
    with pytest.raises(ValueError, match="status SCORES_SEALED_ANALYSIS_SWAP"):
        main(["--input", str(source), "--out", str(tmp_path / "out")])
    assert not (tmp_path / "out").exists()
