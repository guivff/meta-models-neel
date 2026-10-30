"""≤1440s original custody; model/adapter unchanged; no probing or judging."""
import argparse,os,signal,threading,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from projects.g_agreement.e101.contract import read,write,sha,verify
from projects.g_agreement.e101.runner import ROOT,dependencies,output_provenance
from .capture import capture_lens
from .build import ROWS
from .protocol import cap_valid


def load(root):
    s=verify(root,'INPUT_SEAL.json',sha(root/'INPUT_SEAL.json'))
    names={'items.json','h44.npy','MANIFEST.json'}
    if s['experiment']!='E113' or s['labels_on_pod'] is not False or set(s['files'])!=names or {p.name for p in root.iterdir()}!=names|{'INPUT_SEAL.json'}:raise ValueError('public-only E113 input')
    items=read(root/'items.json');h=np.load(root/'h44.npy',allow_pickle=False)
    if h.shape!=(1008,5120) or h.dtype!=np.float32 or not np.isfinite(h).all() or len(items)!=1008 or len({x['id'] for x in items})!=1008:raise ValueError('complete original carrier grid')
    for row in ROWS:
        for split in ('dev','test'):
            if sum(x['row']==row and x['split']==split for x in items)!=84:raise ValueError('84 dev/test per row')
    for i,x in enumerate(items):
        if set(x)!={'id','base_id','row','split','vector_index','block'} or x['vector_index']!=i or x['block']!=44:raise ValueError('label-free native read sites')
    return items,h


def acquire(items,h,runtime,out,end):
    import torch
    (out/'states').mkdir();events=[];index=[];cost=[]
    start=time.monotonic();runtime.load_oracle();torch.cuda.synchronize()
    events.append(dict(phase='oracle_setup',seconds=time.monotonic()-start))
    lens=runtime.readers.oracle;start=time.monotonic()
    capture_lens(lens,np.random.default_rng(20261029).standard_normal((1,h.shape[1])).astype(np.float32))
    torch.cuda.synchronize();events.append(dict(phase='discarded_warmup',seconds=time.monotonic()-start))
    write(out/'SETUP.json',events)
    jobs=list(range(0,len(items),8))
    for job,start in enumerate(jobs):
        if time.time()>=end:return 'NO_FIT'
        begin=time.monotonic();part=h[start:start+8].copy();before=part.tobytes()
        values,tokens,metadata=capture_lens(lens,part)
        if part.tobytes()!=before:raise ValueError('carrier vectors mutated')
        member=f'states/{job:04d}.npy';np.save(out/member,values,allow_pickle=False)
        for k,x in enumerate(items[start:start+8]):index.append(dict(x,member=member,vector_index_in_file=k,first_token_id=int(tokens[k,0])))
        torch.cuda.synchronize();cost.append(time.monotonic()-begin)
        if job==0:write(out/'CAPTURE_FORMAT.json',dict(metadata,shape='[items,lens_layers,positions,hidden_dimension]',dtype='float32',model_dtype=str(next(lens.model.parameters()).dtype)))
        from admission import atomic
        atomic(out/'PROGRESS.json',dict(completed_items=len(index),jobs=job+1,total_jobs=len(jobs),mean_batch_seconds=float(np.mean(cost)),remaining_seconds=1.25*(len(jobs)-job-1)*float(np.mean(cost))))
        if time.time()+1.25*(len(jobs)-job-1)*float(np.mean(cost))>=end:return 'NO_FIT'
    write(out/'INDEX.json',index);write(out/'BATCH_TIMINGS.json',cost);return 'COMPLETE'


def main():
    p=argparse.ArgumentParser()
    for n in ('inputs','assets','assignment','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('input-sha','source-sha'):p.add_argument('--'+n,required=True)
    a=p.parse_args();verify(ROOT,str(a.source_seal.resolve().relative_to(ROOT)),a.source_sha);verify(a.inputs,'INPUT_SEAL.json',a.input_sha)
    items,h=load(a.inputs);ass=read(a.assignment)
    if (ass['experiment']!='E113' or not cap_valid(ass) or ass['pod_id']!=os.environ.get('RUNPOD_POD_ID')
        or ass['daily_budget_verified'] is not True
        or ass['input_sha256']!=a.input_sha or ass['source_sha256']!=a.source_sha or ass['assets_sha256']!=sha(a.assets)):raise ValueError('original custody/source/input/assets and budget binding')
    old,Runtime,gate,bind,finite=dependencies();bind(ass,ROWS);hardware=gate(ass,None,a.assets,['oracle'])
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);write(a.out/'HARDWARE.json',hardware)
    timer=threading.Timer(max(0,ass['absolute_deadline_epoch']-time.time()-150),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='FAILED'
    try:
        runtime=Runtime(a.assets);runtime.hardware_assignment=ass
        status=acquire(items,h,runtime,a.out,ass['absolute_deadline_epoch']-180)
    except BaseException as e:write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:300]));raise
    finally:
        timer.cancel()
        files=list((a.out/'states').glob('*.npy'));first=min(files,key=lambda p:p.stat().st_mtime_ns) if files else None
        provenance=dict(first_output_utc=datetime.fromtimestamp(first.stat().st_mtime,timezone.utc).isoformat() if first else 'unknown',first_output_evidence=dict(member=str(first.relative_to(a.out)),sha256=sha(first),mtime_ns=first.stat().st_mtime_ns) if first else None)
        write(a.out/'OUTPUT_SEAL.json',dict(experiment='E113',status=status,input_sha256=a.input_sha,source_sha256=a.source_sha,
          gpu_type=hardware['gpu_type'],model_or_judge_training=False,judging=False,**provenance,
          files={str(p.relative_to(a.out)):sha(p) for p in a.out.rglob('*') if p.is_file()}))

if __name__=='__main__':main()
