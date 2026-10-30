"""Synthetic-only probe precision regression; no corpus or capture inputs."""
from __future__ import annotations

import unittest

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from .probes import fit_probe, verify_raw_conversion


class ProbePrecisionTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(73)
        self.dev_y = np.tile([0, 1], 32)
        self.dev_x = (rng.normal(size=(64, 64)) * 3 + rng.uniform(-10, 10, size=64)).astype(np.float32)
        self.dev_x[:, 0] += self.dev_y * 4
        self.scaler = StandardScaler().fit(self.dev_x)
        self.model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000, random_state=20261027)
        self.model.fit(self.scaler.transform(self.dev_x), self.dev_y)
        self.direction = self.model.coef_[0] / self.scaler.scale_
        self.intercept = self.model.intercept_[0] - self.direction @ self.scaler.mean_
        self.test_x = (rng.normal(size=(16, 64)) * 3 + self.scaler.mean_).astype(np.float32)
        # Fixed synthetic construction near the decision boundary exposes the
        # old relative-tolerance assertion without selecting any real examples.
        pivot = np.argmax(np.abs(self.direction))
        self.test_x[:, pivot] = 0
        self.test_x[:, pivot] = -(self.test_x.astype(np.float64) @ self.direction + self.intercept) / self.direction[pivot]
        self.test_y = np.tile([0, 1], 8)
        self.transformed = self.scaler.transform(self.test_x)
        self.scores = self.model.decision_function(self.transformed)

    def check(self, **overrides):
        arguments = dict(test_x=self.test_x, transformed_x=self.transformed, mean=self.scaler.mean_,
                         scale=self.scaler.scale_, coef=self.model.coef_[0], bias=self.model.intercept_[0],
                         direction=self.direction, intercept=self.intercept, scores=self.scores)
        arguments.update(overrides)
        return verify_raw_conversion(**arguments)

    def test_old_assertion_fails_but_fixed_fit_preserves_exact_decision_scores(self):
        original_dev, original_test = self.dev_x.copy(), self.test_x.copy()
        raw = self.test_x @ self.direction + self.intercept
        self.assertFalse(np.allclose(raw, self.scores))
        result = fit_probe(self.dev_x, self.dev_y, self.test_x, self.test_y)
        np.testing.assert_array_equal(result["test_scores"], self.scores)
        self.assertEqual(result["test_scores"].dtype, self.scores.dtype)
        np.testing.assert_array_equal(result["direction"], self.direction)
        self.assertEqual(result["intercept"], self.intercept)
        self.assertEqual(result["test_auroc"], roc_auc_score(self.test_y, self.scores))
        np.testing.assert_array_equal(self.dev_x, original_dev)
        np.testing.assert_array_equal(self.test_x, original_test)
        self.assertGreater(result["precision_check"]["max_score_error"], 1e-8)

    def test_float64_algebra_check_rejects_wrong_coefficient_conversion(self):
        changed = self.direction.copy()
        changed[0] += .01
        with self.assertRaisesRegex(ValueError, "float64 algebra"):
            self.check(direction=changed)
        with self.assertRaisesRegex(ValueError, "float64 algebra"):
            self.check(intercept=self.intercept + .01)

    def test_decision_path_bound_rejects_unexplained_score_changes(self):
        with self.assertRaisesRegex(ValueError, "exceeds precision bound"):
            self.check(scores=self.scores + np.asarray(.1, dtype=self.scores.dtype))

    def test_float64_decision_path_is_supported_without_changing_scores(self):
        z64 = (self.test_x.astype(np.float64) - self.scaler.mean_) / self.scaler.scale_
        scores64 = z64 @ self.model.coef_[0].astype(np.float64) + float(self.model.intercept_[0])
        original = scores64.copy()
        diagnostic = self.check(transformed_x=z64, scores=scores64)
        self.assertEqual(diagnostic["score_dtype"], "float64")
        self.assertEqual(diagnostic["max_scaler_rounding_bound"], 0)
        np.testing.assert_array_equal(scores64, original)


if __name__ == "__main__":
    unittest.main()
