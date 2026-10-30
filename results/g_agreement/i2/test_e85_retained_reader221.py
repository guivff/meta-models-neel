import importlib.util,sys,time,json
from pathlib import Path
import numpy as np
import pytest
R=Path(__file__).resolve().parents[3];late=R/'cache/g_agreement/i2/e85_retained_section221_v1/runtime/results/g_agreement/understand/late198';sys.path.insert(0,str(late));spec=importlib.util.spec_from_file_location('ret85',Path(__file__).with_name('e85_retained_reader221.py'));M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
from test_worker import TinyRuntime

def units():return [dict(id=str(i),feature='f'+str(i//200),arm='a'+str((i//100)%2),split='test')for i in range(400)]
def acts():return {k:np.ones((400,5120),np.float32)for k in (42,44)}
def ass(prior=M.PRIOR):return dict(prior_seconds=prior,cap_seconds=2503.385465145111,custody_start_epoch=time.time())
def clock(out,b):return M.W.Clock(out,time.time()+2503,{},b)
def test_exact_retained_frozen_capture_no_probe():
 h=R/'cache/g_agreement/i2/parallel_operators/e85-a2';items=M.read(R/'cache/g_agreement/i2/e85_retained_section221_v1/inputs/items.json');u,a=M.retained(items,h/'verified_capture',h/'cpu_once/PUBLIC_PROBE_RECEIPT.json')
 assert len(u)==400 and all(x['split']=='test'for x in u)and all(v.shape==(400,5120)for v in a.values())
def test_no_capture_probe_downstream_and_full_grid(tmp_path):
 b=TinyRuntime();M.run(b,clock(tmp_path,b),units(),acts(),tmp_path,ass());assert not({'load_base','capture','warm_capture','next_token','text'}&set(b.calls));assert sum(len(json.loads(p.read_text()))for p in tmp_path.glob('*/*.json')if p.name!='STAGE_SEAL.json')==800
 assert all(json.loads((tmp_path/(r+'_PARITY.json')).read_text())['n']==8 for r in ['oracle','nla'])
def test_report_only_real_parity_mismatch(tmp_path):
 class Different(TinyRuntime):
  def native(self,reader,h,sampled=False):return [[dict(text='batch'if len(h)>1else'serial',raw='x')]for _ in h]
 b=Different();M.run(b,clock(tmp_path,b),units(),acts(),tmp_path,ass());assert all(json.loads((tmp_path/(r+'_PARITY.json')).read_text())['status']=='FAIL_REPORT_ONLY'for r in ['oracle','nla']);assert len(list((tmp_path/'oracle').glob('[0-9]*.json')))==13
@pytest.mark.parametrize('prior',[0,M.PRIOR-1,3600])
def test_prior_or_cumulative_reset_rejected(tmp_path,prior):
 b=TinyRuntime()
 with pytest.raises(ValueError):M.run(b,clock(tmp_path,b),units(),acts(),tmp_path,ass(prior))
 assert b.calls==[]
def test_load_failure_remains_fatal(tmp_path):
 class Broken(TinyRuntime):
  def load_oracle(self):raise RuntimeError('load failure')
 b=Broken()
 with pytest.raises(RuntimeError):M.run(b,clock(tmp_path,b),units(),acts(),tmp_path,ass())
 assert not(tmp_path/'oracle').exists()
def test_original_deadline_not_extended(tmp_path):
 b=TinyRuntime();c=M.W.Clock(tmp_path,time.time()-1,{},b)
 with pytest.raises(M.W.NoFit):M.run(b,c,units(),acts(),tmp_path,ass())
 assert b.calls==[]
