"""Deterministic tests for uninterrupted packed experiment clocks."""
from datetime import datetime, timedelta, timezone
import json
import signal
import time

import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand import packed_budget as B


class Clock:
    def __init__(self):
        self.mono = 100.
        self.wall = time.time()
        self.timers = []

    def advance(self, seconds):
        self.mono += seconds
        self.wall += seconds


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(B.time, 'monotonic', lambda: clock.mono)
    monkeypatch.setattr(B.time, 'time', lambda: clock.wall)
    monkeypatch.setattr(B.signal, 'getsignal', lambda _: signal.SIG_DFL)
    monkeypatch.setattr(B.signal, 'signal', lambda *args: None)
    monkeypatch.setattr(B.signal, 'setitimer', lambda kind, seconds: clock.timers.append(seconds))
    return clock


def make_budget(tmp_path, monkeypatch, **changes):
    sources = {'packed.py': '0'*64}
    seals = {'E3': {'primary': '1'*64}, 'E4': {'primary': '2'*64, 'e9': '3'*64}}
    monkeypatch.setattr(B, 'source_hashes', lambda: sources)
    assignment = {'experiment': 'E3_E4_PACK', 'sequence': ['E3', 'E4'],
                  'gpu_count': 1, 'pod_id': 'integrator-pod',
                  'external_hard_stop_verified': True,
                  'max_science_seconds': {'E3': 2160., 'E4': 2160.},
                  'setup_allowance_seconds': 1500., 'source_files': sources,
                  'input_seals': seals,
                  'hard_deadline_utc': (datetime.now(timezone.utc)+timedelta(hours=3)).isoformat()}
    assignment.update(changes)
    path = tmp_path/'assignment.json'
    P.dump(path, assignment)
    return B.PackedBudget(path, tmp_path/'budget', seals)


def receipts(experiment, unit_time=1., units=100):
    return {phase: {'warmups': 1, 'timings_seconds': [unit_time, unit_time, unit_time],
                    'units': units, 'forecast_seconds': unit_time*units}
            for phase in B.PHASES[experiment]}


@pytest.mark.parametrize('change', [
    {'experiment': 'E3'}, {'sequence': ['E4', 'E3']}, {'gpu_count': 2},
    {'max_science_seconds': {'E3': 2161, 'E4': 2160}},
    {'setup_allowance_seconds': 1501}, {'external_hard_stop_verified': False},
    {'source_files': {'packed.py': '4'*64}}, {'input_seals': {'E3': {'primary': '1'*64}}},
])
def test_packed_assignment_rejects_mismatch(tmp_path, monkeypatch, clock, change):
    with pytest.raises(ValueError, match='assignment'):
        make_budget(tmp_path, monkeypatch, **change)


def test_one_shared_setup_allowance_and_no_late_setup(tmp_path, monkeypatch, clock):
    budget = make_budget(tmp_path, monkeypatch)
    try:
        with budget.setup():
            clock.advance(200)
        with budget.setup():
            clock.advance(300)
        assert budget.state['setup_seconds'] == 500
        budget.start('E3')
        with pytest.raises(ValueError, match='before the first'):
            with budget.setup():
                pass
        assert budget.elapsed() == 0
    finally:
        budget.close()


def test_setup_exception_still_charged_and_cap_stops_science(tmp_path, monkeypatch, clock):
    budget = make_budget(tmp_path, monkeypatch)
    try:
        with pytest.raises(RuntimeError):
            with budget.setup():
                clock.advance(1501)
                raise RuntimeError('loader failed')
        assert budget.state['setup_seconds'] == 1501
        assert budget.state['setup_budget_status'] == 'CAP_EXCEEDED'
        with pytest.raises(TimeoutError, match='setup allowance'):
            budget.start('E3')
    finally:
        budget.close()


def test_science_clock_never_resets_at_gate_and_includes_transfers(tmp_path, monkeypatch, clock):
    budget = make_budget(tmp_path, monkeypatch)
    try:
        budget.start('E3')
        assert clock.timers[-1] == 2160
        clock.advance(80)  # warming, calibration, swaps and disk writes
        gate = budget.gate('E3', receipts('E3'), remaining_transition_seconds=40)
        assert gate['forecast_seconds'] == 340
        assert gate['science_cap_seconds'] == 870
        assert gate['science_consumed_seconds'] == 80
        assert clock.timers[-1] == 790  # cap minus original elapsed, not a fresh cap
        clock.advance(100)  # production and seal latency
        record = budget.finish('E3', 'COMPLETE', sealed=True)
        assert record['science_seconds'] == 180
        assert record['budget_status'] == 'WITHIN_CAP'
        assert budget.state['active'] is None
        budget.start('E4')
        assert budget.elapsed() == 0
        assert clock.timers[-1] == 2160
        clock.advance(30)
        budget.gate('E4', receipts('E4'))
        clock.advance(5)
        budget.finish('E4', 'COMPLETE', sealed=True)
        assert budget.state['experiments']['E3']['science_seconds'] == 180
        assert budget.state['experiments']['E4']['science_seconds'] == 35
    finally:
        budget.close()


def test_e4_waits_for_e3_complete_or_partial_seal(tmp_path, monkeypatch, clock):
    budget = make_budget(tmp_path, monkeypatch)
    try:
        with pytest.raises(ValueError, match='E3 must be sealed'):
            budget.start('E4')
        budget.start('E3')
        with pytest.raises(ValueError):
            budget.start('E4')
        budget.stop('E3', 'capture failed')
        with pytest.raises(ValueError):
            budget.finish('E3', 'PARTIAL')
        with pytest.raises(ValueError):
            budget.start('E4')
        budget.mark_sealed('E3', partial=True)
        budget.start('E4')
        assert budget.state['active'] == 'E4'
    finally:
        budget.close()


def test_failed_science_cpu_partial_seal_remains_on_original_clock(tmp_path, monkeypatch, clock):
    budget = make_budget(tmp_path, monkeypatch)
    try:
        budget.start('E3')
        clock.advance(2161)
        with pytest.raises(TimeoutError):
            budget.checkpoint()
        budget.stop('E3', 'cap expired')
        with pytest.raises(RuntimeError, match='no GPU resumption'):
            budget.checkpoint()
        clock.advance(7)
        record = budget.mark_sealed('E3', partial=True)
        assert record['science_seconds'] == 2168
        assert record['science_seconds_at_gpu_stop'] == 2161
        assert record['post_stop_cpu_sealing_seconds'] == 7
        assert record['cap_overrun_seconds'] == 8
        assert record['budget_status'] == 'CAP_EXCEEDED'
        assert record['status'] == 'PARTIAL'
        with pytest.raises(ValueError, match='already attempted'):
            budget.start('E3')
    finally:
        budget.close()


def test_warmed_no_go_disables_gpu_without_hiding_cpu_seal_elapsed(tmp_path, monkeypatch, clock):
    budget = make_budget(tmp_path, monkeypatch)
    try:
        budget.start('E3')
        clock.advance(200)
        with pytest.raises(RuntimeError, match='NO-GO'):
            budget.gate('E3', receipts('E3', units=700))
        record = budget.state['experiments']['E3']
        assert record['science_cap_seconds'] == 2160
        assert record['gate']['admitted'] is False
        assert record['gpu_stopped'] is True
        clock.advance(2)
        record = budget.mark_sealed('E3')
        assert record['science_seconds'] == 202
    finally:
        budget.close()


def test_gate_requires_all_phases_is_once_only_and_rejects_bad_transfer_forecast(tmp_path, monkeypatch, clock):
    budget = make_budget(tmp_path, monkeypatch)
    try:
        budget.start('E3')
        with pytest.raises(ValueError, match='all reader/target'):
            budget.gate('E3', {'olens': receipts('E3')['olens']})
        with pytest.raises(ValueError, match='finite and nonnegative'):
            budget.gate('E3', receipts('E3'), remaining_transition_seconds=-1)
        budget.gate('E3', receipts('E3'))
        with pytest.raises(ValueError, match='already evaluated'):
            budget.gate('E3', receipts('E3'))
    finally:
        budget.close()


def test_provider_hard_deadline_can_be_tighter_than_science_cap(tmp_path, monkeypatch, clock):
    deadline = datetime.fromtimestamp(clock.wall+50, timezone.utc).isoformat()
    budget = make_budget(tmp_path, monkeypatch, hard_deadline_utc=deadline)
    try:
        budget.start('E3')
        assert clock.timers[-1] == pytest.approx(50, abs=1e-6)
        clock.advance(51)
        with pytest.raises(TimeoutError):
            budget.checkpoint()
    finally:
        budget.close()


def test_interrupted_or_completed_pack_cannot_be_reopened(tmp_path, monkeypatch, clock):
    budget = make_budget(tmp_path, monkeypatch)
    budget.start('E3'); clock.advance(4); budget.close()
    saved = json.loads((tmp_path/'budget/packed_budget.json').read_text())
    assert saved['experiments']['E3']['status'] == 'INTERRUPTED_UNSEALED'
    assert saved['experiments']['E3']['science_seconds_on_close'] == 4
    seals = budget.assignment['input_seals']
    with pytest.raises(ValueError, match='already attempted'):
        B.PackedBudget(tmp_path/'assignment.json', tmp_path/'budget', seals)


def test_e4_only_retry_has_own_continuous_clock_without_e3(tmp_path,monkeypatch,clock):
    sources={'packed.py':'0'*64}
    seals={'E4':{'primary':'2'*64,'e9':'3'*64}}
    monkeypatch.setattr(B,'source_hashes',lambda:sources)
    assignment={'experiment':'E4_ONLY_RETRY','sequence':['E4'],'gpu_count':1,'pod_id':'retry-pod',
                'external_hard_stop_verified':True,'max_science_seconds':{'E4':2160},
                'setup_allowance_seconds':1500,'source_files':sources,'input_seals':seals,
                'hard_deadline_utc':(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()}
    path=tmp_path/'assignment.json';P.dump(path,assignment)
    budget=B.E4OnlyBudget(path,tmp_path/'retry',seals)
    with budget.setup():clock.advance(100)
    with pytest.raises(ValueError):budget.start('E3')
    budget.start('E4');clock.advance(23.7)
    gate=budget.gate('E4',receipts('E4',unit_time=.1,units=100))
    assert gate['science_consumed_seconds']==pytest.approx(23.7)
    assert gate['science_cap_seconds']==420
    clock.advance(10)
    final=budget.finish('E4','COMPLETE',sealed=True)
    assert final['science_seconds']==pytest.approx(33.7)
    assert set(budget.state['experiments'])=={'E4'}
    with pytest.raises(ValueError,match='already attempted'):budget.start('E4')
    budget.close()
