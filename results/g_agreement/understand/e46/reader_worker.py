"""E46 reader stage: frozen E36 backend and parity gate, eligible rows only."""
import argparse,importlib.util,os,sys,time,signal,math
from io46 import *

def eligible_rows(medians):
 result=[]
 for r in medians['rows']:
  expected=r['excluded_initial_unknown']/r['n']<=.2 and (r['median']>=24 if r['cell']=='long' else r['median']<=4)
  if r['eligible']!=expected:raise ValueError('persistence eligibility mismatch')
  if expected:result.append(r['row'])
 return sorted(result)

def load_runtime(root):
 sys.path.insert(0,str(root));sys.path.insert(0,str(root/'external/mats-nla-workspace/src'))
 sys.path.insert(0,str(root/'results/g_agreement/understand/e36'))
 spec=importlib.util.spec_from_file_location('e36_reader_runtime46',root/'results/g_agreement/understand/e36/worker.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def pipeline(items,candidates,backend,budget,out,parity_inputs,gate):
 budget.call('oracle_setup',backend.load_oracle)
 gate(backend,budget,out,parity_inputs)  # Full 252-item gate before any E46 capture/scoring.
 backend.validate_tokenization(items)
 parts={42:[],44:[]};chunks=[items[i:i+8] for i in range(0,len(items),8)]
 for k,chunk in enumerate(chunks):
  h=budget.call('capture',lambda:backend.capture(chunk),len(chunks)-k-1)
  for layer in parts:parts[layer].append(h[layer])
 acts={layer:backend.join(v) for layer,v in parts.items()}
 for layer,h in acts.items():backend.save_capture(out/f'acts{layer}.npy',h)
 dump(out/'items.order.json',[x['id'] for x in items])
 with (out/'scores.jsonl').open('x') as f:
  for channel,key,layer in [('oracle_descriptive','olens_descriptive',44),('nla','nla',42)]:
   if channel=='nla':budget.call('nla_setup',backend.load_nla)
   jobs=[]
   for row in sorted({x['feature'] for x in items}):
    ix=[i for i,x in enumerate(items) if x['feature']==row and x['split']=='test']
    jobs.extend((row,ix[j:j+8]) for j in range(0,len(ix),8))
   for k,(row,ix) in enumerate(jobs):
    selected=[items[i] for i in ix];h=backend.take(acts[layer],ix);pairs=candidates['rows'][row][key]
    values=budget.call(channel,lambda:backend.score(channel,selected,h,pairs),len(jobs)-k-1)
    if len(values)!=len(ix) or any(len(v)!=2 or not all(math.isfinite(x) for x in v) for v in values):raise ValueError('score coverage')
    for item,scores in zip(selected,values):f.write(json.dumps({'id':item['id'],'feature':row,'channel':channel,'block':layer,'scores':scores,'status':'COMPLETE'})+'\n')
    f.flush()

def run(a):
 root=a.root.resolve();os.chdir(root);plan=read(a.plan);q=read(a.assignment)
 if q.get('issuer')!='integrator' or q.get('experiment')!='E46' or q.get('pod_id')!=os.environ.get('RUNPOD_POD_ID') or not q.get('pod_id'):raise ValueError('integrator assignment required')
 if q.get('plan_sha256')!=sha(a.plan) or q.get('assets_manifest_sha256')!=sha(a.assets):raise ValueError('assignment hash mismatch')
 with a.assignment.with_suffix('.reader.once.lock').open('x') as f:f.write(sha(a.plan))
 prior=q['prior_gpu_seconds'];start=q['allocation_started_at'];deadline=q['hard_deadline']
 if not math.isfinite(prior) or prior<plan['minimum_prior_gpu_seconds'] or not start<=time.time()<deadline-180 or not 0<deadline-start<=10800-prior:raise ValueError('aggregate custody cap')
 stop=q['external_stop']
 if stop.get('confirmed') is not True or stop.get('deadline')!=deadline or not stop.get('receipt'):raise ValueError('verified external stop required')
 if q.get('gpu_type')!='H200' or q.get('gpu_count')!=1:raise ValueError('one H200 assignment required')
 for rel,h in plan['source_files'].items():
  if sha(root/rel)!=h:raise ValueError('source changed: '+rel)
 def bound(ref):
  path=root/ref['path']
  if sha(path)!=ref['sha256']:raise ValueError('bound artifact changed')
  return path
 med=read(bound(plan['persistence_medians']));persist=bound(plan['persistence_seal']);verify(persist.parent,persist.name)
 if eligible_rows(med)!=plan['eligible_rows']:raise ValueError('eligible row set changed')
 if med['bank_seal_sha256']!=plan['bank_seal']['sha256'] or med['state_seal_sha256']!=plan['state_seal']['sha256']:raise ValueError('persistence bank/state binding')
 bound(plan['bank_seal']);bound(plan['state_seal']);bank=bound(plan['reader_items']);cand=bound(plan['candidates'])
 items=rows(bank);candidates=read(cand)
 if sorted({x['feature'] for x in items})!=plan['eligible_rows'] or len(items)!=168*len(plan['eligible_rows']):raise ValueError('reader bank scope')
 runtime=load_runtime(root)
 runtime.verify_assets_binding({'assets':{'path':str(a.assets.resolve()),'sha256':sha(a.assets)},'source_bindings':[{'path':str(root/r),'sha256':h} for r,h in plan['source_files'].items()],'registered_revisions':plan['registered_revisions']},a.assets.resolve(),root)
 parity={'path':str(bound(plan['parity_inputs'])),'sha256':plan['parity_inputs']['sha256']}
 parity_inputs=runtime.G.load_inputs(parity)
 a.out.mkdir(parents=True,exist_ok=False)
 def timeout(*_):raise TimeoutError('E46 reader custody deadline')
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,deadline-180-time.time())
 status='ABORTED'
 try:
  budget=runtime.Budget(q,a.out,cap_gpu_seconds=10800)
  pipeline(items,candidates,runtime.NativeBackend(root,a.assets,q),budget,a.out,parity_inputs,runtime.G.run_gate)
  status='COMPLETE'
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  dump(a.out/'RUNTIME.json',{'status':status,'plan_sha256':sha(a.plan),'persistence_seal_sha256':plan['persistence_seal']['sha256'],'assignment_sha256':sha(a.assignment),'prior_gpu_seconds':prior,'current_custody_seconds':time.time()-start,'aggregate_cap_seconds':10800,'parity_precedes_production':True})
 if status=='COMPLETE':seal(a.out,[p.name for p in sorted(a.out.iterdir()) if p.is_file()],'READER_OUTPUT_SEAL.json')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['root','plan','assignment','assets','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in ['plan','assignment','assets','out']:setattr(a,n,getattr(a,n).resolve())
 run(a)
