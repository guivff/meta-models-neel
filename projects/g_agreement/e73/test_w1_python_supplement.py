"""After-capture source-specific W1 fixture supplement; no scientific-bank reads.

The original 400 fixtures and their generator remain byte-for-byte unchanged.
This adds ten independently labelled Python unit examples to the original forty
Python W1 examples, without replacing their ten legacy JavaScript companions.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import unittest

from .states import extract_states

HERE = Path(__file__).resolve().parent
FROZEN_SAMPLER_COMMIT = "345ae3de8605fbbdc6534e21af061e4d80bece0c"
FROZEN_HASHES = {
    "hand_examples.json": "2bf9543c3130cd529de4c476ffe2ee188762c2f8532ba41caeffac0c4cc34d5f",
    "fixtures.py": "34533f11406b97f4865f4cd5f2b560519a2ea77b03972e64d90e4dfb7622eb2c",
    "w1_python_supplement.json": "b6a8b6480b71d15caeb6f188d85f5503e45e3c93e6d6b13a5fca0df5c57dc55a",
}


class PythonW1Supplement(unittest.TestCase):
    def test_50_python_cases_without_changing_original_400(self):
        for name, expected_sha in FROZEN_HASHES.items():
            self.assertEqual(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), expected_sha, name)
        original = json.loads((HERE / "hand_examples.json").read_text())
        self.assertEqual(len(original), 400)
        self.assertEqual(Counter(r["state"] for r in original), {f"W{i}": 50 for i in range(1, 9)})
        w1_original = [r for r in original if r["state"] == "W1"]
        self.assertEqual(Counter(r["language"] for r in w1_original), {"python": 40, "javascript": 10})
        original_python = [r for r in w1_original if r["language"] == "python"]
        supplemental = json.loads((HERE / "w1_python_supplement.json").read_text())
        self.assertEqual(len(supplemental), 10)
        self.assertTrue(all(r["state"] == "W1" and r["language"] == "python" for r in supplemental))
        self.assertEqual(Counter(r["expected"] for r in supplemental), {0: 5, 1: 5})
        combined = original_python + supplemental
        self.assertEqual(len(combined), 50)
        self.assertEqual(len({r["id"] for r in combined}), 50)
        self.assertEqual(Counter(r["expected"] for r in combined), {0: 25, 1: 25})
        for row in combined:
            with self.subTest(id=row["id"], reason=row["reason"]):
                self.assertEqual(extract_states(row["text"], "python", [row["offset"]])["W1"], [row["expected"]])


if __name__ == "__main__":
    unittest.main()
