"""E58b once-only CPU analysis of the complete, verified eight-arm grid."""
import json
import time
import numpy as np
from common58 import *
from math58 import aggregate, check_basis
from worker58 import validate_bank, validate_pod_directory, memory_safe
from batching58 import choose_budget
from cpu_join58 import load_custodied_join, join_records

OUT = HERE / 'analysis_20261027'


def validate_pull():
    request = read(HERE / 'LAUNCH_REQUEST.json')
    require(request['status'] == 'READY', 'Unbound or scientifically held request')
    inp = CACHE / 'pod_inputs_v2'
    require(sha(inp / 'INPUT_SEAL.json') == request['input_seal_sha256'], 'Input seal mismatch')
    validate_pod_directory(inp)
    bank = read(inp / 'BANK.json')
    rows = validate_bank(bank)
    pull = CACHE / 'verified-pull-rerun1'
    receipt = read(pull / 'VERIFIED_PULL.json')
    require(receipt.get('issuer') == 'integrator' and receipt.get('experiment') == 'E58b'
            and receipt.get('verified_complete') is True, 'Integrator-verified complete pull required')
    final = pull / 'final'
    require(receipt['output_seal_sha256'] == sha(final / 'OUTPUT_SEAL.json'), 'Pull receipt seal mismatch')
    output = verify(final, 'OUTPUT_SEAL.json')
    require(output.get('status') == 'COMPLETE' and output.get('experiment') == 'E58b', 'Incomplete E58b grid')
    custody = read(final / 'CUSTODY.json'); a = custody['assignment']
    require(a.get('issuer') == 'integrator' and a.get('experiment') == 'E58b' and a.get('gpu_count') == 1
            and a.get('pod_id') == receipt.get('pod_id') and a.get('source_pushed') is True, 'Custody identity mismatch')
    require(custody['request_sha256'] == sha(HERE / 'LAUNCH_REQUEST.json') == a['request_sha256']
            and custody['input_seal_sha256'] == request['input_seal_sha256'] == a['input_seal_sha256']
            and custody['source_seal_sha256'] == sha(HERE / 'POD_SOURCE_SEAL.20261027.json') == a['source_seal_sha256']
            and request['analysis_source_seal_sha256'] == sha(HERE / 'SOURCE_SEAL.20261027.json'),
            'Scientific/code/request bindings mismatch')
    stopped = receipt['provider_stopped_epoch']
    require(all(finite_number(x) for x in (stopped, a['provider_created_epoch'], a['previous_gpu_seconds'],
            a['allocated_gpu_seconds'], a['deadline_epoch'], custody['completed_epoch'])), 'Finite custody required')
    require(a['previous_gpu_seconds'] >= 0 and 0 < a['allocated_gpu_seconds']
            and a['previous_gpu_seconds'] + a['allocated_gpu_seconds'] <= MAX_CAP
            and a['provider_created_epoch'] <= custody['completed_epoch'] <= stopped <= a['deadline_epoch']
            and stopped <= a['provider_created_epoch'] + a['allocated_gpu_seconds']
            and a['deadline_epoch'] <= PROGRAMME_STOP, 'Allocation/provider/programme cap violation')
    require(a.get('external_hardstop_verified') is True and a.get('hold_renewer_verified') is True,
            'Custody hardstop evidence required')
    require(a.get('prior_no_production_verified') is True and a.get('budget_watch_verified') is True
            and type(a.get('retry_number')) is int and a['retry_number'] == 1,
            'Prior no-production custody and selected-budget watcher required')
    budget = read(final / 'BUDGET.json'); benchmark = read(final / 'BENCHMARK.json')
    require(budget == choose_budget(a, budget['remaining_forecast_seconds'], budget['admitted_epoch']),
            'Budget decision does not reproduce from measured forecast/custody')
    require(budget['status'] == 'FIT' and budget['selected_total_gpu_seconds'] in (CAP, MAX_CAP), 'Measured budget admission missing')
    require(not budget['extension_used'] or (budget['preferred_fit'] is False and a.get('conditional_extension_authorized') is True),
            'Extension requires measured failure of registered cap')
    require(stopped <= budget['effective_provider_deadline_epoch']
            and a['previous_gpu_seconds'] + stopped - a['provider_created_epoch'] <= budget['selected_total_gpu_seconds'],
            'Actual custody exceeded selected cap')
    require(benchmark['selected_batch_size'] in (32, 64) and benchmark['real_frozen_prefixes'] is True
            and benchmark['pilot_scores_saved'] is False, 'Real batch/memory measurements required')
    selected = [v for v in benchmark['batch_candidates'] if v['batch_size'] == benchmark['selected_batch_size']]
    require(len(selected) == 1 and selected[0]['status'] == 'MEMORY_SAFE'
            and memory_safe(selected[0]['total_bytes'], selected[0]['free_after_bytes'], selected[0]['peak_reserved_bytes']),
            'Selected batch lacked measured memory admission')
    require(read(final / 'FORECAST.json').get('zero_projection_parity_exact') is True, 'Projection parity missing')
    pca = read(final / 'PCA_shared.json')
    require(pca['rows'] == [r['key'] for r in rows] and pca['dev_items'] == 84 * len(rows)
            and pca['rank'] == RANK and pca['test_activations_used'] is False
            and pca['same_subspace_for_every_row'] is True and pca['population'] == bank['pca_population'],
            'Shared pooled-dev PCA source/scope mismatch')
    require(pca['dev_samples'] == (sum(len(x['ids']) for r in rows for x in r['dev'])
            if bank['pca_population'] == 'pooled_dev_prompt_positions' else 84 * len(rows)), 'PCA sample-count mismatch')
    check_basis(np.load(final / 'PCA_shared.npy', allow_pickle=False))
    for seed in SEEDS:
        check_basis(np.load(final / f'random_basis_seed{seed}.npy', allow_pickle=False))
    records = [json.loads(line) for line in (final / 'scores.jsonl').read_text().splitlines()]
    cpu_join = load_custodied_join(request, bank, request['input_seal_sha256'])
    original_rows, oriented_records = join_records(bank, cpu_join, records)
    result = aggregate(original_rows, oriented_records)
    result.update(experiment='E58b', status='COMPLETE', source_seal_sha256=custody['source_seal_sha256'],
        input_seal_sha256=request['input_seal_sha256'], request_sha256=custody['request_sha256'],
        output_seal_sha256=sha(final / 'OUTPUT_SEAL.json'), arms=list(ARMS), rank=RANK, block=BLOCK,
        gpu_provider_seconds=stopped - a['provider_created_epoch'], analysis_invocations=1,
        analysis_source_seal_sha256=sha(HERE / 'SOURCE_SEAL.20261027.json'),
        cpu_custody_binding_sha256=sha(HERE / 'CPU_CUSTODY_BINDING.20261027.json'),
        labels_joined_on_cpu_only=True, pod_record_schema='separate_logp_A_logp_B')
    return result


def main():
    source_verify()
    for name, expected in read(HERE / 'COMMAND_SEAL.20261027.json')['files'].items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT.resolve()) and sha(path) == expected, 'Analysis command seal mismatch')
    dump(HERE / 'ANALYSIS.RUN_ONCE.json', {'experiment': 'E58b', 'started_epoch': time.time(),
        'source_seal_sha256': sha(HERE / 'SOURCE_SEAL.20261027.json')})
    OUT.mkdir(exist_ok=False)
    try:
        result = validate_pull()
        dump(OUT / 'RESULTS.json', result)
        r1, r2 = result['R_b1'], result['R_b2']
        lines = ['# E58b — registered J-space ablation', '',
            f"R-b1: {'HOLDS' if r1['met'] else 'DOES NOT HOLD'} ({r1['passing']}/3 controls).", '',
            f"R-b2: {r2['status'] if r2['met'] is None else 'HOLDS' if r2['met'] else 'DOES NOT HOLD'} ({r2['passing']}/{r2['denominator']} rows).", '',
            '| Bank/row | None log-odds | J damage | Random mean damage (5 seeds) | J/random | PCA damage |',
            '|---|---:|---:|---:|---:|---:|']
        for row in result['rows']:
            ratio = 'undefined (random=0)' if row['J_over_random_damage'] is None else f"{row['J_over_random_damage']:.6f}"
            label = row['row'] + (' (shallow content, descriptive)' if row['shallow_content_descriptive'] else '')
            lines.append(f"| {label} | {row['mean_correct_minus_wrong']['none']:.6f} | {row['damage']['J']:.6f} | {row['random_damage_mean5']:.6f} | {ratio} | {row['damage']['PCA']:.6f} |")
        lines += ['', 'Signed mean drops are used without clipping. Rows with PCA damage below random remain included and are listed in RESULTS.json. Each random seed is also reported there.', '']
        lines += ['## E57 paired-prompt swap controls (descriptive)', '',
                  '| Row | Swapped none | Swapped J | Swapped PCA |', '|---|---:|---:|---:|']
        for row in result['rows']:
            if 'paired_prompt_swap_control' in row:
                values = row['paired_prompt_swap_control']['mean_correct_minus_wrong']
                lines.append(f"| {row['row']} | {values['none']:.6f} | {values['J']:.6f} | {values['PCA']:.6f} |")
        lines += ['', 'Swap scores reuse the frozen opposite-state paired prompt with the same candidate pair and shared basis; no extra GPU forwards or primary-rule inputs.', '']
        (OUT / 'RESULTS.md').write_text('\n'.join(lines))
        seal(OUT, 'ANALYSIS_SEAL.json', experiment='E58b', status='COMPLETE',
             source_seal_sha256=result['source_seal_sha256'], output_seal_sha256=result['output_seal_sha256'],
             analysis_source_seal_sha256=result['analysis_source_seal_sha256'],
             cpu_custody_binding_sha256=result['cpu_custody_binding_sha256'])
    except Exception as exc:
        dump(OUT / 'FAILURE.json', {'status': 'VALIDATION_STOP', 'error_type': type(exc).__name__,
                                   'guard_preserved': True, 'retry_allowed': False})
        raise


if __name__ == '__main__':
    main()
