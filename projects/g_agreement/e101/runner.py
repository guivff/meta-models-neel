"""Two-stage E101 acquisition; no target labels or dose decisions on pods."""
import argparse,importlib.util,os,signal,sys,threading,time,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from .contract import read,write,sha,verify,validate,policy_settings
from .acquisition import behaviour,batches
ROOT=Path(__file__).resolve().parents[3]
OLD=ROOT/'results/g_agreement/understand/e79/worker.py'
OLD_SHA='721ce7680400df9a96b0ce1e54ea944a5c080acd94335bed08006d790a9a8f0c'


def dependencies():
    if sha(OLD)!=OLD_SHA: raise ValueError('frozen E79 runner changed')
    sys.path[:0]=[str(ROOT),str(ROOT/'results/g_agreement/understand/late198'),str(ROOT/'external/mats-nla-workspace/src')]
    spec=importlib.util.spec_from_file_location('_e101_e79',OLD);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    from runtime import Runtime
    from hardware204 import production_gate,bind_units,finite
    return old,Runtime,production_gate,bind_units,finite


def output_provenance(out):
    files=list((out/'jobs').glob('*.json'))
    if not files:return dict(first_output_utc='unknown',first_output_evidence=None)
    p=min(files,key=lambda p:p.stat().st_mtime_ns)
    return dict(first_output_utc=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),first_output_evidence=dict(member=str(p.relative_to(out)),sha256=sha(p),mtime_ns=p.stat().st_mtime_ns,source='archived_file_mtime'))


def jobs(items,stage):
    result=[dict(kind='logits',indices=v) for v in batches(items)]
    if stage=='test':
        for block,reader in [(44,'oracle'),(42,'nla')]:
            ix=[i for i,x in enumerate(items) if x['block']==block]
            result.extend(dict(kind=reader,indices=ix[k:k+8]) for k in range(0,len(ix),8))
    return result


def acquire(items,h,runtime,clock,out,stage,mode,timing=False):
    """Reuse E79 Clock and native_one unchanged; logits are base-model forwards."""
    jj=jobs(items,stage);observations=[];profile=[];write(out/'JOB_GRID.json',jj);(out/'jobs').mkdir();done=[]
    for phase in ('logits','oracle','nla'):
        indices=[i for i,j in enumerate(jj) if j['kind']==phase]
        if not indices: continue
        setup=runtime.load_base if phase=='logits' else runtime.load_oracle if phase=='oracle' else runtime.load_nla
        if phase=='oracle':runtime.model=runtime.tok=None
        def load_phase():
            if phase=='nla' and runtime.readers is None:runtime.load_oracle()
            setup()
        clock.call(phase+'_setup',load_phase)
        # Dummy warm-up is discarded and excluded from the measured rate.
        first=items[jj[indices[0]]['indices'][0]]
        dummy=np.random.default_rng(20261028).standard_normal((1,h.shape[1])).astype(np.float32)
        def warm():
            if phase=='logits':
                model,_,cm=runtime.subject()
                x=dict(first,ids=[1]*len(first['ids']))
                with cm:return behaviour(model,[x],dummy,mode)
            return runtime.readers.native_one(phase,dummy)
        clock.call(phase+'_warmup_discarded',warm)
        clock.cost={phase:[]}
        phase_jobs=[dict(kind=phase) for _ in indices];phase_done=set()
        seen_strata=set();stratum_seconds={};stratum_counts={}
        def stratum(j):
            return (len(j['indices']),tuple(sorted({(items[v]['row'],items[v]['block'],len(items[v]['ids']),tuple(tuple(len(c) for c in pair) for pair in items[v]['candidate_ids'])) for v in j['indices']})))
        for jidx in indices:
            key=stratum(jj[jidx]);stratum_counts[key]=stratum_counts.get(key,0)+1
        for k,i in enumerate(indices):
            j=jj[i];xs=[items[v] for v in j['indices']];v=h[j['indices']].copy();before=v.tobytes()
            strata=stratum(j)
            if timing and strata in seen_strata:continue
            seen_strata.add(strata)
            def call():
                if phase=='logits':
                    model,_,cm=runtime.subject()
                    with cm: return behaviour(model,xs,v,mode)
                groups=runtime.readers.native_one(phase,v)
                if len(groups)!=len(xs) or any(len(g)!=1 for g in groups): raise ValueError('one greedy readout per cell')
                return [g[0] for g in groups]
            rr=clock.call(phase,call)
            if len(rr)!=len(xs) or v.tobytes()!=before: raise ValueError('acquisition alignment or vector mutation')
            write(out/'jobs'/f'{i:06d}.json',[dict(id=x['id'],norm_ratio=x.get('norm_ratio'),off_distribution=x.get('norm_ratio',0)>1.5,block=x['block'],channel=phase,gpu_type=getattr(runtime,'hardware_assignment',{}).get('gpu_type','CPU_SYNTHETIC'),**r) for x,r in zip(xs,rr)])
            done.append(i);phase_done.add(k)
            stratum_seconds.setdefault(strata,[]).append(clock.events[-1]['seconds'])
            observations.append(dict(job=i,phase=phase,strata=strata,items=len(xs),seconds=clock.events[-1]['seconds']))
            # Clock's atomic writer preserves progress after each completed batch.
            from admission import atomic
            atomic(out/'COMPLETED.json',done)
            atomic(out/'OBSERVATIONS.json',observations)
            if timing:continue
            if not clock.forecast(phase_jobs,phase_done): return 'NO_FIT'
        profile.append(dict(phase=phase,jobs=len(indices),sample_seconds=list(clock.cost[phase]),
                            mean_job_seconds=sum(stratum_counts[k]*float(np.mean(v)) for k,v in stratum_seconds.items())/len(indices)))
    if timing:
        def cell_keys(job):
            return {(job['kind'],items[i]['row'],items[i]['block'],items[i].get('alpha'),items[i].get('condition')) for i in job['indices']}
        expected=set().union(*(cell_keys(j) for j in jj))
        covered=set().union(*(cell_keys(jj[i]) for i in done))
        if covered!=expected:raise ValueError('SMOKE FAILED: missing registered arm/condition/layer/dose')
        write(out/'SMOKE_COVERAGE.json',dict(status='PASS',expected_cells=len(expected),covered_cells=len(covered)))
        from .timing import profile_receipt
        write(out/'MEASURED_PROFILE.json',profile_receipt(clock.events,profile))
    return 'TIMING_ONLY' if timing else 'COMPLETE' 


def main():
    p=argparse.ArgumentParser()
    for n in ('inputs','assets','assignment','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('input-sha','source-sha'):p.add_argument('--'+n,required=True)
    p.add_argument('--profile',type=Path);p.add_argument('--timing',action='store_true');p.add_argument('--hardware-receipt',type=Path)
    a=p.parse_args();verify(ROOT,str(a.source_seal.relative_to(ROOT)),a.source_sha)
    seal=verify(a.inputs,'INPUT_SEAL.json',a.input_sha);m=read(a.inputs/'MANIFEST.json')
    if set(seal['files'])!={'MANIFEST.json','items.json','vectors.npy'}:raise ValueError('only label-free pod members')
    if seal['experiment']!='E101' or seal['labels_on_pod'] is not False or m['status']!='FROZEN_READY':raise ValueError('owner input seal')
    items=read(a.inputs/'items.json');h=np.load(a.inputs/'vectors.npy',allow_pickle=False)
    validate(items,h,m['stage'],m['dev_count'],m.get('selected_doses'))
    count,policy,mode=policy_settings(m.get('policy','clarification1'))
    if m['dev_count']!=count or m['dose_policy']!=policy or m['scoring_mode']!=mode or not m['ruling_commit']: raise ValueError('registered scoring and dose ruling')
    if m['stage']=='test' and (not m['dose_commit'] or not m['dose_sha256']):raise ValueError('committed dose binding')
    ass=read(a.assignment)
    if (ass['experiment']!='E101' or ass['input_sha256']!=a.input_sha or ass['source_sha256']!=a.source_sha
        or ass['assets_sha256']!=sha(a.assets) or ass['gpu_count']!=1 or ass['daily_budget_verified'] is not True
        or ass['pod_id']!=os.environ.get('RUNPOD_POD_ID') or ass['cap_seconds']<=0
        or ass['absolute_deadline_epoch']!=ass['pod_created_epoch']+ass['cap_seconds']): raise ValueError('fixed creation custody and bindings')
    from .timing import admit,bind_profile
    if not a.timing:admit(a.profile,ass,a.input_sha,a.source_sha)
    old,Runtime,gate,bind,finite=dependencies()
    bind(ass,{x['row'] for x in items})
    hardware=gate(ass,a.hardware_receipt,a.assets,['oracle','nla'] if m['stage']=='test' else [])
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);write(a.out/'HARDWARE.json',hardware)
    write(a.out/'STAGING.json',dict(seconds=max(0,time.time()-ass['pod_created_epoch'])))
    end=ass['absolute_deadline_epoch'];timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='FAILED'
    try:
        import torch
        torch.manual_seed(20261028);np.random.seed(20261028)
        runtime=Runtime(a.assets);runtime.hardware_assignment=ass
        status=acquire(items,h,runtime,old.Clock(a.out,end),a.out,m['stage'],m['scoring_mode'],a.timing)
        if a.timing:bind_profile(a.out,ass,a.input_sha,a.source_sha,hardware)
        for path in (a.out/'jobs').glob('*.json'):
            if not finite(read(path)):raise ValueError('non-finite acquisition receipt')
    except BaseException as e:
        status='FAILED'
        write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:300]));raise
    finally:
        timer.cancel()
        write(a.out/'OUTPUT_SEAL.json',dict(experiment='E101',status=status,stage=m['stage'],input_sha256=a.input_sha,source_sha256=a.source_sha,
            gpu_type=hardware['gpu_type'],actual_gpu_name=hardware['actual_gpu_name'],dose_sha256=m.get('dose_sha256'),pod_id=ass['pod_id'],completed_epoch=time.time(),**output_provenance(a.out),files={str(f.relative_to(a.out)):sha(f) for f in a.out.rglob('*') if f.is_file()}))
if __name__=='__main__':main()
