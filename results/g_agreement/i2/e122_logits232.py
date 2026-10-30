"""E122a: original E105 supplied-vector continuation scorer; no selection or analysis.
All four branches and token sums are retained. T/S is never invoked here.
"""
import argparse,json,hashlib,time,threading,signal,os,math
from pathlib import Path
import numpy as np

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.new');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def validate(root,expected):
 assert sha(root/'INPUT_SEAL.json')==expected;s=read(root/'INPUT_SEAL.json');assert s['experiment']=='E122'and s['labels_on_pod']is False
 for n,h in s['files'].items():assert sha(root/n)==h
 xs=read(root/'items.json');h=np.load(root/'H44.npy',allow_pickle=False);contract=read(root/'CONTRASTS.json');pairs=[[x['positive']['token_ids'],x['negative']['token_ids']]for x in contract['contrasts']]
 assert len(xs)==600 and len({x['id']for x in xs})==600 and h.shape==(600,5120)and h.dtype==np.float32 and np.isfinite(h).all()
 assert sum(x['split']=='dev'for x in xs)==200 and sum(x['split']=='test'for x in xs)==400
 assert len(pairs)==4
 for i,x in enumerate(xs):
  assert set(x)=={'id','ids','read_index','split','row','block','vector_index','candidate_ids'}and x['vector_index']==i and x['block']==44 and x['read_index']==len(x['ids'])-1 and x['candidate_ids']==pairs
 return xs,h,contract

def main():
 p=argparse.ArgumentParser()
 for n in ('inputs','assets','assignment','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
 for n in ('input-sha','source-sha','operator-sha'):p.add_argument('--'+n,required=True)
 p.add_argument('--validate-only',action='store_true');a=p.parse_args();assert sha(__file__)==a.operator_sha and sha(a.source_seal)==a.source_sha
 for n,h in read(a.source_seal)['files'].items():assert sha(n)==h
 scorer=Path('projects/g_agreement/e101/acquisition.py');assert sha(scorer)=='932c62afbaa4eb7f219d75292529ad27224562a9324591b06f033f09bf01c73a'
 xs,h,contract=validate(a.inputs,a.input_sha)
 from projects.g_agreement.e101.runner import dependencies
 Runtime=dependencies()[1]
 from projects.g_agreement.e101.acquisition import behaviour,batches
 if a.validate_only:return
 ass=read(a.assignment);assert ass['experiment']=='E122'and ass['source_sha256']==a.source_sha and ass['input_sha256']==a.input_sha and ass['assets_sha256']==sha(a.assets)and ass['pod_id']==os.environ.get('RUNPOD_POD_ID')and ass['allocation_verified']and ass['daily_budget_verified'];assert ass['gpu_type']=='H200'and ass['absolute_deadline_epoch']==ass['pod_created_epoch']+ass['cap_seconds']and ass['cap_seconds']*5.29/3600<=25 and ass['pod_created_epoch']<1793296800
 import torch
 assert torch.cuda.is_available()and torch.cuda.device_count()==1 and 'H200'in torch.cuda.get_device_name(0)
 a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);write(a.out/'CONTRAST_ORDER.json',dict(contrasts=[x['id']for x in contract['contrasts']],pair_order=['positive','negative'],score='sum natural log probabilities over EVERY candidate token, no mean/no appended EOS',dev_selection='CPU only, frozen before first test opening',transplant_stage='NOT RUN until separately sealed R-BEV1 PASS'))
 timer=threading.Timer(max(0,ass['absolute_deadline_epoch']-time.time()-30),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='FAILED';times=[]
 try:
  start=time.monotonic();rt=Runtime(a.assets);rt.load_base();torch.cuda.synchronize();write(a.out/'SETUP.json',dict(seconds=time.monotonic()-start))
  jobs=sorted(batches(xs,8),key=lambda ix:(len(xs[ix[0]]['ids']),len(ix)),reverse=True);write(a.out/'JOB_GRID.json',jobs);index=[]
  for job,ix in enumerate(jobs):
   assert time.time()<ass['absolute_deadline_epoch']-60,'NO_FIT original custody reserve'
   part=h[ix].copy();before=part.tobytes();start=time.monotonic();model,_,cm=rt.subject()
   with cm:rr=behaviour(model,[xs[i]for i in ix],part,'continuation')
   torch.cuda.synchronize();times.append(time.monotonic()-start);assert part.tobytes()==before and len(rr)==len(ix)
   for z in rr:assert len(z['pair_logprobs'])==4 and np.isfinite(np.asarray(z['pair_logprobs'])).all()
   member=f'jobs/{job:06d}.json';write(a.out/member,[dict(z,id=xs[i]['id'],source_block=44,split=xs[i]['split'],gpu_type='H200')for z,i in zip(rr,ix)]);index.extend(dict(id=xs[i]['id'],member=member,index=k)for k,i in enumerate(ix));write(a.out/'PROGRESS.json',dict(completed=len(index),planned=600,jobs=job+1));write(a.out/'TIMINGS.json',times)
   pending=len(jobs)-job-1;need=1.25*(time.time()-ass['pod_created_epoch']+pending*max(times))+60;write(a.out/'FORECAST.json',dict(projected_total_cap_seconds=need,max_measured_batch_seconds=max(times),remaining_full_batches=pending,elapsed_including_staging=time.time()-ass['pod_created_epoch'],margin=1.25,reserve_seconds=60))
   if pending and ass['pod_created_epoch']+need>ass['absolute_deadline_epoch']:status='NO_FIT';break
  else:status='COMPLETE'
  write(a.out/'INDEX.json',index)
 except BaseException as e:write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:400]));raise
 finally:
  timer.cancel();files=[p for p in a.out.rglob('*')if p.is_file()and p.name!='OUTPUT_SEAL.json'];real=list((a.out/'jobs').glob('*.json'));first=min(real,key=lambda p:p.stat().st_mtime_ns)if real else None
  write(a.out/'OUTPUT_SEAL.json',dict(experiment='E122',part='a',status=status,source_sha256=a.source_sha,input_sha256=a.input_sha,operator_sha256=a.operator_sha,original_E105_scorer_sha256=sha(scorer),readout_or_judging_calls=0,labels_cpu_only=True,outputs_unopened=True,T_S_transplants_invoked=False,first_output_utc=__import__('datetime').datetime.fromtimestamp(first.stat().st_mtime,__import__('datetime').timezone.utc).isoformat()if first else'unknown',first_output_evidence=dict(member=str(first.relative_to(a.out)),sha256=sha(first),mtime_ns=first.stat().st_mtime_ns)if first else None,files={str(p.relative_to(a.out)):sha(p)for p in files}))
if __name__=='__main__':main()
