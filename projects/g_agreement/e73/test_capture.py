"""CPU tests of custody, budget rejection and probe train/test separation."""
from __future__ import annotations

import hashlib
import json
import tarfile
import tempfile
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest
from pathlib import Path

from .capture import remaining_fits, save_capture_shard, warmed_capture_admission
from .custody import (archive_inputs, check_admission, check_go, seal, sha256,
                      validate_public, verify_seal, write_json)


def item(i=0):
    return {"id": f"{i:032x}", "input_ids": [100] * 256}


def admission():
    return {"schema": "e73-admission-v1", "track": "C", "authorized_by": "I-2",
            "sampler_commit": "a" * 40, "input_sha256": "b" * 64,
            "bank_manifest_sha256": "c" * 64, "gpu_count": 1,
            "gpu_seconds_cap": 1000, "prior_track_gpu_seconds": 100,
            "forecast_gpu_seconds": 700, "staging_cap_seconds": 900,
            "combined_spend_before_usd": 110, "launch_spend_cap_usd": 10,
            "daily_ceiling_usd": 300, "source_files": {"capture.py": "d" * 64}}


class CustodyTests(unittest.TestCase):
    def test_cold_compilation_charged_without_poisoning_warmed_forecast(self):
        fits, forecast = warmed_capture_admission(100, 4, 4000, [(4, 100)], 3600)
        self.assertTrue(fits)
        self.assertIsNone(forecast)  # Warmed admission cannot be claimed yet.
        fits, forecast = warmed_capture_admission(102, 8, 4000, [(4, 100), (4, 2)], 3600)
        self.assertTrue(fits)
        self.assertEqual(forecast, 102 + 3992 * .5)  # All 100 cold seconds remain charged.
        self.assertFalse(warmed_capture_admission(2900, 4, 4000, [(4, 2900)], 3600)[0])

    def test_public_schema_rejects_label_or_source(self):
        validate_public([item()])
        for field in ("label", "state", "split", "text", "doc_hash"):
            with self.assertRaises(ValueError):
                validate_public([{**item(), field: "forbidden"}])

    def test_public_schema_rejects_wrong_tokens_and_duplicate(self):
        for rows in ([item(), item()], [{**item(), "input_ids": [1] * 255}],
                     [{**item(), "input_ids": [True] * 256}], [{**item(), "id": "W1_A_001"}],
                     [{**item(), "input_ids": [248320] * 256}]):
            with self.assertRaises(ValueError):
                validate_public(rows)

    def test_budget_and_binding_fail_closed(self):
        check_admission(admission(), "b" * 64, "c" * 64)
        bad = [("forecast_gpu_seconds", 801), ("prior_track_gpu_seconds", 21000),
               ("combined_spend_before_usd", 295), ("staging_cap_seconds", 901),
               ("input_sha256", "e" * 64), ("authorized_by", "worker"),
               ("sampler_commit", "not-committed"), ("forecast_gpu_seconds", float("nan"))]
        for key, value in bad:
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_admission({**admission(), key: value}, "b" * 64, "c" * 64)

    def test_forecast_retains_elapsed_and_buffer(self):
        fits, seconds = remaining_fits(100, 10, 100, [(10, 20)], 350)
        self.assertTrue(fits)
        self.assertEqual(seconds, 280)
        self.assertFalse(remaining_fits(101, 10, 100, [(10, 20)], 350)[0])
        with self.assertRaises(ValueError):
            remaining_fits(10, 0, 100, [], 350)

    def test_seal_is_immutable_and_detects_change(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            write_json(d / "data.json", {"value": 1})
            seal(d, "SEAL.json", [d / "data.json"])
            verify_seal(d, "SEAL.json")
            with self.assertRaises(FileExistsError):
                seal(d, "SEAL.json", [d / "data.json"])
            write_json(d / "data.json", {"value": 2})
            with self.assertRaises(ValueError):
                verify_seal(d, "SEAL.json")

    def test_archive_has_exact_opaque_records_and_no_private_map(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            manifest = d / "bank.json"
            write_json(manifest, {"schema": "mock-bank"})
            shards = archive_inputs([item(i) for i in range(5)], d, manifest_sha256=sha256(manifest), bank_manifest=manifest, max_rows=2)
            self.assertEqual([s["count"] for s in shards], [2, 2, 1])
            for summary in shards:
                with tarfile.open(d / summary["file"]) as tar:
                    self.assertEqual(set(tar.getnames()), {"inputs/items.jsonl", "inputs/MANIFEST.json", "inputs/BANK_MANIFEST.json"})
                    data = tar.extractfile("inputs/items.jsonl").read()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), summary["input_sha256"])
                    validate_public([json.loads(x) for x in data.splitlines()])
            with self.assertRaises(FileExistsError):
                archive_inputs([item()], d, manifest_sha256=sha256(manifest), bank_manifest=manifest)

    def test_go_requires_forecast_and_preserves_judging_gate(self):
        go = {"schema": "e73-reader-go-v1", "authorized_by": "I-2", "action": "GO",
              "capture_seal_sha256": "a" * 64, "bank_manifest_sha256": "b" * 64,
              "jforecast_commit": "c" * 40, "jforecast_sha256": "d" * 64,
              "judging_authorized": False}
        check_go(go, capture_seal_sha="a" * 64, input_manifest_sha="b" * 64)
        for key in ("jforecast_commit", "jforecast_sha256", "capture_seal_sha256", "judging_authorized"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_go({**go, key: None}, capture_seal_sha="a" * 64, input_manifest_sha="b" * 64)

    def test_hard_deadline_interrupts_a_slow_operation(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "timeout.json"
            code = ("from pathlib import Path\nimport time\n"
                    "from projects.g_agreement.e73.custody import hard_deadline\n"
                    f"with hard_deadline(.1, Path({str(p)!r})):\n    time.sleep(5)\n")
            result = subprocess.run([sys.executable, "-c", code], timeout=3, capture_output=True)
            self.assertEqual(result.returncode, 124)
            self.assertEqual(json.loads(p.read_text())["status"], "HARD_TIMEOUT")

    def test_staging_deadline_interrupts_slow_model_loader_without_capture_seal(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            code = ("from pathlib import Path\nimport time\n"
                    "from projects.g_agreement.e73.capture import load_ready\n"
                    "from projects.g_agreement.e73.custody import hard_deadline\n"
                    f"destination=Path({str(d)!r})\n"
                    "with hard_deadline(2, destination/'COMPUTE_TIMEOUT.json'):\n"
                    "    load_ready(lambda: time.sleep(5), destination=destination,\n"
                    "               initial_staging_seconds=.15, worker_started_monotonic=time.monotonic(),\n"
                    "               staging_cap_seconds=.25)\n"
                    "(destination/'CAPTURE_SEAL.json').write_text('incorrect continuation')\n")
            result = subprocess.run([sys.executable, "-c", code], timeout=3, capture_output=True)
            self.assertEqual(result.returncode, 124)
            timeout = json.loads((d / "STAGING_TIMEOUT.json").read_text())
            self.assertLessEqual(timeout["cap_seconds"], .1)
            self.assertFalse((d / "MODEL_READY.json").exists())
            self.assertFalse((d / "CAPTURE_SEAL.json").exists())
            self.assertFalse((d / "COMPUTE_TIMEOUT.json").exists())


class NumericalTests(unittest.TestCase):
    def test_capture_run_with_mock_model_seals_before_any_reader(self):
        import numpy as np
        from .capture import run
        repo = Path(__file__).resolve().parents[3]
        source_paths = ["projects/g_agreement/e73/capture.py", "projects/g_agreement/e73/custody.py",
                        "projects/g_agreement/core/model.py", "projects/g_agreement/core/config.py",
                        "projects/g_agreement/core/accounting.py"]
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            inputs, manifest, auth = d / "items.jsonl", d / "manifest.json", d / "admission.json"
            inputs.write_text("\n".join(json.dumps(item(i)) for i in range(2)) + "\n")
            write_json(manifest, {"binding": "mock"})
            value = {**admission(), "input_sha256": sha256(inputs), "bank_manifest_sha256": sha256(manifest),
                     "source_files": {p: sha256(repo / p) for p in source_paths}}
            write_json(auth, value)
            args = SimpleNamespace(inputs=inputs, manifest=manifest, admission=auth, repo=repo,
                                   out=d / "capture", staging_started_unix=time.time(), batch_size=2)
            def capture_fn(model, ids):
                return {44: np.zeros((len(ids), 256, 5120), dtype=np.float16),
                        42: np.zeros((len(ids), 5120), dtype=np.float16)}
            result = run(args, loader=lambda: SimpleNamespace(model=None), capture_fn=capture_fn)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["reader_outputs"], 0)
            self.assertGreaterEqual(result["elapsed_seconds"], result["readiness_elapsed_seconds"])
            self.assertAlmostEqual(result["staging_through_readiness_seconds"],
                                   result["initial_staging_seconds"] + result["readiness_elapsed_seconds"])
            self.assertLessEqual(result["staging_through_readiness_seconds"], 900)
            ready = json.loads((args.out / "MODEL_READY.json").read_text())
            self.assertEqual(ready["status"], "MODEL_READY")
            self.assertTrue(ready["readiness_included_in_worker_elapsed"])
            self.assertEqual(verify_seal(args.out, "CAPTURE_SEAL.json")["status"], "COMPLETE")
            value["source_files"][source_paths[0]] = "0" * 64
            write_json(auth, value)
            args.out = d / "bad"
            with self.assertRaises(ValueError):
                run(args, loader=lambda: self.fail("model loaded before failed source gate"))

    def test_native_rejects_missing_go_before_import_or_generation(self):
        import numpy as np
        from .native import native_batch, validate_reader_shard
        with self.assertRaises(ValueError):
            native_batch(None, np.zeros((1, 5120)), kind="nla", go={},
                         capture_seal_sha="a" * 64, bank_manifest_sha="b" * 64)

    def test_probe_rejects_swapped_labels_and_gate_before_capture_load(self):
        from .probes import run
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            labels, gate, manifest = d / "labels.jsonl", d / "gate.json", d / "manifest.json"
            labels.write_text(json.dumps({"id": item()["id"], "state": "W1", "split": "dev", "label": 0}) + "\n")
            write_json(gate, {"included_states": ["W1"]})
            write_json(manifest, {"private_labels_sha256": "0" * 64, "gate_report_sha256": sha256(gate)})
            args = SimpleNamespace(gate=gate, labels=labels, manifest=manifest, capture=[d / "does-not-exist"], out=d / "out")
            with self.assertRaisesRegex(ValueError, "private labels"):
                run(args)
            write_json(manifest, {"private_labels_sha256": sha256(labels), "gate_report_sha256": "0" * 64})
            with self.assertRaisesRegex(ValueError, "BOW gate"):
                run(args)

    def test_capture_shard_exact_shapes_no_pickle_and_size(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            arrays = {44: np.ones((2, 256, 5120), dtype=np.float16), 42: np.ones((2, 5120), dtype=np.float16)}
            p = save_capture_shard(d, 0, [item(0), item(1)], arrays)
            self.assertLessEqual(p.stat().st_size, 20_000_000)
            with np.load(p, allow_pickle=False) as x:
                self.assertEqual(x["block44"].shape, (2, 256, 5120))
                self.assertEqual(x["block42"].dtype, np.float16)
                self.assertEqual(x["ids"].tolist(), [item(0)["id"], item(1)["id"]])
            arrays[42][0, 0] = np.nan
            with self.assertRaises(ValueError):
                save_capture_shard(d, 1, [item(0), item(1)], arrays)

    def test_fit_uses_dev_only_and_keeps_fixed_positive_class(self):
        import numpy as np
        from .probes import fit_probe
        rng = np.random.default_rng(20261027)
        dy = np.tile([0, 1], 50)
        ty = np.tile([0, 1], 20)
        dx = rng.normal(size=(100, 6)); dx[:, 0] += dy * 8
        tx = rng.normal(size=(40, 6)); tx[:, 0] += ty * 8
        good = fit_probe(dx, dy, tx, ty)
        opposite = fit_probe(dx, dy, tx, 1 - ty)
        self.assertGreater(good["test_auroc"], .95)
        self.assertLess(opposite["test_auroc"], .05)
        np.testing.assert_array_equal(good["direction"], opposite["direction"])
        np.testing.assert_allclose(good["scaler_mean"], dx.mean(axis=0))


if __name__ == "__main__":
    unittest.main()
