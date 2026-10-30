"""Nine-shard continuation of sealed first-wave captures; no completed pilot replay."""
import sys,json,time,os,threading,signal,shutil
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'e57/job'));sys.path.insert(0,str(HERE.parent/'e56/job'))
from production_joint import preflight as old_preflight,make_jobs,execute_job
from contract56 import read,dump,sha,verify,seal,require
from worker56 import Backend
from admission import atomic,NoFit
import parity_gate
CAPS={'E56':[5949,5948,5948],'E57':[7207,7206,7206],'E61':[6292,6292,6292]}

def selected_jobs(plan,e,shard):return [j for j in plan['jobs'] if j['exp']==e and j['shard']==shard and not j['retained_pilot']]

def check_assignment(a,plan):
 require(a['experiment'] in CAPS and a['shard'] in range(3) and a['gpu_count']==1 and a['fresh_pod'] is True,'nine fresh single GPU shards')
 cap=CAPS[a['experiment']][a['shard']];require(a['cap_seconds']==cap and a['deadline_epoch']==a['pod_created_epoch']+cap,'creation-based approved cap')
 require(a['daily_budget_verified'] is True and 0<=a['projected_daily_USD']<=150,'integrator daily spending gate')
 require(a['plan_sha256']==plan['identity'],'sealed plan assignment');return a['deadline_epoch']

def preflight(a):
 verify(HERE,'SOURCE_SEAL.json',a.source_sha)
 for n,d in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==d,'dependency '+n)
 verify(a.inputs,'INPUT_SEAL.json',a.input_sha);plan=read(a.inputs/'PLAN.json');require(plan['identity']==sha(a.inputs/'PLAN_BODY.json'),'plan identity');ass=read(a.assignment);end=check_assignment(ass,plan)
 require(all(not {'label','value','class'}&x.keys() for j in plan['jobs'] for x in j['units']),'label-free unit metadata')
 for e,slots in plan['capture_seals'].items():
  for slot,digest in slots.items():verify(a.inputs/'captures'/e/slot,'CAPTURE_SEAL.json',digest)
 jobs=selected_jobs(plan,ass['experiment'],ass['shard']);require(jobs,'nonempty shard')
 for j in jobs:
  if j['h_file']:
   h=np.load(a.inputs/j['h_file'],mmap_mode='r');require(h.shape==(len(j['units']),5120) and np.isfinite(h).all(),'frozen activation packet')
 parity=parity_gate.load_inputs({'path':str(a.inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256});read(a.assets)
 return ass,end,plan,jobs,parity

class Clock:
 def __init__(self,out,end):self.out=out;self.end=end;self.events=[]
 def check(self):
  if time.time()>=self.end-60:raise NoFit('retrieval reserve')
 def call(self,key,fn,*args):
  self.check();t=time.monotonic()
  try:v=fn()
  except BaseException:
   self.events.append({'phase':key,'seconds':time.monotonic()-t,'status':'FAILED'});atomic(self.out/'PHASE_TIMINGS.json',self.events);raise
  self.events.append({'phase':key,'seconds':time.monotonic()-t,'status':'COMPLETE'});atomic(self.out/'PHASE_TIMINGS.json',self.events);self.check();return v

def validate_go(go,ready):
 require(go['reader_launch_authorized'] is True and go['pod_id']==ready['pod_id'] and go['plan_sha256']==ready['plan_sha256'] and go['capture_seals']==ready['capture_seals'],'capture-bound GO')
 require(ready['ready_epoch']<=go['issued_epoch']<=time.time(),'GO after sealed capture binding')
 require(go['forecast_commit'].startswith({'E56':'46cd1f4a','E57':'023f715f','E61':'cd77d7d9'}[ready['experiment']]) and len(go['forecast_seal_sha256'])==64,'standing forecast/E61 record')

def execute_remaining(jobs,inputs,backend,clock,out):
 completed=[];remaining=list(jobs);scales={}
 # One load per reader, never a new pilot or recapture. Existing measured timings seed admission.
 for reader in ('oracle','nla'):
  own=[j for j in jobs if j['reader']==reader]
  if not own:continue
  if reader=='nla':clock.call('nla_setup',backend.load_nla)
  for j in own:
   forecast=2*sum(x['measured_seconds']*scales.get(x['phase'],1.) for x in remaining)+(400 if reader=='oracle' and any(x['reader']=='nla' for x in remaining) else 0)+60
   fits=time.time()+forecast<clock.end;atomic(out/'FORECAST.json',{'status':'ADMIT' if fits else 'NO_FIT','remaining_seconds':forecast,'deadline_epoch':clock.end,'completed_jobs':completed,'observed_phase_scales':scales,'prior_margin':2,'deviation':'32c55cb7; caps forecast x1.25, no additional cap multiplier'})
   if not fits:raise NoFit('remaining measured forecast exceeds cap')
   job=dict(j,number=j['resume_number'],h=np.load(inputs/j['h_file']) if j['h_file'] else None)
   clock.call(j['phase'],lambda:execute_job(job,backend,out));scales[j['phase']]=max(scales.get(j['phase'],1.),clock.events[-1]['seconds']/j['measured_seconds']);completed.append(j['key']);remaining.remove(j)
 return completed

def main():
 import argparse
 p=argparse.ArgumentParser()
 for k in ('inputs','assignment','assets','out','go'):p.add_argument('--'+k,type=Path,required=True)
 for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
 p.add_argument('--dry-run',action='store_true');a=p.parse_args();ass,end,plan,jobs,parity=preflight(a);a.out.mkdir(parents=True,exist_ok=False)
 if a.dry_run:
  from test_runtime import smoke
  smoke(a.out/'smoke');dump(a.out/'DRY_RUN.json',{'status':'PASS','experiment':ass['experiment'],'shard':ass['shard'],'unfinished_jobs':len(jobs),'retained_pilots_excluded':True,'GPU_calls':0});return
 clock=Clock(a.out,end);timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  backend=Backend(ROOT,a.assets,{'gpu_type':'H200'});clock.call('oracle_setup',backend.load_oracle);gate=a.out/'parity';gate.mkdir();parity_gate.run_gate(backend,clock,gate,parity)
  ready={'experiment':ass['experiment'],'pod_id':ass['pod_id'],'plan_sha256':plan['identity'],'capture_seals':plan['capture_seals'][ass['experiment']],'ready_epoch':time.time(),'capture_mode':'REBOUND_EXACT_SEALED_FIRST_WAVE','reader_outputs':0};dump(a.out/'CAPTURE_READY.json',ready)
  while not a.go.exists():clock.check();time.sleep(1)
  go=read(a.go);validate_go(go,ready);dump(a.out/'GO_RECEIPT.json',go);dump(a.out/'ASSIGNMENT.json',ass);(a.out/'jobs').mkdir();done=execute_remaining(jobs,a.inputs,backend,clock,a.out)
  dump(a.out/'COMPLETED.json',done);dump(a.out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':end});seal(a.out,'OUTPUT_SEAL.json',{'experiment':ass['experiment'],'shard':ass['shard'],'pod_id':ass['pod_id'],'plan_sha256':plan['identity'],'source_seal_sha256':a.source_sha,'status':'COMPLETE'})
 except NoFit as e:atomic(a.out/'NO_FIT.json',{'status':'NO_FIT','reason':str(e)})
 except BaseException as e:atomic(a.out/'FAILURE.json',{'error':str(e)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
