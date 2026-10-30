"""§196 Oracle44 causal acquisition. Inputs are precomposed owner vectors only."""
import argparse,sys,time,threading,signal,os,math
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];U=HERE.parent
sys.path.insert(0,str(U/'e56/job'));sys.path.insert(0,str(U/'e57/job'));sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
from contract56 import read,dump,sha,verify,seal,require
from admission import atomic
from worker56 import Backend

A_ROWS={'nesting_depth','indent_level','page_range_digit'};B_ROWS={'format_plan','language_plan'}
FIELDS={'id','base_item_id','arm','feature','cell','vector_index','ids','read_index'}

def validate(items,vectors):
 require(len(items)==4704 and len({x['id'] for x in items})==4704,'exact4704 unique units')
 require(vectors.shape==(4704,5120) and vectors.dtype==np.float32 and np.isfinite(vectors).all(),'supplied full vectors')
 require(all(set(x)<=FIELDS for x in items),'public allowlist; no labels/targets/private fields')
 require({x['vector_index'] for x in items}==set(range(4704)),'exact vector indices')
 for arm,rows,cells in [('A',A_ROWS,{'none'}|{f'{d}:{a}' for d in ('J','perp','random') for a in (.25,.5,1,2,4)}),('B',B_ROWS,{'none','J','perp','random'})]:
  xs=[x for x in items if x['arm']==arm];require({x['feature'] for x in xs}==rows,'registered rows')
  for row in rows:
   sets=[]
   for cell in cells:
    group=[x for x in xs if x['feature']==row and x['cell']==cell];require(len(group)==84 and len({x['base_item_id'] for x in group})==84,'84items/cell');sets.append({x['base_item_id'] for x in group})
    for x in group:
     if arm=='B':require(x['ids'] and x['read_index']==len(x['ids'])-1 and all(type(t)is int and t>=0 for t in x['ids']),'frozen prompt ends at read token')
     else:require('ids' not in x and 'read_index' not in x,'ArmA no item text')
   require(all(s==sets[0] for s in sets),'same84items across cells')
 require(sum(x['arm']=='B' for x in items)==672,'672continuations')

def patched_logits(model,tok,items,h):
 """Patch block44 output once on prefill only; base-model forward, selecting frozen candidate token logits."""
 import torch
 from mats.capture import decoder_blocks
 require(len(items)==len(h) and len({len(x['ids']) for x in items})==1,'equal-length batches; no padding')
 ids=torch.tensor([x['ids'] for x in items],device=model.get_input_embeddings().weight.device);positions=[x['read_index'] for x in items];seen=[]
 def hook(module,args,out):
  if seen:return out
  z=out[0] if isinstance(out,tuple) else out;require(z.shape[:2]==ids.shape,'prefill shape');z=z.clone();v=torch.as_tensor(np.array(h,copy=True),device=z.device,dtype=z.dtype)
  for i,pos in enumerate(positions):z[i,pos]=v[i]
  seen.append(True);return (z,*out[1:]) if isinstance(out,tuple) else z
 handle=decoder_blocks(model)[44].register_forward_hook(hook)
 try:
  with torch.inference_mode():output=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,logits_to_keep=1).logits[:,0].float()
 finally:handle.remove()
 require(len(seen)==1,'exactly one block44prefill patch')
 contract=read(HERE/'CANDIDATES.json')
 result=[]
 for x,z in zip(items,output):
  pairs=contract['candidate_token_ids'][x['feature']]
  result.append(dict(pair_logits=[[float(z[a]),float(z[b])] for a,b in pairs]))
 return result

class RunnerBackend(Backend):
 def load_oracle(self):
  super().load_oracle()
  expected=read(HERE/'CANDIDATES.json')['candidate_token_ids']
  strings={'format_plan':[['-','The']],'language_plan':[['Je','The'],['Le','The']]}
  for row,pairs in strings.items():
   require([[[self.oracle.tok.encode(a,add_special_tokens=False)],[self.oracle.tok.encode(b,add_special_tokens=False)]] for a,b in pairs]==[[[[a]],[[b]]] for a,b in expected[row]],'frozen first-token candidates')
 def continuation(self,items,h):
  with self.oracle.base():return patched_logits(self.oracle.model,self.oracle.tok,items,h)

def jobs(items):
 native=[dict(kind='native',indices=list(range(i,min(i+8,len(items))))) for i in range(0,len(items),8)]
 buckets={}
 for i,x in enumerate(items):
  if x['arm']=='B':buckets.setdefault(len(x['ids']),[]).append(i)
 cont=[dict(kind='continuation',indices=v[i:i+8]) for _,v in sorted(buckets.items()) for i in range(0,len(v),8)]
 return native+cont

class Clock:
 def __init__(self,out,end):self.out=out;self.end=end;self.events=[];self.cost={'native':[],'continuation':[]}
 def check(self):require(time.time()<self.end-60,'fixed custody deadline reserve')
 def call(self,kind,fn):
  self.check();start=time.monotonic()
  try:v=fn()
  except BaseException:
   self.events.append(dict(phase=kind,seconds=time.monotonic()-start,status='FAILED'));atomic(self.out/'PHASE_TIMINGS.json',self.events);raise
  dt=time.monotonic()-start;self.events.append(dict(phase=kind,seconds=dt,status='COMPLETE'));atomic(self.out/'PHASE_TIMINGS.json',self.events)
  if kind in self.cost:self.cost[kind].append(dt)
  self.check();return v
 def forecast(self,jj,done):
  left={kind:sum(j['kind']==kind and i not in done for i,j in enumerate(jj)) for kind in self.cost}
  require(all(self.cost[k] or n==0 for k,n in left.items()),'real retained pilot for each phase')
  seconds=1.25*sum(n*np.mean(self.cost[k]) for k,n in left.items() if n);fits=time.time()+seconds<self.end-60
  atomic(self.out/'FORECAST.json',dict(status='ADMIT' if fits else 'NO_FIT',remaining=left,remaining_seconds=float(seconds),margin=1.25,mean_real_batch_seconds={k:float(np.mean(v)) for k,v in self.cost.items() if v},deadline_epoch=self.end))
  return fits

def acquire(items,h,b,clock,out):
 clock.call('oracle_setup',b.load_oracle)
 dummy=np.random.default_rng(20261028).standard_normal((8,5120)).astype(np.float32)
 def warm_native():b.native_one('oracle',dummy)
 clock.call('native_warmup_discarded',warm_native)
 # Shape is fixed independently of real prompts, with dummy token IDs only.
 token=b.oracle.tok.encode(' the',add_special_tokens=False)[0]
 def warm_cont():b.continuation([dict(ids=[token]*32,read_index=31,feature='format_plan') for _ in range(8)],dummy)
 clock.call('continuation_warmup_discarded',warm_cont)
 jj=jobs(items);dump(out/'JOB_GRID.json',jj);(out/'jobs').mkdir();done=set()
 def run(i):
  j=jj[i];xs=[items[k] for k in j['indices']];v=h[[x['vector_index'] for x in xs]].copy();before=v.tobytes()
  if j['kind']=='native':result=clock.call('native',lambda:b.native_one('oracle',v));require(len(result)==len(xs) and all(len(g)==1 for g in result),'one native per unit');result=[g[0] for g in result]
  else:result=clock.call('continuation',lambda:b.continuation(xs,v));require(len(result)==len(xs),'continuation grid')
  require(v.tobytes()==before,'supplied vectors unchanged')
  dump(out/'jobs'/f'{i:06d}.json',[dict(id=x['id'],**r) for x,r in zip(xs,result)]);done.add(i);atomic(out/'COMPLETED.json',sorted(done))
 # Retain one real pilot per channel, then admit the entire remaining run.
 for kind in ('native','continuation'):run(next(i for i,j in enumerate(jj) if j['kind']==kind))
 if not clock.forecast(jj,done):return False
 for i in range(len(jj)):
  if i in done:continue
  run(i)
  if not clock.forecast(jj,done):return False
 return True

def main():
 p=argparse.ArgumentParser()
 for n in ('inputs','assignment','assets','out'):p.add_argument('--'+n,type=Path,required=True)
 for n in ('source-sha','input-sha'):p.add_argument('--'+n,required=True)
 p.add_argument('--dry-run',action='store_true');a=p.parse_args();verify(HERE,'SOURCE_SEAL.json',a.source_sha)
 for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'dependency')
 verify(a.inputs,'INPUT_SEAL.json',a.input_sha);items=read(a.inputs/'items.json');h=np.load(a.inputs/'vectors.npy',allow_pickle=False);validate(items,h);limits=read(HERE/'STAGE_REQUEST.json');ass=read(a.assignment)
 require(ass['experiment']=='E79' and ass['gpu_count']==1 and ass['prior_seconds']>=0 and ass['cap_seconds']>0 and ass['prior_seconds']+ass['cap_seconds']<=limits['cap_seconds'],'stage request cap')
 require(ass['custody_start_epoch']==ass['pod_created_epoch'] and ass['absolute_deadline_epoch']==ass['pod_created_epoch']+ass['cap_seconds'],'creation clock includes staging/setup/warmup');require(ass['daily_budget_verified'] is True and 0<=ass['projected_daily_USD']<=limits['account_gate_USD'],'verified spend')
 a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'ASSIGNMENT.json',ass);end=ass['absolute_deadline_epoch'];timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  if a.dry_run:
   from test_worker import TinyBackend
   backend=TinyBackend()
  else:backend=RunnerBackend(ROOT,a.assets,{'gpu_type':'H200'})
  complete=acquire(items,h,backend,Clock(a.out,end),a.out)
  if a.dry_run:dump(a.out/'DRY_RUN.json',dict(status='PASS' if complete else 'NO_FIT',GPU_calls=0,items=len(items)))
  dump(a.out/'TIMING.json',dict(completed_epoch=time.time(),deadline_epoch=end));seal(a.out,'OUTPUT_SEAL.json',dict(experiment='E79',status='COMPLETE' if complete else 'NO_FIT',source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,pod_id=ass['pod_id']))
 finally:timer.cancel()
if __name__=='__main__':main()
