"""E80: sealed block42/44 capture, forecast-bound GO, then native readers only."""
import sys,argparse,time,threading,signal,os,re,math
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];U=HERE.parent
sys.path.insert(0,str(U/'e56/job'));sys.path.insert(0,str(U/'e57/job'));sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
from contract56 import read,dump,sha,verify,seal,require
from admission import atomic
from worker56 import Backend
from native_nla512 import truncation_summary
FAMILIES={'multihop':100,'multilingual_multihop':98,'chain_intermediates':120,'association':100,'poetry':100}

def validate(items):
 from collections import Counter
 require(len(items)==518 and len({x['id'] for x in items})==518,'exact518 unique items')
 require(Counter(x['feature'] for x in items)==FAMILIES,'six frozen family counts')
 for x in items:
  require(set(x)=={'id','feature','text','ids','read_index'},'public allowlist; no targets/labels/judge prompts')
  require(isinstance(x['text'],str) and x['ids'] and all(type(v)is int and v>=0 for v in x['ids']) and type(x['read_index'])is int and 0<=x['read_index']<len(x['ids']),'owner frozen token site')

class E80Backend(Backend):
 def capture_positions(self,items):
  import torch
  from mats.capture import capture
  self.validate_tokenization(items)
  with self.oracle.base(),torch.inference_mode():
   values=capture(self.oracle.model,[x['ids'][:x['read_index']+1] for x in items],(42,44),[[x['read_index']] for x in items],batch_size=8,pad_id=self.oracle.tok.pad_token_id or 0)
  return {k:v[:,0].float().cpu().numpy() for k,v in values.items()}

class Clock:
 def __init__(self,out,end,seed):self.out=out;self.end=end;self.seed=seed;self.events=[];self.observed={}
 def check(self):require(time.time()<self.end-60,'fixed deadline/retrieval reserve')
 def call(self,phase,fn):
  self.check();t=time.monotonic()
  try:v=fn()
  except BaseException:
   self.events.append(dict(phase=phase,status='FAILED',seconds=time.monotonic()-t));atomic(self.out/'PHASE_TIMINGS.json',self.events);raise
  dt=time.monotonic()-t;self.events.append(dict(phase=phase,status='COMPLETE',seconds=dt));atomic(self.out/'PHASE_TIMINGS.json',self.events)
  if phase in ('oracle_native','nla_native'):self.observed.setdefault(phase,[]).append(dt)
  self.check();return v
 def forecast(self,remaining,nla_loaded):
  seconds=0.;means={}
  for reader,n in remaining.items():
   k=reader+'_native';per=float(np.mean(self.observed[k])) if self.observed.get(k) else self.seed[k];means[k]=per;seconds+=n*per
  if remaining.get('nla',0) and not nla_loaded:seconds+=self.seed['nla_setup']
  fits=time.time()+1.25*seconds<self.end-60;atomic(self.out/'FORECAST.json',dict(status='ADMIT' if fits else 'NO_FIT',remaining=remaining,mean_real_or_seed_seconds=means,margin=1.25,remaining_seconds=1.25*seconds,deadline_epoch=self.end));return fits

def capture_stage(items,b,c,out,binding):
 c.call('oracle_setup',b.load_oracle);cap=out/'capture';cap.mkdir();parts={42:[],44:[]}
 for i in range(0,len(items),8):
  got=c.call('capture',lambda:b.capture_positions(items[i:i+8]))
  for layer in parts:parts[layer].append(got[layer])
 acts={layer:np.concatenate(v) for layer,v in parts.items()}
 for layer,h in acts.items():require(h.shape==(518,5120) and np.isfinite(h).all(),'full capture shape');np.save(cap/f'acts{layer}.npy',h)
 dump(cap/'items.order.json',[x['id'] for x in items]);dump(cap/'POSITIONS.json',[dict(id=x['id'],read_index=x['read_index']) for x in items]);seal(cap,'CAPTURE_SEAL.json',dict(binding,layers=[42,44],reader_outputs=0));ready=dict(binding,capture_seal_sha256=sha(cap/'CAPTURE_SEAL.json'),ready_epoch=time.time(),reader_outputs=0);dump(out/'CAPTURE_READY.json',ready);return acts,ready

def reuse_capture(inputs,items,limits,out,binding):
 cap=inputs/'capture';digest=limits['capture_seal_sha256'];sealed=verify(cap,'CAPTURE_SEAL.json',digest)
 require(sealed['experiment']=='E80' and sealed['layers']==[42,44] and sealed['synthetic'] is False and sealed['reader_outputs']==0,'authentic delivered pre-reader capture')
 require(read(cap/'items.order.json')==[x['id'] for x in items],'delivered capture exact item order')
 acts={l:np.load(cap/f'acts{l}.npy',allow_pickle=False) for l in (42,44)}
 require(all(h.shape==(518,5120) and np.isfinite(h).all() for h in acts.values()),'delivered paired read-position vectors')
 ready=dict(binding,capture_seal_sha256=digest,ready_epoch=time.time(),reader_outputs=0,capture_reused=True)
 dump(out/'CAPTURE_READY.json',ready);dump(out/'REUSED_CAPTURE.json',dict(path=str(cap),capture_seal_sha256=digest,recapture=False));return acts,ready

def check_go(go,ready,now):
 for k in ('experiment','pod_id','input_seal_sha256','source_seal_sha256','capture_seal_sha256'):require(go[k]==ready[k],'capture-bound GO '+k)
 require(go['reader_launch_authorized'] is True and ready['ready_epoch']<=go['issued_epoch']<=now,'explicit post-capture release')
 require(re.fullmatch('[0-9a-f]{40}',go['forecast_commit']) and re.fullmatch('[0-9a-f]{64}',go['forecast_seal_sha256']),'committed per-item J/logit-lens forecast')

def wait_go(path,ready,c):
 while not path.exists():c.check();time.sleep(1)
 go=read(path);check_go(go,ready,time.time());dump(c.out/'GO_RECEIPT.json',go);return go

def read_stages(items,acts,b,c,out):
 batches=[list(range(i,min(i+8,518))) for i in range(0,518,8)];remaining={'oracle':len(batches),'nla':len(batches)};allrecords=[];(out/'jobs').mkdir()
 for reader in ('oracle','nla'):
  if reader=='nla':c.call('nla_setup',b.load_nla)
  dummy=np.random.default_rng(20261028).standard_normal((8,5120)).astype(np.float32)
  def warmup():b.native_one(reader,dummy)
  c.call(reader+'_warmup_discarded',warmup)
  for n,ix in enumerate(batches):
   h=acts[44 if reader=='oracle' else 42][ix].copy();before=h.tobytes();groups=c.call(reader+'_native',lambda:b.native_one(reader,h));require(h.tobytes()==before and len(groups)==len(ix) and all(len(g)==1 for g in groups),'one native/read vector unchanged')
   records=[dict(id=items[i]['id']+':'+reader,unit_id=items[i]['id'],feature=items[i]['feature'],reader=reader,layer=44 if reader=='oracle' else 42,repeat=0,**g[0]) for i,g in zip(ix,groups)];dump(out/'jobs'/f'{reader}_{n:04d}.json',records);allrecords+=records;remaining[reader]-=1
   if not c.forecast(remaining,reader=='nla'):return False
  seal(out/'jobs',reader+'_STAGE_SEAL.json',dict(reader=reader,status='COMPLETE'))
 dump(out/'RECORDS.json',allrecords);dump(out/'NLA_TRUNCATION.json',truncation_summary([x for x in allrecords if x['reader']=='nla']));return True

def main():
 p=argparse.ArgumentParser()
 for k in ('inputs','assignment','assets','out','go'):p.add_argument('--'+k,type=Path,required=True)
 for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
 p.add_argument('--dry-run',action='store_true');p.add_argument('--readers-only',action='store_true');a=p.parse_args();verify(HERE,'SOURCE_SEAL.json',a.source_sha)
 for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'dependency')
 verify(a.inputs,'INPUT_SEAL.json',a.input_sha);items=read(a.inputs/'items.json')
 if a.readers_only:
  from collections import Counter
  require(len(items)==518 and len({x['id'] for x in items})==518 and all(set(x)=={'id','feature'} for x in items) and Counter(x['feature'] for x in items)==FAMILIES,'label-free readers-only item grid')
 else:validate(items)
 ass=read(a.assignment);limits=read(HERE/'STAGE_REQUEST.json')
 require(ass['experiment']=='E80' and ass['gpu_count']==1 and ass['cap_seconds']>0 and ass['prior_seconds']>=0 and ass['cap_seconds']<=limits['cap_seconds'] and ass['prior_seconds']+ass['cap_seconds']<=limits.get('cumulative_cap_seconds',limits['cap_seconds']),'sealed stage cap');require(ass['pod_created_epoch']<=ass['custody_start_epoch']<=time.time() and ass['absolute_deadline_epoch']==ass['custody_start_epoch']+ass['cap_seconds'],'fixed creation clock');require(ass['daily_budget_verified'] is True and 0<=ass['projected_daily_USD']<=limits['account_gate_USD'],'verified budget')
 a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'ASSIGNMENT.json',ass);end=ass['absolute_deadline_epoch'];c=Clock(a.out,end,read(HERE/'SEED_TIMINGS.json'));timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();binding=dict(experiment='E80',synthetic=a.dry_run,pod_id=ass['pod_id'],source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha)
 try:
  if a.dry_run:
   from test_worker import TinyBackend
   b=TinyBackend()
  else:b=E80Backend(ROOT,a.assets,{'gpu_type':'H200'})
  if a.readers_only:
   acts,ready=reuse_capture(a.inputs,items,limits,a.out,binding)
  else:acts,ready=capture_stage(items,b,c,a.out,binding)
  if a.dry_run:
   # Stub only: exercise release validator on synthetic receipt; never run this branch with models.
   go=dict(ready,reader_launch_authorized=True,issued_epoch=time.time(),forecast_commit='a'*40,forecast_seal_sha256='b'*64);check_go(go,ready,time.time());dump(a.out/'GO_RECEIPT.json',go)
  else:wait_go(a.go,ready,c)
  if a.readers_only:c.call('oracle_setup',b.load_oracle)
  complete=read_stages(items,acts,b,c,a.out);dump(a.out/'TIMING.json',dict(completed_epoch=time.time(),deadline_epoch=end))
  if a.dry_run:dump(a.out/'DRY_RUN.json',dict(status='PASS' if complete else 'NO_FIT',GPU_calls=0))
  seal(a.out,'OUTPUT_SEAL.json',dict(binding,status='COMPLETE' if complete else 'NO_FIT',capture_seal_sha256=ready['capture_seal_sha256'],capture_reused=a.readers_only))
 except BaseException as error:
  dump(a.out/'FAILURE.json',dict(error_type=type(error).__name__,reason=str(error),reader_outputs_authorized=(a.out/'GO_RECEIPT.json').exists()));raise
 finally:timer.cancel()
if __name__=='__main__':main()
