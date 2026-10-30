"""Synthetic CPU W7 contracts; no target model or GPU results."""
from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot import w7_steering as W


def test_random_controls_match_probe_norm_and_are_frozen():
    probe = np.array([2., -3., 1., 7.])
    random = W.random_vectors(probe)
    assert random.shape == (5, 4)
    np.testing.assert_allclose(np.linalg.norm(random, axis=1), np.linalg.norm(probe), rtol=1e-6)
    np.testing.assert_array_equal(random, W.random_vectors(probe))
    assert not np.allclose(random, W.random_vectors(probe, seed=12))


def test_dose_maximum_requires_all_three_doses_both_signs_and_every_control_safe():
    ratios = np.ones((9, 6, 2))
    assert W.choose_doses(W.MULTIPLIERS, ratios) == [2., 4., 8.]
    ratios[-1, 5, 0] = 1.100001
    assert W.choose_doses(W.MULTIPLIERS, ratios) == [1., 2., 4.]
    ratios[-2, 0, 1] = 1.11
    assert W.choose_doses(W.MULTIPLIERS, ratios) == [.5, 1., 2.]
    ratios[:] = 1.11
    with pytest.raises(ValueError, match="no three doses"):
        W.choose_doses(W.MULTIPLIERS, ratios)


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0., -1.])
def test_bad_ppl_calibration_is_rejected(bad):
    ratios = np.ones((9, 6, 2)); ratios[0, 0, 0] = bad
    with pytest.raises(ValueError, match="calibration grid"):
        W.choose_doses(W.MULTIPLIERS, ratios)


def scores_fixture(failing=None):
    scores, calibration = [], {}
    for f, spec in W.FEATURES.items():
        ratios = np.ones((9, 6, 2)); ratios[np.asarray(W.MULTIPLIERS) > 1] = 1.2
        calibration[f] = {"doses": [.25, .5, 1.], "multipliers": W.MULTIPLIERS, "ppl_ratios": ratios.tolist()}
        for i in range(60):
            base = {"id": f"{f}:{i}", "feature": f, "cluster": f"template:{i//10}"}
            scores.append({**base, "arm": "baseline", "dose": 0., "sign": 0, "logp": -3.})
            for dose in calibration[f]["doses"]:
                for arm in ("probe", *[f"random:{j}" for j in range(1, 6)]):
                    effect = (.4 if f != failing else -.4) if arm == "probe" else .02
                    for sign in (-1, 1):
                        scores.append({**base, "arm": arm, "dose": dose, "sign": sign,
                            "logp": -3. + sign * spec["predicted_sign"] * dose * effect})
    return scores, calibration


def test_registered_cluster_contrast_requires_both_rows_in_predicted_direction():
    scores, calibration = scores_fixture()
    result = W.analyse_scores(scores, calibration)
    assert result["status"] == "CONFIRMED"
    for row in result["rows"]:
        assert row["n"] == 60 and row["rule_met"]
        assert row["effect"] == pytest.approx(.38 * np.mean([.25, .5, 1.]))
        assert row["ci95"][0] > 0
    scores, calibration = scores_fixture(failing="table_column")
    result = W.analyse_scores(scores, calibration)
    assert result["status"] == "NOT MET"
    assert {r["feature"]: r["rule_met"] for r in result["rows"]} == {"prose_paren": True, "table_column": False}


@pytest.mark.parametrize("corruption", ["missing", "duplicate", "nan", "cluster", "ppl"])
def test_analysis_refuses_corrupt_or_unqualified_science_grid(corruption):
    scores, calibration = scores_fixture()
    if corruption == "missing": scores.pop()
    elif corruption == "duplicate": scores.append(dict(scores[-1]))
    elif corruption == "nan": scores[-1]["logp"] = float("nan")
    elif corruption == "cluster": scores[-1]["cluster"] = "different"
    else: calibration["prose_paren"]["ppl_ratios"][-1][0][0] = 1.
    if corruption == "ppl":
        calibration["prose_paren"]["doses"] = [2., 4., 8.]
    with pytest.raises(ValueError):
        W.analyse_scores(scores, calibration)


class ToyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.config = SimpleNamespace(num_hidden_layers=45)
        self.layers = torch.nn.ModuleList([torch.nn.Identity() for _ in range(45)])
        self.embedding = torch.nn.Embedding(5, 3)
        self.embedding.weight.data[:] = torch.tensor([1., .5, -.5])
        self.head = torch.nn.Linear(3, 5, bias=False)
        self.head.weight.data[:] = torch.tensor([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.], [-1., 0., 0.], [0., 0., 0.]])

    def forward(self, input_ids, attention_mask, **kwargs):
        h = self.embedding(input_ids)
        for block in self.layers: h = block(h)
        return SimpleNamespace(logits=self.head(h))


def test_real_vendored_hook_adds_raw_vector_at_block44_last_real_token():
    model = ToyModel()
    seqs = [[1, 2], [1, 2, 3]]
    vector = np.array([2., -1., .5], np.float32)
    actual = W.token_logp(model, seqs, 0, vector, .5, batch=1)
    edited = torch.tensor([1., .5, -.5]) + .5 * torch.tensor(vector)
    expected = torch.log_softmax(model.head(edited), -1)[0].item()
    np.testing.assert_allclose(actual, expected, rtol=1e-6)
    assert not model.layers[44]._forward_hooks
    baseline = W.token_logp(model, seqs, 0, batch=2)
    assert np.all(actual > baseline)


def test_unrelated_ppl_uses_teacher_forced_tokens_not_feature_outcomes():
    model = ToyModel()
    seqs = [[0, 1, 2, 3], [1, 2, 3, 4]]
    lp = torch.log_softmax(model.head(torch.tensor([1., .5, -.5])), -1).detach()
    expected = -torch.tensor([lp[t] for seq in seqs for t in seq[1:]]).mean().item()
    assert W.text_nll(model, seqs, batch=1) == pytest.approx(expected)
    assert not model.layers[44]._forward_hooks


def prepare_fixture(tmp_path):
    bank, priority = tmp_path / "bank", tmp_path / "priority"
    bank.mkdir(); priority.mkdir()
    items, labels, rows, arrays = [], [], [], {}
    for f, spec in W.FEATURES.items():
        for i in range(30):
            for side in (0, 1):
                iid, donor = f"{f}:{i}:{side}", f"{f}:{i}:{1-side}"
                items.append({"id": iid, "feature": f, "donor_id": donor, "ids": [1, 2]})
                labels.append({"id": iid, "feature": f, "split": "test", "value": spec["positive_value"] if side == 0 else "other", "cluster": f"c:{i//5}"})
        rows.append({"feature": f, "layer": 44, "fit_split": "dev", "positive_value": spec["positive_value"],
                     "orientation_flipped": False, "array_prefix": f, "dev_class_mean_projection_gap": 2.})
        arrays[f + "__unit"] = np.array([1., 0., 0.])
    label_file = tmp_path / "labels.DO_NOT_STAGE.jsonl"
    P.jsonl(label_file, labels); P.jsonl(bank / "items.input.jsonl", items)
    P.dump(bank / "provenance.json", {"labels_sha256": P.sha(label_file)})
    P.seal(bank, ["items.input.jsonl", "provenance.json"], "INPUTS_FROZEN_SYNTHETIC")
    P.dump(priority / "probe_directions.json", {"fit_split": "dev", "rows": rows})
    np.savez(priority / "probe_directions.npz", **arrays)
    P.dump(priority / "provenance.json", {"input_seal_sha256": P.sha(bank / "INPUT_SEAL.json"), "direction_space": "raw_block44"})
    P.seal(priority, ["probe_directions.json", "probe_directions.npz", "provenance.json"], "INPUTS_FROZEN_SYNTHETIC")
    unrelated = tmp_path / "unrelated.jsonl"
    P.jsonl(unrelated, [{"id": f"neutral:{i}", "ids": [1] * 70} for i in range(20)])
    return SimpleNamespace(bank=bank, labels=label_file, priority=priority, priority_seal="INPUT_SEAL.json", unrelated=unrelated, out=tmp_path / "bundle")


def test_preparation_freezes_sixty_items_per_row_and_no_values_on_worker(tmp_path):
    a = prepare_fixture(tmp_path); W.prepare(a)
    P.verify(a.out, "INPUT_SEAL.json")
    items = P.rows(a.out / "items.input.jsonl")
    assert len(items) == len({r["id"] for r in items}) == 120
    assert all("value" not in r and "split" not in r for r in items)
    assert len(P.rows(a.out / "unrelated.input.jsonl")) == 16
    with np.load(a.out / "directions.npz", allow_pickle=False) as z:
        assert set(z.files) == set(W.FEATURES)
        for x in z.values(): np.testing.assert_allclose(np.linalg.norm(x, axis=1), 2., rtol=1e-6)


def test_complete_worker_seals_doses_before_outcomes_and_all_five_controls(tmp_path, monkeypatch):
    """Exercise the worker orchestration with inert CPU loaders and numeric doubles."""
    import importlib
    from transformers import AutoModelForCausalLM, AutoTokenizer
    a = prepare_fixture(tmp_path); W.prepare(a)
    assignment = tmp_path / "assignment.json"
    P.dump(assignment, {"input_seal_sha256": P.sha(a.out / "INPUT_SEAL.json"), "manifest_committed": True})
    assets = tmp_path / "assets.json"
    monkeypatch.setattr(importlib.import_module("projects.g_agreement.blindspot.run"), "_assets",
                        lambda path, names: {"model": "CPU-DOUBLE-NOT-WEIGHTS"})
    model = SimpleNamespace(); model.eval = lambda: model
    tokenizer = SimpleNamespace(encode=lambda text, **kw: [1 if text == ")" else 2])
    monkeypatch.setattr(AutoModelForCausalLM, "from_pretrained", lambda *a, **kw: model)
    monkeypatch.setattr(AutoTokenizer, "from_pretrained", lambda *a, **kw: tokenizer)
    monkeypatch.setattr(W, "compute", lambda path: nullcontext({"deadline_epoch": W.time.time()+1000}))
    output = tmp_path / "scores"
    target_calls = []
    def nll(*args, **kwargs):
        assert not target_calls, "PPL calibration must precede any target outcomes"
        return 2.
    def logp(model, seqs, token, vector=None, dose=0, batch=4):
        assert (output / "INPUT_SEAL.json").is_file()
        P.verify(output, "INPUT_SEAL.json")
        target_calls.append((token, dose))
        coefficient = 0. if vector is None else float(vector[0])
        return np.full(len(seqs), -4. + (1 if token == 1 else -1) * coefficient * dose * .05)
    monkeypatch.setattr(W, "text_nll", nll)
    monkeypatch.setattr(W, "token_logp", logp)
    W.run(SimpleNamespace(bundle=a.out, assets=assets, assignment=assignment, out=output, batch=4))
    seal = P.verify(output, "SCORE_SEAL.json")
    assert {"scores.w7.jsonl", "calibration.json", "forecast.json", "provenance.json"} == set(seal["files"])
    scores = P.rows(output / "scores.w7.jsonl")
    assert len(scores) == 2 * 60 * 37
    assert len(target_calls) == 2 * 37
    calibration = W.read(output / "calibration.json")["rows"]
    assert all(r["doses"] == [2., 4., 8.] for r in calibration.values())
    assert W.analyse_scores(scores, calibration)["status"] == "CONFIRMED"


@pytest.mark.parametrize("corruption", ["test_means", "fit_split", "sign", "bank"])
def test_priority_direction_provenance_must_be_dev_only_and_same_bank(tmp_path, corruption):
    a = prepare_fixture(tmp_path)
    path = a.priority / "probe_directions.json"; meta = W.read(path)
    if corruption == "test_means": meta["rows"][0]["test_class_mean_projection_gap"] = 2.
    elif corruption == "fit_split": meta["fit_split"] = "test"
    elif corruption == "sign": meta["rows"][0]["orientation_flipped"] = True
    else: P.dump(a.priority / "provenance.json", {"input_seal_sha256": "wrong"})
    P.dump(path, meta)
    P.seal(a.priority, ["probe_directions.json", "probe_directions.npz", "provenance.json"], "INPUTS_FROZEN_SYNTHETIC")
    with pytest.raises(ValueError): W.prepare(a)
    assert not a.out.exists()


def assignment_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "ROOT", tmp_path)
    brief = tmp_path / P.BRIEF; brief.parent.mkdir(parents=True); brief.write_text("synthetic brief")
    monkeypatch.setenv("RUNPOD_POD_ID", "synthetic-pod")
    monkeypatch.setattr(W, "source_hashes", lambda: {"synthetic": "source"})
    monkeypatch.setattr(W.time, "time", lambda: 1000.)
    monkeypatch.setattr(P, "logged", lambda *a, **kw: nullcontext())
    monkeypatch.setattr(P, "compute_window", lambda *a, **kw: nullcontext())
    record = {"issuer": "integrator", "pod_id": "synthetic-pod", "experiment": "W7", "mechanism_budget": "w7",
        "gpu_count": 1, "brief_registered": True, "brief_pushed": True, "external_hardstop_verified": True,
        "brief_sha256": P.sha(brief), "source_files": W.source_hashes(), "source_commit": "a"*40,
        "brief_commit": "b"*40, "provider_created_epoch": 990., "deadline_epoch": 1800.,
        "allocated_gpu_seconds": 900., "previous_gpu_seconds": 0., "smoke_forecast_seconds": 720.}
    return tmp_path / "assignment.json", record


def test_w7_exact_assignment_admits_without_consuming_gpu(tmp_path, monkeypatch):
    path, record = assignment_fixture(tmp_path, monkeypatch); P.dump(path, record)
    with W.compute(path) as accepted: assert accepted == record


@pytest.mark.parametrize("field,value", [("gpu_count", 2), ("experiment", "W1"), ("pod_id", "wrong"),
    ("external_hardstop_verified", False), ("allocated_gpu_seconds", 1081.), ("previous_gpu_seconds", 181.),
    ("deadline_epoch", 1179.), ("source_files", {}), ("source_commit", "uncommitted")])
def test_bad_assignment_is_rejected_before_model_work(tmp_path, monkeypatch, field, value):
    path, record = assignment_fixture(tmp_path, monkeypatch); record[field] = value; P.dump(path, record)
    with pytest.raises(ValueError):
        with W.compute(path): pytest.fail("invalid allocation admitted")


def test_published_training_export_uses_block44_raw_means_and_coefficients():
    priority = P.ROOT / "results/g_agreement/blindspot/w1/priority_training"
    meta = W.read(priority / "probe_directions.json")
    vectors, audit = W.priority_vectors(priority, "TRAINING_EXPORT_SEAL.json",
        meta["input_seal_sha256"], meta["source_labels_sha256"])
    with np.load(priority / "probe_directions.npz", allow_pickle=False) as z:
        for feature in W.FEATURES:
            prefix = feature + "__L44"
            unit = z[prefix + "__unit"]
            gap = (z[prefix + "__mean_A"].astype(float) - z[prefix + "__mean_B"]) @ unit
            np.testing.assert_allclose(vectors[feature][0], unit * gap, rtol=1e-5, atol=1e-6)
            assert audit[feature]["raw_means_coefficient_verified"] is True
            assert audit[feature]["layer"] == 44


@pytest.mark.parametrize("corrupt", ["coefficient", "mean", "value", "labels"])
def test_training_export_rejects_inconsistent_raw_lineage(tmp_path, corrupt):
    source = P.ROOT / "results/g_agreement/blindspot/w1/priority_training"
    meta = W.read(source / "probe_directions.json")
    with np.load(source / "probe_directions.npz", allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    row = next(r for r in meta["rows"] if r["feature"] == "table_column" and r["layer"] == 44)
    if corrupt == "coefficient": arrays[row["arrays"]["raw_coefficient"]] *= -1
    elif corrupt == "mean": arrays[row["arrays"]["raw_mean_A"]] = arrays[row["arrays"]["raw_mean_B"]].copy()
    elif corrupt == "value": row["negative_value"] = "wrong"
    label_sha = meta["source_labels_sha256"]
    if corrupt == "labels": meta["source_labels_sha256"] = "0" * 64
    P.dump(tmp_path / "probe_directions.json", meta)
    np.savez(tmp_path / "probe_directions.npz", **arrays)
    P.dump(tmp_path / "TRAINING_EXPORT_SEAL.json", {"status": "SEALED_TRAINING_ONLY_EXPORT",
        "files": {name: P.sha(tmp_path / name) for name in ("probe_directions.json", "probe_directions.npz")}})
    with pytest.raises(ValueError):
        W.priority_vectors(tmp_path, "TRAINING_EXPORT_SEAL.json", meta["input_seal_sha256"], label_sha)


def test_reference_retry_smoke_budget_has_900s_setup_outside_science(tmp_path, monkeypatch):
    path, record = assignment_fixture(tmp_path, monkeypatch)
    record.update(smoke_forecast_seconds=2000., previous_gpu_seconds=516.,
        allocated_gpu_seconds=2484., setup_allowance_seconds=900., deadline_epoch=990.+900.+2484.)
    P.dump(path, record)
    with W.compute(path) as accepted: assert accepted == record
    record['allocated_gpu_seconds'] += 1
    P.dump(path, record)
    with pytest.raises(ValueError):
        with W.compute(path): pytest.fail('above smoke-sized cap')


def test_reference_retry_rejects_above_one_hour_forecast(tmp_path, monkeypatch):
    path, record = assignment_fixture(tmp_path, monkeypatch)
    record['smoke_forecast_seconds'] = 3601.
    P.dump(path, record)
    with pytest.raises(ValueError, match='report before launch'):
        with W.compute(path): pytest.fail('forecast over1GPU-h')


def test_1245_single_attempt_grant_preserves_prior_charges_separately(tmp_path, monkeypatch):
    path, record = assignment_fixture(tmp_path, monkeypatch)
    ledger=tmp_path/'results/g_agreement/compute.jsonl';ledger.parent.mkdir(parents=True)
    P.jsonl(ledger,[{'gpu_hours':516./3600,'extra':{'mechanism_budget':'w7'}}])
    record.update(budget_round='2026-10-23-1245',smoke_forecast_seconds=2000.,
        allocated_gpu_seconds=3000.,setup_allowance_seconds=900.,deadline_epoch=4890.)
    P.dump(path,record)
    with W.compute(path): pass
    assert P.rows(ledger)[0]['gpu_hours']==516./3600
    record['budget_round']='unregistered-reset';P.dump(path,record)
    with pytest.raises(ValueError,match='unregistered'):
        with W.compute(path): pytest.fail('unauthorized extra grant')
