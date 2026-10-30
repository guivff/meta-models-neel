"""Exact-archive CPU checks, including adversarial data and tar substitutions."""
from __future__ import annotations

import builtins
import copy
import gzip
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .custody import archive_inputs, sha256, write_json
from .preflight import CAPTURE_SOURCES, BANK_HASH_FIELDS, validate_archive


def digest(content):
    return hashlib.sha256(content).hexdigest()


def payload(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode()


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rows = [{"id": f"{i:032x}", "input_ids": [100 + i] * 256} for i in range(3)]
        self.bank = self.root / "BANK.json"
        self.bank_inputs = self.root / "items.jsonl"
        self.bank_inputs.write_bytes(b"".join(payload(row) for row in self.rows))
        self.bank_value = {"experiment": "E73", "stage": "BOW_GATE_SEALED", "items": 3,
                           "context_tokens": 256, "input_schema": ["id", "input_ids"],
                           **{k: "c" * 64 for k in BANK_HASH_FIELDS},
                           "code_sha256": {k: "d" * 64 for k in ("sources.py", "states.py", "sample.py", "bow.py")}}
        self.bank_value["items_sha256"] = sha256(self.bank_inputs)
        write_json(self.bank, self.bank_value)
        self.sources = {}
        for i, name in enumerate(sorted(CAPTURE_SOURCES)):
            source = self.root / f"source{i}.py"
            # A preflight that executed sources would fail this test immediately.
            source.write_text("import torch\nraise RuntimeError('source must not execute')\n")
            self.sources[name] = source
        self.hashes = {name: sha256(path) for name, path in self.sources.items()}
        summaries = archive_inputs(self.rows, self.root / "archive", manifest_sha256=sha256(self.bank),
                                   bank_manifest=self.bank, source_files=self.sources, max_rows=2)
        self.archive = self.root / "archive" / summaries[0]["file"]
        with tarfile.open(self.archive, "r:gz") as tar:
            self.members = {member.name: tar.extractfile(member).read() for member in tar}

    def validate(self, path=None, **kwargs):
        path = path or self.archive
        return validate_archive(path, bank_manifest=self.bank, bank_inputs=self.bank_inputs,
                                source_hashes=kwargs.pop("source_hashes", self.hashes),
                                expected_archive_sha256=kwargs.pop("expected_archive_sha256", sha256(path)), **kwargs)

    def write_archive(self, members=None, *, extras=()):
        path = self.root / "modified.tar.gz"
        with tarfile.open(path, "w:gz") as tar:
            for name, data in (members or self.members).items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            for info, data in extras:
                tar.addfile(info, io.BytesIO(data))
        return path

    def test_valid_exact_archive_compiles_without_gpu_imports_or_execution(self):
        original_import = builtins.__import__
        def no_gpu(name, *args, **kwargs):
            if name.split(".")[0] in ("torch", "transformers", "numpy", "peft"):
                self.fail("GPU/numerical library imported by CPU preflight")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", no_gpu):
            report = self.validate()
        self.assertEqual(report["status"], "PREFLIGHT_PASS")
        self.assertEqual(report["record_count"], 2)
        self.assertFalse(report["admission_checked"])
        self.assertFalse(report["grants_admission_or_go"])
        self.assertEqual(report["compiled_sources"], len(CAPTURE_SOURCES))

    def test_package_initializers_and_accounting_dependency(self):
        members = copy.deepcopy(self.members)
        members["projects/g_agreement/core/__init__.py"] = b"from . import accounting, config\n"
        members["projects/g_agreement/e73/__init__.py"] = b'"""E73 package."""\n'
        hashes = {name: digest(data) for name, data in members.items() if name.endswith(".py")}
        result = self.validate(self.write_archive(members), source_hashes=hashes)
        self.assertEqual(result["compiled_sources"], len(CAPTURE_SOURCES) + 2)
        missing = "projects/g_agreement/core/accounting.py"
        members.pop(missing); hashes.pop(missing)
        with self.assertRaisesRegex(ValueError, "required capture source"):
            self.validate(self.write_archive(members), source_hashes=hashes)

    def test_i2_admission_bound_to_exact_source_and_input(self):
        shard = json.loads(self.members["inputs/MANIFEST.json"])
        admission = {"schema": "e73-admission-v1", "track": "C", "authorized_by": "I-2",
                     "sampler_commit": "a" * 40, "input_sha256": shard["input_sha256"],
                     "bank_manifest_sha256": sha256(self.bank), "gpu_count": 1,
                     "gpu_seconds_cap": 1000, "prior_track_gpu_seconds": 100,
                     "forecast_gpu_seconds": 700, "staging_cap_seconds": 900,
                     "combined_spend_before_usd": 110, "launch_spend_cap_usd": 10,
                     "daily_ceiling_usd": 300, "source_files": self.hashes}
        self.assertTrue(self.validate(admission=admission)["admission_checked"])
        admission["source_files"] = {**self.hashes, "extra.py": "c" * 64}
        with self.assertRaises(ValueError):
            self.validate(admission=admission)

    def test_reject_unsafe_paths_types_duplicates_and_private_members(self):
        for name in ("/etc/passwd", "../evil.py", "./inputs/items.jsonl", "inputs\\items.jsonl",
                     "PRIVATE.json", "KEY.json", "labels.jsonl", "candidates.sqlite3",
                     "data/corpus.json", "GATE_REPORT.json", "projects/g_agreement/e73/states.py"):
            with self.subTest(name=name):
                info = tarfile.TarInfo(name); info.size = 2
                with self.assertRaises(ValueError):
                    self.validate(self.write_archive(extras=[(info, b"{}")]))
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind):
                info = tarfile.TarInfo("inputs/items.jsonl"); info.type = kind; info.linkname = "../private"
                with self.assertRaises(ValueError):
                    self.validate(self.write_archive(extras=[(info, b"")]))
        info = tarfile.TarInfo("inputs/MANIFEST.json"); info.size = 2
        with self.assertRaises(ValueError):
            self.validate(self.write_archive(extras=[(info, b"{}")]))

    def test_reject_labels_state_fields_bad_tokens_and_duplicate_ids(self):
        for field in ("label", "state", "split", "text", "PRIVATE", "key", "gate"):
            rows = [{**self.rows[0], field: "secret"}, self.rows[1]]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(self.replace_rows(rows))
        for replacement in ({"input_ids": [1] * 255}, {"input_ids": [True] * 256},
                            {"input_ids": [248320] * 256}, {"id": "W1_A_1"}):
            with self.subTest(replacement=str(replacement)[:40]), self.assertRaises(ValueError):
                self.validate(self.replace_rows([{**self.rows[0], **replacement}, self.rows[1]]))
        with self.assertRaises(ValueError):
            self.validate(self.replace_rows([self.rows[0], self.rows[0]]))

    def replace_rows(self, rows):
        members = copy.deepcopy(self.members)
        members["inputs/items.jsonl"] = b"".join(payload(row) for row in rows)
        shard = json.loads(members["inputs/MANIFEST.json"])
        shard.update(input_sha256=digest(members["inputs/items.jsonl"]), count=len(rows))
        members["inputs/MANIFEST.json"] = payload(shard)
        return self.write_archive(members)

    def test_no_well_formed_input_substitution_against_frozen_bank(self):
        rows = copy.deepcopy(self.rows[:2]); rows[0]["input_ids"][0] += 1
        with self.assertRaisesRegex(ValueError, "frozen public bank"):
            self.validate(self.replace_rows(rows))

    def test_manifest_schema_rejects_actual_private_data_and_hash_mismatch(self):
        for value in ("sports", [0, 1], {"W1": 0}):
            bank = {**self.bank_value, "private_labels_sha256": value}
            write_json(self.bank, bank)
            members = copy.deepcopy(self.members)
            members["inputs/BANK_MANIFEST.json"] = self.bank.read_bytes()
            shard = json.loads(members["inputs/MANIFEST.json"])
            shard["bank_manifest_sha256"] = sha256(self.bank)
            members["inputs/MANIFEST.json"] = payload(shard)
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.validate(self.write_archive(members))
        write_json(self.bank, self.bank_value)
        members = copy.deepcopy(self.members)
        members["inputs/MANIFEST.json"] = payload({**json.loads(members["inputs/MANIFEST.json"]), "labels": [0, 1]})
        with self.assertRaises(ValueError):
            self.validate(self.write_archive(members))
        with self.assertRaises(ValueError):
            self.validate(expected_archive_sha256="0" * 64)

    def test_missing_dependencies_changed_sources_and_invalid_python_fail(self):
        name = sorted(self.hashes)[0]
        for data, change_hash in ((b"print('changed')\n", False), (b"invalid syntax +\n", True)):
            members = copy.deepcopy(self.members); members[name] = data
            hashes = {**self.hashes, name: digest(data)} if change_hash else self.hashes
            with self.subTest(change_hash=change_hash), self.assertRaises(ValueError):
                self.validate(self.write_archive(members), source_hashes=hashes)
        members = copy.deepcopy(self.members); members.pop(name)
        with self.assertRaises(ValueError):
            self.validate(self.write_archive(members))

    def test_duplicate_json_fields_and_hidden_tar_payload_are_rejected(self):
        members = copy.deepcopy(self.members)
        members["inputs/items.jsonl"] = b'{"id":"' + b"0" * 32 + b'","id":"' + b"1" * 32 + b'","input_ids":[]}\n'
        with self.assertRaises(ValueError):
            self.validate(self.write_archive(members))
        raw = gzip.decompress(self.archive.read_bytes())
        hidden = self.root / "hidden.tar.gz"
        hidden.write_bytes(gzip.compress(raw + b"nonzero hidden payload"))
        with self.assertRaises(ValueError):
            self.validate(hidden)

    def test_compressed_and_expanded_size_limits_are_enforced(self):
        oversized = self.root / "large.tar.gz"
        with oversized.open("wb") as f:
            f.truncate(20_000_001)
        with self.assertRaises(ValueError):
            self.validate(oversized)
        bomb = self.root / "bomb.tar.gz"
        bomb.write_bytes(gzip.compress(b"0" * 1025))
        with patch("projects.g_agreement.e73.preflight.MAX_UNCOMPRESSED_BYTES", 1024), self.assertRaises(ValueError):
            self.validate(bomb)


if __name__ == "__main__":
    unittest.main()
