import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).with_name('count_once.py')
SPEC = importlib.util.spec_from_file_location('e51_count', P)
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class CountTests(unittest.TestCase):
    def test_extraction_both_delimiters(self):
        text = 'ignored preface\\n- first\\n- second\n- third<|im_end|>'
        self.assertEqual(list(C.bullets(text)), ['first', 'second', 'third'])

    def test_empty_and_wrapped_bullets(self):
        self.assertEqual(list(C.bullets('- one\nwrapped text\n- <|im_end|>')), ['one\nwrapped text', ''])
        self.assertEqual(list(C.bullets('unmarked text')), [])

    def test_whole_word_case_phrase(self):
        p = C.compile_forms(['row', 'list item'])
        self.assertIsNone(p.search('brown rows itemized'))
        self.assertIsNotNone(p.search('list \n item'))
        self.assertIsNotNone(p.search('ROW'.casefold()))

    def test_repeat_overlap_and_sensitivity(self):
        lex = {'structure': {'row': ['row', 'rows'], 'nest': ['nested']},
               'content': {'error': ['error']}, 'passage_position': {'sentence': ['sentence']}}
        r = C.count(['rows row error', 'nested row sentence'], lex, ['row'])
        self.assertEqual(r['matching_bullets'], {'structure': 2, 'content': 1, 'passage_position': 1})
        self.assertEqual(r['structure_without_ambiguous']['matching_bullets'], 1)

    def test_r1_strict_and_inclusive_boundaries(self):
        lex = {'structure': {'nest': ['nested']}, 'content': {'topic': ['topic']}, 'passage_position': {}}
        r = C.count(['topic'] * 100 + ['plain'] * 9900, lex, [])
        self.assertTrue(r['R1']['met'])
        r = C.count(['nested'] + ['topic'] * 100 + ['plain'] * 9899, lex, [])
        self.assertFalse(r['R1']['met'])
        r = C.count(['topic'] * 99 + ['plain'] * 9901, lex, [])
        self.assertFalse(r['R1']['met'])

    def test_empty_population(self):
        with self.assertRaises(ValueError):
            C.count([], {}, [])


if __name__ == '__main__':
    unittest.main()
