"""Integrator-only real GPU timing preflight. No verdict or registered analysis."""
import argparse,time,threading,os,signal,math,json
from pathlib import Path
import numpy as np
from contract56 import ROOT,HERE,read,dump,verify,sha,seal,require
from worker56 import Backend,readout_records
import parity_gate

class ProfileBudget:
 def __init__(self,end,journal=None):self.end=end;self.observed={};self.journal=journal
 def check(self):require(time.time()<self.end-60,'profile custody reserve')
 def record(self,phase,status,elapsed=None):
  if self.journal is None:return
  with Path(self.journal).open('a') as f:
   f.write(json.dumps({'phase':phase,'status':status,'elapsed_seconds':elapsed,'recorded_epoch':time.time()},allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
 def call(self,phase,fn,remaining_units=0):
  self.check();start=time.monotonic();self.record(phase,'started')
  try:value=fn()
  except BaseException:
   self.record(phase,'failed',time.monotonic()-start);raise
  elapsed=time.monotonic()-start;self.observed.setdefault(phase,[]).append(elapsed)
  self.record(phase,'completed',elapsed);self.check();return value

def profile_deadline(ass):
 require(ass['new_pod_allowed'] is True and ass['gpu_count']==1 and 0<ass['cap_seconds']<=1800,'fresh dedicated profile pod allocation')
 created=ass['pod_created_epoch'];end=ass['absolute_deadline_epoch']
 require(all(isinstance(v,(int,float)) and math.isfinite(v) for v in (created,end,ass['cap_seconds'])),'finite custody clock')
 require(bool(ass['pod_id']) and created<=time.time() and created<end<=created+ass['cap_seconds'],'creation-based profile deadline')
 return end

def select_dev_units(items,continuations):
 require(items and all(x.get('split')=='dev' for x in items),'profile input must contain dev items only')
 row=sorted(r for r,v in continuations.items() if v['pairs'] is not None and sum(x['feature']==r for x in items)>=8)[0]
 units=sorted([x for x in items if x['feature']==row],key=lambda x:x['id'])[:8]
 require(len(units)==8 and len({x['id'] for x in units})==8,'eight unique dev units')
 return row,units

def preflight(inputs,assets,ass):
 verify(HERE,'SOURCE_SEAL.json',ass['source_seal_sha256']);verify(inputs,'INPUT_SEAL.json',ass['input_seal_sha256'])
 for path,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/path)==digest,'dependency: '+path)
 items=read(inputs/'items.json');row,units=select_dev_units(items,read(inputs/'CONTINUATIONS.json'))
 parity_inputs=parity_gate.load_inputs({'path':str(inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256})
 # The assets manifest is supplied by the integrator; weight loading is the only stubbed I/O in CPU preflight.
 manifest=read(assets);require(isinstance(manifest,dict),'assets manifest')
 return row,units,parity_inputs

def run_stages(backend,budget,units,pairs,parity_inputs,out,mode):
 records=[]
 require(mode in ('all','nla_only_synthetic'),'profile mode')
 if mode=='all':
  budget.call('oracle_setup',backend.load_oracle)
  parity=out/'parity';parity.mkdir();parity_gate.run_gate(backend,budget,parity,parity_inputs)
  backend.validate_tokenization(units);acts=budget.call('capture',lambda:backend.capture(units));readers=('oracle','nla')
 else:
  acts={42:np.random.default_rng(20261027).standard_normal((8,5120)).astype(np.float32)}
  units=[{'id':f'synthetic:{i}','feature':'timing_only','split':'synthetic'} for i in range(8)];readers=('nla',)
 for reader in readers:
  if reader=='nla':budget.call('nla_setup',backend.load_nla)
  layer=44 if reader=='oracle' else 42
  values=budget.call(reader+'_native',lambda:backend.native_one(reader,acts[layer]))
  records+=readout_records(reader,units,values,'text')
  budget.call(reader+'_continuation',lambda:backend.score('continuation' if reader=='oracle' else 'nla',units,acts[layer],pairs))
 return records,units

def main():
 p=argparse.ArgumentParser()
 for k in ('inputs','assets','assignment','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--dry-run',action='store_true')
 a=p.parse_args();ass=read(a.assignment)
 end=profile_deadline(ass)
 a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'ASSIGNMENT.json',ass)
 budget=ProfileBudget(end,a.out/'PHASE_TIMINGS.jsonl');budget.check()
 try:row,units,parity_inputs=budget.call('preflight',lambda:preflight(a.inputs,a.assets,ass))
 except BaseException as error:dump(a.out/'FAILURE.json',{'error':str(error),'phase':'preflight'});raise
 if a.dry_run:
  from smoke_profile import smoke
  smoke(a.out/'SMOKE')
  # Real preflight plus complete shared dispatch with tiny CPU models; no production weights.
  dump(a.out/'DRY_RUN.json',{'status':'PASS','model_loading':'STUBBED','parity_inputs':len(parity_inputs[0]),'profile_items':[x['id'] for x in units],'item_split':'dev','GPU_calls':0,'all_stages_smoke':'PASS'});return
 timer=threading.Timer(end-time.time(),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  backend=Backend(ROOT,a.assets,{'gpu_type':'H200'})
  mode=ass.get('profile_mode','all');pairs=read(a.inputs/'CONTINUATIONS.json')[row]['pairs']
  records,units=run_stages(backend,budget,units,pairs,parity_inputs,a.out,mode)
  dump(a.out/'PROFILE_READOUTS.json',records)
  dump(a.out/'PROFILE.json',{'authority':'fc3a9c44; 8c66b004','item_split':'synthetic' if mode=='nla_only_synthetic' else 'dev','profile_mode':mode,'test_items':0,'real_GPU_job':True,'batch_items':8,'readouts_per_item':1,'row':'timing_only' if mode=='nla_only_synthetic' else row,'item_ids':[x['id'] for x in units],'phase_seconds':budget.observed,'completed_epoch':time.time(),'deadline_epoch':end,'scores_used_for_science':False})
  seal(a.out,'PROFILE_SEAL.json',{'source_seal_sha256':ass['source_seal_sha256'],'input_seal_sha256':ass['input_seal_sha256'],'pod_id':ass['pod_id'],'status':'COMPLETE'})
 except BaseException as error:dump(a.out/'FAILURE.json',{'error':str(error)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
