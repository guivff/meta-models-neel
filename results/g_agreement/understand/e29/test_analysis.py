"""Synthetic E29 custody, sequencing and fixed-orientation value checks only."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

spec = importlib.util.spec_from_file_location("e29_values", Path(__file__).with_name("analyze.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def fixture():
    cohorts, all_labels, all_scores = [], {}, {}
    for name, blind, phrases in (("w12", True, 2), ("suraj_exp13", False, 1)):
        rows = [name + "_row0", name + "_row1"]
        items, labels, scores = [], [], []
        for row in rows:
            for i in range(4):
                key, value = row + "_" + str(i), "A" if i < 2 else "B"
                items.append({"id": key, "feature": row})
                labels.append({"id": key, "feature": row, "value": value})
                for p in range(phrases):
                    for c in ("A", "B"):
                        scores.append({"id": key, "feature": row, "phrasing": p, "candidate": c,
                                       "token_count": 1 if p == 0 else 7,
                                       "mean_logprob": -2 - 2*p - int(c != value)})
        cohorts.append({"name": name, "blind": blind, "rows": rows, "items": items,
                        "phrasing_count": phrases, "expected_scores": len(scores),
                        "input_seal_sha256": "1" * 64, "labels_sha256": "2" * 64,
                        "freeze": {"id": "synthetic-freeze", "sealed_before_scoring": True}})
        all_labels[name], all_scores[name] = labels, scores
    source = str(Path(a.__file__).relative_to(a.ROOT))
    plan = {"status": "READY", "cohorts": cohorts, "source_files": {source: a.sha(a.__file__)}}
    return plan, all_labels, all_scores


def staged_fixture(root):
    plan, labels, scores = fixture()
    paths = {}
    for cohort in plan["cohorts"]:
        name = cohort["name"]
        label_path = root / (name + "-labels.json")
        label_path.write_text(json.dumps(labels[name]))
        cohort["labels_sha256"] = a.sha(label_path)
        paths[name] = {"labels": label_path, "scores": root / (name + "-scores")}
    plan_path = root / "plan.json"
    plan_path.write_text(json.dumps(plan))
    for cohort in plan["cohorts"]:
        name = cohort["name"]
        score_dir = paths[name]["scores"]
        score_dir.mkdir()
        (score_dir / "scores.jsonl").write_text("".join(json.dumps(s) + "\n" for s in scores[name]))
        (score_dir / "provenance.json").write_text(json.dumps({
            "input_seal_sha256": cohort["input_seal_sha256"], "source_files": plan["source_files"],
            "assignment_sha256": "3" * 64}))
        (score_dir / "SCORE_SEAL.json").write_text(json.dumps({"complete": True, "cohort": name,
            "plan_sha256": a.sha(plan_path),
            "files": {p: a.sha(score_dir / p) for p in ("scores.jsonl", "provenance.json")}}))
    return plan_path, paths


def argv(plan, paths, name, out):
    return ["--plan", str(plan), "--cohort", name, "--scores-dir", str(paths[name]["scores"]),
            "--labels", str(paths[name]["labels"]), "--out", str(out)]


class ValuesTests(unittest.TestCase):
    def test_perfect_and_reversed_D_no_sign_repair(self):
        plan, labels, scores = fixture()
        cohort = a.select_cohort(plan, "w12")
        rows, ledger = a.compute_values(scores["w12"], labels["w12"], cohort)
        self.assertTrue(all(r["D"] == 1 for r in rows))
        self.assertTrue(all(r["P"] == -3 for r in rows))
        self.assertEqual([r["id"] for r in ledger], [r["id"] for r in cohort["items"]])
        reversed_scores = copy.deepcopy(scores["w12"])
        for s in reversed_scores:
            s["candidate"] = "B" if s["candidate"] == "A" else "A"
        rows, _ = a.compute_values(reversed_scores, labels["w12"], cohort)
        self.assertTrue(all(r["D"] == 0 for r in rows))

    def test_fixed_preference_half_and_token_counts_do_not_weight_phrasings(self):
        plan, labels, scores = fixture()
        for s in scores["w12"]:
            s["mean_logprob"] = -1 if s["candidate"] == "A" else -2
        rows, _ = a.compute_values(scores["w12"], labels["w12"], plan["cohorts"][0])
        self.assertTrue(all(r["D"] == .5 and r["P"] == -1.5 for r in rows))
        plan, labels, scores = fixture()
        rows, _ = a.compute_values(scores["w12"], labels["w12"], plan["cohorts"][0])
        # True phrasing scores -2/-4 with token counts 1/7 must average to -3, not -3.75.
        self.assertTrue(all(r["P"] == -3 for r in rows))

    def test_average_pair_scores_before_item_median(self):
        plan, labels, scores = fixture()
        truth = {r["id"]: r["value"] for r in labels["w12"]}
        for s in scores["w12"]:
            if s["candidate"] == truth[s["id"]]:
                i = int(s["id"].rsplit("_", 1)[1])
                s["mean_logprob"] = ([-1, -1, -1, -9] if s["phrasing"] == 0 else [-9, -1, -9, -1])[i]
        rows, _ = a.compute_values(scores["w12"], labels["w12"], plan["cohorts"][0])
        self.assertTrue(all(r["P"] == -5 for r in rows))

    def test_tied_auc_matches_pairwise_probability(self):
        y = np.array([1, 1, 0, 0])
        scores = np.array([1., 1., 1., 0.])
        expected = np.mean((scores[y == 1, None] > scores[y == 0]).astype(float)
                           + .5*(scores[y == 1, None] == scores[y == 0]))
        self.assertEqual(a.auc(y, scores), expected)
        self.assertEqual(expected, .75)
        with self.assertRaises(ValueError):
            a.auc([1, 1], [1, 2])

    def test_companion_values_are_nonblind_D_only(self):
        plan, labels, scores = fixture()
        rows, ledger = a.compute_values(scores["suraj_exp13"], labels["suraj_exp13"], plan["cohorts"][1])
        self.assertTrue(all("P" not in r for r in rows))
        self.assertTrue(all("true_candidate_score" not in r for r in ledger))

    def test_exact_grid_and_label_validation(self):
        mutations = (
            lambda s, y: s.append(dict(s[0])), lambda s, y: s.pop(),
            lambda s, y: s[0].update(phrasing=True), lambda s, y: s[0].update(phrasing=2),
            lambda s, y: s[0].update(mean_logprob=float("inf")), lambda s, y: s[0].update(mean_logprob=.00001),
            lambda s, y: s[0].update(token_count=True), lambda s, y: s[0].update(token_count=0),
            lambda s, y: s[0].update(feature="unexpected"), lambda s, y: y.pop(),
            lambda s, y: y[0].update(value="C"), lambda s, y: y.append(dict(y[0])),
            lambda s, y: [r.update(value="A") for r in y],
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                plan, labels, scores = fixture()
                mutation(scores["w12"], labels["w12"])
                with self.assertRaises(ValueError):
                    a.compute_values(scores["w12"], labels["w12"], plan["cohorts"][0])

    def test_plan_order_and_population_are_frozen(self):
        for mutation in (lambda p: p.update(status="PENDING"), lambda p: p["cohorts"].reverse(),
                         lambda p: p["cohorts"][0].update(blind=False),
                         lambda p: p["cohorts"][0].update(expected_scores=1),
                         lambda p: p["cohorts"][0]["items"].append(dict(p["cohorts"][0]["items"][0]))):
            plan, _, _ = fixture()
            mutation(plan)
            with self.assertRaises(ValueError):
                a.select_cohort(plan, "w12")


class CustodyTests(unittest.TestCase):
    def test_score_and_source_failures_precede_labels(self):
        for fault in ("score", "source", "provenance", "label"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                root = Path(d); plan, paths = staged_fixture(root)
                if fault == "score":
                    with (paths["w12"]["scores"] / "scores.jsonl").open("a") as f: f.write("{}\n")
                elif fault == "source":
                    p = a.read(plan); p["source_files"][next(iter(p["source_files"]))] = "0"*64
                    plan.write_text(json.dumps(p))
                elif fault == "provenance":
                    (paths["w12"]["scores"] / "provenance.json").write_text("{}")
                else:
                    paths["w12"]["labels"].write_text("[]")
                original, opened = a.read, []
                def tracked(path):
                    opened.append(Path(path))
                    return original(path)
                with mock.patch.object(a, "read", side_effect=tracked):
                    with self.assertRaises(ValueError):
                        a.main(argv(plan, paths, "w12", root / "out"))
                self.assertNotIn(paths["w12"]["labels"], opened)
                self.assertFalse((root / "out").exists())

    def test_companion_cannot_join_labels_before_primary_posted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); plan, paths = staged_fixture(root)
            with mock.patch.object(a, "compute_values", side_effect=AssertionError("must not compute")):
                with self.assertRaisesRegex(ValueError, "primary seal"):
                    a.main(argv(plan, paths, "suraj_exp13", root / "out"))
            self.assertFalse((root / "out").exists())

    def test_primary_then_posted_companion_seals_and_keeps_item_pairing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); plan, paths = staged_fixture(root)
            primary = root / "primary"
            a.main(argv(plan, paths, "w12", primary))
            seal = a.read(primary / "VALUES_SEAL.json")
            self.assertEqual(set(seal["files"]), {"METRICS.json", "RESULTS.md", "cache/ITEM_SCORES.jsonl"})
            for name, digest in seal["files"].items(): self.assertEqual(a.sha(primary / name), digest)
            ledger = a.jsonl(primary / "cache/ITEM_SCORES.jsonl")
            self.assertEqual([x["id"] for x in ledger], [x["id"] for x in a.read(plan)["cohorts"][0]["items"]])
            posted = root / "posted.json"
            posted.write_text(json.dumps({"issuer": "W-text", "posted": True,
                "posted_at": datetime.now(timezone.utc).isoformat(), "primary_seal_sha256": a.sha(primary / "VALUES_SEAL.json"),
                "publication_reference": "Synthetic current-chat publication fixture; no real posting occurred"}))
            args = argv(plan, paths, "suraj_exp13", root / "companion") + ["--primary-seal", str(primary / "VALUES_SEAL.json"), "--primary-posted-record", str(posted)]
            a.main(args)
            companion = a.read(root / "companion/METRICS.json")
            self.assertFalse(companion["blind"])
            self.assertEqual(companion["primary_posting"]["issuer"], "W-text")
            self.assertTrue(companion["primary_posting"]["publication_reference"])
            self.assertTrue(all("P" not in row for row in companion["rows"]))
            self.assertIn("NON-BLIND", (root / "companion/RESULTS.md").read_text())
            with self.assertRaisesRegex(ValueError, "Existing output"):
                a.main(args)

    def test_primary_attestation_and_payload_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); plan_path, paths = staged_fixture(root); plan = a.read(plan_path)
            primary = root / "primary"; a.main(argv(plan_path, paths, "w12", primary))
            seal = primary / "VALUES_SEAL.json"; posted = root / "posted.json"
            valid = {"issuer": "integrator", "posted": True, "posted_at": datetime.now(timezone.utc).isoformat(),
                     "primary_seal_sha256": a.sha(seal), "publication_reference": "synthetic-publication-reference"}
            for change in ({"posted": False}, {"issuer": "worker"}, {"publication_reference": " "}, {"primary_seal_sha256": "0"*64},
                           {"posted_at": "2026-01-01T00:00:00Z"}, {"posted_at": "2999-01-01T00:00:00Z"},
                           {"posted_at": "2026-10-25T10:00:00"}):
                posted.write_text(json.dumps(valid | change))
                with self.assertRaises(ValueError): a.verify_primary_posted(seal, posted, plan_path, plan)
            posted.write_text(json.dumps(valid)); (primary / "cache/ITEM_SCORES.jsonl").write_text("{}\n")
            with self.assertRaises(ValueError): a.verify_primary_posted(seal, posted, plan_path, plan)


if __name__ == "__main__":
    unittest.main()
