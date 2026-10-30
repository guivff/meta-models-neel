"""Create an E17 launch receipt from committed items and committed source only."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

from projects.g_agreement.blindspot import protocol as P
from . import e17_items as I, e17_run as R
from .e17_analysis import METRIC_SPEC

FROZEN = P.ROOT / 'results/g_agreement/understand/e17'
STAGE = P.ROOT / 'cache/g_agreement/understand/e17-stage-v1'
ITEM_COMMIT = '75f60d3d'
AUTHORITY = '409690eef4efe65ac222c80b0c446f91ba448ce2'


def git(*args):
    return subprocess.check_output(['git', '-C', str(P.ROOT), *args])


def stage_frozen(stage=STAGE):
    """Restore exact committed bytes after cache loss; never regenerate new items."""
    stage = Path(stage)
    freeze = FROZEN / 'freeze'
    manifest = json.loads((freeze / 'manifest.json').read_text())
    payload = gzip.decompress((freeze / 'items.jsonl.gz').read_bytes())
    if (P.sha(freeze / 'items.jsonl.gz') != manifest['full_bank_gzip_sha256']
            or hashlib.sha256(payload).hexdigest() != manifest['full_bank_uncompressed_sha256']):
        raise ValueError('committed item-bank hash mismatch')
    items = [json.loads(line) for line in payload.decode().splitlines()]
    labels = stage.parent / (stage.name + '.labels.DO_NOT_STAGE.jsonl')
    if not stage.exists():
        stage.mkdir(parents=True, exist_ok=False)
        for name in ('manifest.json', 'phrasings.json', 'pairs.json', 'INPUT_SEAL.json'):
            (stage / name).write_bytes((freeze / name).read_bytes())
        P.jsonl(stage / 'items.input.jsonl', [{k: x[k] for k in I.STAGE_KEYS} for x in items])
    if not labels.exists():
        P.jsonl(labels, [{k: x[k] for k in ('id', 'feature', 'cell', 'split', 'cluster', 'lexical_id', 'pair_id', 'label', 'value')} for x in items])
    if P.sha(labels) != manifest['labels_sha256']:
        raise ValueError('restored label hash mismatch')
    P.verify(stage, 'INPUT_SEAL.json')
    R.inputs(stage)
    return labels


def receipt():
    stage_frozen()
    source_commit = git('rev-parse', 'HEAD').decode().strip()
    item_commit = git('rev-parse', ITEM_COMMIT).decode().strip()
    hashes = R.source_hashes()
    for name, digest in hashes.items():
        if hashlib.sha256(git('show', source_commit + ':' + name)).hexdigest() != digest:
            raise ValueError('runtime source must be committed first: ' + name)
    frozen = FROZEN / 'freeze'
    for path in frozen.iterdir():
        rel = str(path.relative_to(P.ROOT))
        if git('show', item_commit + ':' + rel) != path.read_bytes():
            raise ValueError('frozen bank changed after item commit: ' + rel)
    archive = STAGE.parent / f'e17-source-{source_commit[:8]}.tar.gz'
    names = sorted(set(hashes) | {'projects/g_agreement/understand/e17_request.py'})
    # Allowlist only: the committed labelled bank is deliberately absent.
    archive.write_bytes(git('archive', '--format=tar.gz', source_commit, *names))
    with tarfile.open(archive) as tar:
        for name, digest in hashes.items():
            if hashlib.sha256(tar.extractfile(name).read()).hexdigest() != digest:
                raise ValueError('source archive mismatch: ' + name)
        if any('DO_NOT_STAGE' in name or name.endswith('items.jsonl.gz') for name in tar.getnames()):
            raise ValueError('labelled bank in source archive')
    P.dump(FROZEN / 'METRIC_SPEC.json', METRIC_SPEC)
    result = {
        'schema': 'e17-horizon-launch-v1', 'status': 'REQUESTED_NOT_ASSIGNED_AWAITING_MEASURED_FORECAST',
        'experiment': 'E17', 'section': 110, 'recipient': 'phase-r integrator', 'brief_commit': AUTHORITY,
        'manifest_commit': item_commit, 'source_commit': source_commit, 'source_files': hashes,
        'source_archive_local': str(archive), 'source_archive_sha256': P.sha(archive),
        'stage_path_local': str(STAGE), 'input_seal_sha256': P.sha(STAGE / 'INPUT_SEAL.json'),
        'manifest_sha256': P.sha(STAGE / 'manifest.json'),
        'frozen_bank_path': str(frozen / 'items.jsonl.gz'), 'frozen_bank_sha256': P.sha(frozen / 'items.jsonl.gz'),
        'registered_section_sha256': P.sha(FROZEN / 'REGISTERED_SECTION.md'),
        'metric_spec_sha256': P.sha(FROZEN / 'METRIC_SPEC.json'),
        'scope': '1920 fresh items /960 pairs /10cells; source44 and real-next16 AR44 vectors; Oracle native continuation and W1 asked, both2pairs, true/random/opposite arms; all dev+test retained;11520 score records',
        'requested_gpu': 'one H200-class GPU with sufficient host RAM for parked27B backbone; /weights/venv',
        'science_cap_gpu_seconds': 3600, 'staging_allowance_seconds': 2400, 'previous_gpu_seconds': 0,
        'maximum_custody_seconds_including_retrieval': 6180,
        'timing': 'setup unscored warmups; immutable firstscience before retained acquisition; median3 actual retained production units per capturecell/scoringfeaturepath and AR; fullremaining forecast includes residencytransfer; capmin(1.5F+360,3600);180s retrieval reserve; NO_FIT without scope reduction or retry',
        'priority': 'W12 freeze Sunday25October evening must not be delayed. Integrator alone publishes/operates E17.',
        'synchronization': 'clean isolated pull --rebase failed GitHub DNS; authority read via GitHub connector; reconcile local branch r/e17-horizon before publication, never push stale branch wholesale',
        'stage_allowlist': ['items.input.jsonl', 'manifest.json', 'phrasings.json', 'pairs.json', 'INPUT_SEAL.json'],
        'do_not_stage': ['freeze/items.jsonl.gz', '*.labels.DO_NOT_STAGE.jsonl', 'any other experiment bank or output'],
        'required_assignment': ['issuer=integrator', 'experiment=E17', 'pod_id', 'source_commit', 'source_files',
            'manifest_commit', 'manifest_sha256', 'input_seal_sha256', 'brief_commit', 'brief_registered=true',
            'brief_pushed=true', 'manifest_committed=true', 'external_hardstop_verified=true', 'provider_created_epoch',
            'deadline_epoch', 'allocated_gpu_seconds', 'science_cap_gpu_seconds=3600', 'staging_allowance_seconds=2400',
            'previous_gpu_seconds=0'],
        'official_AR_source': {'path': '/workspace/understand/official-ar', 'git_commit': 'a32590085a6070d75f950155d3c2b3db3eec97ef'},
        'whitener': {'path': '/workspace/understand/whitener.pt', 'sha256': '178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a'},
        'worker_command': 'python -m projects.g_agreement.understand.e17_run --bank STAGED_E17_BANK --assignment ASSIGNMENT.json --assets VERIFIED_ASSETS.json --official /workspace/understand/official-ar --whitener /workspace/understand/whitener.pt --out NEW_E17_OUTPUT',
        'analysis_command': 'OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m projects.g_agreement.understand.e17_analysis --bank ORIGINAL_STAGED_E17_BANK --outputs RETRIEVED_E17_OUTPUT --labels cache/g_agreement/understand/e17-stage-v1.labels.DO_NOT_STAGE.jsonl --out NEW_E17_ANALYSIS',
        'restore_stage_command': 'python -m projects.g_agreement.understand.e17_request stage',
        'retrieval': ['SCORE_SEAL.json', 'CAPTURE_SEAL.json', 'source44.npy', 'window44.npy', 'items.order.json',
            'scores.jsonl', 'provenance.json', 'unit_plan.json', 'FORECAST.json', 'EXPERIMENT_CLOCK.json',
            'SCIENCE_RECEIPT.json', 'STATUS.json', 'FAILURE.json if present', 'units/', 'worker logs', 'exact assignment'],
        'no_capture_or_scoring_performed_here': True,
    }
    P.dump(FROZEN / 'LAUNCH_REQUEST.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('stage', 'receipt'))
    a = p.parse_args()
    if a.command == 'stage':
        print(stage_frozen())
    else:
        result = receipt()
        print(json.dumps({k: result[k] for k in ('status', 'manifest_commit', 'source_commit', 'source_archive_sha256', 'input_seal_sha256')}, indent=2))
