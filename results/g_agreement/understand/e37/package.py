"""Freeze the conditional E37 request; creates no pod and loads no model."""
from __future__ import annotations
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PREFIX = 'results/g_agreement/understand/e37/'
CACHE = ROOT / 'cache/g_agreement/understand'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, v):
    p.write_text(json.dumps(v, indent=2, sort_keys=True, allow_nan=False) + '\n')


def archive(path, files):
    with path.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as z:
        with tarfile.open(fileobj=z, mode='w') as tar:
            for name, source in sorted(files.items()):
                data = source.read_bytes()
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(data), 0o644, 0
                tar.addfile(info, io.BytesIO(data))
    with tarfile.open(path) as tar:
        assert set(tar.getnames()) == set(files)
        for member in tar.getmembers():
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == sha(files[member.name])


def main():
    inputs = CACHE / 'e37-inputs-v1'
    seal = read(inputs / 'INPUT_SEAL.json')
    for name, digest in seal['files'].items():
        assert sha(inputs / name) == digest
    assert read(inputs / 'provenance.json')['plan_sha256'] == sha(HERE / 'PLAN.json')
    assert read(HERE / 'PARITY_GATE.json')['input_seal_sha256'] == sha(inputs / 'INPUT_SEAL.json')
    validation = read(HERE / 'CPU_VALIDATION.json')
    assert validation['status'] == 'PASS'
    names = [str(p.relative_to(ROOT)) for p in HERE.glob('*.py')]
    names += [PREFIX + n for n in ('PLAN.json', 'PARITY_GATE.json', 'SMOKE_SET.json',
              'SOURCE_REFERENCES.json', 'HANDOFF_2026-10-25.md', 'OWNER_READING_2026-10-25.md')]
    names += ['results/g_agreement/understand/e33/runtime.py', 'projects/g_agreement/manifest/assets.json',
              'projects/g_agreement/understand/e24_statements.py',
              'external/mats-nla-workspace/src/mats/__init__.py',
              'external/mats-nla-workspace/src/mats/metrics.py',
              'external/mats-nla-workspace/src/mats/readers/__init__.py',
              'external/mats-nla-workspace/src/mats/readers/olens.py',
              'external/mats-nla-workspace/src/mats/readers/nla.py']
    names += list(read(HERE / 'SOURCE_REFERENCES.json')['files']['repository'])
    pins = {name: sha(ROOT / name) for name in sorted(names)}
    source_archive, input_archive = CACHE / 'e37-source-v1.tar.gz', CACHE / 'e37-inputs-v1.tar.gz'
    archive(source_archive, {name: ROOT / name for name in pins})
    archive(input_archive, {name: inputs / name for name in [*seal['files'], 'INPUT_SEAL.json']})
    manifest = {'schema': 'E37_SOURCE_MANIFEST_v1', 'source_files': pins,
                'source_archive': str(source_archive.relative_to(ROOT)), 'source_archive_sha256': sha(source_archive),
                'input_archive': str(input_archive.relative_to(ROOT)), 'input_archive_sha256': sha(input_archive),
                'input_seal_sha256': sha(inputs / 'INPUT_SEAL.json'), 'archive_members_verified': True}
    dump(HERE / 'SOURCE_MANIFEST.json', manifest)
    receipt = {'schema': 'E37_SFT_RECEIPT_v1', 'status': 'BLOCKED_AWAITING_CHECKPOINT', 'issuer': 'integrator',
               'provided_by': 'Agam', 'checkpoint_identity': 's3d.omp4bp.s2/step251',
               'identity_verified': False, 'received_epoch': None, 'local_path': None, 'files': {},
               'base_model_revision': '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9',
               'frozen_before_model_calls': False, 'model_calls_before_freeze': 0}
    dump(HERE / 'CHECKPOINT_RECEIPT.template.json', receipt)
    predecessors = {'schema': 'E37_PREREQUISITE_COMPLETION_v1', 'issuer': 'integrator',
                    'status': 'PENDING', 'experiments': {n: {'status': 'PENDING', 'receipts': []} for n in ('E33', 'E28')}}
    dump(HERE / 'PREDECESSORS.template.json', predecessors)
    assignment = {'issuer': 'integrator', 'experiment': 'E37', 'gpu_count': 1, 'pod_id': None,
                  'registered': True, 'pushed': False, 'external_hardstop_verified': False,
                  'allocated_gpu_seconds': 5400, 'previous_gpu_seconds': 0,
                  'provider_created_epoch': None, 'deadline_epoch': None,
                  'input_seal_sha256': sha(inputs / 'INPUT_SEAL.json'), 'plan_sha256': sha(HERE / 'PLAN.json'),
                  'parity_gate_sha256': sha(HERE / 'PARITY_GATE.json'), 'assets_sha256': None,
                  'checkpoint_receipt_sha256': None, 'predecessors_sha256': None, 'source_files': pins}
    dump(HERE / 'ASSIGNMENT.template.json', assignment)
    command = ('python results/g_agreement/understand/e37/runtime.py run --inputs INPUTS '
               '--assets VERIFIED_ASSETS.json --checkpoint-receipt CHECKPOINT_RECEIPT.json '
               '--predecessors PREDECESSORS.json --parity-gate results/g_agreement/understand/e37/PARITY_GATE.json '
               '--assignment ASSIGNMENT.json --out cache/g_agreement/understand/e37-run-v1')
    request = {'schema': 'E37_LAUNCH_REQUEST_v1', 'experiment': 'E37', 'date': '2026-10-25',
               'status': 'BLOCKED_AWAITING_CHECKPOINT', 'owner': 'W-lens', 'operator': 'Integrator',
               'branch': 'r/blindspot', 'registration_commit': read(HERE / 'PLAN.json')['registration_commit'],
               'clarification_commit': read(HERE / 'PLAN.json')['clarification_commit'],
               'source_commit': 'Integrator resolves commit containing this request; exact source hashes below',
               **manifest, 'schema': 'E37_LAUNCH_REQUEST_v1',
               'source_manifest_sha256': sha(HERE / 'SOURCE_MANIFEST.json'),
               'plan_sha256': sha(HERE / 'PLAN.json'), 'parity_gate_sha256': sha(HERE / 'PARITY_GATE.json'),
               'checkpoint_received_by': '2026-10-27T20:00:00+01:00',
               'missing_or_late_checkpoint': 'NOT_RUN; no substitute checkpoint',
               'launch_priority_after': ['E33', 'E28'],
               'release_gate': ['Original step251 provided by Agam arrives on time; complete bytes and identity frozen before any forward',
                                'E33 and E28 complete or explicitly closed by Integrator with no active pods',
                                'Source published, all file hashes verified, assignment and external hardstop in force',
                                'Both-arm smoke repeat and RL three-row AUROC parity PASS; any failure stops',
                                'Eight-path warmed forecast admits full scope within5400provider GPU-seconds'],
               'gpu': '1 H200 >=140GB; same pinned Qwen base and local Oracle assets as E33',
               'max_gpu_hours': 1.5, 'max_provider_seconds': 5400, 'retrieval_reserve_seconds': 120,
               'science_cap': 'min(1.5F+360,5400); setup included in provider cap',
               'forecast': 'Each arm/channel path warm once then three timed units; median3; C4 timing forces128 decoding steps, discards outputs',
               'scope': {'arms': ['RL', 'SFT'], 'rows': 25, 'items_per_row': 84, 'layer': 44,
                         'C1': 4200, 'C1prime': 4200, 'C2_matched': 1176, 'C2_opposite': 1176,
                         'C4': 4200, 'score_records': 10752},
               'worker_command': command,
               'validate_command': command.replace('runtime.py run', 'runtime.py validate').split(' --out ')[0],
               'analysis_command': 'python results/g_agreement/understand/e37/analyse.py --inputs INPUTS --collection COMPLETE_COLLECTION --labels FROZEN_W1_PRIVATE_ITEMS --out cache/g_agreement/understand/e37-analysis-v1',
               'checkpoint_receipt_template': PREFIX + 'CHECKPOINT_RECEIPT.template.json',
               'assignment_template': PREFIX + 'ASSIGNMENT.template.json',
               'predecessors_template': PREFIX + 'PREDECESSORS.template.json',
               'global_operations': {'pod_ceiling': 12, 'launch_spacing_seconds': 180,
                                     'programme_deadline_utc': '2026-10-28T22:59:00Z'},
               'validation': validation, 'GPU_jobs_launched_by_worker': False,
               'limitations': ['No step251 checkpoint received or loaded', 'No real GPU parity or throughput measurement',
                               '252 fixed gate labels only staged; full private key remains off worker']}
    dump(HERE / 'LAUNCH_REQUEST.json', request)
    print(json.dumps({'status': request['status'], 'source_archive_sha256': sha(source_archive),
                      'input_archive_sha256': sha(input_archive), 'input_seal_sha256': manifest['input_seal_sha256']}))


if __name__ == '__main__':
    main()
