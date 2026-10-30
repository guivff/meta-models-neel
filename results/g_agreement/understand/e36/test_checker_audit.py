"""Independent 2026-10-25 audit: invented strings only; never read a bank.

Regression assertions permit conservative rejection of unsupported input, but
never a confident wrong label. No author module is imported.
"""
import hashlib
import json
from pathlib import Path
import unittest

from check_content import infer_label as content_label
from check_structure import infer_label as structure_label


PACKET_SHA256 = "2afa8e1202c0d7c181e6f95984b18bd59f99af81fc8cf8f27dcce02e8e38056c"


class IndependentSyntheticAudit(unittest.TestCase):
    def either_correct_or_rejected(self, checker, feature, text, correct):
        try:
            result = checker(feature, text)
        except ValueError:
            return
        self.assertEqual(result["value"], correct)

    def test_packet_orientation_all_25_rows(self):
        packet_bytes = Path(__file__).with_name("ROW_DEFINITIONS.json").read_bytes()
        self.assertEqual(hashlib.sha256(packet_bytes).hexdigest(), PACKET_SHA256)
        definitions = json.loads(packet_bytes)["rows"]
        # Each pair is invented here, in the packet's A/B order.
        examples = {
            "json_status": ('{"decision":"approved"', '{"decision":"rejected"'),
            "json_type": ('{"temperature":"warm', '{"temperature":24'),
            "latex_environment": (r"\begin{equation}x + y", r"\begin{quote}A quiet line"),
            "latex_role": (r"For every integer \(k\), \(k+0=k\).", r"Choose \(k=9\); this particular calculation gives \(k+0=9\)."),
            "latex_section": (r"\section{Dawn}The body begins", r"\section{A}a\section{B}b\section{C}c\section{D}d\section{E}e\section{F}The body begins"),
            "latex_subject": (r"A polynomial has a coefficient, a discriminant, and roots \(r\).", r"The triangle has an angle, a vertex, and a perpendicular altitude \(h\)."),
            "list_depth": ("- outer item", "- outer item\n  - middle item\n    - inner item"),
            "list_index": ("- first item", "- one\n- two\n- three\n- four\n- five\n- six"),
            "list_priority": ("- Replace the fuse immediately.", "- Complete the routine inspection."),
            "list_topic": ("- Reserve a hotel for the flight and journey.", "- Study the syllabus and textbook before the exam."),
            "prose_paren": ("The day (a quiet morning", "The day (a quiet morning) began slowly"),
            "prose_quote": ('She said "dawn holds', 'She said "dawn holds" and waited'),
            "prose_sentence": ("A soft mist gathers", "Rain fell. Wind rose. Birds hid. Clouds moved. Sun shone. A soft mist gathers"),
            "prose_sentiment": ("The event was wonderful and rewarding.", "The event was dreadful and unpleasant."),
            "prose_topic": ("The gardener mixes compost into soil for seedlings.", "Marine tides bring seawater across the coral reef."),
            "python_argument": ("emit(alpha", "emit(alpha, beta, gamma, delta, epsilon"),
            "python_comment": ("x = 3 # a quiet note", "x = 3"),
            "python_depth": ("[sample", "[[[sample"),
            "python_error": ("def f():\n    raise ValueError('bad')", "def f():\n    return 3"),
            "python_indent": ("def f():\n    x = 3", "def f():\n    if True:\n        if True:\n            x = 3"),
            "python_string": ('name = "quiet dawn', 'name = "quiet dawn" + suffix'),
            "table_column": ("| A | B | C | D | E |\n| --- | --- | --- | --- | --- |\n| item", "| A | B | C | D | E |\n| --- | --- | --- | --- | --- |\n| a | b | c | d | item"),
            "table_role": ("| Record | Category", "| Record | Category |\n| --- | --- |\n| record | category"),
            "table_row": ("| A |\n| --- |\n| one", "| A |\n| --- |\n| one |\n| two |\n| three |\n| four |\n| five |\n| six"),
            "table_status": ("| Decision |\n| --- |\n| approved", "| Decision |\n| --- |\n| rejected"),
        }
        self.assertEqual(set(examples), set(definitions))
        for feature, pair in examples.items():
            checker = content_label if definitions[feature]["class"] == "semantic" else structure_label
            for text, expected in zip(pair, definitions[feature]["values"]):
                with self.subTest(feature=feature, expected=expected):
                    result = checker(feature, text)
                    self.assertEqual(result["value"], expected)
                    self.assertIsInstance(result["evidence"], dict)

    def test_python_final_comment_is_not_final_statement(self):
        with self.assertRaises(ValueError):
            content_label("python_error", "def f():\n    return 1\n    # audit marker")

    def test_content_does_not_move_read_endpoint_before_final_newline(self):
        cases = (("json_status", '{"decision":"approved"\n'), ("table_status", "| Decision |\n| --- |\n| approved\n"), ("python_error", "def f():\n    return 1\n"))
        for feature, text in cases:
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                content_label(feature, text)

    def test_python_deterministic_exception_is_not_normal_return(self):
        for text in ("def f():\n    return 1 / 0", "def f():\n    missing = 1 / 0\n    return 1"):
            with self.subTest(text=text):
                self.either_correct_or_rejected(content_label, "python_error", text, "raise")

    def test_earlier_python_statements_must_support_normal_completion(self):
        self.either_correct_or_rejected(content_label, "python_error", "def f():\n    x = [][1]\n    return 1", "raise")
        with self.assertRaises(ValueError):
            content_label("python_error", "def f():\n    while True:\n        pass\n    return 1")

    def test_topic_requires_current_list_item(self):
        with self.assertRaises(ValueError):
            content_label("list_topic", "Book a hotel and flight for the journey.")
        self.either_correct_or_rejected(content_label, "list_topic", "- Book a hotel and flight for the journey.\n- Memorise these notes for tomorrow's quiz.", "study")

    def test_priority_uses_current_list_item(self):
        self.either_correct_or_rejected(content_label, "list_priority", "- Repair the outage immediately.\n- Refill the stationery cupboard every Monday.", "routine")

    def test_long_scope_negation_is_not_positive(self):
        self.either_correct_or_rejected(content_label, "prose_sentiment", "It was not in any way delightful or enjoyable.", "negative")

    def test_priority_long_scope_negation_is_not_urgent(self):
        self.either_correct_or_rejected(content_label, "list_priority", "- This is not in any way urgent.", "routine")

    def test_latex_question_is_not_a_theorem_statement(self):
        with self.assertRaises(ValueError):
            content_label("latex_role", r"For every integer \(n\), is \(n^2\) even?")

    def test_semantic_latex_read_endpoint_is_not_in_a_comment(self):
        cases = (("latex_role", r"For every integer \(n\), \(n+0=n\). % audit marker"), ("latex_subject", r"The polynomial has coefficients and roots \(r\). % audit marker"))
        for feature, text in cases:
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                content_label(feature, text)

    def test_blank_line_ends_markdown_status_table(self):
        with self.assertRaises(ValueError):
            content_label("table_status", "| Decision |\n| --- |\n\n| approved")

    def test_empty_call_has_no_argument(self):
        with self.assertRaises(ValueError):
            structure_label("python_argument", "f(")

    def test_definition_parameters_are_not_call_arguments(self):
        with self.assertRaises(ValueError):
            structure_label("python_argument", "def f(")

    def test_lambda_commas_are_not_call_commas(self):
        self.either_correct_or_rejected(structure_label, "python_argument", "f(lambda a, b, c, d, e: e", "first")

    def test_final_latex_comment_is_not_body_text(self):
        for feature, text in (("latex_environment", r"\begin{equation}x % audit marker"), ("latex_section", r"\section{One}Body % audit marker")):
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                structure_label(feature, text)

    def test_final_table_delimiter_is_not_cell_content(self):
        for feature in ("table_column", "table_role", "table_row"):
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                structure_label(feature, "| A | B |\n| --- | --- |\n| data |")
        with self.assertRaises(ValueError):
            structure_label("table_role", "| Header |")

    def test_json_invalid_escape_is_rejected(self):
        for text in ('{"x":"\\qbad', '{"\\q":"value'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                structure_label("json_type", text)

    def test_loose_markdown_list_does_not_restart_at_blank_line(self):
        # Two items are outside A=first and B=sixth-to-eighth.
        with self.assertRaises(ValueError):
            structure_label("list_index", "- one\n\n- two")

    def test_delimiter_closure_is_not_earlier_than_read_token(self):
        for feature, text in (("prose_quote", 'She said "go"'), ("prose_paren", "It was (warm)")):
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                structure_label(feature, text)


if __name__ == "__main__":
    unittest.main()
