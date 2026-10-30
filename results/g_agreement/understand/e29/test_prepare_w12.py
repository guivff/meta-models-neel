"""Synthetic adapter checks: preserve A/B order, exact whitespace and read token."""
import copy
import unittest
import prepare_w12 as P


def fixture():
    rows = ['row'+str(i) for i in range(6)]
    templates = {r: {'values': ['z', 'a'], 'class': 'structure', 'olens': [[' A ', ' B '], ['\nC', '\nD']]} for r in rows}
    items = [{'id': f'{r}:{f}:{i}', 'feature': r, 'split': 'dev' if f < 6 else 'test',
              'value': 'z' if i % 2 == 0 else 'a', 'class': 'structure', 'cluster': str(f),
              'text': ' exact text\n', 'ids': [1, 2], 'meta': {'read_position': 1, 'token_length': 2}}
             for r in rows for f in range(12) for i in range(14)]
    return items, templates, rows


class AdapterTests(unittest.TestCase):
    def test_literal_prefix_candidates_and_A_order(self):
        data = fixture()
        staged, labels, candidates, classes = P.adapt(*data)
        self.assertEqual(len(staged), 504)
        self.assertEqual(staged[0]['id'], 'row0:6:0')
        self.assertEqual(staged[0]['text'], ' exact text\n')
        self.assertEqual([x['value'] for x in labels[:2]], ['A', 'B'])
        self.assertEqual(candidates['row0'], data[1]['row0']['olens'])
        self.assertEqual(set(classes.values()), {'structure'})

    def test_missing_item_and_split_leakage_rejected(self):
        items, templates, rows = fixture()
        with self.assertRaises(ValueError): P.adapt(items[:-1], templates, rows)
        items[84]['cluster'] = '0'
        with self.assertRaises(ValueError): P.adapt(items, templates, rows)

    def test_nonfinal_read_position_rejected(self):
        data = fixture()
        data[0][84]['meta']['read_position'] = 0
        with self.assertRaisesRegex(ValueError, 'read token'): P.adapt(*data)

    def test_wrong_class_or_pair_population_rejected(self):
        data = fixture()
        data[1]['row0']['olens'].pop()
        with self.assertRaises(ValueError): P.adapt(*data)
        data = fixture()
        data[0][84]['class'] = 'content'
        with self.assertRaises(ValueError): P.adapt(*data)


if __name__ == '__main__': unittest.main()
