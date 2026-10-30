import sys
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from contract56 import read,ROOT
sys.path.insert(0,str(ROOT/"external/mats-nla-workspace/src"))

def test_all_test_items_no_bank_labels_in_inputs():
 for e in ('e56','e57'):
  b=read(HERE.parents[1]/e/'job/INPUT_BINDING.json');p=Path(b['inputs']);items=read(p/'items.json');plan=read(p/('SAMPLING.json' if e=='e56' else 'RUN_PLAN.json'))
  assert not (p/'dev_labels.json').exists()
  assert all('label' not in x and 'value' not in x for x in items)
  for row,ids in plan['native_ids'].items():assert set(ids)=={x['id'] for x in items if x['feature']==row and x['split']=='test'}

def test_cpu_class_means_and_dev_only_fit(monkeypatch):
 import torch,mats.probes
 from cpu_capture import compute
 h=np.array([[0.,2.],[4.,6.],[10.,12.],[14.,16.]],dtype=np.float32)
 items=[dict(id=str(i),feature='x',split='dev' if i<2 else 'test',label=i%2) for i in range(4)]
 def fit(x,y):
  assert torch.equal(x,torch.from_numpy(h[:2])) and y.tolist()==[0,1]
  return type('Probe',(),{'decision':lambda self,x:torch.zeros(len(x))})()
 monkeypatch.setattr(mats.probes,'fit_logreg',fit)
 scores,means=compute(items,h)
 assert [x['id'] for x in scores]==['2','3']
 assert np.array_equal(means['x__dev__A'],h[1]) and np.array_equal(means['x__test__B'],h[2])

def test_measured_allocation_requires_fit_inside_twice_ceiling():
 from resize_from_profile import allocation
 assert allocation(100,50,300)==510
 with pytest.raises(ValueError,match='NO_FIT'):allocation(1000,100,300)
 from stats_native import rate
 assert rate([[1]]*84)['readouts']==84
 with pytest.raises(ValueError):rate([[1]*8]*84)
