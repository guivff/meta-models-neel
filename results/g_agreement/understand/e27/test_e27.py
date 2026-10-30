"""Synthetic correctness and seal-failure checks; no real-data analysis."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

spec = spec_from_file_location("e27_analysis", Path(__file__).with_name("analyze.py"))
A = module_from_spec(spec)
spec.loader.exec_module(A)


class E27Tests(unittest.TestCase):
    def test_tied_auc_independent_algorithms(self):
        s = np.array([1.0, 0.0, 1.0, 3.0])
        y = np.array([1, 0, 0, 1])
        self.assertEqual(A.rank_auc(s, y), 0.875)
        self.assertEqual(A.pairwise_auc(s, y), 0.875)

    def test_orientation_invariance_and_complementarity(self):
        rng = np.random.default_rng(12)
        for _ in range(25):
            s = rng.integers(-3, 4, 20).astype(float)
            y = np.tile([0, 1], 10)
            self.assertAlmostEqual(A.rank_auc(-s, 1-y), A.pairwise_auc(s, y), places=14)
            self.assertAlmostEqual(A.rank_auc(s, y) + A.rank_auc(s, 1-y), 1, places=14)

    def test_vectorized_bootstrap_matches_manual_resamples(self):
        s = np.array([1, 2, 2, 0, -1, 4], float)
        y = np.array([1, 0, 1, 0, 0, 1])
        ix = np.random.default_rng(9).integers(0, 6, (70, 6))
        result = A.bootstrap_auc(s, y, ix)
        expected = [A.pairwise_auc(s[k], y[k]) for k in ix]
        np.testing.assert_allclose(result, expected, equal_nan=True, atol=1e-14)

    def test_one_class_bootstrap_reported(self):
        samples = A.bootstrap_auc([0, 1], [0, 1], np.array([[0, 0], [0, 1], [1, 1]]))
        result = A.interval(samples)
        self.assertEqual(result["invalid_bootstrap_draws"], 2)
        self.assertEqual(result["valid_bootstrap_draws"], 1)
        self.assertEqual(result["ci95"], [1.0, 1.0])

    def test_sign_metric_is_distinct_and_zero_not_following(self):
        scores = np.array([10, 9, 8, 7], float)
        labels = np.array([1, 1, 0, 0])
        ix = np.tile(np.arange(4), (5, 1))
        self.assertEqual(A.rank_auc(scores, labels), 1.0)
        self.assertEqual(A.sign_follow(scores, labels, ix)["rate"], 0.5)
        result = A.sign_follow([0, 1, -1, 0], [1, 1, 0, 0], ix)
        self.assertEqual(result["k"], 2)
        self.assertEqual(result["ties"], 2)
        self.assertEqual(result["ci95"], [0.5, 0.5])

    def test_wilson_known_values_and_nonbinomial_rejected(self):
        lo, hi = A.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.236593090512564, places=12)
        self.assertAlmostEqual(hi, 0.763406909487436, places=12)
        self.assertAlmostEqual(A.wilson(0, 10)[0], 0, places=12)
        self.assertAlmostEqual(A.wilson(10, 10)[1], 1, places=12)
        with self.assertRaises(ValueError):
            A.wilson(0.9813 * 200, 200)

    def test_nonfinite_and_wrong_grid_rejected(self):
        for scores, labels in (([0, float("nan")], [0, 1]), ([0, 1], [0, 2]), ([0], [0, 1])):
            with self.assertRaises(ValueError):
                A.rank_auc(scores, labels)
        with self.assertRaises(ValueError):
            A.bootstrap_auc([0, 1], [0, 1], np.array([[0, 2]]))

    def test_seal_and_payload_mutations_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = root / "scores.jsonl"
            payload.write_text('{"score":1}\n')
            A.write_json(root / "SCORE_SEAL.json", {"files": {payload.name: A.sha(payload)}})
            pin = A.sha(root / "SCORE_SEAL.json")
            self.assertTrue(A.verify_seal(root, "SCORE_SEAL.json", pin))
            payload.write_text('{"score":2}\n')
            with self.assertRaises(ValueError):
                A.verify_seal(root, "SCORE_SEAL.json", pin)
            with self.assertRaises(ValueError):
                A.verify_seal(root, "SCORE_SEAL.json", "0" * 64)

    def test_unsafe_seal_member_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            A.write_json(root / "SCORE_SEAL.json", {"files": {"../escape": "0" * 64}})
            with self.assertRaises(ValueError):
                A.verify_seal(root, "SCORE_SEAL.json", A.sha(root / "SCORE_SEAL.json"))


if __name__ == "__main__":
    unittest.main()
