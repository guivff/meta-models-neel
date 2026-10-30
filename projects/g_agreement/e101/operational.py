"""E79 operational wrapper shared by E101 text and E100 reader shards."""
import argparse,os,signal,threading,time
from pathlib import Path
import numpy as np
from .contract import read,write,sha,verify
from .runner import ROOT,dependencies,output_provenance
from .timing import admit,bind_profile


def run(experiment,load,acquire,capabilities,*,seed=20261028):
    p=argparse.ArgumentParser()
    for n in ('inputs','assets','assignment','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('input-sha','source-sha'):p.add_argument('--'+n,required=True)
    p.add_argument('--timing',action='store_true');p.add_argument('--profile',type=Path);p.add_argument('--hardware-receipt',type=Path)
    p.add_argument('--setup-profile',type=Path,action='append',default=[])
    a=p.parse_args();verify(ROOT,str(a.source_seal.resolve().relative_to(ROOT)),a.source_sha)
    verify(a.inputs,'INPUT_SEAL.json',a.input_sha)
    items,h=load(a.inputs);ass=read(a.assignment)
    if (ass['experiment']!=experiment or ass['input_sha256']!=a.input_sha or ass['source_sha256']!=a.source_sha
        or ass['assets_sha256']!=sha(a.assets) or ass['gpu_count']!=1 or ass['daily_budget_verified'] is not True
        or ass['pod_id']!=os.environ.get('RUNPOD_POD_ID') or ass['cap_seconds']<=0
        or ass['absolute_deadline_epoch']!=ass['pod_created_epoch']+ass['cap_seconds']):raise ValueError('fixed creation custody and bindings')
    if a.timing and a.setup_profile:raise ValueError('setup profiles are production admission only')
    admission=None if a.timing else admit(a.profile,ass,a.input_sha,a.source_sha,setup_profiles=a.setup_profile)
    old,Runtime,gate,bind,finite=dependencies();bind(ass,{x['row'] for x in items})
    hardware=gate(ass,a.hardware_receipt,a.assets,capabilities)
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);write(a.out/'HARDWARE.json',hardware)
    if admission is not None:write(a.out/'CAP_ADMISSION.json',admission)
    write(a.out/'STAGING.json',dict(seconds=max(0,time.time()-ass['pod_created_epoch'])))
    end=ass['absolute_deadline_epoch'];timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='FAILED'
    try:
        import torch
        torch.manual_seed(seed);np.random.seed(seed)
        runtime=Runtime(a.assets);runtime.hardware_assignment=ass
        status=acquire(items,h,runtime,old.Clock(a.out,end),a.out,a.timing)
        if a.timing:bind_profile(a.out,ass,a.input_sha,a.source_sha,hardware)
        if any(not finite(read(f)) for f in (a.out/'jobs').glob('*.json')):raise ValueError('finite acquisition output')
    except BaseException as e:
        status='FAILED';write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:300]));raise
    finally:
        timer.cancel()
        write(a.out/'OUTPUT_SEAL.json',dict(experiment=experiment,status=status,seed=seed,input_sha256=a.input_sha,source_sha256=a.source_sha,
            gpu_type=hardware['gpu_type'],actual_gpu_name=hardware['actual_gpu_name'],pod_id=ass['pod_id'],completed_epoch=time.time(),**output_provenance(a.out),
            files={str(f.relative_to(a.out)):sha(f) for f in a.out.rglob('*') if f.is_file()}))
