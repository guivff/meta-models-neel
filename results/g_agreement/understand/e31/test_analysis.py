"""E31 synthetic tests only; real E15 analysis requires a separate explicit launch."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location("e31_analyze", Path(__file__).with_name("analyze.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


class E31AnalysisTests(unittest.TestCase):
    def test_auc_ties_orientation_and_no_automatic_flips(self):
        self.assertEqual(A.auc([1, 0, 1, 3], [1, 0, 0, 1]), .875)
        self.assertEqual(A.auc([0, 1], [1, 0]), 0.)
        self.assertEqual(A.auc([2, 2], [1, 0]), .5)
        self.assertEqual(A.auc([1, 0, 1, 3], [1, 0, 0, 1]), A.auc([-1, 0, -1, -3], [0, 1, 1, 0]))

    def test_invalid_scores_fail_and_single_class_is_not_half(self):
        self.assertIsNone(A.auc([], []))
        self.assertIsNone(A.auc([1, 2], [1, 1]))
        for s, y in (([float("nan"), 1], [0, 1]), ([1, 2], [0, 2]), ([1], [0, 1])):
            with self.assertRaises(ValueError):
                A.auc(s, y)

    def test_vectorized_bootstrap_matches_pairwise_definition(self):
        s, y = np.array([1, 2, 2, 0, -1, 4.]), np.array([1, 0, 1, 0, 0, 1])
        ix = np.random.default_rng(4).integers(0, 6, (80, 6))
        got = A.bootstrap_auc(s, y, ix)
        expected = []
        for k in ix:
            pos, neg = s[k][y[k] == 1], s[k][y[k] == 0]
            expected.append(float((pos[:, None] > neg).mean()+.5*(pos[:, None] == neg).mean()) if len(pos) and len(neg) else np.nan)
        np.testing.assert_allclose(got, expected, atol=1e-14, equal_nan=True)

    def test_shared_resamples_preserve_paired_donor_difference(self):
        y = [0, 1, 0, 1]
        scores = {arm: [0., 1., 0., 1.] for arm in A.ARMS}
        result, draws = A.analyze_stratum(y, scores, np.random.default_rng(3), 100)
        self.assertEqual(result["oracle_true_minus_random_donor"]["difference"], 0.)
        self.assertEqual(result["oracle_true_minus_random_donor"]["ci95"], [0., 0.])
        self.assertGreater(result["arms"]["oracle_true"]["undefined_bootstrap_draws"], 0)
        self.assertEqual(len(draws), 100)

    def test_empty_and_single_class_strata_remain_not_evaluable(self):
        for y in ([], [1, 1]):
            scores = {arm: [1.] * len(y) for arm in A.ARMS}
            result, draws = A.analyze_stratum(y, scores, np.random.default_rng(1), 20)
            self.assertEqual(result["status"], "NOT_EVALUABLE")
            self.assertIsNone(result["arms"]["oracle_true"]["auroc"])
            self.assertEqual(result["arms"]["oracle_true"]["attempted_bootstrap_draws"], 0)
            self.assertIsNone(draws)

    def test_per_row_predictions_and_independent_stratum_contrast(self):
        records = []
        for st, score in (("informative", [0., 1., 0., 1.]), ("uninformative", [1., 0., 1., 0.])):
            records += [{"stratum": st, "label": y, **{arm: s for arm in A.ARMS}} for s, y in zip(score, [0, 1, 0, 1])]
        result = A.analyze_row("synthetic", records, .5, np.random.default_rng(2), 100)
        self.assertTrue(result["predictions"]["local_cue_info_ge075_and_uninfo_le060"])
        self.assertFalse(result["predictions"]["remote_state_both_ge070"])
        self.assertEqual(result["informative_minus_uninformative_oracle"]["difference"], 1.)
        self.assertEqual(result["informative_minus_uninformative_oracle"]["ci95"], [1., 1.])
        self.assertNotEqual(result["strata"]["informative"]["bootstrap_indices_sha256"], result["strata"]["uninformative"]["bootstrap_indices_sha256"])

    def test_interval_counts_undefined_without_replacement(self):
        x = A.interval([np.nan, .2, .8, np.nan])
        self.assertEqual(x["attempted_bootstrap_draws"], 4)
        self.assertEqual(x["finite_bootstrap_draws"], 2)
        self.assertEqual(x["undefined_bootstrap_draws"], 2)
        self.assertEqual(A.interval([np.nan])["ci95"], None)

    def test_lock_prevents_overwrite_and_reanalysis(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/"analysis"
            A.exclusive_start(out, {"source": "fixture"})
            with self.assertRaises(ValueError):
                A.exclusive_start(out, {})
            (out/"STARTED.json").unlink()
            out.rmdir()
            with self.assertRaises(FileExistsError):
                A.exclusive_start(out, {})

    def test_seal_identity_and_payload_tamper_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/"strata.jsonl").write_text('{"label":1}\n')
            A.dump(root/"SEAL.json", {"files": {"strata.jsonl": A.sha(root/"strata.jsonl")}})
            pin = A.sha(root/"SEAL.json")
            A.verify_seal(root/"SEAL.json", pin)
            (root/"strata.jsonl").write_text('{"label":0}\n')
            with self.assertRaises(ValueError):
                A.verify_seal(root/"SEAL.json", pin)
            with self.assertRaises(ValueError):
                A.verify_seal(root/"SEAL.json", "0"*64)

    def test_synthetic_full_grid_freeze_join_and_seal(self):
        """No actual W1/E15 data: 4704 toy records exercise the complete custody path."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage, scores, frozen, prior = [root/n for n in ("stage", "scores", "freeze", "prior")]
            for d in (stage, scores, frozen, prior):
                d.mkdir()
            (frozen/"cache").mkdir()
            features = A.ROWS+["table_column"]
            tests, devs, labels, strata, raw = [], [], [], [], []
            for f in features:
                for split in ("dev", "test"):
                    for i in range(84):
                        key, y = f+":"+split+":"+str(i), int(i % 2 == 0)
                        (tests if split == "test" else devs).append({"id": key, "feature": f})
                        labels.append({"id": key, "feature": f, "split": split, "value": "A" if y else "B"})
                        if f in A.ROWS:
                            p = .8 if i % 4 < 2 else .6
                            strata.append({**labels[-1], "label": y, "p_A": p, "margin": abs(2*p-1), "stratum": "informative" if i%4<2 else "uninformative"})
                        for reader, arms in (("base", ["true"]),) if split == "dev" else (("olens", ["true", "random_donor", "w1_mismatched"]), ("nla", ["true", "random_donor", "w1_mismatched"])):
                            for arm in arms:
                                s = 0 if arm == "random_donor" else 2*y-1
                                raw.append({"id": key, "feature": f, "reader": reader, "arm": arm, "scores": [s, s], "layer": None if reader == "base" else 44 if reader == "olens" else 42, "status": "COMPLETE"})
            def jl(path, values):
                path.write_text("".join(json.dumps(v)+"\n" for v in values))
            jl(stage/"items.input.jsonl", tests)
            jl(stage/"reference.input.jsonl", devs)
            jl(root/"labels.jsonl", labels)
            jl(scores/"scores.jsonl", raw)
            plan = {"source_files": {}, "labels_sha256": A.sha(root/"labels.jsonl"), "values": {f: ["A", "B"] for f in features}}
            A.dump(stage/"plan.json", plan)
            A.dump(stage/"INPUT_SEAL.json", {"files": {n: A.sha(stage/n) for n in ("plan.json", "items.input.jsonl", "reference.input.jsonl")}})
            A.dump(scores/"provenance.json", {"input_seal_sha256": A.sha(stage/"INPUT_SEAL.json"), "source_files": {}})
            A.dump(scores/"SCORE_SEAL.json", {"files": {n: A.sha(scores/n) for n in ("scores.jsonl", "provenance.json")}})
            metrics = {"score_seal_sha256": A.sha(scores/"SCORE_SEAL.json"), "labels_sha256": A.sha(root/"labels.jsonl"), "rows": [{"feature": f, "status": "EVALUABLE", "valid_pairs": [0, 1], "readers": {r: {"arms": {"true": {"auroc": 1.}, "random_donor": {"auroc": .5}}} for r in ("olens", "nla")}} for f in A.ROWS]}
            A.dump(prior/"metrics.json", metrics)
            A.dump(prior/"ANALYSIS_SEAL.json", {"files": {"metrics.json": A.sha(prior/"metrics.json")}})
            protocol = {"experiment": "E31", "status": "READY", "rows": A.ROWS, "seed": 20261025, "bootstrap": 2000, "suffix_slice": "include_read", "source_files": {A.SELF: A.sha(A.__file__)}}
            for key, file in (("input_seal", stage/"INPUT_SEAL.json"), ("score_seal", scores/"SCORE_SEAL.json"), ("metrics_seal", prior/"ANALYSIS_SEAL.json"), ("plan", stage/"plan.json"), ("scores", scores/"scores.jsonl"), ("labels", root/"labels.jsonl"), ("metrics", prior/"metrics.json")):
                protocol["e15_"+key+"_sha256"] = A.sha(file)
            A.dump(root/"protocol.json", protocol)
            (frozen/"protocol.json").write_bytes((root/"protocol.json").read_bytes())
            A.dump(frozen/"DEV_CUTOFFS.json", {"suffix_slice": "include_read", "method": "dev_median_abs_probability_margin", "informative_operator": ">", "margin_formula": "abs(p_A-p_B)", "rows": [{"feature": f, "cutoff": .4} for f in A.ROWS]})
            A.dump(frozen/"PROVENANCE.json", {"protocol_sha256": A.sha(root/"protocol.json"), "source_files": protocol["source_files"], "test_labels_used_for_cutoff": False, "continuation_scores_accessed": False})
            A.dump(frozen/"cache/models.json", {"fixture": True})
            jl(frozen/"cache/strata.jsonl", strata)
            names = ("protocol.json", "DEV_CUTOFFS.json", "PROVENANCE.json", "cache/models.json", "cache/strata.jsonl")
            A.dump(frozen/"STRATA_SEAL.json", {"complete": True, "status": "E31_STRATA_FROZEN_BEFORE_E15_OUTCOME_JOIN", "protocol_sha256": A.sha(root/"protocol.json"), "source_files": protocol["source_files"], "files": {n: A.sha(frozen/n) for n in names}})
            args = SimpleNamespace(protocol=root/"protocol.json", freeze=frozen/"STRATA_SEAL.json", e15_stage=stage, e15_scores=scores, e15_labels=root/"labels.jsonl", e15_metrics=prior/"metrics.json", out=root/"result")
            result = A.run(args)
            self.assertEqual(result["full_test_parity_checks"], 21)
            A.verify_seal(args.out/"ANALYSIS_SEAL.json", result["seal_sha256"])
            observed = A.read(args.out/"METRICS.json")
            self.assertEqual(observed["descriptive_counts"], {"evaluable_rows": 7, "not_evaluable_rows": 0, "local_cue_rows": 0, "remote_state_rows": 7})
            self.assertEqual(A.read(args.out/"RUN.json")["new_model_fits"], 0)
            with self.assertRaises(ValueError):
                A.run(args)
            bad = A.read(frozen/"DEV_CUTOFFS.json")
            bad["rows"][0]["cutoff"] = .41
            with self.assertRaisesRegex(ValueError, "dev-margin median"):
                A.verify_frozen_cutoffs(strata, bad, protocol)
            bad["suffix_slice"] = "exclude_read"
            with self.assertRaisesRegex(ValueError, "suffix"):
                A.verify_frozen_cutoffs(strata, bad, protocol)


if __name__ == "__main__":
    unittest.main()
