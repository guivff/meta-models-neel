import signal
from decimal import Decimal
import pytest
from .priority_lock_safe import park,recover_locked_pauses


def w():return dict(pid=9,bank='E118',module='own',phase_directory='ownphase',loaded_cutoff_epoch=100)


def test_stopped_flock_waiter_is_resumed_before_caller_releases_global_lock():
    state=dict(waiting=[dict(pid=9,bank='E118',ticket='own'),dict(pid=8,bank='foreign',ticket='other')]);signals=[]
    out=park(state,{'own':w()},lambda p:(Decimal(0),Decimal(0)),lambda *x:signals.append(x),lambda p:True)
    assert out=={} and signals==[(9,signal.SIGSTOP),(9,signal.SIGCONT)] and len(state['waiting'])==2


def test_only_unreserved_worker_without_pacing_fd_remains_parked():
    state=dict(waiting=[dict(pid=9,bank='E118',ticket='own'),dict(pid=8,bank='foreign',ticket='other')]);signals=[]
    out=park(state,{'own':w()},lambda p:(Decimal(0),Decimal(0)),lambda *x:signals.append(x),lambda p:False)
    assert set(out)=={'own'} and signals==[(9,signal.SIGSTOP)] and state['waiting']==[dict(pid=8,bank='foreign',ticket='other')]


def test_unknown_or_inflight_charge_is_never_stopped():
    state=dict(waiting=[dict(pid=9,bank='E118',ticket='own')]);signals=[]
    assert park(state,{'own':w()},lambda p:(Decimal(0),Decimal(1)),lambda *x:signals.append(x),lambda p:False)=={}
    assert signals==[] and len(state['waiting'])==1


def test_fd_probe_error_resumes_before_lock_release():
    def bad(p):raise RuntimeError('inspection unavailable')
    signals=[]
    with pytest.raises(RuntimeError):park(dict(waiting=[dict(pid=9,bank='E118',ticket='own')]),{'own':w()},lambda p:(Decimal(0),Decimal(0)),lambda *x:signals.append(x),bad)
    assert signals==[(9,signal.SIGSTOP),(9,signal.SIGCONT)]


@pytest.mark.parametrize('fault',['foreign','unknown','expired','402'])
def test_startup_recovery_requires_existing_own_known_zero_and_live_authority(fault):
    signals=[];paused={'own':w()}
    with pytest.raises(ValueError):recover_locked_pauses(paused,lambda *x:fault!='foreign',lambda p:(Decimal(0),Decimal(1 if fault=='unknown' else 0)),lambda *x:signals.append(x),lambda p:True,101 if fault=='expired'else 1,fault=='402')
    assert signals==[] and 'own'in paused


def test_only_prior_paused_own_lock_waiter_is_recovered_same_process():
    signals=[];paused={'own':w()}
    assert recover_locked_pauses(paused,lambda *x:True,lambda p:(Decimal('.2'),Decimal(0)),lambda *x:signals.append(x),lambda p:True,1,False)==['own']
    assert paused=={} and signals==[(9,signal.SIGCONT)]


def test_existing_primary_is_preserved_even_if_already_inflight_when_controller_recovers():
    from .priority_lock_safe import restored_known
    plan=dict(ordered_existing_phases=[dict(name='main',bank='E117',module='module',phase_directory='main'),dict(name='lower',bank='E118')])
    state=dict(active={'main':dict(bank='E117',pid=22),'lower':dict(bank='E118',pid=23)})
    out=restored_known(plan,state);assert out['main']['pid']==22 and out['main']['phase_directory']=='main'
    state['active']['main']['bank']='foreign'
    with pytest.raises(ValueError):restored_known(plan,state)


def test_cli_passes_the_exact_original_plan_restore_and_refresh_paths(monkeypatch):
    from pathlib import Path
    from . import priority_lock_safe as module
    calls=[];monkeypatch.setattr(module,'run',lambda *a:calls.append(a))
    module.main(['--plan','original/PLAN.json','--restore-status','new/ORIGINAL_STATUS.json','--dispatch-refresh','new/ADMISSION.json'])
    assert calls==[(Path('original/PLAN.json'),Path('new/ORIGINAL_STATUS.json'),Path('new/ADMISSION.json'))]
