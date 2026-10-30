"""Synthetic F1 leakage/resampling tests; no research outcomes loaded."""
from copy import deepcopy
import unittest
import numpy as np
from projects.g_agreement.r_bench import th2_f1_forecast as F


def synthetic_facts():
    facts = []
    for fold in range(5):
        halves = {}
        for half in ('calibration', 'endpoint'):
            base = np.r_[np.arange(64), np.zeros(40, int), np.full(40, 63, int)]
            codes = np.tile(base, 2).astype(int)
            bits = ((codes[:, None] >> np.arange(6)) & 1).astype(int)
            bits[:, 5] = 1-bits[:, 5]  # negative external loading
            codes = bits @ (1 << np.arange(6))
            y = np.repeat([0, 1], len(base))
            rng = np.random.default_rng(7120+fold+(0 if half == 'calibration' else 100))
            x = rng.normal(size=(len(y), 6))
            x[:, 0] += 2*bits[:, :4].mean(axis=1)
            x[:, 1] -= bits[:, 4]
            ids = np.array([f'f{fold}_{half}_{i}' for i in range(len(y))])
            halves[half] = dict(ids=ids, docs=ids.copy(), y=y, bits=bits, codes=codes,
                                x=[x.copy() for _ in range(5)])
        facts.append(dict(dataset=f'fact{fold}', corpus=f'corpus{fold}', fold=fold, halves=halves))
    return facts


class WeightedTailTest(unittest.TestCase):
    def test_fractional_boundaries_and_zero_weights(self):
        low, high = F.weighted_tails([0, 1, 2, 3, 999], [1, 2, 1, 6, 0], list('abcde'))
        np.testing.assert_array_equal(low, [1, 1, 0, 0, 0])
        np.testing.assert_array_equal(high, [0, 0, 0, 2, 0])
        self.assertEqual(low.sum(), 2)
        self.assertEqual(high.sum(), 2)
        self.assertFalse(np.any((low > 0) & (high > 0)))

    def test_stable_id_ties_and_row_permutation(self):
        scores, weights, ids = np.zeros(3), np.array([2., 1., 2.]), np.array(['z', 'a', 'm'])
        low, high = F.weighted_tails(scores, weights, ids)
        np.testing.assert_array_equal(low, [0, 1, 0])
        np.testing.assert_array_equal(high, [1, 0, 0])
        ix = np.array([2, 0, 1])
        other_low, other_high = F.weighted_tails(scores[ix], weights[ix], ids[ix])
        np.testing.assert_array_equal(other_low, low[ix])
        np.testing.assert_array_equal(other_high, high[ix])

    def test_invalid_input_fails(self):
        for scores, weights in [([0, np.nan], [1, 1]), ([0, 1], [1, -1])]:
            with self.assertRaises(ValueError):
                F.weighted_tails(scores, weights, ['a', 'b'])


class RidgeIsolationTest(unittest.TestCase):
    def setUp(self):
        self.x = np.array([[0., np.nan], [1., 4.], [2., 6.], [3., 8.]])
        self.y, self.w = np.array([3., 1., 0., 4.]), np.array([1., 3., 2., 4.])
        self.z = np.array([[.1, 4.], [.5, np.nan], [1.5, 8.]])

    def test_weighted_fit_matches_replicated_rows(self):
        pred, meta = F.fit_predict(self.x, self.y, self.w, self.z)
        copies = self.w.astype(int)
        other, other_meta = F.fit_predict(np.repeat(self.x, copies, axis=0),
            np.repeat(self.y, copies), np.ones(copies.sum()), self.z)
        np.testing.assert_allclose(pred, other, atol=1e-12)
        for key in ('coef', 'mean', 'scale', 'fill', 'intercept'):
            np.testing.assert_allclose(meta[key], other_meta[key], atol=1e-12)

    def test_endpoint_distribution_cannot_change_training_preprocessing(self):
        pred, meta = F.fit_predict(self.x, self.y, self.w, self.z)
        extreme = np.r_[self.z, [[1e12, -1e12], [np.nan, np.nan]]]
        extended, other_meta = F.fit_predict(self.x, self.y, self.w, extreme)
        np.testing.assert_array_equal(pred, extended[:len(pred)])
        for key in meta:
            np.testing.assert_array_equal(meta[key], other_meta[key])

    def test_absent_and_constant_columns_remain_inactive(self):
        x = np.c_[np.ones(4), np.full(4, np.nan)]
        pred, meta = F.fit_predict(x, self.y, self.w, [[99., 100.], [-99., np.nan]])
        np.testing.assert_array_equal(meta['active'], np.zeros(4, bool))
        np.testing.assert_allclose(pred, np.average(self.y, weights=self.w))


class OccurrenceBootstrapTest(unittest.TestCase):
    @staticmethod
    def fact(name, corpus):
        halves = {h:dict(ids=np.array([name+'_shared', name+'_unique']),
                        docs=np.array([h+'_shared', h+'_'+name]))
                  for h in ('calibration', 'endpoint')}
        return dict(dataset=name, corpus=corpus, fold=0, halves=halves)

    def test_corpus_copies_and_fact_copies_have_correct_shared_weights(self):
        facts = [self.fact('uniquea', 'A'), self.fact('uniqueb', 'A'), self.fact('uniquec', 'B')]
        class ScriptedRng:
            def __init__(self):
                self.draws = iter([np.array([0, 0]), np.array([0, 0]), np.array([0, 1])])
                self.docs = iter([np.array([2, 0]), np.array([0, 2]),
                                  np.array([0, 1, 2]), np.array([2, 1, 0])])
            def integers(self, high, size):
                result = next(self.draws)
                assert len(result) == size and result.max() < high
                return result
            def multinomial(self, n, p):
                result = next(self.docs)
                assert result.sum() == n and len(result) == len(p)
                return result
        got = F.occurrences(facts, ScriptedRng())
        self.assertEqual([x['occurrence'] for x in got], [0, 1, 2, 3])
        self.assertEqual([x['fact']['dataset'] for x in got], ['uniquea', 'uniquea', 'uniquea', 'uniqueb'])
        for h in ('calibration', 'endpoint'):
            np.testing.assert_array_equal(got[0]['weights'][h], got[1]['weights'][h])
            self.assertFalse(np.array_equal(got[0]['weights'][h], got[2]['weights'][h]))
            self.assertEqual(got[2]['weights'][h][0], got[3]['weights'][h][0])


class FullPipelineIsolationTest(unittest.TestCase):
    def test_endpoint_labels_and_errors_cannot_change_scores_or_ranks(self):
        facts = synthetic_facts()
        original = F.evaluate(F.occurrences(facts), return_predictions=True)
        changed = deepcopy(facts)
        for f in changed:
            e = f['halves']['endpoint']
            e['y'] = 1-e['y']
            e['bits'] = 1-e['bits']
            e['codes'] = e['bits'] @ (1 << np.arange(6))
        perturbed = F.evaluate(F.occurrences(changed), return_predictions=True)
        self.assertEqual(original['fits'], perturbed['fits'])
        self.assertEqual(original['coefs'], perturbed['coefs'])
        for old, new in zip(original['predictions'], perturbed['predictions']):
            np.testing.assert_array_equal(old['ids'], new['ids'])
            np.testing.assert_array_equal(old['predicted_difficulty'], new['predicted_difficulty'])
            a = F.weighted_tails(old['predicted_difficulty'], old['weights'], old['ids'])
            b = F.weighted_tails(new['predicted_difficulty'], new['weights'], new['ids'])
            for lohi_a, lohi_b in zip(a, b):
                np.testing.assert_array_equal(lohi_a, lohi_b)
            self.assertGreater(np.linalg.norm(old['posterior_difficulty']-new['posterior_difficulty']), 1.)
        self.assertGreater(abs(original['metrics']['gap']), .01)
        self.assertAlmostEqual(original['metrics']['gap'], -perturbed['metrics']['gap'], places=12)

    def test_heldout_calibration_outcomes_cannot_train_its_regressor(self):
        facts = synthetic_facts()
        original = F.evaluate(F.occurrences(facts), return_predictions=True)
        changed = deepcopy(facts)
        cal = changed[0]['halves']['calibration']
        cal['bits'][:, 1] = 1-cal['bits'][:, 1]
        cal['codes'] = cal['bits'] @ (1 << np.arange(6))
        perturbed = F.evaluate(F.occurrences(changed), return_predictions=True)
        old = next(p for p in original['predictions'] if p['fold'] == 0)
        new = next(p for p in perturbed['predictions'] if p['fold'] == 0)
        np.testing.assert_array_equal(old['predicted_difficulty'], new['predicted_difficulty'])
        for key in ('coefs', 'fits'):
            self.assertEqual([r for r in original[key] if r['fold'] == 0],
                             [r for r in perturbed[key] if r['fold'] == 0])

if __name__ == '__main__':
    unittest.main(verbosity=2)


from pathlib import Path as _GuardPath
from projects.g_agreement.tests import _write_guard as WG
_GUARD_ROOT = _GuardPath(__file__).resolve().parents[3]
_GUARD = WG.ModuleWriteGuard([_GUARD_ROOT/'results'/'g_agreement', _GUARD_ROOT/'cache'/'g_agreement'])
_write_guard = _GUARD.fixture()


def test_zz_outputs_untouched():
    _GUARD.assert_clean()
