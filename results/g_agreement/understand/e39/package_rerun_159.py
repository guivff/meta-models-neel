"""Package §159 recovery without modifying any original pod-bound source."""
from pathlib import Path
import gzip
import io
import tarfile
import contract as C
import rerun_159 as R
PREFIX='results/g_agreement/understand/e39/'
HERE=C.HERE
NEW_NAMES=['RERUN_SCOPE_159_2026-10-26.json','rerun_159.py','recovery_159.py','analyze_recovered_159.py',
    'analysis_once_recovered_159.py','package_rerun_159.py','test_recovery_159.py','test_rerun_grid_159.py',
    'OWNER_READING_RECOVERY_159_2026-10-26.md','HANDOFF_RECOVERY_159_2026-10-26.md','CPU_VALIDATION_RECOVERY_159_2026-10-26.json']

def main():
    old=C.read(HERE/'SOURCE_MANIFEST.json')['files']
    for n,h in old.items():
        if C.sha(C.ROOT/n)!=h:raise ValueError('original pod-bound source changed')
    C.dump(R.MANIFEST,{'files':{PREFIX+n:C.sha(HERE/n) for n in NEW_NAMES}})
    prior={'issuer':'integrator','experiment':'E39','status':'PENDING','recovery_complete':False,'all_original_pods_stopped':False,
        'unrecoverable_runs':R.scope()['rerun_runs'],'retained_complete_runs':50,'total_gpu_seconds':None,
        'pods':[{'pod_id':x['pod_id'],'provider_created_epoch':x['provider_created_epoch'],
                 'provider_terminated_epoch':None,'gpu_seconds':None} for x in R.scope()['original_pods']]}
    C.dump(HERE/'PRIOR_CUSTODY_159.template.json',prior)
    assignment=C.read(HERE/'ASSIGNMENT_SLOT0.template.json')
    assignment.update(recovery_authority='§159 item4',pod_count=1,slot=0,pod_id=None,runs=R.scope()['rerun_runs'],seed=C.SEED,
        allocated_gpu_seconds=13500,previous_gpu_seconds=None,prior_custody_sha256=None,
        input_seal_sha256=R.scope()['input_seal_sha256'],rerun_source_manifest_sha256=C.sha(R.MANIFEST))
    C.dump(HERE/'ASSIGNMENT_RERUN_159.template.json',assignment)
    request=C.read(HERE/'ANALYSIS_REQUEST_2026-10-26.json')
    request.update(command='python '+PREFIX+'analysis_once_recovered_159.py',recovery_authority='§159 item4',cwd='.',
        bound_launch_request='cache/g_agreement/understand/e39-bound-v2/LAUNCH_REQUEST_BOUND.json',
        input_directory='cache/g_agreement/understand/e39-bound-v2/input',
        pull_directories=[f'cache/g_agreement/understand/e39-verified-v1/slot{i}' for i in range(6)]+['cache/g_agreement/understand/e39-rerun-159/verified'],
        status='SEALED_WAITING_FOR_FOUR_RERUNS_AND_VERIFIED_54_RUN_GRID',
        input_availability='Original bound-v2 input present;50original run seals recovered;4B runs authorised only after final recovery/custody verification',
        full_scope='All54runs/18rows/3arms,7checkpoints,84items and step800free;50retained original runs plus4authorised B reruns',
        collection_policy='Original receipts stay byte-identical; fixed54-entry run_sources selects50original +4rerun with no score-based choice',
        original_pod_count=6,rerun_pod_count=1)
    C.dump(HERE/'ANALYSIS_REQUEST_2026-10-26.json',request)
    pulls=[];sources={}
    from recovery_159 import retained_runs
    for i,relative in enumerate(request['pull_directories']):
        runs=retained_runs(i) if i<6 else R.scope()['rerun_runs'];ident=f'original_slot{i}' if i<6 else 'rerun_159'
        pulls.append({'pull_id':ident,'directory':relative,'pod_id':R.scope()['original_pods'][i]['pod_id'] if i<6 else None,
                      'selected_runs':runs,'pull_sums_sha256':C.sha(C.ROOT/relative/'PULL_SUMS') if i<6 else None})
        for row,arm in runs:sources[row+'__'+arm]={'pull_id':ident,'score_seal_sha256':C.sha(C.ROOT/relative/'out'/(row+'__'+arm)/'SCORE_SEAL.json') if i<6 else None}
    C.dump(HERE/'VERIFIED_RECOVERY_PULLS_159.template.json',{'schema':'E39_VERIFIED_RECOVERY_PULLS_159_v1','issuer':'integrator','experiment':'E39',
        'status':'PENDING','production_complete':False,'original_pod_count':6,'rerun_pod_count':1,
        'input_seal_sha256':R.scope()['input_seal_sha256'],'pulls':pulls,'run_sources':sources})
    paths={n:C.ROOT/n for n in old}
    paths.update({PREFIX+n:HERE/n for n in NEW_NAMES+['RERUN_SOURCE_MANIFEST_159.json','SOURCE_MANIFEST.json','ASSIGNMENT_RERUN_159.template.json','PRIOR_CUSTODY_159.template.json']})
    archive=C.ROOT/'cache/g_agreement/understand/e39-rerun-159-source-v1.tar.gz'
    with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='',compresslevel=1) as z,tarfile.open(fileobj=z,mode='w') as t:
        for n,p in sorted(paths.items()):
            b=p.read_bytes();info=tarfile.TarInfo(n);info.size=len(b);info.mode=0o644;info.mtime=0;t.addfile(info,io.BytesIO(b))
    with tarfile.open(archive) as t:
        if set(t.getnames())!=set(paths):raise ValueError('archive membership changed')
        import hashlib
        for n,p in paths.items():
            if hashlib.sha256(t.extractfile(n).read()).hexdigest()!=C.sha(p):raise ValueError('archive bytes differ')
    bound=C.read(C.ROOT/request['bound_launch_request'])
    C.dump(HERE/'LAUNCH_REQUEST_RERUN_159.json',{'experiment':'E39','authority':'§159 item4','date':'2026-10-26',
        'status':'READY_AFTER_INTEGRATOR_CUSTODY_AND_RECOVERY_BINDING','runs':R.scope()['rerun_runs'],'seed':C.SEED,
        'pod_count':1,'allocated_gpu_seconds':13500,'experiment_cap_gpu_seconds':81000,
        'prior_custody':'Integrator actual provider ledger required, never inferred from training time; prior+13500<=81000',
        'source_archive':str(archive.relative_to(C.ROOT)),'source_archive_sha256':C.sha(archive),
        'original_source_manifest_sha256':C.sha(HERE/'SOURCE_MANIFEST.json'),'rerun_source_manifest_sha256':C.sha(R.MANIFEST),
        'input_archive':'cache/g_agreement/understand/e39-bound-v2/input.tar.gz','input_archive_sha256':bound['input_archive_sha256'],
        'input_seal_sha256':R.scope()['input_seal_sha256'],'assignment_template':PREFIX+'ASSIGNMENT_RERUN_159.template.json',
        'prior_custody_template':PREFIX+'PRIOR_CUSTODY_159.template.json',
        'environment_prepare_command':'/weights/venv-kernels/bin/python '+PREFIX+'training_environment.py prepare --base-python /weights/venv-kernels/bin/python --overlay /tmp/e39-rerun159-POD_ID --manifest TRAINING_ENVIRONMENT.json',
        'worker_command':'/tmp/e39-rerun159-POD_ID/bin/python '+PREFIX+'rerun_159.py run --assignment ASSIGNMENT.json --prior-custody PRIOR_CUSTODY_159.json --mapping '+PREFIX+'LORA_TARGETS.json --input INPUT_CACHE --assets VERIFIED_ASSETS.json --out cache/g_agreement/understand/e39-rerun-159-run --admission ADMISSION.json --environment-manifest TRAINING_ENVIRONMENT.json --parity-inputs PARITY_INPUTS',
        'admit_command':'python '+PREFIX+'rerun_159.py admit --forecast FORECAST.json --assignment ASSIGNMENT.json --prior-custody PRIOR_CUSTODY_159.json --out ADMISSION.json',
        'analysis_command':request['command'],'parity':'Original E28 W1 gate first before any optimizer; scientific failure stops without retry',
        'science_cap':'min(1.5F+360,10800), unchanged; same original warmed L/B paths and full four-run production',
        'registered_analysis_invocations':0,'GPU_jobs_launched':0})
    # The original pod source manifest is untouched. Only the CPU analysis seal
    # follows the new request and additional recovery code/receipt templates.
    prior_code=C.read(HERE/'ANALYSIS_CODE_SEAL_2026-10-26.json')['files']
    extra=NEW_NAMES+['RERUN_SOURCE_MANIFEST_159.json','LAUNCH_REQUEST_RERUN_159.json','ASSIGNMENT_RERUN_159.template.json',
        'PRIOR_CUSTODY_159.template.json','VERIFIED_RECOVERY_PULLS_159.template.json','ANALYSIS_REQUEST_2026-10-26.json']
    names=set(prior_code)|{PREFIX+n for n in extra}
    C.dump(HERE/'ANALYSIS_CODE_SEAL_2026-10-26.json',{'files':{n:C.sha(C.ROOT/n) for n in sorted(names)}})
    print('E39 four-run package and54-run once-only analysis sealed; original pod source manifest unchanged')

if __name__=='__main__':main()
