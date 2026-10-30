import importlib.util,sys,unittest
from pathlib import Path
import numpy as np
import torch
# Load original helpers first to avoid same-name recursive import.
p=Path(__file__).resolve().parents[1]/'e80/jlens/forecast.py'
spec=importlib.util.spec_from_file_location('forecast',p);old=importlib.util.module_from_spec(spec);sys.modules['forecast']=old;spec.loader.exec_module(old)
spec=importlib.util.spec_from_file_location('corrected',Path(__file__).with_name('forecast.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_direct_cosine(self):
  torch.manual_seed(197);j=torch.randn(5,5);w=torch.randn(21,5);h=torch.randn(3,5)
  actual=m.cosine(h,j,w,m.denominators(j,w));atoms=w@j
  expected=torch.stack([torch.stack([torch.dot(x,a)/a.norm() for a in atoms]) for x in h])
  torch.testing.assert_close(actual,expected,atol=2e-6,rtol=2e-6)
 def test_zero(self):
  d=m.denominators(torch.zeros(2,2),torch.ones(12,2));self.assertTrue(torch.all(d==1e-9))
 def test_rank(self):
  x=np.arange(20,dtype=np.float32);r=old.summarise_logits(x,[0,12]);self.assertTrue(r['visible_top10']);self.assertEqual(r['best_target_rank1'],8)
 def test_tie_membership(self):
  r=old.summarise_logits(np.ones(20),[0],np.arange(10,20));self.assertFalse(r['visible_top10']);self.assertEqual(r['best_target_rank0'],0)
if __name__=='__main__':unittest.main()
