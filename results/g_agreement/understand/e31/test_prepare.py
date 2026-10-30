"""Synthetic-only tests for E31 preparation; never open the real frozen banks."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

SPEC = importlib.util.spec_from_file_location("e31_prepare", Path(__file__).with_name("prepare.py"))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def synthetic_membership():
    features = M.ROWS + ["table_column"]
    templates = {f: {"values": ["A", "B"]} for f in features}
    plan = {"features": features, "values": {f: ["A", "B"] for f in features}}
    bank, items, refs, labels = [], [], [], []
    for feature in features:
        for split in ("dev", "test"):
            for cluster in range(6):
                for index in range(14):
                    key = f"{feature}/{split}/{cluster}/{index}"
                    row = {"id": key, "feature": feature, "split": split,
                           "cluster": f"{feature}/{split}/{cluster}",
                           "value": "A" if index < 7 else "B", "ids": [1, 2, 3, 4, 5],
                           "meta": {"read_position": 4}}
                    bank.append(row)
                    labels.append({k: row[k] for k in ("id", "feature", "split", "cluster", "value")})
                    item = {"id": key, "feature": feature}
                    if split == "dev":
                        refs.append({**item, "ids": list(row["ids"])})
                    else:
                        items.append(item)
    return bank, templates, items, refs, labels, plan


def synthetic_files(base):
    """Make a complete fake bank and seals, with a tiny locally built tokenizer."""
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    w1, stage, metric_dir, tok = [base / n for n in ("w1", "stage", "metrics", "tokenizer")]
    for path in (w1, stage, metric_dir, tok):
        path.mkdir()
    bank, templates, items, refs, labels, plan = synthetic_membership()
    def jsonl(path, rows):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    jsonl(w1 / "items.DO_NOT_STAGE.jsonl", bank)
    M._write(w1 / "templates.json", templates)
    label_path = base / "labels.jsonl"
    jsonl(label_path, labels)
    jsonl(stage / "items.input.jsonl", items)
    jsonl(stage / "reference.input.jsonl", refs)
    plan.update({"W1_full_items_sha256": M.sha(w1 / "items.DO_NOT_STAGE.jsonl"),
                 "labels_sha256": M.sha(label_path)})
    M._write(stage / "plan.json", plan)
    M._write(stage / "pairs.json", {"synthetic": True})
    M._write(stage / "INPUT_SEAL.json", {"status": "E15_FROZEN_BEFORE_ANY_REFERENCE_OR_READER_SCORING",
             "files": {n: M.sha(stage / n) for n in M.INPUT_FILES}})
    M._write(metric_dir / "metrics.json", {"labels_sha256": M.sha(label_path),
             "score_seal_sha256": "1" * 64,
             "rows": [{"feature": f, "valid_pairs": [0, 1]} for f in M.ROWS]
                     + [{"feature": "table_column", "valid_pairs": []}]})
    M._write(metric_dir / "ANALYSIS_SEAL.json", {"status": "E15_ANALYSIS_COMPLETE",
             "files": {"metrics.json": M.sha(metric_dir / "metrics.json")}})
    Tokenizer(WordLevel({"[UNK]": 0, "a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
                        unk_token="[UNK]")).save(str(tok / "tokenizer.json"))
    source = "results/g_agreement/understand/e31/prepare.py"
    protocol = {"status": "READY", "suffix_slice": "include_read", "rows": M.ROWS,
                "source_files": {source: M.sha(M.ROOT / source)},
                "e1b_recipe_sha256": M.E1B_RECIPE_SHA256,
                "w1_items_sha256": M.sha(w1 / "items.DO_NOT_STAGE.jsonl"),
                "w1_templates_sha256": M.sha(w1 / "templates.json"),
                "e15_input_seal_sha256": M.sha(stage / "INPUT_SEAL.json"),
                "e15_metrics_seal_sha256": M.sha(metric_dir / "ANALYSIS_SEAL.json"),
                "e15_labels_sha256": M.sha(label_path), "e15_score_seal_sha256": "1" * 64,
                "tokenizer_files": {"tokenizer.json": M.sha(tok / "tokenizer.json")}}
    # Noncanonical formatting must survive the freeze copy byte-for-byte.
    protocol_path = base / "protocol.json"
    protocol_path.write_text(json.dumps(protocol, indent=1) + "\n")
    return SimpleNamespace(protocol=protocol_path, w1_bank=w1, e15_stage=stage,
                           e15_labels=label_path, e15_metrics=metric_dir / "metrics.json",
                           tokenizer=tok, out=base / "freeze"), protocol


class PreparationTests(unittest.TestCase):
    def test_suffix_boundaries_and_exact_length(self):
        item = {"ids": [10, 11, 12, 13, 14, 15], "meta": {"read_position": 5}}
        self.assertEqual(M.suffix_ids(item, "include_read"), [12, 13, 14, 15])
        self.assertEqual(M.suffix_ids(item, "exclude_read"), [11, 12, 13, 14])
        for mode in (None, "both", "before"):
            with self.assertRaises(ValueError):
                M.suffix_ids(item, mode)
        item["meta"]["read_position"] = 4
        with self.assertRaises(ValueError):
            M.suffix_ids(item, "include_read")
        with self.assertRaises(ValueError):
            M.suffix_ids({"ids": [1, 2, 3, 4], "meta": {"read_position": 3}}, "exclude_read")

    def test_margin_is_unsigned_and_ties_are_uninformative(self):
        np.testing.assert_allclose(M.confidence([0.1, 0.9]), [0.8, 0.8])
        p = [0., .25, .5, .75, 1.]
        self.assertEqual(M.assign_strata(p, .5), ["informative", "uninformative", "uninformative",
                                                "uninformative", "informative"])
        self.assertEqual(M.assign_strata([.5] * 4, 0.), ["uninformative"] * 4)
        for value in (float("nan"), float("inf"), -0.1, 1.1):
            with self.assertRaises(ValueError):
                M.confidence([value])

    def test_e1b_hyperparameters_dev_fit_and_json_restoration(self):
        dev = ["aaaA", "aaaB", "bbbA", "bbbB", "aaba", "bbab"]
        labels = [1, 1, 0, 0, 1, 0]
        test = ["aaaA", "bbbA", "zzZZΩΩ"]
        model, dp, tp = M.fit_row(dev, labels, test)
        changed, changed_dp, _ = M.fit_row(dev, labels, ["UNSEEN_TEST_ONLY"])
        self.assertEqual(model["vocabulary"], changed["vocabulary"])
        self.assertFalse(any("Ω" in text for text in model["vocabulary"]))
        self.assertEqual(model["coef"], changed["coef"])
        self.assertEqual(model["idf"], changed["idf"])
        np.testing.assert_array_equal(dp, changed_dp)
        self.assertEqual(model["classifier_params"], dict(C=1., penalty="l2", solver="lbfgs",
                                                          max_iter=2000, tol=1e-4, random_state=20261023))
        self.assertEqual(model["vectorizer_params"]["ngram_range"], [1, 4])
        self.assertFalse(model["vectorizer_params"]["lowercase"])
        self.assertEqual(model["classes"], [0, 1])
        self.assertGreater(tp[0], tp[1])
        roundtrip = json.loads(json.dumps(model, allow_nan=False))
        np.testing.assert_allclose(M.restored_probabilities(roundtrip, test), tp, rtol=0, atol=1e-15)
        np.testing.assert_allclose(M.restored_probabilities(roundtrip, dev), dp, rtol=0, atol=1e-15)
        self.assertEqual(float(np.median(M.confidence(dp))), float(np.median(M.confidence(changed_dp))))

    def test_convergence_warning_is_error_no_retry(self):
        from sklearn.exceptions import ConvergenceWarning
        with patch("sklearn.linear_model.LogisticRegression.fit", side_effect=ConvergenceWarning("synthetic failure")) as fit:
            with self.assertRaises(ConvergenceWarning):
                M.fit_row(["a", "b"], [1, 0], ["a"])
            self.assertEqual(fit.call_count, 1)

    def test_full_membership_and_seven_row_scope(self):
        fixture = synthetic_membership()
        selected = M.validate_membership(*fixture)
        self.assertEqual(len(selected), 1176)
        self.assertEqual(sum(r["split"] == "dev" for r in selected), 588)
        self.assertEqual({r["feature"] for r in selected}, set(M.ROWS))

    def test_membership_rejects_label_token_and_cluster_drift(self):
        for mutation in ("label", "tokens", "duplicate", "cluster"):
            fixture = list(copy.deepcopy(synthetic_membership()))
            bank, _, _, refs, labels, _ = fixture
            if mutation == "label":
                labels[0]["value"] = "B"
            elif mutation == "tokens":
                refs[0]["ids"][0] = 900
            elif mutation == "duplicate":
                refs.append(copy.deepcopy(refs[0]))
            else:
                # Change both banks' cluster labels: hash identity alone must not hide split leakage.
                for row in bank:
                    if row["feature"] == M.ROWS[0] and row["split"] == "test":
                        row["cluster"] = row["cluster"].replace("/test/", "/dev/")
                for row in labels:
                    if row["feature"] == M.ROWS[0] and row["split"] == "test":
                        row["cluster"] = row["cluster"].replace("/test/", "/dev/")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                M.validate_membership(*fixture)

    def test_protocol_source_hash_and_unresolved_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            name = "results/g_agreement/understand/e31/prepare.py"
            source = base / name
            source.parent.mkdir(parents=True)
            source.write_text("synthetic source")
            protocol = {"status": "READY", "suffix_slice": "include_read", "rows": M.ROWS,
                        "e1b_recipe_sha256": M.E1B_RECIPE_SHA256,
                        "source_files": {name: M.sha(source)}, "tokenizer_files": {"tokenizer.json": "0" * 64}}
            M.validate_protocol(protocol, root=base)
            for field, value in (("status", "PENDING"), ("suffix_slice", None), ("rows", M.ROWS[:-1])):
                changed = {**protocol, field: value}
                with self.assertRaises(ValueError):
                    M.validate_protocol(changed, root=base)
            source.write_text("changed source")
            with self.assertRaises(ValueError):
                M.validate_protocol(protocol, root=base)

    def test_hashes_and_exclusive_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "file.json"
            M._write(p, {"synthetic": True})
            M.verify_files(tmp, {"file.json": M.sha(p)})
            with self.assertRaises(FileExistsError):
                M._write(p, {})
            with self.assertRaises(ValueError):
                M.verify_files(tmp, {"file.json": "0" * 64})
            with self.assertRaises(ValueError):
                M.verify_files(tmp, {"../file.json": "0" * 64})

    def test_json_rejects_duplicate_keys_and_nonfinite(self):
        for text in ('{"id":1,"id":2}', '{"p":NaN}', '{"p":Infinity}'):
            with self.assertRaises(ValueError):
                M.loads(text)

    def test_complete_synthetic_freeze_binds_models_assignments_and_original_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, _ = synthetic_files(Path(tmp))
            result = M.prepare(args)
            self.assertEqual(result["status"], "FROZEN")
            seal = M.read(args.out / "STRATA_SEAL.json")
            M.verify_files(args.out, seal["files"])
            self.assertEqual(seal["protocol_sha256"], M.sha(args.protocol))
            self.assertEqual(seal["protocol_sha256"], M.sha(args.out / "protocol.json"))
            records = M.read_jsonl(args.out / "cache/strata.jsonl")
            self.assertEqual(len(records), 1176)
            self.assertEqual(len({r["id"] for r in records}), 1176)
            self.assertEqual(len(M.read(args.out / "cache/models.json")["rows"]), 7)
            provenance = M.read(args.out / "PROVENANCE.json")
            self.assertFalse(provenance["test_labels_used_for_cutoff"])
            self.assertFalse(provenance["continuation_scores_accessed"])
            with patch.object(M, "fit_row", side_effect=AssertionError("must not refit")):
                with self.assertRaisesRegex(ValueError, "exists"):
                    M.prepare(args)

    def test_seal_failure_precedes_label_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, protocol = synthetic_files(Path(tmp))
            args.e15_metrics.write_text('{"tampered":true}')
            with patch.object(M, "read_jsonl", side_effect=AssertionError("labels parsed prematurely")) as reader:
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    M.load_inputs(args, protocol)
                reader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
