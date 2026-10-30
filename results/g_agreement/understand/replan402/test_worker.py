import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker import *
from smoke_profile import TinyBackend,TinyOracle,TinyModel
from contextlib import nullcontext

def smoke(out,omit=False):
 out.mkdir();TinyOracle.base=lambda self:nullcontext();TinyModel.get_input_embeddings=lambda self:self.emb
 b=TinyBackend();b.load_oracle();orig_load=b.load_nla;orig_native=b.native_one
 def nla_load():
  orig_load();b.oracle=None
 def native(reader,h):
  if reader=='oracle':assert b.oracle is not None,'Oracle must reload after NLA'
  return orig_native(reader,h)
 b.load_nla=nla_load;b.native_one=native
 np.save(out/'h.npy',np.ones((1,5120),np.float32));jobs=[]
 for stage in ('D4','D3'):
  for reader in ('oracle','nla'):
   n=len(jobs);jobs.append(dict(stage=stage,reader=reader,kind='native',phase=stage+'_'+reader,key=str(n),number=n,h_file='h.npy',measured_seconds=99999 if omit and stage=='D3' and reader=='nla' else 1,units=[{'id':str(n),'feature':'stub','ids':[1]}]))
 plan={'experiment':'E61','jobs':jobs,'retained_pilots':[]};run_stages(plan,out,b,Clock(out,time.time()+10000),out,{'plan_sha256':'stub'})
 assert (out/'D4/STAGE_SEAL.json').exists() and (out/'D3/STAGE_SEAL.json').exists()
 assert read(out/'D3/STAGE_SEAL.json')['status']==('ORACLE_ONLY' if omit else 'COMPLETE')
 if not omit:
  from smoke_joint import smoke_joint
  smoke_joint(out/'continuation_and_base_paths')

def test_every_stage(tmp_path):smoke(tmp_path/'full')
def test_D3_fallback(tmp_path):smoke(tmp_path/'fallback',True)
def test_go_starts_compute_clock():
 now=time.time();a={'experiment':'E61','pod_created_epoch':now-800,'compute_cap_seconds':6292};r={'pod_id':'p','cohort_id':COHORT,'plan_sha256':'x','capture_seals':{},'ready_epoch':now-2};g=dict(r,issued_epoch=now-1,reader_launch_authorized=True,forecast_commit='cd77d7d9');assert validate_go(g,r,a)==now-1+6292
