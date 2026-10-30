"""Integrator-only E42 base-model greedy acquisition; 1,800 s total custody."""
import argparse,os,signal,time,math
from pathlib import Path
from io42 import *
MODEL='Qwen/Qwen3.6-27B';REVISION='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
TOKENIZER='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
BATCH=32;CAP=1800

def warmed_forecast(times, remaining_units):
 """Cold first batch is charged but never extrapolated to remaining items."""
 warmed = times[1:]
 return (sum(warmed)/len(warmed))*remaining_units if warmed else None

def record_batch_timing(stream, batch_index, batch_items, times, remaining_units):
 forecast=warmed_forecast(times,remaining_units)
 stream.write(__import__('json').dumps({'batch_index':batch_index,'items':batch_items,
  'seconds':times[-1],'cold':batch_index==0,'remaining_batches':remaining_units,
  'warmed_mean_seconds':sum(times[1:])/len(times[1:]) if len(times)>1 else None,
  'forecast_remaining_seconds':forecast,'gate_remaining_seconds':1.5*forecast if forecast is not None else None})+'\n')
 stream.flush()
 return forecast

def run(a):
 import torch
 from transformers import AutoModelForCausalLM,AutoTokenizer,GenerationConfig
 q=read(a.assignment);plan=read(a.plan);assets=read(a.assets)
 if q.get('issuer')!='integrator' or q.get('experiment')!='E42' or q.get('pod_id')!=os.environ.get('RUNPOD_POD_ID') or not q.get('pod_id'):raise ValueError('integrator pod required')
 if q.get('plan_sha256')!=sha(a.plan) or q.get('assets_manifest_sha256')!=sha(a.assets) or q.get('previous_gpu_seconds')!=0:raise ValueError('assignment identity/retry')
 if not all(q.get(k) is True for k in ['external_hardstop_verified','state_functions_committed','source_published']):raise ValueError('publication/hardstop gate')
 start=q['provider_created_epoch'];deadline=q['deadline_epoch'];stop=deadline-60
 if not start<=time.time()<stop or not 0<deadline-start<=CAP:raise ValueError('aggregate cap')
 def halt(*_):raise TimeoutError('E42 custody deadline')
 signal.signal(signal.SIGALRM,halt);signal.setitimer(signal.ITIMER_REAL,stop-time.time())
 with a.assignment.with_suffix('.once.lock').open('x') as f:f.write(sha(a.plan))
 verify(a.stage,'INPUT_SEAL.json',plan['input_seal_sha256'])
 for n,h in plan['source_files'].items():
  if sha(ROOT/n)!=h:raise ValueError('source identity '+n)
 items=rows(a.stage/'prefixes.jsonl')
 if len(items)!=3444 or len({r['key'] for r in items})!=3444:raise ValueError('scope')
 path=Path(assets['model_path'])
 if assets.get('model_id')!=MODEL or assets.get('revision')!=REVISION or assets.get('adapter') is not None or assets.get('injection') is not None or (path/'adapter_config.json').exists():raise ValueError('base-only assets')
 required=set(read(path/'model.safetensors.index.json')['weight_map'].values())|{'model.safetensors.index.json','config.json','tokenizer.json','tokenizer_config.json'}
 if not required<=set(assets['files']):raise ValueError('incomplete asset manifest')
 for n,h in assets['files'].items():
  if Path(n).is_absolute() or '..' in Path(n).parts or sha(path/n)!=h:raise ValueError('asset hash')
 if sha(path/'tokenizer.json')!=TOKENIZER or not torch.cuda.is_available():raise ValueError('tokenizer/CUDA')
 a.out.mkdir(parents=True,exist_ok=False)
 try:
  torch.manual_seed(20261026);torch.cuda.manual_seed_all(20261026)
  tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
  model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,dtype=torch.bfloat16,device_map='cuda').eval()
  if hasattr(model,'peft_config'):raise ValueError('adapter forbidden')
  # Exactly 32 model-generated tokens. EOS stopping is disabled, not padded after early EOS.
  config=GenerationConfig(do_sample=False,num_beams=1,max_new_tokens=32,min_new_tokens=32,eos_token_id=None,forced_eos_token_id=None,pad_token_id=tok.pad_token_id or 0,use_cache=True)
  times=[];first=time.time();units=math.ceil(len(items)/BATCH)
  with (a.out/'continuations.jsonl').open('x') as f, (a.out/'batch_timings.jsonl').open('x') as timing:
   for k in range(units):
    batch=items[k*BATCH:(k+1)*BATCH];width=max(len(r['ids']) for r in batch)
    ids=torch.tensor([[config.pad_token_id]*(width-len(r['ids']))+r['ids'] for r in batch],device='cuda')
    mask=torch.tensor([[0]*(width-len(r['ids']))+[1]*len(r['ids']) for r in batch],device='cuda')
    t=time.time()
    with torch.inference_mode():generated=model.generate(input_ids=ids,attention_mask=mask,generation_config=config)[:,width:]
    torch.cuda.synchronize();times.append(time.time()-t)
    if generated.shape!=(len(batch),32):raise ValueError('exact horizon')
    for item,tokens in zip(batch,generated.tolist()):
     f.write(__import__('json').dumps({'key':item['key'],'following_ids':tokens,'prefix_ids_sha256':__import__('hashlib').sha256(__import__('json').dumps(item['ids'],separators=(',',':')).encode()).hexdigest()})+'\n')
    f.flush()
    # The first batches ARE production; no repeated item generation for warming.
    forecast=record_batch_timing(timing,k,len(batch),times,units-k-1)
    if forecast is not None and time.time()+1.5*forecast>stop:raise TimeoutError('full-scope warmed forecast cannot fit; no retry')
  dump(a.out/'PROVENANCE.json',{'experiment':'E42','status':'COMPLETE','plan_sha256':sha(a.plan),'input_seal_sha256':plan['input_seal_sha256'],'state_seal_sha256':plan['state_seal_sha256'],'assignment_sha256':sha(a.assignment),'assets_sha256':sha(a.assets),'model':MODEL,'revision':REVISION,'seed':20261026,'source':'model-expected continuation','greedy':True,'tokens':32,'EOS_stopping':False,'items':len(items),'total_custody_seconds':time.time()-start,'science_seconds':time.time()-first})
  seal(a.out,['continuations.jsonl','PROVENANCE.json','batch_timings.jsonl'],'FOLLOWING_TEXT_SEAL.json')
 finally:signal.setitimer(signal.ITIMER_REAL,0)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['plan','stage','assignment','assets','out']:p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
