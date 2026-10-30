"""2026-10-25 focused E29 CPU tests; synthetic records and a tiny random model only."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("e29_worker_tested", Path(__file__).with_name("worker.py"))
W = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(W)


def plan_fixture():
    cohorts = []
    for name, blind, phrasings, names in (("w12", True, 2, ["w" + str(i) for i in range(6)]),
                                       ("suraj_exp13", False, 1, ["s" + str(i) for i in range(7)])):
        n = 84 if blind else 160
        cohorts.append({"name": name, "blind": blind, "phrasing_count": phrasings,
                        "input_seal_sha256": "1" * 64, "labels_sha256": "2" * 64,
                        "rows": names, "items": [{"id": name + ":" + row + ":" + str(i), "feature": row} for row in names for i in range(n)],
                        "expected_scores": len(names) * n * phrasings * 2,
                        "freeze": {"status": "FROZEN", "source_commit": "fixture"}})
    return {"experiment": "E29", "status": "READY", "batch_size": 8,
            "frame": W.FRAME, "scoring": W.SCORING,
            "model": {"model_id": W.MODEL, "revision": W.REVISION, "adapter": None, "injection": None},
            "source_files": {W.E25_RELATIVE: W.E25_SHA256, W.SELF_RELATIVE: W.sha(Path(W.__file__))},
            "cohorts": cohorts}


def assignment_fixture(plan, path):
    return {"issuer": "integrator", "experiment": "E29", "pod_id": "test-pod", "plan_sha256": W.sha(path),
            "source_files": plan["source_files"], "source_published": True, "inputs_published": True,
            "registration_published": True, "external_hardstop_verified": True,
            "w12_freeze_verified": True, "w12_readers_not_scored": True, "w12_reader_hold_enforced": True,
            "gpu_count": 1, "total_gpu_seconds": 1800, "retrieval_reserve_seconds": 30, "retry_authorized": False,
            "budget_start_epoch": 1000, "previous_gpu_seconds": 20, "deadline_epoch": 2780,
            "assets_manifest_sha256": "3" * 64}


def stage_fixture(root, plan):
    for c in plan["cohorts"]:
        d = root / c["name"]
        d.mkdir(parents=True)
        (d / "items.jsonl").write_text("".join(json.dumps({**i, "text": "Exact prefix"}) + "\n" for i in c["items"]))
        W.dump(d / "candidates.json", {r: [["candidate A", "candidate B"] for _ in range(c["phrasing_count"])] for r in c["rows"]})
        W.dump(d / "INPUT_SEAL.json", {"files": {n: W.sha(d / n) for n in ("items.jsonl", "candidates.json")}})
        c["input_seal_sha256"] = W.sha(d / "INPUT_SEAL.json")


class E29WorkerTests(unittest.TestCase):
    def test_exact_e25_functions_reused(self):
        self.assertIs(W.encode_frame, W.E25.encode_frame)
        self.assertIs(W.score_batch, W.E25.score_batch)
        self.assertEqual(W.sha(W.ROOT / W.E25_RELATIVE), W.E25_SHA256)
        W.verify_sources(plan_fixture())

    def test_primary_must_be_ready_blind_first_and_complete(self):
        W.validate_plan(plan_fixture())
        for mutate in (
            lambda p: p.update(status="WAITING_W12_FREEZE"),
            lambda p: p["cohorts"][0].update(blind=False),
            lambda p: p["cohorts"].reverse(),
            lambda p: p["cohorts"].pop(),
            lambda p: p["cohorts"][1].update(phrasing_count=2),
            lambda p: p["cohorts"][0].update(expected_scores=2),
            lambda p: p["cohorts"][0].update(freeze={}),
            lambda p: p["cohorts"][0]["items"].pop(),
            lambda p: p["cohorts"][1]["items"].pop(),
            lambda p: p["model"].update(adapter="adapter"),
        ):
            plan = plan_fixture()
            mutate(plan)
            with self.assertRaises(ValueError):
                W.validate_plan(plan)

    def test_assignment_binds_all_blinding_holds(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"RUNPOD_POD_ID": "test-pod"}):
            path = Path(temp) / "plan.json"
            plan = plan_fixture()
            W.dump(path, plan)
            a = assignment_fixture(plan, path)
            W.validate_assignment(a, plan, path, 1010)
            for field in ("source_published", "inputs_published", "registration_published", "external_hardstop_verified",
                          "w12_freeze_verified", "w12_readers_not_scored", "w12_reader_hold_enforced"):
                with self.assertRaisesRegex(ValueError, field):
                    W.validate_assignment(a | {field: False}, plan, path, 1010)
            for change in ({"pod_id": "wrong"}, {"gpu_count": 2}, {"gpu_count": True}, {"retry_authorized": True}, {"plan_sha256": "0" * 64}):
                with self.assertRaises(ValueError):
                    W.validate_assignment(a | change, plan, path, 1010)

    def test_cumulative_previous_time_and_internal_reserve(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"RUNPOD_POD_ID": "test-pod"}):
            path = Path(temp) / "plan.json"
            plan = plan_fixture()
            W.dump(path, plan)
            a = assignment_fixture(plan, path)
            # §143: previous20 means total deadline2780, compute deadline2750, never2800.
            W.validate_assignment(a, plan, path, 2749)
            for change, now in (({}, 2750), ({"deadline_epoch": 2800}, 1010),
                                ({"budget_start_epoch": 1100}, 1010), ({"previous_gpu_seconds": -1}, 1010),
                                ({"previous_gpu_seconds": float("nan")}, 1010),
                                ({"setup_allowance_seconds": 1500}, 1010)):
                with self.assertRaises(ValueError):
                    W.validate_assignment(a | change, plan, path, now)

    def test_clock_rollback_cannot_restore_budget(self):
        wall, mono = [1010.0], [50.0]
        a = {"budget_start_epoch": 1000, "previous_gpu_seconds": 20, "deadline_epoch": 1340}
        budget = W.CumulativeBudget(a, wall=lambda: wall[0], monotonic=lambda: mono[0])
        self.assertEqual(budget.check(), 300)
        wall[0], mono[0] = 900, 150
        self.assertEqual(budget.check(), 200)
        self.assertEqual(budget.snapshot()["cumulative_gpu_seconds"], 130)
        mono[0] = 350
        with self.assertRaises(TimeoutError):
            budget.check()

    def test_stage_exact_identity_and_no_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            plan, stage = plan_fixture(), Path(temp) / "stage"
            stage_fixture(stage, plan)
            result = W.verify_stage(stage, plan)
            self.assertEqual(set(result), {"w12", "suraj_exp13"})
            (stage / "w12" / "labels.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "unexpected files"):
                W.verify_stage(stage, plan)

    def test_stage_tampering_and_changed_order_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            plan, stage = plan_fixture(), Path(temp) / "stage"
            stage_fixture(stage, plan)
            original = (stage / "w12" / "items.jsonl").read_bytes()
            (stage / "w12" / "items.jsonl").write_bytes(original.replace(b"Exact", b"Other"))
            with self.assertRaisesRegex(ValueError, "payload changed"):
                W.verify_stage(stage, plan)
            (stage / "w12" / "items.jsonl").write_bytes(original)
            changed = copy.deepcopy(plan)
            changed["cohorts"][1]["items"].reverse()
            with self.assertRaisesRegex(ValueError, "order changed"):
                W.verify_stage(stage, changed)

    def test_forecast_covers_both_cohorts_with_one_budget(self):
        snapshot = {"compute_deadline_epoch": 1310, "cumulative_gpu_seconds": 300}
        f = W.forecast_gate([0.8, 1.0, 0.9], {"w12": 80, "suraj_exp13": 160}, snapshot, 1280)
        self.assertEqual(f["remaining_batches"], {"w12": 10, "suraj_exp13": 20})
        self.assertEqual(f["guarded_remaining_seconds"], 45)
        self.assertEqual(f["status"], "NO_FIT")
        self.assertEqual(W.forecast_gate([.8, 1, .9], {"w12": 80, "suraj_exp13": 160}, snapshot, 1200)["status"], "FIT")
        with self.assertRaises(ValueError):
            W.forecast_gate([1, 1, 1], {"w12": 80}, snapshot, 1200)

    def test_warmup_is_synthetic_worst_shape(self):
        frames = [{"ids": [1, 2, 3, 4, 5], "candidate_start": 4, "token_count": 1},
                  {"ids": [1, 2, 3, 4], "candidate_start": 1, "token_count": 3}]
        warm = W.synthetic_worst_batch(frames, 7)
        self.assertEqual(len(warm), 8)
        self.assertTrue(all(f == {"ids": [7] * 5, "candidate_start": 2, "token_count": 3} for f in warm))
        self.assertTrue(all("id" not in f and "feature" not in f for f in warm))

    def test_frozen_frame_exact_and_scored_suffix_only(self):
        seen = []
        def tok(text, **kwargs):
            seen.append((text, kwargs))
            return {"input_ids": list(range(len(text))), "offset_mapping": [(i, i+1) for i in range(len(text))]}
        result = W.make_frames(tok, [{"id": "x", "feature": "f", "text": "prefix\n"}], {"f": [["- A", " B"]]})
        self.assertEqual([s[0] for s in seen], ["prefix\n\n- A", "prefix\n\n B"])
        self.assertTrue(all(s[1]["add_special_tokens"] is False for s in seen))
        self.assertEqual([r["token_count"] for r in result], [3, 2])
        self.assertEqual([r["candidate"] for r in result], ["A", "B"])

    def test_reused_e25_scorer_matches_full_tiny_transformer(self):
        import torch
        from transformers import LlamaConfig, LlamaForCausalLM
        torch.manual_seed(20261025)
        model = LlamaForCausalLM(LlamaConfig(vocab_size=11, hidden_size=16, intermediate_size=24,
                                 num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=2)).eval()
        frames = [{"ids": [1, 2, 3, 4, 5], "candidate_start": 3, "token_count": 2},
                  {"ids": [7, 8, 2], "candidate_start": 2, "token_count": 1}]
        actual = W.score_batch(model, frames, 0)
        for frame, got in zip(frames, actual):
            with torch.inference_mode():
                lp = model(torch.tensor([frame["ids"]]), use_cache=False).logits[0].log_softmax(-1)
            expected = sum(float(lp[j-1, frame["ids"][j]]) for j in range(frame["candidate_start"], len(frame["ids"]))) / frame["token_count"]
            self.assertAlmostEqual(got, expected, places=6)

    def test_qwen_nested_and_direct_context_configs(self):
        self.assertEqual(W.context_limit(SimpleNamespace(text_config=SimpleNamespace(max_position_embeddings=262144))), 262144)
        self.assertEqual(W.context_limit(SimpleNamespace(max_position_embeddings=2048)), 2048)
        with self.assertRaises(ValueError):
            W.context_limit(SimpleNamespace())

    def test_cohort_seal_requires_complete_unique_grid(self):
        cohort = plan_fixture()["cohorts"][0]
        records = [{**item, "phrasing": p, "candidate": c, "token_count": 1, "mean_logprob": -1.0}
                   for item in cohort["items"] for p in range(2) for c in ("A", "B")]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for bad in (records[:-1], records + [records[0]], [records[0] | {"mean_logprob": float("nan")}] + records[1:],
                        [records[0] | {"mean_logprob": 0.1}] + records[1:]):
                with self.assertRaises(ValueError):
                    W.seal_cohort(root / "bad", cohort, bad, {}, "0" * 64)
            W.seal_cohort(root / "w12", cohort, records, {"labels_joined": False}, "0" * 64)
            seal = W.read(root / "w12" / "SCORE_SEAL.json")
            self.assertTrue(seal["complete"])
            self.assertEqual(seal["cohort"], "w12")
            self.assertEqual(set(seal["files"]), {"scores.jsonl", "provenance.json"})
            for name, digest in seal["files"].items():
                self.assertEqual(W.sha(root / "w12" / name), digest)
            with self.assertRaises(FileExistsError):
                W.seal_cohort(root / "w12", cohort, records, {}, "0" * 64)


if __name__ == "__main__":
    unittest.main()
