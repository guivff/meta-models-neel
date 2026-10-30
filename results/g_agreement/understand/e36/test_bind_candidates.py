"""Synthetic candidate-only tests; no experimental items or outcomes."""
import copy
import unittest
from unittest.mock import patch

import channel_contract as C
import bind_candidates as B


def fixtures():
    packet = {"rows": {r: {"values": ["synthetic-a", "synthetic-b"]} for r in C.ROWS}}
    w1 = {r: {"values": ["synthetic-a", "synthetic-b"], "score_orientation": "value_A_positive",
              "olens": [["- A one", "- B one"], ["- A two", "- B two"]],
              "nla": [["A one", "B one"], ["A two", "B two"]], "ignored_field": object()} for r in C.ROWS}
    e15 = {"orientation": "W1 value A positive, no sign reversal", "oracle_prefix": "- ",
           "rows": {r: {"pairs": [{"A": "  A", "B": "\tB", "A_ids": [1], "B_ids": [2]},
                                     {"A": "   ", "B": "\t", "A_ids": [3], "B_ids": [4]}]} for r in (*C.STATES, "table_column")}}
    e30 = {"orientation": "each pair is [value A, value B] in W1 templates.json 'values' order; score = logP(A) - logP(B), A positive",
           "before_any_score": True, "w1_templates_sha256": B.SOURCES["w1_descriptive_nla"]["sha256"],
           "values": {r: ["synthetic-a", "synthetic-b"] for r in C.ROWS},
           "candidates": {r: [["- A value", "- B value"], ["- A predicate", "- B predicate"]] for r in C.ROWS}}
    return packet, {"w1_descriptive_nla": w1, "e15_continuation": e15, "e30_value_word": e30}


class CandidateBindingTests(unittest.TestCase):
    def test_exact_values_whitespace_pair_order_and_single_e30_channel(self):
        packet, source = fixtures()
        result, audit = B.normalize(packet, source, scope=C.original_scope())
        for row in C.ROWS:
            self.assertEqual(result["rows"][row]["olens_descriptive"], source["w1_descriptive_nla"][row]["olens"])
            self.assertEqual(result["rows"][row]["nla"], source["w1_descriptive_nla"][row]["nla"])
            self.assertEqual(result["rows"][row]["olens_value_word"], {"e30_bullet": source["e30_value_word"]["candidates"][row]})
            self.assertEqual(audit[row]["e30_raw_pair_indices"], [0, 1])
            self.assertNotIn("ignored_field", result["rows"][row])
        self.assertEqual(result["rows"]["prose_paren"]["continuation"], [["  A", "\tB"], ["   ", "\t"]])
        self.assertTrue(result["rows"]["table_column"]["continuation"])
        self.assertNotIn("table_column", C.EXPANDED_H4_ROWS)
        result["rows"]["prose_paren"]["olens_descriptive"][0][0] = "changed synthetic copy"
        self.assertEqual(source["w1_descriptive_nla"]["prose_paren"]["olens"][0][0], "- A one")

    def test_orientation_mismatch_fails_instead_of_flipping(self):
        packet, source = fixtures()
        source["e30_value_word"]["values"]["prose_paren"].reverse()
        with self.assertRaisesRegex(ValueError, "ordered values differ"):
            B.normalize(packet, source, scope=C.original_scope())

    def test_ambiguous_or_changed_candidate_schema_fails(self):
        packet, source = fixtures()
        source["e30_value_word"]["candidates"]["prose_paren"] = {"unexpected": []}
        with self.assertRaisesRegex(ValueError, "two frozen pairs"):
            B.normalize(packet, source, scope=C.original_scope())
        packet, source = fixtures()
        source["w1_descriptive_nla"]["prose_paren"]["olens"][0][0] = "missing bullet"
        with self.assertRaisesRegex(ValueError, "bullet prefix"):
            B.normalize(packet, source, scope=C.original_scope())

    def test_freeze_failure_precedes_any_candidate_access(self):
        with patch.object(B, "freeze_gate", side_effect=ValueError("not frozen")), patch.object(B, "load_candidate_sources") as load:
            with self.assertRaisesRegex(ValueError, "not frozen"):
                B.bind(now="2026-10-25T00:00:00Z")
            load.assert_not_called()

    def test_actual_receipts_reject_a_pre_freeze_timestamp_without_items(self):
        with self.assertRaisesRegex(ValueError, "before bank freeze"):
            B.freeze_gate(B.ROOT, "2026-10-25T00:00:00Z")

    def test_all_registered_h4_rows_need_frozen_pairs(self):
        packet, source = fixtures()
        del source["e15_continuation"]["rows"]["python_string"]
        with self.assertRaisesRegex(ValueError, "H4 row missing"):
            B.normalize(packet, source, scope=C.original_scope())


if __name__ == "__main__":
    unittest.main()
