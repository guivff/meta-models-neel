"""Prepare E13(a)'s fresh-only staged inputs and committed-source receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from projects.g_agreement.blindspot import protocol as P
from . import e13_completion as E

ROOT = P.ROOT
FROZEN = ROOT/'results/g_agreement/understand/e13a'
STAGE = ROOT/'cache/g_agreement/understand/e13a-stage-v1'
SECTION = 'results/g_agreement/understand/e13a/REGISTERED_SECTION.md'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def prepare():
    bank = ROOT/'cache/g_agreement/blindspot/w1b-stage-v1'
    capture = ROOT/'cache/g_agreement/blindspot/w1b-units/ybqkwg5zoc3vwg/w1b-out/target'
    P.verify(bank, 'INPUT_SEAL.json')
    P.verify(capture, 'CAPTURE_SEAL.json')
    P.verify(capture, 'SCORE_SEAL.json')
    if FROZEN.exists() or STAGE.exists():
        raise ValueError('preserve existing preparation')
    FROZEN.mkdir(parents=True)
    authority = git('rev-parse', 'fa68a633').decode().strip()
    text = git('show', authority+':projects/g_agreement/BRIEF_UNDERSTAND.md').decode()
    section = text[text.index('## §101'):].split('\n## §102')[0]
    (ROOT/SECTION).write_text(section)
    source = P.code_hashes()
    for name in ('projects/g_agreement/understand/__init__.py',
                 'projects/g_agreement/understand/e13_completion.py',
                 'projects/g_agreement/understand/e13_request.py', SECTION):
        source[name] = P.sha(ROOT/name)
    provenance = json.loads((capture/'provenance.target.json').read_text())
    manifest = {'experiment': 'E13a', 'section': 101, 'authority_commit': authority,
                'authority_section_sha256': P.sha(ROOT/SECTION),
                'user_amendment': 'Fresh FULL free-target phase; no resume/reuse of unsealed 3200/3360 partial. Same §84 code/items/settings. Cap min(1.5F+360,2400).',
                'input_seal_sha256': P.sha(bank/'INPUT_SEAL.json'),
                'capture_seal_sha256': P.sha(capture/'CAPTURE_SEAL.json'),
                'asked_score_seal_sha256': P.sha(capture/'SCORE_SEAL.json'),
                'original_source_files': provenance['source_files'], 'source_files': source,
                'items': 1680, 'rows': 10, 'readers': list(E.READERS), 'samples_per_reader': 2,
                'expected_records': 10080, 'batch': 32, 'science_cap_gpu_seconds': E.CAP,
                'staging_allowance_seconds': E.SETUP, 'no_new_capture': True,
                'old_partial_outputs_used': False, 'scope_reduction_allowed': False,
                'decoding_sha256': P.sha(bank/'decoding.json'), 'runtime_sha256': P.sha(bank/'runtime.json')}
    items, _, _ = E.verify_inputs(bank, capture, manifest)
    STAGE.mkdir(parents=True)
    shutil.copytree(bank, STAGE/'bank')
    (STAGE/'capture').mkdir()
    # Exact allowlist: never enumerate or stage any unasked file, sealed or partial.
    names = ('acts42.npy', 'acts44.npy', 'items.order.json', 'provenance.capture.json',
             'provenance.target.json', 'scores.target.jsonl', 'CAPTURE_SEAL.json', 'SCORE_SEAL.json')
    for name in names:
        shutil.copyfile(capture/name, STAGE/'capture'/name)
    manifest['capture_stage_allowlist'] = list(names)
    P.dump(FROZEN/'manifest.json', manifest)
    P.dump(STAGE/'manifest.json', manifest)
    for name in ('decoding.json', 'runtime.json', 'INPUT_SEAL.json'):
        shutil.copyfile(bank/name, FROZEN/name)
    E.verify_inputs(STAGE/'bank', STAGE/'capture', manifest)
    return manifest


def receipt():
    manifest_path = FROZEN/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    source = git('rev-parse', 'HEAD').decode().strip()
    for name, digest in manifest['source_files'].items():
        if hashlib.sha256(git('show', source+':'+name)).hexdigest() != digest:
            raise ValueError('uncommitted/changed source: '+name)
    relative = str(manifest_path.relative_to(ROOT))
    if git('show', source+':'+relative) != manifest_path.read_bytes():
        raise ValueError('commit manifest before receipt')
    manifest_commit = git('log', '-1', '--format=%H', '--', relative).decode().strip()
    archive = ROOT/f'cache/g_agreement/understand/e13a-source-{source[:8]}.tar.gz'
    if archive.exists():
        raise ValueError('preserve existing archive')
    git('archive', '--format=tar.gz', '--output='+str(archive), source, '--', *sorted(manifest['source_files']))
    request = {'schema': 'e13a-fresh-free-target-v1', 'experiment': 'E13a', 'section': 101,
        'status': 'REQUESTED_NOT_ASSIGNED_AWAITING_MEASURED_FORECAST', 'recipient': 'phase-r integrator',
        'source_commit': source, 'source_files': manifest['source_files'],
        'source_archive_local': str(archive), 'source_archive_sha256': P.sha(archive),
        'manifest_commit': manifest_commit, 'manifest_path_local': str(manifest_path),
        'manifest_sha256': P.sha(manifest_path), 'brief_commit': manifest['authority_commit'],
        'registered_section_path': SECTION, 'registered_section_sha256': manifest['authority_section_sha256'],
        'stage_path_local': str(STAGE), 'input_seal_sha256': manifest['input_seal_sha256'],
        'capture_seal_sha256': manifest['capture_seal_sha256'], 'asked_score_seal_sha256': manifest['asked_score_seal_sha256'],
        'command': 'python -m projects.g_agreement.understand.e13_completion --receipt LAUNCH_REQUEST.json --manifest STAGED/manifest.json --bank STAGED/bank --capture STAGED/capture --assignment ASSIGNMENT.json --assets VERIFIED_ASSETS.json --out NEW_EMPTY_OUTPUT_PATH',
        'environment': '/weights/venv', 'requested_gpu': 'one H200-class GPU; same pinned target/Oracle/J-lens assets as §84',
        'items': 1680, 'rows': 10, 'records': 10080, 'readers': list(E.READERS),
        'scope': 'Fresh full free-target: Oracle 3360 + deterministic repeated J-lens3360 + logit3360. No new capture or asked scoring. Old unsealed 3200/3360 Oracle partial is not staged/read/resumed.',
        'science_cap_gpu_seconds': E.CAP, 'staging_allowance_seconds': E.SETUP, 'previous_gpu_seconds': 0,
        'setup': '1500 seconds outside science; unchanged model loads and one unscored full 32-item canonical warm-up per reader path.',
        'science': 'Persistent first-science clock before first timed unit. Median of3 timed canonical batches per reader; forecast=elapsed science+sum(median*53). Timing outputs discarded. Full pass from item0 with unchanged seeds/batches/sampling. Cap min(1.5F+360,2400). NO_FIT without scope reduction.',
        'required_assignment': ['issuer=integrator', 'experiment=E13a', 'pod_id', 'request_sha256',
            'source_commit', 'source_files', 'brief_commit', 'brief_registered=true', 'brief_pushed=true',
            'manifest_commit', 'manifest_sha256', 'manifest_committed=true', 'provider_created_epoch',
            'deadline_epoch', 'allocated_gpu_seconds', 'science_cap_gpu_seconds=2400',
            'staging_allowance_seconds=1500', 'previous_gpu_seconds=0', 'external_hardstop_verified=true'],
        'retrieval': ['FREE_SEAL.json', 'unasked.target.jsonl', 'provenance.unasked.target.json',
                      'WARMUP.json', 'FORECAST.json', 'EXPERIMENT_CLOCK.json', 'SCIENCE_RECEIPT.json',
                      'STATUS.json', 'FAILURE.json if present', 'worker log', 'exact assignment'],
        'operations': 'Integrator alone publishes/allocates/operates. Exact archived source and fresh output directory; absolute external hardstop with180s retrieval reserve. No automatic retries. E13(b) remains lens-chat-owned; no labels/judge in this launch.'}
    P.dump(FROZEN/'LAUNCH_REQUEST.json', request)
    return request


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['prepare', 'receipt'])
    a = p.parse_args()
    (prepare if a.command == 'prepare' else receipt)()
