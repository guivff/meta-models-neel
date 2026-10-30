"""Seal the built E44 source and already-bound verified capture; never launch."""
import gzip
import io
import tarfile
from pathlib import Path
import contract as C
PREFIX='results/g_agreement/understand/e44/'
CACHE=C.ROOT/'cache/g_agreement/understand'

def archive(path,files):
    with Path(path).open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='',compresslevel=1) as z,tarfile.open(fileobj=z,mode='w') as tar:
        for name,p in sorted(files.items()):
            data=Path(p).read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0
            tar.addfile(info,io.BytesIO(data))
    with tarfile.open(path) as tar:
        if set(tar.getnames())!=set(files):raise ValueError('archive member mismatch')
        import hashlib
        for name,p in files.items():
            if hashlib.sha256(tar.extractfile(name).read()).hexdigest()!=C.sha(p):raise ValueError('archive byte mismatch')

def main():
    inp=CACHE/'e44-bound-v1/input';C.verify(inp)
    binding=C.read(inp/'PREPARATION.json');binding['provenance_sha256']=C.sha(inp/'provenance.json')
    C.dump(C.HERE/'BOUND_INPUT.json',binding)
    excluded={'SOURCE_MANIFEST.json','LAUNCH_REQUEST.json','ASSIGNMENT.template.json','ANALYSIS_CODE_SEAL_2026-10-26.json','SECRET_SCAN_2026-10-26.json'}
    paths={PREFIX+p.name:p for p in C.HERE.iterdir() if p.is_file() and p.name not in excluded}
    inherited=C.read(C.HERE.parent/'e39/SOURCE_MANIFEST.json')['files']
    for name,h in inherited.items():
        if '/understand/e39/' in name:continue
        if C.sha(C.ROOT/name)!=h:raise ValueError('frozen E39 native dependency drift')
        paths[name]=C.ROOT/name
    C.dump(C.HERE/'SOURCE_MANIFEST.json',{'files':{n:C.sha(p) for n,p in sorted(paths.items())}})
    paths[PREFIX+'SOURCE_MANIFEST.json']=C.HERE/'SOURCE_MANIFEST.json'
    source=CACHE/'e44-source-v1.tar.gz';archive(source,paths)
    input_archive=CACHE/'e44-bound-v1/input.tar.gz';names=list(C.read(inp/'INPUT_SEAL.json')['files'])+['INPUT_SEAL.json']
    archive(input_archive,{n:inp/n for n in names})
    parity=C.read(C.HERE/'PARITY_PREPARATION_2026-10-25.json')['parity_input_seal_sha256']
    C.dump(C.HERE/'ASSIGNMENT.template.json',{'issuer':'integrator','experiment':'E44','pod_id':None,'pod_count':1,'slot':0,'runs':[['pooled_content','C']],
        'plan_sha256':C.sha(C.HERE/'PLAN.json'),'target_mapping_sha256':C.sha(C.HERE/'LORA_TARGETS.json'),
        'source_manifest_sha256':C.sha(C.HERE/'SOURCE_MANIFEST.json'),'input_seal_sha256':binding['input_seal_sha256'],
        'assets_sha256':None,'source_published':False,'source_commit':None,'external_hardstop_verified':False,
        'allocated_gpu_seconds':14400,'previous_gpu_seconds':0,'provider_created_epoch':None,'deadline_epoch':None,
        'training_environment_sha256':None,'parity_input_seal_sha256':parity,'release_gate_sha256':C.sha(C.HERE/'E39_RELEASE_GATE_2026-10-26.json')})
    C.dump(C.HERE/'LAUNCH_REQUEST.json',{'experiment':'E44','date':'2026-10-26','status':'READY_E39_STEP25_VERIFIED','authority_commit':'266c15f0',
        'source_commit':'Integrator publishes commit containing this request','source_manifest_sha256':C.sha(C.HERE/'SOURCE_MANIFEST.json'),
        'source_archive':str(source.relative_to(C.ROOT)),'source_archive_sha256':C.sha(source),
        'input_archive':str(input_archive.relative_to(C.ROOT)),'input_archive_sha256':C.sha(input_archive),
        'input_seal_sha256':binding['input_seal_sha256'],'plan_sha256':C.sha(C.HERE/'PLAN.json'),
        'release_gate':PREFIX+'E39_RELEASE_GATE_2026-10-26.json','release_gate_sha256':C.sha(C.HERE/'E39_RELEASE_GATE_2026-10-26.json'),
        'assignment_template':PREFIX+'ASSIGNMENT.template.json','parity_archive':'cache/g_agreement/understand/e28-parity-v1.tar.gz',
        'parity_archive_sha256':C.sha(CACHE/'e28-parity-v1.tar.gz'),'parity_input_seal_sha256':parity,
        'scope':{'arms':['C'],'content_dev_rows':list(C.CONTENT),'train_items':756,'test_rows':list(C.ROWS),'test_items':2100,'steps':400,'checkpoints':list(C.CHECKPOINTS),'asked_item_records':8400,'seed':C.SEED},
        'budget':{'max_provider_gpu_seconds':14400,'max_pods':2,'requested_pods':1,'setup_seconds_max':2400,'retrieval_reserve_seconds':180,'science_cap':'min(1.5F+360,10800)','programme_cutoff_epoch':C.PROGRAMME_CUTOFF,'all_setup_and_warmup_included':True},
        'environment_prepare_command':'/weights/venv-kernels/bin/python '+PREFIX+'training_environment.py prepare --base-python /weights/venv-kernels/bin/python --overlay /tmp/e44-training-POD_ID --manifest cache/g_agreement/understand/e44-POD_ID/TRAINING_ENVIRONMENT.json',
        'worker_command':'/tmp/e44-training-POD_ID/bin/python '+PREFIX+'worker.py --assignment ASSIGNMENT.json --mapping '+PREFIX+'LORA_TARGETS.json --input INPUT_CACHE --assets VERIFIED_ASSETS.json --out cache/g_agreement/understand/e44-run-v1 --environment-manifest TRAINING_ENVIRONMENT.json --parity-inputs PARITY_INPUTS --release-gate '+PREFIX+'E39_RELEASE_GATE_2026-10-26.json',
        'analysis_command':'python '+PREFIX+'analysis_once_2026_10_26.py','analysis_request':PREFIX+'ANALYSIS_REQUEST_2026-10-26.json',
        'gpu_jobs_launched':0,'registered_analysis_invocations':0,'validation':C.read(C.HERE/'CPU_VALIDATION_2026-10-26.json'),
        'release_authority':'E39 step0/25 checkpoint hashes and parity/CUDA receipts verified before this handoff; Integrator alone pushes and launches'})
    pins=C.read(C.HERE/'SOURCE_MANIFEST.json')['files']
    pins.update({PREFIX+n:C.sha(C.HERE/n) for n in ('SOURCE_MANIFEST.json','LAUNCH_REQUEST.json','ASSIGNMENT.template.json')})
    C.dump(C.HERE/'ANALYSIS_CODE_SEAL_2026-10-26.json',{'files':pins})
    print('E44 READY_E39_STEP25_VERIFIED; source and once-only entry sealed')

if __name__=='__main__':main()
