"""Second-wave stage: E62 all-position capture, E59 plans, shared E63 pools."""
import argparse,sys,time,threading,os,signal,json,math,shutil
from pathlib import Path
import numpy as np
from runtime62 import HERE,E56,ROOT,read,dump,verify,sha,seal,require,Backend,readout_records,acquire_capture,behaviour
sys.path.insert(0,str(HERE.parents[1]/'e57/job'))
from admission import Budget,NoFit,atomic,admit_and_run
from production_joint import validate_go,execute_job
from native_nla512 import truncation_summary
import parity_gate
REGISTERED={'E62':7200,'E62P':2160,'E59':3600,'E63':1440,'D4A':540}
GROUPS=({'E62','E62P'},{'E59','E63','D4A'})

def allocation(a):
 require(a['gpu_count']==1,'single-GPU stage')
 if set(a['caps'])==GROUPS[0]:require(a.get('fresh_dedicated_pod') is True and not a.get('existing_pod',False),'ladder fresh dedicated pod')
 else:require(a.get('existing_pod') is True and not a.get('fresh_dedicated_pod',False),'auxiliary stage on first freed joint slot')
 require(set(a['caps']) in GROUPS and set(a['caps'])==set(a['prior_custody_seconds']),'complete allocation ledger')
 for e,v in a['caps'].items():
  prior=a['prior_custody_seconds'][e]
  require(isinstance(v,(float,int)) and math.isfinite(v) and v>0 and math.isfinite(prior) and prior>=0 and v+prior<=2*REGISTERED[e],'cumulative 2x cap')
 if set(a['caps'])==GROUPS[0]:require(a['pod_created_epoch']==a['custody_start_epoch'],'ladder clock starts at provider creation')
 require(a['pod_created_epoch']<=a['custody_start_epoch']<=time.time(),'fixed custody start no later than now')
 end=a['custody_start_epoch']+sum(a['caps'].values());require(end==a['absolute_deadline_epoch'] and end<=a['provider_deadline_epoch'],'fixed provider custody deadline')
 return a['caps'],end

def preflight(a):
 ass=read(a.assignment);caps,end=allocation(ass);states={}
 for e in REGISTERED:
  if e not in caps:continue
  path=getattr(a,e.lower()+'_inputs');require(path is not None,'bound amendment archive');job=HERE if e in ('E62P','D4A') else HERE.parents[1]/e.lower()/'job';verify(job,'SOURCE_SEAL.json',ass['source_seals'][e]);verify(path,'INPUT_SEAL.json',ass['input_seals'][e])
  for name,digest in read(job/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'dependency '+name)
  items=read(path/'items.json');require(all(not {'label','value','class'}&x.keys() for x in items),'no labels on pod')
  state=dict(inputs=path,items=items,source=ass['source_seals'][e],input_sha=ass['input_seals'][e])
  if e=='E62':
   from bind62 import validate_full_grid
   validate_full_grid(items)
  elif e=='E62P':
   require(len(items)==2520,'15 placebo cells x168')
   from amendment_inputs import validate_placebo
   validate_placebo(items)
  elif e=='D4A':
   from amendment_inputs import validate_d4a
   validate_d4a(items);state['lexicon']=read(path/'LEXICON.json')
  elif e=='E59':
   require(len(items)==1008 and len({x['id'] for x in items})==1008,'plan bank grid')
   state.update(plan=read(path/'PLAN.json'))
  else:
   state['random']=np.load(path/'random.npy');require(state['random'].shape==(200,5120) and state['random'].dtype==np.float32 and np.isfinite(state['random']).all(),'Gaussian pool')
   require(len(items)==200 and len({x['id'] for x in items})==200,'real pool grid');read(path/'POOL_SELECTION.json')
  states[e]=state
 read(a.assets);parity=parity_gate.load_inputs({'path':str(a.e62_inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256})
 require(len(ass['parent_request_sha256'])==64 and len(ass['cohort_id'])>0,'same-run first wave binding')
 return ass,caps,end,states,parity

class CaptureBudget:
 def __init__(self,b,e='E62'):self.b=b;self.e=e
 def call(self,key,fn,left=0):return self.b.call(key,fn,self.e)

def capture_all(states,backend,budget,out,ass,parity):
 budget.call('oracle_setup',backend.load_oracle);gate=out/'parity';gate.mkdir();parity_gate.run_gate(backend,budget,gate,parity)
 for e,s in states.items():
  root=out/e.lower();root.mkdir();s['out']=root;dump(root/'ASSIGNMENT.json',ass)
  binding={'source_seal_sha256':s['source'],'input_seal_sha256':s['input_sha'],'pod_id':ass['pod_id'],'cohort_id':ass['cohort_id'],'experiment':e}
  if e in ('E62','E62P'):cap=acquire_capture(s['items'],backend,CaptureBudget(budget,e),root,binding)
  else:
   backend.validate_tokenization(s['items'])
   if e=='D4A':
    for x in s['items']:
     if x['split']!='test':continue
     require(backend.oracle.tok.encode(x['completion_text'],add_special_tokens=False)==x['completion_ids'] and backend.oracle.tok.encode(x['answer_text'],add_special_tokens=False)==[x['answer_token_id']],'D4a frozen completion/answer tokens')
   cap=root/'capture';cap.mkdir();parts={42:[],44:[]}
   for start in range(0,len(s['items']),8):
    h=budget.call(e+'_capture',lambda:backend.capture(s['items'][start:start+8]),e)
    for l in parts:parts[l].append(h[l])
   for l,v in parts.items():
    h=np.concatenate(v);require(h.shape==(len(s['items']),5120) and np.isfinite(h).all(),'capture shape');np.save(cap/f'acts{l}.npy',h)
   dump(cap/'items.order.json',[x['id'] for x in s['items']]);seal(cap,'CAPTURE_SEAL.json',binding)
  s['cap']=cap;s['acts']={l:np.load(cap/f'acts{l}.npy',mmap_mode='r') for l in (42,44)}
 ready={'pod_id':ass['pod_id'],'captured_epoch':time.time(),'cohort_id':ass['cohort_id'],'capture_seals':{e:sha(s['cap']/'CAPTURE_SEAL.json') for e,s in states.items()},'input_seals':{e:s['input_sha'] for e,s in states.items()},'reader_outputs':0}
 dump(out/'CAPTURE_READY.json',ready);return ready

def jobs_for(states):
 jobs=[]
 def add(e,r,kind,units,h=None,**kw):jobs.append(dict(exp=e,reader=r,kind=kind,units=units,h=h,phase=e+'_'+r+('_native' if kind in ('native','pool') else '_'+kind),**kw))
 for reader in ('oracle','nla'):
  l=44 if reader=='oracle' else 42
  for e,s in states.items():
   items=s['items'];h=s['acts'][l]
   if e=='E63':
    for arm in ('random','shuffled'):
     vectors=s['random'] if arm=='random' else h
     for start in range(0,200,8):add(e,reader,'pool',[{'id':f'{arm}:{i:03d}'} for i in range(start,min(start+8,200))],vectors[start:start+8].copy(),arm=arm)
    continue
   ix=[i for i,x in enumerate(items) if x['split']=='test' and not x.get('reuse_first_wave',False)]
   for start in range(0,len(ix),8):
    ids=ix[start:start+8];add(e,reader,'native',[items[i] for i in ids],h[ids])
   if e in ('E62','E62P','D4A') and reader=='oracle':
    for i in ix:
     if e=='D4A':add(e,reader,'d4base',[items[i]])
     elif items[i]['rung'] in ('L4','L4p'):add(e,reader,'behaviour',[items[i]])
   if e=='E59':
    index={x['id']:i for i,x in enumerate(items)}
    for row,pairs in s['plan']['continuation_pairs'].items():
     if pairs is None:continue
     selected=[i for i in ix if items[i]['feature']==row]
     for start in range(0,len(selected),8):
      ids=selected[start:start+8];xs=[items[i] for i in ids]
      for arm in ('own','swap'):
       pos=ids if arm=='own' else [index[s['plan']['donors'][x['id']]] for x in xs]
       add(e,reader,'continuation',xs,h[pos],pairs=pairs,arm=arm)
 for i,j in enumerate(jobs):j['number']=i
 return jobs

def execute(j,backend,out):
 if j['kind']=='d4base':
  sys.path.insert(0,str(HERE.parents[1]/'e61/job'))
  from runtime61 import base_answer_probability
  v=[base_answer_probability(backend,j['units'][0])]
 elif j['kind']=='behaviour':v=[behaviour(backend,j['units'][0])]
 elif j['kind']=='pool':
  before=j['h'].tobytes();groups=backend.native_one(j['reader'],j['h']);require(len(groups)==len(j['units']) and all(len(g)==1 for g in groups),'pool readout grid')
  v=[dict(pool=j['arm'],vector_id=x['id'],reader=j['reader'],layer=44 if j['reader']=='oracle' else 42,repeat=0,**g[0]) for x,g in zip(j['units'],groups)];require(j['h'].tobytes()==before,'pool mutation')
 else:return execute_job(j,backend,out)
 dump(out/'jobs'/f'{j["number"]:06d}.json',v);return v

def finish(states,jobs,results,out,budget,ass,go):
 for e,s in states.items():
  root=s['out'];native={r:[] for r in ('oracle','nla')};cont={r:[] for r in native};base=[]
  for i,j in enumerate(jobs):
   if j['exp']!=e:continue
   if j['kind'] in ('behaviour','d4base'):base+=results[i]
   elif j['kind']=='continuation':cont[j['reader']]+=results[i]
   else:native[j['reader']]+=results[i]
  for reader,records in native.items():
   name=reader+('.jsonl' if e=='E63' else '.native.jsonl')
   with (root/name).open('x') as f:
    for x in records:f.write(json.dumps(x,allow_nan=False)+'\n')
   if e=='E59':dump(root/(reader+'.continuation.json'),cont[reader])
  if e in ('E62','E62P'):dump(root/'BEHAVIOUR.json',base)
  if e=='D4A':dump(root/'BASE_PROBABILITIES.json',base)
  dump(root/'NLA_TRUNCATION.json',truncation_summary(native['nla'],row_key='pool' if e=='E63' else 'feature'))
  dump(root/'GO_RECEIPT.json',go);dump(root/'ADMISSION.json',read(out/'FORECAST.json'));dump(root/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':budget.end})
  shutil.copytree(out/'parity',root/'parity')
  dump(root/'PARITY_REUSE.json',{'parity_result_sha256':sha(out/'parity/PARITY_RESULT.json'),'status':'PASS'})
  seal(root,'OUTPUT_SEAL.json',{'experiment':e,'status':'COMPLETE','pod_id':ass['pod_id'],'source_seal_sha256':s['source'],'input_seal_sha256':s['input_sha'],'cohort_id':ass['cohort_id'],'parent_request_sha256':ass['parent_request_sha256']})

def main():
 p=argparse.ArgumentParser()
 for k in ('assignment','e62-inputs','assets','out','go'):p.add_argument('--'+k,type=Path,required=True)
 for k in ('e59-inputs','e63-inputs','e62p-inputs','d4a-inputs'):p.add_argument('--'+k,type=Path)
 p.add_argument('--dry-run',action='store_true');a=p.parse_args();ass,caps,end,states,parity=preflight(a);a.out.mkdir(parents=True,exist_ok=False)
 if a.dry_run:
  from smoke_second import smoke
  smoke(a.out/'smoke',experiments=set(states));dump(a.out/'DRY_RUN.json',{'experiments':list(states),'status':'PASS','preflight':'REAL','all_stages':'TINY_MODEL','GPU_calls':0});return
 seed=read(E56/'SAVED_ORACLE_TIMINGS.json')['completed_phase_seconds'];budget=Budget(a.out,caps,end,seed);timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  backend=Backend(ROOT,a.assets,{'gpu_type':'H200'});ready=capture_all(states,backend,budget,a.out,ass,parity)
  while not a.go.exists():budget.check();time.sleep(1)
  go=read(a.go);validate_go(go,ready);require(go['cohort_id']==ass['cohort_id'],'cohort GO');dump(a.out/'GO_RECEIPT.json',go);(a.out/'jobs').mkdir()
  jobs=jobs_for(states);results=admit_and_run(jobs,backend,budget,lambda j:execute(j,backend,a.out));finish(states,jobs,results,a.out,budget,ass,go)
 except NoFit as e:
  previous=read(a.out/'FORECAST.json') if (a.out/'FORECAST.json').exists() else {}
  atomic(a.out/'FORECAST.json',dict(previous,status='NO_FIT',reason=str(e)));atomic(a.out/'NO_FIT.json',{'status':'NO_FIT','reason':str(e),'observed':budget.observed})
 except BaseException as e:atomic(a.out/'FAILURE.json',{'error':str(e)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
