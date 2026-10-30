import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import overnight149 as O
E = O.module('e29_compare_test', O.BASE / 'e29/compare149.py')

class OvernightTests(unittest.TestCase):
    def test_paired_ci(self):
        y = [0, 1]*42
        x = np.array(y, dtype=float)
        same = O.contrast(y, x, x, np.random.default_rng(20261025))
        self.assertEqual(same['difference'], 0)
        self.assertEqual(same['ci95'], [0., 0.])
        opposite = O.contrast(y, x, -x, np.random.default_rng(20261025))
        self.assertEqual(opposite['ci95'], [1., 1.])

    def test_h3_thresholds(self):
        names = ['table_row','table_column','python_argument','latex_section','python_comment','python_depth']
        c = {n:{'difference':.15,'ci95':[.0001,.4]} for n in names}
        self.assertEqual(O.h3_rule(c,names)['status'],'REPLICATED')
        for n in names[:3]:c[n]['ci95'][0]=0
        self.assertEqual(O.h3_rule(c,names)['status'],'NOT_REPLICATED')
        self.assertEqual(O.h3_rule(c,names[:3])['status'],'NOT_EVALUABLE')

    def test_e29_rules(self):
        def row(n,d=.7,ol=.5,lower=.01):
            return {'feature':n,'D':d,'Oracle':ol,'Oracle_CI':{'ci95':[.66,.9]},'D_minus_Oracle':{'difference':d-ol,'ci95':[lower,.5]}}
        rows = [row('a'),row('b'),row('c',ol=.6)]
        self.assertEqual(E.verdict(rows)['R2']['status'],'MET')
        rows[1]['D_minus_Oracle']['ci95'][0]=0
        self.assertEqual(E.verdict(rows)['R2']['status'],'NOT_MET')
        self.assertEqual(E.verdict(rows[:2])['R2']['required'],2)
        self.assertTrue(E.verdict([row('x',d=.9,ol=.75)])['R1']['registered_falsified'])
        self.assertFalse(E.verdict([row('x',d=.69,ol=.75)])['R1']['registered_falsified'])

    def test_failed_validation_is_once_only(self):
        with tempfile.TemporaryDirectory() as d, patch.object(O,'BASE',Path(d)):
            (Path(d)/'e29').mkdir()
            with self.assertRaises(FileNotFoundError):O.begin('e29')
            with self.assertRaises(FileExistsError):O.begin('e29')

    def test_native_probe_cpu_smoke(self):
        from types import SimpleNamespace
        import torch
        import channel_contract as C
        from worker import frozen_function
        sys.path.insert(0, str(O.ROOT / 'external/mats-nla-workspace/src'))
        torch.set_num_threads(2)
        fn = frozen_function(O.ROOT, C.PROBE_RECIPE['source'], C.PROBE_RECIPE['function'],
                             C.PROBE_RECIPE['function_sha256'], {'np': np, 'P': SimpleNamespace(SEED=C.SEED)})
        y = np.tile([0, 1], 42)
        groups = np.repeat(np.arange(6), 14)
        x = np.random.default_rng(123).normal(size=(84, 4))
        x[:, 0] += 2*y
        scores, _, folds = fn(x, y, groups, np.arange(84), k=5)
        self.assertEqual(len(scores), 84)
        self.assertTrue(np.isfinite(scores).all())
        self.assertEqual(len(folds), 5)
        self.assertTrue(all(not set(f['train_clusters']) & set(f['test_clusters']) for f in folds))

    def test_receipt_rejects_unverified(self):
        with tempfile.TemporaryDirectory() as d, patch.object(O,'BASE',Path(d)):
            p=Path(d)/'e29/cache/verified_pull_149';p.mkdir(parents=True)
            O.A.dump(p/'RECEIPT.json',{'verified':False})
            with self.assertRaises(ValueError):O.receipt('e29')

if __name__ == '__main__':unittest.main()
