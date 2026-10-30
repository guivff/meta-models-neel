import tempfile
import unittest
from pathlib import Path
import numpy as np
import analyze as E
import freeze as F

class TestE41(unittest.TestCase):
    def test_exact_recipe_and_dev_only_vocabulary(self):
        text = ['apple aa', 'apple ab', 'berry ba', 'berry bb']
        m, p, _ = F.P.fit_row(text, [1, 1, 0, 0], ['ΩΩΩΩ'])
        self.assertFalse(any('Ω' in k for k in m['vocabulary']))
        np.testing.assert_allclose(F.P.restored_probabilities(m, text), p, atol=1e-12, rtol=0)
        self.assertEqual(m['classifier_params']['random_state'], 20261023)
        self.assertEqual(m['vectorizer_params']['ngram_range'], [1, 4])

    def test_ties_and_read_token(self):
        self.assertEqual(F.P.assign_strata([.5, .5], 0), ['uninformative'] * 2)
        self.assertEqual(F.P.suffix_ids({'ids': [1, 2, 3, 4, 5], 'meta': {'read_position': 4}}, 'include_read'), [2, 3, 4, 5])

    def row(self, n):
        return [{'stratum': s, 'label': j % 2, 'score': j % 2} for s in ['informative', 'uninformative'] for j in range(n)]

    def test_ten_item_boundary_and_bootstrap(self):
        nine = E.summarize('synthetic', self.row(9), np.random.default_rng(20261025))
        ten = E.summarize('synthetic', self.row(10), np.random.default_rng(20261025))
        self.assertFalse(nine['evaluable'])
        self.assertTrue(ten['evaluable'])
        self.assertTrue(ten['remote_state'])
        self.assertEqual(ten['strata']['informative']['attempted_bootstrap_draws'], 2000)
        self.assertEqual(ten['strata']['informative']['auroc'], 1)
        self.assertEqual(ten, E.summarize('synthetic', self.row(10), np.random.default_rng(20261025)))

    def test_undefined_and_empty(self):
        for records in [[], [{'stratum': 'informative', 'label': 1, 'score': 1}] * 20]:
            self.assertFalse(E.summarize('synthetic', records, np.random.default_rng(1))['evaluable'])

    def test_majority_none_and_minimum(self):
        remote = {'evaluable': True, 'remote_state': True, 'local_cue': False}
        neither = {'evaluable': True, 'remote_state': False, 'local_cue': False}
        local = {'evaluable': True, 'remote_state': False, 'local_cue': True}
        self.assertEqual(E.decision([remote])['status'], 'NOT_EVALUABLE')
        self.assertEqual(E.decision([remote, neither])['status'], 'NOT_EVALUABLE')
        self.assertEqual(E.decision([remote, remote, neither])['status'], 'R')
        self.assertEqual(E.decision([remote, remote, local])['status'], 'NOT_R')

    def test_clarified_boundaries(self):
        def judge(ni=9, nu=10, ai=.8, au=.70, lower=.50001):
            return E.judge_strata({'informative': {'n': ni, 'auroc': ai, 'ci95': [.1, .9]},
                                  'uninformative': {'n': nu, 'auroc': au, 'ci95': [lower, .95]}})
        self.assertTrue(judge()['remote_state'])
        self.assertEqual(judge()['criterion'], 'uninformative_only')
        self.assertFalse(judge(lower=.50)['remote_state'])
        self.assertFalse(judge(au=.69999)['remote_state'])
        self.assertTrue(judge(au=.60)['local_cue'])
        self.assertFalse(judge(au=.60001)['local_cue'])
        self.assertFalse(judge(nu=9)['judged'])
        self.assertTrue(judge(ni=0)['judged'])
        self.assertTrue(judge(ni=10, lower=.1)['remote_state'])
        self.assertEqual(judge(ni=10)['criterion'], 'both_strata')
        self.assertFalse(judge(ni=10, ai=None)['judged'])
        self.assertFalse(judge(au=None)['judged'])
        self.assertTrue(judge(ni=10, ai=.75, au=.60)['local_cue'])
        self.assertFalse(judge(ni=10, ai=.74999, au=.60)['local_cue'])

    def test_fallback_bootstrap_integration(self):
        records = [r for r in self.row(12) if r['stratum'] == 'uninformative']
        result = E.summarize('synthetic', records, np.random.default_rng(20261025))
        self.assertTrue(result['remote_state'])
        self.assertEqual(result['criterion'], 'uninformative_only')
        self.assertEqual(result['strata']['uninformative']['attempted_bootstrap_draws'], 2000)
        self.assertEqual(result['strata']['uninformative']['ci95'], [1., 1.])
        remote = result
        neither = dict(result, remote_state=False)
        self.assertEqual(E.decision([remote, remote])['status'], 'NOT_EVALUABLE')
        self.assertEqual(E.decision([remote, remote, neither])['status'], 'R')
        self.assertEqual(E.decision([remote, remote, neither, neither])['status'], 'NOT_R')

    def test_exclusive_once_guard(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'analysis'
            F.A.exclusive_start(path, {})
            with self.assertRaises(ValueError):
                F.A.exclusive_start(path, {})

    def test_real_seal_integrity_without_test_access(self):
        F.verify_inputs()
        F.A.verify_seal(E.FROZEN / 'CLASSIFIER_SEAL.json', E.CLASSIFIER_SEAL)
        self.assertEqual(set(F.P.read(E.FROZEN / 'cache/models.json')), set(F.P.ROWS))

if __name__ == '__main__':
    unittest.main()
