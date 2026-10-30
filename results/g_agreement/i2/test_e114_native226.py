import importlib.util,sys,json,time
from pathlib import Path
import numpy as np
import pytest
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'cache/g_agreement/i2/e85_retained_section223_a2/runtime/results/g_agreement/understand/late198'));sp=importlib.util.spec_from_file_location('e114',Path(__file__).with_name('e114_native226.py'));M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)
def inputs():return [dict(id=str(i),prompt='public',input_ids=[1,2],read_position=1)for i in range(504)]
def test_frozen_grid_and_read_token():assert len(M.validate(inputs()))==504
@pytest.mark.parametrize('change',['drop','private','readtoken','length'])
def test_bad_input_rejected(change):
 x=inputs()
 if change=='drop':x.pop()
 if change=='private':x[0]['target']='private'
 if change=='readtoken':x[0]['read_position']=0
 if change=='length':x[0]['input_ids']=[1]*39;x[0]['read_position']=38
 with pytest.raises(ValueError):M.validate(x)
def test_full_remaining_fit_no_cap_reset():
 d=M.fit(400,[1,2,3],5,[10],15);assert d['need_seconds']==400+1.25*(3*5+10*15)+60 and d['status']=='PASS';assert M.fit(1900,[3],5,[10],15)['status']=='NO_FIT'
def test_shared_model_full_grid_once(tmp_path,monkeypatch):
 class B:
  def __init__(self):self.calls=[]
  def sync(self):pass
  def seed(self,x):assert x==20261029
  def load_oracle(self):self.calls.append('load_oracle')
  def capture44(self,xs):self.calls+=['capture']*len(xs);return np.ones((len(xs),5120),np.float32)
  def native(self,r,v,sampled):assert r=='oracle'and sampled is False;self.calls+=['native']*len(v);return [[dict(raw='synthetic')]for x in v]
 h=tmp_path/'inputs.json';h.write_text(json.dumps(inputs()));a=type('Args',(),dict(assignment=tmp_path/'assignment.json',inputs=h,out=tmp_path/'out',input_sha256=M.sha(h),source_sha256='frozen'))();a.assignment.write_text(json.dumps(dict(experiment='E114',pod_created_epoch=time.time(),absolute_deadline_epoch=time.time()+2000,cap_seconds=2000)))
 d=json.loads(a.assignment.read_text());d['absolute_deadline_epoch']=d['pod_created_epoch']+2000;a.assignment.write_text(json.dumps(d));b=B();M.run(a,b);assert b.calls.count('load_oracle')==1 and b.calls.count('capture')==b.calls.count('native')==504
 assert M.read(a.out/'OUTPUT_SEAL.json')['native_outputs']==504
