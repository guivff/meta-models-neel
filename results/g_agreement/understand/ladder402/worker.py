"""402be5f0: shard-local inputs, staging deadline, GO compute clock, separately sealed stages."""
import sys,time,threading,signal,os,argparse
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'joint9'))
from runtime import Clock,NoFit,Backend,parity_gate,execute_job,read,dump,sha,verify,seal,require,atomic
sys.path.insert(0,str(HERE.parent/'e62/job'))
from second_worker import execute as execute_job
COHORT='joint-a7fea77c-7279007d'
def preflight(a):
 verify(HERE,'SOURCE_SEAL.json',a.source_sha)
 for n,d in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==d,'dependency '+n)
 verify(a.inputs,'INPUT_SEAL.json',a.input_sha);plan=read(a.inputs/'PLAN.json');ass=read(a.assignment)
 require(ass['cohort_id']==plan['cohort_id']==COHORT and ass['experiment']==plan['experiment'] and ass['shard']==plan['shard'],'cohort/shard identity')
 require(ass['compute_cap_seconds']==plan['compute_cap_seconds'] and ass['staging_cap_seconds']==900 and ass['gpu_count']==1,'fixed caps')
 require(ass['daily_budget_verified'] is True and 0<=ass['projected_daily_USD']<=300,'daily spending gate')
 require(ass['plan_sha256']==sha(a.inputs/'PLAN.json'),'plan binding')
 require(ass['staging_start_epoch']==ass['pod_created_epoch'] and ass['absolute_deadline_epoch']==ass['staging_start_epoch']+900+ass['compute_cap_seconds'],'staging-plus-compute outer deadline')
 require(all(j['reader']=='oracle' for j in plan['jobs']),'Oracle-only ladder')
 for j in plan['jobs']:
  require(all(not {'label','value','class'}&x.keys() for x in j['units']),'no private unit labels')
  if j['h_file']:
   h=np.load(a.inputs/j['h_file'],mmap_mode='r');require(h.shape==(len(j['units']),5120) and np.isfinite(h).all(),'packet')
 parity=parity_gate.load_inputs({'path':str(a.inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256});read(a.assets)
 return ass,plan,parity

def validate_go(go,ready,ass):
 for k in ('pod_id','cohort_id','plan_sha256','capture_seals'):require(go[k]==ready[k],'GO '+k)
 require(go['reader_launch_authorized'] is True and ready['ready_epoch']<=go['issued_epoch']<=time.time(),'GO after capture binding')
 require(go['issued_epoch']<=ass['pod_created_epoch']+900,'15 minute staging deadline')
 expected={'E62':'b6203308','E62P':'fb26a098'}[ass['experiment']]
 require(go['forecast_commit'].startswith(expected),'standing forecast/record')
 return go['issued_epoch']+ass['compute_cap_seconds']

def stages(plan):return ['D4','D3'] if plan['experiment']=='E61' else [plan['experiment']]

def run_stages(plan,inp,backend,clock,out,receipt):
 nla_loaded=False;scales={}
 for stage in stages(plan):
  if stage=='D3' and nla_loaded:
   # NativeBackend.load_nla releases Oracle; restore it before D3 Oracle.
   import gc,torch
   backend.nla=None;gc.collect();torch.cuda.empty_cache();clock.call('oracle_reload_D3',backend.load_oracle);nla_loaded=False
  dest=out/stage;dest.mkdir();(dest/'jobs').mkdir();jobs=[j for j in plan['jobs'] if j['stage']==stage];done=[];omitted=[]
  for reader in ('oracle','nla'):
   own=[j for j in jobs if j['reader']==reader]
   if not own:continue
   future=[j for j in jobs if j['key'] not in done]
   estimate=2*sum(j['measured_seconds']*scales.get(j['phase'],1) for j in future)+(700 if not nla_loaded and any(j['reader']=='nla' for j in future) else 0)+60
   if stage=='D3' and reader=='oracle' and time.time()+estimate>=clock.end:
    omitted=[j['key'] for j in jobs if j['reader']=='nla'];future=[j for j in future if j['reader']=='oracle']
   if reader=='nla' and omitted:continue
   if reader=='nla' and not nla_loaded:
    estimate=2*sum(j['measured_seconds']*scales.get(j['phase'],1) for j in own)+700+60
    if time.time()+estimate>=clock.end:
     if stage=='D3':omitted=[j['key'] for j in own];continue
     raise NoFit('D4 NLA does not fit compute cap')
    clock.call('nla_setup',backend.load_nla);nla_loaded=True
   for j in own:
    pending=[x for x in jobs if x['key'] not in done+omitted]
    estimate=2*sum(x['measured_seconds']*scales.get(x['phase'],1) for x in pending)+(700 if not nla_loaded and any(x['reader']=='nla' for x in pending) else 0)+60
    fits=time.time()+estimate<clock.end
    atomic(out/'FORECAST.json',{'stage':stage,'remaining_seconds':estimate,'fits':fits,'compute_deadline':clock.end,'omitted_D3_NLA_jobs':omitted,'compute_from_GO':True})
    if not fits:raise NoFit(stage+' remaining compute exceeds cap')
    job=dict(j,number=j['number'],h=np.load(inp/j['h_file']) if j['h_file'] else None)
    clock.call(j['phase'],lambda:execute_job(job,backend,dest));done.append(j['key']);scales[j['phase']]=max(scales.get(j['phase'],1),clock.events[-1]['seconds']/j['measured_seconds'])
  dump(dest/'COMPLETED.json',done);dump(dest/'NOT_RUN.json',omitted);dump(dest/'RECEIPT.json',dict(receipt,completed_epoch=time.time(),compute_deadline=clock.end))
  seal(dest,'STAGE_SEAL.json',{'status':'COMPLETE' if not omitted else 'ORACLE_ONLY','stage':stage,'cohort_id':COHORT,'plan_sha256':receipt['plan_sha256'],'NLA':'NOT RUN per 402be5f0','retained_pilots_required':[j for j in plan['retained_pilots'] if j['stage']==stage]})
  atomic(out/(stage+'_READY.json'),{'stage':stage,'stage_seal_sha256':sha(dest/'STAGE_SEAL.json'),'pull_immediately':True,'stage_path':str(dest)})

def main():
 p=argparse.ArgumentParser()
 for k in ('inputs','assignment','assets','out','go'):p.add_argument('--'+k,type=Path,required=True)
 for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
 p.add_argument('--dry-run',action='store_true');a=p.parse_args();ass,plan,parity=preflight(a);a.out.mkdir(exist_ok=False,parents=True)
 if a.dry_run:
  from test_worker import smoke
  smoke(a.out/'smoke');dump(a.out/'DRY_RUN.json',{'status':'PASS','GPU_calls':0,'experiment':plan['experiment'],'shard':plan['shard']});return
 staging_end=ass['pod_created_epoch']+900;clock=Clock(a.out,staging_end);timer=threading.Timer(max(0,staging_end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  backend=Backend(ROOT,a.assets,{'gpu_type':'H200'});clock.call('oracle_setup',backend.load_oracle);gate=a.out/'parity';gate.mkdir();parity_gate.run_gate(backend,clock,gate,parity)
  ready={'pod_id':ass['pod_id'],'cohort_id':COHORT,'plan_sha256':sha(a.inputs/'PLAN.json'),'capture_seals':plan['capture_seals'],'ready_epoch':time.time(),'capture_mode':'REUSE_EXACT_VERIFIED_CAPTURE_PACKETS'};dump(a.out/'CAPTURE_READY.json',ready)
  while not a.go.exists():clock.check();time.sleep(1)
  go=read(a.go);end=validate_go(go,ready,ass);timer.cancel();timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();clock.end=end
  dump(a.out/'GO_RECEIPT.json',go);dump(a.out/'ASSIGNMENT.json',ass)
  receipt=dict(assignment=ass,go=go,capture_ready=ready,plan_sha256=ready['plan_sha256'],input_sha256=a.input_sha,source_sha256=a.source_sha,parity_sha256=sha(gate/'PARITY_RESULT.json'),parity_status=read(gate/'PARITY_RESULT.json')['status'])
  run_stages(plan,a.inputs,backend,clock,a.out,receipt)
  seal(a.out,'OUTPUT_SEAL.json',{'status':'COMPLETE','cohort_id':COHORT,'experiment':plan['experiment'],'shard':plan['shard']})
 except NoFit as e:atomic(a.out/'NO_FIT.json',{'reason':str(e),'completed_stage_seals_stand':True})
 except BaseException as e:atomic(a.out/'FAILURE.json',{'error':str(e)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
