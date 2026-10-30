"""Prepare a sealed, label-free bank and a verifiable request for the integrator."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from . import protocol as P


def git(*args):
    return subprocess.check_output(['git', '-C', str(P.ROOT), *args])


def export_freeze(bank, destination):
    """Copy the small audit receipts to the version-controlled results tree."""
    bank, destination = Path(bank), Path(destination)
    P.verify(bank, 'INPUT_SEAL.json')
    destination.mkdir(parents=True, exist_ok=False)
    for name in ('manifest.json', 'INPUT_SEAL.json', 'lengths.json', 'templates.json', 'decoding.json', 'runtime.json'):
        shutil.copyfile(bank/name, destination/name)


def stage_bank(bank, destination):
    bank, destination = Path(bank), Path(destination)
    receipt = P.verify(bank, 'INPUT_SEAL.json')
    if any('DO_NOT_STAGE' in n for n in receipt['files']):
        raise ValueError('input seal improperly includes labels')
    destination.mkdir(parents=True, exist_ok=False)
    for name in [*receipt['files'], 'INPUT_SEAL.json']:
        (destination/name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bank/name, destination/name)
    P.verify(destination, 'INPUT_SEAL.json')
    return receipt


def launch_request(bank, freeze, experiment='W1', execution_plan=None):
    bank, freeze = Path(bank).resolve(), Path(freeze).resolve()
    if experiment not in P.CAP_SECONDS:
        raise ValueError('unknown experiment')
    if execution_plan is not None and experiment == 'W1b':
        raise ValueError('W1 execution plan cannot authorize W1b')
    P.verify(bank, 'INPUT_SEAL.json')
    relative = str((freeze/'manifest.json').relative_to(P.ROOT))
    commit = git('log', '-1', '--format=%H', '--', relative).decode().strip()
    if not commit:
        raise ValueError('commit the frozen manifest before requesting capture')
    committed = git('show', f'{commit}:{relative}')
    if hashlib.sha256(committed).hexdigest() != P.sha(bank/'manifest.json'):
        raise ValueError('committed manifest differs from bank')
    source_commit = git('rev-parse', 'HEAD').decode().strip()
    source_files = P.code_hashes()
    for path, digest in source_files.items():
        if hashlib.sha256(git('show', f'{source_commit}:{path}')).hexdigest() != digest:
            raise ValueError('commit current source bytes before requesting capture: '+path)
    result = {'schema': 'blindspot-pod-request-v2', 'status': 'REQUESTED_NOT_ASSIGNED',
        'recipient': 'phase-r integrator', 'branch': 'r/blindspot', 'experiment': experiment,
        'section': {'W1':70, 'W5':74, 'W1b':84}[experiment],
        'cap_gpu_seconds': P.CAP_SECONDS[experiment], 'prior_gpu_seconds': 0,
        'source_commit': source_commit, 'source_files': source_files,
        'brief_commit': git('log','-1','--format=%H','--',P.BRIEF).decode().strip(),
        'brief_path': P.BRIEF, 'brief_sha256': P.sha(P.ROOT/P.BRIEF),
        'manifest_commit': commit, 'manifest_path': relative,
        'manifest_sha256': P.sha(bank/'manifest.json'),
        'input_seal_sha256': P.sha(bank/'INPUT_SEAL.json'),
        'bank_path_local': str(bank), 'assets_pin_path': 'projects/g_agreement/manifest/assets.json',
        'requested_gpu': 'one H100 80 GB or H200; sequential target/Oracle and NLA processes',
        'required_assignment': ['exact pod_id', 'provider_created_epoch', 'deadline_epoch',
            'allocated_gpu_seconds', 'previous_gpu_seconds', 'external_hardstop_verified',
            'source_commit', 'source_files', 'brief_commit', 'brief_sha256', 'brief_registered',
            'brief_pushed', 'manifest_commit', 'manifest_sha256', 'manifest_committed'],
        'operational_note': 'All staging/loading/custody counts within cap; reserve final 180 s for retrieval. No pod has been allocated by this receipt.'}
    if experiment == 'W1b':
        result.update(science_cap_gpu_seconds=3600, staging_allowance_seconds=1500,
            operational_note='Integrator-authorized §84 setup allowance is outside 3600 science seconds. '
                'Science starts at the persistent first-science clock, shared across target/NLA phases; '
                'never use creation plus setup as the science start. Keep the independent absolute '
                'custody hardstop and final 180-second retrieval reserve. No pod allocated here.')
        result['required_assignment'] += ['science_cap_gpu_seconds', 'staging_allowance_seconds']
    if execution_plan is not None:
        from .execution import validate_plan
        execution_plan = Path(execution_plan).resolve()
        plan = validate_plan(bank, execution_plan)
        if plan.get('runtime_source_files') != source_files:
            raise ValueError('execution plan runtime source differs')
        path = str(execution_plan.relative_to(P.ROOT))
        plan_commit = git('log','-1','--format=%H','--',path).decode().strip()
        if not plan_commit or hashlib.sha256(git('show',f'{plan_commit}:{path}')).hexdigest() != P.sha(execution_plan):
            raise ValueError('commit execution plan before requesting capture')
        result.update(execution_plan_path=path, execution_plan_commit=plan_commit,
                      execution_plan_sha256=P.sha(execution_plan),
                      execution_plan_committed=True, manifest_committed=True,
                      execution_modes=['parallel if integrator confirms concurrent volume reads', 'serial fallback'],
                      priority_features=['table_column','prose_paren','prose_sentiment','python_effect','latex_subject'],
                      early_export='training/dev-only probe directions and class means, after priority score seals; no test exports or W1 decision',
                      final_analysis='Once, after every frozen W1 row is scored and assembled',
                      w5_order='After complete W1 analysis',
                      aggregate_w1_gpu_seconds=P.CAP_SECONDS['W1'])
        result['required_assignment'] += ['execution_plan_commit', 'execution_plan_sha256',
                                         'execution_plan_committed']
        if experiment == 'W1':
            result['required_assignment'] += ['execution_units',
                'allocation_group: mode, previous_gpu_seconds, allocations for every pod; reservations sum within 7200 seconds']
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['export-freeze','stage-bank','request'])
    parser.add_argument('--bank',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--freeze',type=Path)
    parser.add_argument('--experiment',choices=list(P.CAP_SECONDS),default='W1')
    parser.add_argument('--execution-plan',type=Path)
    args=parser.parse_args(argv)
    with P.logged('stage-'+args.action):
        if args.action=='export-freeze': export_freeze(args.bank,args.out)
        elif args.action=='stage-bank': stage_bank(args.bank,args.out)
        else:
            if args.freeze is None: parser.error('--freeze is required for a request')
            P.dump(args.out,launch_request(args.bank,args.freeze,args.experiment,args.execution_plan))


if __name__=='__main__': main()
