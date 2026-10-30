import unittest,numpy as np
from .analyze_once import compute,whitener
from .selection import STATES
class Tests(unittest.TestCase):
 def fixture(self):
  rows=[];reb={}
  for state in STATES:
   for i in range(20):
    variants={k:f'{state}:{i}:{k}'for k in ('original','true','false','neutral')}
    for k,v in variants.items():reb[v]=np.array([1,1]if k=='true'else[0,0],dtype=np.float32)
    rows.append(dict(id=f'{state}:{i}',state=state,variants=variants))
  ds={s:dict(vectors=[[0,0],[2,0]],labels=[0,1])for s in STATES}
  return rows,np.ones((120,2),dtype=np.float32),reb,ds
 def test_whole_pipeline_primary_and_secondary_distinct(self):
  m,v=compute(*self.fixture());self.assertEqual(m['instrument_gate'],'PASS');self.assertEqual(len(v),120)
  for s in STATES:
   self.assertEqual(m['states'][s]['true_minus_neutral']['mean'],1.)
   self.assertEqual(m['delta_u'][s]['conditions']['true']['mean'],.5)
 def test_missing_pair_rejected(self):
  rows,h,rb,d=self.fixture();rb.pop(next(iter(rb)))
  with self.assertRaises(KeyError):compute(rows,h,rb,d)
 def test_zero_gap_secondary_not_reward_failure(self):
  rows,h,rb,d=self.fixture();d['evaluation_cue']['vectors']=[[1,0],[1,0]]
  m,_=compute(rows,h,rb,d);self.assertEqual(m['instrument_gate'],'PASS');self.assertEqual(m['delta_u']['evaluation_cue']['status'],'NOT EVALUABLE')
 def test_whitening_port_small_fixture(self):
  import tempfile
  from pathlib import Path
  import torch
  from safetensors.torch import save_file
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'mom.pt';save_file({'mu':torch.tensor([1.,2.]),'cov':torch.diag(torch.tensor([1.,3.]))},str(p))
   mu,w=whitener(p);np.testing.assert_array_equal(mu,[1,2]);np.testing.assert_allclose(w,np.diag(1/np.sqrt([1.2,3.2])),rtol=1e-6)
if __name__=='__main__':unittest.main()
