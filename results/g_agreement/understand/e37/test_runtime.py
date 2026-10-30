"""CPU-only E37 runtime contracts; mock tensors, no pretrained weights or GPU."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("e37_runtime_tests", HERE / "runtime.py")
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)
STAGE = r.ROOT / "cache/g_agreement/understand/e37-inputs-v1"


def dump(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True))


def assignment(now=1000):
    return {"issuer": "integrator", "experiment": "E37", "gpu_count": 1, "pod_id": "cpu-test",
            "registered": True, "pushed": True, "external_hardstop_verified": True,
            "allocated_gpu_seconds": 5400, "previous_gpu_seconds": 0,
            "provider_created_epoch": now, "deadline_epoch": now + 5400}


def receipt(folder, received=1000):
    folder = Path(folder)
    adapter = folder / "sft"
    adapter.mkdir()
    dump(adapter / "adapter_config.json", {"peft_type": "LORA", "r": 2, "lora_alpha": 8, "target_modules": ["q_proj"]})
    (adapter / "adapter_model.safetensors").write_bytes(b"CPU fixture; no model load")
    pinned = r.read(r.ROOT / "projects/g_agreement/manifest/assets.json")
    value = {"schema": "E37_SFT_RECEIPT_v1", "status": "RECEIVED_FROZEN", "issuer": "integrator",
             "provided_by": "Agam", "checkpoint_identity": "s3d.omp4bp.s2/step251", "identity_verified": True,
             "frozen_before_model_calls": True, "model_calls_before_freeze": 0, "received_epoch": received,
             "base_model_revision": pinned["target"]["revision"], "local_path": str(adapter),
             "files": {p.name: r.sha(p) for p in adapter.iterdir()}}
    path = folder / "checkpoint.json"
    dump(path, value)
    return path, value


def closed_predecessors(folder):
    value = {"schema": "E37_PREREQUISITE_COMPLETION_v1", "issuer": "integrator",
             "status": "READY_AFTER_PREDECESSORS", "experiments": {}}
    for experiment in ("E33", "E28"):
        path = Path(folder) / (experiment + "-closure.json")
        dump(path, {"schema": "E37_PREDECESSOR_TERMINAL_v1", "issuer": "integrator", "experiment": experiment,
                    "status": "NOT_RUN", "closed": True, "all_expected_runs_closed": True, "no_active_pods": True,
                    "reason": "CPU fixture terminal closure", "closed_epoch": time.time() - 10,
                    "provider_accounting": {"gpu_seconds": 0}})
        value["experiments"][experiment] = {"status": "NOT_RUN", "receipts": [{"path": str(path), "sha256": r.sha(path)}]}
    path = Path(folder) / "predecessors.json"
    dump(path, value)
    return path, value


class ConditionalTests(unittest.TestCase):
    def test_missing_checkpoint_blocks_then_closes_not_run(self):
        with tempfile.TemporaryDirectory() as d:
            for now, expected in [(r.ARRIVAL_DEADLINE - 1, "BLOCKED_AWAITING_CHECKPOINT"),
                                  (r.ARRIVAL_DEADLINE + 1, "NOT_RUN")]:
                with self.subTest(now=now), self.assertRaises(r.Blocked) as caught:
                    r.checkpoint_receipt(Path(d) / "missing", now=now)
                self.assertEqual(caught.exception.status, expected)

    def test_on_time_checkpoint_eligible_after_arrival_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            path, value = receipt(d, received=r.ARRIVAL_DEADLINE)
            self.assertEqual(r.checkpoint_receipt(path, now=r.ARRIVAL_DEADLINE + 3600), value)
            value["received_epoch"] += 1
            dump(path, value)
            with self.assertRaises(r.Blocked) as caught:
                r.checkpoint_receipt(path, now=r.ARRIVAL_DEADLINE + 3600)
            self.assertEqual(caught.exception.status, "NOT_RUN")

    def test_checkpoint_provenance_and_byte_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, value = receipt(d)
            for change in ({"provided_by": "unknown"}, {"identity_verified": False},
                           {"model_calls_before_freeze": 1}, {"base_model_revision": "wrong"}):
                dump(path, {**value, **change})
                with self.subTest(change=change), self.assertRaises(ValueError):
                    r.checkpoint_receipt(path, now=2000)
            dump(path, value)
            (Path(value["local_path"]) / "adapter_model.safetensors").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                r.checkpoint_receipt(path, now=2000)

    def test_predecessors_require_actual_receipts_or_terminal_closure(self):
        with tempfile.TemporaryDirectory() as d:
            path, value = closed_predecessors(d)
            self.assertEqual(r.predecessors(path), value)
            evidence = Path(value["experiments"]["E28"]["receipts"][0]["path"])
            data = r.read(evidence)
            data["no_active_pods"] = False
            dump(evidence, data)
            value["experiments"]["E28"]["receipts"][0]["sha256"] = r.sha(evidence)
            dump(path, value)
            with self.assertRaises(ValueError):
                r.predecessors(path)

    def test_unresolved_parity_blocks_and_threshold_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "gate.json"
            dump(path, {"status": "UNRESOLVED"})
            with self.assertRaises(r.Blocked):
                r.validate_parity_policy(path)
            policy = r.read(HERE / "PARITY_GATE.json")
            policy["smoke"]["self_repeat_max_abs"] = .01
            dump(path, policy)
            with self.assertRaises(ValueError):
                r.validate_parity_policy(path)


class BudgetTests(unittest.TestCase):
    def test_eight_paths_required_and_no_fit_keeps_full_scope(self):
        budget = r.Budget(assignment(), now=lambda: 1000)
        budget.start()
        keys = {(arm, c) for arm in r.ARMS for c in r.CHANNELS}
        with self.assertRaises(ValueError):
            budget.forecast({("RL", "C1"): [1, 1, 1]}, {("RL", "C1"): 150})
        report = budget.forecast({k: [5, 5, 5] for k in keys}, {k: 150 for k in keys})
        self.assertFalse(report["fit"])
        self.assertEqual(report["science_cap_seconds"], 5400)
        self.assertEqual(len(report["paths"]), 8)

    def test_setup_counted_no_clock_reset_and_no_retry(self):
        now = [6200]
        budget = r.Budget(assignment(), now=lambda: now[0])
        budget.start()
        keys = {(arm, c) for arm in r.ARMS for c in r.CHANNELS}
        self.assertFalse(budget.forecast({k: [1, 1, 1] for k in keys}, {k: 10 for k in keys})["fit"])
        with self.assertRaises(ValueError):
            budget.start()
        with self.assertRaises(ValueError):
            r.Budget({**assignment(), "previous_gpu_seconds": 1}, now=lambda: 1000)

    def test_alarm_uses_absolute_nonresetting_deadlines(self):
        now = [1000]
        budget = r.Budget(assignment(), now=lambda: now[0])
        with patch.object(r.signal, "getitimer", return_value=(0, 0)), patch.object(r.signal, "signal"), patch.object(r.signal, "setitimer") as timer:
            budget.install_alarm()
            self.assertEqual(timer.call_args.args[1], 5280)
            budget.start()
            budget.science_cap = 500
            now[0] = 1100
            budget.guard()
            self.assertEqual(timer.call_args.args[1], 280)
            budget.close_alarm()
            self.assertEqual(timer.call_args.args[1], 0)


class NativeScoringTests(unittest.TestCase):
    def test_auc_ties_and_positive_A(self):
        self.assertEqual(r.auroc([2, 1, 1, 0], [1, 1, 0, 0]), .875)
        self.assertEqual(r.auroc([1, 1], [1, 0]), .5)
        with self.assertRaises(ValueError):
            r.auroc([1], [1])

    def test_exact_embedding_replacement_preserves_other_positions(self):
        import torch
        model = torch.nn.Module()
        model.embedding = torch.nn.Embedding(10, 3)
        model.get_input_embeddings = lambda: model.embedding
        ids = torch.tensor([[1, 2, 3], [4, 2, 6]])
        original = model.embedding(ids).detach().clone()
        h = torch.tensor([[3., 4., 0.], [0., 0., 2.]])
        actual = r.injected_embeddings(model, ids, h, {"alpha": 16000, "marker_index": 1})
        self.assertTrue(torch.equal(actual[:, [0, 2]], original[:, [0, 2]]))
        self.assertTrue(torch.equal(actual[:, 1], 16000 * h / h.norm(dim=1, keepdim=True)))

    def test_exact_native_oracle_reference_scoring(self):
        import torch
        import common
        from mats.readers.olens import OracleLens

        class Tok:
            pad_token_id = 0
            eos_token_id = 15
            def encode(self, text, **kwargs):
                return {"a": [5], "b": [6, 7], "c": [8, 9], "d": [10], "- ": [11]}[text]

        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.embedding = torch.nn.Embedding(16, 3)
            def get_input_embeddings(self):
                return self.embedding
            def forward(self, inputs_embeds, attention_mask, logits_to_keep, use_cache=False):
                x = inputs_embeds.cumsum(1).sum(-1, keepdim=True)
                logits = torch.sin(x + torch.arange(16).reshape(1, 1, 16))
                return SimpleNamespace(logits=logits[:, -logits_to_keep:])

        torch.manual_seed(1)
        tok, model = Tok(), Model()
        h = torch.tensor([[.3, .4, .5], [.5, -.1, .2]])
        reader = OracleLens(model=model, tok=tok, device="cpu")
        reader._slots[44] = ([1, 2, 3], 1)
        text_pairs = [["a", "b"], ["c", "d"]]
        expected = reader.paired_logodds_templates(h, 44, text_pairs, prefix="- ").T.tolist()
        carrier = {"head_ids": [1, 2, 3], "marker_index": 1, "alpha": 16000, "prefix_ids": {"C2": [11]}}
        pairs = {"C2": {"f": [[tok.encode(t) for t in pair] for pair in text_pairs]}}
        items = [{"id": "0", "feature": "f"}, {"id": "1", "feature": "f"}]
        result = r.score_unit(model, tok, {"channel": "C2", "feature": "f", "indices": [0, 1]}, items, h, pairs, carrier, device="cpu")
        self.assertEqual([x["scores"] for x in result], expected)
        self.assertEqual([x["score"] for x in result], [sum(x) / 2 for x in expected])

    def test_checkpoint_tensor_coverage_with_real_peft(self):
        import torch
        from peft import LoraConfig, PeftModel, get_peft_model
        with tempfile.TemporaryDirectory() as d:
            model = get_peft_model(torch.nn.Sequential(torch.nn.Linear(4, 3)), LoraConfig(target_modules=["0"], r=2,
                                   lora_alpha=4, lora_dropout=0, init_lora_weights=False))
            model.save_pretrained(d, safe_serialization=True)
            loaded = PeftModel.from_pretrained(torch.nn.Sequential(torch.nn.Linear(4, 3)), d, is_trainable=False)
            loaded.load_adapter(d, adapter_name="sft", is_trainable=False)
            for adapter in ("default", "sft"):
                report = r.verify_adapter_parameters(loaded, d, adapter)
                self.assertTrue(report["all_tensors_matched"])
                self.assertEqual(report["matched_tensors"], 2)


class PreparedInputTests(unittest.TestCase):
    def test_actual_stage_shapes_units_and_parity_boundary(self):
        items, h, templates, _, _, parity, labels = r.load_inputs(STAGE)
        self.assertEqual(h.shape, (2100, 5120))
        self.assertEqual(len(labels), 252)
        self.assertEqual(len(parity["smoke_ids"]), 20)
        self.assertEqual({k: len(v) for k, v in r.unit_plan(items, templates).items()},
                         {"C1": 150, "C1prime": 150, "C2": 42, "C4": 150})

    def test_extra_unsealed_labels_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "input"
            shutil.copytree(STAGE, target)
            dump(target / "full_private_labels.json", {"extra": "forbidden"})
            with self.assertRaises(ValueError):
                r.load_inputs(target)

    def test_real_source_bindings_without_model_load(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            checkpoint, checkpoint_value = receipt(folder)
            from test_checkpoint_cpu import unverified_fixture
            cpu=unverified_fixture();cpu["received_epoch"]=checkpoint_value["received_epoch"]
            cpu["selected_files"]=checkpoint_value["files"]
            cpu_path=folder / "CPU_TENSOR_CHECK.json";dump(cpu_path,cpu)
            checkpoint_value.update(cpu_tensor_check_path=str(cpu_path),cpu_tensor_check_sha256=r.sha(cpu_path),
                                    selected_branch=cpu["selected_branch"],readme_identity_claim_verified=False)
            dump(checkpoint,checkpoint_value)
            prior, _ = closed_predecessors(folder)
            assets = folder / "assets.json"
            dump(assets, {})
            args = SimpleNamespace(inputs=STAGE, assets=assets, checkpoint_receipt=checkpoint, predecessors=prior,
                                   parity_gate=HERE / "PARITY_GATE.json", assignment=folder / "assignment.json")
            fields = {"input_seal_sha256": STAGE / "INPUT_SEAL.json", "assets_sha256": assets,
                      "checkpoint_receipt_sha256": checkpoint, "predecessors_sha256": prior,
                      "parity_gate_sha256": args.parity_gate, "plan_sha256": HERE / "PLAN.json"}
            a = {**assignment(time.time()), **{k: r.sha(p) for k, p in fields.items()}}
            sources = [r.PREFIX + n for n in ("runtime.py", "PLAN.json", "PARITY_GATE.json", "checkpoint_cpu.py", "CHECKPOINT_MANIFEST_2026-10-26.json")]
            sources += [r.BASE_RUNTIME, "projects/g_agreement/manifest/assets.json"]
            a["source_files"] = {n: r.sha(r.ROOT / n) for n in sources}
            dump(args.assignment, a)
            # This fixture uses fake weight bytes; exercise real receipt binding,
            # with byte comparison independently covered by test_checkpoint_cpu.
            with patch.object(r.CPU,"validate_selection",return_value=cpu):
                result = r.preflight(args)
            self.assertEqual(len(result[-1][0]), 2100)
            a["input_seal_sha256"] = "wrong"
            with self.assertRaises(ValueError):
                r.verify_assignment(a, args)


if __name__ == "__main__":
    unittest.main()
