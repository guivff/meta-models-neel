"""Synthetic source-selection and frozen-fitter serialization checks."""
import importlib.util,tempfile
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('p',Path(__file__).with_name('fit_probes.py'));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
def test_only_unhooked_dev_selection():
 ids=[str(i) for i in range(84)];inv={'fact_recall':dict(dev_ids=ids,dev_labels=[0,1]*42,test_ids=['test'])}
 a=[dict(base_id=i,row='fact_recall',split='dev',condition='unhooked') for i in ids]
 extra=[dict(base_id='test',row='fact_recall',split='test',condition='steered')]
 selected,y=p.select(a+extra,inv,'fact_recall');assert [x['base_id'] for x in selected]==ids
 for bad in [a[:-1],a+a[:1]]:
  try:p.select(bad,inv,'fact_recall')
  except AssertionError:pass
  else:raise AssertionError('missing/duplicate dev admitted')
def test_frozen_fit_and_serialization():
 y=np.array([0,1]*42);x=np.column_stack([2*y-1,np.zeros(84)])
 m=p.fit(x,y);assert m.coef_[0,0]>0 and m.classes_.tolist()==[0,1]
 with tempfile.TemporaryDirectory() as d:
  q=Path(d)/'probe.npz';p.dump_probe(q,m);z=np.load(q,allow_pickle=False)
  np.testing.assert_allclose(x@z['w']+z['b'],m.decision_function(x),rtol=0,atol=0)
 assert m.get_params()['C']==1 and m.get_params()['solver']=='lbfgs' and m.get_params()['max_iter']==2000
if __name__=='__main__':test_only_unhooked_dev_selection();test_frozen_fit_and_serialization();print('2 synthetic tests PASS')
