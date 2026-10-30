"""CPU-only E139 scoring. No model import/forward or old analysis invocation."""
import json,os,hashlib,datetime
from pathlib import Path
import numpy as np
from .reward import whiten,primary_four,summarize,delta_u
from .selection import STATES

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def verify(root,name,expected):
 root=Path(root).resolve();p=root/name
 if sha(p)!=expected:raise ValueError('seal identity')
 seal=read(p)
 for name,h in seal['files'].items():
  f=(root/name).resolve()
  if not f.is_relative_to(root)or sha(f)!=h:raise ValueError('sealed member identity')
 return seal

def compute(rows,white_targets,rebuilds,directions):
 if len(rows)!=120 or len({r['id']for r in rows})!=120 or set(directions)!=set(STATES):raise ValueError('six complete sealed states')
 if np.asarray(white_targets).shape[0]!=120:raise ValueError('all original target activations required')
 values=[];secondary={}
 for i,r in enumerate(rows):
  if set(r['variants'])!={'original','true','false','neutral'}:raise ValueError('four conditions')
  values.append(dict(id=r['id'],state=r['state'],scores=primary_four({k:rebuilds[v]for k,v in r['variants'].items()},white_targets[i])))
 result=summarize(values)
 for state in STATES:
  xs=[r for r in rows if r['state']==state]
  if len(xs)!=20:raise ValueError('20 originals/state')
  d=directions[state]
  try:
   secondary[state]=delta_u(d['vectors'],d['labels'],[rebuilds[r['variants']['original']]for r in xs],{name:[rebuilds[r['variants'][name]]for r in xs]for name in ('true','false','neutral')})
  except ValueError as e:
   # A zero class gap invalidates only this secondary statistic; no replacement.
   if str(e)!='NOT EVALUABLE: zero/nonfinite dev class gap':raise
   secondary[state]={'status':'NOT EVALUABLE','reason':str(e)}
 result['delta_u']=secondary
 result['interpretation']='Descriptive proxy reward only; CI including zero does not establish equivalence/absence. No structural reading if instrument gate fails.'
 return result,values

def whitener(moments):
 # Project-owned port of pinned released arithmetic; never import external repo.
 import torch
 from safetensors.torch import load_file
 torch.set_num_threads(8)
 x=load_file(str(moments),device='cpu');cov=x['cov'].double();cov=.5*(cov+cov.T)
 lam=torch.clamp_min(.1*cov.diagonal().mean(),1e-12)
 ev,u=torch.linalg.eigh(cov);w=((u*(ev.clamp_min(0)+lam).rsqrt().unsqueeze(0))@u.T).float()
 return x['mu'].float().numpy(),w.numpy()

def run(cpu_root,cpu_sha,acq_root,acq_sha,out,guard):
 cpu_root=Path(cpu_root);acq_root=Path(acq_root);out=Path(out);guard=Path(guard)
 here=Path(__file__).parent;code=here/'SCORING_ANALYSIS_SEAL.json';cs=read(code)
 for name,h in cs['files'].items():
  if sha(here/name)!=h:raise ValueError('committed source changed')
 private=verify(cpu_root,'CPU_INPUT_SEAL.json',cpu_sha)
 if private.get('experiment')!='E139'or private.get('status')!='COMPLETE'or private.get('items')!=120:raise ValueError('full frozen owner input; incomplete intake prohibited')
 acq=verify(acq_root,'OUTPUT_SEAL.json',acq_sha)
 if acq.get('experiment')!='E139'or acq.get('status')!='COMPLETE'or acq.get('tag')!=44 or acq.get('variant')!=['li','ln']:raise ValueError('complete same-space reconstruction pass required')
 if acq['owner_contract']['source_sha256']!=sha(code)or acq['owner_contract']['reward_mode']!='proxy_whitened_FVE':raise ValueError('prospective source/reward contract binding')
 plan=read(cpu_root/'PLAN.PRIVATE.json');ix=read(acq_root/'INDEX.json')
 if len(ix)!=len(set(r['id']for r in ix))or set(r['id']for r in ix)!=set(plan['acquire_ids']):raise ValueError('complete exact frozen acquisition census')
 if len(plan['rows'])!=120 or len(plan['directions'])!=300:raise ValueError('120 readouts plus200 cue/100 other DEV direction inputs')
 wanted=[v for r in plan['rows']for v in r['variants'].values()]+[r['id']for r in plan['directions']if r['source']=='acquired']
 if len(wanted)!=580 or len(set(wanted))!=580 or set(wanted)!=set(plan['acquire_ids']):raise ValueError('480 whole-readout variants plus100 DEV span inputs, disjoint exact census')
 for state in STATES:
  ds=[r for r in plan['directions']if r['state']==state];n=100 if state=='evaluation_cue'else 10
  if any(sum(r['label']==label for r in ds)!=n for label in (0,1))or len(ds)!=2*n:raise ValueError('frozen balanced DEV direction class counts')
  if any(r['source']!=('E130'if state=='evaluation_cue'else'acquired')for r in ds):raise ValueError('no mixed or substituted DEV direction source')
 if out.exists():raise FileExistsError('preserve completed/partial output')
 if sha(plan['moments_path'])!='178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a':raise ValueError('original moments only')
 # Exclusive persistent attempt marker; every later error requires owner review, no retry.
 with guard.open('x')as f:json.dump(dict(experiment='E139',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpu_seal=cpu_sha,acquisition_seal=acq_sha,source_seal=sha(code)),f)
 out.mkdir()
 arrays={};rebuilds={}
 for r in ix:
  if r['file']not in arrays:arrays[r['file']]=np.load(acq_root/r['file'],allow_pickle=False)
  v=arrays[r['file']][r['index']]
  if v.shape!=(5120,)or v.dtype!=np.float32 or not np.isfinite(v).all():raise ValueError('native complete fp32 AR vectors')
  rebuilds[r['id']]=v
 old=np.load(cpu_root/'E85_DEV_REBUILDS.PRIVATE.npy',allow_pickle=False)
 if old.shape!=(200,5120)or old.dtype!=np.float32 or not np.isfinite(old).all():raise ValueError('all200 original native E85 DEV rebuilds')
 directions={s:dict(vectors=[],labels=[])for s in STATES}
 for r in plan['directions']:
  d=directions[r['state']];d['labels'].append(r['label']);d['vectors'].append(old[r['index']]if r['source']=='E130'else rebuilds[r['id']])
 raw=np.load(cpu_root/'h44.PRIVATE.npy',allow_pickle=False)
 if raw.shape!=(120,5120)or raw.dtype!=np.float32:raise ValueError('exact original h44 target array')
 mu,w=whitener(plan['moments_path']);metrics,values=compute(plan['rows'],whiten(raw,mu,w),rebuilds,directions)
 write(out/'METRICS.json',metrics);write(out/'VALUES.PRIVATE.json',values)
 write(out/'ANALYSIS_SEAL.json',dict(experiment='E139',status='COMPLETE',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpu_seal_sha256=cpu_sha,acquisition_sha256=acq_sha,code_sha256=sha(code),guard_sha256=sha(guard),files={p.name:sha(p)for p in out.iterdir()if p.is_file()}))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser()
 for n in ('cpu-root','cpu-sha','acq-root','acq-sha','out','guard'):p.add_argument('--'+n,required=True)
 a=p.parse_args();run(a.cpu_root,a.cpu_sha,a.acq_root,a.acq_sha,a.out,a.guard)
