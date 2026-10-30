"""Follow-on shard-per-bank acquisition; original native/scoring functions, separate staging and GO clock."""
import sys,time,threading,signal,os,argparse,re
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];U=HERE.parent
sys.path.insert(0,str(U/'e62/job'));sys.path.insert(0,str(U/'e57/job'));sys.path.insert(0,str(U/'joint9'))
from runtime import Clock
from second_worker import Backend,read,dump,sha,verify,seal,require,parity_gate,jobs_for,execute
from admission import Budget,NoFit,atomic,admit_and_run
COHORT='joint-a7fea77c-7279007d';CAPS={'E59':7200,'E63':2880,'D4A':1080}

def preflight(a):
 verify(HERE,'SOURCE_SEAL.json',a.source_sha)
 for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'dependency '+n)
 verify(a.inputs,'INPUT_SEAL.json',a.input_sha);plan=read(a.inputs/'SHARD.json');ass=read(a.assignment);e=plan['experiment'];require(e in CAPS and ass['experiment']==e and ass['shard']==0 and ass['gpu_count']==1 and ass['cohort_id']==COHORT,'follow-on shard/cohort')
 require(ass['prior_compute_seconds']>=0 and ass['compute_cap_seconds']+ass['prior_compute_seconds']==CAPS[e] and ass['compute_cap_seconds']>0,'registered 2x including prior compute')
 require(ass['staging_cap_seconds']==900 and ass['pod_created_epoch']<=ass['staging_start_epoch'] and ass.get('go_wait_cap_seconds',0)==(2700 if e=='E59' else 0) and ass['absolute_deadline_epoch']==ass['staging_start_epoch']+900+ass.get('go_wait_cap_seconds',0)+ass['compute_cap_seconds'],'fixed staging plus compute deadline')
 require(ass['daily_budget_verified'] is True and 0<=ass['projected_daily_USD']<=300,'daily USD300 ceiling')
 dep=read(a.inputs/'DEPENDENCY_CONTRACT.json');proof=ass['dependency_receipt'];require(proof['verified'] is True and proof['cohort_id']==COHORT and len(proof['E57_output_seals'])==3 and all(re.fullmatch('[0-9a-f]{64}',h) for h in proof['E57_output_seals']),'verified E57 complete before launch')
 if e=='D4A':require(len(proof['E61_D4_stage_seals'])==3 and all(re.fullmatch('[0-9a-f]{64}',h) for h in proof['E61_D4_stage_seals']),'existing D4 outputs/probabilities required, not reacquired')
 items=read(a.inputs/'items.json');require(len(items)==plan['capture_items'] and len({x['id'] for x in items})==len(items) and all(not {'label','value','class'}&x.keys() for x in items),'own frozen label-free items')
 state={'items':items,'inputs':a.inputs}
 if e=='E59':state['plan']=read(a.inputs/'PLAN.json')
 if e=='D4A':read(a.inputs/'LEXICON.json')
 if e=='E63':
  state['random']=np.load(a.inputs/'random.npy');require(state['random'].shape==(200,5120) and state['random'].dtype==np.float32 and np.isfinite(state['random']).all(),'unchanged Gaussian pool');read(a.inputs/'POOL_SELECTION.json')
 read(a.assets);parity=parity_gate.load_inputs({'path':str(a.inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256});return ass,e,state,parity

def capture(state,backend,clock,out,e,input_sha):
 xs=state['items'];backend.validate_tokenization(xs)
 if e=='D4A':
  for x in xs:
   if x['split']=='test':require(backend.oracle.tok.encode(x['completion_text'],add_special_tokens=False)==x['completion_ids'] and backend.oracle.tok.encode(x['answer_text'],add_special_tokens=False)==[x['answer_token_id']],'D4a frozen tokens')
 cap=out/'capture';cap.mkdir();parts={42:[],44:[]}
 for start in range(0,len(xs),8):
  values=clock.call(e+'_capture',lambda:backend.capture(xs[start:start+8]))
  for l in parts:parts[l].append(values[l])
 state['acts']={l:np.concatenate(v) for l,v in parts.items()}
 for l,h in state['acts'].items():require(h.shape==(len(xs),5120) and np.isfinite(h).all(),'capture grid');np.save(cap/f'acts{l}.npy',h)
 dump(cap/'items.order.json',[x['id'] for x in xs]);seal(cap,'CAPTURE_SEAL.json',{'experiment':e,'cohort_id':COHORT,'input_seal_sha256':input_sha,'layers':[42,44],'D4A_dev_and_test':e=='D4A'});return cap

class GoTimeout(Exception):pass

def go_deadline(ready,ass):
 return ready['ready_epoch']+2700 if ass.get('experiment')=='E59' else ass['staging_start_epoch']+900

def wait_go(path,ready,ass):
 end=go_deadline(ready,ass)
 while True:
  if time.time()>end:raise GoTimeout('No valid GO within the post-capture window; NOT RUN today (55833480)')
  if path.exists():return read(path)
  time.sleep(min(1,max(0,end-time.time())))

def go_end(go,ready,ass):
 for k in ('pod_id','cohort_id','capture_seals','input_seals'):require(go[k]==ready[k],'GO '+k)
 require(go['reader_launch_authorized'] is True and ready['ready_epoch']<=go['issued_epoch']<=time.time() and go['issued_epoch']<=go_deadline(ready,ass),'GO after capture within authorized window')
 require(re.fullmatch('[0-9a-f]{40}',go['forecast_commit']) and re.fullmatch('[0-9a-f]{64}',go['forecast_seal_sha256']),'committed forecast or coordinator record')
 return go['issued_epoch']+ass['compute_cap_seconds']

def main():
 p=argparse.ArgumentParser()
 for k in ('inputs','assignment','assets','out','go'):p.add_argument('--'+k,type=Path,required=True)
 for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
 p.add_argument('--dry-run',action='store_true');a=p.parse_args();ass,e,state,parity=preflight(a);a.out.mkdir(exist_ok=False,parents=True)
 if a.dry_run:
  from test_worker import smoke
  smoke(a.out/'smoke',e);dump(a.out/'DRY_RUN.json',{'status':'PASS','experiment':e,'shard':0,'GPU_calls':0});return
 end=ass['staging_start_epoch']+900;clock=Clock(a.out,end);timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  b=Backend(ROOT,a.assets,{'gpu_type':'H200'});clock.call('oracle_setup',b.load_oracle);gate=a.out/'parity';gate.mkdir();parity_gate.run_gate(b,clock,gate,parity);cap=capture(state,b,clock,a.out,e,a.input_sha);ready={'pod_id':ass['pod_id'],'cohort_id':COHORT,'capture_seals':{e:sha(cap/'CAPTURE_SEAL.json')},'input_seals':{e:a.input_sha},'ready_epoch':time.time()};dump(a.out/'CAPTURE_READY.json',ready)
  require(ready['ready_epoch']<=ass['staging_start_epoch']+900,'capture completed inside staging cap')
  if e=='E59':timer.cancel() # Idle wait charged to custody; compute still starts only at GO.
  dump(a.out/'GO_WAIT.json',{'capture_ready_epoch':ready['ready_epoch'],'go_deadline_epoch':go_deadline(ready,ass),'idle_charged_to_spend':True})
  if e=='E59':go=wait_go(a.go,ready,ass)
  else:
   while not a.go.exists():clock.check();time.sleep(1)
   go=read(a.go)
  end=go_end(go,ready,ass);timer.cancel();timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();dump(a.out/'GO_RECEIPT.json',go);dump(a.out/'ASSIGNMENT.json',ass)
  dump(a.out/'GO_WAIT_TIMING.json',{'capture_ready_epoch':ready['ready_epoch'],'ended_epoch':time.time(),'idle_seconds':time.time()-ready['ready_epoch'],'charged_to_spend':True})
  # New budget begins at GO. Staging timings remain independently sealed and charged.
  dump(a.out/'STAGING_TIMINGS.json',clock.events);budget=Budget(a.out,{e:ass['compute_cap_seconds']},end,read(HERE/'SEED_TIMINGS.json'));jobs=jobs_for({e:state});(a.out/'jobs').mkdir();dump(a.out/'JOB_GRID.json',[{k:v for k,v in j.items() if k!='h'} for j in jobs]);results=admit_and_run(jobs,b,budget,lambda j:execute(j,b,a.out))
  dump(a.out/'COMPLETED.json',sorted(results));dump(a.out/'TIMING.json',{'completed_epoch':time.time(),'compute_from_GO':go['issued_epoch'],'deadline_epoch':end});seal(a.out,'OUTPUT_SEAL.json',{'status':'COMPLETE','experiment':e,'shard':0,'cohort_id':COHORT,'source_seal_sha256':a.source_sha,'input_seal_sha256':a.input_sha,'pod_id':ass['pod_id'],'capture_seal_sha256':sha(cap/'CAPTURE_SEAL.json')})
 except GoTimeout as error:
  atomic(a.out/'NOT_RUN.json',{'reason':str(error),'reader_outputs':0,'capture_ready_epoch':ready['ready_epoch'],'ended_epoch':time.time(),'idle_seconds':time.time()-ready['ready_epoch'],'charged_to_spend':True});dump(a.out/'STAGING_TIMINGS.json',clock.events);seal(a.out,'OUTPUT_SEAL.json',{'status':'NOT RUN','experiment':e,'cohort_id':COHORT,'source_seal_sha256':a.source_sha,'input_seal_sha256':a.input_sha,'capture_seal_sha256':sha(cap/'CAPTURE_SEAL.json')})
 except NoFit as error:atomic(a.out/'NO_FIT.json',{'reason':str(error),'pilot_outputs_retained':True})
 except BaseException as error:atomic(a.out/'FAILURE.json',{'error':str(error)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
