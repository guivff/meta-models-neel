"""Capture all assigned experiments before GO; retain pilot jobs and self-admit readers."""
import argparse,sys,time,threading,os,signal,json,re
from pathlib import Path
import numpy as np
from runtime57 import HERE,E56,validate_plan
from contract56 import ROOT,read,dump,verify,sha,seal,require,BANK_SHA
from worker56 import Backend,readout_records
from admission import Budget,NoFit,atomic,validate_allocation,admit_and_run
from counts57 import count_item
from native_nla512 import truncation_summary
import parity_gate
sys.path.insert(0,str(HERE.parents[1]/'e61/job'))
from runtime61 import position_jobs,base_answer_probability

def preflight(a):
 ass=read(a.assignment);caps,end=validate_allocation(ass);states={}
 for e,path in [('E56',a.e56_inputs),('E57',a.e57_inputs),('E61',a.e61_inputs)]:
  if e not in caps:continue
  require(path is not None,'required input archive');job=HERE.parents[1]/e.lower()/'job';prefix='' if e=='E56' else e.lower()+'_'
  verify(job,'SOURCE_SEAL.json',ass[prefix+'source_seal_sha256']);verify(path,'INPUT_SEAL.json',ass[prefix+'input_seal_sha256'])
  for name,digest in read(job/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'dependency '+name)
  require(not (path/'dev_labels.json').exists(),'labels must remain on CPU');items=read(path/'items.json');require(all(not {'label','value'}&x.keys() for x in items),'label-free items')
  s={'inputs':path,'source':ass[prefix+'source_seal_sha256'],'input_sha':ass[prefix+'input_seal_sha256'],'all_items':items}
  if e=='E56':
   plan=read(path/'SHARDS.json');rows=plan['rows'][str(ass['slot'])];s.update(plan=plan,samples=read(path/'SAMPLING.json')['native_ids'],cont=read(path/'CONTINUATIONS.json'),donors=read(path/'DONORS.json'),injection=read(path/'injection/ITEMS.json')['items'],vectors=np.load(path/'injection/INPUT_VECTORS.npz')['activations'])
  elif e=='E57':
   plan=read(path/'RUN_PLAN.json');validate_plan(plan,items,None);rows=plan['shards'][str(ass['slot'])];s.update(plan=plan,samples=plan['native_ids'])
  else:rows=None
  s['items']=[x for x in items if rows is None or x['feature'] in rows];s['rows']=rows;s['capture_items']=position_jobs(s['items']) if e=='E61' else s['items'];states[e]=s
 read(a.assets)
 parity=parity_gate.load_inputs({'path':str(a.e56_inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256})
 return ass,caps,end,states,parity

def capture_states(states,backend,budget,out,ass,parity):
 budget.call('oracle_setup',backend.load_oracle)
 for e,s in states.items():s['out']=out/e.lower();s['out'].mkdir();dump(s['out']/'ASSIGNMENT.json',ass)
 gate=states['E56']['out']/'parity';gate.mkdir();parity_gate.run_gate(backend,budget,gate,parity)
 for e,s in states.items():
  backend.validate_tokenization(s['items'])
  if e=='E61':
   for x in s['items']:
    if x['display']=='D4':
     require(backend.oracle.tok.encode(x['completion_text'],add_special_tokens=False)==x['completion_ids'],'completion IDs')
     require(backend.oracle.tok.encode(x['answer_text'],add_special_tokens=False)==[x['answer_token_id']],'answer ID')
  xs=s['capture_items'];parts={42:[],44:[]}
  for start in range(0,len(xs),8):
   values=budget.call(e+'_capture',lambda:backend.capture(xs[start:start+8]),e)
   for l in parts:parts[l].append(values[l])
  s['acts']={l:np.concatenate(v) for l,v in parts.items()};s['index']={x['id']:i for i,x in enumerate(xs)};cap=s['out']/'capture';cap.mkdir()
  for l,h in s['acts'].items():require(h.shape==(len(xs),5120) and np.isfinite(h).all(),'capture grid');np.save(cap/f'acts{l}.npy',h)
  dump(cap/('POSITION_ORDER.json' if e=='E61' else 'items.order.json'),xs if e=='E61' else [x['id'] for x in xs])
  seal(cap,'CAPTURE_SEAL.json',{'experiment':e,'slot':ass['slot'],'pod_id':ass['pod_id'],'source_seal_sha256':s['source'],'input_seal_sha256':s['input_sha'],'bank_seal_sha256':BANK_SHA if e=='E56' else None})
  s['capture_sha']=sha(cap/'CAPTURE_SEAL.json')
 ready={'experiment':'E56_E57_E61_CAPTURE','pod_id':ass['pod_id'],'slot':ass['slot'],'captured_epoch':time.time(),'capture_seals':{e:s['capture_sha'] for e,s in states.items()},'input_seals':{e:s['input_sha'] for e,s in states.items()},'reader_outputs':0}
 dump(out/'CAPTURE_READY.json',ready);return ready

def validate_go(go,ready):
 require(go.get('reader_launch_authorized') is True and go['capture_seals']==ready['capture_seals'] and go['input_seals']==ready['input_seals'] and go['pod_id']==ready['pod_id'],'forecast go binding')
 require(ready['captured_epoch']<=go['issued_epoch']<=time.time(),'go issued after capture')
 for e in ready['capture_seals']:
  require(bool(re.fullmatch('[0-9a-f]{64}',go['forecast_seals'][e])) and bool(re.fullmatch('[0-9a-f]{40}',go['forecast_commits'][e])),'committed R3b forecast before readers')

def make_jobs(states,slot):
 jobs=[]
 def add(e,reader,kind,units,h=None,pairs=None,arm=None):
  jobs.append(dict(exp=e,reader=reader,kind=kind,units=units,h=h,pairs=pairs,arm=arm,phase=e+'_'+reader+('_native' if kind in ('native','injection','position') else '_'+kind)))
 for reader in ('oracle','nla'):
  layer=44 if reader=='oracle' else 42
  for e,s in states.items():
   xs=s['capture_items'];ix=s['index'];h=s['acts'][layer]
   if e=='E61':
    for start in range(0,len(xs),8):add(e,reader,'position',xs[start:start+8],h[start:start+8])
    if reader=='oracle':
     for x in s['items']:
      if x['display']=='D4':add(e,reader,'base',[x])
    continue
   for row in s['rows']:
    ids=s['samples'][row]
    for start in range(0,len(ids),8):
     idx=[ix[k] for k in ids[start:start+8]];add(e,reader,'native',[xs[i] for i in idx],h[idx])
   if e=='E56':
    inj=[x for x in s['injection'] if x['row'] in s['plan']['injection_rows'][str(slot)]]
    for start in range(0,len(inj),8):
     units=inj[start:start+8];add(e,reader,'injection',units,s['vectors'][[x['index'] for x in units]].copy())
   for row in s['rows']:
    pairs=s['cont'][row]['pairs'] if e=='E56' else s['plan']['rows'][row]['continuation_pairs']
    if pairs is None:continue
    idx=[i for i,x in enumerate(xs) if x['feature']==row and x['split']=='test'];size=1 if pairs=='PER_ITEM' else 8
    for start in range(0,len(idx),size):
     own=idx[start:start+size];units=[xs[i] for i in own];pp=s['plan']['item_pairs'][units[0]['id']] if pairs=='PER_ITEM' else pairs
     add(e,reader,'continuation',units,h[own],pp,'own')
     if e=='E56':add(e,reader,'continuation',units,h[[ix[s['donors'][x['id']]] for x in units]],pp,'swap')
 for i,j in enumerate(jobs):j['number']=i
 return jobs

def execute_job(job,backend,out):
 xs=job['units'];reader=job['reader'];kind=job['kind'];result=[]
 if kind in ('native','injection','position'):
  groups=backend.native_one(reader,job['h'])
  if kind=='position':
   for x,g in zip(xs,groups):
    require(len(g)==1,'one position readout');result.append({k:v for k,v in dict(x,reader=reader,reader_native_layer=44 if reader=='oracle' else 42,repeat=0,**g[0]).items() if k!='ids'})
  else:result=readout_records(reader,xs,groups,'injection' if kind=='injection' else 'text')
 elif kind=='base':result=[base_answer_probability(backend,xs[0])]
 else:
  scores=backend.score('continuation' if reader=='oracle' else 'nla',xs,job['h'],job['pairs'])
  result=[dict(id=x['id'],feature=x['feature'],reader=reader,arm=job['arm'],scores=v) for x,v in zip(xs,scores)]
 dump(out/'jobs'/f'{job["number"]:06d}.json',result);return result

def finish(states,jobs,results,budget,ass,go):
 for e,s in states.items():
  native={r:[] for r in ('oracle','nla')};cont={r:[] for r in native};base=[]
  for i,j in enumerate(jobs):
   if j['exp']!=e:continue
   if j['kind'] in ('native','injection','position'):native[j['reader']]+=results[i]
   elif j['kind']=='base':base+=results[i]
   else:cont[j['reader']]+=results[i]
  out=s['out'];counts=[]
  if e=='E56':(out/'native').mkdir();(out/'continuation').mkdir()
  for reader in native:
   if e=='E57':
    own={x['id']:x for x in cont[reader]};cont[reader]=[dict(x,arm=arm,scores=x['scores'] if arm=='own' else own[s['plan']['donors'][x['id']]]['scores']) for x in own.values() for arm in ('own','swap')]
    for x in native[reader]:
     if x['feature'] in ('category_switch','capacity_list'):counts.append(count_item([x],s['plan']['count_metadata'][x['unit_id']]))
   for kind,data in [('native',native[reader]),('continuation',cont[reader])]:
    if e=='E61' and kind=='continuation':continue
    path=out/kind/(reader+'.jsonl') if e=='E56' else out/(reader+'.'+kind+'.jsonl')
    with path.open('x') as f:
     for x in data:f.write(json.dumps(x,allow_nan=False)+'\n')
  if e=='E57':dump(out/'COUNTS.json',counts)
  if e=='E61':dump(out/'BASE_PROBABILITIES.json',base)
  dump(out/'NLA_TRUNCATION.json',truncation_summary(native['nla'],row_key='display' if e=='E61' else 'feature'))
  dump(out/'GO_RECEIPT.json',go);dump(out/'ADMISSION.json',read(budget.out/'FORECAST.json'))
  dump(out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':budget.end,'charged_caps':budget.caps,'phase_seconds':budget.observed})
  if e!='E56':dump(out/'PARITY_REUSE.json',{'pod_id':ass['pod_id'],'e56_output_seal_sha256':sha(states['E56']['out']/'OUTPUT_SEAL.json'),'parity_result_sha256':sha(states['E56']['out']/'parity/PARITY_RESULT.json'),'status':'PASS'})
  seal(out,'OUTPUT_SEAL.json',{'experiment':e,'status':'COMPLETE','slot':ass['slot'],'pod_id':ass['pod_id'],'source_seal_sha256':s['source'],'input_seal_sha256':s['input_sha']})

def main():
 p=argparse.ArgumentParser()
 for key in ('assignment','e56-inputs','e57-inputs','assets','out','go'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--e61-inputs',type=Path);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 ass,caps,end,states,parity=preflight(a);a.out.mkdir(parents=True,exist_ok=False)
 if a.dry_run:
  from smoke_joint import smoke_joint
  smoke_joint(a.out/'SMOKE');dump(a.out/'DRY_RUN.json',{'status':'PASS','archive_preflight':'REAL','all_stage_smoke':'PASS','GPU_calls':0});return
 seed=read(E56/'SAVED_ORACLE_TIMINGS.json')['completed_phase_seconds'];budget=Budget(a.out,caps,end,seed);timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  backend=Backend(ROOT,a.assets,{'gpu_type':'H200'});ready=capture_states(states,backend,budget,a.out,ass,parity)
  while not a.go.exists():budget.check();time.sleep(1)
  go=read(a.go);validate_go(go,ready);dump(a.out/'GO_RECEIPT.json',go);(a.out/'jobs').mkdir()
  jobs=make_jobs(states,ass['slot']);results=admit_and_run(jobs,backend,budget,lambda j:execute_job(j,backend,a.out));finish(states,jobs,results,budget,ass,go)
 except NoFit as e:
  atomic(a.out/'NO_FIT.json',{'status':'NO_FIT','reason':str(e),'observed':budget.observed,'deadline_epoch':end})
  previous=read(a.out/'FORECAST.json') if (a.out/'FORECAST.json').exists() else {}
  atomic(a.out/'FORECAST.json',dict(previous,status='NO_FIT',reason=str(e),observed=budget.observed,deadline_epoch=end))
 except BaseException as e:atomic(a.out/'FAILURE.json',{'error':str(e)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
