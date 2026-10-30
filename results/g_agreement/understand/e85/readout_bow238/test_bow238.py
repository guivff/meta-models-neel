"""Synthetic only; never access real native outputs or fit on TEST."""
import unittest
import numpy as np
from bow238 import fit_dev, score_test, reading, validate_rows


def rows(split, n=4):
    return [dict(id=f'{split}{q}{g}{a}', split=split, quartet=f'{split}{q}', genre=g, addressed=a,
                 text=('hedge ' if a else 'direct ') + ('benchmark ' if g else 'ordinary ') + f'shared{q}')
            for q in range(n) for g in (0, 1) for a in (0, 1)]


class Synthetic(unittest.TestCase):
    def test_positive_orientation_and_genre_control(self):
        v, models = fit_dev(rows('dev'))
        result = score_test(v, models, rows('test'), bootstraps=20)
        for target in ('addressed', 'genre'):
            self.assertEqual(result[target]['auroc'], 1.)
            self.assertEqual(result[target]['quartet_bootstrap_95ci'], [1., 1.])
        self.assertEqual(result['addressed']['registered_reading'], 'CARRIED_IN_WORDS')

    def test_test_only_words_never_enter_vocabulary_or_fit(self):
        v, models = fit_dev(rows('dev'))
        before = {k: m.coef_.copy() for k, m in models.items()}
        test = rows('test')
        for r in test:
            r['text'] += ' exclusivelytestword'
        score_test(v, models, test, bootstraps=4)
        self.assertNotIn('exclusivelytestword', v.vocabulary_)
        for k, m in models.items():
            np.testing.assert_array_equal(before[k], m.coef_)
        with self.assertRaises(ValueError):
            fit_dev(test)

    def test_thresholds(self):
        self.assertEqual(reading(.8), 'CARRIED_IN_WORDS')
        self.assertEqual(reading(.6), 'HIDDEN_STATE_TO_OUTPUT_BOTTLENECK')
        self.assertEqual(reading(.7), 'INTERMEDIATE')

    def test_full_balance_and_missing_dev_gate(self):
        data = rows('dev', 50) + rows('test', 100)
        validate_rows(data)
        for bad in (data[1:], data + [data[0]], rows('test', 100)):
            with self.assertRaises(ValueError):
                validate_rows(bad)

    def test_weights_direction_and_empty_text_not_dropped(self):
        dev = rows('dev'); dev[0]['text'] = ''
        v, models = fit_dev(dev)
        r = score_test(v, models, rows('test'), bootstraps=4)
        pos = r['addressed']['top_weights_dev_only']['positive_class']
        self.assertIn('hedge', [p['word'] for p in pos])
        self.assertTrue(all(p['weight'] > 0 for p in pos))


if __name__ == '__main__':
    unittest.main()
