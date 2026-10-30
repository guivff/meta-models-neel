"""Permanent lexical regressions beyond the 50 hand-checkable cases/state."""
import unittest
from .states import extract_states


class StateEdgeTests(unittest.TestCase):
    def labels(self, text, marker="§", language="python"):
        offset = text.index(marker)
        return {k: v[0] for k, v in extract_states(text.replace(marker, ""), language, [offset]).items()}

    def test_fstrings_are_excluded_on_legacy_and_pep701_tokenizers(self):
        for text in (
            'a = f"hi {fn(1§2)}"; b = [1]\n',
            'a = f"hi {f\'hello {fn(1§2)}\'}"; b = [1]\n',
            'a = f"hi {fn(1§2)}',
        ):
            with self.subTest(text=text):
                got = self.labels(text)
                self.assertEqual([got[s] for s in ("W1", "W2", "W4")], [None] * 3)
        got = self.labels('a = f"hi {fn(12)}"; b = [§1]\n')
        self.assertEqual((got["W1"], got["W2"]), (1, 0))

    def test_python_truncated_quotes_are_not_outside(self):
        self.assertIsNone(self.labels('x="abc§')["W1"])
        self.assertEqual(self.labels('x="""abc§')["W1"], 0)
        self.assertEqual(self.labels('x=(1, §')["W2"], 0)

    def test_js_regex_after_control_does_not_add_brackets(self):
        for text in (
            'if (x) /[(]/§.test(x);',
            'while (f(x)) /[{}]/§.test(x);',
            'const value = /[({]/§;',
        ):
            with self.subTest(text=text):
                got = self.labels(text, language="javascript")
                self.assertEqual(got["W1"], 1)
                self.assertIsNone(got["W2"])
        self.assertEqual(self.labels('function f(x) { let y = 2§; }', language="javascript")["W4"], 1)

    def test_mismatched_brackets_invalidate_following_structure(self):
        for language in ("python", "javascript"):
            got = self.labels('value = [1); x§ = 2', language=language)
            self.assertIsNone(got["W2"])
            self.assertIsNone(got["W4"])

    def test_non_ascii_ast_byte_offsets(self):
        self.assertEqual(self.labels('é = str(1§2)\n')["W4"], 0)
        self.assertEqual(self.labels('é = str(12)§\n')["W4"], 1)
        self.assertEqual(self.labels('é = str(fn([1,2]), 3§)\n')["W4"], 0)

    def test_tabs_do_not_become_space_indentation(self):
        self.assertIsNone(self.labels('\t    value§ = 2\n')["W3"])
        self.assertIsNone(self.labels('    \tvalue§ = 2\n')["W3"])
        self.assertEqual(self.labels('            value§ = 2\n')["W3"], 1)

    def test_markdown_fences_and_indented_code_are_not_tables(self):
        for fence in ('```', '~~~'):
            text = fence + '\n| A | B | C |\n| --- | --- | --- |\n| aa§ | bb | cc |\n' + fence
            self.assertIsNone(self.labels(text, language="markdown")["W6"])
        text = '    | A | B | C |\n    | --- | --- | --- |\n    | aa§ | bb | cc |\n'
        self.assertIsNone(self.labels(text, language="markdown")["W6"])
        text = '| A | B | C |\n| --- | --- | --- |\n| a\\|b | `c|d` | e§ |\n'
        self.assertEqual(self.labels(text, language="markdown")["W6"], 1)
        malformed = '| A | B |\n| --- | --- | --- |\n| a§ | b | c |\n'
        self.assertIsNone(self.labels(malformed, language="markdown")["W6"])
        extra_cell = '| A | B |\n| --- | --- |\n| a | b | c§ |\n'
        self.assertIsNone(self.labels(extra_cell, language="markdown")["W6"])

    def test_offsets_reject_invalid_input(self):
        for bad in (0, -1, 4, True, 1.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                extract_states("abc", "prose", [bad])


if __name__ == "__main__":
    unittest.main()
