"""§185–189 acquisition. Only frozen public inputs enter the pod.
All custody (including setup/capture) is capped; no unregistered cap uplift.
"""
import argparse,sys,time,os,signal,threading
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];U=HERE.parent
sys.path.insert(0,str(U/'e62/job'));sys.path.insert(0,str(U/'e57/job'))
from runtime62 import Backend,behaviour,read,dump,sha,verify,seal,require
from admission import Budget as BaseBudget,NoFit,atomic
from budget68 import Budget
from native_nla512 import truncation_summary
CAPS={'E68':5664}
POSITIONS=('registered','midpoint','pre_answer')
ROWS68={'container_after_move','holder_after_handovers','topic_twin'}
ROWS70={'unit_system','var_type_at_use','user_expertise'}
FIELDS={'id','base_item_id','feature','split','text','ids','read_index','position','arm','alpha_token_id','beta_token_id','vector_index','dose','sign','carrier_id','direction_id'}

def validate_items(e,items,full=False):
 require(items and len({x['id'] for x in items})==len(items),'unique nonempty input grid')
 for x in items:
  require(set(x)<=FIELDS,'public fields allowlist; labels/private fields prohibited')
  require(x['split'] in ('dev','test') and isinstance(x['id'],str),'split/identity')
  if e!='E70':
   require(isinstance(x['text'],str) and x['ids'] and all(type(i)is int and i>=0 for i in x['ids']),'frozen text/token IDs')
   require(type(x['read_index'])is int and 0<=x['read_index']<len(x['ids']),'frozen read position')
  if e=='E68':require(x['position'] in POSITIONS and x['feature'] in ROWS68,'E68 frozen row/position')
  if e=='E69':require(x['arm'] in ('own','swap') and x['alpha_token_id']!=x['beta_token_id'] and x['split']=='test','E69 decision/swap')
  if e=='E72':require(x['feature'] in ROWS70 and x['split']=='test','E72 original three rows')
  if e=='E70':
   require(x['split']=='test' and x['sign'] in (-1,1) and type(x['vector_index'])is int and x['vector_index']>=0 and x['carrier_id'] and x['direction_id'],'E70 signed carrier identity')
   require((x['feature'] in ROWS70 and x['dose'] in (1,2,4)) or (x['feature']=='prose_sentiment' and x['dose']==1),'E70 cells')
 if not full:return
 from collections import Counter
 if e=='E68':
  counts=Counter((x['feature'],x['position'],x['split']) for x in items)
  require(all(counts[row,pos,'test']==84 and counts[row,pos,'dev']==84 for row in ROWS68 for pos in POSITIONS),'84 frozen dev and84 ratified test per row/position')
  for row in ROWS68:
   for split in ('dev','test'):
    groups=[{x['base_item_id']:x for x in items if (x['feature'],x['position'],x['split'])==(row,p,split)} for p in POSITIONS]
    require(all(set(g)==set(groups[0]) for g in groups),'same items across positions')
    for k in groups[0]:
     xs=[g[k] for g in groups];require(all(x['ids']==xs[0]['ids'] and x['text']==xs[0]['text'] for x in xs),'same frozen trajectory')
     require(xs[0]['read_index']<=xs[1]['read_index']<=xs[2]['read_index'],'position ordering')
 elif e=='E69':
  for row in {x['feature'] for x in items}:
   groups=[{x['base_item_id'] for x in items if x['feature']==row and x['arm']==a} for a in ('own','swap')]
   require(len(groups[0])==84 and groups[0]==groups[1] and sum(x['feature']==row for x in items)==168,'84 matched own/swap')
 elif e=='E72':require(Counter(x['feature'] for x in items)=={r:84 for r in ROWS70},'E72 3x84')
 elif e=='E70':
  expected={(r,d,s):8 for r in ROWS70|{'prose_sentiment'} for d in ((1,) if r=='prose_sentiment' else (1,2,4)) for s in (-1,1)}
  require(Counter((x['feature'],x['dose'],x['sign']) for x in items)==expected,'E70 eight carrier seeds per signed cell')
  require(len({x['vector_index'] for x in items})==len(items),'unique immutable vector index')

def preflight(a):
 verify(HERE,'SOURCE_SEAL.json',a.source_sha)
 for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'source dependency '+n)
 verify(a.inputs,'INPUT_SEAL.json',a.input_sha);plan=read(a.inputs/'PLAN.json');items=read(a.inputs/'items.json');ass=read(a.assignment);e=plan['experiment'];validate_items(e,items)
 require(e in CAPS and ass['experiment']==e and ass['shard']==plan['shard'],'experiment/shard')
 require(ass['gpu_count']==1 and ass['cap_seconds']==plan['cap_seconds'] and 0<ass['cap_seconds']<=CAPS[e],'sealed cap')
 require(sum(plan['all_shard_caps'])+plan['prior_seconds']<=CAPS[e] and plan['cap_seconds']==plan['all_shard_caps'][plan['shard']],'total registered cap including setup/prior spend')
 require(ass['pod_created_epoch']<=time.time() and ass['absolute_deadline_epoch']==ass['pod_created_epoch']+ass['cap_seconds'],'provider creation clock')
 require(ass['daily_budget_verified'] is True and 0<=ass['projected_daily_USD']<=300,'spend verification')
 require(plan['forecast_required'] is False,'no forecasts for these registrations; no borrowed GO')
 require(plan['item_ids']==[x['id'] for x in items],'exact shard input order');read(a.assets)
 if e=='E70':
  h=np.load(a.inputs/'vectors.npy',allow_pickle=False);require(h.shape==(len(items),5120) and h.dtype==np.float32 and np.isfinite(h).all(),'sealed supplied vectors, unchanged')
 return plan,items,ass

class LateBackend(Backend):
 def capture_at(self,items,layers):
  import torch
  from mats.capture import capture
  self.validate_tokenization(items)
  with self.oracle.base(),torch.no_grad():
   h=capture(self.oracle.model,[x['ids'][:x['read_index']+1] for x in items],layers,[[x['read_index']] for x in items],batch_size=8,pad_id=self.oracle.tok.pad_token_id or 0)
  return {l:h[l][:,0].float().cpu().numpy() for l in layers}

def capture_stage(e,items,backend,budget,out,inputs,binding):
 cap=out/'capture';cap.mkdir();layers=(36,40) if e=='E72' else (42,44)
 if e=='E70':
  h=np.load(inputs/'vectors.npy',allow_pickle=False);acts={l:h for l in layers}
 elif e=='E69':acts={}
 else:
  chunks={l:[] for l in layers}
  for i in range(0,len(items),8):
   got=budget.call('capture',lambda:backend.capture_at(items[i:i+8],layers),e)
   for l in layers:chunks[l].append(got[l])
  acts={l:np.concatenate(v) for l,v in chunks.items()}
 for l,h in acts.items():
  require(h.shape==(len(items),5120) and np.isfinite(h).all(),'capture shape/finiteness');np.save(cap/f'acts{l}.npy',h)
 dump(cap/'items.order.json',[x['id'] for x in items]);dump(cap/'POSITIONS.json',[{k:v for k,v in x.items() if k in ('id','base_item_id','feature','split','position','read_index','vector_index','dose','sign','carrier_id','direction_id')} for x in items]);seal(cap,'CAPTURE_SEAL.json',dict(binding,stage='CAPTURE',forecast_required=False,source='unchanged supplied vectors' if e=='E70' else 'base Qwen'))
 dump(out/'CAPTURE_READY.json',dict(binding,capture_seal_sha256=sha(cap/'CAPTURE_SEAL.json'),reader_outputs=0,forecast_required=False))
 return acts

def jobs_for(e,items,acts):
 jobs=[]
 if e=='E69':
  for x in items:jobs.append(dict(reader='oracle',phase='base_behaviour',units=[x]))
 else:
  for reader in (('oracle',) if e=='E72' else ('oracle','nla')):
   for layer in ((36,40) if e=='E72' else (44 if reader=='oracle' else 42,)):
    ix=[i for i,x in enumerate(items) if x['split']=='test']
    for start in range(0,len(ix),8):
     ids=ix[start:start+8];jobs.append(dict(reader=reader,phase=reader+'_native',source_layer=layer,units=[items[i] for i in ids],h=acts[layer][ids]))
 for i,j in enumerate(jobs):j.update(number=i,exp=e)
 return jobs

def execute(j,b,out):
 if j['phase']=='base_behaviour':
  x=j['units'][0];b.validate_tokenization([x]);records=[dict(behaviour(b,x),arm=x['arm'])]
 else:
  before=j['h'].tobytes();groups=b.native_one(j['reader'],j['h']);require(j['h'].tobytes()==before,'adapter input unchanged')
  require(len(groups)==len(j['units']) and all(len(g)==1 for g in groups),'one greedy per unit')
  records=[dict(**{k:v for k,v in x.items() if k not in ('text','ids')},reader=j['reader'],source_layer=j['source_layer'],reader_native_layer=44 if j['reader']=='oracle' else 42,repeat=0,off_distribution=j['exp']=='E72',**g[0]) for x,g in zip(j['units'],groups)]
 atomic(out/'jobs'/f'{j["number"]:06d}.json',records);return records

def run_jobs(jobs,b,budget,out):
 # Retain pilots and admit each resident reader stage. No unnecessary model reload.
 results={}
 for reader in ('oracle','nla'):
  group=[j for j in jobs if j['reader']==reader]
  if not group:continue
  if reader=='nla':budget.call('nla_setup',b.load_nla)
  seen={}
  for j in group:
   if seen.get(j['phase'],0)>=2:continue
   results[j['number']]=budget.call(j['phase'],lambda j=j:execute(j,b,out),j['exp']);seen[j['phase']]=seen.get(j['phase'],0)+1
  # Forecast this stage using real jobs; the next stage must independently admit.
  stage_results={i:results[j['number']] for i,j in enumerate(group) if j['number'] in results}
  budget.forecast(jobs,results,False)
  for i,j in enumerate(group):
   if j['number'] in results:continue
   results[j['number']]=budget.call(j['phase'],lambda j=j:execute(j,b,out),j['exp']);stage_results[i]=results[j['number']];budget.forecast(jobs,results,False)
  atomic(out/(reader+'_STAGE.json'),{'status':'COMPLETE','job_numbers':[j['number'] for j in group]})
 return results

def acquire(plan,items,b,budget,out,inputs,binding):
 e=plan['experiment'];budget.call('oracle_setup',b.load_oracle)
 acts=capture_stage(e,items,b,budget,out,inputs,binding);jobs=jobs_for(e,items,acts);(out/'jobs').mkdir();dump(out/'JOB_GRID.json',[{k:v for k,v in j.items() if k!='h'} for j in jobs]);results=run_jobs(jobs,b,budget,out)
 records=[x for i in sorted(results) for x in results[i]];dump(out/'RECORDS.json',records);dump(out/'NLA_TRUNCATION.json',truncation_summary([x for x in records if x.get('reader')=='nla']))
 seal(out,'OUTPUT_SEAL.json',dict(binding,status='COMPLETE',capture_seal_sha256=sha(out/'capture/CAPTURE_SEAL.json')))

def main():
 p=argparse.ArgumentParser()
 for k in ('inputs','assignment','assets','out'):p.add_argument('--'+k,type=Path,required=True)
 for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
 p.add_argument('--dry-run',action='store_true');a=p.parse_args();plan,items,ass=preflight(a);a.out.mkdir(parents=True,exist_ok=False)
 if a.dry_run:
  from test_worker import smoke
  smoke(a.out/'smoke',plan['experiment']);dump(a.out/'DRY_RUN.json',{'status':'PASS','experiment':plan['experiment'],'model_loading':'stubbed','production_GPU_calls':0});return
 end=ass['absolute_deadline_epoch'];timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();budget=Budget(a.out,{plan['experiment']:ass['cap_seconds']},end,read(HERE/'SEED_TIMINGS.json'));dump(a.out/'ASSIGNMENT.json',ass)
 try:acquire(plan,items,LateBackend(ROOT,a.assets,{'gpu_type':'H200'}),budget,a.out,a.inputs,dict(experiment=plan['experiment'],shard=plan['shard'],pod_id=ass['pod_id'],source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,bank_seal_sha256=plan['bank_seal_sha256']))
 except NoFit as error:atomic(a.out/'NO_FIT.json',{'status':'NO_FIT','reason':str(error),'pilots_retained':True,'no_retry_authorized':True})
 except BaseException as error:atomic(a.out/'FAILURE.json',{'error':str(error)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
