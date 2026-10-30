"""§213 dedicated, once-only dev40 capture; no profiling, dose run, or readers."""
import argparse,os,signal,threading,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from .contract import read,write,sha,verify
from .contract104 import SEED
from .runner import ROOT,dependencies
CAP_SECONDS=1800
REQUEST=ROOT/'results/g_agreement/understand/e104/vectors/REQUEST.json'


def load_capture(inputs,input_sha):
    request=read(REQUEST);seal=verify(inputs,'INPUT_SEAL.json',input_sha)
    if input_sha!=request['public_input_sha256']:raise ValueError('exact registered dev40 packet')
    if (inputs/'CAPTURE_ONCE.json').exists():raise FileExistsError('dev40 CAPTURE_ONCE exists; no replay')
    if (set(seal['files'])!={'items.json'} or {p.name for p in inputs.iterdir()}!={'items.json','INPUT_SEAL.json'}
        or seal['experiment']!='E104' or seal['stage']!='dev_direction40' or seal['block']!=40 or seal['position']!='read_token'
        or seal['labels_on_pod'] is not False):raise ValueError('dev-only public capture members')
    xs=read(inputs/'items.json')
    if len(xs)!=request['records'] or len({x['id'] for x in xs})!=len(xs):raise ValueError('exact frozen dev40 inventory')
    for x in xs:
        if (set(x)!={'id','ids','read_index'} or len(x['ids'])<9 or x['read_index']!=len(x['ids'])-1
            or any(type(t)is not int or t<0 for t in x['ids'])):raise ValueError('label-free frozen dev capture tokens')
    return request


def validate_assignment(ass,input_sha,source_sha,assets_sha):
    if (ass['experiment']!='E104' or ass['stage']!='dev_direction40' or ass['capture_once'] is not True
        or ass['input_sha256']!=input_sha or ass['source_sha256']!=source_sha or ass['assets_sha256']!=assets_sha
        or ass['gpu_count']!=1 or ass['daily_budget_verified'] is not True or ass['cap_seconds']!=CAP_SECONDS
        or ass['pod_id']!=os.environ.get('RUNPOD_POD_ID') or ass['custody_start_epoch']!=ass['pod_created_epoch']
        or ass['absolute_deadline_epoch']!=ass['pod_created_epoch']+CAP_SECONDS):raise ValueError('dedicated once-only capture custody/bindings, cap1800s')


def warm_capture(runtime):
    import torch
    from mats.capture import capture
    model,tok,cm=runtime.subject();token=tok.encode(' the',add_special_tokens=False)[0]
    with cm,torch.inference_mode():values=capture(model,[[token]*32],[40],[[31]],batch_size=1,pad_id=tok.pad_token_id or 0)
    h=values[40]
    if tuple(h.shape)!=(1,1,5120) or not bool(torch.isfinite(h).all()):raise ValueError('finite synthetic block40 warm-up')


def acquire_capture(inputs,input_sha,runtime,clock,out):
    """Exactly one call of the owner's capture_once, after base-only setup/warm-up."""
    from projects.g_agreement.e104_vectors.build import capture_once
    # Check again before model loading; a fresh output path cannot bypass the input guard.
    load_capture(inputs,input_sha)
    clock.call('capture40_setup',runtime.load_base)
    clock.call('capture40_warmup_discarded',lambda:warm_capture(runtime))
    capture_once(runtime,inputs,input_sha,out/'capture40',clock)
    seal=verify(out/'capture40','CAPTURE_SEAL.json',sha(out/'capture40/CAPTURE_SEAL.json'))
    if seal['status']!='COMPLETE' or seal['input_sha256']!=input_sha:raise ValueError('complete bound dev40 capture')
    return 'COMPLETE'


def provenance(out):
    p=out/'capture40/acts40.npy'
    if not p.exists():return dict(first_output_utc='unknown',first_output_evidence=None)
    return dict(first_output_utc=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),
        first_output_evidence=dict(member=str(p.relative_to(out)),sha256=sha(p),mtime_ns=p.stat().st_mtime_ns,source='raw_capture_file_mtime'))


def main(argv=None):
    p=argparse.ArgumentParser(description='E104 once-only dev40 capture, dedicated1800s pod; no --timing or dose stage')
    p.add_argument('--capture-dev40',type=Path,required=True);p.add_argument('--capture-sha',required=True);p.add_argument('--capture-out',type=Path,required=True)
    for name in ('assets','assignment','source-seal'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source-sha',required=True);p.add_argument('--hardware-receipt',type=Path);a=p.parse_args(argv)
    verify(ROOT,str(a.source_seal.resolve().relative_to(ROOT)),a.source_sha);request=load_capture(a.capture_dev40,a.capture_sha)
    ass=read(a.assignment);validate_assignment(ass,a.capture_sha,a.source_sha,sha(a.assets))
    old,Runtime,gate,bind,finite=dependencies();bind(ass,set(request['rows']))
    # Pure subject-model capture: B200 requires the registered base-text smoke.
    hardware=gate(ass,a.hardware_receipt,a.assets,['text'])
    a.capture_out.mkdir(parents=True,exist_ok=False);write(a.capture_out/'ASSIGNMENT.json',ass);write(a.capture_out/'HARDWARE.json',hardware)
    write(a.capture_out/'RUN.json',dict(experiment='E104',stage='dev_direction40',seed=SEED,block=40,position='read_token',records=request['records'],
        capture_once=True,profiling=False,cap_seconds=CAP_SECONDS,input_sha256=a.capture_sha,source_sha256=a.source_sha))
    end=ass['absolute_deadline_epoch'];timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='FAILED'
    try:
        import torch
        torch.manual_seed(SEED);np.random.seed(SEED)
        runtime=Runtime(a.assets);runtime.hardware_assignment=ass
        status=acquire_capture(a.capture_dev40,a.capture_sha,runtime,old.Clock(a.capture_out,end),a.capture_out)
        if not finite(np.load(a.capture_out/'capture40/acts40.npy',allow_pickle=False)):raise ValueError('non-finite block40 capture')
    except BaseException as error:
        status='FAILED';write(a.capture_out/'FAILURE.json',dict(type=type(error).__name__,message=str(error)[:300]));raise
    finally:
        timer.cancel()
        marker=a.capture_dev40/'CAPTURE_ONCE.json'
        if marker.exists():(a.capture_out/'CAPTURE_ONCE.json').write_bytes(marker.read_bytes())
        write(a.capture_out/'OUTPUT_SEAL.json',dict(experiment='E104',stage='dev_direction40',status=status,seed=SEED,capture_once=True,profiling=False,
            input_sha256=a.capture_sha,source_sha256=a.source_sha,pod_id=ass['pod_id'],gpu_type=hardware['gpu_type'],actual_gpu_name=hardware['actual_gpu_name'],
            completed_epoch=time.time(),**provenance(a.capture_out),files={str(f.relative_to(a.capture_out)):sha(f) for f in a.capture_out.rglob('*') if f.is_file()}))
if __name__=='__main__':main()
