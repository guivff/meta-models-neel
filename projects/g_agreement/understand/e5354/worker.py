"""Single H200 E53 continuation + E54 descriptive native channels; <=5400s custody."""
import argparse,os,sys,time,threading,signal,re
from collections import defaultdict
from .contract import *
from .e15_scorer import native_score,base_score
sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
from .runtime import Backend
import parity_gate

def jobs(items,pairs,split):
 groups=defaultdict(list)
 for i,x in enumerate(items):
  if x['split']==split:groups[(x['feature'],json.dumps(pairs[x['id']]))].append(i)
 return [(r,json.loads(p),ix[s:s+8]) for (r,p),ix in groups.items() for s in range(0,len(ix),8)]

def run(a):
 sources();assignment=read(a.assignment);budget=Budget(assignment)
 require(re.fullmatch('[0-9a-f]{40}',assignment.get('e49_forecast_commit','')),'E49 forecast must precede these continuation scores')
 require(sha(HERE/'SOURCE_SEAL.json')==assignment['source_seal_sha256'],'assignment source')
 s=verify(a.inputs,'INPUT_SEAL.json',assignment['input_seal_sha256']);require(s.get('stage')=='BOUND','verified E49 capture binding required')
 require(sha(a.assets)==assignment['assets_manifest_sha256'],'assets manifest binding')
 lock=a.inputs/'JOB_ONCE.json';dump(lock,{'pod_id':assignment['pod_id'],'started_epoch':time.time()})
 a.out.mkdir(parents=True,exist_ok=False)
 timer=threading.Timer(max(0,budget.end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 elapsed54=0.
 def call(phase,fn,n=0):
  nonlocal elapsed54
  t=time.monotonic();v=budget.call(phase,fn,n)
  if phase.startswith('e54') or phase.endswith('setup'):elapsed54+=time.monotonic()-t
  require(elapsed54<1800,'E54 own cap 1800s including shared reader setup')
  return v
 try:
  import torch
  torch.manual_seed(SEED);np.random.seed(SEED)
  dump(a.out/'ASSIGNMENT.json',assignment)
  backend=Backend(ROOT,a.assets,{'gpu_type':'H200'})
  call('oracle_setup',backend.load_oracle)
  parity=a.out/'parity';parity.mkdir()
  parity_gate.run_gate(backend,budget,parity,parity_gate.load_inputs({'path':str(a.inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256}))
  items=read(a.inputs/'e49_items.json');pairs=read(a.inputs/'e49_pairs.json');dm=read(a.inputs/'e49_donors.json');lookup={x['id']:i for i,x in enumerate(items)}
  backend.validate_tokenization(items)
  for pp in pairs.values():
   for x,y in pp:require(len(backend.oracle.tok.encode(x,add_special_tokens=False))==len(backend.oracle.tok.encode(y,add_special_tokens=False))>0,'candidate token lengths')
  h49={b:np.load(a.inputs/f'e49_acts{b}.npy',allow_pickle=False) for b in (42,44)}
  require(all(h.shape==(len(items),5120) and np.isfinite(h).all() for h in h49.values()),'E49 grid')
  # Only E54 requires target capture. Both layers are exported for native reader alignment.
  i54=read(a.inputs/'e54_items.json');backend.validate_tokenization(i54);parts=[]
  batches=[i54[k:k+8] for k in range(0,len(i54),8)]
  for n,batch in enumerate(batches):parts.append(call('e54_capture',lambda:backend.capture(batch),len(batches)-n-1))
  h54={b:np.concatenate([x[b] for x in parts]) for b in (42,44)}
  cap=a.out/'e54_capture';cap.mkdir()
  for b,h in h54.items():require(h.shape==(336,5120) and np.isfinite(h).all(),'E54 capture grid');np.save(cap/f'acts{b}.npy',h)
  dump(cap/'items.order.json',[x['id'] for x in i54]);dump(cap/'CAPTURE_METADATA.json',{'experiment':'E54','bank_seal_sha256':E54_SHA,'block':44,'auxiliary_block':42,'read_position':'last raw-prefix token','adapter':'disabled'})
  seal(cap,'CAPTURE_SEAL.json',{'e54_bank_sha256':E54_SHA,'pod_id':assignment['pod_id']})
  def record(v):
   with (a.out/'scores.jsonl').open('a') as f:f.write(json.dumps(v,allow_nan=False)+'\n')
  # Exact E15 base reference; dev-only validity, frozen threshold >=.80 applied on CPU.
  todo=jobs(items,pairs,'dev')
  for n,(row,pp,ix) in enumerate(todo):
   v=call('e53_base',lambda:base_score(backend.oracle,[items[i] for i in ix],pp).T.numpy(),len(todo)-n-1)
   for i,val in zip(ix,v):record({'id':items[i]['id'],'bank':'E49','row':row,'reader':'base','arm':'true','scores':val.tolist()})
  todo=jobs(items,pairs,'test')
  for reader,block in [('olens',44),('nla',42)]:
   if reader=='nla':call('nla_setup',backend.load_nla)
   obj=backend.oracle if reader=='olens' else backend.nla
   for arm in ['true','opposite_swap']:
    for n,(row,pp,ix) in enumerate(todo):
     use=ix if arm=='true' else [lookup[dm[items[i]['id']]] for i in ix]
     v=call('e53_'+reader+'_'+arm,lambda:native_score(reader,obj,torch.as_tensor(h49[block][use]),pp).T.detach().float().cpu().numpy(),len(todo)-n-1)
     require(v.shape==(len(ix),len(pp)) and np.isfinite(v).all(),'continuation score grid')
     for i,val in zip(ix,v):record({'id':items[i]['id'],'bank':'E49','row':row,'reader':reader,'arm':arm,'scores':val.tolist()})
   if reader=='olens':
    old=read(a.inputs/'e36_items.json');d36=read(a.inputs/'e36_donors.json');p36=read(a.inputs/'e36_pairs.json')['rows'];hh=np.load(a.inputs/'e36_acts44.npy');li={x['id']:i for i,x in enumerate(old)}
    p36={x['id']:[[p['A'],p['B']] for p in p36[x['feature']]['pairs']] for x in old};js=jobs(old,p36,'test')
    for n,(row,pp,ix) in enumerate(js):
     use=[li[d36[old[i]['id']]] for i in ix]
     v=call('e36_swap',lambda:native_score('olens',obj,torch.as_tensor(hh[use]),pp).T.detach().float().cpu().numpy(),len(js)-n-1)
     for i,val in zip(ix,v):record({'id':old[i]['id'],'bank':'E36','row':row,'reader':'olens','arm':'opposite_swap','scores':val.tolist()})
   native_reader='oracle' if reader=='olens' else 'nla';ix=[i for i,x in enumerate(i54) if x['split']=='test'];js=[ix[k:k+8] for k in range(0,len(ix),8)]
   for n,idx in enumerate(js):
    texts=call('e54_'+native_reader,lambda:backend.native(native_reader,h54[block][idx]),len(js)-n-1)
    require(len(texts)==len(idx),'native output grid')
    for i,t in zip(idx,texts):record({'id':i54[i]['id'],'bank':'E54','row':i54[i]['feature'],'reader':reader,'arm':'native',**t})
  dump(a.out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':budget.end,'E54_seconds_including_shared_setup':elapsed54,'observed_max_batch_seconds':budget.observed})
  seal(a.out,'OUTPUT_SEAL.json',{'status':'COMPLETE','experiment':'E53+E54','input_seal_sha256':assignment['input_seal_sha256'],'source_seal_sha256':assignment['source_seal_sha256'],'pod_id':assignment['pod_id']})
 except BaseException as e:
  dump(a.out/'FAILURE.json',{'status':'FAILED_NO_RETRY','type':type(e).__name__,'error':str(e)});raise
 finally:timer.cancel()
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['inputs','assignment','assets','out']:p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
