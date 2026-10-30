"""Commit-verified §86 launch receipt and source archive, no pod operations."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from . import protocol as P
from .w10_items import source_hashes, SECTION


def git(*args):
    return subprocess.check_output(['git', '-C', str(P.ROOT), *args])


def launch_request(bank, freeze, staged, archive):
    bank, freeze, staged, archive = map(lambda p: Path(p).resolve(), (bank, freeze, staged, archive))
    P.verify(bank, 'INPUT_SEAL.json')
    P.verify(staged, 'INPUT_SEAL.json')
    if P.sha(bank/'INPUT_SEAL.json') != P.sha(staged/'INPUT_SEAL.json'):
        raise ValueError('stage differs from full local bank')
    relative = str((freeze/'manifest.json').relative_to(P.ROOT))
    manifest_commit = git('log', '-1', '--format=%H', '--', relative).decode().strip()
    if not manifest_commit or hashlib.sha256(git('show', manifest_commit+':'+relative)).hexdigest() != P.sha(bank/'manifest.json'):
        raise ValueError('commit the exact manifest before requesting capture')
    source_commit = git('rev-parse', 'HEAD').decode().strip()
    hashes = source_hashes()
    manifest = json.loads((bank/'manifest.json').read_text())
    if manifest['source_files'] != hashes:
        raise ValueError('source changed after freeze')
    for path, digest in hashes.items():
        if hashlib.sha256(git('show', source_commit+':'+path)).hexdigest() != digest:
            raise ValueError('commit exact source first: '+path)
    for path in freeze.iterdir():
        relative_file = str(path.relative_to(P.ROOT))
        if hashlib.sha256(git('show', source_commit+':'+relative_file)).hexdigest() != P.sha(path):
            raise ValueError('freeze file not committed: '+relative_file)
    if archive.exists():
        raise ValueError('source archive already exists; preserve it')
    archive.parent.mkdir(parents=True, exist_ok=True)
    git('archive', '--format=tar.gz', '--output='+str(archive), source_commit, '--', *sorted(hashes))
    origin = json.loads((P.ROOT/'results/g_agreement/blindspot/w10/REGISTRATION_ORIGIN.json').read_text())
    return {'schema': 'blindspot-w10-launch-v1', 'status': 'REQUESTED_NOT_ASSIGNED_AWAITING_MEASURED_FORECAST',
        'recipient': 'phase-r integrator', 'branch': 'r/blindspot', 'experiment': 'W10', 'section': 86,
        'source_commit': source_commit, 'source_files': hashes, 'source_archive_local': str(archive),
        'source_archive_sha256': P.sha(archive), 'manifest_commit': manifest_commit,
        'manifest_path': relative, 'manifest_sha256': P.sha(bank/'manifest.json'),
        'input_seal_sha256': P.sha(bank/'INPUT_SEAL.json'), 'brief_commit': origin['commit'],
        'brief_path': origin['path'], 'section86_path': SECTION, 'section86_sha256': P.sha(P.ROOT/SECTION),
        'bank_path_local': str(bank), 'stage_path_local': str(staged),
        'mode_rows': 14, 'mode_items': 1680, 'mode_checks': 280, 'surprisal_pool_items': 2688,
        'science_cap_gpu_seconds': 3600, 'staging_allowance_seconds': 1500, 'previous_gpu_seconds': 0,
        'science_allocation_formula': '1.5 * measured complete-work forecast + 360; NO_FIT if above 3600',
        'timing': 'Persistent first-science clock begins before timed smoke; setup/load/unscored synthetic warm-up outside science. Smoke, capture, scoring and 280 free continuations inside it. Independent absolute hardstop and final 180 s retrieval reserve retained.',
        'requested_gpu': 'one H200 141GB or larger; target/Oracle, J and NLA resident before science; fail setup rather than silently change runtime',
        'judge_cap_usd': 3, 'judge_packets': 200, 'script_checks': 80,
        'attempt_policy': 'one attempt; only integrator may authorize one retry after documented pure infrastructure failure with zero science; no automatic relaunch',
        'worker_module': 'projects.g_agreement.blindspot.w10_run',
        'worker_command': 'python -m projects.g_agreement.blindspot.w10_run --bank STAGED_BANK --assignment INTEGRATOR_ASSIGNMENT.json --assets VERIFIED_ASSETS.json --out NEW_W10_OUTPUT_DIRECTORY',
        'required_assignment': ['issuer=integrator', 'experiment=W10', 'pod_id', 'source_commit', 'source_files',
            'brief_commit', 'section86_sha256', 'brief_registered=true', 'brief_pushed=true', 'manifest_commit',
            'manifest_sha256', 'manifest_committed=true', 'provider_created_epoch', 'deadline_epoch',
            'allocated_gpu_seconds', 'science_cap_gpu_seconds', 'staging_allowance_seconds=1500',
            'previous_gpu_seconds=0', 'external_hardstop_verified=true'],
        'retrieval': ['CAPTURE_SEAL.json', 'acts42.npy', 'acts44.npy', 'items.order.json', 'surprisal.jsonl',
                      'provenance.json', 'FORECAST.json', 'SCORE_SEAL.json', 'scores.jsonl',
                      'MODE_GENERATION_SEAL.json', 'mode_generations.jsonl', 'assignment science-clock.json'],
        'analysis_contract': 'Verify all seals and complete score grid before local label join. W-core owns analysis. Two phrasing scores retained; signed A-minus-B orientation, no sign flip. Surprisal pool labels derived from sealed base-model logits only after scores sealed. Mode gates from frozen 20 dev items, test rules on six held-out passage families. §84 generation remains integrator-owned.',
        'open_dependency': 'Camila reconstructor text-window confirmation; record window and qualify interpretation, no rule change or blind-by-construction claim assumed.',
        'operations': 'Integrator pushes local commits, stages the exact allowlist and source archive, verifies pinned assets/environment, arms independent guards and operates the pod. W-core made no pod or API calls.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('bank', 'freeze', 'stage', 'archive', 'out'):
        p.add_argument('--'+name, required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('request already exists')
    P.dump(a.out, launch_request(a.bank, a.freeze, a.stage, a.archive))


if __name__ == '__main__':
    main()
