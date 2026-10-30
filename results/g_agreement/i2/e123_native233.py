"""E123 original unhooked H44/H52 only; no recapture, labels, hooks or scores."""
import argparse,json,hashlib,time,threading,signal,os
from pathlib import Path
import numpy as np

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.new');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def validate(root,digest):
 assert sha(root/'INPUT_SEAL.json')==digest;s=read(root/'INPUT_SEAL.json');assert s['experiment']=='E123'and s['labels_on_pod']is False and s['condition']=='unhooked'
 for n,h in s['files'].items():assert sha(root/n)==h
 xs=read(root/'items.json');assert len(xs)==134 and len({x['id']for x in xs})==134 and all(set(x)=={'id','vector_index'}and x['vector_index']==i for i,x in enumerate(xs));arrays={l:np.load(root/f'H{l}.npy',allow_pickle=False)for l in (44,52)}
 assert all(h.shape==(134,5120)and h.dtype==np.float32 and np.isfinite(h).all()for h in arrays.values());return xs,arrays

def main():
 p=argparse.ArgumentParser()
 for n in ('inputs','assets','assignment','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
 for n in ('input-sha','source-sha','operator-sha'):p.add_argument('--'+n,required=True)
 p.add_argument('--validate-only',action='store_true');a=p.parse_args();assert sha(__file__)==a.operator_sha and sha(a.source_seal)==a.source_sha
 for n,d in read(a.source_seal)['files'].items():assert sha(n)==d
 xs,arrays=validate(a.inputs,a.input_sha)
 from projects.g_agreement.e101.runner import dependencies
 Runtime=dependencies()[1]
 from projects.g_agreement.e101.runner109 import backend87
 if a.validate_only:return
 ass=read(a.assignment);assert ass['experiment']=='E123'and ass['source_sha256']==a.source_sha and ass['input_sha256']==a.input_sha and ass['assets_sha256']==sha(a.assets)and ass['pod_id']==os.environ.get('RUNPOD_POD_ID')and ass['allocation_verified']and ass['daily_budget_verified'];assert ass['gpu_type']=='H200'and ass['absolute_deadline_epoch']==ass['pod_created_epoch']+ass['cap_seconds']and ass['cap_seconds']*5.29/3600<=25 and ass['pod_created_epoch']<1793296800
 import torch
 assert torch.cuda.is_available()and torch.cuda.device_count()==1 and 'H200'in torch.cuda.get_device_name(0)
 a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);status='FAILED';times=[];index=[];timer=threading.Timer(max(0,ass['absolute_deadline_epoch']-time.time()-30),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  start=time.monotonic();rt=Runtime(a.assets);rt.load_oracle();torch.cuda.synchronize();write(a.out/'SETUP.json',dict(oracle_only=True,seconds=time.monotonic()-start))
  from mats.readers.olens import TRAINED_LAYERS
  assert {44,52}<=set(TRAINED_LAYERS);B=backend87();jobs=[(l,list(range(k,min(k+8,134))))for l in (44,52)for k in range(0,134,8)];write(a.out/'JOB_GRID.json',jobs)
  for job,(layer,ix)in enumerate(jobs):
   assert time.time()<ass['absolute_deadline_epoch']-60,'NO_FIT original reserve'
   h=arrays[layer][ix].copy();before=h.tobytes();start=time.monotonic();rr=B.sweep(rt,'oracle',h,layer);torch.cuda.synchronize();times.append(time.monotonic()-start);assert h.tobytes()==before and len(rr)==len(ix)
   member=f'jobs/{job:06d}.json';write(a.out/member,[dict(z,id=xs[i]['id']+':oracle:'+str(layer),item_id=xs[i]['id'],source_layer=layer,source_vector_index=i,condition='unhooked',reader='oracle',gpu_type='H200')for z,i in zip(rr,ix)]);index.extend(dict(id=xs[i]['id'],source_layer=layer,member=member,index=k)for k,i in enumerate(ix));write(a.out/'PROGRESS.json',dict(completed=len(index),planned=268));write(a.out/'TIMINGS.json',times)
   pending=len(jobs)-job-1;need=1.25*(time.time()-ass['pod_created_epoch']+pending*max(times))+60;write(a.out/'FORECAST.json',dict(projected_total_cap_seconds=need,max_measured_batch_seconds=max(times),remaining_full_batches=pending,total_full_batches=len(jobs),elapsed_including_staging=time.time()-ass['pod_created_epoch'],margin=1.25,reserve_seconds=60))
   if pending and ass['pod_created_epoch']+need>ass['absolute_deadline_epoch']:status='NO_FIT';break
  else:status='COMPLETE'
  write(a.out/'INDEX.json',index)
 except BaseException as e:write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:400]));raise
 finally:
  timer.cancel();files=[p for p in a.out.rglob('*')if p.is_file()and p.name!='OUTPUT_SEAL.json'];real=list((a.out/'jobs').glob('*.json'));first=min(real,key=lambda p:p.stat().st_mtime_ns)if real else None
  write(a.out/'OUTPUT_SEAL.json',dict(experiment='E123',status=status,source_sha256=a.source_sha,input_sha256=a.input_sha,operator_sha256=a.operator_sha,captures=0,subject_forward_calls=0,judging_calls=0,labels_cpu_only=True,outputs_unopened=True,first_output_utc=__import__('datetime').datetime.fromtimestamp(first.stat().st_mtime,__import__('datetime').timezone.utc).isoformat()if first else'unknown',first_output_evidence=dict(member=str(first.relative_to(a.out)),sha256=sha(first),mtime_ns=first.stat().st_mtime_ns)if first else None,files={str(p.relative_to(a.out)):sha(p)for p in files}))
if __name__=='__main__':main()
