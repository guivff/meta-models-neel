"""Rebind the unchanged public E81/E90 bank to the batched source and admitted cap."""
import argparse
import math
import shutil
import tarfile
from pathlib import Path
from worker81 import HERE, ROOT, read, write, sha, seal, verify, require, validate


def build(old_request, destination, cap_seconds, profile_only, measured_profile=None, phase_timings=None, profile_seal=None):
    old=read(old_request)
    require(type(cap_seconds) is int and cap_seconds>60,'positive integrator-admitted cap')
    if not profile_only:
        require(measured_profile is not None,'production requires measured profile')
        require(phase_timings is not None and profile_seal is not None,'sealed phase timings required')
        receipt=read(profile_seal)
        require(receipt['status']=='PROFILE_ONLY' and receipt.get('synthetic') is False and receipt['files'].get('MEASURED_PROFILE.json')==sha(measured_profile) and
                receipt['files'].get('PHASE_TIMINGS.json')==sha(phase_timings),'verified profile pull binding')
        measured=read(measured_profile)
        timings=read(phase_timings)
        measured_seeds={}
        for phase in ('base_text128','base_text32'):
            samples=[x['seconds'] for x in timings if x['phase']==phase and x['status']=='COMPLETE' and x['real']]
            require(len(samples)==3,'three measured real batches per phase')
            measured_seeds[phase]=sum(samples)/len(samples)
        require(measured['status']=='TIMING_ONLY_NOT_SCIENCE' and
                measured['batches_per_phase']==3 and measured['parity_items_per_phase']==8,
                'complete representative timing and parity')
        require(cap_seconds>=math.ceil(measured['forecast_seconds']),'measured forecast times1.25')
    require(sha(old['input_archive'])==old['input_archive_sha256'],'original input archive')
    destination.mkdir(parents=True,exist_ok=False)
    with tarfile.open(old['input_archive']) as archive:
        archive.extractall(destination,filter='data')
    inp=destination/'inputs'
    verify(inp,'INPUT_SEAL.json',old['input_seal_sha256'])
    validate(read(inp/'PUBLIC_INPUTS.json'))
    public_sha=sha(inp/'PUBLIC_INPUTS.json')
    limits=read(inp/'STAGE_REQUEST.json')
    limits.update(cap_seconds=cap_seconds,cumulative_cap_seconds=cap_seconds,
                  batch_size=64,account_gate_USD=1500,status='READY')
    if not profile_only:
        limits['seed_seconds_per_batch'].update(measured_seeds)
        limits['measured_profile_sha256']=sha(measured_profile)
        limits['profile_output_seal_sha256']=sha(profile_seal)
    write(inp/'STAGE_REQUEST.json',limits,replace=True)
    (inp/'INPUT_SEAL.json').unlink()
    input_sha=seal(inp,'INPUT_SEAL.json',experiment='E81',owner_public_sha256=public_sha)
    source_sha=sha(HERE/'SOURCE_SEAL.json');verify(HERE,'SOURCE_SEAL.json',source_sha)
    deps=read(HERE/'DEPENDENCIES.json')
    for name,h in deps.items():require(sha(ROOT/name)==h,'source dependency '+name)
    names=set(deps)|{str((HERE/n).relative_to(ROOT)) for n in read(HERE/'SOURCE_SEAL.json')['files']}|{str((HERE/'SOURCE_SEAL.json').relative_to(ROOT))}
    with tarfile.open(destination/'source.tar.gz','w:gz') as archive:
        for name in sorted(names):archive.add(ROOT/name,arcname=name,recursive=False)
    with tarfile.open(destination/'inputs.tar.gz','w:gz') as archive:archive.add(inp,arcname='inputs')
    request=dict(old,status='READY_FOR_TIMING_PROBE' if profile_only else 'READY_AFTER_MEASURED_ADMISSION',
        source_archive=str((destination/'source.tar.gz').resolve()),source_archive_sha256=sha(destination/'source.tar.gz'),
        input_archive=str((destination/'inputs.tar.gz').resolve()),input_archive_sha256=sha(destination/'inputs.tar.gz'),
        source_seal_sha256=source_sha,input_seal_sha256=input_sha,cap_seconds=cap_seconds,
        cumulative_cap_seconds=cap_seconds,profile_only=profile_only,public_inputs_sha256=public_sha,
        batch_size=64,serial_parity_items_per_phase=8,regenerate_all_11064_in_production=True,
        actual_checkpoint_parity='PENDING live gate',labels_on_pod=False,integrator_owns_launch=True)
    for name in ('forecast','exact_preflight_sha256','admission','alongside'):request.pop(name,None)
    request['measured_profile_sha256']=sha(measured_profile) if measured_profile else None
    argv=[x for x in request['argv'] if x!='--profile-only'];request['argv']=argv;argv[argv.index('--source-sha')+1]=source_sha;argv[argv.index('--input-sha')+1]=input_sha
    if profile_only:argv.append('--profile-only')
    write(destination/'REQUEST.json',request)
    return request


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--old-request',type=Path,required=True);p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--cap-seconds',type=int,required=True);p.add_argument('--profile-only',action='store_true')
    p.add_argument('--measured-profile',type=Path);p.add_argument('--phase-timings',type=Path);p.add_argument('--profile-seal',type=Path)
    a=p.parse_args();build(a.old_request,a.destination,a.cap_seconds,a.profile_only,a.measured_profile,a.phase_timings,a.profile_seal)
