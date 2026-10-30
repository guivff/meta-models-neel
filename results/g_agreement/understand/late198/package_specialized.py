"""Package W-text's exact E82/E86 public bank without CPU targets or relabeling."""
import argparse
from pathlib import Path
import tarfile
from contract import read,write,sha,seal,verify,require,ROOT
from specialized import HERE,validate_public


def build(owner_request,destination,cap_seconds=None):
    owner=read(owner_request);exp=owner['experiment'];require(exp in ('E82','E86'),'specialized bank')
    require(sha(owner['public_archive'])==owner['public_archive_sha256'],'owner public archive identity')
    member='PUBLIC_CAPTURE.json' if exp=='E82' else 'PUBLIC_FILTER_INPUTS.json'
    with tarfile.open(owner['public_archive']) as archive:
        require(archive.getnames()==[member] and archive.getmember(member).isfile(),'public-only archive')
        data=archive.extractfile(member).read()
    import json
    items=validate_public(json.loads(data),exp)
    destination.mkdir(parents=True,exist_ok=False);inp=destination/'inputs';inp.mkdir()
    (inp/'PUBLIC_INPUTS.json').write_bytes(data)
    cap=cap_seconds if cap_seconds is not None else owner['gpu_cap_seconds_total']
    require(type(cap)is int and 60<cap<=owner['gpu_cap_seconds_total'],'owner cumulative cap')
    write(inp/'STAGE_REQUEST.json',dict(experiment=exp,status='READY',cap_seconds=cap,
        cumulative_cap_seconds=owner['gpu_cap_seconds_total'],account_gate_USD=1500,
        owner_public_archive_sha256=owner['public_archive_sha256'],seed_seconds_per_batch={}))
    input_sha=seal(inp,'INPUT_SEAL.json',experiment=exp,owner_request_sha256=sha(owner_request),public_sha256=sha(inp/'PUBLIC_INPUTS.json'))
    source_sha=sha(HERE/'SOURCE_SEAL.json');s=verify(HERE,'SOURCE_SEAL.json',source_sha);deps=read(HERE/'DEPENDENCIES.json')
    for n,h in deps.items():require(sha(ROOT/n)==h,'dependency '+n)
    names=set(deps)|{str((HERE/n).relative_to(ROOT)) for n in s['files']}|{str((HERE/'SOURCE_SEAL.json').relative_to(ROOT))}
    with tarfile.open(destination/'source.tar.gz','w:gz') as archive:
        for n in sorted(names):archive.add(ROOT/n,arcname=n,recursive=False)
    with tarfile.open(destination/'inputs.tar.gz','w:gz') as archive:archive.add(inp,arcname='inputs')
    request=dict(experiment=exp,status='READY_FOR_CAPTURE_AND_TIMING' if exp=='E82' else 'READY_FOR_FILTER_TIMING',
        items=len(items),positions=sum(len(x['read_positions']) for x in items) if exp=='E82' else None,
        source_archive=str((destination/'source.tar.gz').resolve()),source_archive_sha256=sha(destination/'source.tar.gz'),
        input_archive=str((destination/'inputs.tar.gz').resolve()),input_archive_sha256=sha(destination/'inputs.tar.gz'),
        source_seal_sha256=source_sha,input_seal_sha256=input_sha,owner_request_sha256=sha(owner_request),
        owner_public_archive_sha256=owner['public_archive_sha256'],public_inputs_sha256=sha(inp/'PUBLIC_INPUTS.json'),
        cap_seconds=cap,cumulative_cap_seconds=owner['gpu_cap_seconds_total'],integrator_owns_launch=True,
        measured_admission_required=True,live_eight_item_parity_required=True,reader_batch_size=32,
        filter_batch_size=64 if exp=='E86' else None,labels_on_pod=False,
        argv=['python','/workspace/results/g_agreement/understand/late198/specialized.py','--inputs','/workspace/binding/inputs',
            '--assets','/workspace/e56/assets.json','--assignment','/workspace/binding/assignment.json','--out','/workspace/binding/out',
            '--source-sha',source_sha,'--input-sha',input_sha,'--stage','capture' if exp=='E82' else 'filter'])
    if exp=='E86':request['argv'].append('--profile-only')
    write(destination/'REQUEST.json',request);return request


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--owner-request',type=Path,required=True);p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--cap-seconds',type=int);a=p.parse_args();build(a.owner_request,a.destination,a.cap_seconds)
