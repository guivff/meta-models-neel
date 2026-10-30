"""§159: four irrecoverable B runs only, using the original sealed E39 worker."""
from pathlib import Path
import argparse
import math
import shutil
import time
import contract as C
import worker as W
HERE=Path(__file__).resolve().parent
SCOPE=HERE/'RERUN_SCOPE_159_2026-10-26.json'
MANIFEST=HERE/'RERUN_SOURCE_MANIFEST_159.json'

def scope():return C.read(SCOPE)

def check_sources():
    C.verify(C.ROOT,str((HERE/'SOURCE_MANIFEST.json').relative_to(C.ROOT)))
    C.verify(C.ROOT,str(MANIFEST.relative_to(C.ROOT)))
    if C.sha(HERE/'SOURCE_MANIFEST.json')!=scope()['original_source_manifest_sha256']:raise ValueError('original source identity changed')

def custody(path):
    value=C.read(path);s=scope()
    if (value.get('issuer')!='integrator' or value.get('experiment')!='E39'
            or value.get('status')!='CUSTODY_AND_RECOVERY_VERIFIED'
            or value.get('recovery_complete') is not True or value.get('all_original_pods_stopped') is not True
            or value.get('unrecoverable_runs')!=s['rerun_runs'] or value.get('retained_complete_runs')!=50):
        raise ValueError('completed recovery and exact four lost runs required before launch')
    entries=value.get('pods',[])
    if len(entries)!=6 or {x['pod_id'] for x in entries}!={x['pod_id'] for x in s['original_pods']}:raise ValueError('six original provider custody records required')
    total=0.
    for old in s['original_pods']:
        item=next(x for x in entries if x['pod_id']==old['pod_id'])
        start,end,seconds=(item.get(k) for k in ('provider_created_epoch','provider_terminated_epoch','gpu_seconds'))
        if (any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,end,seconds))
                or start!=old['provider_created_epoch'] or end>time.time() or abs(end-start-seconds)>1e-4
                or not old['minimum_observed_worker_gpu_seconds']<=seconds<=old['allocated_gpu_seconds']):
            raise ValueError('actual stopped-provider custody must include worker and retrieval time')
        total+=seconds
    if (type(value.get('total_gpu_seconds')) not in (int,float) or not math.isfinite(value['total_gpu_seconds'])
            or abs(value['total_gpu_seconds']-total)>1e-4 or total>67500):
        raise ValueError('verified custody plus13500 must fit81000')
    return value

def assignment(a,ledger,now=None):
    now=time.time() if now is None else now;s=scope()
    if (a.get('issuer')!='integrator' or a.get('experiment')!='E39' or a.get('recovery_authority')!='§159 item4'
            or a.get('pod_count')!=1 or a.get('slot')!=0 or not a.get('pod_id')
            or a['pod_id'] in {x['pod_id'] for x in s['original_pods']}
            or a.get('runs')!=s['rerun_runs'] or a.get('seed')!=C.SEED
            or a.get('plan_sha256')!=C.sha(HERE/'PLAN.json')
            or a.get('source_manifest_sha256')!=s['original_source_manifest_sha256']
            or a.get('rerun_source_manifest_sha256')!=C.sha(MANIFEST)
            or a.get('input_seal_sha256')!=s['input_seal_sha256']
            or a.get('target_mapping_sha256')!=C.sha(HERE/'LORA_TARGETS.json')
            or a.get('source_published') is not True or a.get('external_hardstop_verified') is not True):
        raise ValueError('published single-pod exact four-run assignment required')
    for k in ('allocated_gpu_seconds','previous_gpu_seconds','provider_created_epoch','deadline_epoch'):
        if type(a.get(k)) not in (int,float) or not math.isfinite(a[k]):raise ValueError('finite provider fields required')
    if (a['allocated_gpu_seconds']!=13500 or a['previous_gpu_seconds']!=ledger['total_gpu_seconds']
            or a['previous_gpu_seconds']+a['allocated_gpu_seconds']>81000
            or not a['provider_created_epoch']<=now<a['deadline_epoch']-180
            or max(p['provider_terminated_epoch'] for p in ledger['pods'])>a['provider_created_epoch']
            or a['deadline_epoch']>min(a['provider_created_epoch']+13500,C.PROGRAMME_CUTOFF)):
        raise ValueError('cumulative cap or nonresetting provider deadline violated')
    return a

def bind_ledger(a,path,now=None):
    ledger=custody(path)
    if a.get('prior_custody_sha256')!=C.sha(path):raise ValueError('assignment custody hash differs')
    assignment(a,ledger,now);return ledger

def admit(f,a):
    if (a.get('allocated_gpu_seconds')!=13500 or type(a.get('previous_gpu_seconds')) not in (int,float)
            or not math.isfinite(a['previous_gpu_seconds']) or not 0<=a['previous_gpu_seconds']<=67500):
        raise ValueError('single-pod allocation plus prior must fit81000')
    if (f.get('status')!='WARMED_FORECAST' or f.get('slot')!=0 or f.get('pod_count')!=1
            or f.get('plan_sha256')!=C.sha(HERE/'PLAN.json') or f.get('input_seal_sha256')!=a['input_seal_sha256']
            or f.get('allocated_gpu_seconds')!=a['allocated_gpu_seconds'] or f.get('previous_gpu_seconds')!=a['previous_gpu_seconds']):
        raise ValueError('actual same-pod bound warmed forecast required')
    keys=('forecast_remaining_seconds','elapsed_science_seconds','elapsed_provider_seconds','setup_elapsed_seconds')
    if any(type(f.get(k)) not in (int,float) or not math.isfinite(f[k]) for k in keys):raise ValueError('finite forecast required')
    remaining,elapsed,provider,setup=(f[k] for k in keys)
    if remaining<=0 or not 0<=setup<=2400 or not 0<=elapsed<=provider or provider<setup:raise ValueError('invalid elapsed setup/science clock')
    science=min(1.5*(remaining+elapsed)+360,10800)
    fit=remaining+elapsed<=science and science-elapsed<=a['allocated_gpu_seconds']-provider-180
    return {'status':'ADMIT_FULL_GRID' if fit else 'NO_FIT_STOP','plan_sha256':C.sha(HERE/'PLAN.json'),
        'pods':[{'slot':0,'fit':fit,'science_seconds':science,'forecast_sha256':f['forecast_sha256']}],
        'total_allocated_gpu_seconds':a['allocated_gpu_seconds'],'previous_gpu_seconds':a['previous_gpu_seconds'],
        'total_experiment_reserved_gpu_seconds':a['previous_gpu_seconds']+a['allocated_gpu_seconds']}

def run(a):
    check_sources();assigned=C.read(a.assignment);ledger=bind_ledger(assigned,a.prior_custody)
    # Only the operational assignment checker differs. Original loading, parity,
    # pilots, seed resets, all800 steps/checkpoints/scoring and receipts are intact.
    original=C.assignment;C.assignment=lambda value,now=None:assignment(value,ledger,now)
    try:return W.run(a)
    finally:
        C.assignment=original
        if a.out.is_dir():
            shutil.copyfile(a.prior_custody,a.out/'PRIOR_CUSTODY_159.json')
            C.dump(a.out/'RERUN_CONTEXT_159.json',{'authority':'§159 item4','scope_sha256':C.sha(SCOPE),
                'rerun_source_manifest_sha256':C.sha(MANIFEST),'prior_custody_sha256':C.sha(a.prior_custody),
                'runs':scope()['rerun_runs'],'original_worker_unchanged':True})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    launch=sub.add_parser('run')
    for key in ('assignment','mapping','input','assets','out','admission','environment-manifest','parity-inputs','prior-custody'):
        launch.add_argument('--'+key,type=Path,required=True)
    gate=sub.add_parser('admit')
    for key in ('forecast','assignment','prior-custody','out'):gate.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();check_sources()
    if a.command=='run':
        import os
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1');run(a)
    else:
        assigned=C.read(a.assignment);bind_ledger(assigned,a.prior_custody)
        f=C.read(a.forecast)
        if f.get('assignment_sha256')!=C.sha(a.assignment):raise ValueError('forecast assignment differs')
        C.dump(a.out,admit({**f,'forecast_sha256':C.sha(a.forecast)},assigned))
