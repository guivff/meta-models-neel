"""Synthetic-only E25 checks. No scientific input is opened by these tests."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from scipy.stats import spearmanr

spec = importlib.util.spec_from_file_location("e25_analyze", Path(__file__).with_name("analyze.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def fixture():
    rows = [f"row_{i:02d}" for i in range(25)]
    plan = {"rows": rows, "items": [], "analysis": {"seed": 20261025, "bootstrap": 2000},
            "clarifications": {"integrator_acknowledged": True, "D_definition": "AUROC(s_A-s_B,value_is_A)",
                               "clarification_commit": "e4225a1e", "phrasing_aggregation": "mean_of_two_W1_pairs"}}
    labels, refs, scores = {"items": []}, {"rows": []}, []
    for r, row in enumerate(rows):
        refs["rows"].append({"feature": row, "class": "structure" if r < 16 else "semantic",
                             "olens": .5 + r / 50, "nla": .98 - r / 50, "probe": .9})
        for i in range(84):
            key, y = f"{row}_{i:02d}", int(i < 42)
            plan["items"].append({"id": key, "feature": row})
            labels["items"].append({"id": key, "feature": row, "label": y})
            # Perfect conventional discrimination, identical truth margins in both classes.
            for phrasing in (0, 1):
                true_score = -10 + r / 10 + phrasing / 10
                for candidate in ("A", "B"):
                    correct = (candidate == "A") == (y == 1)
                    scores.append({"id": key, "feature": row, "phrasing": phrasing,
                                   "candidate": candidate, "mean_logprob": true_score if correct else true_score - 2,
                                   "token_count": 1 + phrasing})
    return scores, labels, refs, plan


class MetricsTests(unittest.TestCase):
    def test_tied_auc_orientation_is_fixed(self):
        self.assertEqual(a.auc([1, 1, 0, 0], [1, 1, 1, 0]), .75)
        self.assertEqual(a.auc([1, 1, 0, 0], [-1, -1, -1, 0]), .25)
        self.assertEqual(a.auc([1, 0], [5, 5]), .5)
        with self.assertRaises(ValueError):
            a.auc([1, 1], [1, 2])

    def test_auc_matches_pairwise_probability_oracle(self):
        rng = np.random.default_rng(44)
        y = np.array([0] * 11 + [1] * 13)
        for _ in range(10):
            scores = rng.integers(-3, 4, size=len(y))
            positives, negatives = scores[y == 1], scores[y == 0]
            expected = np.mean((positives[:, None] > negatives).astype(float)
                               + .5 * (positives[:, None] == negatives))
            self.assertAlmostEqual(a.auc(y, scores), expected, places=14)

    def test_spearman_ties_match_independent_scipy(self):
        x, y = [0, 1, 1, 3, 4, 4], [3, 1, 0, 2, 4, 4]
        self.assertAlmostEqual(a.correlation(x, y), spearmanr(x, y).statistic, places=14)
        self.assertIsNone(a.correlation([1, 1, 1], [1, 2, 3]))

    def test_perfect_item_sensitive_discrimination_has_D_one(self):
        scores, labels, refs, plan = fixture()
        result = a.summarize(scores, labels, refs, plan)
        self.assertTrue(all(r["D"] == 1 for r in result["rows"]))
        self.assertEqual(set(result["correlations"]), {"P", "D"})
        self.assertEqual(set(result["definitions"]), {"P", "D"})
        self.assertAlmostEqual(result["rows"][0]["P"], -9.95)
        self.assertAlmostEqual(result["correlations"]["P"]["olens"]["rho"], 1)
        self.assertAlmostEqual(result["correlations"]["P"]["nla"]["rho"], -1)
        self.assertEqual(result["correlations"]["P"]["probe"]["undefined_draws"], 2000)
        self.assertIsNone(result["correlations"]["P"]["probe"]["ci95"])
        delta = result["discriminant_paired_rho_differences"]["P"]["olens_minus_nla"]
        self.assertAlmostEqual(delta["difference"], 2)
        np.testing.assert_allclose(delta["ci95"], [2, 2])
        self.assertTrue(result["prediction"]["held"])
        json.dumps(result, allow_nan=False)
        self.assertEqual(result, a.summarize(scores, labels, refs, plan))

    def test_constant_candidate_preference_has_D_half(self):
        inputs = fixture()
        for score in inputs[0]:
            score["mean_logprob"] = -1 if score["candidate"] == "A" else -2
        result = a.summarize(*inputs)
        self.assertTrue(all(r["D"] == .5 for r in result["rows"]))
        self.assertTrue(all(r["P"] == -1.5 for r in result["rows"]))

    def test_unacknowledged_choices_have_no_prediction_claim(self):
        inputs = fixture()
        inputs[3]["clarifications"]["integrator_acknowledged"] = False
        result = a.summarize(*inputs)
        self.assertIsNone(result["prediction"]["held"])
        self.assertEqual(result["status"], "DESCRIPTIVE_PENDING_CLARIFICATION")

    def test_unweighted_phrasing_mean_precedes_median(self):
        inputs = fixture()
        # Different token counts must not turn mean-per-token candidate scoring into token weighting.
        for s in inputs[0]:
            if s["feature"] == "row_00" and s["candidate"] == ("A" if int(s["id"].split("_")[-1]) < 42 else "B"):
                s["mean_logprob"] = -2 if s["phrasing"] == 0 else -8
                s["token_count"] = 1 if s["phrasing"] == 0 else 10
        result = a.summarize(*inputs)
        self.assertEqual(result["rows"][0]["P"], -5)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.inputs = fixture()

    def test_duplicate_missing_nonfinite_and_out_of_scope_rejected(self):
        mutations = (
            lambda x: x[0].append(dict(x[0][0])),
            lambda x: x[0].pop(),
            lambda x: x[0][0].update(mean_logprob=float("nan")),
            lambda x: x[0][0].update(feature="new_row"),
            lambda x: x[0][0].update(phrasing=2),
            lambda x: x[0][0].update(token_count=0),
            lambda x: x[0][0].update(mean_logprob=.1),
            lambda x: x[1]["items"].pop(),
            lambda x: x[1]["items"][0].update(label=True),
            lambda x: x[2]["rows"][0].update(olens=float("inf")),
        )
        for change in mutations:
            with self.subTest(change=change):
                data = copy.deepcopy(self.inputs)
                change(data)
                with self.assertRaises(ValueError):
                    a.validate_grid(*data)

    def test_25_16_9_population_enforced(self):
        for target in ("rows", "classes", "balance"):
            with self.subTest(target=target):
                data = copy.deepcopy(self.inputs)
                if target == "rows":
                    data[3]["rows"].pop()
                elif target == "classes":
                    data[2]["rows"][0]["class"] = "semantic"
                else:
                    data[1]["items"][0]["label"] = 0
                with self.assertRaises(ValueError):
                    a.validate_grid(*data)

    def test_registration_seed_and_bootstrap_fixed(self):
        for field in ("seed", "bootstrap"):
            with self.subTest(field=field):
                data = copy.deepcopy(self.inputs)
                data[3]["analysis"][field] += 1
                with self.assertRaises(ValueError):
                    a.summarize(*data)

    def test_failed_score_seal_cannot_open_labels(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "plan.json").write_text("{}")
            (root / "scores.jsonl").write_text("{}\n")
            (root / "seal.json").write_text(json.dumps({"schema_version": 1, "complete": True,
                "plan_sha256": a.sha256(root / "plan.json"), "files": {"scores.jsonl": "0" * 64}}))
            actual_loader = a.load_json
            calls = []
            def tracked(path):
                calls.append(Path(path).name)
                return actual_loader(path)
            with mock.patch.object(a, "load_json", side_effect=tracked):
                with self.assertRaisesRegex(ValueError, "SHA256"):
                    a.main(["--scores", str(root / "scores.jsonl"), "--score-seal", str(root / "seal.json"),
                            "--plan", str(root / "plan.json"), "--labels", str(root / "DO_NOT_OPEN.json"),
                            "--references", str(root / "DO_NOT_OPEN_REFS.json"), "--out", str(root / "new")])
            self.assertNotIn("DO_NOT_OPEN.json", calls)
            self.assertNotIn("DO_NOT_OPEN_REFS.json", calls)
            self.assertFalse((root / "new").exists())

    def test_unacknowledged_plan_cannot_open_labels(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan = self.inputs[3]
            plan["clarifications"]["integrator_acknowledged"] = False
            (root / "plan.json").write_text(json.dumps(plan))
            (root / "scores.jsonl").write_text("{}\n")
            (root / "seal.json").write_text(json.dumps({"schema_version": 1, "complete": True,
                "plan_sha256": a.sha256(root / "plan.json"), "files": {"scores.jsonl": a.sha256(root / "scores.jsonl")}}))
            with self.assertRaisesRegex(ValueError, "acknowledgement"):
                a.main(["--scores", str(root / "scores.jsonl"), "--score-seal", str(root / "seal.json"),
                        "--plan", str(root / "plan.json"), "--labels", str(root / "DO_NOT_OPEN.json"),
                        "--references", str(root / "DO_NOT_OPEN_REFS.json"), "--out", str(root / "new")])
            self.assertFalse((root / "new").exists())

    def test_every_sealed_member_is_checked_before_labels(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "plan.json").write_text("{}")
            (root / "scores.jsonl").write_text("{}\n")
            (root / "provenance.json").write_text("{}")
            seal = {"schema_version": 1, "complete": True,
                    "plan_sha256": a.sha256(root / "plan.json"),
                    "files": {n: a.sha256(root / n) for n in ("scores.jsonl", "provenance.json")}}
            (root / "seal.json").write_text(json.dumps(seal))
            (root / "provenance.json").write_text('{"altered":true}')
            with self.assertRaisesRegex(ValueError, "provenance.json"):
                a.verify_scores_before_labels(root / "scores.jsonl", root / "seal.json", root / "plan.json")
            seal["files"] = {"scores.jsonl": a.sha256(root / "scores.jsonl"), "../private.json": "0" * 64}
            (root / "seal.json").write_text(json.dumps(seal))
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                a.verify_scores_before_labels(root / "scores.jsonl", root / "seal.json", root / "plan.json")

    def test_withheld_label_and_reference_hashes_are_required(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            labels, refs = root / "labels.json", root / "refs.json"
            labels.write_text('{"items":[]}')
            refs.write_text('{"rows":[]}')
            plan = {"analysis_inputs": {"labels_sha256": a.sha256(labels), "references_sha256": a.sha256(refs)}}
            a.verify_analysis_inputs(labels, refs, plan)
            labels.write_text('{"items":[0]}')
            with self.assertRaisesRegex(ValueError, "labels_sha256"):
                a.verify_analysis_inputs(labels, refs, plan)
            plan["analysis_inputs"]["labels_sha256"] = a.sha256(labels)
            refs.write_text('{"rows":[0]}')
            with self.assertRaisesRegex(ValueError, "references_sha256"):
                a.verify_analysis_inputs(labels, refs, plan)

    def test_complete_cli_seals_outputs_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            scores, labels, refs, plan = self.inputs
            for name, data in (("labels.json", labels), ("refs.json", refs)):
                (root / name).write_text(json.dumps(data))
            plan["analysis_inputs"] = {"labels_sha256": a.sha256(root / "labels.json"),
                                       "references_sha256": a.sha256(root / "refs.json")}
            (root / "plan.json").write_text(json.dumps(plan))
            (root / "scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in scores))
            (root / "seal.json").write_text(json.dumps({"schema_version": 1, "complete": True,
                "plan_sha256": a.sha256(root / "plan.json"), "files": {"scores.jsonl": a.sha256(root / "scores.jsonl")}}))
            argv = ["--scores", str(root / "scores.jsonl"), "--score-seal", str(root / "seal.json"),
                    "--plan", str(root / "plan.json"), "--labels", str(root / "labels.json"),
                    "--references", str(root / "refs.json"), "--out", str(root / "output")]
            a.main(argv)
            seal = json.loads((root / "output/ANALYSIS_SEAL.json").read_text())
            for name, expected in seal["files"].items():
                self.assertEqual(a.sha256(root / "output" / name), expected)
            self.assertIn("The exploratory prediction held", (root / "output/RESULTS.md").read_text())
            with self.assertRaisesRegex(ValueError, "already exists"):
                a.main(argv)


if __name__ == "__main__":
    unittest.main()
