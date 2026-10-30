"""Prepare the §87 local launch receipt and exact-source archive; never allocate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from . import protocol as P
from .w11_items import source_hashes, SECTION, ORIGIN


def git(*args):return subprocess.check_output(['git','-C',str(P.ROOT),*args])


def launch_request(bank,freeze,stage,archive):
    bank,freeze,stage,archive=map(lambda p:Path(p).resolve(),(bank,freeze,stage,archive))
    P.verify(bank,'INPUT_SEAL.json');P.verify(stage,'INPUT_SEAL.json')
    if P.sha(bank/'INPUT_SEAL.json')!=P.sha(stage/'INPUT_SEAL.json'):raise ValueError('stage differs')
    manifest=json.loads((bank/'manifest.json').read_text());hashes=source_hashes()
    if manifest['source_files']!=hashes:raise ValueError('source changed after freeze')
    source=git('rev-parse','HEAD').decode().strip()
    relative=str((freeze/'manifest.json').relative_to(P.ROOT))
    commit=git('log','-1','--format=%H','--',relative).decode().strip()
    if not commit or hashlib.sha256(git('show',commit+':'+relative)).hexdigest()!=P.sha(bank/'manifest.json'):
        raise ValueError('freeze must be committed before launch receipt')
    for path,digest in hashes.items():
        if hashlib.sha256(git('show',source+':'+path)).hexdigest()!=digest:raise ValueError('uncommitted source: '+path)
    for path in freeze.iterdir():
        if git('show',source+':'+str(path.relative_to(P.ROOT)))!=path.read_bytes():raise ValueError('uncommitted freeze')
    if archive.exists():raise ValueError('archive exists; preserve it')
    archive.parent.mkdir(parents=True,exist_ok=True)
    git('archive','--format=tar.gz','--output='+str(archive),source,'--',*sorted(hashes))
    return {'schema':'blindspot-w11-launch-v1','status':'REQUESTED_NOT_ASSIGNED_AWAITING_MEASURED_FORECAST',
        'experiment':'W11','section':87,'recipient':'phase-r integrator','branch':'r/blindspot',
        'source_commit':source,'source_files':hashes,'source_archive_local':str(archive),'source_archive_sha256':P.sha(archive),
        'manifest_commit':commit,'manifest_path':relative,'manifest_sha256':P.sha(bank/'manifest.json'),
        'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
        'brief_commit':manifest['registration']['commit'],'section87_path':SECTION,'section87_sha256':P.sha(P.ROOT/SECTION),
        'registration_origin':ORIGIN,'bank_path_local':str(bank),'stage_path_local':str(stage),
        'items':1200,'pairs':600,'rows':10,'capture_sites':[42,44],'capture_positions':['pretarget','target_last'],
        'scope':'all ten frozen rows; no timing-dependent reduction or priority selection in this receipt',
        'science_cap_gpu_seconds':3600,'staging_allowance_seconds':1500,'previous_gpu_seconds':0,
        'timing':'one synthetic unscored warm-up per path in setup; median of three timed production-sized units; F includes elapsed timing science plus projected remaining work',
        'science_allocation_formula':'min(1.5F+360,3600) seconds from persistent first science; NO_FIT if complete work cannot fit allocation',
        'requested_gpu':'one H200 141GB or larger, all three readers resident before first science',
        'worker_command':'python -m projects.g_agreement.blindspot.w11_run --bank STAGED_BANK --assignment INTEGRATOR_ASSIGNMENT.json --assets VERIFIED_ASSETS.json --out NEW_W11_OUTPUT_DIRECTORY',
        'analysis_command':'python -m projects.g_agreement.blindspot.w11_analysis --bank FULL_LOCAL_BANK --outputs RETRIEVED_OUTPUTS --labels FROZEN_LOCAL_LABELS --out NEW_W11_ANALYSIS_DIRECTORY',
        'required_assignment':['issuer=integrator','experiment=W11','pod_id','source_commit','source_files','brief_commit',
            'section87_sha256','brief_registered=true','brief_pushed=true','manifest_commit','manifest_sha256',
            'manifest_committed=true','provider_created_epoch','deadline_epoch','allocated_gpu_seconds',
            'science_cap_gpu_seconds<=3600','staging_allowance_seconds=1500','previous_gpu_seconds=0','external_hardstop_verified=true'],
        'retrieval':['CAPTURE_SEAL.json','SCORE_SEAL.json','scores.jsonl','acts42.npy','acts44.npy',
            'pretarget.acts42.npy','pretarget.acts44.npy','items.order.json','provenance.json','FORECAST.json',
            'SCIENCE_RECEIPT.json','assignment science-clock.json'],
        'gates':manifest['analysis_contract'],'operations':'Integrator alone publishes and operates, verifies all receipts, arms independent absolute hardstop with final 180s retrieval reserve. No automatic retries. W-core does not push or allocate.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('bank','freeze','stage','archive','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('request already exists')
    P.dump(a.out,launch_request(a.bank,a.freeze,a.stage,a.archive))
