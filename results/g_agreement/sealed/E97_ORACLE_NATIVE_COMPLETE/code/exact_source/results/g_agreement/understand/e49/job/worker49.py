"""E49 parity -> sealed capture -> explicit release -> gates/readers."""
import argparse,os,sys,time,threading,signal
from pathlib import Path
import numpy as np
from contract49 import *
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'));sys.path.insert(0,str(HERE/'vendor'))
import parity_gate

class Budget:
 def __init__(self,a):self.assignment=a;self.end=deadline(a);self.observed={}
 def check(self):require(time.time()<self.end-60,'custody deadline / retrieval reserve')
 def call(self,phase,fn,remaining_units=0):
  self.check();start=time.monotonic();result=fn();elapsed=time.monotonic()-start
  self.observed[phase]=max(elapsed,self.observed.get(phase,0));self.check()
  require(time.time()+1.5*self.observed[phase]*remaining_units<self.end-60,'NO_FIT phase '+phase)
  return result

def wait_for_go(path,a,capture_sha,captured_epoch,budget):
 # Integrator writes atomically. Absence is a hold, never an implicit approval.
 while True:
  budget.check()
  if Path(path).exists():return validate_go(read(path),a,capture_sha,time.time(),captured_epoch)
  time.sleep(1)

def acquire(items,dev_labels,candidates,backend,budget,out,assignment,parity_inputs,release):
 out=Path(out);parity=out/'parity';parity.mkdir()
 budget.call('oracle_setup',backend.load_oracle)
 parity_gate.run_gate(backend,budget,parity,parity_inputs)
 backend.validate_tokenization(items)
 cap=out/'capture';cap.mkdir();chunks=[items[s:s+8] for s in range(0,len(items),8)];parts=[]
 for i,batch in enumerate(chunks):parts.append(budget.call('capture',lambda:backend.capture(batch),len(chunks)-i-1))
 h=np.concatenate([x[44] for x in parts]);h42=np.concatenate([x[42] for x in parts]);require(h42.shape==(2688,5120) and np.isfinite(h42).all(),'native NLA capture grid')
 require(h.shape==(2688,5120) and np.isfinite(h).all(),'full capture grid')
 testix=[i for i,x in enumerate(items) if x['split']=='test'];devix=[i for i,x in enumerate(items) if x['split']=='dev']
 require(len(testix)==len(devix)==1344,'capture split counts')
 np.save(cap/'acts42.npy',h42);np.save(cap/'acts44.npy',h);np.save(cap/'acts44.test.npy',h[testix]);dump(cap/'items.order.json',[x['id'] for x in items]);dump(cap/'test.order.json',[items[i]['id'] for i in testix])
 captured_epoch=time.time()
 dump(cap/'CAPTURE_METADATA.json',{'block':44,'auxiliary_NLA_block':42,'padding':'right','batch':8,'read_position':'last raw-prefix token','adapter':'disabled','captured_epoch':captured_epoch,'items':2688,'test_items':1344,'reader_calls_on_E49':0,'bank_seal_sha256':BANK_SHA,'parity_result_sha256':sha(parity/'PARITY_RESULT.json'),'pod_id':assignment['pod_id']})
 seal(cap,'CAPTURE_SEAL.json',{'experiment':'E49','stage':'CAPTURE_COMPLETE_WAITING_FOR_GO','input_seal_sha256':assignment['input_seal_sha256'],'source_seal_sha256':assignment['source_seal_sha256'],'bank_seal_sha256':BANK_SHA,'pod_id':assignment['pod_id']})
 capsha=sha(cap/'CAPTURE_SEAL.json')
 dump(out/'CAPTURE_READY.json',{'status':'WAITING_FOR_INTEGRATOR_GO','capture_seal_sha256':capsha,'capture_path':str(cap),'captured_epoch':captured_epoch,'reader_calls_on_E49':0})
 go=release(capsha,captured_epoch)
 validate_go(go,assignment,capsha,time.time(),captured_epoch);dump(out/'GO_ACCEPTED.json',go)
 # No E49 score or generation occurs above this boundary.
 gates=out/'gates';gates.mkdir();rows=sorted(candidates['rows']);rowix={r:[i for i in testix if items[i]['feature']==r] for r in rows}
 import torch
 from mats.probes import fit_logreg
 torch.set_num_threads(1);torch.manual_seed(SEED)
 probe=[];weights={};fits=[]
 for row in rows:
  tr=[i for i in devix if items[i]['feature']==row];te=rowix[row];require(len(tr)==len(te)==84,'per-row split counts')
  y=torch.tensor([dev_labels[items[i]['id']] for i in tr]);require(int(y.sum())==42,'dev label balance')
  model=budget.call('probe_cpu',lambda:fit_logreg(torch.from_numpy(h[tr].copy()),y))
  values=model.decision(torch.from_numpy(h[te].copy())).numpy()
  probe.extend({'id':items[i]['id'],'feature':row,'score':float(v)} for i,v in zip(te,values))
  weights[row+'__w']=(model.w/model.sd).numpy();weights[row+'__b']=np.array(model.b-float(model.mu@(model.w/model.sd)))
  fits.append({'row':row,'dev_ids':[items[i]['id'] for i in tr],'recipe':'mats.probes.fit_logreg; lambda=.001;200iterations;dev standardization only'})
 dump(gates/'probe.json',probe);np.savez_compressed(gates/'probe_weights.npz',**weights);dump(gates/'probe_fits.json',fits)
 base=[];jobs=[(r,rowix[r][s:s+8]) for r in rows for s in range(0,84,8)]
 for n,(row,ix) in enumerate(jobs):
  values=budget.call('base_text',lambda:backend.base_scores([items[i] for i in ix],candidates['rows'][row]['oracle']),len(jobs)-n-1)
  base.extend({'id':items[i]['id'],'feature':row,'scores':v} for i,v in zip(ix,values))
 dump(gates/'base.json',base);seal(gates,'GATE_OUTPUT_SEAL.json',{'experiment':'E49','capture_seal_sha256':capsha,'go_sha256':sha(out/'GO_ACCEPTED.json')})
 readers=out/'readers';readers.mkdir()
 for reader in ['oracle','nla']:
  if reader=='nla':budget.call('nla_setup',backend.load_nla)
  for n,(row,ix) in enumerate(jobs):
   dest=readers/row;dest.mkdir(exist_ok=True)
   texts=budget.call(reader+'_native',lambda:backend.native(reader,(h if reader=='oracle' else h42)[ix]),len(jobs)-n-1)
   with (dest/(reader+'_native.jsonl')).open('a') as f:
    require(len(texts)==len(ix),'native readout count')
    for i,x in zip(ix,texts):f.write(json.dumps({'id':items[i]['id'],'feature':row,'block':44 if reader=='oracle' else 42,**x},allow_nan=False)+'\n')
  for n,(row,ix) in enumerate(jobs):
   pairs=candidates['rows'][row]['oracle' if reader=='oracle' else 'nla']
   values=budget.call(reader+'_asked',lambda:backend.score('oracle_descriptive' if reader=='oracle' else 'nla',[items[i] for i in ix],backend.take(h if reader=='oracle' else h42,ix),pairs),len(jobs)-n-1)
   with (readers/row/(reader+'_asked.jsonl')).open('a') as f:
    for i,v in zip(ix,values):f.write(json.dumps({'id':items[i]['id'],'feature':row,'block':44 if reader=='oracle' else 42,'scores':v},allow_nan=False)+'\n')
  if reader=='oracle':
   for row in rows:
    pairs=candidates['rows'][row]['continuation']
    if not pairs:continue
    for start in range(0,84,8):
     ix=rowix[row][start:start+8];values=budget.call('continuation',lambda:backend.score('continuation',[items[i] for i in ix],backend.take(h,ix),pairs))
     with (readers/row/'continuation.jsonl').open('a') as f:
      for i,v in zip(ix,values):f.write(json.dumps({'id':items[i]['id'],'feature':row,'scores':v},allow_nan=False)+'\n')
 seal(readers,'READER_OUTPUT_SEAL.json',{'experiment':'E49','capture_seal_sha256':capsha,'go_sha256':sha(out/'GO_ACCEPTED.json')})
 dump(out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':budget.end,'max_phase_seconds':budget.observed})
 seal(out,'OUTPUT_SEAL.json',{'experiment':'E49','status':'COMPLETE','bank_seal_sha256':BANK_SHA,'input_seal_sha256':assignment['input_seal_sha256'],'source_seal_sha256':assignment['source_seal_sha256'],'pod_id':assignment['pod_id'],'capture_seal_sha256':capsha})

def main():
 p=argparse.ArgumentParser()
 for k in ['inputs','assets','assignment','go','out']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();assignment=read(a.assignment);budget=Budget(assignment);budget.check();a.out.mkdir(parents=True,exist_ok=False)
 timer=threading.Timer(max(0,deadline(assignment)-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  verify(HERE,'SOURCE_SEAL.json',assignment['source_seal_sha256']);verify(a.inputs,'INPUT_SEAL.json',assignment['input_seal_sha256'])
  for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'dependency '+n)
  dump(a.out/'ASSIGNMENT.json',assignment)
  import torch
  torch.manual_seed(SEED);np.random.seed(SEED)
  from runtime49 import Backend
  backend=Backend(ROOT,a.assets,{'gpu_type':assignment['gpu_type']})
  parity=parity_gate.load_inputs({'path':str(a.inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256})
  acquire(read(a.inputs/'items.json'),read(a.inputs/'dev_labels.json'),read(a.inputs/'candidates.json'),backend,budget,a.out,assignment,parity,lambda cs,ct:wait_for_go(a.go,assignment,cs,ct,budget))
 except BaseException as e:
  dump(a.out/'FAILURE.json',{'status':'FAILED','error':str(e),'type':type(e).__name__});raise
 finally:timer.cancel()
if __name__=='__main__':main()
