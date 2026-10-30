"""Synthetic checker tests only: no author import and no bank traversal."""
import unittest

from check_content import infer_label


class SyntheticContentChecks(unittest.TestCase):
    def assert_value(self, feature, text, expected):
        result = infer_label(feature, text)
        self.assertEqual(result["value"], expected)
        self.assertIsInstance(result["evidence"], dict)

    def test_sentiment_actual_words(self):
        self.assert_value("prose_sentiment", "The result was superb and delightful.", "positive")
        self.assert_value("prose_sentiment", "The result was awful and depressing.", "negative")
        self.assert_value("prose_sentiment", "It was not awful, and never disappointing.", "positive")
        self.assert_value("prose_sentiment", "It was not delightful, and never enjoyable.", "negative")
        with self.assertRaises(ValueError):
            infer_label("prose_sentiment", "It was excellent but also awful.")
        with self.assertRaises(ValueError):
            infer_label("prose_sentiment", "It was not in any way delightful or enjoyable.")
        with self.assertRaises(ValueError):
            infer_label("prose_sentiment", "I cannot praise it enough; it was delightful.")

    def test_topic_actual_words(self):
        self.assert_value("prose_topic", "Compost enriches garden soil for seedlings.", "garden")
        self.assert_value("prose_topic", "Seawater salinity changes near the coral reef.", "ocean")
        with self.assertRaises(ValueError):
            infer_label("prose_topic", "A garden of coral beside seawater and soil.")

    def test_list_domains(self):
        self.assert_value("list_topic", "- Book a hotel and a flight for the journey.", "travel")
        self.assert_value("list_topic", "- Revise the syllabus and practice exam exercises.", "study")
        self.assert_value("list_priority", "- Fix the terminal immediately.", "urgent")
        self.assert_value("list_priority", "- File the receipt during the routine review.", "routine")
        self.assert_value("list_priority", "- This is not urgent; file it next month.", "routine")
        self.assert_value("list_topic", "- Book a hotel and flight for the journey.\n- Memorise these notes for tomorrow's quiz.", "study")
        self.assert_value("list_priority", "- Repair the outage immediately.\n- Refill the stationery cupboard every Monday.", "routine")
        self.assert_value("list_topic", "- Review the course syllabus\n  and practice the exam exercises.", "study")
        with self.assertRaises(ValueError):
            infer_label("list_topic", "Book a hotel and flight for the journey.")
        with self.assertRaises(ValueError):
            infer_label("list_priority", "- Act immediately.\n\nAn unrelated paragraph follows.")
        with self.assertRaises(ValueError):
            infer_label("list_priority", "- This is not in any way urgent.")
        self.assert_value("list_priority", "- Repair the cable without delay.", "urgent")

    def test_latex_content(self):
        self.assert_value("latex_role", r"For every integer \(n\), \(n+n=2n\).", "theorem")
        self.assert_value("latex_role", r"Choose \(n=8\); this particular calculation gives \(n+n=16\).", "example")
        self.assert_value("latex_subject", r"The polynomial coefficients determine the roots of \(p(x)\).", "algebra")
        self.assert_value("latex_subject", r"The triangle has an altitude perpendicular to its base and vertex angle \(a\).", "geometry")
        with self.assertRaises(ValueError):
            infer_label("latex_role", r"For every integer \(n\), is \(n^2\) even?")
        for feature, text in (
            ("latex_role", r"For every integer \(n\), \(n+0=n\). % audit marker"),
            ("latex_subject", r"The polynomial has coefficients and roots \(r\). % audit marker"),
        ):
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                infer_label(feature, text)

    def test_python_ast(self):
        self.assert_value("python_error", 'def f():\n    message = "return"\n    raise ValueError(message)', "raise")
        self.assert_value("python_error", 'def f():\n    # raise RuntimeError()\n    return "raise"', "return")
        with self.assertRaises(ValueError):
            infer_label("python_error", 'def f():\n    raise ValueError()\n    return 2')
        for source in (
            'def f():\n    return 1\n    # audit marker',
            'def f():\n    return 1  # audit marker',
            'def f():\n    return 1 / 0',
            'def f():\n    missing = 1 / 0\n    return 1',
            'def f():\n    return unknown',
            'def f():\n    return external_function()',
            'def f():\n    return [1][5]',
            'def f():\n    x = [][1]\n    return 1',
            'def f():\n    while True:\n        pass\n    return 1',
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                infer_label("python_error", source)
        self.assert_value("python_error", 'def f():\n    message = "finished"\n    return message', "return")

    def test_supported_finite_python_grammar(self):
        # Invented programs exercise supported constructs, not authored items.
        self.assert_value("python_error", 'def f(records):\n    labels = [str(part).strip() for part in records]\n    text = " / ".join(labels)\n    return text', "return")
        self.assert_value("python_error", 'def f(records):\n    count = len(records)\n    half = count // 2\n    a, b = records[:half], records[half:]\n    label = f"{a}: {b}"\n    return label', "return")
        self.assert_value("python_error", 'def f(records):\n    counts = {}\n    for part in records:\n        label = str(part)\n        counts[label] = counts.get(label, 0) + 1\n    return counts', "return")
        self.assert_value("python_error", 'def f(records):\n    indexed = list(enumerate(records))\n    lookup = {index: part for index, part in enumerate(records)}\n    positions = [index for index, part in enumerate(records) if part is not None]\n    pairs = list(zip(records, records[1:]))\n    return positions', "return")
        self.assert_value("python_error", 'def f(records):\n    lengths = [len(str(part)) for part in records]\n    largest = max(lengths, default=0)\n    distinct = set(str(part) for part in records)\n    ordered = sorted(distinct)\n    reverse = list(reversed(records))\n    total = sum(lengths)\n    message = f"{largest} {total}"\n    raise RuntimeError(message)', "raise")

    def test_json_actual_field(self):
        self.assert_value("json_status", '{"note":"rejected","inner":{"decision":"approved"', "approved")
        self.assert_value("json_status", '{"decision":"approved","next":{"decision":"rejected"', "rejected")
        with self.assertRaises(ValueError):
            infer_label("json_status", '{"decision":"approved","note":"rejected"')

    def test_table_current_cell(self):
        self.assert_value("table_status", '| Item | Decision |\n| --- | --- |\n| old | rejected |\n| new | approved', "approved")
        self.assert_value("table_status", '| Decision | Item |\n| --- | --- |\n| rejected', "rejected")
        with self.assertRaises(ValueError):
            infer_label("table_status", '| Decision | Note |\n| --- | --- |\n| approved | rejected')
        with self.assertRaises(ValueError):
            infer_label("table_status", '| Decision |\n| --- |\n\n| approved')

    def test_exact_read_endpoint(self):
        for feature, prefix in (
            ("json_status", '{"decision":"approved"'),
            ("table_status", '| Decision |\n| --- |\n| approved'),
            ("python_error", 'def f():\n    return 1'),
        ):
            for suffix in (" ", "\n", "\t"):
                with self.subTest(feature=feature, suffix=repr(suffix)), self.assertRaises(ValueError):
                    infer_label(feature, prefix + suffix)


if __name__ == "__main__":
    unittest.main()
