"""Synthetic CPU timing/accounting tests only; no GPU or experiment inputs."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('e35_training_clock_under_test', HERE / 'training_clock.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)
REQUEST_SHA = 'a' * 64


@pytest.fixture
def environment(monkeypatch):
    elapsed = {'now': 1000.}
    monkeypatch.setattr(P, 'time', SimpleNamespace(time=lambda: elapsed['now']))
    monkeypatch.setenv('RUNPOD_POD_ID', 'synthetic-pod')
    return elapsed


def assignment():
    return {
        'issuer': 'integrator', 'experiment': 'E35', 'stage': 'training',
        'gpu_count': 1, 'pod_id': 'synthetic-pod', 'request_sha256': REQUEST_SHA,
        'source_commit': 'b' * 40, 'source_pushed': True,
        'external_hardstop_verified': True, 'hold_renewer_verified': True,
        'provider_created_epoch': 1000., 'setup_deadline_epoch': 2500.,
        'deadline_epoch': 11800., 'allocated_gpu_seconds': 10800.,
        'previous_gpu_seconds': 1034.2, 'later_reserved_gpu_seconds': 3600.,
        'prior_accounting': {'attempt1_gpu_seconds': 434.2, 'rerun_gpu_seconds': 600.,
                             'rerun_mode': 'provider_actual', 'receipt_sha256': 'c' * 64},
    }


def piloted(environment, *, capture=.1, train=.05, gate=.15):
    clock = P.TrainingClock(assignment(), REQUEST_SHA)
    clock.begin_science()
    for kind, duration in [('capture512', capture), ('train4096', train), ('gate512', gate)]:
        for factor in (1., 1.1, .9):
            dt = duration * factor
            environment['now'] += dt
            clock.record_pilot(kind, dt)
    return clock


def test_admission_counts_every_short_chunk_update_and_gate(environment):
    clock = piloted(environment)
    clock.admit(42000)
    report = clock.record()
    components = report['forecast_components']
    assert report['status'] == 'RUNNING'
    assert components['training_capture_seconds'] == pytest.approx(4200.)
    assert components['optimizer_seconds'] == pytest.approx(4883 * .05)
    assert components['gate_seconds'] == pytest.approx(487 * .15)
    assert components['pilot_elapsed_seconds'] == pytest.approx(.9)
    assert report['forecast_seconds'] == pytest.approx(.9 + 4200 + 4883 * .05 + 487 * .15)
    assert report['science_cap_seconds'] == pytest.approx(1.5 * report['forecast_seconds'] + 360)
    assert report['training_tokens'] == 20_000_000
    assert report['science_clock_resets'] == 0


def test_valid_conservative_accounting_books_entire_rerun_allocation(environment):
    a = assignment()
    a['prior_accounting'].update(rerun_mode='conservative_allocation', rerun_gpu_seconds=3600.)
    a['previous_gpu_seconds'] = 4034.2
    clock = P.TrainingClock(a, REQUEST_SHA)
    assert clock.record()['previous_gpu_seconds'] == 4034.2


def test_known_worker_elapsed_is_only_a_floor(environment):
    a = assignment()
    a['prior_accounting']['rerun_gpu_seconds'] = P.RERUN_WORKER_MIN_SECONDS
    a['previous_gpu_seconds'] = P.KNOWN_PRIOR_MIN_SECONDS
    P.TrainingClock(a, REQUEST_SHA)
    a['previous_gpu_seconds'] -= 1e-6
    with pytest.raises(ValueError):
        P.TrainingClock(a, REQUEST_SHA)


@pytest.mark.parametrize('field,value', [
    ('issuer', 'worker'), ('experiment', 'E36'), ('stage', 'gate'),
    ('gpu_count', 2), ('gpu_count', True), ('pod_id', 'another-pod'),
    ('request_sha256', 'd' * 64), ('source_commit', 'b' * 39),
    ('source_pushed', False), ('external_hardstop_verified', 1), ('hold_renewer_verified', False),
    ('allocated_gpu_seconds', 10801.), ('allocated_gpu_seconds', 180.),
    ('later_reserved_gpu_seconds', 3599.999), ('later_reserved_gpu_seconds', 10000.),
    ('previous_gpu_seconds', float('nan')), ('allocated_gpu_seconds', float('inf')),
    ('later_reserved_gpu_seconds', True), ('provider_created_epoch', 1001.),
    ('setup_deadline_epoch', 2500.001), ('setup_deadline_epoch', 1000.),
    ('deadline_epoch', 11800.001), ('deadline_epoch', 2500.),
])
def test_assignment_failures_rejected(environment, field, value):
    a = assignment()
    a[field] = value
    with pytest.raises(ValueError):
        P.TrainingClock(a, REQUEST_SHA)


@pytest.mark.parametrize('field,value', [
    ('attempt1_gpu_seconds', 434.199), ('rerun_gpu_seconds', 538.),
    ('rerun_mode', 'worker_elapsed'), ('receipt_sha256', None),
    ('attempt1_gpu_seconds', True), ('rerun_gpu_seconds', float('inf')),
])
def test_invalid_prior_receipt_fields_rejected(environment, field, value):
    a = assignment()
    a['prior_accounting'][field] = value
    with pytest.raises(ValueError):
        P.TrainingClock(a, REQUEST_SHA)


def test_conservative_mode_cannot_book_only_worker_elapsed(environment):
    a = assignment()
    a['prior_accounting']['rerun_mode'] = 'conservative_allocation'
    with pytest.raises(ValueError, match='full rerun allocation'):
        P.TrainingClock(a, REQUEST_SHA)


def test_total_prior_field_cannot_understate_individually_booked_charges(environment):
    a = assignment()
    a['previous_gpu_seconds'] = P.KNOWN_PRIOR_MIN_SECONDS
    with pytest.raises(ValueError, match='understates'):
        P.TrainingClock(a, REQUEST_SHA)


def test_setup_and_programme_deadlines_include_provider_time(environment):
    clock = P.TrainingClock(assignment(), REQUEST_SHA)
    environment['now'] = 2500.
    with pytest.raises(P.NoFit):
        clock.check()
    a = assignment()
    a['provider_created_epoch'] = P.STOP - 1000
    a['setup_deadline_epoch'] = P.STOP - 1
    a['deadline_epoch'] = P.STOP + 1
    environment['now'] = P.STOP - 1000
    with pytest.raises(ValueError):
        P.TrainingClock(a, REQUEST_SHA)


def test_caller_assignment_mutation_cannot_extend_validated_deadline(environment):
    a = assignment()
    clock = P.TrainingClock(a, REQUEST_SHA)
    a['setup_deadline_epoch'] += 10000
    a['prior_accounting']['rerun_gpu_seconds'] = 0
    assert clock.a['prior_accounting']['rerun_gpu_seconds'] == 600
    environment['now'] = 2500
    with pytest.raises(P.NoFit):
        clock.check()


def test_no_science_reset_or_second_admission(environment):
    clock = piloted(environment)
    start = clock.science_start
    with pytest.raises(ValueError, match='cannot reset'):
        clock.begin_science()
    clock.admit(39063)
    with pytest.raises(ValueError):
        clock.admit(39063)
    with pytest.raises(ValueError):
        clock.record_pilot('capture512', .1)
    assert clock.science_start == start


@pytest.mark.parametrize('duration', [0, -1, True, float('nan'), float('inf')])
def test_invalid_pilot_timings(environment, duration):
    clock = P.TrainingClock(assignment(), REQUEST_SHA)
    clock.begin_science()
    with pytest.raises(ValueError):
        clock.record_pilot('capture512', duration)


def test_all_three_kinds_need_exactly_three_warmed_observations(environment):
    clock = P.TrainingClock(assignment(), REQUEST_SHA)
    with pytest.raises(ValueError):
        clock.record_pilot('capture512', .1)
    clock.begin_science()
    with pytest.raises(ValueError):
        clock.admit(39063)
    for _ in range(3):
        clock.record_pilot('capture512', .1)
    with pytest.raises(ValueError):
        clock.record_pilot('capture512', .1)
    with pytest.raises(ValueError):
        clock.record_pilot('unregistered-kind', .1)
    with pytest.raises(ValueError):
        clock.admit(39063)


@pytest.mark.parametrize('chunks,steps,gate_docs', [
    (39062, 4883, 487), (39063., 4883, 487), (20_000_001, 4883, 487),
    (39063, 4882, 487), (39063, 4883., 487), (39063, 4883, 486),
    (39063, 4883, 487.),
])
def test_scope_cannot_be_reduced_to_fit(environment, chunks, steps, gate_docs):
    clock = piloted(environment)
    with pytest.raises(ValueError):
        clock.admit(chunks, steps, gate_docs)


def test_no_fit_is_terminal_and_does_not_change_scope(environment):
    clock = piloted(environment, capture=1., train=.5, gate=1.)
    with pytest.raises(P.NoFit):
        clock.admit(39063)
    assert clock.status == 'NO_FIT'
    assert clock.forecast_components['training_tokens'] == 20_000_000
    assert clock.forecast_components['gate_documents'] == 487
    with pytest.raises(P.NoFit):
        clock.check()
    with pytest.raises(P.NoFit):
        clock.admit(39063)


def test_training_and_gate_share_the_same_science_cap(environment):
    clock = piloted(environment)
    clock.admit(39063)
    environment['now'] = clock.science_start + clock.science_limit
    with pytest.raises(P.NoFit):
        clock.check()


def test_pilots_cannot_consume_retrieval_reserve(environment):
    clock = P.TrainingClock(assignment(), REQUEST_SHA)
    clock.begin_science()
    environment['now'] = clock.a['deadline_epoch'] - 180
    with pytest.raises(P.NoFit):
        clock.record_pilot('capture512', .1)


def test_record_returns_independent_pilot_and_accounting_snapshots(environment):
    clock = piloted(environment)
    snapshot = clock.record()
    snapshot['pilot_seconds']['capture512'].clear()
    snapshot['prior_accounting']['rerun_gpu_seconds'] = 0
    assert len(clock.pilot_seconds['capture512']) == 3
    assert clock.a['prior_accounting']['rerun_gpu_seconds'] == 600
