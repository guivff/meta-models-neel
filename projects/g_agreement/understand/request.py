"""Create the packed E3/E4 launch request from committed code and frozen inputs.

The individual-request function remains for historical reproducibility only.
The active user instruction is one E3_E4_PACK request, never two launches.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from projects.g_agreement.blindspot import protocol as P
from .budget import ROOT, PHASES, source_hashes
from .inputs import load_inputs


def create(experiment, inputs, tests, out):
    inputs, tests, out = map(Path, (inputs, tests, out))
    if out.exists():
        raise ValueError('launch request already exists')
    hashes = source_hashes()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    for path, digest in hashes.items():
        blob = subprocess.check_output(['git', 'show', commit+':'+path], cwd=ROOT)
        if hashlib.sha256(blob).hexdigest() != digest:
            raise ValueError('source differs from committed freeze: '+path)
    directories = [experiment.lower()] + (['e9'] if experiment == 'E4' else [])
    seals = {}; populations = {}
    for name in directories:
        data = load_inputs(inputs/name)
        seals['primary' if name == experiment.lower() else name] = P.sha(inputs/name/'INPUT_SEAL.json')
        populations[name] = {'n_items': len(data['items']), 'n_rows': len(data['rows']),
                            'items_per_row': 168 if name == 'e3' else 84}
    test_receipt = json.loads(tests.read_text())
    if test_receipt.get('status') != 'PASS' or test_receipt.get('gpu_hours') != 0:
        raise ValueError('passing offline CPU test receipt required')
    receipt = {
        'status': 'LAUNCH_REQUESTED_PENDING_INTEGRATOR_ASSIGNMENT_AND_WARMED_GATE',
        'experiment': experiment, 'owner': 'W-internals', 'exploratory': True,
        'branch': 'r/blindspot-internals', 'source_commit': commit, 'source_files': hashes,
        'brief': 'projects/g_agreement/BRIEF_UNDERSTAND.md',
        'brief_sha256': P.sha(ROOT/'projects/g_agreement/BRIEF_UNDERSTAND.md'),
        'implementation': 'projects/g_agreement/understand/INTERNALS.md',
        'local_input_parent': str(inputs.resolve()), 'stage_only': directories,
        'do_not_stage': 'labels.DO_NOT_STAGE.jsonl; never copy the entire input parent',
        'input_seals': seals, 'populations': populations, 'phases': list(PHASES[experiment]),
        'gpu_count': 1, 'max_science_seconds': 2160, 'setup_allowance_seconds': 1500,
        'science_cap_rule': 'min(1.5 * sum(warmed_phase_forecasts) + 360, 2160)',
        'warm_policy': 'one discarded warm-up; median of three timed units per phase including serialization/fsync/hash',
        'admission': 'all phase calibrations complete; used_science + full forecast <= cap; no population reduction',
        'operations': 'integrator pushes, assigns exact pod, stages local pinned assets, runs external hard stop, executes, pulls, and accounts custody',
        'assignment_required': {'experiment': experiment, 'pod_id': 'INTEGRATOR_MUST_FILL',
            'gpu_count': 1, 'hard_deadline_utc': 'INTEGRATOR_MUST_FILL_TIMEZONE_AWARE',
            'external_hard_stop_verified': True, 'setup_allowance_seconds': 1500,
            'max_science_seconds': 2160, 'source_files': hashes, 'input_seals': seals},
        'launch_argv': ['bash', 'projects/g_agreement/understand/pod_run.sh', experiment,
                        'STAGED_INPUT_PARENT', 'NEW_OUTPUT_DIRECTORY', 'PINNED_LOCAL_ASSETS_JSON', 'INTEGRATOR_ASSIGNMENT_JSON'],
        'after_pull_analysis_argv': ['python', '-m', 'projects.g_agreement.understand.analyse',
            '--experiment', experiment, '--inputs', str(inputs.resolve()), '--scores', 'PULLED_OUTPUT_DIRECTORY',
            '--labels', str((inputs/'labels.DO_NOT_STAGE.jsonl').resolve()),
            '--out', 'NEW_RESULTS_DIRECTORY', '--cache-out', 'NEW_ANALYSIS_CACHE_DIRECTORY'],
        'cpu_tests_receipt': str(tests.relative_to(ROOT) if tests.is_absolute() and tests.is_relative_to(ROOT) else tests),
        'cpu_tests_sha256': P.sha(tests), 'gpu_results': 'NOT_RUN',
        'clarifications': ['J-lens E3 residual layers are not applicable; named input and J_h stages retained',
            'E3 asked head excludes all candidate tokens; one production forward per item',
            'E4 J-lens objective is native cosine contrast, not probabilistic log-odds',
            'E9 all40 target rows fit within E4 allocation or gate returns NO-GO',
            'Exact target JVP requires real-kernel second-derivative support; test during calibration, no proxy fallback'],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    P.dump(out, receipt)
    return receipt


def create_packed(inputs, tests, out, *, e4_only=False):
    """One launch request for the user-authorized E3 then E4 packed process."""
    from .packed import input_seals
    inputs, tests, out = map(Path, (inputs, tests, out))
    if out.exists():
        raise ValueError('launch request already exists')
    hashes = source_hashes()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    for path, digest in hashes.items():
        blob = subprocess.check_output(['git', 'show', commit+':'+path], cwd=ROOT)
        if hashlib.sha256(blob).hexdigest() != digest:
            raise ValueError('source differs from committed freeze: '+path)
    sequence = ['E4'] if e4_only else ['E3', 'E4']
    experiment = 'E4_ONLY_RETRY' if e4_only else 'E3_E4_PACK'
    populations = {}
    for name in (('e4', 'e9') if e4_only else ('e3', 'e4', 'e9')):
        data = load_inputs(inputs/name)
        populations[name] = {'n_items': len(data['items']), 'n_rows': len(data['rows']),
                            'items_per_row': 168 if name == 'e3' else 84}
    validation = json.loads(tests.read_text())
    if validation.get('status') != 'PASS' or validation.get('gpu_hours') != 0:
        raise ValueError('passing offline CPU test receipt required')
    seals = input_seals(inputs, e4_only=True) if e4_only else input_seals(inputs)
    assignment = {'experiment': experiment, 'sequence': sequence,
        'pod_id': 'INTEGRATOR_MUST_FILL', 'gpu_count': 1,
        'hard_deadline_utc': 'INTEGRATOR_MUST_FILL_TIMEZONE_AWARE',
        'external_hard_stop_verified': True, 'setup_allowance_seconds': 1500,
        'max_science_seconds': {e: 2160 for e in sequence},
        'source_files': hashes, 'input_seals': seals}
    receipt = {'status': 'LAUNCH_REQUESTED_PENDING_INTEGRATOR_ASSIGNMENT_AND_EACH_WARMED_GATE',
        'experiment': experiment, 'owner': 'W-internals', 'sequence': sequence,
        'branch': 'r/blindspot-internals', 'source_commit': commit, 'source_files': hashes,
        'brief': 'projects/g_agreement/BRIEF_UNDERSTAND.md',
        'brief_sha256': P.sha(ROOT/'projects/g_agreement/BRIEF_UNDERSTAND.md'),
        'implementation': 'projects/g_agreement/understand/PACKED.md',
        'single_process': True, 'gpu_count': 1,
        'resources': {'gpu_memory_gib_at_least': 80, 'available_host_memory_gib_at_least': 160,
                      'disk_free_gib_at_least': 40},
        'model_loads': {'olens': 1, 'nla': 1, 'jlens_tensors': 1, 'target': 'aliases loaded Oracle base'},
        'residency': 'models retained in host RAM, offloaded before next GPU activation; no disk reload between experiments',
        'setup_allowance_seconds': 1500, 'experiment_science_caps_seconds': {e: 2160 for e in sequence},
        'cap_rule_each': 'min(1.5 * warmed_forecast + 360, 2160), elapsed from that experiment first science step; never reset',
        'timing_each': 'one unscored warm-up + median of three timed units per phase; transfer forecast included; E4 starts only after E3 seal',
        'local_input_parent': str(inputs.resolve()), 'stage_only': list(populations),
        'do_not_stage': 'labels.DO_NOT_STAGE.jsonl or entire parent directory',
        'input_seals': seals, 'populations': populations,
        'output_folders': {e: 'PACK_OUT/'+e.lower() for e in sequence},
        'assignment_required': assignment,
        'environment': {'venv': '/weights/venv', 'python': '/weights/venv/bin/python',
            'reason': 'E4 exact target-logit JVP requires second derivatives; use the integrator-designated environment',
            'variables': {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}},
        'launch_argv': ['/weights/venv/bin/python', '-m', 'projects.g_agreement.understand.packed',
            '--inputs', 'STAGED_INPUT_PARENT', '--out', 'NEW_PACK_OUT',
            '--assets', 'PINNED_LOCAL_ASSETS_JSON', '--assignment', 'INTEGRATOR_ASSIGNMENT_JSON'],
        'cpu_tests_receipt': str(tests), 'cpu_tests_sha256': P.sha(tests),
        'operations': 'integrator pushes, supplies pod/asset/deadline assignment, external hard stop, runs process, pulls artifacts and accounts provider custody',
        'gpu_results': 'NOT_RUN', 'exploratory': True,
        'limits': ['J-lens has no residual stream; E3 reports N/A and named native stages',
            'E9 exact full-logit JVP kernel support is checked at E4 calibration; unsupported or over-budget work stops without proxy/subsampling',
            'Stopped experiment partials are sealed by CPU I/O with separately recorded custody overhead; no GPU retry or cap borrowing']}
    if e4_only:
        receipt['launch_argv'].append('--e4-only')
        receipt['authorization'] = 'One E4-only OOM retry under §91 amendment 4af1004b1e184cfce6bbf2a67a432ebe72e916bc'
        receipt['previous_attempt'] = {'pod_id': 'cybhnezi82omzz', 'status': 'CUDA_OUT_OF_MEMORY',
                                       'science_seconds': 23.7, 'retain_original_accounting': True}
        receipt['memory_policy'] = {'reader_activations_per_batch': 1, 'candidate_sequences_per_batch': 2,
                                    'target_items_per_batch': 1, 'saved_autograd_tensors': 'CPU offload, pinned memory',
                                    'items_prompts_scope': 'unchanged; all 25 reader rows and all 40 E9 rows'}
        receipt['resources']['available_host_memory_gib_at_least'] = 192
        receipt['timing_each'] = 'One unscored warm-up and median of three timed units per phase, with CPU offload and transfers included; continuous E4 clock from first science step'
        receipt['allocation_policy'] = 'Fresh integrator allocation/assignment and new output folder; one authorized retry; no E3 rerun or borrowing/resetting prior clocks'
        receipt['after_pull_analysis_argv'] = ['/weights/venv/bin/python', '-m', 'projects.g_agreement.understand.analyse',
            '--experiment', 'E4', '--inputs', str(inputs.resolve()), '--scores', 'PULLED_PACK_OUT/e4',
            '--labels', str((inputs/'labels.DO_NOT_STAGE.jsonl').resolve()), '--out', 'NEW_RESULTS_DIRECTORY',
            '--cache-out', 'NEW_ANALYSIS_CACHE_DIRECTORY']
    out.parent.mkdir(parents=True, exist_ok=True); P.dump(out, receipt)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment', choices=('E3', 'E4', 'E3_E4_PACK', 'E4_ONLY_RETRY'), required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--tests', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    r = create_packed(a.inputs, a.tests, a.out, e4_only=a.experiment == 'E4_ONLY_RETRY') if a.experiment in ('E3_E4_PACK', 'E4_ONLY_RETRY') else create(a.experiment, a.inputs, a.tests, a.out)
    print(json.dumps({'experiment': r['experiment'], 'status': r['status'], 'source_commit': r['source_commit']}))


if __name__ == '__main__':
    main()
