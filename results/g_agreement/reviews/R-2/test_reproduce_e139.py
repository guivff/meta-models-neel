import importlib.util
from pathlib import Path
import unittest
import numpy as np
s=importlib.util.spec_from_file_location('e139_review',Path(__file__).with_name('reproduce_e139.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class GateTests(unittest.TestCase):
    def test_delta_u_is_fraction_not_reward(self):
        base=np.zeros((20,2));dev=[[0,0],[0,0],[2,0],[2,0]]
        out=m.delta_u(dev,[0,0,1,1],base,{'true':base+[1,100],'false':base+[-1,0],'neutral':base+[0,100]},draws=40,seed=20261030)
        self.assertEqual(out['true'],dict(mean=.5,CI95=[.5,.5]))
        self.assertEqual(out['neutral']['mean'],0);self.assertEqual(out['false']['mean'],-.5)
        with self.assertRaises(ValueError):m.delta_u([[1,0],[1,0]],[0,1],base,{k:base for k in ('true','false','neutral')},draws=40,seed=20261030)
    def test_score_pair_order_is_frozen(self):
        rows=[dict(id=str(i),true=float(i),neutral=0.)for i in range(20)]
        out=m.paired_gain(rows,draws=30,seed=20261030)
        from common.stats import bootstrap_ci
        expected=bootstrap_ci(np.arange(20,dtype=float),n_boot=30,seed=20261030)
        self.assertEqual([out['estimate'],*out['CI95']],list(expected))
    def test_one_control_is_sufficient(self):
        r=m.instrument_gate({'language':[-.1,.1],'fact_recall':[.01,.2]},reward_label='proxy reward')
        self.assertEqual(r['status'],'PASS');self.assertTrue(r['structural_reading_allowed'])
        self.assertEqual(r['reward_label'],'proxy reward')
    def test_zero_lower_bound_does_not_pass(self):
        r=m.instrument_gate({'language':[0,.1],'fact_recall':[-.1,.1]},reward_label='training reward')
        self.assertEqual(r['status'],'NOT EVALUABLE (instrument)');self.assertFalse(r['structural_reading_allowed'])
    def test_unknown_not_a_negative(self):
        self.assertEqual(m.instrument_gate({'language':None,'fact_recall':[-1,0]},reward_label='proxy reward')['status'],'PENDING: incomplete controls')
        self.assertEqual(m.instrument_gate({'language':None,'fact_recall':[.01,.1]},reward_label='proxy reward')['status'],'PASS')
    def test_pairs_and_source_census(self):
        rows=[dict(id=str(i),true=2,neutral=1) for i in range(20)]
        r=m.paired_gain(rows,draws=50,seed=1)
        self.assertEqual(r['CI95'],[1,1]);self.assertEqual(r,m.paired_gain(rows[::-1],draws=50,seed=1))
        with self.assertRaises(ValueError):m.paired_gain(rows[:-1],draws=50,seed=1)
        rows[-1]['id']=rows[0]['id']
        with self.assertRaises(ValueError):m.paired_gain(rows,draws=50,seed=1)
    def test_missing_scores_are_not_zero(self):
        r=m.paired_gain([dict(id=str(i),true=None,neutral=1)for i in range(20)],draws=50,seed=1)
        self.assertIsNone(r['estimate']);self.assertEqual(r['missing'],20)
    def test_explicit_reward_label_and_controls(self):
        with self.assertRaises(ValueError):m.instrument_gate({'language':[1,2]},reward_label='training reward')
        with self.assertRaises(ValueError):m.instrument_gate({'language':[1,2],'fact_recall':[1,2]},reward_label='FVE')

if __name__=='__main__':unittest.main()
