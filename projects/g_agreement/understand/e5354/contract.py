import hashlib,json,math,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'results/g_agreement/understand/e5354'
CAP=5400
SEED=20261027
E54_SHA='c13d59f5816321a249d673dd65c35490906b64afcc33fe633bcc66d148d53358'
E49_SHA='ccc2b3b6e27d0227f2d17f1de0efe2cb9a33cfd4d299656f19d7e4a4e3db43c9'
def require(v,msg):
 if not v:raise ValueError(msg)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def dump(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def verify(p,name,digest=None):
 p=Path(p)
 if digest:require(sha(p/name)==digest,'seal identity '+name)
 s=read(p/name)
 for n,h in s['files'].items():
  q=(p/n).resolve();require(q.is_relative_to(p.resolve()) and sha(q)==h,'sealed member '+n)
 return s
def seal(p,name,extra=None):
 p=Path(p);dump(p/name,dict(extra or {},files={str(q.relative_to(p)):sha(q) for q in sorted(p.rglob('*')) if q.is_file() and q.name!=name}))
def sources():
 s=read(HERE/'SOURCE_SEAL.json')
 for n,h in s['files'].items():require(sha(ROOT/n)==h,'source changed '+n)
def auc(y,s):
 y=np.asarray(y);s=np.asarray(s,float);require(y.shape==s.shape and np.isfinite(s).all(),'AUROC grid')
 a=s[y==1];b=s[y==0];require(len(a)>0 and len(b)>0,'two AUROC classes')
 return float(((a[:,None]>b)+.5*(a[:,None]==b)).mean())
def donors(items):
 out={}
 for x in items:
  pool=sorted(v['id'] for v in items if v['feature']==x['feature'] and v['split']==x['split'] and v['label']!=x['label'] and v['cluster']!=x['cluster'])
  require(pool,'opposite-state other-cluster donor missing')
  out[x['id']]=pool[int(hashlib.sha256(('E53:20261027:'+x['id']).encode()).hexdigest(),16)%len(pool)]
 return out

def deadline(a):
 require(a.get('issuer')=='integrator' and a.get('experiment')=='E53+E54','assignment authority')
 require(a.get('gpu_count')==1 and a.get('cap_seconds')==CAP and a.get('gpu_type')=='H200','one H200, total5400s')
 require(a.get('external_hardstop_verified') is True and a.get('pod_id'),'external custody guard')
 start=float(a['pod_created_epoch']);end=float(a['deadline_epoch'])
 require(math.isfinite(start) and math.isfinite(end) and start<=time.time() and end==start+CAP,'provider-creation cap')
 return end
class Budget:
 def __init__(self,a):
  self.end=deadline(a);self.observed={};self.phase_end=None
  self.remaining=dict(a['phase_estimates_seconds'])
  require(set(self.remaining)==set(['oracle_setup','parity','e54_capture','e53_base','e53_olens_true','e53_olens_opposite_swap','e36_swap','e54_oracle','nla_setup','e53_nla_true','e53_nla_opposite_swap','e54_nla']),'complete phase forecast required')
  require(all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in self.remaining.values()),'finite positive forecast')
  self.check();self.forecast()
 def forecast(self):require(time.time()+1.5*sum(self.remaining.values())+360<self.end-120,'NO_FIT full remaining job')
 def check(self):require(time.time()<min(self.end-120,self.phase_end or self.end),'deadline/retrieval reserve')
 def call(self,phase,fn,remaining_units=0):
  self.check();t=time.monotonic();v=fn();dt=time.monotonic()-t;self.observed[phase]=max(dt,self.observed.get(phase,0));self.check()
  require(phase in self.remaining,'unforecast phase')
  self.remaining[phase]=max(self.remaining[phase]*remaining_units/(remaining_units+1),self.observed[phase]*remaining_units)
  self.forecast()
  require(time.time()+1.5*self.observed[phase]*remaining_units<min(self.end-120,self.phase_end or self.end),'NO_FIT '+phase)
  return v
