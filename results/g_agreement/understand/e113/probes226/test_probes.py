import unittest
import numpy as np
from probes import fit_dev,evaluate_test_once,validate_ids,decisions,ROWS,POSITIONS
class Tests(unittest.TestCase):
 def test_separation_and_no_test_selection(self):
  rng=np.random.default_rng(4);y=np.tile([0,1],42);x=rng.normal(size=(84,5));x[:,0]=10*y-5
  m,s=fit_dev(x,y);self.assertEqual(evaluate_test_once(m,x,y),1.);self.assertFalse(s['test_used_for_selection']);self.assertEqual(s['selected_C'],.01)
  z=m.named_steps['standardscaler'];np.testing.assert_allclose(z.mean_,x.mean(axis=0))
 def test_ids(self):
  validate_ids(list(range(84)),list(range(84,168)))
  with self.assertRaises(AssertionError):validate_ids(list(range(84)),list(range(84)))
 def test_gates_complete_and_boundaries(self):
  a={r:{'0':{p:(.65 if r in ROWS[:3] else .90) for p in POSITIONS}} for r in ROWS}
  self.assertTrue(decisions(a)['falsifier']);self.assertFalse(decisions(a)['R_IN1'])
  for r in ROWS[:2]:a[r]['0'][POSITIONS[0]]=.90
  self.assertTrue(decisions(a)['R_IN1']);del a[ROWS[-1]]
  with self.assertRaises(AssertionError):decisions(a)
if __name__=='__main__':unittest.main()
