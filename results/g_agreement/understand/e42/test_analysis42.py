import unittest
import numpy as np
from scipy.stats import spearmanr
from run42 import correlation,draws,tests

class AnalysisTests(unittest.TestCase):
 def test_spearman_ties_and_draws(self):
  x=[1,1,3,4,4];y=[5,2,3,1,1]
  self.assertAlmostEqual(correlation(x,y),spearmanr(x,y).statistic)
  ix=np.array([[0,1,2,3,4],[4,3,2,1,0]])
  np.testing.assert_allclose(draws(x,y,ix),correlation(x,y))
  self.assertIsNone(correlation([1,1],[2,3]))
 def test_same_D_persistence_difference(self):
  r=[{'key':str(i),'persistence':i*4,'Oracle':i/10,'D':i*4,'probe':1.,'NLA':i/10} for i in range(9)]
  t=tests(r)
  self.assertTrue(t['R1']['met']);self.assertFalse(t['R2']['met'])
  self.assertEqual(t['R2']['ci95'],[0.,0.]);self.assertIsNone(t['controls']['probe']['rho'])
  self.assertEqual(t['controls']['probe']['undefined_draws'],10000)
 def test_no_binary_group_not_evaluable(self):
  r=[{'key':str(i),'persistence':10+i,'Oracle':.5,'D':None,'probe':None,'NLA':None} for i in range(3)]
  self.assertEqual(tests(r)['R3']['status'],'NOT_EVALUABLE')
 def test_threshold_falsifier_inclusive(self):
  r=[{'key':'short','persistence':8,'Oracle':.80,'D':None,'probe':None,'NLA':None},
     {'key':'long','persistence':16,'Oracle':.65,'D':None,'probe':None,'NLA':None}]
  t=tests(r);self.assertEqual(t['falsifier']['short_sayable_rows'],['short'])
  self.assertEqual(t['R3']['high_hits'],1);self.assertEqual(t['R3']['low_hits'],0)
if __name__=='__main__':unittest.main()
