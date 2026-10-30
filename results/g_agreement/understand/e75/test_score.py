"""Synthetic only: no capture, native readout, judgment, or real forecast loads."""
import copy
import unittest
from score import score


def fixture(n=60, model='synthetic-qwen', reader='oracle'):
    return [dict(model=model, reader=reader, bank='synthetic', row=str(i),
                 category=['content', 'bookkeeping', 'syntactic'][i % 3],
                 truth='REPORTED' if i % 2 else 'MISSED',
                 j_prediction='REPORTED' if i % 2 else 'MISSED',
                 j_label='IN-J' if i % 2 else 'DIFFUSE', j_fraction=.03,
                 j_null_median=.02, j_null_percentile975=.04) for i in range(n)]


class SyntheticTests(unittest.TestCase):
    def test_perfect_and_null_reporting(self):
        r = score(fixture())['results'][0]
        self.assertTrue(r['R_P1_met'])
        self.assertEqual(r['J_balanced_accuracy'], 1)
        self.assertEqual(r['constant_MISSED_balanced_accuracy'], .5)
        self.assertEqual(r['category_balanced_accuracy'], .5)
        self.assertEqual(r['J_minus_constant_percentile95'], [.5, .5])
        self.assertTrue(all(x['j_null_median'] == .02 and x['j_null_percentile975'] == .04 for x in r['rows']))

    def test_models_and_readers_never_inflate_sample_size(self):
        rows = fixture(30) + fixture(30, reader='nla') + fixture(30, model='synthetic-glm')
        out = score(rows)['results']
        self.assertEqual(len(out), 3)
        self.assertTrue(all(r['n'] == 30 and r['R_P1_met'] is None for r in out))

    def test_class_minimum_and_single_class(self):
        rows = fixture()
        for i, r in enumerate(rows):
            r['truth'] = 'REPORTED' if i < 14 else 'MISSED'
        self.assertFalse(score(rows)['results'][0]['pooled_sample_eligible'])
        for r in rows:
            r['truth'] = 'MISSED'
        out = score(rows)['results'][0]
        self.assertIsNone(out['J_balanced_accuracy'])
        self.assertIsNone(out['constant_REPORTED_balanced_accuracy'])

    def test_category_only_has_no_increment_or_within_signal(self):
        rows = fixture()
        for r in rows:
            r['j_prediction'] = 'REPORTED' if r['category'] == 'content' else 'MISSED'
            r['j_label'] = 'IN-J' if r['j_prediction'] == 'REPORTED' else 'OUT-J'
        out = score(rows)['results'][0]
        self.assertEqual(out['J_minus_category_balanced_accuracy'], 0)
        self.assertEqual(out['bootstrap']['percentile95']['J_minus_category_balanced_accuracy'], [0, 0])
        self.assertEqual(set(out['within_category']['permutation']['null_balanced_accuracy']), {.5})
        self.assertFalse(out['R_P1_met'])
        self.assertTrue(out['falsifier'])

    def test_one_stratum_is_descriptive(self):
        rows = fixture()
        for r in rows:
            r['category'] = 'content'
        out = score(rows)['results'][0]
        self.assertEqual(out['within_category']['status'], 'DESCRIPTIVE')
        self.assertIsNone(out['R_P1_met'])

    def test_serialization_order_is_irrelevant(self):
        self.assertEqual(score(fixture()), score(fixture()[::-1]))

    def test_refuse_missing_null_bad_forecast_and_duplicate(self):
        for field, value in [('j_null_median', None), ('j_null_median', float('nan')),
                             ('j_null_median', .1), ('j_prediction', 'REPORTED'), ('category', 'unknown')]:
            rows = copy.deepcopy(fixture())
            rows[0][field] = value
            with self.assertRaises(ValueError):
                score(rows)
        with self.assertRaises(ValueError):
            score(fixture() + fixture()[:1])


if __name__ == '__main__':
    unittest.main()
