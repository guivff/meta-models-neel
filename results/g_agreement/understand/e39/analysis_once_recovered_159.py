"""§149 integrator-only entry point for E39's unchanged registered analysis.

Uses fixed owner paths and an atomic, never-reset claim. Any failure waits for
owner review. No alternative inputs, outputs, thresholds or retry CLI exists.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
REQUEST=HERE/'ANALYSIS_REQUEST_2026-10-26.json'
CODE_SEAL=HERE/'ANALYSIS_CODE_SEAL_2026-10-26.json'
CLAIM=ROOT/'cache/g_agreement/understand/e39-analysis-once-v1/CLAIM.json'
STATUS=ROOT/'cache/g_agreement/understand/e39-analysis-once-v1/STATUS.json'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def read(path):return json.loads(Path(path).read_text())


def write_new(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:
        json.dump(obj,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())


def claim_once(path):
    # Exclusive creation is atomic across independent watcher processes.
    write_new(path,{'experiment':'E39','status':'CLAIMED_NEVER_RESET','authority':'§149 RUN-BY-INTEGRATOR',
        'created_epoch':time.time(),'pid':os.getpid(),'analysis_entry_invocations':1,
        'failure_policy':'STOP_WAIT_OWNER; do not remove claim or retry'})


def verify_files(base,files):
    base=Path(base).resolve()
    for name,digest in files.items():
        p=(base/name).resolve()
        if not p.is_relative_to(base) or not p.is_file() or sha(p)!=digest:
            raise ValueError('sealed file missing, escaped, or changed')


def verify_pull(directory,expected_digest):
    """Recheck Integrator's transfer manifest; exact complete out/ coverage."""
    directory=Path(directory)
    sums=directory/'PULL_SUMS'
    if sha(sums)!=expected_digest:raise ValueError('Integrator transfer manifest hash mismatch')
    files={}
    for line in sums.read_text().splitlines():
        fields=line.split(maxsplit=1)
        if len(fields)!=2 or len(fields[0])!=64 or any(c not in '0123456789abcdef' for c in fields[0]):
            raise ValueError('invalid transfer manifest record')
        name=fields[1].removeprefix('*').removeprefix('./')
        if name in files:raise ValueError('duplicate transfer manifest path')
        files[name]=fields[0]
    verify_files(directory,files)
    actual={p.relative_to(directory).as_posix() for p in (directory/'out').rglob('*') if p.is_file()}
    expected={n for n in files if n.startswith('out/')}
    if not actual or actual!=expected:raise ValueError('verified manifest must cover every output file exactly')
    return {'pull_sums_sha256':expected_digest,'verified_file_count':len(files)}


def preflight():
    verify_files(ROOT,read(CODE_SEAL)['files'])
    request=read(REQUEST)
    if request['experiment']!='E39' or request['recovery_authority']!='§159 item4':raise ValueError('wrong recovery request')
    import sys
    sys.path.insert(0,str(HERE))
    import recovery_159 as recovery
    receipt_path=ROOT/request['verified_pull_receipt'];receipt=read(receipt_path)
    paths,proofs=recovery.receipt_preflight(request,receipt)
    inp=ROOT/request['input_directory'];bound=read(ROOT/request['bound_launch_request'])
    if (sha(inp/'INPUT_SEAL.json')!=bound['input_seal_sha256'] or receipt['input_seal_sha256']!=bound['input_seal_sha256']
            or sha(HERE/'SOURCE_MANIFEST.json')!=bound['source_manifest_sha256']
            or sha(HERE/'PLAN.json')!=bound['plan_sha256']):raise ValueError('same bound-v2 input/source required')
    verify_files(inp,read(inp/'INPUT_SEAL.json')['files'])
    output=ROOT/request['analysis_cache_output'];publish=ROOT/request['publish_directory']
    if output.exists() or publish.exists():raise ValueError('existing output blocks a second analysis')
    return request,inp,paths,output,publish,{'verified_pull_receipt_sha256':sha(receipt_path),
        'input_seal_sha256':sha(inp/'INPUT_SEAL.json'),'pulls':proofs,'run_sources':receipt['run_sources'],
        'analysis_source_sha256':sha(HERE/'analyze_recovered_159.py'),'request_sha256':sha(REQUEST),
        'code_seal_sha256':sha(CODE_SEAL),'prior_custody_sha256':sha(paths[-1]/'PRIOR_CUSTODY_159.json')}


def execute(inp,paths,output,stdout,stderr):
    command=[sys.executable,str(HERE/'analyze_recovered_159.py'),'--input',str(inp),
        '--outputs',*[str(p) for p in paths],'--out',str(output)]
    with stdout.open('xb') as out,stderr.open('xb') as err:
        return subprocess.run(command,cwd=ROOT,stdout=out,stderr=err,check=False).returncode


def publish_sealed(output,publish):
    seal=read(output/'ANALYSIS_SEAL.json');verify_files(output,seal['files'])
    names=set(seal['files'])|{'ANALYSIS_SEAL.json'}
    if {p.name for p in output.iterdir()}!=names:raise ValueError('unsealed analysis output file')
    publish.mkdir(parents=True,exist_ok=False)
    for name in sorted(names):
        shutil.copyfile(output/name,publish/name)
        if sha(output/name)!=sha(publish/name):raise ValueError('publication copy changed bytes')
    return sha(publish/'ANALYSIS_SEAL.json')


def run_once():
    try:claim_once(CLAIM)
    except FileExistsError:
        print('E39 ALREADY_CLAIMED: stop and await owner; no analysis invoked')
        return 3
    result={'experiment':'E39','label':'§149 RUN-BY-INTEGRATOR','started_epoch':time.time(),
        'status':'STOP_WAIT_OWNER','registered_analysis_invocations':0,'gpu_hours':0}
    try:
        request,inp,paths,output,publish,evidence=preflight()
        result['verification']=evidence
        result['registered_analysis_invocations']=1
        code=execute(inp,paths,output,CLAIM.parent/'analysis.stdout.log',CLAIM.parent/'analysis.stderr.log')
        result['analysis_exit_code']=code
        if code!=0:raise RuntimeError('registered analysis stopped; no retry')
        result['analysis_seal_sha256']=publish_sealed(output,publish)
        result['status']='COMPLETE_SEALED_UNINTERPRETED'
        result['published_directory']=request['publish_directory']
        result['finished_epoch']=time.time()
        write_new(ROOT/request['publication_receipt'],result)
    except BaseException as exc:
        result['status']='STOP_WAIT_OWNER';result['error_type']=type(exc).__name__
        # Keep diagnostics local; do not print private data or exception payloads.
    finally:
        result['finished_epoch']=time.time()
        write_new(STATUS,result)
    print('E39 '+result['status']+'; no automatic retry')
    return 0 if result['status']=='COMPLETE_SEALED_UNINTERPRETED' else 2


if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('No overrides permitted; use the committed command without arguments')
    raise SystemExit(run_once())
