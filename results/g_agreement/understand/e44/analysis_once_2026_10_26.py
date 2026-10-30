"""§149 integrator-only entry point for E44's unchanged registered analysis.

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
CLAIM=ROOT/'cache/g_agreement/understand/e44-analysis-once-v1/CLAIM.json'
STATUS=ROOT/'cache/g_agreement/understand/e44-analysis-once-v1/STATUS.json'


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
    write_new(path,{'experiment':'E44','status':'CLAIMED_NEVER_RESET','authority':'§149 RUN-BY-INTEGRATOR',
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
    if request['experiment']!='E44' or request['authority_commit']!='886d03b0':raise ValueError('wrong request')
    manifest=read(HERE/'SOURCE_MANIFEST.json');verify_files(ROOT,manifest['files'])
    receipt_path=ROOT/request['verified_pull_receipt'];receipt=read(receipt_path)
    if (receipt.get('experiment')!='E44' or receipt.get('issuer')!='integrator'
            or receipt.get('status')!='VERIFIED_COMPLETE' or receipt.get('production_complete') is not True
            or receipt.get('directory')!=request['pull_directory']
            or receipt.get('source_manifest_sha256')!=sha(HERE/'SOURCE_MANIFEST.json')):
        raise ValueError('Integrator verified complete original pull required')
    directory=ROOT/request['pull_directory'];proof=verify_pull(directory,receipt['pull_sums_sha256'])
    inp=ROOT/request['input_directory']
    if sha(inp/'INPUT_SEAL.json')!=read(HERE/'BOUND_INPUT.json')['input_seal_sha256']:raise ValueError('input seal drift')
    verify_files(inp,read(inp/'INPUT_SEAL.json')['files'])
    collection=directory/'out'
    run=read(collection/'RUN_RECEIPT.json')
    if run.get('status')!='COMPLETE_FULL_ASSIGNED_GRID' or run.get('experiment')!='E44':
        raise ValueError('full E44 production required')
    reference=ROOT/request['e39_analysis_directory']
    verify_files(reference,read(reference/'ANALYSIS_SEAL.json')['files'])
    if sha(reference/'ANALYSIS_SEAL.json')!=receipt.get('e39_analysis_seal_sha256'):
        raise ValueError('Integrator must bind the existing sealed E39 analysis')
    output=ROOT/request['analysis_cache_output'];publish=ROOT/request['publish_directory']
    if output.exists() or publish.exists():raise ValueError('existing output blocks a second analysis')
    return request,inp,collection,output,publish,{'verified_pull_receipt_sha256':sha(receipt_path),
        **proof,'request_sha256':sha(REQUEST),'code_seal_sha256':sha(CODE_SEAL)}


def execute(inp,collection,output,stdout,stderr):
    reference=ROOT/read(REQUEST)['e39_analysis_directory']
    command=[sys.executable,str(HERE/'analyze.py'),'--inputs',str(inp),'--collection',str(collection),
        '--e39-analysis',str(reference),'--out',str(output)]
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
        print('E44 ALREADY_CLAIMED: stop and await owner; no analysis invoked')
        return 3
    result={'experiment':'E44','label':'§149 RUN-BY-INTEGRATOR','started_epoch':time.time(),
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
    print('E44 '+result['status']+'; no automatic retry')
    return 0 if result['status']=='COMPLETE_SEALED_UNINTERPRETED' else 2


if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('No overrides permitted; use the committed command without arguments')
    raise SystemExit(run_once())
