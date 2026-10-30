"""Mock acquisition tests. Empty text is intentional: no item examples authored."""
import json
import ast
import builtins
import contextlib
from pathlib import Path
import symtable
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import channel_contract as C
import worker as W
from test_parity_gate import synthetic_inputs


def items(rows=C.ROWS):
    return [{"id": f"{row}:{family}:{n}", "feature": row, "split": "dev" if family < 6 else "test",
             "cluster": str(family), "ids": [1], "text": ""}
            for row in rows for family in range(12) for n in range(14)]


def candidates(rows=C.ROWS):
    pair = [["synthetic-a", "synthetic-b"]]
    return {"rows": {row: {"values": ["synthetic-a", "synthetic-b"], "olens_descriptive": pair,
                           "olens_value_word": {"word": pair, "digit": pair}, "nla": pair,
                           "continuation": pair if row in C.STATES else []} for row in rows}}


class FakeBudget:
    def __init__(self):
        self.calls = []

    def call(self, phase, fn, remaining_units=0):
        self.calls.append((phase, remaining_units))
        return fn()

    def complete_empty(self, phase):
        self.calls.append((phase, 0))

    def start_science(self):
        pass


class FakeBackend:
    def __init__(self):
        self.state = "new"

    def load_oracle(self):
        self.state = "oracle"

    def validate_tokenization(self, values):
        assert all(x["ids"] == [1] for x in values)

    def capture(self, values):
        assert self.state == "oracle" and len(values) <= 8
        return {42: [42] * len(values), 44: [44] * len(values)}

    def join(self, parts):
        return [x for part in parts for x in part]

    def take(self, h, indices):
        return [h[i] for i in indices]

    def save_capture(self, path, values):
        Path(path).write_text(json.dumps(values))

    def load_nla(self):
        self.state = "nla"

    def score(self, channel, values, acts, pairs):
        assert all(x["split"] == "test" for x in values)
        if channel == "nla":
            assert self.state == "nla" and set(acts) == {42}
        else:
            assert self.state == "oracle" and set(acts) == {44}
        return [[float(j) for j in range(len(pairs))] for _ in values]


class WorkerTests(unittest.TestCase):
    def test_complete_label_free_pipeline_with_separate_variants(self):
        budget = FakeBudget()
        with tempfile.TemporaryDirectory() as tmp:
            result = W.run_pipeline(items(), candidates(), FakeBackend(), budget, tmp, parity_inputs=synthetic_inputs())
            self.assertTrue(result["label_free"])
            records = [json.loads(line) for line in (Path(tmp) / "scores.jsonl").read_text().splitlines()]
            counts = {}
            for r in records:
                counts[r["channel"]] = counts.get(r["channel"], 0) + 1
                self.assertNotIn("value", r)
            self.assertEqual(counts, {"oracle_descriptive": 672,
                                     "oracle_value_word:word": 672, "oracle_value_word:digit": 672,
                                     "continuation": 336, "nla": 672})
            self.assertEqual(len(json.loads((Path(tmp) / "items.order.json").read_text())), 1344)
            bank = items()
            labels = [{k: x[k] for k in ("id", "feature", "split", "cluster")} | {
                "value": "synthetic-a" if int(x["id"].split(":")[-1]) % 2 == 0 else "synthetic-b"} for x in bank]
            target = {x["id"]: float(x["value"] == "synthetic-a") for x in labels}
            for rec in records:
                rec["scores"] = [target[rec["id"]]]
            callback = lambda indices, y, groups: (y, [{"mock_only": True}])
            analysis = C.analyse_acquisition(bank, labels, candidates(), records, [0] * 1344,
                                             repo_root="unused-in-mock", probe_callback=callback)
            self.assertEqual(analysis["hypotheses"]["H4"]["status"], "REPLICATED")
            self.assertEqual(analysis["hypotheses"]["H3"]["status"], "NOT_EVALUABLE")
            records.remove(next(r for r in records if r["channel"] == "continuation"))
            analysis = C.analyse_acquisition(bank, labels, candidates(), records, [0] * 1344,
                                             repo_root="unused-in-mock", probe_callback=callback)
            self.assertEqual(analysis["hypotheses"]["H4"]["status"], "NOT_EVALUABLE")
            self.assertEqual(analysis["hypotheses"]["H4"]["denominator"], 4)
        phases = [p for p, _ in budget.calls]
        self.assertLess(phases.index("continuation"), phases.index("nla_setup"))
        self.assertEqual(phases.count("capture"), 168)

    def test_labels_and_family_leakage_rejected_before_model_load(self):
        bank = items()
        bank[0]["value"] = 0
        with self.assertRaisesRegex(ValueError, "labels"):
            C.validate_items(bank)
        bank = items()
        bank[84]["cluster"] = "0"
        with self.assertRaises(ValueError):
            C.validate_items(bank)

    def test_changed_function_hash_fails_without_importing_source_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.py"
            path.write_text("raise RuntimeError('module must never import')\ndef operation():\n    return 7\n")
            source = "def operation():\n    return 7"
            import hashlib
            f = W.frozen_function(tmp, "source.py", "operation", hashlib.sha256(source.encode()).hexdigest())
            self.assertEqual(f(), 7)
            with self.assertRaisesRegex(ValueError, "recipe changed"):
                W.frozen_function(tmp, "source.py", "operation", "0" * 64)

    def test_runtime_budget_counts_setup_and_aborts_before_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = {"phase_estimates_seconds": {p: 2000 for p in W.PHASES}, "prior_gpu_seconds": 0,
                 "allocation_started_at": 100, "hard_deadline": 10900}
            budget = W.Budget(a, tmp, clock=lambda: 200)
            called = []
            with self.assertRaisesRegex(ValueError, "warm forecast"):
                budget.call("capture", lambda: called.append(True))
            self.assertEqual(called, [])

    def test_frozen_operational_source_recipes_still_match(self):
        root = Path(__file__).resolve().parents[4]
        self.assertTrue(callable(W.frozen_function(root, C.PROBE_RECIPE["source"], C.PROBE_RECIPE["function"],
                                                  C.PROBE_RECIPE["function_sha256"])))
        for name, digest in C.E15_SOURCE_HASHES.items():
            self.assertTrue(callable(W.frozen_function(root, "projects/g_agreement/understand/e15.py", name, digest)))

    def test_easy_warm_batch_does_not_erase_conservative_forecast(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = {"phase_estimates_seconds": {p: 0 for p in W.PHASES}, "prior_gpu_seconds": 0,
                 "allocation_started_at": 100, "hard_deadline": 10900}
            a["phase_estimates_seconds"]["capture"] = 1000
            budget = W.Budget(a, tmp, clock=lambda: 200)
            budget.call("capture", lambda: None, remaining_units=9)
            self.assertEqual(budget.remaining["capture"], 900)

    def test_compiled_operational_functions_have_complete_namespaces(self):
        root = Path(__file__).resolve().parents[4]
        for relative, name, supplied in (("projects/g_agreement/understand/e15.py", "base_score", set()),
                                         (C.PROBE_RECIPE["source"], "grouped_probe", {"np", "P"})):
            source = (root / relative).read_text()
            node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
            snippet = ast.get_source_segment(source, node)
            table = symtable.symtable(snippet, relative, "exec").get_children()[0]
            def globals_used(scope):
                own = {s.get_name() for s in scope.get_symbols() if s.is_global() and s.is_referenced()}
                return own | set().union(*(globals_used(child) for child in scope.get_children()))
            missing = globals_used(table) - set(dir(builtins)) - supplied
            self.assertEqual(missing, set())

    def test_native_scoring_transposes_pair_major_output_and_uses_prefixes(self):
        class Tensor:
            ndim = 2
            shape = (2, 3)
            def detach(self): return self
            def float(self): return self
            def cpu(self): return self
            @property
            def T(self): return SimpleNamespace(tolist=lambda: [[1., 4.], [2., 5.], [3., 6.]])
        calls = []
        def oracle_score(h, block, pairs, prefix):
            calls.append((block, prefix))
            return Tensor()
        fake_torch = SimpleNamespace(no_grad=contextlib.nullcontext,
                                     isfinite=lambda _: SimpleNamespace(all=lambda: True))
        backend = W.NativeBackend("unused", "unused")
        backend.oracle = SimpleNamespace(paired_logodds_templates=oracle_score)
        with patch.dict(sys.modules, {"torch": fake_torch}):
            for channel in ("oracle_descriptive", "oracle_value_word", "continuation"):
                result = backend.score(channel, [{"ids": [1]}] * 3, "synthetic-activation", [["a", "b"], ["c", "d"]])
                self.assertEqual(result, [[1., 4.], [2., 5.], [3., 6.]])
        self.assertEqual(calls, [(44, ""), (44, ""), (44, "- ")])

    def test_native_capture_uses_exact_final_positions_and_pair_of_blocks(self):
        class Captured:
            ndim = 3
            shape = (2, 1, 3)
            def __getitem__(self, key):
                assert key == (slice(None), 0)
                return self
            def float(self): return self
            def cpu(self): return self
            def numpy(self): return [[0., 0., 0.], [0., 0., 0.]]
        def capture(model, seqs, layers, positions, **kwargs):
            self.assertEqual(seqs, [[1], [1, 2, 3]])
            self.assertEqual(layers, [42, 44])
            self.assertEqual(positions, [[0], [2]])
            self.assertEqual(kwargs, {"batch_size": 8, "pad_id": 0})
            return {42: Captured(), 44: Captured()}
        fake_torch = SimpleNamespace(no_grad=contextlib.nullcontext,
                                     isfinite=lambda _: SimpleNamespace(all=lambda: True))
        backend = W.NativeBackend("unused", "unused")
        backend.oracle = SimpleNamespace(base=contextlib.nullcontext, model=object(), tok=SimpleNamespace(pad_token_id=0))
        with patch.dict(sys.modules, {"torch": fake_torch, "mats.capture": SimpleNamespace(capture=capture)}):
            result = backend.capture([{"ids": [1]}, {"ids": [1, 2, 3]}])
        self.assertEqual(set(result), {42, 44})
        self.assertEqual(len(result[44]), 2)

    def test_assets_path_hash_and_revisions_are_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registered_path = root / "projects/g_agreement/manifest/assets.json"
            registered_path.parent.mkdir(parents=True)
            registered = {"target": {"revision": C.REGISTERED_REVISIONS["model"]},
                          "readers": {name: {"revision": C.REGISTERED_REVISIONS[name]} for name in ("olens", "nla")}}
            registered_path.write_text(json.dumps(registered))
            assets_path = root / "local-assets.json"
            local = {"revisions": C.REGISTERED_REVISIONS, "files": [{"path": "synthetic-weight", "sha256": "a" * 64}]}
            assets_path.write_text(json.dumps(local))
            plan = {"registered_revisions": C.REGISTERED_REVISIONS,
                    "assets": {"path": str(assets_path), "sha256": C.file_hash(assets_path)},
                    "source_bindings": [{"path": str(registered_path), "sha256": C.file_hash(registered_path)}]}
            self.assertEqual(W.verify_assets_binding(plan, assets_path, root), local)
            with self.assertRaisesRegex(ValueError, "runtime assets differ"):
                W.verify_assets_binding(plan, root / "unbound.json", root)
            local["revisions"] = dict(C.REGISTERED_REVISIONS, model="different-revision")
            assets_path.write_text(json.dumps(local))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                W.verify_assets_binding(plan, assets_path, root)
            plan["assets"]["sha256"] = C.file_hash(assets_path)
            with self.assertRaisesRegex(ValueError, "local asset revision mismatch"):
                W.verify_assets_binding(plan, assets_path, root)

    def test_runtime_code_root_must_match_source_bindings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = []
            for relative in C.REQUIRED_SOURCE_PATHS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("pass\n")
                sources.append({"path": str(path), "sha256": C.file_hash(path)})
            W.verify_source_bindings({"source_bindings": sources}, root)
            with self.assertRaisesRegex(ValueError, "runtime root"):
                W.verify_source_bindings({"source_bindings": sources}, root / "other-root")

    def test_expanded_pipeline_captures_all4200_items_without_scope_cuts(self):
        from test_channel_contract import expanded_scope
        scope = expanded_scope()
        bank, pairs = items(scope["rows"]), candidates(scope["rows"])
        C.validate_items(bank, scope)
        with self.assertRaises(ValueError):
            C.validate_items(bank)
        budget = FakeBudget()
        with tempfile.TemporaryDirectory() as tmp:
            result = W.run_pipeline(bank, pairs, FakeBackend(), budget, tmp, scope, parity_inputs=synthetic_inputs())
            self.assertEqual((result["items"], result["scope_id"]), (4200, "expanded25"))
            records = [json.loads(line) for line in (Path(tmp) / "scores.jsonl").read_text().splitlines()]
            self.assertEqual(sum(r["channel"] == "oracle_descriptive" for r in records), 2100)
            self.assertEqual(sum(r["channel"] == "nla" for r in records), 2100)
        self.assertEqual(sum(p == "capture" for p, _ in budget.calls), 525)

    def test_worker_budget_uses_bound_scope_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = {"phase_estimates_seconds": {p: 1200 for p in W.PHASES}, "prior_gpu_seconds": 0,
                 "allocation_started_at": 100, "hard_deadline": 28900}
            expanded = W.Budget(a, tmp, clock=lambda: 200, cap_gpu_seconds=60000)
            self.assertTrue(expanded.check()["fits"])
            original = W.Budget(a, tmp, clock=lambda: 200)
            with self.assertRaisesRegex(ValueError, "warm forecast"):
                original.check()

    def test_continuation_averages_all_frozen_pairs_without_dev_selection(self):
        bank, pairs = items(), candidates()
        for row in C.STATES:
            pairs["rows"][row]["continuation"] = [["synthetic-a", "synthetic-b"], ["synthetic-c", "synthetic-d"]]
        labels = [{k: x[k] for k in ("id", "feature", "split", "cluster")} | {
            "value": "synthetic-a" if int(x["id"].split(":")[-1]) % 2 == 0 else "synthetic-b"} for x in bank]
        target = {x["id"]: float(x["value"] == "synthetic-a") for x in labels}
        budget = FakeBudget()
        with tempfile.TemporaryDirectory() as tmp:
            W.run_pipeline(bank, pairs, FakeBackend(), budget, tmp, parity_inputs=synthetic_inputs())
            records = [json.loads(line) for line in (Path(tmp) / "scores.jsonl").read_text().splitlines()]
        self.assertTrue(all(r["split"] == "test" for r in records))
        self.assertNotIn("base_continuation_dev", C.PHASES)
        for r in records:
            if r["channel"] == "continuation":
                r["scores"] = [target[r["id"]], -target[r["id"]]]
        report = C.analyse_acquisition(bank, labels, pairs, records, [0] * 1344, repo_root="unused",
                                      probe_callback=lambda indices, y, groups: (y, []))
        for row in C.STATES:
            self.assertEqual(report["metrics"][row]["continuation"], .5)
            self.assertEqual(report["row_detail"][row]["continuation_frozen_pair_indices"], [0, 1])
        self.assertEqual(report["hypotheses"]["H4"]["status"], "NOT_REPLICATED")


if __name__ == "__main__":
    unittest.main()
