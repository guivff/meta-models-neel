"""Freeze serial E81 profile, then one coordinated measured production shard set."""
import argparse
from pathlib import Path
import shutil
import tarfile
import worker81 as W
from serial81 import AUTHORITY,roster


def archive_inputs(inp):
    (inp/'INPUT_SEAL.json').unlink(missing_ok=True)
    digest=W.seal(inp,'INPUT_SEAL.json',experiment='E81',authority=AUTHORITY)
    path=inp.parent/'inputs.tar.gz'
    with tarfile.open(path,'w:gz') as a:a.add(inp,arcname='inputs')
    return digest,path


def prepare(old_request,dest,shards=8,probe_cap=1800):
    old=W.read(old_request);W.require(W.sha(old['input_archive'])==old['input_archive_sha256'],'owner input archive')
    dest.mkdir(parents=True,exist_ok=False)
    with tarfile.open(old['input_archive']) as a:a.extractall(dest,filter='data')
    inp=dest/'inputs';W.verify(inp,'INPUT_SEAL.json',old['input_seal_sha256'])
    items=W.validate(W.read(inp/'PUBLIC_INPUTS.json'));public_sha=W.sha(inp/'PUBLIC_INPUTS.json')
    W.write(inp/'SERIAL_PLAN.json',dict(authority=AUTHORITY,mode='profile',shard=None,shards=shards,
        shard_ids=roster(items,shards),public_inputs_sha256=public_sha))
    limits=W.read(inp/'STAGE_REQUEST.json');limits.update(status='READY',batch_size=1,cap_seconds=probe_cap,cumulative_cap_seconds=probe_cap,seed_seconds_per_batch={})
    W.write(inp/'STAGE_REQUEST.json',limits,replace=True);ih,ia=archive_inputs(inp)
    source_sha=W.sha(W.HERE/'SOURCE_SEAL.json');s=W.verify(W.HERE,'SOURCE_SEAL.json',source_sha);deps=W.read(W.HERE/'DEPENDENCIES.json')
    for n,h in deps.items():W.require(W.sha(W.ROOT/n)==h,'dependency '+n)
    names=set(deps)|{str((W.HERE/n).relative_to(W.ROOT)) for n in s['files']}|{str((W.HERE/'SOURCE_SEAL.json').relative_to(W.ROOT))}
    with tarfile.open(dest/'source.tar.gz','w:gz') as a:
        for n in sorted(names):a.add(W.ROOT/n,arcname=n,recursive=False)
    request=dict(experiment='E81',includes='E90',authority=AUTHORITY,status='READY_SERIAL_TIMING_REQUIRES_OPERATOR_ADMISSION',
        source_archive=str((dest/'source.tar.gz').resolve()),source_archive_sha256=W.sha(dest/'source.tar.gz'),source_seal_sha256=source_sha,
        input_archive=str(ia.resolve()),input_archive_sha256=W.sha(ia),input_seal_sha256=ih,public_inputs_sha256=public_sha,
        batch_size=1,parity_gate=False,shards=shards,profile_mode=True,cap_seconds=probe_cap,cumulative_cap_seconds=probe_cap,
        profile_real_items=6*shards,all_profile_outputs_discarded=True,regenerate_all_11064=True,labels_on_pod=False,
        argv=['python','/workspace/results/g_agreement/understand/e81/serial81.py','--inputs','/workspace/e81/inputs','--assets','/workspace/e56/assets.json',
              '--assignment','/workspace/e81/assignment.json','--out','/workspace/e81/out','--source-sha',source_sha,'--input-sha',ih])
    W.write(dest/'REQUEST.json',request);return request


def production(profile_request,report_path,dest,prior_seconds=0):
    q=W.read(profile_request);m=W.read(report_path);receipt=W.read(report_path.parent/'OUTPUT_SEAL.json')
    W.require(receipt['status']=='PROFILE_ONLY' and receipt['synthetic'] is False and receipt['files'].get('MEASURED_PROFILE.json')==W.sha(report_path),'sealed actual serial timing')
    W.require(m['status']=='SERIAL_TIMING_ONLY_NOT_SCIENCE' and m['authority']==AUTHORITY and m['batch_size']==1 and m['margin']==1.25 and
        m['source_seal_sha256']==q['source_seal_sha256'] and m['input_seal_sha256']==q['input_seal_sha256'] and
        m['public_inputs_sha256']==q['public_inputs_sha256'] and len(m['shards'])==q['shards'],'exact serial profile source/bank')
    W.require(receipt['files'].get('STAGING_RECEIPT.json')==m['staging_receipt_sha256']==W.sha(report_path.parent/'STAGING_RECEIPT.json'),'sealed staging receipt')
    staging=W.read(report_path.parent/'STAGING_RECEIPT.json');ass=W.read(report_path.parent/'ASSIGNMENT.json')
    from serial81 import staging_receipt
    W.require(staging==m['staging']==staging_receipt(ass,staging['worker_ready_epoch'],W.sha(report_path.parent/'ASSIGNMENT.json')) and
        receipt['files'].get('ASSIGNMENT.json')==staging['assignment_sha256'],'original provider assignment binding')
    for row in m['shards']:
        import math
        expected=1.25*(sum(row['phase_counts'][k]*row['seconds_per_item'][k] for k in ('128','32'))+staging['staging_seconds']+row['setup_warmup_seconds']+60)
        W.require(row['staging_seconds']==staging['staging_seconds'] and math.isclose(row['forecast_seconds'],expected,rel_tol=1e-12) and
            row['cap_seconds']==math.ceil(expected),'full-endpoint forecast including staging')
    W.require(W.sha(q['input_archive'])==q['input_archive_sha256'],'profile archive')
    dest.mkdir(parents=True,exist_ok=False);requests=[]
    for i,forecast in enumerate(m['shards']):
        W.require(forecast['shard']==i and forecast['cap_seconds']>60,'measured ordered shard caps')
        folder=dest/f'shard{i}';folder.mkdir()
        with tarfile.open(q['input_archive']) as a:a.extractall(folder,filter='data')
        inp=folder/'inputs';W.verify(inp,'INPUT_SEAL.json',q['input_seal_sha256'])
        plan=W.read(inp/'SERIAL_PLAN.json');plan.update(mode='production',shard=i,measured_profile_sha256=W.sha(report_path))
        W.write(inp/'SERIAL_PLAN.json',plan,replace=True)
        limits=W.read(inp/'STAGE_REQUEST.json');limits.update(cap_seconds=forecast['cap_seconds'],cumulative_cap_seconds=forecast['cap_seconds']+prior_seconds)
        W.write(inp/'STAGE_REQUEST.json',limits,replace=True);ih,ia=archive_inputs(inp)
        r=dict(q,status='READY_SERIAL_PRODUCTION_REQUIRES_OPERATOR_ADMISSION',profile_mode=False,shard=i,input_archive=str(ia.resolve()),
            input_archive_sha256=W.sha(ia),input_seal_sha256=ih,cap_seconds=forecast['cap_seconds'],cumulative_cap_seconds=limits['cumulative_cap_seconds'],
            measured_profile_sha256=W.sha(report_path),profile_output_seal_sha256=W.sha(report_path.parent/'OUTPUT_SEAL.json'))
        r['argv']=list(q['argv']);r['argv'][r['argv'].index('--input-sha')+1]=ih;r['argv']+=['--profile-report','/workspace/e81/MEASURED_PROFILE.json']
        W.write(folder/'REQUEST.json',r);requests.append(r)
    W.write(dest/'COORDINATED_RUN.json',dict(authority=AUTHORITY,total_items=11064,source_seal_sha256=q['source_seal_sha256'],
        public_inputs_sha256=q['public_inputs_sha256'],shards=requests,prior_seconds=prior_seconds,
        total_production_cap_seconds=sum(x['cap_seconds'] for x in requests),probe_items_repeated_in_production=True))
    return requests


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('profile');a.add_argument('--old-request',type=Path,required=True);a.add_argument('--destination',type=Path,required=True)
    a.add_argument('--shards',type=int,default=8);a.add_argument('--probe-cap',type=int,default=1800)
    a=sub.add_parser('production');a.add_argument('--profile-request',type=Path,required=True);a.add_argument('--report',type=Path,required=True)
    a.add_argument('--destination',type=Path,required=True);a.add_argument('--prior-seconds',type=float,required=True)
    a=p.parse_args()
    if a.command=='profile':prepare(a.old_request,a.destination,a.shards,a.probe_cap)
    else:production(a.profile_request,a.report,a.destination,a.prior_seconds)
