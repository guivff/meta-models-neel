"""Synthetic checks only; no E58b data or registered analysis invocation."""
import unittest
import numpy as np
from posthoc_ci_20261027 import bootstrap, item_damage, DRAWS, SEED
from common58 import ARMS


class PostHocTests(unittest.TestCase):
    def test_paired_contrast_and_percentile_reference(self):
        x = np.linspace(-3, 4, 84)
        values = np.column_stack([x, x - 2, np.ones(84) * 5, np.ones(84) * 2])
        actual = bootstrap(values)
        rng = np.random.default_rng(SEED)
        reference = [np.mean(x[rng.integers(0, 84, 84)]) for _ in range(DRAWS)]
        np.testing.assert_allclose(actual['J_damage']['ci95'], np.quantile(reference, [.025, .975]), rtol=0, atol=1e-14)
        self.assertEqual(actual['J_minus_random_damage']['ci95'], [2., 2.])
        self.assertEqual(actual['PCA_damage']['ci95'], [5., 5.])
        self.assertEqual(actual, bootstrap(values))

    def test_item_pair_orientation_and_five_seed_mean(self):
        items = [{'id': str(i), 'label': i % 2, 'pairs': [{}, {}]} for i in range(84)]
        rows = [{'key': 'row', 'test': items}]
        records = []
        for item in items:
            sign = 1 if item['label'] else -1
            for pair in range(2):
                scores = {'none': 10., 'J': 7., 'PCA': 6., **{'random' + str(i): 10. - i for i in range(5)}}
                records += [{'row': 'row', 'id': item['id'], 'pair_index': pair, 'arm': arm,
                             'logodds_A_minus_B': sign * (score + pair)} for arm, score in scores.items()]
        values = item_damage(rows, records)[0]
        np.testing.assert_array_equal(values, np.tile([3., 2., 4., 1.], (84, 1)))
        with self.assertRaises(ValueError): item_damage(rows, records[:-1])
        with self.assertRaises(ValueError): item_damage(rows, records + records[:1])

    def test_exact_population_and_finite_values(self):
        for values in (np.zeros((83, 4)), np.full((84, 4), np.nan)):
            with self.assertRaises(ValueError): bootstrap(values)


if __name__ == '__main__':
    unittest.main()
