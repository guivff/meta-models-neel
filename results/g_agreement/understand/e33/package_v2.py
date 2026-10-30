"""Build the §133 E33 dose-sharded launch packet without changing scientific inputs."""
from __future__ import annotations

import gzip
import io
import json
from pathlib import Path
import tarfile

from prepare import HERE, dump, read, sha, verify

ROOT = HERE.parents[3]
PREFIX = 'results/g_agreement/understand/e33/'
CACHE = ROOT / 'cache/g_agreement/understand'


def archive(path, files):
    """Deterministic archive; verify bytes after closing it."""
    with path.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as tar:
            for name, source in sorted(files.items()):
                data = source.read_bytes()
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(data), 0o644, 0
                tar.addfile(info, io.BytesIO(data))
    with tarfile.open(path) as tar:
        assert set(tar.getnames()) == set(files)
        for member in tar.getmembers():
            import hashlib
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == sha(files[member.name])


def main():
    ops = read(HERE / 'OPERATIONS_2026-10-25.json')
    prior = read(HERE / 'PRIOR_ATTEMPT_ACCOUNTING.json')
    inputs = CACHE / 'e33-inputs-v1'
    verify(inputs)
    assert sha(HERE / 'PLAN.json') == ops['original_plan_sha256']
    assert sha(inputs / 'INPUT_SEAL.json') == ops['input_seal_sha256']
    assert ops['previous_gpu_seconds'] == prior['reserved_prior_gpu_seconds'] == 928
    assert sum(a['allocated_gpu_seconds'] for a in ops['default_allocations']) + 928 == 16200
    validation = read(HERE / 'CPU_VALIDATION_V2.json')
    assert validation['status'] == 'PASS'
    names = [str(p.relative_to(ROOT)) for p in sorted(HERE.glob('*.py'))]
    names += [PREFIX + n for n in ['PLAN.json', 'UPSTREAM_SOURCE.json', 'OPERATIONS_2026-10-25.json',
              'PRIOR_ATTEMPT_ACCOUNTING.json', 'REGISTERED_RULING_2026-10-25.md', 'HANDOFF_S133_2026-10-25.md', 'OWNER_READING_2026-10-25.md', 'HANDOFF_REPIN_2026-10-25.md']]
    names.append('projects/g_agreement/manifest/assets.json')
    pins = {name: sha(ROOT / name) for name in sorted(names)}
    source_archive = CACHE / 'e33-s136-source-v3.tar.gz'
    input_archive = CACHE / 'e33-s133-inputs-v1.tar.gz'
    archive(source_archive, {name: ROOT / name for name in names})
    input_files = read(inputs / 'INPUT_SEAL.json')['files']
    archive(input_archive, {name: inputs / name for name in [*input_files, 'INPUT_SEAL.json']})
    manifest = {'schema': 'E33_SOURCE_MANIFEST_v2', 'date': '2026-10-25', 'source_files': pins,
                'source_archive': str(source_archive.relative_to(ROOT)), 'source_archive_sha256': sha(source_archive),
                'archive_members_verified': True, 'input_archive': str(input_archive.relative_to(ROOT)),
                'input_archive_sha256': sha(input_archive), 'input_seal_sha256': sha(inputs / 'INPUT_SEAL.json')}
    dump(HERE / 'SOURCE_MANIFEST.json', manifest)
    common = {'schema': 'E33_RUN_PLAN_v2', 'experiment': 'E33', 'run_id': 'e33-s136-repin-20261025-v3',
              'operations_sha256': sha(HERE / 'OPERATIONS_2026-10-25.json'),
              'original_plan_sha256': ops['original_plan_sha256'], 'input_seal_sha256': ops['input_seal_sha256'],
              'previous_gpu_seconds': 928, 'global_cap_gpu_seconds': 16200, 'source_files': pins}
    plans = {'TWO_PODS': {**common, 'allocations': [{**a, 'pod_id': None} for a in ops['default_allocations']]},
             'SINGLE_POD': {**common, 'allocations': [{'slot': 0, 'pod_id': None, 'doses': [0, .25, .5, .75, 1],
                                                    'allocated_gpu_seconds': 15272, 'budget_envelope_gpu_seconds': 15272, 'infrastructure_loss_gpu_seconds': 0, 'infrastructure_losses': []}]}}
    dump(HERE / 'RUN_PLAN.template.json', plans['TWO_PODS'])
    dump(HERE / 'RUN_PLAN_SINGLE.template.json', plans['SINGLE_POD'])
    dump(HERE / 'INFRASTRUCTURE_LOSS.template.json', {
        'schema': 'E33_INFRASTRUCTURE_LOSS_v1', 'issuer': 'integrator', 'experiment': 'E33',
        'slot': None, 'pod_id': None, 'status': 'PENDING', 'stopped': False, 'setup_only': False,
        'science_gpu_seconds': 0, 'provider_gpu_seconds': None, 'provider_stopped_epoch': None})
    for mode, plan in plans.items():
        for a in plan['allocations']:
            label = 'SINGLE' if mode == 'SINGLE_POD' else f"SLOT{a['slot']}"
            assignment = {'issuer': 'integrator', 'experiment': 'E33', 'gpu_count': 1, 'pod_count': len(plan['allocations']),
                          **a, 'registered': True, 'pushed': False, 'external_hardstop_verified': False,
                          'previous_gpu_seconds': 928, 'provider_created_epoch': None, 'deadline_epoch': None,
                          'input_seal_sha256': ops['input_seal_sha256'], 'assets_sha256': None,
                          'source_files': pins, 'run_plan_sha256': None}
            dump(HERE / f'ASSIGNMENT_{label}.template.json', assignment)
    worker = ('python results/g_agreement/understand/e33/runtime.py run --inputs INPUTS '
              '--assets VERIFIED_ASSETS.json --run-plan GLOBAL_RUN_PLAN.json '
              '--assignment ASSIGNMENT.json --out cache/g_agreement/understand/e33-s133-SLOT')
    common_request = {'schema': 'E33_LAUNCH_REQUEST_v2', 'date': '2026-10-25', 'experiment': 'E33',
                      'authority_section': '§133 item5 + §136 operational rebuild', 'authority_commit': ops['authority_commit'],
                      'branch': 'r/blindspot', 'worker': 'W-lens',
                      'status': 'CPU_READY_FOR_INTEGRATOR_PUBLICATION_AND_OWN_WARMED_FORECAST',
                      'source_commit': 'Integrator resolves the commit containing this request; source pins are exact',
                      'source_manifest': PREFIX + 'SOURCE_MANIFEST.json', 'source_manifest_sha256': sha(HERE / 'SOURCE_MANIFEST.json'),
                      'source_archive': manifest['source_archive'], 'source_archive_sha256': manifest['source_archive_sha256'],
                      'input_archive': manifest['input_archive'], 'input_archive_sha256': manifest['input_archive_sha256'],
                      'input_seal_sha256': ops['input_seal_sha256'], 'original_plan_sha256': ops['original_plan_sha256'],
                      'operations_sha256': common['operations_sha256'],
                      'prior_accounting': PREFIX + 'PRIOR_ATTEMPT_ACCOUNTING.json',
                      'prior_accounting_sha256': sha(HERE / 'PRIOR_ATTEMPT_ACCOUNTING.json'),
                      'prior_booked_seconds': 927.1, 'prior_reserved_seconds': 928,
                      'total_experiment_cap_gpu_hours': 4.5, 'total_experiment_cap_gpu_seconds': 16200,
                      'new_allocated_seconds': 15272, 'source_files': pins, 'worker_command': worker,
                      'asset_schema': {'model': 'local pinned Qwen directory', 'olens': 'local pinned Oracle adapter directory',
                                       'revisions': {'model': '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9',
                                                     'olens': 'c95215d5d2f6250f20c305ae55c6e4d7569f92dc'},
                                       'files': '[{path,sha256}] covering all local model/adapter files'},
                      'per_pod_gpu_count': 1, 'gpu': 'H200 >=140 GB VRAM; pinned local assets',
                      'warmed_forecast_gate': {'per_assigned_path': 'one warm-up plus three timed units; median3',
                                               'admit': '1.5F+120 fits both remaining provider and science budgets',
                                               'science_cap': 'min(1.5F+360, assigned_provider_seconds)',
                                               'scope_cut_or_retry': False, 'no_fit': 'seal own shard failure and stop'},
                      'global_operations': {'operator': 'Integrator', 'pod_ceiling': 12, 'launch_spacing_seconds': 180,
                                            'source_publication_and_external_hardstop_required': True,
                                            'same_finalized_run_plan_on_every_pod': True, 'E28_launches_after_E33': True},
                      'scientific_scope': ops['scope'], 'unchanged_scientific_inputs': True, 'infrastructure_loss_allowance_seconds_per_slot': 600, 'infrastructure_loss_policy': ops['infrastructure_loss_policy'],
                      'infrastructure_loss_receipt_template': PREFIX + 'INFRASTRUCTURE_LOSS.template.json',
                      'ledger_freeze_order': 'Provision/stage both live pods and collect stopped-deploy receipts; freeze identical common run-plan bytes before either worker starts',
                      'validation': validation, 'new_GPU_jobs_launched_by_worker': False}
    requests = []
    for a in ops['default_allocations']:
        name = f"LAUNCH_REQUEST_SLOT{a['slot']}.json"
        item = {**common_request, 'slot': a['slot'], 'pod_count': 2, 'assigned_doses': a['doses'],
                'allocated_gpu_seconds': a['allocated_gpu_seconds'], 'expected_score_records': 2100 * 2 * len(a['doses']),
                'warmed_paths': 2 * len(a['doses']), 'run_plan_template': PREFIX + 'RUN_PLAN.template.json',
                'assignment_template': PREFIX + f"ASSIGNMENT_SLOT{a['slot']}.template.json",
                'worker_command': worker.replace('--assignment ASSIGNMENT.json', f"--assignment ASSIGNMENT_SLOT{a['slot']}.json").replace('e33-s133-SLOT', f"e33-s133-slot{a['slot']}")}
        dump(HERE / name, item)
        requests.append(PREFIX + name)
    main_request = {**common_request, 'default_pods': 2, 'max_pods': 2, 'shard_requests': requests,
                    'default_allocations': ops['default_allocations'], 'run_plan_template': PREFIX + 'RUN_PLAN.template.json',
                    'one_pod_alternative': {'run_plan_template': PREFIX + 'RUN_PLAN_SINGLE.template.json',
                                            'assignment_template': PREFIX + 'ASSIGNMENT_SINGLE.template.json',
                                            'allocated_gpu_seconds': 15272, 'doses': [0, .25, .5, .75, 1],
                                            'worker_command': worker.replace('--assignment ASSIGNMENT.json', '--assignment ASSIGNMENT_SINGLE.json').replace('e33-s133-SLOT', 'e33-s133-single'),
                                            'exclusive_with_two_pod_plan': True},
                    'analysis_command': 'python results/g_agreement/understand/e33/analyse.py --inputs INPUTS --collections SHARD0 SHARD1 --labels FROZEN_W1_PRIVATE_ITEMS --out cache/g_agreement/understand/e33-s133-analysis-v2',
                    'supersedes': 'Earlier E33 0.4GPUh one-pod launch request; no prior production scores are reused'}
    dump(HERE / 'LAUNCH_REQUEST.json', main_request)
    print(json.dumps({'status': 'PACKET_BUILT', 'source_archive_sha256': sha(source_archive),
                      'input_archive_sha256': sha(input_archive), 'new_seconds': 15272, 'prior_seconds': 928}))


if __name__ == '__main__':
    main()
