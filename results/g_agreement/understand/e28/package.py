"""Seal an already CPU-validated E28 worker package. No model or network operations."""
from pathlib import Path
import sys
import tarfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C


def main():
    r = C.HERE
    inp = r / 'cache/input-v1'
    C.verify(inp)
    names = ['contract.py', 'worker.py', 'analyze.py', 'package.py', 'test_e28.py',
             'PLAN.json', 'LORA_TARGETS.json', 'NOTES_2026-10-25.md', 'PREPARATION.json']
    extra = ['common/__init__.py', 'common/stats.py',
        'external/mats-nla-workspace/src/mats/__init__.py',
        'external/mats-nla-workspace/src/mats/metrics.py',
        'external/mats-nla-workspace/src/mats/readers/__init__.py',
        'external/mats-nla-workspace/src/mats/readers/olens.py',
        'external/mats-nla-workspace/src/mats/readers/nla.py',
        'projects/g_agreement/blindspot/__init__.py',
        'projects/g_agreement/blindspot/run.py', 'projects/g_agreement/blindspot/protocol.py',
        'projects/g_agreement/manifest/assets.json', 'projects/g_agreement/understand/__init__.py',
        'projects/g_agreement/understand/e24_statements.py']
    paths = [str((r/n).relative_to(C.ROOT)) for n in names] + extra
    C.dump(r / 'SOURCE_MANIFEST.json', {'files': {n: C.sha(C.ROOT/n) for n in sorted(paths)}})
    source_archive = r / 'cache/e28-source-v1.tar.gz'
    with tarfile.open(source_archive, 'w:gz') as t:
        for n in sorted(paths) + [str((r/'SOURCE_MANIFEST.json').relative_to(C.ROOT))]:
            t.add(C.ROOT/n, arcname=n)
    input_archive = r / 'cache/e28-input-v1.tar.gz'
    with tarfile.open(input_archive, 'w:gz') as t:
        for n in sorted(C.read(inp/'INPUT_SEAL.json')['files']) + ['INPUT_SEAL.json']:
            t.add(inp/n, arcname=n)
    for slot in range(2):
        assignment = {'issuer': 'integrator', 'experiment': 'E28', 'pod_id': 'REQUIRED',
            'slot': slot, 'pod_count': 2, 'runs': [list(x) for i, x in enumerate(C.RUNS) if i%2 == slot],
            'plan_sha256': C.sha(r/'PLAN.json'), 'target_mapping_sha256': C.sha(r/'LORA_TARGETS.json'),
            'source_manifest_sha256': C.sha(r/'SOURCE_MANIFEST.json'),
            'input_seal_sha256': C.sha(inp/'INPUT_SEAL.json'), 'assets_sha256': 'INTEGRATOR_SET_VERIFIED_ASSETS_SHA256',
            'source_published': False, 'source_commit': 'INTEGRATOR_SET_AFTER_PUBLICATION',
            'external_hardstop_verified': False, 'allocated_gpu_seconds': 9000, 'previous_gpu_seconds': 0,
            'provider_created_epoch': None, 'deadline_epoch': None}
        C.dump(r/f'ASSIGNMENT_SLOT{slot}.template.json', assignment)
    launch = {'experiment': 'E28', 'status': 'CPU_READY_FOR_INTEGRATOR_REVIEW_WARMED_FULL_GRID_GATE_REQUIRED',
        'authority_commit': '5731e92e0835e2a20d57a88cfcae7f3f57108fe4', 'lora_clarification_commit': '6481dd99',
        'worker_worktree_local': str(C.ROOT), 'branch': 'r/blindspot',
        'source_commit': 'INTEGRATOR_USE_COMMIT_CONTAINING_THIS_REQUEST', 'GPU_hours_local': 0,
        'gpu': 'H200 >=140GB; training memory and warmed fit are runtime gates', 'default_pods': 2, 'max_pods': 2,
        'budget': {'total_gpu_hours': 5, 'total_provider_gpu_seconds': 18000,
            'default_per_pod_provider_seconds': 9000, 'setup_seconds_max': 2400,
            'per_pod_science': 'min(1.5F+360,10800)s; nonresetting from first warmed forward',
            'retrieval_seconds': 180, 'retry_authorized': False,
            'programme_cutoff_utc': '2026-10-28T22:59:00Z'},
        'scope': {'rows': list(C.ROWS), 'L_rows': 6, 'B_rows': 6,
            'S_rows': ['prose_paren', 'prose_sentiment'], 'runs': 14, 'steps_per_run': 400,
            'batch_size': 8, 'checkpoints': list(C.CHECKPOINTS), 'asked_item_records': 7056,
            'final_free_readouts': 1176},
        'plan': 'results/g_agreement/understand/e28/PLAN.json', 'plan_sha256': C.sha(r/'PLAN.json'),
        'lora_targets': 'results/g_agreement/understand/e28/LORA_TARGETS.json',
        'lora_targets_sha256': C.sha(r/'LORA_TARGETS.json'),
        'source_manifest_sha256': C.sha(r/'SOURCE_MANIFEST.json'),
        'source_archive_local': str(source_archive), 'source_archive_sha256': C.sha(source_archive),
        'input_archive_local': str(input_archive), 'input_archive_sha256': C.sha(input_archive),
        'input_seal_sha256': C.sha(inp/'INPUT_SEAL.json'), 'input_archive_has_test_labels': False,
        'worker_command': 'python results/g_agreement/understand/e28/worker.py run --assignment ASSIGNMENT.json --mapping results/g_agreement/understand/e28/LORA_TARGETS.json --input INPUT_CACHE --assets VERIFIED_ASSETS.json --out NEW_OUTPUT_CACHE --admission ADMISSION.json',
        'admit_command': 'python results/g_agreement/understand/e28/worker.py admit --forecasts POD0/FORECAST.json POD1/FORECAST.json --out ADMISSION.json',
        'analysis_command': 'python results/g_agreement/understand/e28/analyze.py --input LOCAL_INPUT_WITH_PRIVATE_KEY --outputs POD0 POD1 --out NEW_ANALYSIS_CACHE',
        'evidence': C.read(r/'CPU_VALIDATION.json'),
        'readiness_limits': ['Actual CUDA loading/merging/training has not run',
            'No real warmed forecast has been measured', 'Integrator publication and external hardstops required'],
        'operations': 'Integrator alone publishes, assigns, launches, retrieves, terminates and consolidates shared logs. Full14runs only. E33 first. Global8pod ceiling and5minute launch spacing. No retry or scope cuts.'}
    C.dump(r/'LAUNCH_REQUEST.json', launch)
    print('E28 source and input archives sealed; no GPU operations')


if __name__ == '__main__':
    main()
