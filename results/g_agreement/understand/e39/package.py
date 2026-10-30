"""Seal E39 source now; bind verified E36 captures later without changing science."""
import argparse
import gzip
import hashlib
import io
from pathlib import Path
import tarfile
import contract as C
import prepare_inputs as P

PREFIX='results/g_agreement/understand/e39/'
CACHE=C.ROOT/'cache/g_agreement/understand'


def archive(path, files):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as z:
        with tarfile.open(fileobj=z,mode='w') as tar:
            for n,p in sorted(files.items()):
                data=p.read_bytes();info=tarfile.TarInfo(n);info.size=len(data);info.mode=0o644;info.mtime=0
                tar.addfile(info,io.BytesIO(data))
    with tarfile.open(path) as tar:
        if set(tar.getnames())!=set(files):raise ValueError('archive coverage mismatch')
        for member in tar.getmembers():
            if hashlib.sha256(tar.extractfile(member).read()).hexdigest()!=C.sha(files[member.name]):
                raise ValueError('reopened archive content mismatch')


def assignments(input_seal=None,count=6):
    if type(count)!=int or not 1<=count<=6:raise ValueError('one to six pods required')
    parity=C.read(C.HERE/'PARITY_PREPARATION_2026-10-25.json')
    return [{'issuer':'integrator','experiment':'E39','pod_id':'REQUIRED','slot':i,'pod_count':count,
        'runs':C.assigned_runs(i,count),'plan_sha256':C.sha(C.HERE/'PLAN.json'),
        'target_mapping_sha256':C.sha(C.HERE/'LORA_TARGETS.json'),
        'source_manifest_sha256':C.sha(C.HERE/'SOURCE_MANIFEST.json'),
        'input_seal_sha256':input_seal,'assets_sha256':'INTEGRATOR_SET_VERIFIED_ASSETS_SHA256',
        'source_published':False,'source_commit':'INTEGRATOR_SET_PUBLISHED_COMMIT',
        'external_hardstop_verified':False,'allocated_gpu_seconds':C.CAP/count,'previous_gpu_seconds':0,
        'provider_created_epoch':None,'deadline_epoch':None,'training_environment_sha256':None,
        'parity_input_seal_sha256':parity['parity_input_seal_sha256']} for i in range(count)]


def build():
    C.validate_plan(C.plan())
    # Common imports are the sealed E28 worker's existing native dependencies.
    inherited=C.read(C.HERE.parent/'e28/SOURCE_MANIFEST.json')['files']
    paths={n:C.ROOT/n for n in inherited if '/understand/e28/' not in n}
    names=[p.name for p in C.HERE.glob('*.py')]+['PLAN.json','LORA_TARGETS.json','ROW_DEFINITIONS.json',
        'OVERLAY_REQUIREMENTS.txt','PARITY_PREPARATION_2026-10-25.json','PREPARATION.json',
        'PRIOR_ATTEMPT_ACCOUNTING_2026-10-26.json','OWNER_READING_2026-10-26.md']
    paths.update({PREFIX+n:C.HERE/n for n in names})
    C.dump(C.HERE/'SOURCE_MANIFEST.json',{'files':{n:C.sha(p) for n,p in sorted(paths.items())}})
    paths[PREFIX+'SOURCE_MANIFEST.json']=C.HERE/'SOURCE_MANIFEST.json'
    source=CACHE/'e39-source-v1.tar.gz';archive(source,paths)
    stage=CACHE/'e39-stage-v1';C.verify(stage,'STAGE_SEAL.json')
    parity=CACHE/'e28-parity-v1';C.verify(parity)
    expected=C.read(C.HERE/'PARITY_PREPARATION_2026-10-25.json')['parity_input_seal_sha256']
    if C.sha(parity/'INPUT_SEAL.json')!=expected:raise ValueError('unchanged E28 parity payload required')
    # Reuse the exact original parity archive: no new labels or population.
    parity_tar=CACHE/'e28-parity-v1.tar.gz'
    with tarfile.open(parity_tar) as tar:
        files=C.read(parity/'INPUT_SEAL.json')['files']
        if set(tar.getnames())!=set(files)|{'INPUT_SEAL.json'}:raise ValueError('parity archive coverage mismatch')
        for n,h in files.items():
            if hashlib.sha256(tar.extractfile(n).read()).hexdigest()!=h:raise ValueError('parity archive bytes mismatch')
    for i,a in enumerate(assignments()):C.dump(C.HERE/f'ASSIGNMENT_SLOT{i}.template.json',a)
    request={'experiment':'E39','date':'2026-10-26','status':'CPU_BUILT_BLOCKED_AWAITING_VERIFIED_E36_CAPTURE',
        'authority_commit':'a38044dd','clarification_commit':'8cc9d46d','source_commit':'INTEGRATOR_USE_COMMIT_CONTAINING_REQUEST',
        'plan_sha256':C.sha(C.HERE/'PLAN.json'),'source_manifest_sha256':C.sha(C.HERE/'SOURCE_MANIFEST.json'),
        'source_archive_local':str(source.relative_to(C.ROOT)),'source_archive_sha256':C.sha(source),
        'metadata_stage_local':str(stage.relative_to(C.ROOT)),'metadata_stage_seal_sha256':C.sha(stage/'STAGE_SEAL.json'),
        'parity_archive_local':str(parity_tar.relative_to(C.ROOT)),'parity_archive_sha256':C.sha(parity_tar),
        'parity_input_seal_sha256':expected,'input_archive_has_private_test_labels':False,
        'scope':{'rows':list(C.ROWS),'structure_rows':list(C.STRUCTURE),'semantic_rows':list(C.SEMANTIC),
            'runs':54,'arms':['L','B','S'],'S_every_row':True,'train_items_per_row':84,'test_items_per_row':84,
            'steps':800,'checkpoints':list(C.CHECKPOINTS),'asked_item_records':31752,'free_readouts':4536,'seed':C.SEED},
        'budget':{'total_gpu_hours':15,'total_provider_gpu_seconds':54000,'previous_gpu_seconds':0,'max_pods':6,
            'default_pods':6,'default_provider_seconds_per_pod':9000,'setup_seconds_max':2400,
            'ssh_setup_allowance_seconds_per_pod':600,'allowance_inside_allocation':True,
            'science_cap':'min(1.5F+360,10800) seconds per pod, unchanged E28 nonresetting clock',
            'retrieval_reserve_seconds':180,'programme_cutoff_epoch':C.PROGRAMME_CUTOFF,
            'all_setup_parity_warmup_admission_wait_inside_cap':True,'every_pod_requires_own_warmed_forecast':True},
        'pretraining_parity_gate':'Unchanged E28 W1 rows prose_sentiment/prose_paren/python_string,84each,untrained lens AUROC tolerance0.03; before any optimizer,including warmup; scientific failure no retry',
        'environment':'Same isolated /weights/venv-kernels overlay adding only wheel-hashed Triton3.7.1; freeze inherited packages; actualCUDAbackward gate',
        'environment_prepare_command':'/weights/venv-kernels/bin/python '+PREFIX+'training_environment.py prepare --base-python /weights/venv-kernels/bin/python --overlay /tmp/e39-training-POD_ID --manifest cache/g_agreement/understand/e39-POD_ID/TRAINING_ENVIRONMENT.json',
        'bind_command':'python '+PREFIX+'package.py bind --metadata cache/g_agreement/understand/e39-stage-v1 --captures VERIFIED_E36_PULL_0 VERIFIED_E36_PULL_1 --out cache/g_agreement/understand/e39-bound-v1 --pods 6',
        'worker_command':'/tmp/e39-training-POD_ID/bin/python '+PREFIX+'worker.py run --assignment ASSIGNMENT.json --mapping '+PREFIX+'LORA_TARGETS.json --input INPUT_CACHE --assets VERIFIED_ASSETS.json --out NEW_OUTPUT_CACHE --admission ADMISSION.json --parity-inputs PARITY_INPUTS --environment-manifest TRAINING_ENVIRONMENT.json',
        'admit_command':'python '+PREFIX+'worker.py admit --forecasts ALL_ASSIGNED_PODS_FORECAST_FILES --out ADMISSION.json',
        'analysis_command':'python '+PREFIX+'analyze.py --input LOCAL_INPUT_WITH_PRIVATE_KEY --outputs ALL_COMPLETE_VERIFIED_POD_OUTPUTS --out NEW_ANALYSIS_CACHE',
        'operations':'Integrator alone publishes, binds verified captures, assigns, launches, admits, retrieves and terminates. §139 priority/global20pod ceiling/180s deploy spacing. No partial-grid launch, no automatic retry; §136 operational rebuild once only with prior custody repinned. E37 stays ready.',
        'analysis_invocations':0,'gpu_hours_local':0,'evidence':C.read(C.HERE/'CPU_VALIDATION_2026-10-26.json')}
    C.dump(C.HERE/'LAUNCH_REQUEST.json',request)
    return request


def bind(metadata,captures,out,pods):
    # This binding step may occur after E36 finishes; no source/scientific choice changes.
    C.verify(C.ROOT,str((C.HERE/'SOURCE_MANIFEST.json').relative_to(C.ROOT)))
    out=C.cache_output(out)
    prep=P.prepare(metadata,captures,out/'input')
    inp=out/'input';files=C.read(inp/'INPUT_SEAL.json')['files']
    archive(out/'input.tar.gz',{n:inp/n for n in [*files,'INPUT_SEAL.json']})
    for i,a in enumerate(assignments(prep['input_seal_sha256'],pods)):
        C.dump(out/f'ASSIGNMENT_SLOT{i}.template.json',a)
    request=C.read(C.HERE/'LAUNCH_REQUEST.json')
    request.update(status='INPUT_BOUND_INTEGRATOR_PUBLICATION_PARITY_AND_WARMED_GATE_REQUIRED',
        input_archive_local=str(out/'input.tar.gz'),input_archive_sha256=C.sha(out/'input.tar.gz'),
        input_seal_sha256=prep['input_seal_sha256'],bound_input_provenance_sha256=C.sha(inp/'provenance.json'),
        assignment_files=[str(out/f'ASSIGNMENT_SLOT{i}.template.json') for i in range(pods)])
    C.dump(out/'LAUNCH_REQUEST_BOUND.json',request)
    return request


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('build');b=sub.add_parser('bind')
    b.add_argument('--metadata',type=Path,required=True);b.add_argument('--captures',type=Path,nargs='+',required=True)
    b.add_argument('--out',type=Path,required=True);b.add_argument('--pods',type=int,default=6)
    a=p.parse_args();result=build() if a.command=='build' else bind(a.metadata,a.captures,a.out,a.pods)
    print(result['status'])
