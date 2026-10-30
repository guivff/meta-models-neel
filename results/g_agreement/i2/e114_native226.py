"""E114 frozen sentence arms, shared base/Oracle model, exact native Oracle44 only.
Capture uses the Oracle backend's existing adapter-OFF subject context; no second
model load, new reader, probe, source filter or CPU truth on the pod.
"""
import argparse,time,threading,signal,os,json,math
from pathlib import Path
import numpy as np
from runtime import Runtime
from contract import read,write,sha,require
class OracleRuntime(Runtime):
 def capture44(self,items):
  import torch,sys
  from contract import ROOT
  sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
  from mats.capture import capture
  self.check_tokens(items);model,tok,cm=self.subject()
  with cm,torch.inference_mode():v=capture(model,[x['ids']for x in items],(44,),[[x['read_index']]for x in items],batch_size=8,pad_id=tok.pad_token_id or 0)
  return v[44][:,0].float().cpu().numpy()
def validate(items):
 require(len(items)==len({x['id']for x in items})==504,'all504 frozen original transformed inputs')
 for x in items:
  require(set(x)=={'id','prompt','input_ids','read_position'},'public fields only')
  require(x['input_ids']and x['read_position']==len(x['input_ids'])-1 and len(x['input_ids'])<=38,'original final read token, no cropping')
 return [dict(id=x['id'],text=x['prompt'],ids=x['input_ids'],read_index=x['read_position'])for x in items]
def fit(elapsed,capture_profile,captures_remaining,native_profile,natives_remaining,cap=2000):
 require(capture_profile and native_profile and all(v>0 for v in capture_profile+native_profile),'actual timings')
 need=elapsed+1.25*(max(capture_profile)*captures_remaining+max(native_profile)*natives_remaining)+60
 return dict(status='PASS'if need<=cap else'NO_FIT',need_seconds=need,cap_seconds=cap,elapsed_setup_and_profile_seconds=elapsed,max_capture_batch_seconds=max(capture_profile),remaining_capture_batches=captures_remaining,max_native_batch_seconds=max(native_profile),remaining_native_batches=natives_remaining,margin=1.25)
def run(a,b):
 ass=read(a.assignment);start=ass['pod_created_epoch'];end=ass['absolute_deadline_epoch'];require(ass['experiment']=='E114'and ass['cap_seconds']==2000 and end==start+2000,'approved2000custody')
 require(time.time()<start+900 and sha(a.inputs)==a.input_sha256,'input/source setup binding');items=validate(read(a.inputs));a.out.mkdir(exist_ok=False);(a.out/'capture').mkdir();(a.out/'oracle').mkdir();events=[]
 def timed(name,fn):
  require(time.time()<end-60,'original deadline');t=time.monotonic();v=fn();b.sync();events.append(dict(phase=name,seconds=time.monotonic()-t));write(a.out/'TIMINGS.json',events,replace=True);return v
 b.native_batch_size=8;timed('oracle_shared_base_setup',b.load_oracle);b.seed(20261029);require(time.time()<start+900,'setup900')
 chunks=[items[i:i+64]for i in range(0,504,64)];captures={};cp=[];npf=[];native_done=0;status='COMPLETE'
 for n,xs in enumerate(chunks):
  v=timed('capture44',lambda xs=xs:b.capture44(xs));require(v.shape==(len(xs),5120)and np.isfinite(v).all(),'finite original44capture');cp.append(events[-1]['seconds']);np.savez(a.out/'capture'/f'{n:04d}.npz',ids=np.array([x['id']for x in xs]),activations=v)
  captures.update({x['id']:row for x,row in zip(xs,v)})
  if n==2:
   batch=items[:8];v=timed('oracle_native',lambda:b.native('oracle',np.array([captures[x['id']]for x in batch]),False));npf.append(events[-1]['seconds']);require(len(v)==8 and all(len(g)==1 for g in v),'onegreedy originalnative')
   write(a.out/'oracle/0000.json',[dict(id=x['id'],output=g[0])for x,g in zip(batch,v)]);native_done=8
   admission=fit(time.time()-start,cp,len(chunks)-3,npf,math.ceil((504-8)/8));write(a.out/'MEASURED_ADMISSION.json',admission)
   if admission['status']=='NO_FIT':status='NO_FIT';break
 if status=='COMPLETE':
  require(len(captures)==504,'complete capture bank')
  for i in range(native_done,504,8):
   xs=items[i:i+8];v=timed('oracle_native',lambda xs=xs:b.native('oracle',np.array([captures[x['id']]for x in xs]),False));require(len(v)==len(xs)and all(len(g)==1 for g in v),'onegreedy Oracle')
   write(a.out/'oracle'/f'{i:04d}.json',[dict(id=x['id'],output=g[0])for x,g in zip(xs,v)])
  require(sum(len(read(p))for p in(a.out/'oracle').glob('*.json'))==504,'exact full504 native bank')
 files=[p for p in a.out.rglob('*')if p.is_file()];first=min([p for p in files if p.suffix=='.npz'],key=lambda p:p.stat().st_mtime_ns)
 write(a.out/'OUTPUT_SEAL.json',dict(experiment='E114',status=status,source_sha256=a.source_sha256,input_sha256=a.input_sha256,model_revision='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9',oracle_block=44,greedy_max_new_tokens=128,capture_items=len(captures),native_outputs=sum(len(read(p))for p in(a.out/'oracle').glob('*.json')),original_504_inputs_no_sampling=True,labels_cpu_only=True,shared_base_adapter_disabled_for_capture=True,first_output_evidence=dict(member=str(first.relative_to(a.out)),mtime_ns=first.stat().st_mtime_ns,sha256=sha(first)),files={str(p.relative_to(a.out)):sha(p)for p in files}))
def main():
 p=argparse.ArgumentParser()
 for k in ['inputs','assets','assignment','out']:p.add_argument('--'+k,type=Path,required=True)
 for k in ['input-sha256','source-sha256']:p.add_argument('--'+k,required=True)
 a=p.parse_args();end=read(a.assignment)['absolute_deadline_epoch'];t=threading.Timer(max(0,end-time.time()-10),lambda:os.kill(os.getpid(),signal.SIGKILL));t.daemon=True;t.start()
 try:run(a,OracleRuntime(a.assets))
 finally:t.cancel()
if __name__=='__main__':main()
