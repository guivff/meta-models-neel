"""E40 single-pod calibration,100M training and one final registered gate."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import time
import numpy as np
from e40_common import HERE,ROOT,E35,read,sha,dump_new
from e40_clock import Clock,NoFit,RESERVE
from e40_sae import Trainer,ScaledSAE,FIXED_CONFIG
from calibration import calibrate,seal_calibration,eligible
from pipeline import captured_stream,collect_calibration,eligible_batches,evaluate_gate
from e40_data import verify_sources,documents,chunks
from gate_worker import capture44,decoder_blocks,TARGET_REPO,TARGET_REVISION

REQUEST='LAUNCH_REQUEST.training.json'
OUT='cache/g_agreement/understand/e40/training-20261026/out'
SAMPLE_SHA='dff73a3a83b76a6de4a5a2cbf2fe909a14a6888eaa9b91eeca6df849323fc593'
RUNTIME_FILE='results/g_agreement/blindspot/s79/RUNTIME_PINS.json'
RUNTIME_KEYS=('torch','transformers','triton','flash-linear-attention','fla-core','causal-conv1d','tokenizers','numpy')

class OperationalSetupError(ValueError):
    pass


def verify_code(request):
    required={'worker.py','e40_sae.py','calibration.py','pipeline.py','e40_clock.py',
              'e40_data.py','e40_common.py','FINEWEB_FILES.20261026.json','TRAINING_PLAN.20261026.json'}
    pins=request.get('source_files',{})
    inherited={str((E35/name).relative_to(ROOT))for name in
               ('gate_inputs.py','gate_math.py','gate_worker.py','sae.py','fallback_sae.py')}
    names={Path(k).name for k in pins if Path(k).parent==HERE.relative_to(ROOT)}
    if (request.get('experiment')!='E40'or request.get('output_path')!=OUT
            or not required<=names or not inherited|{RUNTIME_FILE}<=set(pins)):
        raise ValueError('complete E40 frozen source request required')
    for name,digest in pins.items():
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT.resolve())or sha(path)!=digest:
            raise ValueError('E40 source checksum mismatch')
    plan=read(HERE/'TRAINING_PLAN.20261026.json')
    if plan['training']!=asdict(FIXED_CONFIG):raise ValueError('registered E40 configuration required')


def verify_gate_input(request):
    folder=(ROOT/request['heldout_dir']).resolve()
    if not folder.is_relative_to((ROOT/'cache/g_agreement/understand/e35').resolve()):
        raise ValueError('sealed original E35 heldout data required')
    for name,digest in request['heldout_files'].items():
        if sha(folder/name)!=digest:raise ValueError('heldout input checksum mismatch')
    sample=read(E35/'GATE_SAMPLE.json')
    if sha(E35/'GATE_SAMPLE.json')!=SAMPLE_SHA:raise ValueError('unchanged heldout sample required')
    seal=read(folder/'final/OUTPUT_SEAL.json')
    original=read(folder/'final/GATE_RESULT.json')
    if (original.get('experiment')!='E35' or original.get('status')!='FAIL'
            or original.get('sample_sha256')!=SAMPLE_SHA
            or original.get('metrics',{}).get('n_tokens')!=50000
            or seal['files']['GATE_RESULT.json']!=request['heldout_files']['final/GATE_RESULT.json']):
        raise ValueError('same sealed original gate token ordering required')
    if seal['files']['h.npy']!=request['heldout_files']['arrays/h.npy']:
        raise ValueError('raw h not bound to original gate seal')
    h=np.load(folder/'arrays/h.npy',mmap_mode='r',allow_pickle=False)
    positions=np.array([p for doc in sample['documents']for p in doc['positions']],dtype=np.int64)
    if h.shape!=(50000,5120)or len(positions)!=50000:raise ValueError('exact50000 raw heldout vectors required')
    return h,positions


def memory_admission(free,total,host_available):
    if total<120_000_000_000 or free<60_000_000_000 or host_available<48_000_000_000:
        raise OperationalSetupError('E40 requires >=120GBGPU,60GBfree aftertarget and48GBhostfree')
    return {'gpu_total_bytes':total,'gpu_free_after_target_bytes':free,
            'host_available_bytes':host_available,'calibration_host_buffer_bytes':1_000_000*5120*4}

def validate_runtime(versions):
    expected=read(ROOT/RUNTIME_FILE)
    if any(versions.get(name)!=expected[name]for name in RUNTIME_KEYS):
        raise OperationalSetupError('preserved E35 forward runtime versions required')


def load_target(clock):
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM
    clock.check()
    versions={}
    for name in RUNTIME_KEYS+('pyarrow',):
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    validate_runtime(versions)
    if versions['pyarrow'] is None:
        raise OperationalSetupError('local parquet streaming requires pyarrow')
    if not torch.cuda.is_available()or torch.cuda.device_count()!=1:
        raise OperationalSetupError('exactly oneCUDA GPU required')
    torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(20261026)
    target=Path(snapshot_download(TARGET_REPO,revision=TARGET_REVISION,local_files_only=True))
    model=AutoModelForCausalLM.from_pretrained(target,dtype=torch.bfloat16,device_map='cuda',local_files_only=True)
    model.eval();model.requires_grad_(False);decoder_blocks(model)
    info={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:')}
    free,total=torch.cuda.mem_get_info()
    memory=memory_admission(free,total,info['MemAvailable'])
    memory['versions']=versions;memory['gpu_name']=torch.cuda.get_device_name(0);memory['cpu_threads']=8
    clock.check();return model,memory


def claim(out,assignment_sha,request_sha):
    out=Path(out).resolve()
    if out!=(ROOT/OUT).resolve():raise ValueError('exact E40 output path required')
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise FileExistsError('output exists')
    dump_new(out.parent/'TRAINING.RUN_ONCE.json',{'assignment_sha256':assignment_sha,'request_sha256':request_sha})
    out.mkdir()


def tighten_alarm(clock):
    end=clock.a['deadline_epoch']-RESERVE
    if clock.science_limit is not None:end=min(end,clock.science_start+clock.science_limit)
    signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()))


def heartbeat(out,clock,progress):
    tmp=out/'CLOCK.tmp'
    tmp.write_text(json.dumps({'clock':clock.record(),'progress':progress},indent=2,sort_keys=True)+'\n')
    tmp.replace(out/'CLOCK.json')


def pilots(buffer,norms,calibration,clock,*,device='cuda'):
    import torch
    ix=np.flatnonzero(eligible(norms,np.ones(len(norms),dtype=np.int64),calibration))[:4096]
    if len(ix)!=4096:raise ValueError('full retained scratch timing batch required')
    x=buffer[ix].to(device)
    scratch=Trainer(scale=calibration['scale'],device=device,synthetic=True,timing_force_auxiliary=True)
    optimizer=[];evaluation=[]
    for _ in range(3):
        clock.check();torch.cuda.synchronize();t=time.monotonic()
        scratch.step(x,first_position=scratch.tokens_seen,split='train')
        torch.cuda.synchronize();optimizer.append(time.monotonic()-t)
    with torch.inference_mode():
        for _ in range(3):
            clock.check();torch.cuda.synchronize();t=time.monotonic()
            z=scratch.model.encode(x[:256]*calibration['scale'])
            r=scratch.model.decode(z)/calibration['scale']
            # Include CPU copy and pooled-moment work in the evaluation timing.
            rr=r.cpu().numpy().astype(np.float64)
            xx=x[:256].cpu().numpy().astype(np.float64)
            error=float(np.square(xx-rr).sum());centered=float(np.square(xx-xx.mean(axis=0)).sum())
            active=z.gt(0).any(dim=0).cpu().numpy()
            if not np.isfinite(error+centered)or active.shape!=(65536,):raise ValueError('finite gate-path timing required')
            torch.cuda.synchronize();evaluation.append(time.monotonic()-t)
    del scratch,x,z,r
    torch.cuda.empty_cache()
    return optimizer,evaluation


def execute(a,request,assignment,clock,h,positions):
    import torch
    progress={'raw_captured':0,'capture_chunks':0,'position_zero_excluded':0,'norm_excluded':0,
              'trained_tokens':0,'optimizer_steps':0,'untrained_eligible_tail':0,'full_chunk_seconds':[]}
    status='INCOMPLETE';metrics=None;error_type=None;failure=None;checkpoint_sha=None;calibration_sha=None
    model=None;trainer=None;calibration=None
    started=time.time()
    try:
        verify_sources(a.sources,assignment['sources_sha256'])
        model,memory=load_target(clock)
        dump_new(a.out/'RUNTIME.json',memory)
        torch.cuda.reset_peak_memory_stats()
        clock.begin()
        # Synthetic source only: warmup never recaptures a training occurrence.
        capture44(model,[1]*512,list(range(512)))
        torch.cuda.synchronize()
        with (a.out/'capture_ledger.jsonl').open('x')as ledger:
            def log(record):ledger.write(json.dumps(record,sort_keys=True)+'\n')
            stream=iter(captured_stream(model,chunks(documents(a.sources)),capture44,clock,progress,log))
            t=time.monotonic()
            buffer,nn,pending=collect_calibration(stream)
            calibration_elapsed=time.monotonic()-t
            calibration=calibrate(nn)
            calibration['source_manifest_sha256']=assignment['sources_sha256']
            calibration['capture_chunks']=progress['capture_chunks']
            calibration['single_capture_pass']=True
            calibration_sha=seal_calibration(a.out,calibration)
            heartbeat(a.out,clock,progress)
            opt,ev=pilots(buffer,nn,calibration,clock)
            clock.admit(calibration_elapsed=calibration_elapsed,calibration_chunks=progress['capture_chunks'],
                calibration_retained=calibration['calibration_retained'],full_chunk_seconds=progress['full_chunk_seconds'],
                optimizer_seconds=opt,evaluation_seconds=ev)
            tighten_alarm(clock);heartbeat(a.out,clock,progress)
            dump_new(a.out/'PILOT.json',{'optimizer_seconds':opt,'evaluation_seconds':ev,
                'forced_all_dead_AuxK_scratch_only':True,'retained_pilot_updates':0,
                'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'forecast':clock.forecast_components})
            # A distinct, freshly seeded trainer; the timing-only override is off.
            trainer=Trainer(scale=calibration['scale'],device='cuda')
            for raw in eligible_batches(buffer,nn,pending,stream,calibration,progress):
                clock.check()
                trainer.step(raw.to('cuda'),first_position=trainer.tokens_seen,split='train')
                progress['trained_tokens']=trainer.tokens_seen;progress['optimizer_steps']=trainer.steps
                heartbeat(a.out,clock,progress)
            if trainer.tokens_seen!=100_000_000:raise ValueError('complete100M eligible positions required')
        clock.check()
        params=trainer.checkpoint_tensors();training=trainer.completed_manifest()
        training.update(calibration_sha256=calibration_sha,sources_sha256=assignment['sources_sha256'],
                        data_passes=1,recaptured_training_occurrences=0)
        with(a.out/'layer44.e40.sae.pt').open('xb')as f:torch.save(params,f)
        checkpoint_sha=sha(a.out/'layer44.e40.sae.pt')
        training['sae_checkpoint_sha256']=checkpoint_sha
        dump_new(a.out/'TRAINING_RESULT.json',training)
        del trainer,buffer,nn,pending,stream
        trainer=None
        torch.cuda.empty_cache()
        sae=ScaledSAE(params,calibration['scale'],device='cuda');del params
        clock.check()
        dump_new(a.out/'GATE.RUN_ONCE.json',{'checkpoint_sha256':checkpoint_sha,
            'calibration_sha256':calibration_sha,'sample_sha256':SAMPLE_SHA})
        metrics=evaluate_gate(sae,h,positions,calibration,clock)
        status='PASS'if metrics['filtered']['passed']else'FAIL'
        del sae
    except Exception as e:
        error_type=type(e).__name__;status='NO_FIT'if isinstance(e,NoFit)else'INCOMPLETE'
        failure='OPERATIONAL'if isinstance(e,(NoFit,OSError,torch.cuda.OutOfMemoryError,OperationalSetupError))else'VALIDITY_NO_RETRY'
    finally:
        model=trainer=None
        if torch.cuda.is_initialized():torch.cuda.empty_cache()
    clock.status=status;heartbeat(a.out,clock,progress)
    result={'experiment':'E40','stage':'gate','status':status,'metrics':metrics,
        'primary_gate':'filtered','all_token_fvu_descriptive':True,
        'error_type':error_type,'failure_category':failure,'scientific_retry_allowed':False,
        'request_sha256':sha(HERE/REQUEST),'assignment_sha256':sha(a.assignment),
        'sample_sha256':SAMPLE_SHA,'sae_checkpoint_sha256':checkpoint_sha,
        'calibration_sha256':calibration_sha,'scale':calibration['scale']if calibration else None,
        'sae_k':128,'worker_started_epoch':started,'worker_finished_epoch':time.time(),
        'clock':clock.record(),'progress':progress,'decomposition_calls':0,
        'next_stage':'frozen_§131_blind_labels_then_decomposition'if status=='PASS'else
          ('no_adequate_SAE_stop_no_third_attempt'if status=='FAIL'else'report_incomplete_no_scientific_verdict')}
    dump_new(a.out/'GATE_RESULT.json',result)
    dump_new(a.out/'OUTPUT_SEAL.json',{'status':status,'files':{p.name:sha(p)for p in a.out.iterdir()if p.is_file()}})
    print('E40',status,error_type or'')
    return 0 if status in('PASS','FAIL')else 2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('assignment','sources','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:
        request=read(HERE/REQUEST);verify_code(request)
        assignment=read(a.assignment);clock=Clock(assignment,sha(HERE/REQUEST))
        h,positions=verify_gate_input(request)
        claim(a.out,sha(a.assignment),sha(HERE/REQUEST))
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled',CUBLAS_WORKSPACE_CONFIG=':4096:8')
        signal.signal(signal.SIGALRM,lambda s,f:(_ for _ in()).throw(NoFit('E40 hard deadline')))
        tighten_alarm(clock)
        try:return execute(a,request,assignment,clock,h,positions)
        finally:signal.setitimer(signal.ITIMER_REAL,0)
    except Exception as e:
        print('E40 preflight STOP',type(e).__name__);return 2
if __name__=='__main__':raise SystemExit(main())
