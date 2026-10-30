"""Synthetic §149 command tests; never execute on the actual E40 verified pull."""
import copy
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_check as g

REAL_HERE = Path(__file__).resolve().parent
REAL_ROOT = REAL_HERE.parents[3]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False))


def make_metric(n, fvu=.2, dead=12):
    return {'n_tokens': n, 'd_model': 5120, 'd_sae': 65536,
            'squared_error': 100 * fvu, 'total_variance': 100., 'fvu': fvu,
            'dead_latents': dead, 'dead_fraction': dead / 65536,
            'fvu_pass': fvu <= .25, 'dead_pass': 10 * dead < 65536,
            'passed': fvu <= .25 and 10 * dead < 65536}


@pytest.fixture
def pull(tmp_path, monkeypatch):
    root = tmp_path
    here = root / REAL_HERE.relative_to(REAL_ROOT)
    here.mkdir(parents=True)
    monkeypatch.setattr(g, 'ROOT', root); monkeypatch.setattr(g, 'HERE', here)
    plan = json.loads((REAL_HERE / g.PLAN).read_text())
    request = root / plan['training_request_path']
    request.write_bytes((REAL_ROOT / plan['training_request_path']).read_bytes())
    (here / 'gate_check.py').write_bytes((REAL_HERE / 'gate_check.py').read_bytes())
    dump(here / g.PLAN, plan)
    def code_seal():
        names = [here / 'gate_check.py', here / g.PLAN, request]
        dump(here / g.CODE_SEAL, {'experiment': 'E40', 'status': 'FROZEN',
             'files': {p.relative_to(root).as_posix(): g.digest(p) for p in names}})
    code_seal()
    directory = root / plan['verified_pull_path']
    final, arrays = directory / 'final', directory / 'arrays'
    final.mkdir(parents=True); arrays.mkdir()
    assignment = {'issuer': 'integrator', 'experiment': 'E40', 'stage': 'training',
        'gpu_count': 1, 'source_pushed': True, 'source_commit': 'b' * 40,
        'pod_id': 'synthetic-pod', 'request_sha256': plan['training_request_sha256'],
        'sources_sha256': 'c' * 64}
    dump(final / 'assignment.json', assignment)
    (arrays / 'layer44.e40.sae.pt').write_bytes(b'synthetic weights; checksum only, never loaded')
    (arrays / 'capture_ledger.jsonl').write_text('{}\n')
    calibration = {'experiment': 'E40', 'population_tokens': 1000000,
        'd_model': 5120, 'position_zero_included': False, 'heldout_statistics_used': False,
        'single_capture_pass': True, 'source_manifest_sha256': assignment['sources_sha256'],
        'median_raw_norm': 2., 'outlier_threshold_raw_norm': 20.,
        'mean_raw_norm_after_outlier_exclusion': 2., 'scale': math.sqrt(5120) / 2,
        'calibration_retained': 999900, 'calibration_outliers': 100}
    dump(final / 'CALIBRATION.json', calibration)
    calibration_sha = g.digest(final / 'CALIBRATION.json')
    checkpoint_sha = g.digest(arrays / 'layer44.e40.sae.pt')
    dump(final / 'CALIBRATION_SEAL.json', {'status': 'COMPLETE', 'before_training_step': 1,
          'files': {'CALIBRATION.json': calibration_sha}})
    training = {'experiment': 'E40', 'status': 'COMPLETE', 'synthetic': False,
        'training_tokens': 100000000, 'optimizer_updates': 24415,
        'config': plan['training_configuration'], 'data_passes': 1,
        'recaptured_training_occurrences': 0, 'checkpoint_selection': 'final_only',
        'sae_checkpoint_sha256': checkpoint_sha, 'calibration_sha256': calibration_sha,
        'sources_sha256': assignment['sources_sha256'], 'normalization': {'scale': calibration['scale']}}
    dump(final / 'TRAINING_RESULT.json', training)
    zero = plan['expected_position_zero_tokens']
    filtered, all_tokens = make_metric(50000 - zero), make_metric(50000, fvu=.9)
    all_tokens['rule_applied'] = False
    gate = {'experiment': 'E40', 'stage': 'gate', 'status': 'PASS',
        'request_sha256': plan['training_request_sha256'],
        'assignment_sha256': g.digest(final / 'assignment.json'), 'sample_sha256': g.SAMPLE_SHA,
        'decomposition_calls': 0, 'scientific_retry_allowed': False,
        'sae_checkpoint_sha256': checkpoint_sha, 'calibration_sha256': calibration_sha,
        'scale': calibration['scale'], 'primary_gate': 'filtered', 'all_token_fvu_descriptive': True,
        'sae_k': 128, 'error_type': None, 'failure_category': None,
        'metrics': {'filtered': filtered, 'all_tokens': all_tokens,
           'excluded': {'position_zero': zero, 'norm_above_threshold': 4, 'overlap': 4, 'union': zero}}}
    dump(final / 'GATE_RESULT.json', gate)
    dump(final / 'GATE.RUN_ONCE.json', {'checkpoint_sha256': checkpoint_sha,
          'calibration_sha256': calibration_sha, 'sample_sha256': g.SAMPLE_SHA})
    for name in ('CLOCK.json', 'RUNTIME.json', 'PILOT.json'):
        dump(final / name, {})
    def reseal():
        gg = g.read(final / 'GATE_RESULT.json')
        files = {p.name: g.digest(p) for folder in (final, arrays) for p in folder.iterdir()
                 if p.name not in ('OUTPUT_SEAL.json', 'assignment.json')}
        dump(final / 'OUTPUT_SEAL.json', {'status': gg['status'], 'files': files})
        dump(directory / 'VERIFIED_PULL.json', {'schema': 'E40_VERIFIED_PULL_V1',
            'issuer': 'integrator', 'experiment': 'E40', 'status': 'VERIFIED_COMPLETE',
            'pod_id': assignment['pod_id'], 'request_sha256': plan['training_request_sha256'],
            'assignment_sha256': g.digest(final / 'assignment.json'),
            'output_seal_sha256': g.digest(final / 'OUTPUT_SEAL.json')})
    reseal()
    return SimpleNamespace(root=root, here=here, plan=plan, directory=directory,
        final=final, arrays=arrays, gate=gate, training=training,
        calibration=calibration, reseal=reseal, code_seal=code_seal)


def test_pass_calls_actual_verify_pass_once_but_never_starts_labels(pull, monkeypatch):
    import followup
    calls = []
    real = followup.verify_pass
    def spy(*args):
        calls.append(args[0]); return real(*args)
    monkeypatch.setattr(followup, 'verify_pass', spy)
    assert g.run() == 0
    result = g.read(pull.root / pull.plan['output_path'] / 'GATE_CHECK.json')
    assert result['gate_check']['verdict'] == 'PASS'
    assert result['gate_check']['verify_pass_executed'] is True and len(calls) == 1
    assert result['gate_check']['all_token_fvu'] == .9
    assert result['labelling_or_decomposition_started'] is False
    assert result['judge_or_blind_coder_calls'] == 0
    assert not calls[0].exists()  # cache-only temporary input view removed
    assert not result['recomputed_gate_or_training']


@pytest.mark.parametrize('fvu,dead', [(.3, 12), (.2, 6554)])
def test_valid_fail_is_reported_without_calling_pass_or_retry(pull, monkeypatch, fvu, dead):
    import followup
    monkeypatch.setattr(followup, 'verify_pass', lambda *_: pytest.fail('FAIL called verify_pass'))
    gate = g.read(pull.final / 'GATE_RESULT.json')
    gate['metrics']['filtered'] = make_metric(gate['metrics']['filtered']['n_tokens'], fvu, dead)
    gate['status'] = 'FAIL'; dump(pull.final / 'GATE_RESULT.json', gate); pull.reseal()
    assert g.run() == 0
    checked = g.read(pull.root / pull.plan['output_path'] / 'GATE_CHECK.json')['gate_check']
    assert checked['verdict'] == 'FAIL' and checked['verify_pass_executed'] is False
    assert checked['eligible_for_131_preparation'] is False


def test_original_inclusive_fvu_and_strict_dead_boundaries(pull):
    gate = g.read(pull.final / 'GATE_RESULT.json')
    gate['metrics']['filtered'] = make_metric(gate['metrics']['filtered']['n_tokens'], .25, 6553)
    dump(pull.final / 'GATE_RESULT.json', gate); pull.reseal()
    assert g.validate_pull(pull.plan)['verdict'] == 'PASS'


def test_global_guard_and_existing_outputs_are_never_overwritten(pull):
    assert g.run() == 0
    output = pull.root / pull.plan['output_path']
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    guard = pull.root / pull.plan['guard_path']; guard_before = guard.read_bytes()
    with pytest.raises(FileExistsError): g.run()
    assert guard.read_bytes() == guard_before
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    seal = g.read(output / 'ANALYSIS_SEAL.json')
    assert all(g.digest(output / n) == h for n, h in seal['files'].items())
    assert seal['once_only_guard_sha256'] == g.digest(guard)


def test_validation_failure_consumes_guard_seals_stop_and_waits(pull):
    (pull.arrays / 'layer44.e40.sae.pt').write_bytes(b'corrupt')
    assert g.run() == 2
    output = pull.root / pull.plan['output_path']
    record = g.read(output / 'GATE_CHECK.json')
    assert record['status'] == 'VALIDATION_STOP' and record['gate_check'] is None
    assert record['validation_error'] == 'pulled_artifact_checksum_mismatch'
    with pytest.raises(FileExistsError): g.run()


@pytest.mark.parametrize('kind', ['missing_weight', 'bad_duplicate', 'wrong_receipt', 'wrong_pod', 'wrong_request'])
def test_verified_pull_identity_and_completeness(pull, kind):
    if kind == 'missing_weight':
        (pull.arrays / 'layer44.e40.sae.pt').unlink()
    elif kind == 'bad_duplicate':
        (pull.final / 'layer44.e40.sae.pt').write_bytes(b'wrong')
    else:
        path = pull.directory / 'VERIFIED_PULL.json'; x = g.read(path)
        if kind == 'wrong_receipt': x['status'] = 'UNVERIFIED_TEMPLATE'
        if kind == 'wrong_pod': x['pod_id'] = 'another'
        if kind == 'wrong_request': x['request_sha256'] = 'd' * 64
        dump(path, x)
    with pytest.raises(g.ValidationStop): g.validate_pull(pull.plan)


@pytest.mark.parametrize('target,key,value', [
    ('TRAINING_RESULT.json','training_tokens',99999999),
    ('TRAINING_RESULT.json','optimizer_updates',24414),
    ('TRAINING_RESULT.json','synthetic',True),
    ('TRAINING_RESULT.json','data_passes',2),
    ('TRAINING_RESULT.json','recaptured_training_occurrences',1),
    ('TRAINING_RESULT.json','checkpoint_selection','best_on_gate'),
    ('CALIBRATION_SEAL.json','before_training_step',2),
    ('CALIBRATION_SEAL.json','before_training_step',True),
    ('CALIBRATION.json','population_tokens',999999),
    ('CALIBRATION.json','heldout_statistics_used',True),
    ('CALIBRATION.json','position_zero_included',True),
    ('CALIBRATION.json','single_capture_pass',False),
    ('GATE_RESULT.json','primary_gate','all_tokens'),
    ('GATE_RESULT.json','scale',1.),
])
def test_resealed_semantic_mismatch_cannot_authorize_science(pull,target,key,value):
    x = g.read(pull.final / target); x[key] = value
    dump(pull.final / target, x); pull.reseal()
    with pytest.raises(g.ValidationStop): g.validate_pull(pull.plan)


def test_inconsistent_threshold_flags_or_exclusion_counts_stop(pull):
    gate = g.read(pull.final / 'GATE_RESULT.json')
    gate['metrics']['filtered']['fvu_pass'] = False
    dump(pull.final / 'GATE_RESULT.json', gate); pull.reseal()
    with pytest.raises(g.ValidationStop): g.validate_pull(pull.plan)
    gate['metrics']['filtered']['fvu_pass'] = True
    gate['metrics']['excluded']['union'] += 1
    dump(pull.final / 'GATE_RESULT.json', gate); pull.reseal()
    with pytest.raises(g.ValidationStop): g.validate_pull(pull.plan)


@pytest.mark.parametrize('status', ['NO_FIT','INCOMPLETE'])
def test_valid_operational_stop_has_no_scientific_verdict(pull,status):
    gate = g.read(pull.final / 'GATE_RESULT.json')
    gate.update(status=status,metrics=None,error_type='NoFit',failure_category='OPERATIONAL')
    dump(pull.final / 'GATE_RESULT.json', gate); pull.reseal()
    assert g.run() == 0
    r = g.read(pull.root / pull.plan['output_path'] / 'GATE_CHECK.json')['gate_check']
    assert r['verdict'] is None and r['verify_pass_executed'] is False


def test_upstream_validity_stop_waits_for_owner(pull):
    gate = g.read(pull.final / 'GATE_RESULT.json')
    gate.update(status='INCOMPLETE',metrics=None,error_type='ValueError',failure_category='VALIDITY_NO_RETRY')
    dump(pull.final / 'GATE_RESULT.json', gate); pull.reseal()
    assert g.run() == 2


def test_code_seal_mismatch_stops_before_input_or_guard(pull):
    (pull.here / 'gate_check.py').write_text('changed source')
    with pytest.raises(g.ValidationStop): g.run()
    assert not (pull.root / pull.plan['guard_path']).exists()


def test_output_seal_cannot_reference_parent_files(pull):
    seal = g.read(pull.final / 'OUTPUT_SEAL.json')
    seal['files']['../assignment.json'] = g.digest(pull.final / 'assignment.json')
    dump(pull.final / 'OUTPUT_SEAL.json', seal)
    receipt = g.read(pull.directory / 'VERIFIED_PULL.json')
    receipt['output_seal_sha256'] = g.digest(pull.final / 'OUTPUT_SEAL.json')
    dump(pull.directory / 'VERIFIED_PULL.json', receipt)
    with pytest.raises(g.ValidationStop): g.validate_pull(pull.plan)


def test_nonfinite_json_constants_are_rejected(tmp_path):
    path = tmp_path / 'bad.json'; path.write_text('{"value":NaN}')
    with pytest.raises(g.ValidationStop): g.read(path)


def test_input_paths_support_a_shared_cache_symlink(pull,tmp_path,monkeypatch):
    root = tmp_path / 'other-root'; root.mkdir()
    shared = tmp_path / 'shared-cache'; shared.mkdir()
    (root / 'cache').symlink_to(shared,target_is_directory=True)
    monkeypatch.setattr(g,'ROOT',root)
    path = g.fixed_path('cache/g_agreement/understand/e40/test')
    assert path == shared / 'g_agreement/understand/e40/test'
    with pytest.raises(g.ValidationStop): g.fixed_path('../private')
