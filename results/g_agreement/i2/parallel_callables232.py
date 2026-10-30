"""I2 outer custody binding of original C E116/E120/E121/E120c callables.
No label joins, fitting, judging or statistical decisions on GPU. Real trials
retain original cells; NO_FIT partials are sealed and excluded from fresh attempts.
"""
import argparse,json,hashlib,time,os,signal,threading,math,sys
from pathlib import Path
import numpy as np

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.new');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def verify(root,name,digest):
 p=Path(root)/name;assert sha(p)==digest
 d=read(p)
 for n,h in d['files'].items():assert sha(Path(root)/n)==h
 return d

def batches(items,size=8):
 groups={}
 for i,x in enumerate(items):groups.setdefault(len(x['ids']),[]).append(i)
 return [ix[k:k+size] for length,ix in sorted(groups.items())for k in range(0,len(ix),size)]

def forecast(created,deadline,now,remaining,observed):
 assert now>=created and all(n>=0 for n in remaining.values())
 assert all(not n or observed.get(k) for k,n in remaining.items()),'ALL_PENDING_PHASES_REQUIRE_MEASURED_PILOT'
 need=1.25*(now-created+sum(n*max(observed[k])for k,n in remaining.items()if n))+60
 return dict(status='ADMIT'if created+need<=deadline else'NO_FIT',projected_total_cap_seconds=need,elapsed_including_staging_setup_warmup_and_completed_calls=now-created,remaining_calls=remaining,max_observed_seconds={k:max(v)for k,v in observed.items()if v},margin=1.25,reserve_seconds=60,original_deadline=deadline)

class Custody:
 def __init__(self,a,out):self.a=a;self.out=out;self.events=[];self.observed={}
 def call(self,phase,f,measured=False):
  assert time.time()<self.a['absolute_deadline_epoch']-60,'NO_FIT_ABSOLUTE_RESERVE'
  t=time.monotonic();v=f()
  import torch
  torch.cuda.synchronize();dt=time.monotonic()-t;self.events.append(dict(phase=phase,seconds=dt));write(self.out/'TIMINGS.json',self.events)
  if measured:self.observed.setdefault(phase,[]).append(dt)
  return v
 def fit(self,remaining):
  f=forecast(self.a['pod_created_epoch'],self.a['absolute_deadline_epoch'],time.time(),remaining,self.observed);write(self.out/'FORECAST.json',f);return f['status']=='ADMIT'

def validate(experiment,part,root,input_sha):
 seal=verify(root,'INPUT_SEAL.json',input_sha);assert seal['labels_on_pod'] is False
 xs=read(root/'items.json');assert len(xs)==len({x['id']for x in xs})
 if experiment=='E116':assert len(xs)==376 and all(set(x)=={'id','ids','read_index'}for x in xs)
 elif experiment=='E121':
  assert len(xs)==168 and {x['condition']for x in xs}=={'steered','random'} and all(x['alpha']==8 for x in xs)
  assert len({x['base_id']for x in xs})==84
  assert all(set(x)<={'id','base_id','row','condition','ids','read_index','delta_index','alpha'}for x in xs)
 elif part in ('a','ab'):assert len(xs)==400 and all(x['split']=='test'and set(x)<={'id','ids','read_index','split'}for x in xs)
 else:
  assert len(xs)==(600 if part=='b'else 400)
  assert all(set(x)<={'id','base_id','row','split','vector_index','block'}for x in xs)
  assert all(x['vector_index']==i and x['block']==44 for i,x in enumerate(xs))
 if experiment in ('E116','E121')or part=='a':assert all(x['read_index']==len(x['ids'])-1 for x in xs)
 return xs

def runtime():
 from projects.g_agreement.e101.runner import dependencies
 return dependencies()[1]

def capture_and_read(xs,ass,assets,out,c,experiment,extra_decoder=None):
 from projects.g_agreement.e101 import runner109 as primitive
 from projects.g_agreement.e101 import intervention104 as upstream
 Runtime=runtime();rt=Runtime(assets);c.call('base_setup',rt.load_base);jobs=batches(xs);vectors={l:np.empty((len(xs),5120),dtype=np.float32)for l in ([42]if experiment=='E121'else[52,60])};index=[]
 if experiment=='E121':
  upstream.READ_BLOCK=42;delta=np.load(Path(ass['input_root'])/'deltas.npy',allow_pickle=False);assert delta.dtype==np.float32 and np.isfinite(delta).all()
 else:primitive.CAPTURE=(52,60)
 model,_,cm=rt.subject()
 for job,ix in enumerate(jobs):
  part=[xs[i]for i in ix]
  def call():
   with cm:
    if experiment=='E121':
     ds=delta[[x['delta_index']for x in part]].copy();before=ds.tobytes();_,mm,hh=upstream.intervene_forward(model,[x['ids']for x in part],[x['read_index']for x in part],ds,'U',1,observe=True);assert ds.tobytes()==before;return {42:hh},mm
    return primitive.natural_capture(model,part),None
  hh,mm=c.call('capture',call,True)
  for layer,values in hh.items():
   assert values.shape==(len(ix),5120)and values.dtype==np.float32 and np.isfinite(values).all();vectors[layer][ix]=values
   member=f'capture/{job:06d}_{layer}.npy';(out/'capture').mkdir(exist_ok=True);np.save(out/member,values,allow_pickle=False)
   index.extend(dict(id=xs[i]['id'],source_layer=layer,member=member,vector_index=k)for k,i in enumerate(ix))
  if mm is not None:write(out/f'capture/{job:06d}_norms.json',mm)
 write(out/'CAPTURE_INDEX.json',index)
 for layer,v in vectors.items():np.save(out/f'CAPTURE_{layer}.npy',v,allow_pickle=False)
 del model,cm;rt.model=rt.tok=None
 import gc,torch
 gc.collect();torch.cuda.empty_cache()
 planned=[(layer,list(range(k,min(k+8,len(xs)))))for layer in vectors for k in range(0,len(xs),8)]
 if experiment=='E121':
  from projects.g_agreement.e100.worker import backend
  b=backend(assets,ass);c.call('nla_setup',b.load_nla)
  def native(layer,v):return [x[0]for x in b.native_one('nla',v)]
 else:
  c.call('oracle_setup',rt.load_oracle);b87=primitive.backend87()
  from mats.readers.olens import TRAINED_LAYERS
  assert {52,60}<=set(TRAINED_LAYERS)
  def native(layer,v):return b87.sweep(rt,'oracle',v,layer)
 pilot=None
 if extra_decoder is not None:
  dx,dh=extra_decoder
  from projects.g_agreement.e113.capture import capture_lens
  part=dh[:8].copy();before=part.tobytes();values,tokens,metadata=c.call('decoder',lambda:capture_lens(rt.readers.oracle,part),True);assert part.tobytes()==before and values.shape==(8,64,2,5120)and np.isfinite(values).all()
  dp=out/'decoder';(dp/'states').mkdir(parents=True);np.save(dp/'states/0000.npy',values,allow_pickle=False);write(dp/'CAPTURE_FORMAT.json',metadata)
  pilot=[dict(x,member='states/0000.npy',vector_index_in_file=k,first_token_id=int(tokens[k,0]))for k,x in enumerate(dx[:8])]
 records=[]
 for job,(layer,ix)in enumerate(planned):
  v=vectors[layer][ix].copy();before=v.tobytes();rr=c.call('native',lambda:native(layer,v),True);assert len(rr)==len(ix)and v.tobytes()==before
  rows=[dict(z,id=xs[i]['id']+':'+('nla'if experiment=='E121'else'oracle')+':'+str(layer),item_id=xs[i]['id'],source_layer=layer,condition=xs[i].get('condition'),base_id=xs[i].get('base_id'),reader='nla'if experiment=='E121'else'oracle',gpu_type='H200')for i,z in zip(ix,rr)];write(out/f'jobs/{job:06d}.json',rows);records.extend(rows);write(out/'PROGRESS.json',dict(completed=len(records),planned=len(xs)*(1 if experiment=='E121'else 2)))
  if job+1<len(planned)and not c.fit(dict(native=len(planned)-job-1,**({'decoder':math.ceil(len(extra_decoder[0])/8)-1}if extra_decoder is not None else{}))):return 'NO_FIT'
 write(out/'READOUTS_INDEX.json',dict(items=len(xs),readouts=len(records),jobs=len(planned)))
 if extra_decoder is not None:return decoder(*extra_decoder,assets,out/'decoder',c,rt=rt,pilot=pilot)
 return 'COMPLETE'

def decoder(xs,h,assets,out,c,rt=None,pilot=None):
 from projects.g_agreement.e113.capture import capture_lens
 if rt is None:rt=runtime()(assets);c.call('oracle_setup',rt.load_oracle)
 lens=rt.readers.oracle;index=list(pilot or []);jobs=list(range(0,len(xs),8))
 for job,start in enumerate(jobs):
  if pilot and job==0:continue
  part=h[start:start+8].copy();before=part.tobytes();values,tokens,metadata=c.call('decoder',lambda:capture_lens(lens,part),True);assert part.tobytes()==before and values.shape==(len(part),64,2,5120)and np.isfinite(values).all()
  member=f'states/{job:04d}.npy';(out/'states').mkdir(exist_ok=True);np.save(out/member,values,allow_pickle=False)
  index.extend(dict(x,member=member,vector_index_in_file=k,first_token_id=int(tokens[k,0]))for k,x in enumerate(xs[start:start+8]))
  if job==0:write(out/'CAPTURE_FORMAT.json',metadata)
  write(out/'PROGRESS.json',dict(completed=len(index),planned=len(xs)))
  if job+1<len(jobs)and not c.fit({'decoder':len(jobs)-job-1}):return 'NO_FIT'
 write(out/'INDEX.json',index)
 # Lossless adapter layout, immutable original item order.
 for split in ('dev','test'):
  rows=[];order=[]
  for x in index:
   if x['split']==split:rows.append(np.load(out/x['member'],allow_pickle=False)[x['vector_index_in_file']]);order.append(x['id'])
  np.save(out/(split+'.npy'),np.stack(rows),allow_pickle=False);write(out/(split.upper()+'_ORDER.json'),order)
 return 'COMPLETE'

def questions(xs,h,assets,out,c,config):
 from projects.g_agreement.e100.worker import backend
 b=backend(assets,c.a);c.call('oracle_setup',b.load_oracle)
 from mats.readers.olens import OracleLens,Sampling
 import torch
 lenses={arm:OracleLens(b.oracle.model,b.oracle.tok,prompt=config['carrier_prefix']+' '+config['questions'][arm],alpha=16000,device=b.oracle.device)for arm in config['conditions']}
 jobs=[(arm,k)for arm in config['conditions']for k in range(0,len(xs),8)];index=[]
 for job,(arm,start)in enumerate(jobs):
  part=h[start:start+8].copy();before=part.tobytes()
  def call():
   with torch.inference_mode():return lenses[arm].verbalize(torch.as_tensor(part),44,k=1,sampling=Sampling(temperature=0,top_p=1.,top_k=0,max_new_tokens=128),batch=8)
  rr=c.call('native',call,True);assert len(rr)==len(part)and all(len(x)==1 for x in rr)and part.tobytes()==before
  rows=[dict(id=x['id']+':'+arm,item_id=x['id'],condition=arm,source_layer=44,reader='oracle',raw=z[0],text=z[0],gpu_type='H200')for x,z in zip(xs[start:start+8],rr)];write(out/f'jobs/{job:06d}.json',rows);index.extend(rows);write(out/'PROGRESS.json',dict(completed=len(index),planned=800))
  if job+1<len(jobs)and not c.fit({'native':len(jobs)-job-1}):return 'NO_FIT'
 return 'COMPLETE'

def main():
 p=argparse.ArgumentParser()
 for n in ('config','inputs','assets','assignment','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
 for n in ('source-sha','input-sha','operator-sha'):p.add_argument('--'+n,required=True)
 p.add_argument('--decoder-inputs',type=Path);p.add_argument('--decoder-sha');p.add_argument('--part',choices=('a','ab','b','c'),default='a');p.add_argument('--validate-only',action='store_true');a=p.parse_args();assert sha(__file__)==a.operator_sha
 cfg=read(a.config);exp=cfg['experiment'];ROOT=Path.cwd();verify(ROOT,str(a.source_seal),a.source_sha);xs=validate(exp,a.part,a.inputs,a.input_sha);extra=None
 if a.part=='ab':
  dx=validate('E120','b',a.decoder_inputs,a.decoder_sha);dh=np.load(a.decoder_inputs/'h44.npy',allow_pickle=False);assert dh.shape==(600,5120)and dh.dtype==np.float32 and np.isfinite(dh).all();extra=(dx,dh)
 if a.validate_only:return
 ass=read(a.assignment);assert ass['experiment']==exp and ass['pod_id']==os.environ.get('RUNPOD_POD_ID')and ass['gpu_type']=='H200'and ass['allocation_verified']and ass['daily_budget_verified'];assert ass['source_sha256']==a.source_sha and ass['input_sha256']==a.input_sha and ass['assets_sha256']==sha(a.assets);assert ass['absolute_deadline_epoch']==ass['pod_created_epoch']+ass['cap_seconds'] and ass['pod_created_epoch']<1793296800 and ass['cap_seconds']*5.29/3600<=25
 from projects.g_agreement.e100.worker import hardware
 hardware(ass);a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);write(a.out/'INVENTORY.json',dict(ids=[x['id']for x in xs],part=a.part,source_sha256=a.source_sha,input_sha256=a.input_sha));c=Custody(ass,a.out);status='FAILED'
 timer=threading.Timer(max(0,ass['absolute_deadline_epoch']-time.time()-30),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  ass['input_root']=str(a.inputs)
  if exp in ('E116','E121')or a.part in ('a','ab'):status=capture_and_read(xs,ass,a.assets,a.out,c,exp,extra_decoder=extra)
  else:
   h=np.load(a.inputs/'h44.npy',allow_pickle=False);assert h.shape==(len(xs),5120)and h.dtype==np.float32 and np.isfinite(h).all();status=decoder(xs,h,a.assets,a.out,c)if a.part=='b'else questions(xs,h,a.assets,a.out,c,cfg)
 except BaseException as e:write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:400]));raise
 finally:
  timer.cancel();files=[p for p in a.out.rglob('*')if p.is_file()and p.name!='OUTPUT_SEAL.json'];real=[p for p in files if p.parent.name in ('capture','jobs','states')];first=min(real,key=lambda p:p.stat().st_mtime_ns)if real else None
  write(a.out/'OUTPUT_SEAL.json',dict(experiment=exp,part=a.part,status=status,source_sha256=a.source_sha,input_sha256=a.input_sha,operator_sha256=a.operator_sha,labels_cpu_only=True,judging=False,outputs_unopened=True,first_output_utc=__import__('datetime').datetime.fromtimestamp(first.stat().st_mtime,__import__('datetime').timezone.utc).isoformat()if first else'unknown',first_output_evidence=dict(member=str(first.relative_to(a.out)),sha256=sha(first),mtime_ns=first.stat().st_mtime_ns)if first else None,files={str(p.relative_to(a.out)):sha(p)for p in files}))
if __name__=='__main__':main()
