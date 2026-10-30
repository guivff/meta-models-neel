"""CPU checks of smoke custody, setup and failure gates; never import vLLM."""
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import torch

from projects.g_agreement.e74 import smoke


def fixture():
    return {"schema_version": 1, "token_ids": [154822, 154824, 12, 13], "read_position": 3,
            "expected_readout_sha256": smoke.text_hash("* example"), "source_repo": smoke.DATA_REPO,
            "source_revision": smoke.DATA_REVISION, "tid": "opaque-fixture", "pos": 3,
            "reference_field": "rl_greedy", "adapter_path": smoke.LENS_PATH}


class FakeEngine:
    def __init__(self, output="* example"):
        self.n_workers = 4
        self.prompt_ids = [1]*70
        self.prompt_ids[63] = 154518
        self.mpos = 63
        self.merged = None
        self.output = output
        self.calls = []

    def capture_h51(self, ids, positions):
        self.calls.append(("capture", ids, positions))
        return [torch.ones((1, 6144))]

    def set_lens(self, directory, keep_base):
        self.calls.append(("merge", directory, keep_base))
        self.merged = directory

    def verbalize(self, vec, **kwargs):
        self.calls.append(("readout", kwargs))
        return [[self.output]]


def runtime():
    prompt = ("You are shown an internal activation vector from a language model, enclosed in <concept> tags. "
              "It encodes what the model is about to generate next.\n\n"
              "Write the single most important piece of content in this activation as one line starting with '* '.\n\n"
              "<concept>◉</concept>")
    return types.SimpleNamespace(BASE_REPO=smoke.BASE_REPO, READ_LAYER=51, N_LAYERS=78, HIDDEN=6144,
                                 MARKER_ID=154518, ALPHA=54.1, EOS_ID=154820, LENS1_INSTRUCTION=prompt)


class SmokeTests(unittest.TestCase):
    def test_rejects_label_and_extra_field_before_gpu(self):
        value = fixture()
        value["label"] = "A"
        with self.assertRaises(ValueError):
            smoke.validate_fixture(value)

    def test_rejects_wrong_revision_and_boolean_position(self):
        for key, value in [("source_revision", "main"), ("read_position", True), ("reference_field", "rl_s1")]:
            obj = fixture()
            obj[key] = value
            with self.assertRaises(ValueError):
                smoke.validate_fixture(obj)

    def test_rejects_truncation_or_sink_and_invalid_ids(self):
        for transform in [lambda x: x.update(token_ids=[1]*1152),
                          lambda x: x.update(read_position=0, pos=0),
                          lambda x: x.update(token_ids=[1, 2, 3, 154856])]:
            obj = fixture()
            transform(obj)
            with self.assertRaises(ValueError):
                smoke.validate_fixture(obj)

    def test_exact_pass_has_one_capture_then_merge_then_one_greedy(self):
        engine = FakeEngine()
        result = smoke.one_readout(fixture(), runtime(), engine, "adapter")
        self.assertEqual(result["status"], "PASS_EXACT")
        self.assertEqual([x[0] for x in engine.calls], ["capture", "merge", "readout"])
        self.assertEqual(engine.calls[0][1], [fixture()["token_ids"]])
        self.assertEqual(engine.calls[-1][1], dict(n=1, temperature=0.0, cap=16, seed=0, alpha=54.1))

    def test_nonexact_stops_without_retry_or_fuzzy_match(self):
        engine = FakeEngine("* Example")
        result = smoke.one_readout(fixture(), runtime(), engine, "adapter")
        self.assertEqual(result["status"], "STOP_REVIEW_NOT_IDENTICAL")
        self.assertFalse(result["exact_reference_match"])
        self.assertEqual(len(engine.calls), 3)

    def test_merged_base_or_wrong_prompt_fails_before_capture(self):
        for change in [lambda x: setattr(x, "merged", "already-merged"),
                       lambda x: setattr(x, "mpos", 62),
                       lambda x: setattr(x, "n_workers", 8)]:
            engine = FakeEngine()
            change(engine)
            with self.assertRaises(ValueError):
                smoke.one_readout(fixture(), runtime(), engine, "adapter")
            self.assertFalse(engine.calls)

    def test_hash_binding_and_create_only_output(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"fixture.json"
            smoke.canonical_write(p, fixture())
            self.assertEqual(smoke.load_bound_json(p, smoke.sha256(p)), fixture())
            with self.assertRaises(ValueError):
                smoke.load_bound_json(p, "0"*64)
            with self.assertRaises(FileExistsError):
                smoke.canonical_write(p, {})

    def test_quant_config_rejects_shared_cache_symlink_and_hardlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = root / "original.json"
            original.write_text("{}")
            smoke.require_private_quant_copy(original)
            linked = root / "linked.json"
            linked.symlink_to(original)
            with self.assertRaises(ValueError):
                smoke.require_private_quant_copy(linked)
            hard = root / "hard.json"
            hard.hardlink_to(original)
            with self.assertRaises(ValueError):
                smoke.require_private_quant_copy(original)

    def test_staging_receipt_binds_full_hashes_and_file_identity(self):
        with tempfile.TemporaryDirectory() as td:
            model, adapter = Path(td) / "model", Path(td) / "adapter"
            model.mkdir()
            adapter.mkdir()
            (model / "hf_quant_config.json").write_text("{}")
            (model / "model-00001.safetensors").write_bytes(b"frozen base")
            (adapter / "adapter_model.safetensors").write_bytes(b"frozen RL0100")
            manifest = {"base": {"repo": smoke.BASE_REPO, "revision": smoke.BASE_REVISION, "files": {}},
                        "lens": {"repo": smoke.LENS_REPO, "revision": smoke.LENS_REVISION,
                                 "adapter_path": smoke.LENS_PATH, "files": {}}}
            files = {}
            for area, directory, entry in [("base", model, "base"), ("adapter", adapter, "lens")]:
                for path in directory.iterdir():
                    digest = smoke.sha256(path)
                    manifest[entry]["files"][path.name] = {"sha256": digest, "bytes": path.stat().st_size}
                    files[area + "/" + path.name] = {"sha256": digest, **smoke.stat_identity(path)}
            receipt = {"schema_version": 1, "experiment": "E74", "base_repo": smoke.BASE_REPO,
                       "base_revision": smoke.BASE_REVISION, "lens_repo": smoke.LENS_REPO,
                       "lens_revision": smoke.LENS_REVISION, "adapter_path": smoke.LENS_PATH,
                       "model_dir": str(model.resolve()), "adapter_dir": str(adapter.resolve()),
                       "storage": "local_nvme", "completed_epoch": 900,
                       "full_weight_sha256_verified": True, "canonical_cache_unchanged": True,
                       "weight_manifest_sha256": smoke.WEIGHT_MANIFEST_SHA256,
                       "fork_archive_sha256": smoke.FORK_SHA256, "files": files, "runtime_versions": {}}
            with patch.object(smoke.time, "time", return_value=1900):
                for completed in (900, 1001, 1900):
                    receipt["completed_epoch"] = completed
                    self.assertEqual(smoke.check_staging_receipt(receipt, manifest, model, adapter, 1000)
                                     ["files_bound_to_cpu_checksums"], 3)
                receipt["completed_epoch"] = 1901
                with self.assertRaisesRegex(ValueError, "complete now"):
                    smoke.check_staging_receipt(receipt, manifest, model, adapter, 1000)
            with patch.object(smoke.time, "time", return_value=2000):
                with self.assertRaisesRegex(ValueError, "within 900 seconds"):
                    smoke.check_staging_receipt(receipt, manifest, model, adapter, 1000)
            receipt["completed_epoch"] = 1001
            receipt["files"]["adapter/adapter_model.safetensors"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "checksum"):
                smoke.check_staging_receipt(receipt, manifest, model, adapter, 1000)
            receipt["files"]["adapter/adapter_model.safetensors"]["sha256"] = smoke.sha256(adapter / "adapter_model.safetensors")
            (model / "model-00001.safetensors").write_bytes(b"changed base")
            with self.assertRaisesRegex(ValueError, "identity"):
                smoke.check_staging_receipt(receipt, manifest, model, adapter, 1000)

    def test_missing_staging_receipt_or_wrong_fork_fails_closed(self):
        with self.assertRaises(ValueError):
            smoke.check_staging_receipt({}, {}, Path("model"), Path("adapter"), 1000)
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "stock-vllm.tar.gz"
            fake.write_bytes(b"not the author's fork")
            with self.assertRaisesRegex(ValueError, "fork archive digest"):
                smoke.verify_fork(fake)

    def test_deadline_counts_from_allocation_not_model_load(self):
        self.assertEqual(smoke.validate_deadline(1000, 2200, 2100), 100)
        for args in [(1000, 2201, 2100), (1000, 2200, 2201), (2200, 2300, 2100), (1000, float("inf"), 2100)]:
            with self.assertRaises(ValueError):
                smoke.validate_deadline(*args)


if __name__ == "__main__":
    unittest.main()
