from types import SimpleNamespace
from contextlib import nullcontext

import numpy as np
import pytest

from projects.g_agreement.blindspot import analysis as A
from projects.g_agreement.blindspot import protocol as P


def cell(f, kind, reader="olens", layer=44, auc=.7, probe=.9, mismatch=.1):
    return {"feature": f, "class": kind, "reader": reader, "layer": layer,
            "true": {"auroc": auc}, "mismatched": {"auroc": mismatch},
            "probe_auroc": probe, "status": A.gate(probe, mismatch)}


def table():
    rows = []
    for j in range(4):
        f = f"structural{j}"
        rows += [cell(f, "count-like", auc=.7 if j < 3 else .9),
                 cell(f, "count-like", "nla", 42, auc=.85)]
    rows += [cell(f"semantic{j}", "semantic", auc=.85 if j < 3 else .7) for j in range(4)]
    return rows


def test_registered_gates_use_point_thresholds_inclusive_and_do_not_flip_signs():
    assert A.gate(.85, .60) == "EVALUABLE"
    assert A.gate(.84999, 0) == "NOT DECODABLE"
    assert A.gate(.9, .600001) == "NOT EVALUABLE"
    assert A.gate(.9, 0) == "EVALUABLE"  # opposite-valued donor may invert AUROC
    assert A.gate(.9, None, complete=False) == "NOT EVALUABLE"


def test_replications_keep_fixed_pilot_references_and_report_fresh_gates():
    expected = {"table_column": {"nla": 1., "olens": .67, "jlens": .64},
                "prose_paren": {"nla": .98, "olens": .76, "jlens": .47}}
    assert A.PILOT_REPLICATIONS == expected
    with pytest.raises(TypeError):
        A.PILOT_REPLICATIONS["table_column"]["olens"] = .5
    rows = [cell("table_column", "count-like", auc=.75, mismatch=.7),
            cell("prose_paren", "state-like", "nla", 42, auc=.99)]
    rows[0]["true"].update(lo=.65, hi=.85)
    rows[0].update(n_total=84, n_clusters=6)
    result = A.replication_comparisons(rows)
    assert len(result) == 6
    index = {(r["feature"], r["reader"]): r for r in result}
    oracle = index["table_column", "olens"]
    assert oracle["pilot_auroc"] == .67 and oracle["pilot_status"] == "PILOT_NONCONFIRMATORY"
    assert oracle["pilot_ci95"] is None and oracle["pilot_n"] is None
    assert oracle["fresh_gate_status"] == "NOT EVALUABLE"
    assert oracle["fresh_split"] == "test" and oracle["fresh_ci95"] == [.65, .85]
    assert np.isclose(oracle["fresh_minus_pilot"], .08)
    assert oracle["difference_ci95"] is None
    assert index["prose_paren", "nla"]["fresh_gate_status"] == "EVALUABLE"
    assert index["prose_paren", "jlens"]["fresh_auroc"] is None
    oracle["pilot_auroc"] = .01
    assert A.PILOT_REPLICATIONS == expected


def test_w1_exact_rule_and_conditional_same_rows_denominator():
    result = A.adjudicate_w1(table())
    assert result["status"] == "CONFIRMED"
    assert result["conditions"]["i"]["k"] == 3
    assert result["conditions"]["i"]["n"] == 4
    assert result["conditions"]["ii"]["n"] == 3
    assert result["conditions"]["iii"]["rate"] == .75
    assert len(result["blindspot_features"]) == 3
    changed = table()
    changed[1]["status"] = "NOT EVALUABLE"
    result = A.adjudicate_w1(changed)
    assert result["status"] == "PARTIAL"
    assert result["conditions"]["ii"]["k"] == 2
    assert result["conditions"]["ii"]["n"] == 3
    assert result["nla_exclusions_on_i_rows"] == [{"feature": "structural0", "status": "NOT EVALUABLE"}]
    changed[-2]["true"]["auroc"] = .6
    assert A.adjudicate_w1(changed)["status"] == "NOT MET"


def test_exact_decimal_gap_boundary_is_not_lost_to_binary_rounding():
    rows = [cell("s", "state-like", auc=.80, probe=.95),
            cell("s", "state-like", "nla", 42, auc=.90, probe=.95),
            cell("meaning", "semantic", auc=.90, probe=.95)]
    assert A.adjudicate_w1(rows)["status"] == "CONFIRMED"
    assert A.adjudicate_w1b(rows, ["s"])["status"] == "CONFIRMED"


def test_w1_gated_rows_excluded_from_oracle_denominator_empty_not_evaluable():
    rows = table()
    for row in rows:
        if row["reader"] == "olens" and row["class"] == "count-like":
            row["status"] = "NOT DECODABLE"
    result = A.adjudicate_w1(rows)
    assert result["status"] == "NOT EVALUABLE"
    assert result["conditions"]["i"]["n"] == 0
    assert len(result["oracle_exclusions"]) == 4
    assert "(i) FAIL (0/0, NOT EVALUABLE)" in A._w1_handoff_line(result)


def test_rule_i_export_retains_rows_when_nla_fails_and_overall_is_partial(tmp_path):
    import json
    rows = table()
    rows[1]["status"] = "NOT EVALUABLE"
    data = {"experiment": "W1", "rows": rows, "w1": A.adjudicate_w1(rows),
            "input_seal_sha256": "bank", "reader_seals": ["target", "nla"]}
    out = tmp_path / "analysis"
    A._finish(out, data, [], {}, [], {})
    seal = P.verify(out, "ANALYSIS_SEAL.json")
    assert {"rule_i_rows.json", "HANDOFF.txt"} <= seal["files"].keys()
    selected = json.loads((out / "rule_i_rows.json").read_text())
    assert selected["features"] == ["structural0", "structural1", "structural2"]
    assert [row["feature"] for row in selected["rows"]] == selected["features"]
    assert selected["w1_verdict"] == "PARTIAL"
    assert selected["metrics_sha256"] == P.sha(out / "metrics.json")
    assert (out / "HANDOFF.txt").read_text() == (
        "HANDOFF W1: (i) PASS (3/4); (ii) FAIL (2/3); (iii) PASS (3/4); verdict=PARTIAL.\n")


def test_w5_all_probes_six_layers_and_at_least_five_strict_oracle_threshold():
    rows = [cell(f"f{j}", "state-like", layer=L, auc=.74 if i < 5 else .75, probe=.85)
            for j in range(4) for i, L in enumerate(A.LAYERS)]
    assert A.adjudicate_w5(rows, [f"f{j}" for j in range(4)])["status"] == "CONFIRMED"
    rows[0]["probe_auroc"] = .849
    result = A.adjudicate_w5(rows, [f"f{j}" for j in range(4)])
    assert result["rate"]["k"] == 3 and result["status"] == "CONFIRMED"
    rows[6]["true"]["auroc"] = .75
    assert A.adjudicate_w5(rows, [f"f{j}" for j in range(4)])["status"] == "NOT MET"
    assert A.adjudicate_w5([], [])["status"] == "NOT EVALUABLE"


def test_w5_missing_data_give_bounds_instead_of_scientific_failure():
    rows = [cell("f", "count-like", layer=L, auc=.7, probe=.9) for L in A.LAYERS]
    rows[0]["status"] = rows[1]["status"] = "NOT EVALUABLE"
    result = A.adjudicate_w5(rows, ["f"])
    assert result["status"] == "NOT EVALUABLE"
    assert result["possible_fraction_bounds"] == [0., 1.]
    rows[1]["status"] = "EVALUABLE"  # five valid weak layers suffice
    assert A.adjudicate_w5(rows, ["f"])["status"] == "CONFIRMED"
    rows[2]["true"]["auroc"] = rows[3]["true"]["auroc"] = .8
    assert A.adjudicate_w5(rows, ["f"])["status"] == "NOT MET"


def test_w1b_uses_whole_frozen_selection_including_gate_failures():
    rows = [cell(f"f{j}", "count-like", reader=reader, layer=layer, auc=.7 if reader == "olens" else .85)
            for j in range(10) for reader, layer in (("olens", 44), ("nla", 42))]
    for j in range(3):
        rows[j * 2 + 1]["status"] = "NOT EVALUABLE"
    result = A.adjudicate_w1b(rows, [f"f{j}" for j in range(10)])
    assert result["rate"]["k"] == 7 and result["rate"]["n"] == 10
    assert result["status"] == "CONFIRMED"
    rows[7]["status"] = "NOT EVALUABLE"
    assert A.adjudicate_w1b(rows, [f"f{j}" for j in range(10)])["status"] == "NOT MET"
    with pytest.raises(ValueError, match="committed list"):
        A.adjudicate_w1b(rows, ["f0", "f0"])


def test_w1b_receipt_requires_distinct_committed_new_candidates():
    receipt = {"source_commit": "a" * 40, "selection_file": "results/screen.json", "selection_sha256": "b" * 64,
               "section79_features": ["novel"], "section81_features": ["latent"]}
    assert A.validate_selection_receipt(receipt, {"known"}) == receipt
    with pytest.raises(ValueError, match="exclude W1"):
        A.validate_selection_receipt(receipt, {"novel"})
    with pytest.raises(ValueError, match="overlapping"):
        A.validate_selection_receipt({**receipt, "section81_features": ["novel"]}, set())
    with pytest.raises(ValueError, match="source_commit"):
        A.validate_selection_receipt({**receipt, "source_commit": "main"}, set())


def test_grouped_probe_keeps_entire_templates_and_exports_a_positive_direction():
    groups = np.repeat(np.arange(6).astype(str), 10)
    y = np.tile([1, 0], 30)
    h = np.column_stack([2 * y - 1, np.repeat(np.arange(6) * 10, 10)]).astype(np.float32)
    donors = np.arange(60).reshape(-1, 2)[:, ::-1].reshape(-1)
    score, mis, folds = A.grouped_probe(h, y, groups, donors)
    from mats.metrics import auroc_labels
    assert auroc_labels(score, y) == 1
    assert auroc_labels(mis, y) == 0
    for fold in folds:
        assert not set(fold["train_clusters"]) & set(fold["test_clusters"])
    d = A.fit_direction(h, y)
    assert d["fit_split"] == "dev" and not d["orientation_flipped"]
    assert np.isclose(np.linalg.norm(d["direction"]), 1)
    assert d["dev_class_mean_projection_gap"] > 0
    raw_scores = h @ d["raw_coefficient"] + d["raw_intercept"]
    assert auroc_labels(raw_scores, y) == 1
    import torch
    from mats.probes import fit_logreg
    original = fit_logreg(torch.from_numpy(h), torch.as_tensor(y), lam=1e-3)
    assert np.allclose(raw_scores, original.decision(torch.from_numpy(h)).numpy(), atol=1e-5)
    with pytest.raises(ValueError, match="boundaries"):
        A.grouped_probe(h, y, groups, np.roll(donors, 10))


def test_reader_grid_rejects_missing_or_single_phrasing_before_usable_analysis():
    items = [{"id": "a", "feature": "f"}]
    specs = {"f": {"kind": "binary", "olens": [["A", "B"], ["a", "b"]]}}
    raw = [{"id": "a", "reader": "olens", "layer": 44, "arm": arm,
            "scores": [0., 1.], "status": "COMPLETE"} for arm in ("true", "mismatched")]
    assert len(A._grid(raw, items, specs, [("olens", 44)])) == 2
    with pytest.raises(ValueError, match="score grid"):
        A._grid(raw[:1], items, specs, [("olens", 44)])
    raw[0]["scores"] = [1.]
    with pytest.raises(ValueError, match="phrasing count"):
        A._grid(raw, items, specs, [("olens", 44)])
    for malformed in ([0., 1., 2.], [[0., 1.], [2., 3.]]):
        raw[0]["scores"] = malformed
        with pytest.raises(ValueError, match="phrasing count"):
            A._grid(raw, items, specs, [("olens", 44)])


def test_scores_must_be_verified_before_label_file_is_read(tmp_path, monkeypatch):
    bank, target, nla = (tmp_path / n for n in ("bank", "target", "nla"))
    for p in (bank, target, nla):
        p.mkdir()
    P.jsonl(bank / "items.input.jsonl", [])
    P.dump(bank / "templates.json", {})
    P.dump(bank / "provenance.json", {})
    P.seal(bank, ["items.input.jsonl", "templates.json", "provenance.json"], "INPUTS_FROZEN")
    P.dump(target / "SCORE_SEAL.json", {"status": "SCORES_SEALED", "files": {}})
    labels = tmp_path / "unreadable-labels.jsonl"
    opened = []
    original = type(labels).read_text
    def guard(path, *args, **kwargs):
        opened.append(str(path))
        if path == labels:
            pytest.fail("labels read before score-seal verification")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(type(labels), "read_text", guard)
    args = SimpleNamespace(bank=bank, target=target, nla=nla, labels=labels, out=tmp_path / "out")
    with pytest.raises(ValueError, match="required file coverage"):
        A.analyse(args)
    assert str(labels) not in opened


def synthetic_sealed_run(tmp_path):
    """Small fabricated fixture, only for pipeline testing; never scientific data."""
    bank, target, nla = (tmp_path / n for n in ("bank", "target", "nla"))
    for path in (bank, target, nla):
        path.mkdir()
    items, labels, y = [], [], []
    specs = {}
    for feature, kind in (("structural", "count-like"), ("semantic", "semantic")):
        specs[feature] = {"class": kind, "domain": "fixture", "kind": "binary", "values": ["A", "B"]}
        specs[feature].update({reader: [["A", "B"], ["a", "b"]] for reader, _ in A.NATIVE})
        for cluster in range(12):
            for side in range(2):
                key, donor = f"{feature}-{cluster}-{side}", f"{feature}-{cluster}-{1-side}"
                items.append({"id": key, "feature": feature, "ids": [42, 43], "donor_id": donor})
                labels.append({"id": key, "feature": feature, "class": kind, "domain": "fixture",
                               "split": "dev" if cluster < 6 else "test", "value": "AB"[side], "cluster": str(cluster)})
                y.append(1 - side)
    h = np.column_stack([2 * np.array(y) - 1, np.zeros(len(y))]).astype(np.float32)
    P.jsonl(bank / "items.input.jsonl", items)
    P.jsonl(bank / "labels.DO_NOT_STAGE.jsonl", labels)
    P.dump(bank / "templates.json", specs)
    P.dump(bank / "provenance.json", {"labels_sha256": P.sha(bank / "labels.DO_NOT_STAGE.jsonl")})
    test_ids = [row["id"] for row in labels if row["split"] == "test"]
    P.dump(bank / "sweep.input.json", test_ids)
    P.seal(bank, ["items.input.jsonl", "templates.json", "provenance.json", "sweep.input.json"], "INPUTS_FROZEN")
    target_rows, nla_rows = [], []
    for j, it in enumerate(items):
        for reader, layer in A.NATIVE:
            for arm in ("true", "mismatched"):
                value = 0. if it["feature"] == "structural" and reader == "olens" else float(h[j, 0])
                value *= 1 if arm == "true" else -1
                row = {"id": it["id"], "reader": reader, "layer": layer, "arm": arm, "scores": [value, value], "status": "COMPLETE"}
                (nla_rows if reader == "nla" else target_rows).append(row)
    P.jsonl(target / "scores.target.jsonl", target_rows)
    P.dump(target / "items.order.json", [it["id"] for it in items])
    for layer in (42, 44):
        np.save(target / f"acts{layer}.npy", h)
    P.dump(target / "provenance.target.json", {"input_seal_sha256": P.sha(bank / "INPUT_SEAL.json")})
    P.seal(target, ["scores.target.jsonl", "items.order.json", "acts42.npy", "acts44.npy", "provenance.target.json"], "SCORES_SEALED_TARGET")
    P.jsonl(nla / "scores.nla.jsonl", nla_rows)
    P.dump(nla / "provenance.nla.json", {"input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"), "target_score_seal_sha256": P.sha(target / "SCORE_SEAL.json")})
    P.seal(nla, ["scores.nla.jsonl", "provenance.nla.json"], "SCORES_SEALED_NLA")
    return SimpleNamespace(bank=bank, target=target, nla=nla, labels=bank / "labels.DO_NOT_STAGE.jsonl", out=tmp_path / "analysis")


def test_w1_and_w5_sealed_pipeline_on_synthetic_fixture(tmp_path, monkeypatch, capsys):
    args = synthetic_sealed_run(tmp_path)
    monkeypatch.setattr(A, "N_BOOT", 12)  # speed-only test; production is frozen at 2000
    monkeypatch.setattr(P, "logged", lambda *args, **kwargs: nullcontext())
    result = A.analyse(args)
    assert result["w1"]["status"] == "CONFIRMED"
    assert result["unasked_recall"]["rate"] is None
    P.verify(args.out, "ANALYSIS_SEAL.json")
    import json
    assert capsys.readouterr().out == (args.out / "HANDOFF.txt").read_text()
    selected = json.loads((args.out / "rule_i_rows.json").read_text())
    assert selected["features"] == ["structural"] == result["w1"]["blindspot_features"]
    directions = json.loads((args.out / "probe_directions.json").read_text())
    assert len(directions["rows"]) == 4
    assert all(r["dev_n"] == 12 and r["fit_split"] == "dev" for r in directions["rows"])
    assert all(r["test_class_mean_projection_gap"] > 0 for r in directions["rows"])
    sweep = tmp_path / "sweep"
    sweep.mkdir()
    ids = json.loads((args.bank / "sweep.input.json").read_text())
    full_ids = json.loads((args.target / "items.order.json").read_text())
    idx = [full_ids.index(key) for key in ids]
    P.dump(sweep / "items.order.json", ids)
    for layer in A.LAYERS:
        np.save(sweep / f"acts{layer}.npy", np.load(args.target / "acts44.npy")[idx])
    P.jsonl(sweep / "scores.sweep.jsonl", [{"id": key, "reader": "olens", "layer": layer,
        "arm": arm, "scores": [0., 0.], "status": "COMPLETE"} for key in ids for layer in A.LAYERS for arm in ("true", "mismatched")])
    P.dump(sweep / "provenance.sweep.json", {"input_seal_sha256": P.sha(args.bank / "INPUT_SEAL.json")})
    P.seal(sweep, ["scores.sweep.jsonl", "items.order.json", "provenance.sweep.json"] + [f"acts{L}.npy" for L in A.LAYERS], "SCORES_SEALED_SWEEP")
    result = A.analyse_sweep(SimpleNamespace(bank=args.bank, sweep=sweep, labels=args.labels, w1=args.out, out=tmp_path / "sweep-analysis"))
    assert result["w5"]["status"] == "CONFIRMED"
    assert result["w5"]["rate"]["n"] == 1
    P.dump(args.out / "ANALYSIS_SEAL.json", {"status": "ANALYSIS_SEALED_AFTER_SCORE_VERIFICATION", "files": {}})
    with pytest.raises(ValueError, match="selected blindspot metrics"):
        A.analyse_sweep(SimpleNamespace(bank=args.bank, sweep=sweep, labels=args.labels, w1=args.out, out=tmp_path / "invalid-sweep-analysis"))


def test_complete_seals_with_missing_grid_still_fail_before_labels(tmp_path, monkeypatch):
    args = synthetic_sealed_run(tmp_path)
    rows = P.rows(args.nla / "scores.nla.jsonl")
    (args.nla / "scores.nla.jsonl").unlink()
    P.jsonl(args.nla / "scores.nla.jsonl", rows[:-1])
    P.seal(args.nla, ["scores.nla.jsonl", "provenance.nla.json"], "SCORES_SEALED_NLA")
    original = type(args.labels).read_text
    def guard(path, *pos, **kw):
        if path == args.labels:
            pytest.fail("labels opened before completeness check")
        return original(path, *pos, **kw)
    monkeypatch.setattr(type(args.labels), "read_text", guard)
    with pytest.raises(ValueError, match="incomplete/duplicate score grid"):
        A.analyse(args)
