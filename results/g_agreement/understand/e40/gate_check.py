"""§149 E40 gate receipt check. CPU-only, once; PASS also calls frozen verify_pass."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PLAN = 'ANALYSIS_PLAN.gate-check.20261026.json'
CODE_SEAL = 'ANALYSIS_CODE_SEAL.gate-check.20261026.json'
SAMPLE_SHA = 'dff73a3a83b76a6de4a5a2cbf2fe909a14a6888eaa9b91eeca6df849323fc593'


class ValidationStop(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise ValidationStop(code)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def reject_constant(_):
    raise ValidationStop('nonfinite_json_constant')


def read(path):
    require(Path(path).stat().st_size <= 4 * 1024 * 1024, 'oversized_json')
    return json.loads(Path(path).read_text(), parse_constant=reject_constant)


def write_new(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def integer(x, minimum=0, maximum=None):
    return type(x) is int and x >= minimum and (maximum is None or x <= maximum)


def number(x, minimum=0, positive=False):
    return (type(x) in (int, float) and math.isfinite(x)
            and (x > minimum if positive else x >= minimum))


def sha_string(x):
    return isinstance(x, str) and re.fullmatch('[0-9a-f]{64}', x) is not None


def fixed_path(relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute()
            and '..' not in Path(relative).parts, 'invalid_repository_relative_path')
    path = (ROOT / relative).resolve()
    base = (ROOT / 'cache').resolve() if Path(relative).parts[0] == 'cache' else ROOT.resolve()
    require(path.is_relative_to(base), 'path_outside_owner_workspace')
    return path


def verify_code():
    seal = read(HERE / CODE_SEAL)
    require(seal.get('experiment') == 'E40' and seal.get('status') == 'FROZEN', 'invalid_code_seal')
    required = {(HERE / n).relative_to(ROOT).as_posix() for n in ('gate_check.py', PLAN)}
    require(required <= set(seal.get('files', {})), 'incomplete_analysis_code_seal')
    for relative, expected in seal['files'].items():
        require(digest(fixed_path(relative)) == expected, 'analysis_source_checksum_mismatch')
    plan = read(HERE / PLAN)
    require(plan.get('experiment') == 'E40' and plan.get('analysis') == 'gate_check', 'invalid_analysis_plan')
    require(digest(fixed_path(plan['training_request_path'])) == plan.get('training_request_sha256'),
            'analysis_plan_training_request_mismatch')
    require(str(plan.get('authority_commit', '')).startswith('886d03b0'), 'wrong_overnight_authority')
    # Check the existing project's CPU dependency before claiming any analysis.
    # This helper imports Torch but performs no model inference or judge call.
    from followup import verify_pass
    require(callable(verify_pass), 'verify_pass_helper_unavailable')
    return plan


def metric(record, *, expected_n=None):
    require(isinstance(record, dict), 'missing_gate_metric')
    n = record.get('n_tokens')
    require(integer(n, 1, 50000) and (expected_n is None or n == expected_n), 'wrong_gate_token_count')
    require(record.get('d_model') == 5120 and record.get('d_sae') == 65536, 'wrong_gate_dimensions')
    sse, variance, fvu = (record.get(k) for k in ('squared_error', 'total_variance', 'fvu'))
    require(number(sse) and number(variance, positive=True) and number(fvu), 'invalid_gate_moments')
    require(math.isclose(sse / variance, fvu, rel_tol=1e-12, abs_tol=1e-15), 'inconsistent_gate_fvu')
    dead = record.get('dead_latents')
    require(integer(dead, 0, 65536) and number(record.get('dead_fraction')), 'invalid_dead_count')
    require(math.isclose(record['dead_fraction'], dead / 65536, rel_tol=0, abs_tol=1e-15), 'inconsistent_dead_fraction')
    fvu_pass, dead_pass = fvu <= .25, 10 * dead < 65536
    require(record.get('fvu_pass') is fvu_pass and record.get('dead_pass') is dead_pass
            and record.get('passed') is (fvu_pass and dead_pass), 'inconsistent_gate_flags')
    return fvu_pass and dead_pass


def resolve_artifacts(pull):
    final, arrays = pull / 'final', pull / 'arrays'
    seal = read(final / 'OUTPUT_SEAL.json')
    pins = seal.get('files')
    require(isinstance(pins, dict) and {'GATE_RESULT.json', 'CLOCK.json'} <= set(pins), 'incomplete_output_seal')
    paths = {}
    for name, expected in pins.items():
        require(isinstance(name, str) and Path(name).name == name and name not in ('.', '..')
                and sha_string(expected), 'invalid_output_seal_entry')
        candidates = [p for p in (final / name, arrays / name) if p.is_file()]
        require(candidates, 'missing_sealed_output')
        # Duplicate copies are allowed only when every copy matches the original.
        for path in candidates:
            require(path.resolve().is_relative_to((ROOT / 'cache/g_agreement/understand/e40').resolve()),
                    'artifact_outside_e40_cache')
            require(digest(path) == expected, 'pulled_artifact_checksum_mismatch')
        paths[name] = candidates[0]
    return seal, paths


def check_scientific_result(gate, paths, assignment, plan):
    required = {'TRAINING_RESULT.json', 'CALIBRATION.json', 'CALIBRATION_SEAL.json',
                'GATE.RUN_ONCE.json', 'layer44.e40.sae.pt', 'RUNTIME.json', 'PILOT.json', 'capture_ledger.jsonl'}
    require(required <= set(paths), 'incomplete_scientific_output')
    training, calibration, calibration_seal, gate_guard = [read(paths[n]) for n in
        ('TRAINING_RESULT.json', 'CALIBRATION.json', 'CALIBRATION_SEAL.json', 'GATE.RUN_ONCE.json')]
    checkpoint_sha, calibration_sha = digest(paths['layer44.e40.sae.pt']), digest(paths['CALIBRATION.json'])
    require(gate.get('sae_checkpoint_sha256') == checkpoint_sha
            and gate.get('calibration_sha256') == calibration_sha, 'unbound_final_checkpoint_or_calibration')
    require(calibration_seal.get('status') == 'COMPLETE'
            and type(calibration_seal.get('before_training_step')) is int
            and calibration_seal['before_training_step'] == 1
            and calibration_seal.get('files') == {'CALIBRATION.json': calibration_sha}, 'calibration_not_sealed_before_step1')
    require(calibration.get('population_tokens') == 1000000
            and calibration.get('d_model') == 5120
            and calibration.get('position_zero_included') is False
            and calibration.get('heldout_statistics_used') is False
            and calibration.get('single_capture_pass') is True
            and calibration.get('source_manifest_sha256') == assignment.get('sources_sha256'), 'wrong_calibration_population')
    median, threshold, mean, scale = [calibration.get(k) for k in
        ('median_raw_norm', 'outlier_threshold_raw_norm', 'mean_raw_norm_after_outlier_exclusion', 'scale')]
    require(all(number(x, positive=True) for x in (median, threshold, mean, scale))
            and threshold == 10 * median
            and math.isclose(scale * mean, math.sqrt(5120), rel_tol=1e-12), 'wrong_fixed_scaling_constants')
    kept, removed = calibration.get('calibration_retained'), calibration.get('calibration_outliers')
    require(integer(kept, 1, 1000000) and integer(removed, 0, 999999)
            and kept + removed == 1000000, 'wrong_calibration_exclusion_counts')
    require(training.get('experiment') == 'E40' and training.get('status') == 'COMPLETE'
            and training.get('synthetic') is False and training.get('training_tokens') == 100000000
            and training.get('optimizer_updates') == 24415
            and training.get('config') == plan['training_configuration']
            and training.get('data_passes') == 1 and training.get('recaptured_training_occurrences') == 0
            and training.get('checkpoint_selection') == 'final_only'
            and training.get('sae_checkpoint_sha256') == checkpoint_sha
            and training.get('calibration_sha256') == calibration_sha
            and training.get('sources_sha256') == assignment.get('sources_sha256')
            and training.get('normalization', {}).get('scale') == scale
            and gate.get('scale') == scale, 'incomplete_or_inconsistent_final_training')
    require(gate_guard.get('checkpoint_sha256') == checkpoint_sha
            and gate_guard.get('calibration_sha256') == calibration_sha
            and gate_guard.get('sample_sha256') == SAMPLE_SHA, 'unbound_once_only_gate')
    require(gate.get('primary_gate') == 'filtered' and gate.get('all_token_fvu_descriptive') is True
            and gate.get('sae_k') == 128 and gate.get('error_type') is None
            and gate.get('failure_category') is None, 'wrong_scientific_gate_contract')
    metrics = gate.get('metrics') or {}
    filtered, all_tokens, exclusions = [metrics.get(k) for k in ('filtered', 'all_tokens', 'excluded')]
    passed = metric(filtered)
    metric(all_tokens, expected_n=50000)
    require(all_tokens.get('rule_applied') is False, 'all_token_fvu_must_be_descriptive')
    require(isinstance(exclusions, dict) and all(integer(exclusions.get(k), 0, 50000) for k in
            ('position_zero', 'norm_above_threshold', 'overlap', 'union')), 'invalid_gate_exclusions')
    zero, high, overlap, union = [exclusions[k] for k in ('position_zero', 'norm_above_threshold', 'overlap', 'union')]
    require(zero == plan['expected_position_zero_tokens'] and overlap <= min(zero, high)
            and union == zero + high - overlap and filtered['n_tokens'] == 50000 - union,
            'gate_exclusion_population_mismatch')
    require(gate['status'] == ('PASS' if passed else 'FAIL'), 'status_disagrees_with_registered_thresholds')
    return {'verdict': 'PASS' if passed else 'FAIL', 'filtered_gate': filtered,
            'all_token_fvu': all_tokens['fvu'], 'all_token_metrics_descriptive': all_tokens,
            'exclusions': exclusions, 'calibration': {k: calibration[k] for k in
                ('population_tokens', 'median_raw_norm', 'outlier_threshold_raw_norm', 'scale')},
            'sae_checkpoint_sha256': checkpoint_sha, 'calibration_sha256': calibration_sha,
            'eligible_for_131_preparation': passed,
            'next_action': 'W-sae morning review, then owner blind labelling and unchanged §131 decomposition' if passed else
                           'No adequate SAE; stop E40, no third scientific attempt'}


def validate_pull(plan):
    pull = fixed_path(plan['verified_pull_path'])
    receipt = read(pull / 'VERIFIED_PULL.json')
    require(receipt.get('schema') == 'E40_VERIFIED_PULL_V1' and receipt.get('issuer') == 'integrator'
            and receipt.get('experiment') == 'E40' and receipt.get('status') == 'VERIFIED_COMPLETE'
            and receipt.get('request_sha256') == plan['training_request_sha256'], 'verified_integrator_pull_receipt_required')
    require(digest(pull / 'final/OUTPUT_SEAL.json') == receipt.get('output_seal_sha256'), 'unbound_output_seal')
    seal, paths = resolve_artifacts(pull)
    assignment_path = pull / 'final/assignment.json'
    require(digest(assignment_path) == receipt.get('assignment_sha256'), 'unbound_pulled_assignment')
    assignment, gate = read(assignment_path), read(paths['GATE_RESULT.json'])
    require(assignment.get('issuer') == 'integrator' and assignment.get('experiment') == 'E40'
            and assignment.get('stage') == 'training' and type(assignment.get('gpu_count')) is int
            and assignment['gpu_count'] == 1 and assignment.get('source_pushed') is True
            and isinstance(assignment.get('source_commit'), str)
            and re.fullmatch('[0-9a-f]{40}', assignment['source_commit']) is not None
            and assignment.get('pod_id') == receipt.get('pod_id') and bool(assignment.get('pod_id'))
            and assignment.get('request_sha256') == plan['training_request_sha256']
            and sha_string(assignment.get('sources_sha256')), 'invalid_original_training_assignment')
    require(gate.get('experiment') == 'E40' and gate.get('stage') == 'gate'
            and gate.get('request_sha256') == plan['training_request_sha256']
            and gate.get('assignment_sha256') == receipt['assignment_sha256']
            and gate.get('sample_sha256') == SAMPLE_SHA
            and gate.get('decomposition_calls') == 0
            and gate.get('scientific_retry_allowed') is False
            and gate.get('status') == seal.get('status'), 'invalid_gate_lineage')
    status = gate.get('status')
    require(status in ('PASS', 'FAIL', 'NO_FIT', 'INCOMPLETE'), 'unknown_upstream_status')
    if status in ('PASS', 'FAIL'):
        checked = check_scientific_result(gate, paths, assignment, plan)
        checked['verify_pass_executed'] = False
        if checked['verdict'] == 'PASS':
            from followup import verify_pass
            # The original helper expects a flat sealed directory. This cache
            # view preserves every byte and supports the Integrator's split pull.
            parent = ROOT / 'cache/g_agreement/understand/e40'
            with tempfile.TemporaryDirectory(prefix='gate-check-view-', dir=parent) as temporary:
                view = Path(temporary)
                (view / 'OUTPUT_SEAL.json').symlink_to(pull / 'final/OUTPUT_SEAL.json')
                for name, source in paths.items():
                    (view / name).symlink_to(source.resolve())
                admission = verify_pass(view, plan['training_request_sha256'])
            checked['verify_pass_executed'] = True
            checked['verify_pass_admission'] = admission
    else:
        require(gate.get('metrics') is None, 'partial_metric_cannot_be_interpreted')
        require(gate.get('failure_category') == 'OPERATIONAL', 'upstream_validity_stop_wait_for_owner')
        checked = {'verdict': None, 'eligible_for_131_preparation': False, 'verify_pass_executed': False,
                   'next_action': 'Owner review of operational stop; no scientific gate verdict'}
    return dict(checked, upstream_status=status, pod_id=assignment['pod_id'],
                gate_result_sha256=digest(paths['GATE_RESULT.json']),
                output_seal_sha256=receipt['output_seal_sha256'],
                verified_pull_receipt_sha256=digest(pull / 'VERIFIED_PULL.json'))


def run():
    plan = verify_code()
    output, guard = fixed_path(plan['output_path']), fixed_path(plan['guard_path'])
    require(output.is_relative_to(HERE) and guard.parent == HERE, 'wrong_owner_output_or_guard')
    if guard.exists() or output.exists():
        raise FileExistsError('E40 gate check already claimed; owner review required')
    write_new(guard, {'experiment': 'E40', 'analysis': 'gate_check', 'status': 'CLAIMED',
                     'plan_sha256': digest(HERE / PLAN), 'code_seal_sha256': digest(HERE / CODE_SEAL),
                     'execution_label': '§149 RUN-BY-INTEGRATOR',
                     'claimed_at_utc': datetime.now(timezone.utc).isoformat()})
    output.mkdir(parents=True)
    status, error, checked, rc = 'COMPLETE', None, None, 0
    try:
        checked = validate_pull(plan)
    except Exception as exc:
        status, rc = 'VALIDATION_STOP', 2
        error = str(exc) if isinstance(exc, ValidationStop) else type(exc).__name__
    result = {'experiment': 'E40', 'analysis': 'gate_check', 'status': status,
              'execution_label': '§149 RUN-BY-INTEGRATOR', 'authority_commit': plan['authority_commit'],
              'registered_rule_changes': False, 'recomputed_gate_or_training': False,
              'labelling_or_decomposition_started': False,
              'judge_or_blind_coder_calls': 0, 'new_gpu_hours': 0,
              'analysis_plan_sha256': digest(HERE / PLAN), 'validation_error': error, 'gate_check': checked}
    write_new(output / 'GATE_CHECK.json', result)
    report = ['# E40 gate check — §149 RUN-BY-INTEGRATOR', '', 'Status: ' + status + '.', '']
    if checked is not None:
        report += ['Upstream run: ' + checked['upstream_status'] + '.',
                   'Gate verdict: ' + (checked['verdict'] or 'NOT EVALUABLE') + '.', '']
        if checked['verdict'] is not None:
            m = checked['filtered_gate']
            report += [f"Filtered gate: n={m['n_tokens']}, FVU={m['fvu']:.9g}, dead={m['dead_latents']}/65536 ({m['dead_fraction']:.6%}).",
                       f"All-50000-token FVU (descriptive): {checked['all_token_fvu']:.9g}.", '']
        report += [checked['next_action'] + '.', '']
    else:
        report += ['Validation stopped; the run waits for W-sae. Do not rerun or remove the guard.', '']
    (output / 'GATE_CHECK.md').write_text('\n'.join(report))
    write_new(output / 'ANALYSIS_SEAL.json', {'experiment': 'E40', 'analysis': 'gate_check',
        'status': status, 'execution_label': '§149 RUN-BY-INTEGRATOR',
        'files': {n: digest(output / n) for n in ('GATE_CHECK.json', 'GATE_CHECK.md')},
        'once_only_guard_sha256': digest(guard), 'analysis_plan_sha256': digest(HERE / PLAN),
        'code_seal_sha256': digest(HERE / CODE_SEAL), 'completed_gate_checks': int(status == 'COMPLETE')})
    print('E40_GATE_CHECK', status, (checked or {}).get('verdict') or 'NO_VERDICT')
    return rc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        return run()
    except Exception as exc:
        print('E40_GATE_CHECK_STOP', type(exc).__name__)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
