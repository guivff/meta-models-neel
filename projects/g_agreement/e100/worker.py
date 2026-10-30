"""§208 E79-derived acquisition: transplant/swap only after §208 deviation1."""
import argparse,gc,importlib.util,os,signal,sys,threading,time
from pathlib import Path
import numpy as np
from .contract import ROOT,OLD_RUNNER,ROWS,DIRECTIONS,read,write,sha,verify,require,validate,jobs
from .interventions import transform,ratios
SEAL_DEADLINE=1793271600 # 2026-10-29 11:00 UTC /12:00 CET

def original():
 p=ROOT/'results/g_agreement/understand/e79/worker.py';require(sha(p)==OLD_RUNNER,'E79 runner8e431cca exact pin')
 sys.path[:0]=[str(ROOT),str(ROOT/'external/mats-nla-workspace/src')]
 spec=importlib.util.spec_from_file_location('_e79_for_e100',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def backend(assets,assignment):
 old=original()
 class E100Backend(old.Backend):
  def load_oracle(self):
   import torch
   self.oracle=self.nla=None;gc.collect();torch.cuda.empty_cache();hardware(assignment)
   from projects.g_agreement.blindspot import run
   os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
   self.oracle=run._load_oracle(run._assets(self.assets_path,names=('model','olens')))
  def load_nla(self):hardware(assignment);super().load_nla()
 return E100Backend(ROOT,assets,assignment)

def hardware(assignment):
 import torch
 require(assignment['gpu_type'] in ('H200','B200') and torch.cuda.is_available() and torch.cuda.device_count()==1,'authorized singleGPU')
 name=torch.cuda.get_device_name(0);require(assignment['gpu_type'] in name,'actual GPU matches assigned shard type');return name

def validate_assignment(a,shard,input_sha,source_sha,assets_sha):
 require(a['experiment']=='E100' and a['shard']==shard and a['stage']=='ab' and a['gpu_count']==1,'assigned full shard/stage')
 require(a['gpu_type'] in ('H200','B200') and a['input_seal_sha256']==input_sha and a['source_seal_sha256']==source_sha and a['assets_sha256']==assets_sha,'exact input/source/assets/hardware binding')
 require(a['cap_seconds']>0 and a['prior_seconds']>=0 and a['cap_seconds']+a['prior_seconds']<=a['authorized_cumulative_seconds'],'operator authorized cumulative cap')
 require(a['custody_start_epoch']==a['pod_created_epoch'] and a['absolute_deadline_epoch']==a['pod_created_epoch']+a['cap_seconds'] and a['absolute_deadline_epoch']<=SEAL_DEADLINE,'creation clock andThu12CET seal deadline')
 require(a['daily_budget_verified'] is True and 0<=a['projected_daily_USD']<=a['daily_budget_USD'] and a['allocation_verified'] is True,'verified allocation and daily spend')
 require(set(a['row_gpu_types'])==set(ROWS[shard]) and all(x==a['gpu_type'] for x in a['row_gpu_types'].values()),'one GPU type per whole row')
 require(a['pod_id']==os.environ.get('RUNPOD_POD_ID'),'provider pod identity')

def phase(j,items):return j['reader']+':'+str(len(j['indices']))

def acquire(items,arrays,shard,b,clock,out,gpu_type):
 planned=jobs(items,shard);active=planned;skipped=[]
 for j in active:j['phase']=phase(j,items)
 write(out/'JOB_GRID.json',planned);write(out/'NOT_RUN.json',skipped);write(out/'COMPLETED.json',[]);(out/'jobs').mkdir();done=set();clock.cost={j['phase']:[] for j in active};overhead={}
 readers=[r for r in ('oracle','nla') if any(j['reader']==r for j in active)]
 def setup(reader):
  start=time.monotonic();clock.call(reader+'_setup',getattr(b,'load_'+reader))
  dummy=np.random.default_rng(20261028).standard_normal((8,arrays['H44'].shape[1])).astype(np.float32)
  clock.call(reader+'_warmup_discarded',lambda:b.native_one(reader,dummy));overhead[reader]=time.monotonic()-start
 def run(j):
  ix=j['indices'];xs=[items[i] for i in ix];h=arrays['H44' if j['reader']=='oracle' else 'H42'][ix].copy();before=h.tobytes()
  donor=arrays['H44' if j['reader']=='oracle' else 'H42'][[x['donor_slot'] for x in xs]].copy()
  def operation():
   hp=transform(h,donor,j['mode'],basis=arrays['BASIS_'+j['basis']] if j['mode']=='swap' else None,complement=j.get('complement',False));norm=ratios(h,hp).tolist()
   snapshot=hp.tobytes();values=b.native_one(j['reader'],hp)
   require(snapshot==hp.tobytes() and before==h.tobytes(),'native adapter cannot mutate supplied vectors')
   require(len(values)==len(xs) and all(len(x)==1 for x in values),'one greedy native readout/cell')
   rr=ratios(h,hp)
   return [dict(id=x['id']+':'+j['reader']+':'+j['condition'],item_id=x['id'],row=j['row'],reader=j['reader'],condition=j['condition'],mode=j['mode'],repeat=0,read_block=44 if j['reader']=='oracle' else 42,inject_block=j.get('inject_block',44 if j['reader']=='oracle' else 42),basis_block=44,norm_ratio=float(n),norm_over_1_5=bool(n>1.5),read_layer_norm_ratio=float(r),gpu_type=gpu_type,**v[0]) for x,v,n,r in zip(xs,values,norm,rr)]
  result=clock.call(j['phase'],operation);write(out/'jobs'/f"{j['number']:06d}.json",result);done.add(j['number']);write(out/'COMPLETED.json',sorted(done))
 def forecast(pending_loaders):
  remaining={k:sum(j['phase']==k and j['number'] not in done for j in active) for k in clock.cost}
  require(all(clock.cost[k] or n==0 for k,n in remaining.items()),'retained real pilots for each batch shape')
  seconds=1.25*(sum(n*float(np.mean(clock.cost[k])) for k,n in remaining.items() if n)+sum(overhead[r] for r in pending_loaders));fits=time.time()+seconds<clock.end-60
  write(out/'FORECAST.json',dict(status='ADMIT' if fits else 'NO_FIT',remaining=remaining,remaining_seconds=seconds,margin=1.25,mean_real_batch_seconds={k:float(np.mean(v)) for k,v in clock.cost.items() if v},remaining_loader_seconds={r:overhead[r] for r in pending_loaders},deadline_epoch=clock.end,warmups_in_means=False,pilots_retained=True));return fits
 # Real pilots for every reader/batch shape, retained under their original job IDs.
 for reader in readers:
  setup(reader)
  for key in dict.fromkeys(j['phase'] for j in active if j['reader']==reader):run(next(j for j in active if j['phase']==key))
 pending=[r for r in readers if any(j['reader']==r and j['number'] not in done for j in active)]
 if not forecast(pending):return False
 for reader in readers:
  if reader not in pending:continue
  setup(reader);pending.remove(reader)
  if not forecast(pending):return False
  for j in active:
   if j['reader']!=reader or j['number'] in done:continue
   run(j)
   if not forecast(pending):return False
 require(done=={j['number'] for j in active},'all active cells exactly once');return True

def main():
 if sys.argv[1:]==['--cpu-import-preflight']:
  original();from projects.g_agreement.blindspot import run
  print('E100 exact CPU import PASS; no model load');return
 p=argparse.ArgumentParser()
 for n in ('inputs','assignment','assets','out','source-seal'):p.add_argument('--'+n,type=Path,required=True)
 for n in ('input-sha','source-sha'):p.add_argument('--'+n,required=True)
 p.add_argument('--shard',choices=tuple(ROWS),required=True);p.add_argument('--input-seal',default='INPUT_SEAL.json');p.add_argument('--validate-only',action='store_true');a=p.parse_args()
 verify(ROOT,str(a.source_seal.resolve().relative_to(ROOT)),a.source_sha);s=verify(a.inputs,a.input_seal,a.input_sha)
 require(s['experiment']=='E100','owner sealed E100 input')
 from .owner_input import load
 items,arrays=load(a.inputs,s,a.shard);validate(items,arrays,a.shard)
 if a.validate_only:print('E100 exact public input contract PASS; no model load');return
 ass=read(a.assignment);validate_assignment(ass,a.shard,a.input_sha,a.source_sha,sha(a.assets))
 actual=hardware(ass)
 if ass['gpu_type']=='B200':
  smoke=Path(ass['b200_smoke_receipt']);require(sha(smoke)==ass['b200_smoke_sha256'],'same-image smoke hash');r=read(smoke)
  require(r['verified'] is True and r['status']=='PASS' and r['image_digest']==ass['image_digest'] and r['assets_sha256']==sha(a.assets) and r['finite_outputs'] is True and r['decoding_unchanged'] is True and r['n_items']==3,'§204 same-image3-item B200 smoke required')
 require(time.time()+ass['prelaunch_forecast_seconds']<ass['absolute_deadline_epoch']-180,'full-stage forecast fits allocation before loading')
 a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);write(a.out/'HARDWARE.json',dict(gpu_type=ass['gpu_type'],actual_gpu_name=actual,shard=a.shard,row_gpu_types=ass['row_gpu_types']))
 end=ass['absolute_deadline_epoch'];timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='FAILED'
 try:
  old=original();b=backend(a.assets,ass);complete=acquire(items,arrays,a.shard,b,old.Clock(a.out,end-120),a.out,ass['gpu_type']);status='COMPLETE' if complete else 'NO_FIT'
 except BaseException as exc:write(a.out/'FAILURE.json',dict(error_type=type(exc).__name__));raise
 finally:
  timer.cancel();write(a.out/'OUTPUT_SEAL.json',dict(experiment='E100',shard=a.shard,stage='ab',status=status,completed_epoch=time.time(),source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,gpu_type=ass['gpu_type'],actual_gpu_name=actual,pod_id=ass['pod_id'],labels_cpu_only=True,files={str(p.relative_to(a.out)):sha(p) for p in sorted(a.out.rglob('*')) if p.is_file() and p.name!='OUTPUT_SEAL.json'}))
if __name__=='__main__':main()
