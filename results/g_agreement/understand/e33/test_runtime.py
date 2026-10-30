"""CPU contract tests for E33; no downloaded weights, GPU, or external service."""
from contextlib import contextmanager, nullcontext
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import runtime as r


def assignment(now=1000):
    return {"issuer": "integrator", "experiment": "E33", "gpu_count": 1,
            "pod_id": "cpu-test", "registered": True, "pushed": True,
            "external_hardstop_verified": True, "allocated_gpu_seconds": 1440,
            "previous_gpu_seconds": 407, "provider_created_epoch": now,
            "slot": 0, "pod_count": 1, "doses": list(r.DOSES),
            "deadline_epoch": now + 1440}


def run_plan(pods=1, caps=None):
    caps = caps or ([1440] if pods == 1 else [9475, 6318])
    doses = [list(r.DOSES)] if pods == 1 else [list(r.DOSES[:3]), list(r.DOSES[3:])]
    return {"schema": "E33_RUN_PLAN_v2", "experiment": "E33", "run_id": "cpu-sharded-test",
            "previous_gpu_seconds": 407, "global_cap_gpu_seconds": 16200,
            "allocations": [{"slot": i, "pod_id": "cpu-test" if i == 0 else "cpu-test-1",
                             "doses": d, "allocated_gpu_seconds": caps[i]} for i, d in enumerate(doses)]}


def shard_assignment(plan, slot, now=1000):
    allocation = plan["allocations"][slot]
    return {**assignment(now), **allocation, "pod_count": len(plan["allocations"]),
            "previous_gpu_seconds": plan["previous_gpu_seconds"],
            "deadline_epoch": now + allocation["allocated_gpu_seconds"]}


class BudgetTests(unittest.TestCase):
    def test_infrastructure_losses_reduce_fixed_envelopes_and_require_exact_stopped_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            plan = run_plan(pods=2, caps=[9043, 6229])
            plan["previous_gpu_seconds"] = 928
            for slot, allocation in enumerate(plan["allocations"]):
                receipt = {"schema": "E33_INFRASTRUCTURE_LOSS_v1", "issuer": "integrator", "experiment": "E33",
                           "slot": slot, "pod_id": f"failed-{slot}", "status": "EXITED", "stopped": True,
                           "setup_only": True, "science_gpu_seconds": 0, "provider_gpu_seconds": 599.2,
                           "provider_stopped_epoch": 900}
                path = Path(td) / f"receipt-{slot}.json"
                path.write_text(json.dumps(receipt))
                allocation.update(budget_envelope_gpu_seconds=allocation["allocated_gpu_seconds"],
                                  infrastructure_loss_gpu_seconds=600,
                                  infrastructure_losses=[{"pod_id": receipt["pod_id"], "receipt_path": str(path),
                                                          "receipt_sha256": r.sha(path)}])
                allocation["allocated_gpu_seconds"] -= 600
            self.assertEqual([a["allocated_gpu_seconds"] for a in plan["allocations"]], [8443, 5629])
            r.validate_run_plan(plan)
            for slot in (0, 1):
                a = shard_assignment(plan, slot)
                budget = r.Budget(a, plan, now=lambda: 1600)
                budget.start_science()
                paths = {(p, d) for p in r.PROMPTS for d in budget.doses}
                report = budget.admit({k: [1.34, 1.35, 1.36] if k[0] == "P1" else [1.45, 1.46, 1.47] for k in paths},
                                     {k: 557 for k in paths})
                self.assertTrue(report["fit"])
                self.assertEqual(report["remaining_seconds"], a["allocated_gpu_seconds"] - 600)
                with self.assertRaises(ValueError):
                    r.Budget({**a, "infrastructure_loss_gpu_seconds": 0}, plan, now=lambda: 1000)
            for change in ({"allocated_gpu_seconds": 9043}, {"infrastructure_loss_gpu_seconds": 601},
                           {"infrastructure_loss_gpu_seconds": 599}, {"infrastructure_losses": []}):
                bad = copy.deepcopy(plan)
                bad["allocations"][0].update(change)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    r.validate_run_plan(bad)
            bad = copy.deepcopy(plan)
            bad["allocations"][1]["pod_id"] = "failed-0"
            with self.assertRaises(ValueError):
                r.validate_run_plan(bad)
            entry = plan["allocations"][0]["infrastructure_losses"][0]
            path = Path(entry["receipt_path"])
            receipt = json.loads(path.read_text())
            for change in ({"stopped": False}, {"science_gpu_seconds": 1}, {"setup_only": False}, {"issuer": "worker"}):
                path.write_text(json.dumps({**receipt, **change}))
                entry["receipt_sha256"] = r.sha(path)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    r.validate_run_plan(plan)
            path.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):
                r.validate_run_plan(plan)  # changed bytes without re-pinned receipt hash

    def test_operational_repin_preserves_cap_with_600_second_setup_per_slot(self):
        # 2026-10-25 operational re-pin: 406.6s first run + 520.5s failed
        # deployments = 927.1s, conservatively reserved as 928s. No science
        # or scoring changes. Both live-pod clocks include their setup time.
        plan = run_plan(pods=2, caps=[9043, 6229])
        plan["previous_gpu_seconds"] = 928
        self.assertEqual(928 + sum(a["allocated_gpu_seconds"] for a in plan["allocations"]), 16200)
        for slot in (0, 1):
            a = shard_assignment(plan, slot, now=1000)
            budget = r.Budget(a, plan, now=lambda: 1600)
            budget.start_science()
            paths = {(p, d) for p in r.PROMPTS for d in budget.doses}
            samples = {key: ([1.34, 1.35, 1.36] if key[0] == "P1" else [1.45, 1.46, 1.47]) for key in paths}
            forecast = budget.admit(samples, {key: 557 for key in paths})
            self.assertTrue(forecast["fit"])
            self.assertEqual(forecast["provider_elapsed_seconds"], 600)
            self.assertEqual(forecast["remaining_seconds"], a["allocated_gpu_seconds"] - 600)
            with self.assertRaises(ValueError):
                budget.start_science()
            with self.assertRaises(ValueError):
                r.Budget({**a, "previous_gpu_seconds": 407}, plan, now=lambda: 1600)
        over = run_plan(pods=2, caps=[9044, 6229])
        over["previous_gpu_seconds"] = 928
        with self.assertRaises(ValueError):
            r.validate_run_plan(over)

    def test_two_pod_shared_budget_and_shard_sizes(self):
        plan = run_plan(pods=2)
        for slot, doses, count in [(0, list(r.DOSES[:3]), 12600), (1, list(r.DOSES[3:]), 8400)]:
            b = r.Budget(shard_assignment(plan, slot), plan, now=lambda: 1000)
            self.assertEqual(list(b.doses), doses)
            self.assertEqual(2100 * 2 * len(b.doses), count)
            keys = {(p, d) for p in r.PROMPTS for d in b.doses}
            b.start_science()
            report = b.admit({k: [.1, .2, .3] for k in keys}, {k: 557 for k in keys})
            self.assertTrue(report["fit"])
            self.assertEqual(report["previous_gpu_seconds"], 407)
            self.assertEqual(report["slot"], slot)
            self.assertEqual(report["science_cap_seconds"], min(1.5 * report["F_seconds"] + 360, b.reserved))

    def test_single_pod_preserves_all_five_doses(self):
        plan = run_plan(caps=[15793])
        b = r.Budget(shard_assignment(plan, 0), plan, now=lambda: 1000)
        self.assertEqual(b.doses, r.DOSES)
        self.assertEqual(b.reserved + plan["previous_gpu_seconds"], 16200)

    def test_shard_forecast_rejects_extra_or_missing_paths(self):
        plan = run_plan(pods=2)
        b = r.Budget(shard_assignment(plan, 1), plan, now=lambda: 1000)
        all_keys = {(p, d) for p in r.PROMPTS for d in r.DOSES}
        with self.assertRaises(ValueError):
            b.admit({k: [1, 1, 1] for k in all_keys}, {k: 10 for k in all_keys})

    def test_global_cap_includes_both_allocations_and_prior(self):
        for prior in (0, 408, float("nan")):
            plan = {**run_plan(pods=2), "previous_gpu_seconds": prior}
            with self.subTest(prior=prior), self.assertRaises(ValueError):
                r.validate_run_plan(plan)
        with self.assertRaises(ValueError):
            r.validate_run_plan(run_plan(caps=[15794]))

    def test_duplicate_missing_or_repartitioned_doses_rejected(self):
        for doses in ([0.5, 0.75, 1], [1], [0.25, 0.75, 1]):
            plan = run_plan(pods=2)
            plan["allocations"][1]["doses"] = doses
            with self.subTest(doses=doses), self.assertRaises(ValueError):
                r.validate_run_plan(plan)
        plan = run_plan(pods=2)
        plan["allocations"][1]["pod_id"] = plan["allocations"][0]["pod_id"]
        with self.assertRaises(ValueError):
            r.validate_run_plan(plan)

    def test_assignment_cannot_reallocate_or_recharge_prior(self):
        plan = run_plan(pods=2)
        for change in ({"slot": 1}, {"doses": list(r.DOSES)}, {"previous_gpu_seconds": 406.6},
                       {"pod_count": 1}, {"allocated_gpu_seconds": 9476}, {"pod_id": "other-pod"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                r.Budget({**shard_assignment(plan, 0), **change}, plan, now=lambda: 1000)

    def test_all_paths_required(self):
        b = r.Budget(assignment(), run_plan(), now=lambda: 1000)
        with self.assertRaises(ValueError):
            b.admit({("P1", 0): [1, 1, 1]}, {("P1", 0): 5})

    def test_no_fit_includes_setup_and_reserve(self):
        b = r.Budget(assignment(), run_plan(), now=lambda: 1800)
        b.start_science()
        keys = {(p, d) for p in r.PROMPTS for d in r.DOSES}
        f = b.admit({k: [2, 2, 2] for k in keys}, {k: 20 for k in keys})
        self.assertEqual(f["F_seconds"], 400)
        self.assertEqual(f["required_remaining_seconds"], 720)
        self.assertEqual(f["science_cap_seconds"], 960)
        self.assertFalse(f["fit"])

    def test_fit_and_science_clock_cannot_reset(self):
        b = r.Budget(assignment(), run_plan(), now=lambda: 1100)
        b.start_science()
        keys = {(p, d) for p in r.PROMPTS for d in r.DOSES}
        self.assertTrue(b.admit({k: [1, 1, 1] for k in keys}, {k: 10 for k in keys})["fit"])
        with self.assertRaises(ValueError):
            b.start_science()

    def test_deadline_and_retry_fail_closed(self):
        for change in ({"allocated_gpu_seconds": 1441}, {"previous_gpu_seconds": 1},
                       {"external_hardstop_verified": False}, {"deadline_epoch": 2441}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                r.Budget({**assignment(), **change}, run_plan(), now=lambda: 1000)
        with self.assertRaises(TimeoutError):
            r.Budget(assignment(), run_plan(), now=lambda: 2320)

    def test_nan_timing_rejected(self):
        b = r.Budget(assignment(), run_plan(), now=lambda: 1000)
        keys = {(p, d) for p in r.PROMPTS for d in r.DOSES}
        with self.assertRaises(ValueError):
            b.admit({k: [1, 1, float("nan")] for k in keys}, {k: 10 for k in keys})


class ScoreContractTests(unittest.TestCase):
    def test_right_pad_both_candidates_and_mask(self):
        ids, masks, h, lens = r.build_sequences([[7, 8], [9, 10]], [[1], [2, 3]], 0)
        self.assertEqual(ids, [[7, 8, 1, 0], [7, 8, 2, 3], [9, 10, 1, 0], [9, 10, 2, 3]])
        self.assertEqual(masks, [[1, 1, 1, 0], [1, 1, 1, 1]] * 2)
        self.assertEqual((h, lens), (2, [1, 2]))

    def test_sum_not_length_mean_and_ignore_pad(self):
        self.assertEqual(r.paired_sum_logodds([[-2, 999], [-3, -4]], [1, 2]), [5])
        with self.assertRaises(ValueError):
            r.build_sequences([[1], [1, 2]], [[2], [3]], 0)

    def test_scaling_absolute_and_restored_after_exception(self):
        layer = SimpleNamespace(lora_A={}, lora_B={}, scaling={"default": 2.0}, merged=False)
        model = SimpleNamespace(named_modules=lambda: [("layer", layer)])
        scaler = r.DoseScaler(model)
        for dose in (1, .5, .25, 0, .75, 1):
            scaler.set(dose)
            self.assertEqual(layer.scaling["default"], 2 * dose)
        with self.assertRaisesRegex(RuntimeError, "test failure"):
            with scaler.at(.25):
                raise RuntimeError("test failure")
        self.assertEqual(layer.scaling, {"default": 2.0})

    def test_merged_or_missing_or_hooked_adapter_rejected(self):
        layer = SimpleNamespace(lora_A={}, lora_B={}, scaling={"default": 2.0}, merged=True)
        with self.assertRaises(ValueError):
            r.DoseScaler(SimpleNamespace(named_modules=lambda: [("layer", layer)]))
        with self.assertRaises(ValueError):
            r.DoseScaler(SimpleNamespace(named_modules=lambda: []))
        layer._forward_hooks = {1: "injection"}
        with self.assertRaises(ValueError):
            r.assert_no_hooks(SimpleNamespace(named_modules=lambda: [("layer", layer)]))

    def test_actual_peft_linear_absolute_dose(self):
        import torch
        from peft import LoraConfig, get_peft_model
        torch.manual_seed(20261025)
        base = torch.nn.Linear(4, 3, bias=False)
        model = get_peft_model(torch.nn.Sequential(base), LoraConfig(
            target_modules=["0"], r=2, lora_alpha=4, lora_dropout=0.0,
            init_lora_weights=False)).eval()
        scaler = r.DoseScaler(model)
        x = torch.tensor([[0.2, -0.1, 0.8, 0.3]])
        with torch.inference_mode():
            base_value = base(x)
            full = model(x)
            for dose in (0, .25, .5, .75, 1, .25, 0, 1):
                with scaler.at(dose):
                    actual = model(x)
                    expected = base_value + dose * (full - base_value)
                    self.assertTrue(torch.allclose(actual, expected, atol=1e-7, rtol=1e-6))
                    if dose == 0:
                        self.assertTrue(torch.equal(actual, base_value))

    def test_exact_e16_reference_score_equivalence(self):
        import torch
        from reused import base_head, reference_base_scores

        class Tok:
            pad_token_id = 0
            def apply_chat_template(self, messages, **kwargs):
                return [1, 2, 3 if "alpha" in messages[0]["content"] else 4]
            def encode(self, text, **kwargs):
                return {"a": [5], "b": [6, 7], "c": [8, 9, 10], "d": [11]}[text]

        class Model(torch.nn.Module):
            def forward(self, input_ids, attention_mask, logits_to_keep, use_cache):
                # Deterministic teacher-forcing tensor with padding visible to test
                # exact alignment, candidate lengths, and identical forward batches.
                vocab = torch.arange(16, dtype=torch.float32).reshape(1, 1, -1)
                logits = torch.sin(input_ids.float().unsqueeze(-1) + vocab)
                return SimpleNamespace(logits=logits[:, -logits_to_keep:])

        tok, model = Tok(), Model()
        records = [{"id": "a", "feature": "f", "text": "alpha"},
                   {"id": "b", "feature": "f", "text": "beta"}]
        text_pairs = [["a", "b"], ["c", "d"]]
        token_pairs = {"f": [[tok.encode(t) for t in pair] for pair in text_pairs]}
        reader = SimpleNamespace(tok=tok, model=model, device="cpu", base=nullcontext)
        expected = reference_base_scores(reader, records, text_pairs).tolist()
        for record in records:
            record["heads"] = {"P1": base_head(tok, record["text"])}
        actual = r.score_unit(model, tok, {"indices": [0, 1], "prompt": "P1", "feature": "f"},
                              records, token_pairs, device="cpu")
        self.assertEqual([v["scores"] for v in actual], expected)
        self.assertEqual([v["score"] for v in actual], [sum(v) / 2 for v in expected])


class SealTests(unittest.TestCase):
    def make_bank(self, folder):
        items, templates, pairs, units = [], {}, {}, []
        for f in range(25):
            feature = str(f)
            templates[feature] = {"olens": [["a", "b"], ["c", "d"]]}
            pairs[feature] = [[[1], [2]], [[3], [4]]]
            start = len(items)
            items += [{"id": str(i), "feature": feature, "heads": {"P1": [1, 2], "P2": [1, 3, 4]}}
                      for i in range(start, start + 84)]
            for prompt in r.PROMPTS:
                units += [{"prompt": prompt, "feature": feature, "indices": list(range(i, min(i + 16, start + 84)))}
                          for i in range(start, start + 84, 16)]
        (folder / "items.input.jsonl").write_text("".join(json.dumps(x) + "\n" for x in items))
        for name, obj in [("templates.json", templates), ("token_pairs.json", pairs), ("units.json", units), ("provenance.json", {})]:
            (folder / name).write_text(json.dumps(obj))
        self.seal(folder)

    def seal(self, folder):
        (folder / "INPUT_SEAL.json").write_text(json.dumps({"files": {p.name: r.sha(p) for p in folder.iterdir() if p.name != "INPUT_SEAL.json"}}))

    def test_complete_grid_and_missing_unit_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.make_bank(folder)
            self.assertEqual(len(r.load_inputs(folder)[0]), 2100)
            units = r.read(folder / "units.json")
            (folder / "units.json").write_text(json.dumps(units[:-1]))
            self.seal(folder)
            with self.assertRaisesRegex(ValueError, "cover every item"):
                r.load_inputs(folder)

    def test_tampering_and_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.make_bank(folder)
            (folder / "provenance.json").write_text('{"tamper":true}')
            with self.assertRaisesRegex(ValueError, "seal mismatch"):
                r.load_inputs(folder)
            self.seal(folder)
            seal = r.read(folder / "INPUT_SEAL.json")
            seal["files"]["../escape"] = "a" * 64
            (folder / "INPUT_SEAL.json").write_text(json.dumps(seal))
            with self.assertRaises(ValueError):
                r.load_inputs(folder)


if __name__ == "__main__":
    unittest.main()
