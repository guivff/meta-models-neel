"""E56 acquisition: native only, dev-fit probes, continuation swaps; no forced choice."""
import argparse,json,os,sys,time,threading,signal
from pathlib import Path
import numpy as np
from contract56 import *
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'));sys.path.insert(0,str(E49));sys.path.insert(0,str(E49/'vendor'))
from runtime49 import Backend as E49Backend
import parity_gate

class Backend(E49Backend):
 def score(self,channel,items,activations,pairs):
  import torch
  return super().score(channel,items,torch.as_tensor(activations),pairs)

 def native_one(self,reader,h):
  if reader=='nla':
   from native_nla512 import native_nla
   return native_nla(self.nla,h,k=1,batch=8)
  import torch
  from mats.readers.nla import Sampling,extract_explanation
  # Do not add a carrier or normalize h here: only native adapters may transform it.
  acts=torch.from_numpy(np.array(h,copy=True))
  sampling=Sampling(temperature=0,top_p=1.,top_k=0,max_new_tokens=128)
  with torch.no_grad():
   raw=self.oracle.verbalize(acts,44,k=1,sampling=sampling,batch=8)
  result=[]
  for group in raw:
   require(len(group)==1,'one actual greedy readout required');decoded=[]
   for text in group:
    payload=text
    decoded.append({'raw':text,'text':payload if payload is not None else text,'malformed':payload is None})
   result.append(decoded)
  return result

class Budget:
 def __init__(self,a):self.end=deadline(a);self.observed={}
 def check(self):require(time.time()<self.end-60,'custody retrieval reserve')
 def call(self,phase,fn,remaining_units=0):
  self.check();t=time.monotonic();v=fn();elapsed=time.monotonic()-t;self.observed[phase]=max(elapsed,self.observed.get(phase,0));self.check()
  require(time.time()+1.5*self.observed[phase]*remaining_units<self.end-60,'NO_FIT '+phase)
  return v

def readout_records(reader,units,outputs,kind):
 require(len(units)==len(outputs),'native unit count')
 records=[]
 for unit,group in zip(units,outputs):
  require(len(group)==1,'repeat grid')
  for repeat,value in enumerate(group):
   d={'id':unit['id']+':'+reader+':'+str(repeat),'unit_id':unit['id'],'reader':reader,'repeat':repeat,'kind':kind,'feature':unit['feature'] if kind=='text' else unit['row'],'reader_native_layer':44 if reader=='oracle' else 42,**value}
   if kind=='injection':d.update(direction_id=direction_id(unit),arm=unit['arm'],source_layer=44,vector_index=unit['index'])
   records.append(d)
 return records

def acquire(items,dev_labels,inp,backend,budget,out,a):
 out=Path(out);rows=read(inp/'SHARDS.json')['rows'][str(a['slot'])];injrows=read(inp/'SHARDS.json')['injection_rows'][str(a['slot'])]
 selected=[x for x in items if x['feature'] in rows];indices={x['id']:i for i,x in enumerate(selected)}
 parity=out/'parity';parity.mkdir();budget.call('oracle_setup',backend.load_oracle)
 parity_gate.run_gate(backend,budget,parity,parity_gate.load_inputs({'path':str(inp/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256}))
 backend.validate_tokenization(selected);parts={42:[],44:[]};chunks=[selected[i:i+8] for i in range(0,len(selected),8)]
 for n,chunk in enumerate(chunks):
  v=budget.call('capture',lambda:backend.capture(chunk),len(chunks)-n-1)
  for layer in parts:parts[layer].append(v[layer])
 acts={l:np.concatenate(v) for l,v in parts.items()};cap=out/'capture';cap.mkdir()
 for l,h in acts.items():require(h.shape==(len(selected),5120) and np.isfinite(h).all(),'capture grid');np.save(cap/f'acts{l}.npy',h)
 dump(cap/'items.order.json',[x['id'] for x in selected]);seal(cap,'CAPTURE_SEAL.json',{'experiment':'E56','slot':a['slot'],'bank_seal_sha256':BANK_SHA,'input_seal_sha256':a['input_seal_sha256']})
 dump(out/'CPU_POSTPROCESS_REQUIRED.json',{'probe':True,'class_means':True,'labels_on_pod':False})
 samples=read(inp/'SAMPLING.json')['native_ids'];cont=read(inp/'CONTINUATIONS.json');donors=read(inp/'DONORS.json')
 injection=read(inp/'injection/ITEMS.json')['items'];vectors=np.load(inp/'injection/INPUT_VECTORS.npz')['activations'];check_injection(vectors,injection)
 injection=[x for x in injection if x['row'] in injrows]
 native=out/'native';native.mkdir();continuation=out/'continuation';continuation.mkdir()
 for reader in ('oracle','nla'):
  if reader=='nla':budget.call('nla_setup',backend.load_nla)
  layer=44 if reader=='oracle' else 42
  with (native/(reader+'.jsonl')).open('x') as stream:
   jobs=[(row,samples[row][i:i+8]) for row in rows for i in range(0,len(samples[row]),8)]
   for n,(row,ids) in enumerate(jobs):
    ix=[indices[k] for k in ids];units=[selected[i] for i in ix]
    output=budget.call(reader+'_native',lambda:backend.native_one(reader,acts[layer][ix]),len(jobs)-n-1)
    for r in readout_records(reader,units,output,'text'):stream.write(json.dumps(r,allow_nan=False)+'\n')
   for start in range(0,len(injection),8):
    units=injection[start:start+8];h=vectors[[x['index'] for x in units]].copy();before=h.tobytes()
    output=budget.call(reader+'_injection',lambda:backend.native_one(reader,h));require(h.tobytes()==before,'injection inputs mutated')
    for r in readout_records(reader,units,output,'injection'):stream.write(json.dumps(r,allow_nan=False)+'\n')
  with (continuation/(reader+'.jsonl')).open('x') as stream:
   for row in rows:
    pairs=cont[row]['pairs']
    if pairs is None:continue
    ix=[i for i,x in enumerate(selected) if x['feature']==row and x['split']=='test']
    for start in range(0,84,8):
     batch=ix[start:start+8];units=[selected[i] for i in batch]
     for arm,sourceix in [('own',batch),('swap',[indices[donors[x['id']]] for x in units])]:
      scores=budget.call(reader+'_continuation',lambda:backend.score('continuation' if reader=='oracle' else 'nla',units,backend.take(acts[layer],sourceix),pairs))
      for x,v in zip(units,scores):stream.write(json.dumps({'id':x['id'],'feature':row,'reader':reader,'arm':arm,'scores':v},allow_nan=False)+'\n')
 from native_nla512 import truncation_summary
 dump(out/'NLA_TRUNCATION.json',truncation_summary([json.loads(line) for line in (native/'nla.jsonl').read_text().splitlines()]))
 dump(out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':budget.end,'phase_max_seconds':budget.observed})
 seal(out,'OUTPUT_SEAL.json',{'experiment':'E56','status':'COMPLETE','slot':a['slot'],'pod_id':a['pod_id'],'input_seal_sha256':a['input_seal_sha256'],'source_seal_sha256':a['source_seal_sha256'],'bank_seal_sha256':BANK_SHA})

def main():
 p=argparse.ArgumentParser()
 for k in ['inputs','assets','assignment','out']:p.add_argument('--'+k,type=Path,required=True)
 x=p.parse_args();a=read(x.assignment);budget=Budget(a);budget.check()
 require(read(HERE/'RULE_STATUS.json')['status']=='RESOLVED','§172 verdict definitions held; do not launch before committed ruling')
 x.out.mkdir(parents=True,exist_ok=False);timer=threading.Timer(max(0,budget.end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  verify(HERE,'SOURCE_SEAL.json',a['source_seal_sha256']);verify(x.inputs,'INPUT_SEAL.json',a['input_seal_sha256'])
  for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'dependency '+n)
  dump(x.out/'ASSIGNMENT.json',a)
  import torch
  torch.manual_seed(SEED);np.random.seed(SEED)
  acquire(read(x.inputs/'items.json'),None,x.inputs,Backend(ROOT,x.assets,{'gpu_type':'H200'}),budget,x.out,a)
 except BaseException as e:dump(x.out/'FAILURE.json',{'error':str(e),'type':type(e).__name__});raise
 finally:timer.cancel()
if __name__=='__main__':main()
