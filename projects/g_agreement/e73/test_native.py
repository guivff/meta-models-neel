"""Real CPU-tensor tests of the native batch contract; no pretrained models."""
from __future__ import annotations

from types import SimpleNamespace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

try:
    import torch
    import transformers
except ImportError:
    torch = None

from .native import (STAGING_POLICY, install_e56_nla_hook, load_native_ready,
                     native_batch, run, warmed_native_admission)
from .custody import sha256, verify_seal, write_json


GO = {"schema": "e73-reader-go-v1", "authorized_by": "I-2", "action": "GO",
      "capture_seal_sha256": "a" * 64, "bank_manifest_sha256": "b" * 64,
      "jforecast_commit": "c" * 40, "jforecast_sha256": "d" * 64,
      "judging_authorized": False}


class Tokenizer:
    eos_token_id = 0
    pad_token_id = 0
    unk_token_id = -1

    def convert_tokens_to_ids(self, token):
        return 0

    def decode(self, ids, **kwargs):
        return "".join({1: "<explanation>alpha</explanation>", 2: "<explanation>unfinished", 3: " tail"}.get(int(i), "") for i in ids)

    def batch_decode(self, rows, **kwargs):
        return [self.decode(row.tolist() if hasattr(row, "tolist") else row) for row in rows]


@unittest.skipIf(torch is None, "optional CPU torch/transformers test dependencies unavailable")
class NativeBatchTests(unittest.TestCase):
    def test_nla_row_specific_stop_fp32_normalization_and_unchanged_inputs(self):
        vectors = np.vstack([np.linspace(.01, 13, 5120), np.linspace(4, .1, 5120)]).astype(np.float16)
        original = vectors.copy()
        block = torch.nn.Identity()
        tok = Tokenizer()
        called = []
        model = SimpleNamespace(model=SimpleNamespace(layers=[torch.nn.Identity(), block]), generation_config=SimpleNamespace(eos_token_id=0))
        reader = SimpleNamespace(model=model, name="nla", device="cpu", tokenizer=tok, ids=[9, 8], marker=1,
                                 inject_layer_idx=1, _vec={"v": None}, n_hook_calls=0,
                                 _handle=block.register_forward_hook(lambda *_: None))
        install_e56_nla_hook(reader)

        def generate(**kwargs):
            called.append(kwargs)
            self.assertEqual(kwargs["input_ids"].tolist(), [[9, 8], [9, 8]])
            self.assertFalse(kwargs["do_sample"])
            self.assertEqual(kwargs["max_new_tokens"], 512)
            self.assertEqual(kwargs["num_return_sequences"], 1)
            before = torch.linspace(.3, 7, 2 * 2 * 5120, dtype=torch.float32).reshape(2, 2, 5120).to(torch.bfloat16)
            expected = before.clone()
            v = torch.as_tensor(vectors).float()
            normalized = (v / (v.norm(dim=-1, keepdim=True) + 1e-9)).to(torch.bfloat16)
            expected[:, 1] += expected[:, 1].norm(dim=-1, keepdim=True) * normalized
            actual = block(before.clone())
            self.assertTrue(torch.equal(actual, expected))
            # A decode step must not reinject into the one-token sequence.
            decode = torch.ones(2, 1, 5120)
            self.assertTrue(torch.equal(block(decode.clone()), decode))
            output = torch.tensor([[9, 8, 1, 0], [9, 8, 2, 3]])
            self.assertEqual(kwargs["stopping_criteria"](output, None).tolist(), [True, False])
            return output

        model.generate = generate
        result = native_batch(reader, vectors, kind="nla", go=GO,
                              capture_seal_sha="a" * 64, bank_manifest_sha="b" * 64)
        self.assertEqual(len(called), 1)
        self.assertEqual(len(result), 2)
        self.assertFalse(result[0]["truncated"])
        self.assertTrue(result[1]["truncated"])
        self.assertEqual(result[0]["finish_reason"], "explanation_stop")
        self.assertIsNone(reader._vec["v"])
        self.assertEqual(reader.n_hook_calls, 1)
        np.testing.assert_array_equal(vectors, original)
        reader._handle.remove()

    def test_nla_injection_state_clears_when_generation_fails(self):
        block = torch.nn.Identity()
        model = SimpleNamespace(model=SimpleNamespace(layers=[torch.nn.Identity(), block]))
        reader = SimpleNamespace(model=model, name="nla", device="cpu", tokenizer=Tokenizer(), ids=[9, 8], marker=1,
                                 inject_layer_idx=1, _vec={"v": None}, n_hook_calls=0,
                                 _handle=block.register_forward_hook(lambda *_: None))
        install_e56_nla_hook(reader)
        def fail(**kwargs):
            raise RuntimeError("mock generation failure")
        model.generate = fail
        with self.assertRaisesRegex(RuntimeError, "mock generation failure"):
            native_batch(reader, np.ones((2, 5120), np.float16), kind="nla", go=GO,
                         capture_seal_sha="a" * 64, bank_manifest_sha="b" * 64)
        self.assertIsNone(reader._vec["v"])
        reader._handle.remove()

    def test_oracle_batches_vectors_and_uses_layer44_native_carrier(self):
        from projects.g_agreement.core.config import OLENS_PROMPT
        vectors = np.vstack([np.arange(1, 5121), np.arange(5120, 0, -1)]).astype(np.float16)
        original = vectors.copy()
        calls = []
        parameter = torch.nn.Parameter(torch.ones(1), requires_grad=False)
        model = SimpleNamespace(parameters=lambda: iter([parameter]), generation_config=SimpleNamespace(eos_token_id=0),
                                get_input_embeddings=lambda: (lambda x: torch.ones(*x.shape, 5120, dtype=torch.bfloat16)))
        def generate(**kwargs):
            calls.append(kwargs)
            self.assertNotIn("input_ids", kwargs)
            self.assertEqual(kwargs["inputs_embeds"].shape, (2, 2, 5120))
            self.assertEqual(kwargs["attention_mask"].tolist(), [[1, 1], [1, 1]])
            self.assertFalse(kwargs["do_sample"])
            self.assertEqual(kwargs["max_new_tokens"], 128)
            self.assertEqual(kwargs["num_return_sequences"], 1)
            v = torch.as_tensor(vectors).float()
            expected = (16000 * v / v.norm(dim=-1, keepdim=True)).to(torch.bfloat16)
            self.assertTrue(torch.equal(kwargs["inputs_embeds"][:, 1], expected))
            return torch.tensor([[1, 0], [2, 0]])
        model.generate = generate
        def carrier(layer):
            self.assertEqual(layer, 44)
            return [9, 8], 1, "marker", 8
        reader = SimpleNamespace(name="olens", alpha=16000, prompt=OLENS_PROMPT,
                                 target=SimpleNamespace(model=model, tokenizer=Tokenizer()), carrier=carrier)
        result = native_batch(reader, vectors, kind="oracle", go=GO,
                              capture_seal_sha="a" * 64, bank_manifest_sha="b" * 64)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(r["capture_layer"] == 44 and r["max_new_tokens"] == 128 for r in result))
        np.testing.assert_array_equal(vectors, original)


class NativeAccountingTests(unittest.TestCase):
    def test_retrieval_reservation_is_required_and_checked_before_loading(self):
        sources = {name: "d" * 64 for name in (
            "projects/g_agreement/e73/native.py", "projects/g_agreement/e73/custody.py",
            "projects/g_agreement/core/config.py", "projects/g_agreement/core/model.py",
            "projects/g_agreement/core/readers.py", "projects/g_agreement/core/generate.py",
            "projects/g_agreement/core/accounting.py")}
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            args = SimpleNamespace(inputs=d / "synthetic.npz", index=d / "index.json",
                                   admission=d / "admission.json", repo=d)
            # Deliberately not an NPZ: budget rejection must precede loading
            # either a model or any activation arrays.
            args.inputs.write_bytes(b"synthetic budget-test placeholder")
            write_json(args.index, {"schema": "e73-reader-inputs-v1", "labels_present": False,
                       "bank_manifest_sha256": "b" * 64,
                       "shards": [{"file": args.inputs.name, "sha256": sha256(args.inputs), "count": 1}]})
            base = {"schema": "e73-admission-v1", "track": "C", "authorized_by": "I-2",
                    "sampler_commit": "a" * 40, "input_sha256": sha256(args.inputs),
                    "bank_manifest_sha256": "b" * 64, "gpu_count": 1, "gpu_seconds_cap": 1000,
                    "prior_track_gpu_seconds": 19000, "forecast_gpu_seconds": 700, "staging_cap_seconds": 900,
                    "combined_spend_before_usd": 100, "launch_spend_cap_usd": 10, "daily_ceiling_usd": 300,
                    "source_files": sources}
            for value in ("MISSING", None, -1, True, "300", float("nan"), float("inf"), float("-inf")):
                auth = dict(base)
                if value != "MISSING":
                    auth["retrieval_allowance_seconds"] = value
                args.admission.write_text(json.dumps(auth))
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, "retrieval_allowance_seconds"):
                    run(args, reader_loader=lambda kind: self.fail("loaded before retrieval validation"))
            # The old compute-only guard accepts 19,000 + 1,000; reserving
            # staging and retrieval raises this to 21,601 > the six-hour cap.
            write_json(args.admission, {**base, "retrieval_allowance_seconds": 701})
            with self.assertRaisesRegex(ValueError, "staging and retrieval reservations"):
                run(args, reader_loader=lambda kind: self.fail("loaded past all-in cap"))
            # Exactly 21,600 seconds and a zero reserve are allowed. Stop at the
            # next source check, without GO files, activation reads or a model.
            for reserve in (700, 0):
                write_json(args.admission, {**base, "retrieval_allowance_seconds": reserve})
                with patch.object(sys.modules[run.__module__], "check_source_files",
                           side_effect=RuntimeError("budget accepted; source check reached")):
                    with self.subTest(reserve=reserve), self.assertRaisesRegex(RuntimeError, "budget accepted"):
                        run(args, reader_loader=lambda kind: self.fail("unexpected model load"))

    def test_warmed_forecast_charges_cold_batch_and_reserves_unstarted_nla(self):
        completed = {"oracle": 8, "nla": 0}
        timings = {"oracle": [(8, 100)], "nla": []}
        priors = {"oracle": 2, "nla": 3}
        fits, forecast, states, _ = warmed_native_admission(
            120, completed, 25, timings, priors, 50, 1000, "oracle")
        self.assertTrue(fits)
        self.assertIsNone(forecast)
        self.assertEqual(states, {"oracle": "PENDING", "nla": "NOT_STARTED"})
        # 120 elapsed + 50 setup + 32 rounded NLA positions * 3 seconds.
        self.assertFalse(warmed_native_admission(
            120, completed, 25, timings, priors, 50, 330, "oracle")[0])
        timings["oracle"].append((8, 8))
        completed["oracle"] += 8
        fits, forecast, states, rates = warmed_native_admission(
            128, completed, 25, timings, priors, 50, 1000, "oracle")
        self.assertTrue(fits)
        self.assertEqual(rates, {"oracle": 1, "nla": 3})
        self.assertEqual(forecast, 128 + 16 + 50 + 32 * 3)
        self.assertEqual(states["oracle"], "MEASURED")
        self.assertFalse(warmed_native_admission(
            128, completed, 25, timings, priors, 50, 360, "oracle")[0])

    def test_switch_has_no_new_staging_allowance_or_clock_reset(self):
        clock = [0.0]
        def loader(kind):
            clock[0] += {"oracle": 100, "nla": 50}[kind]
            return kind
        with tempfile.TemporaryDirectory() as t, patch(
                "projects.g_agreement.e73.native.time.monotonic", side_effect=lambda: clock[0]):
            d = Path(t)
            _, first = load_native_ready("oracle", loader, destination=d,
                                        initial_staging_seconds=700, worker_started_monotonic=0)
            clock[0] = 950  # Later generation elapsed beyond the original staging cap.
            _, second = load_native_ready("nla", loader, destination=d,
                                         initial_staging_seconds=700, worker_started_monotonic=0)
            self.assertEqual(first["staging_through_first_readiness_seconds"], 800)
            self.assertEqual(second["worker_elapsed_at_readiness_seconds"], 1000)
            self.assertEqual(second["model_load_seconds"], 50)
            self.assertFalse(second["staging_deadline_applies"])
            self.assertEqual(second["new_staging_allowance_seconds"], 0)
            self.assertEqual(second["phase"], "CONTINUOUS_MODEL_SWITCH")

    def test_slow_initial_loader_is_killed_by_remaining_staging_deadline(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            code = ("from pathlib import Path\nimport time\n"
                    "from projects.g_agreement.e73.native import load_native_ready\n"
                    "from projects.g_agreement.e73.custody import hard_deadline\n"
                    f"destination=Path({str(d)!r})\n"
                    "with hard_deadline(2, destination/'COMPUTE_TIMEOUT.json'):\n"
                    "    load_native_ready('oracle', lambda kind: time.sleep(5), destination=destination,\n"
                    "        initial_staging_seconds=.15, worker_started_monotonic=time.monotonic(),\n"
                    "        staging_cap_seconds=.25)\n"
                    "(destination/'READER_SEAL.json').write_text('incorrect continuation')\n")
            result = subprocess.run([sys.executable, "-c", code], timeout=3, capture_output=True)
            self.assertEqual(result.returncode, 124, result.stderr.decode())
            self.assertLessEqual(json.loads((d / "STAGING_TIMEOUT.json").read_text())["cap_seconds"], .1)
            self.assertFalse((d / "MODEL_READY_oracle.json").exists())
            self.assertFalse((d / "READER_SEAL.json").exists())
            self.assertFalse((d / "COMPUTE_TIMEOUT.json").exists())

    def test_slow_model_switch_is_killed_by_original_compute_deadline(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            code = ("from pathlib import Path\nimport time\n"
                    "from projects.g_agreement.e73.native import load_native_ready\n"
                    "from projects.g_agreement.e73.custody import hard_deadline\n"
                    f"destination=Path({str(d)!r})\n"
                    "start=time.monotonic()\n"
                    "with hard_deadline(.15, destination/'COMPUTE_TIMEOUT.json'):\n"
                    "    load_native_ready('oracle', lambda kind: None, destination=destination,\n"
                    "        initial_staging_seconds=0, worker_started_monotonic=start)\n"
                    "    load_native_ready('nla', lambda kind: time.sleep(5), destination=destination,\n"
                    "        initial_staging_seconds=0, worker_started_monotonic=start)\n"
                    "(destination/'READER_SEAL.json').write_text('incorrect continuation')\n")
            result = subprocess.run([sys.executable, "-c", code], timeout=3, capture_output=True)
            self.assertEqual(result.returncode, 124, result.stderr.decode())
            self.assertTrue((d / "MODEL_READY_oracle.json").exists())
            self.assertTrue((d / "COMPUTE_TIMEOUT.json").exists())
            self.assertFalse((d / "MODEL_READY_nla.json").exists())
            self.assertFalse((d / "STAGING_TIMEOUT.json").exists())
            self.assertFalse((d / "READER_SEAL.json").exists())

    def test_worker_retains_every_cold_readout_and_charges_both_loads_once(self):
        repo = Path(__file__).resolve().parents[3]
        sources = ["projects/g_agreement/e73/native.py", "projects/g_agreement/e73/custody.py",
                   "projects/g_agreement/core/config.py", "projects/g_agreement/core/model.py",
                   "projects/g_agreement/core/readers.py", "projects/g_agreement/core/generate.py",
                   "projects/g_agreement/core/accounting.py"]
        with tempfile.TemporaryDirectory() as t:
            d, clock, loads, unloads = Path(t), [0.0], [], []
            args = SimpleNamespace(inputs=d / "readers.npz", index=d / "index.json", admission=d / "admission.json",
                                   go=d / "go.json", forecast_proof=d / "proof.json", repo=repo,
                                   out=d / "out", staging_started_unix=0)
            ids = [f"{i:032x}" for i in range(24)]
            np.savez(args.inputs, ids=np.array(ids), block44=np.ones((24, 5120), np.float16),
                     block42=np.ones((24, 5120), np.float16))
            write_json(args.index, {"schema": "e73-reader-inputs-v1", "labels_present": False,
                       "bank_manifest_sha256": "b" * 64,
                       "shards": [{"file": args.inputs.name, "sha256": sha256(args.inputs), "count": 24}]})
            write_json(args.go, {**GO, "capture_seal_sha256": sha256(args.index)})
            write_json(args.forecast_proof, {"schema": "e73-forecast-proof-v1", "verified_by": "I-2",
                       "commit": GO["jforecast_commit"], "artifact_sha256": GO["jforecast_sha256"]})
            auth = {"schema": "e73-admission-v1", "track": "C", "authorized_by": "I-2",
                    "sampler_commit": "a" * 40, "input_sha256": sha256(args.inputs),
                    "bank_manifest_sha256": "b" * 64, "gpu_count": 1, "gpu_seconds_cap": 3000,
                    "prior_track_gpu_seconds": 0, "forecast_gpu_seconds": 1000, "staging_cap_seconds": 900,
                    "retrieval_allowance_seconds": 300,
                    "combined_spend_before_usd": 100, "launch_spend_cap_usd": 10, "daily_ceiling_usd": 300,
                    "native_seconds_per_item": {"oracle": 2, "nla": 3}, "nla_setup_seconds": 50,
                    "run_id": "opaque-cpu-test", "run_kind": "real", "runtime_commit": "f" * 40,
                    "source_files": {p: sha256(repo / p) for p in sources}, "staging_readiness_policy": STAGING_POLICY}
            auth["code_sha256"] = hashlib.sha256(json.dumps(auth["source_files"], sort_keys=True,
                                                          separators=(",", ":")).encode()).hexdigest()
            write_json(args.admission, auth)
            original_admission = args.admission.read_bytes()
            def loader(kind):
                loads.append(kind)
                clock[0] += {"oracle": 100, "nla": 50}[kind]
                return kind
            calls = {"oracle": 0, "nla": 0}
            def batch(reader, vectors, **kwargs):
                kind = kwargs["kind"]
                self.assertEqual(reader, kind)
                self.assertEqual(len(vectors), 8)
                clock[0] += ([100, 8, 8] if kind == "oracle" else [150, 16, 16])[calls[kind]]
                calls[kind] += 1
                return [{"synthetic_test_only": True} for _ in vectors]
            with patch("projects.g_agreement.e73.native.time.monotonic", side_effect=lambda: clock[0]), \
                    patch("projects.g_agreement.e73.native.time.time", return_value=700):
                result = run(args, reader_loader=loader, reader_unloader=lambda kind, reader: unloads.append(kind), batch_fn=batch)
                # A stale admission must reject before invoking even the mock loader.
                del auth["staging_readiness_policy"]
                write_json(args.admission, auth)
                args.out = d / "bad"
                with self.assertRaisesRegex(ValueError, "readiness policy"):
                    run(args, reader_loader=lambda kind: self.fail("loaded without policy binding"))
                auth["staging_readiness_policy"] = STAGING_POLICY
                auth["code_sha256"] = "0" * 64
                write_json(args.admission, auth)
                with self.assertRaisesRegex(ValueError, "canonical source map"):
                    run(args, reader_loader=lambda kind: self.fail("loaded without code provenance"))
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["elapsed_seconds"], 448)
            self.assertEqual(result["initial_staging_seconds"], 700)
            self.assertEqual(loads, ["oracle", "nla"])
            self.assertEqual(unloads, loads)
            self.assertEqual(result["retained_cold_batches"]["nla"], {"count": 8, "seconds": 150})
            self.assertEqual(result["completed"], {"oracle": 24, "nla": 24})
            self.assertEqual((d / "out" / "ADMISSION.json").read_bytes(), original_admission)
            for kind in ("oracle", "nla"):
                rows = [json.loads(line) for line in (d / "out" / (kind + ".jsonl")).read_text().splitlines()]
                self.assertEqual([r["id"] for r in rows], ids)
            verified = verify_seal(d / "out", "READER_SEAL.json")
            self.assertEqual(verified["status"], "COMPLETE")
            self.assertIn("MODEL_READY_nla.json", verified["files"])
            self.assertEqual(json.loads((d / "out" / "PROGRESS.json").read_text())["forecast_seconds"], 448)


if __name__ == "__main__":
    unittest.main()
