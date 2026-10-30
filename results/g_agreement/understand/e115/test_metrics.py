import unittest
import numpy as np
from metrics import j_fraction,paired_summary
class Metrics(unittest.TestCase):
 def test_energy_and_fixed_center(self):
  np.testing.assert_allclose(j_fraction([[4,5],[1,6]],[1,2],[[1],[0]]),[.5,0])
 def test_fixed_direction_and_pairing(self):
  self.assertEqual(paired_summary([0,0],[1,1],draws=20)['auroc'],0)
  self.assertEqual(paired_summary([1,1],[0,0],draws=20)['auroc_ci'],[1,1])
 def test_zero_and_missing_reject(self):
  with self.assertRaises(ValueError):j_fraction([[1,2]],[1,2],[[1],[0]])
  with self.assertRaises(ValueError):paired_summary([1],[1,2],draws=2)
if __name__=='__main__':unittest.main()
