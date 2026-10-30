"""Prospective E110 exact-public-input filtering, once under original1800s custody.
No source facts/labels/aliases/joins; selector and outcome analysis stay on CPU.
"""
import argparse,hashlib,json,time,os,signal,threading
from pathlib import Path
from collections import defaultdict
MODEL_REV='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
INPUT_ARCHIVE='f2f7cb9540487288b599093cdba7c99523b66c1d80d3839b5d09b1a69b6cad7a'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def groups(items,batch=64):
 assert len(items)==10917 and len({x['id']for x in items})==10917
 by=defaultdict(list)
 for x in items:
  assert set(x)=={'id','prompt','input_ids','read_position'} and type(x['prompt']) is str
  assert x['input_ids'] and all(type(v)is int and v>=0 for v in x['input_ids']) and x['read_position']==len(x['input_ids'])-1
  by[len(x['input_ids'])].append(x)
 chunks=[xs[i:i+batch]for length,xs in sorted(by.items(),reverse=True)for i in range(0,len(xs),batch)]
 return sorted(chunks,key=lambda xs:(len(xs)*len(xs[0]['input_ids']),len(xs)),reverse=True)
def fit(setup,measured,remaining,cap=1800):
 assert measured and all(x>0 for x in measured) and setup>=0 and remaining>=0
 need=setup+1.25*max(measured)*remaining+60
 return dict(setup_seconds=setup,max_measured_batch_seconds=max(measured),remaining_batches=remaining,margin=1.25,need_seconds=need,original_cap_seconds=cap,status='ADMIT'if need<=cap else'NO_FIT')
def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--inputs-sha256',required=True);p.add_argument('--assignment',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 ass=read(a.assignment);assert ass['experiment']=='E110_FILTER' and ass['cap_seconds']==1800 and ass['gpu_count']==1
 end=ass['absolute_deadline_epoch'];assert end==ass['pod_created_epoch']+1800 and time.time()<ass['pod_created_epoch']+900
 assert a.model.name==MODEL_REV and sha(a.inputs)==a.inputs_sha256
 items=read(a.inputs);batches=groups(items);a.out.mkdir(exist_ok=False);write(a.out/'ASSIGNMENT.json',ass)
 timer=threading.Timer(max(0,end-time.time()-10),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 import torch
 from transformers import AutoModelForCausalLM,AutoTokenizer
 assert torch.cuda.is_available() and torch.cuda.device_count()==1
 torch.manual_seed(20261029)
 tok=AutoTokenizer.from_pretrained(a.model,local_files_only=True)
 assert all(tok.encode(x['prompt'],add_special_tokens=False)==x['input_ids']for x in items),'FROZEN_RAW_TOKEN_BINDING'
 model=AutoModelForCausalLM.from_pretrained(a.model,local_files_only=True,dtype=torch.bfloat16,device_map='cuda').eval()
 assert time.time()<ass['pod_created_epoch']+900,'ORIGINAL_SETUP900'
 eos=model.generation_config.eos_token_id or tok.eos_token_id;eos=set(eos if isinstance(eos,(tuple,list)) else[eos])
 durations=[];allrows=[];admission=None
 for i,batch in enumerate(batches):
  assert time.time()<end-60,'ORIGINAL_FILTER_DEADLINE'
  if i==3:
   admission=fit(time.time()-ass['pod_created_epoch'],durations,len(batches)-i);write(a.out/'MEASURED_ADMISSION.json',admission)
   if admission['status']=='NO_FIT':break
  ids=torch.tensor([x['input_ids']for x in batch],device=model.get_input_embeddings().weight.device)
  torch.cuda.synchronize();started=time.monotonic()
  with torch.inference_mode():generated=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),do_sample=False,max_new_tokens=16,pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id)
  torch.cuda.synchronize();duration=time.monotonic()-started
  suffix=generated[:,ids.shape[1]:].cpu().tolist();rows=[]
  for x,tokens in zip(batch,suffix):
   stop=next((j for j,t in enumerate(tokens)if t in eos),None);kept=tokens[:stop+1]if stop is not None else tokens
   rows.append(dict(id=x['id'],raw=tok.decode(kept,skip_special_tokens=True),token_ids=kept,finish_reason='eos'if stop is not None else'length',max_new_tokens=16,do_sample=False,input_ids_sha256=hashlib.sha256(json.dumps(x['input_ids']).encode()).hexdigest()))
  write(a.out/'batches'/f'{i:06d}.json',rows);allrows.extend(rows);durations.append(duration)
 status='COMPLETE'if len(allrows)==10917 else'NO_FIT'
 if status=='COMPLETE':
  by={x['id']:x for x in allrows};assert len(by)==10917;write(a.out/'FILTER_OUTPUTS.json',[by[x['id']]for x in items])
 write(a.out/'TIMINGS.json',dict(batch_seconds=durations,completed_jobs=len(allrows),total_jobs=10917,profile_outputs_retained_no_replay=True))
 first=min((a.out/'batches').glob('*.json'),key=lambda p:p.stat().st_mtime_ns)
 write(a.out/'OUTPUT_SEAL.json',dict(experiment='E110_FILTER',status=status,model_revision=MODEL_REV,input_sha256=a.inputs_sha256,decoding=dict(do_sample=False,max_new_tokens=16,no_CoT=True),total_jobs=10917,completed_jobs=len(allrows),first_output_evidence=dict(member=str(first.relative_to(a.out)),mtime_ns=first.stat().st_mtime_ns,sha256=sha(first)),files={str(p.relative_to(a.out)):sha(p)for p in a.out.rglob('*')if p.is_file()}));timer.cancel()
if __name__=='__main__':main()
