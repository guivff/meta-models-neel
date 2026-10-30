"""Seal E50's frozen build and label-free inputs; no model calls or launches."""
import gzip
import hashlib
import io
import tarfile
from pathlib import Path
import contract as C
PREFIX='results/g_agreement/understand/e50/'
CACHE=C.ROOT/'cache/g_agreement/understand'

def archive(path,files):
    with Path(path).open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='',compresslevel=1) as z,tarfile.open(fileobj=z,mode='w') as tar:
        for name,p in sorted(files.items()):
            data=Path(p).read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0
            tar.addfile(info,io.BytesIO(data))
    with tarfile.open(path) as tar:
        if set(tar.getnames())!=set(files):raise ValueError('archive member mismatch')
        for name,p in files.items():
            if hashlib.sha256(tar.extractfile(name).read()).hexdigest()!=C.sha(p):raise ValueError('archive byte mismatch')

def main():
    inp=CACHE/'e50-bound-v1/input';C.verify(inp)
    binding=C.read(inp/'PREPARATION.json');binding['provenance_sha256']=C.sha(inp/'provenance.json')
    if C.read(inp/'provenance.json')['plan_sha256']!=C.sha(C.HERE/'PLAN.json'):raise ValueError('input plan drift')
    C.dump(C.HERE/'BOUND_INPUT.json',binding)
    excluded={'SOURCE_MANIFEST.json','LAUNCH_REQUEST.json','ASSIGNMENT_SLOT0.template.json','ASSIGNMENT_SLOT1.template.json','ANALYSIS_CODE_SEAL_2026-10-26.json','SECRET_SCAN_2026-10-26.json'}
    paths={PREFIX+p.name:p for p in C.HERE.iterdir() if p.is_file() and p.name not in excluded}
    inherited=C.read(C.HERE.parent/'e39/SOURCE_MANIFEST.json')['files']
    for name,h in inherited.items():
        if '/understand/e39/' in name:continue
        if C.sha(C.ROOT/name)!=h:raise ValueError('frozen E39 native dependency drift')
        paths[name]=C.ROOT/name
    C.dump(C.HERE/'SOURCE_MANIFEST.json',{'files':{n:C.sha(p) for n,p in sorted(paths.items())}})
    paths[PREFIX+'SOURCE_MANIFEST.json']=C.HERE/'SOURCE_MANIFEST.json'
    source=CACHE/'e50-source-v1.tar.gz';archive(source,paths)
    input_archive=CACHE/'e50-bound-v1/input.tar.gz';names=list(C.read(inp/'INPUT_SEAL.json')['files'])+['INPUT_SEAL.json']
    archive(input_archive,{n:inp/n for n in names})
    parity=C.read(C.HERE/'PARITY_PREPARATION_2026-10-25.json')['parity_input_seal_sha256']
    for slot,split in enumerate(('A','B')):
        C.dump(C.HERE/f'ASSIGNMENT_SLOT{slot}.template.json',{'issuer':'integrator','experiment':'E50','pod_id':None,'pod_count':2,'slot':slot,'runs':[[split,'L'],[split,'S']],
            'plan_sha256':C.sha(C.HERE/'PLAN.json'),'target_mapping_sha256':C.sha(C.HERE/'LORA_TARGETS.json'),
            'source_manifest_sha256':C.sha(C.HERE/'SOURCE_MANIFEST.json'),'input_seal_sha256':binding['input_seal_sha256'],
            'assets_sha256':None,'source_published':False,'source_commit':None,'external_hardstop_verified':False,
            'allocated_gpu_seconds':7200,'previous_gpu_seconds':0,'provider_created_epoch':None,'deadline_epoch':None,
            'training_environment_sha256':None,'parity_input_seal_sha256':parity,
            'secondary':{'status':'NOT_FROZEN_AT_LAUNCH','issuer':'integrator','checked_before_launch':False}})
    C.dump(C.HERE/'LAUNCH_REQUEST.json',{'experiment':'E50','date':'2026-10-26','status':'READY','authority_commit':'1a19bb9d','clarification_commits':['499d99c5','5578d0da'],
        'source_commit':'Integrator publishes commit containing this request','source_manifest_sha256':C.sha(C.HERE/'SOURCE_MANIFEST.json'),
        'source_archive':str(source.relative_to(C.ROOT)),'source_archive_sha256':C.sha(source),
        'input_archive':str(input_archive.relative_to(C.ROOT)),'input_archive_sha256':C.sha(input_archive),
        'input_seal_sha256':binding['input_seal_sha256'],'plan_sha256':C.sha(C.HERE/'PLAN.json'),
        'assignment_templates':[PREFIX+f'ASSIGNMENT_SLOT{i}.template.json' for i in range(2)],
        'parity_archive':'cache/g_agreement/understand/e28-parity-v1.tar.gz','parity_archive_sha256':C.sha(CACHE/'e28-parity-v1.tar.gz'),'parity_input_seal_sha256':parity,
        'scope':{'runs':C.plan()['runs'],'rows':list(C.ROWS),'steps':400,'train_items_per_adapter':672,'asked_item_records':8400,'heldout_free_records':2688,'post_L_W1_records':504,'seed':C.SEED},
        'budget':{'max_provider_gpu_seconds':14400,'max_pods':2,'requested_pods':2,'allocation_per_pod_seconds':7200,'setup_seconds_max':2400,'retrieval_reserve_seconds_per_pod':180,'science_cap':'min(1.5F+360,10800), also bounded by provider deadline less180','all_setup_parity_warmup_and_serialization_included':True,'forecast':'800*max(warmed step time)+53*asked84+16*forced128free84+120; +11*asked84 if E49 enabled','programme_cutoff_epoch':C.PROGRAMME_CUTOFF,'no_scope_trimming':True},
        'secondary':{'condition':'Integrator checks E49 bank freeze before launch; same decision on both pods. If unavailable, set checked_before_launch=true. If frozen, stage verified semantic tracked-state test capture under SECONDARY_INPUT_CONTRACT_2026-10-26.md and bind both assignments. No training on E49.','status_at_build':'NOT_FROZEN','score_only_L':True},
        'environment_prepare_command':'/weights/venv-kernels/bin/python '+PREFIX+'training_environment.py prepare --base-python /weights/venv-kernels/bin/python --overlay /tmp/e50-training-POD_ID --manifest cache/g_agreement/understand/e50-POD_ID/TRAINING_ENVIRONMENT.json',
        'worker_command':'/tmp/e50-training-POD_ID/bin/python '+PREFIX+'worker.py --assignment ASSIGNMENT.json --mapping '+PREFIX+'LORA_TARGETS.json --input INPUT_CACHE --assets VERIFIED_ASSETS.json --out cache/g_agreement/understand/e50-run-v1 --environment-manifest TRAINING_ENVIRONMENT.json --parity-inputs PARITY_INPUTS',
        'optional_worker_argument':'--secondary-input E49_LABEL_FREE_INPUT_CACHE (only with FROZEN_VERIFIED assignment)',
        'analysis_command':'python '+PREFIX+'analysis_once_2026_10_26.py','analysis_request':PREFIX+'ANALYSIS_REQUEST_2026-10-26.json',
        'gpu_jobs_launched':0,'registered_analysis_invocations':0,'validation':C.read(C.HERE/'CPU_VALIDATION_2026-10-26.json')})
    pins=C.read(C.HERE/'SOURCE_MANIFEST.json')['files']
    pins.update({PREFIX+n:C.sha(C.HERE/n) for n in ('SOURCE_MANIFEST.json','LAUNCH_REQUEST.json','ASSIGNMENT_SLOT0.template.json','ASSIGNMENT_SLOT1.template.json')})
    C.dump(C.HERE/'ANALYSIS_CODE_SEAL_2026-10-26.json',{'files':pins})
    print('E50 READY; source, label-free input and once-only analysis sealed')

if __name__=='__main__':main()
