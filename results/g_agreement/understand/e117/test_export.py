import unittest
import numpy as np
from export import select,direction
class Export(unittest.TestCase):
 def test_tie_uses_lowest_layer(self):
  m={f'r__L{l:02d}__first_generated_token':dict(selected_C=.1,dev_CV=[dict(C=.1,mean_AUROC=1.)]) for l in range(48,61)}
  self.assertEqual(select(m,'r')[0],48)
 def test_raw_covector(self):
  d=direction([[2.,4.]],[2.,1.]);np.testing.assert_allclose(d,np.array([1,4])/np.sqrt(17));self.assertAlmostEqual(np.linalg.norm(d),1)
if __name__=='__main__':unittest.main()
