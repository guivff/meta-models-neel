"""CPU-only synthetic metadata tests; contains no experimental item text."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import channel_contract as C
import parity_gate as G


def binding(name):
    return {"path": name, "sha256": "a" * 64}


def expanded_scope():
    packet = Path(__file__).with_name("ROW_DEFINITIONS.json")
    return C.scope_from_definition_packet({"path": str(packet.resolve()), "sha256": C.DEFINITION_PACKET_SHA256})


def expanded_rules():
    path = Path(__file__).with_name("RULE_CLARIFICATION_2026-10-25.json")
    return C.expanded_rule_binding({"path": str(path.resolve()), "sha256": C.RULE_AUTHORITY_SHA256})


def plan(scope=None, rule_binding=None):
    return C.make_plan(binding("new-bank"), binding("new-freeze"), binding("candidate-export"),
                       assets_binding=binding("assets.json"),
                       parity_binding={"path": "INPUT_SEAL.json", "sha256": G.INPUT_SHA256},
                       frozen_at="2026-10-25T12:00:00Z", candidate_bound_at="2026-10-25T12:01:00Z",
                       source_bindings=[binding(p) for p in C.REQUIRED_SOURCE_PATHS], scope=scope, rule_binding=rule_binding)


def freeze_receipt(scope=None):
    scope = C.original_scope() if scope is None else scope
    count = len(scope["rows"]) * 168
    return {"scope": scope["id"], "item_count": count, "bank_sha256": "a" * 64,
            "definition_packet_sha256": C.DEFINITION_PACKET_SHA256,
            "automatic_label_check": {"status": "PASS", "checked": count, "passed": count, "receipt_sha256": "b" * 64},
            "automatic_length_check": {"status": "PASS", "checked": count // 2, "passed": count // 2, "receipt_sha256": "c" * 64},
            "rows": {r: {"values": ["synthetic-a", "synthetic-b"], "class": scope.get("taxonomy", {}).get(r, "synthetic"),
                          "dev": 84, "test": 84, "family_count": 12, "fillers_per_family": 7} for r in scope["rows"]}}


def metrics():
    return {r: {"oracle_descriptive": .65, "oracle_value_word:word": .80,
                "probe": .90, "nla": .75, "continuation": .70} for r in C.ROWS}


class ContractTests(unittest.TestCase):
    def test_plan_is_bound_and_postfreeze(self):
        p = plan()
        C.validate_plan(p)
        p["channels"] = copy.deepcopy(p["channels"])
        p["channels"]["nla"]["prefix"] = ""
        with self.assertRaisesRegex(ValueError, "digest"):
            C.validate_plan(p)
        with self.assertRaisesRegex(ValueError, "predates"):
            C.make_plan(binding("b"), binding("f"), binding("c"), source_bindings=[], assets_binding=binding("assets.json"),
                        frozen_at="2026-10-25T12:00:00Z", candidate_bound_at="2026-10-25T11:59:00Z")

    def test_exact_thresholds_and_full_denominators(self):
        m = metrics()
        for r in C.CONTENT:
            m[r]["oracle_descriptive"] = .85
        h = C.adjudicate(m)
        self.assertEqual([h[k]["status"] for k in ("H1", "H2", "H4", "H5")], ["REPLICATED"] * 4)
        self.assertEqual(h["H1"]["denominator"], 6)
        self.assertEqual(h["H4"]["denominator"], 4)
        del m[C.STRUCTURE[0]]["probe"]
        self.assertEqual(C.adjudicate(m)["H1"]["status"], "NOT_EVALUABLE")
        m[C.STATES[0]]["continuation"] = None
        self.assertEqual(C.adjudicate(m)["H4"]["status"], "NOT_EVALUABLE")

    def test_h1_needs_probe_in_same_rows(self):
        m = metrics()
        for r in C.STRUCTURE[:3]:
            m[r]["probe"] = .899
        self.assertEqual(C.adjudicate(m)["H1"]["status"], "NOT_REPLICATED")

    def test_h3_sealed_matching_variant_and_unavailable(self):
        m = metrics()
        receipt = {"E30_R2_met": True, "eligible_rows": [C.ROWS[0]],
                   "matching_variant_ids": {C.ROWS[0]: ["word"]}, "receipt_sha256": "b" * 64}
        self.assertEqual(C.adjudicate(m)["H3"]["status"], "NOT_EVALUABLE")
        self.assertEqual(C.adjudicate(m, receipt)["H3"]["status"], "REPLICATED")
        receipt["matching_variant_ids"][C.ROWS[0]].append("digit")
        self.assertEqual(C.adjudicate(m, receipt)["H3"]["status"], "NOT_EVALUABLE")
        receipt["old_scores"] = []
        with self.assertRaisesRegex(ValueError, "eligibility only"):
            C.adjudicate(m, receipt)

    def test_raw_logodds_average_then_auc_and_legacy_e15_helper(self):
        dev = [[0., 1.], [0., 1.], [1., 0.], [1., 0.]]
        self.assertEqual(C.continuation_valid_pairs(dev, [0, 0, 1, 1]), [0])
        self.assertEqual(C.average_pair_scores(dev, [0]), [0., 0., 1., 1.])
        self.assertEqual(C.auroc([1., 1.], [0, 1]), .5)
        with self.assertRaises(ValueError):
            C.average_pair_scores(dev, [])

    def test_budget_counts_prior_setup_and_retrieval(self):
        g = C.forecast_gate(prior_gpu_seconds=1000, allocation_started_at=100, now=1100,
                            remaining_work_seconds=5000, hard_deadline=9900)
        self.assertEqual(g["current_allocation_elapsed_seconds"], 1000)
        self.assertTrue(g["fits"])
        g = C.forecast_gate(prior_gpu_seconds=1000, allocation_started_at=100, now=1100,
                            remaining_work_seconds=6000, hard_deadline=9900)
        self.assertFalse(g["fits"])
        self.assertEqual(g["padded_remaining_forecast_seconds"], 9180)

    def test_assignment_requires_external_stop_and_integrator(self):
        p = plan()
        epoch = C.instant(C.EXPANDED_FREEZE_DEADLINE).timestamp()
        a = {"operator": "integrator", "experiment": "E36", "plan_sha256": p["plan_sha256"],
             "gpu_count": 1, "gpu_type": "H200", "pod_id": "synthetic", "prior_gpu_seconds": 0,
             "allocation_started_at": epoch + 100, "hard_deadline": epoch + 10000,
             "phase_estimates_seconds": {p: 100 for p in C.PHASES},
             "external_stop": {"confirmed": True, "deadline": epoch + 10000, "receipt": "synthetic-controller-receipt"}}
        C.validate_assignment(a, p, epoch + 200)
        with self.assertRaisesRegex(ValueError, "fallback is not yet eligible"):
            C.validate_assignment(a, p, epoch - 1)
        a["external_stop"]["confirmed"] = False
        with self.assertRaisesRegex(ValueError, "external stop"):
            C.validate_assignment(a, p, epoch + 200)

    def test_launch_request_is_pending_and_contains_no_labels(self):
        request = C.make_launch_request(plan(), plan_path="p.json", assignment_path="a.json", assets_path="assets.json",
                                       repository_root="/synthetic/repo", output_path="/synthetic/output", prior_gpu_seconds=500,
                                       phase_estimates_seconds={p: 100 for p in C.PHASES})
        self.assertEqual(request["status"], "AWAITING_INTEGRATOR_ASSIGNMENT")
        self.assertEqual(request["maximum_current_allocation_seconds"], 10300)
        self.assertNotIn("--labels", request["command"])
        self.assertTrue(request["external_stop_required"])
        with self.assertRaisesRegex(ValueError, "assets differ"):
            C.make_launch_request(plan(), plan_path="p.json", assignment_path="a.json", assets_path="unbound-assets.json",
                                  repository_root="/synthetic/repo", output_path="/synthetic/output", prior_gpu_seconds=500,
                                  phase_estimates_seconds={p: 100 for p in C.PHASES})

    def test_expanded_scope_uses_definition_packet_and_exact4200_count(self):
        scope = expanded_scope()
        self.assertEqual((len(scope["rows"]), len(scope["structure_rows"]), len(scope["content_rows"])), (25, 16, 9))
        self.assertIsNone(scope["h4_rows"])
        p = plan(scope)
        C.validate_plan(p)
        self.assertEqual((p["item_count"], p["cap_gpu_seconds"]), (4200, 60000))
        bad = copy.deepcopy(scope)
        bad["structure_rows"].pop()
        with self.assertRaisesRegex(ValueError, "definition packet"):
            C.validate_scope(bad)
        bad_plan = copy.deepcopy(p)
        bad_plan["cap_gpu_seconds"] = 10800
        bad_plan["plan_sha256"] = C.canonical_hash({k: v for k, v in bad_plan.items() if k != "plan_sha256"})
        with self.assertRaisesRegex(ValueError, "GPU budget"):
            C.validate_plan(bad_plan)

    def test_expanded_rules_fail_closed_until_explicit_registration_binding(self):
        scope = expanded_scope()
        self.assertTrue(all(x["status"] == "NOT_EVALUABLE" for x in C.adjudicate({}, scope=scope).values()))
        request = C.make_launch_request(plan(scope), plan_path="p.json", assignment_path="a.json", assets_path="assets.json",
                                       repository_root="/synthetic/repo", output_path="/synthetic/output", prior_gpu_seconds=552.8,
                                       phase_estimates_seconds={p: 100 for p in C.PHASES})
        self.assertEqual(request["status"], "HELD_UNRESOLVED_RULE_BINDING")
        bad = expanded_rules()
        bad["required_counts"]["H2"] = 9
        with self.assertRaisesRegex(ValueError, "clarification"):
            plan(scope, bad)

    def test_expanded_counts_are_registered11_7_5_11_not_scaled(self):
        scope = expanded_scope()
        m = {r: {"oracle_descriptive": .66, "probe": .90, "nla": .66, "continuation": .69} for r in scope["rows"]}
        for r in scope["structure_rows"][:11]:
            m[r].update(oracle_descriptive=.65, nla=.75)
        for k, r in enumerate(scope["content_rows"]):
            m[r]["oracle_descriptive"] = .85 if k < 7 else .84
        for r in C.EXPANDED_H4_ROWS[:5]:
            m[r]["continuation"] = .70
        h = C.adjudicate(m, scope=scope, rule_binding=expanded_rules())
        self.assertEqual([h[k]["required"] for k in ("H1", "H2", "H4", "H5")], [11, 7, 5, 11])
        self.assertEqual([h[k]["denominator"] for k in ("H1", "H2", "H4", "H5")], [16, 9, 7, 16])
        self.assertTrue(all(h[k]["status"] == "REPLICATED" for k in ("H1", "H2", "H4", "H5")))
        m[scope["content_rows"][0]]["oracle_descriptive"] = .84
        self.assertEqual(C.adjudicate(m, scope=scope, rule_binding=expanded_rules())["H2"]["status"], "NOT_REPLICATED")
        self.assertEqual(plan()["cap_gpu_seconds"], 10800)
        self.assertEqual(C.adjudicate(metrics())["H4"]["denominator"], 4)

    def test_monday_noon_cet_fallback_cutoff_is_exact(self):
        self.assertEqual(C.scope_decision(now="2026-10-26T10:59:59Z")["status"], "AWAITING_EXPANDED_FREEZE")
        self.assertEqual(C.scope_decision(now="2026-10-26T11:00:00Z")["scope_id"], "original8")
        self.assertEqual(C.scope_decision(now="2026-10-26T11:00:00Z", expanded_frozen_at="2026-10-26T12:00:00+01:00")["scope_id"], "expanded25")
        self.assertEqual(C.scope_decision(now="2026-10-26T11:00:01Z", expanded_frozen_at="2026-10-26T11:00:01Z")["scope_id"], "original8")

    def test_expanded_budget_does_not_change_original_budget(self):
        args = dict(prior_gpu_seconds=0, allocation_started_at=100, now=200, remaining_work_seconds=10000, hard_deadline=28900)
        self.assertFalse(C.forecast_gate(**args)["fits"])
        self.assertTrue(C.forecast_gate(**args, cap_gpu_seconds=60000)["fits"])

    def test_gpu_fallback_requires_verified_wait_and_memory_receipts(self):
        a = {"gpu_count": 1, "gpu_type": "B200", "allocation_started_at": 1000}
        with self.assertRaisesRegex(ValueError, "verified"):
            C.validate_gpu_assignment(a, 1001)
        a["gpu_fallback"] = {"h200_unavailable": {"verified": True, "verified_by": "integrator", "receipt_sha256": "d" * 64,
                                                     "started_at": 0, "ended_at": 900},
                             "memory_check": {"verified": True, "verified_by": "integrator", "receipt_sha256": "e" * 64,
                                              "status": "PASS", "gpu_type": "B200", "required_bytes": 100, "available_bytes": 200}}
        C.validate_gpu_assignment(a, 1001)
        a["gpu_fallback"]["h200_unavailable"]["ended_at"] = 899
        with self.assertRaisesRegex(ValueError, "15 minutes"):
            C.validate_gpu_assignment(a, 1001)

    def test_freeze_requires_full_label_and_length_checks_and_e30_separate_budget(self):
        receipt = freeze_receipt()
        C.validate_freeze_receipt(receipt, binding("new-bank"))
        bad = copy.deepcopy(receipt)
        bad["automatic_length_check"]["passed"] -= 1
        with self.assertRaisesRegex(ValueError, "automatic_length_check"):
            C.validate_freeze_receipt(bad, binding("new-bank"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FREEZE_RECEIPT.json"
            path.write_text(json.dumps(receipt))
            handoff = C.make_e30_replication_handoff(bank_binding=binding("new-bank"),
                freeze_binding={"path": str(path), "sha256": C.file_hash(path)},
                e30_candidates_binding=binding("/not-opened/CANDIDATES.json"),
                frozen_at="2026-10-25T12:00:00Z", candidates_bound_at="2026-10-25T12:01:00Z")
            self.assertEqual(handoff["aggregate_cap_gpu_seconds"], 1800)
            self.assertEqual(handoff["e36_cap_unchanged"], 10800)
            self.assertEqual(handoff["budget_account"], "E30_SECOND_BANK_SEPARATE_FROM_E36")


if __name__ == "__main__":
    unittest.main()
