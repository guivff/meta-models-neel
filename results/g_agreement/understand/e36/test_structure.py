"""Synthetic checker tests and optional content-free token-length audit.

Synthetic fixtures are invented independently of author templates. Running the
unit tests never labels the generated bank. --lengths only compares token counts.
"""
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('e36_structure_checker', HERE / 'check_structure.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
infer_label = checker.infer_label


class SyntheticStructureChecks(unittest.TestCase):
    def check_value(self, feature, text, expected):
        answer = infer_label(feature, text)
        self.assertEqual(answer['value'], expected)
        self.assertIsInstance(answer['evidence'], dict)
        self.assertTrue(answer['evidence'])

    def test_parentheses(self):
        self.check_value('prose_paren', 'A visitor (carrying a map moved toward the gate', 'inside')
        self.check_value('prose_paren', 'A visitor (carrying a map) moved toward the gate', 'outside')
        self.check_value('prose_paren', 'A visitor (with a map (already folded) moved forward', 'inside')
        self.check_value('prose_paren', 'The bell rang. A visitor (with a map) moved forward', 'outside')

    def test_quotations(self):
        self.check_value('prose_quote', 'We read "a path through the hills on the map', 'inside')
        self.check_value('prose_quote', 'We read "a path through the hills" on the map', 'outside')
        self.check_value('prose_quote', 'We read “a path through the hills on the map', 'inside')
        self.check_value('prose_quote', 'We read “a path through the hills” on the map', 'outside')

    def test_sentences(self):
        self.check_value('prose_sentence', 'Clouds crossed the valley', 'early')
        self.check_value('prose_sentence', 'The train stopped. Clouds crossed the valley', 'early')
        self.check_value('prose_sentence', 'Rain fell. Wind rose. Gates shut. Lamps glowed. Buses stopped. Clouds crossed the valley', 'late')
        self.check_value('prose_sentence', 'Rain fell; Wind rose; Gates shut; Lamps glowed; Buses stopped; Clouds crossed the valley', 'early')

    def test_python_strings(self):
        self.check_value('python_string', 'path = "station/platform', 'inside')
        self.check_value('python_string', 'path = "station" + platform_name', 'outside')
        self.check_value('python_string', "path = r'gate\\'s location", 'inside')
        self.check_value('python_string', 'path = """station\nplatform', 'inside')
        self.check_value('python_string', "path = '''station\nplatform''' + route_name", 'outside')

    def test_python_comments(self):
        self.check_value('python_comment', 'cost = base # plus the delivery fee', 'comment')
        self.check_value('python_comment', 'cost = base + delivery_fee', 'code')
        self.check_value('python_comment', 'mark = "#"\ncost = base + delivery_fee', 'code')
        self.check_value('python_comment', '# preceding note\ncost = base + delivery_fee', 'code')

    def test_python_depth(self):
        self.check_value('python_depth', 'x = [alpha + beta', 'shallow')
        self.check_value('python_depth', 'x = [{"route": (alpha + beta', 'deep')
        self.check_value('python_depth', 'x = ["ignored ([", beta', 'shallow')
        self.check_value('python_depth', 'x = [alpha, # ignored ]\n beta', 'shallow')

    def test_python_arguments(self):
        self.check_value('python_argument', 'submit(alpha + beta', 'first')
        self.check_value('python_argument', 'submit(alpha, beta, gamma, delta, epsilon', 'later')
        self.check_value('python_argument', 'submit([alpha, beta, gamma, delta, epsilon', 'first')
        self.check_value('python_argument', 'submit(pair(alpha, beta), gamma, delta, epsilon, zeta', 'later')
        self.check_value('python_argument', 'submit(count=(alpha, beta, gamma', 'first')

    def test_python_indentation(self):
        self.check_value('python_indent', 'def route():\n    result = current_stop', 'shallow')
        self.check_value('python_indent', 'def route():\n    if active:\n        for stop in stops:\n            result = current_stop', 'deep')
        self.check_value('python_indent', 'def route():\n    if active:\n        for stop in stops:\n            result = current_stop\n    return result', 'shallow')

    def test_json_types(self):
        self.check_value('json_type', '{"route": "station', 'string')
        self.check_value('json_type', '{"route": -12.75e2', 'number')
        self.check_value('json_type', '{"stops": [true, null, {"route": "station', 'string')
        self.check_value('json_type', '{"a": {"old": 2}, "route": 900', 'number')
        self.check_value('json_type', r'{"route": "escaped\nvalue\u0041', 'string')

    def test_latex_environments(self):
        self.check_value('latex_environment', '\\begin{equation}\nx + y', 'equation')
        self.check_value('latex_environment', '\\begin{quote}\nThe route follows the river', 'quote')
        self.check_value('latex_environment', '\\begin{center}\\begin{quote}Old text\\end{quote}\\begin{equation}x + y', 'equation')
        self.check_value('latex_environment', '% \\begin{equation}\n\\begin% explanation\n{quote}\nA path follows the river', 'quote')

    def test_latex_sections(self):
        self.check_value('latex_section', '\\section{Route}\\subsection{Map}\nThe path follows the river', 'early')
        self.check_value('latex_section', '\\section[Map]{Route}\\section{Stops}\nThe path follows the river', 'early')
        self.check_value('latex_section', ''.join('\\section{Route}' for _ in range(6)) + '\nThe path follows the river', 'late')
        self.check_value('latex_section', '% \\section{Ignore}\n\\section{Route}\nThe path follows the river', 'early')

    def test_list_depth(self):
        self.check_value('list_depth', '- Choose a route\n  - Read the map\n- Find the station', 'shallow')
        self.check_value('list_depth', '- Choose a route\n  - Read the map\n    - Find the station', 'deep')
        self.check_value('list_depth', '* [ ] Choose a route\n  * [ ] Read the map\n    * [ ] Find the station', 'deep')

    def test_list_index(self):
        self.check_value('list_index', 'Read the map before leaving\n\n+ Find the station', 'first')
        self.check_value('list_index', '\n'.join(['+ Read the map'] * 5 + ['+ Find the station']), 'later')

    def test_table_roles(self):
        self.check_value('table_role', '| Route | Final destination', 'header')
        self.check_value('table_role', '| Route | Destination |\n| --- | ---: |\n| North | Final destination', 'data')
        self.check_value('table_role', '| Route | Destination |\n| --- | --- |\n| North | Valley |\n\n| New route | Final destination', 'header')
        self.check_value('table_role', 'Route | Destination\n:--- | ---:\nNorth | Final destination', 'data')

    def test_table_columns(self):
        head = '| Route | Time | Cost | Stop | Destination |\n| --- | --- | --- | --- | --- |\n'
        self.check_value('table_column', head + '| North road', 'first')
        self.check_value('table_column', head + '| North | Noon | Three | Town | Final destination', 'later')
        self.check_value('table_column', head + '| `north|south` road', 'first')
        self.check_value('table_column', head + '| North \\| south road', 'first')
        self.check_value('table_column', head + '| North \\|', 'first')

    def test_table_rows(self):
        head = '| Route | Destination |\n| --- | --- |\n'
        self.check_value('table_row', head + '| North | Valley', 'early')
        self.check_value('table_row', head + '| North | Valley |\n| South | Coast', 'early')
        self.check_value('table_row', head + '| North | Valley |\n' * 5 + '| South | Coast', 'late')

    def test_ambiguous_cases_raise(self):
        cases = (
            ('prose_paren', 'A visitor (carrying a map)'),
            ('prose_paren', 'A visitor arrived at the gate'),
            ('prose_paren', 'A visitor ) arrived at the gate'),
            ('prose_quote', 'We read "a path through the hills"'),
            ('prose_quote', 'We read “a path through the hills”'),
            ('prose_quote', 'A visitor arrived at the gate'),
            ('prose_quote', 'We read ”a path through the hills'),
            ('prose_sentence', 'Rain fell. Wind rose. Clouds crossed the valley'),
            ('prose_sentence', 'Dr. Stone crossed the valley'),
            ('python_string', 'value = alpha + beta'),
            ('python_string', 'value = "alpha"'),
            ('python_string', 'value = f"route {station'),
            ('python_comment', 'value = "unclosed string'),
            ('python_depth', 'value = [[alpha + beta'),
            ('python_depth', 'value = [alpha] + beta'),
            ('python_argument', 'submit('),
            ('python_argument', 'def submit('),
            ('python_argument', 'class Route('),
            ('python_argument', 'submit(lambda a,b,c,d,e:e'),
            ('python_argument', 'submit(alpha, beta'),
            ('python_argument', 'submit(alpha, beta,'),
            ('python_indent', 'def route():\n    if active:\n        result = current_stop'),
            ('json_type', r'{"route": "bad\q'),
            ('json_type', r'{"route": "bad\uXYZ1'),
            ('json_type', '{"unclosed key'),
            ('json_type', '{"route": true'),
            ('json_type', '{"route": [123'),
            ('latex_environment', '\\begin{center}The route follows the river'),
            ('latex_environment', '\\begin{quote}'),
            ('latex_environment', '\\begin{quote}Body text % comment read token'),
            ('latex_section', '\\section{Route}Body text % comment read token'),
            ('latex_section', '\\section*{Route}\nThe path follows the river'),
            ('list_depth', '- Choose a route\n  - Read the map'),
            ('list_index', '- Choose a route\n- Read the map'),
            ('list_index', '- Older item\n\n- Find the station'),
            ('table_role', 'Ordinary text about the station'),
            ('table_role', '| Route | Stop |'),
            ('table_role', '| Route | Stop |\n| --- | --- |\n| North | Town |'),
            ('table_column', '| Route | Stop |\n| --- | --- |\n| North |'),
            ('table_column', '| Route | Stop |\n| --- | --- |\n| North | Town'),
            ('table_row', '| Route | Stop |\n| --- | --- |\n| North | Town |\n| South | Coast |\n| West | Hill'),
        )
        for feature, text in cases:
            with self.subTest(feature=feature):
                with self.assertRaises(ValueError):
                    infer_label(feature, text)


def length_audit():
    """Allowed pre-freeze audit: lengths and uniqueness only, never labels."""
    from tokenizers import Tokenizer
    spec = importlib.util.spec_from_file_location('e36_structure_author', HERE / 'author_structure.py')
    author = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(author)
    tokenizer = Tokenizer.from_file('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json')
    summaries = {}
    failures = []
    for feature in author.FEATURES:
        maximum = 0
        hashes = set()
        for template in range(12):
            for filler in range(7):
                texts = [author.render(feature, template, filler, value) for value in (0, 1)]
                lengths = [len(tokenizer.encode(text, add_special_tokens=False).ids) for text in texts]
                ratio = max(lengths) / min(lengths)
                maximum = max(maximum, ratio)
                if ratio > 1.10:
                    failures.append((feature, template, filler, lengths))
                for text in texts:
                    digest = hashlib.sha256(text.encode()).hexdigest()
                    if digest in hashes:
                        failures.append((feature, template, filler, 'duplicate'))
                    hashes.add(digest)
        summaries[feature] = {'pairs': 84, 'unique_prefixes': len(hashes), 'max_token_ratio': round(maximum, 7)}
    print({'length_audit': summaries, 'failure_coordinates': failures})
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    if '--lengths' in sys.argv:
        length_audit()
    else:
        unittest.main()
