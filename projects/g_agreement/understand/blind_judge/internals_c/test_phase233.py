from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
import pytest
from . import phase233 as phase, accounting234 as accounting
from projects.g_agreement.readerbench.io import write


def test_new_E123_only_concrete_open_residual_once(tmp_path, monkeypatch):
    monkeypatch.setattr(accounting, 'SHARED', tmp_path)
    monkeypatch.setattr(accounting, 'bank_actual', lambda root: (Decimal('.4'), Decimal('.1')))
    base = dict(open_banks={}, open_caps_remaining_usd='0', actual_plus_open_caps_usd='.5')
    assert accounting.add_open_234(deepcopy(base)) == dict(base, warning_triggered=False)
    root = tmp_path/'E123'; root.mkdir()
    a = dict(bank='E123', operator='W-internals-C', allocation_usd=3, reservation_included=True, status='OPEN')
    write(root/'ALLOCATION_C.json', a)
    out = accounting.add_open_234(deepcopy(base))
    assert out['actual_plus_open_caps_usd'] == '3.0' and out['open_banks']['E123']['open_usd'] == '2.5'
    assert accounting.add_open_234(deepcopy(out)) == out
    write(root/'ALLOCATION_C.json', dict(a, status='RELEASED'))
    assert accounting.add_open_234(deepcopy(base))['actual_plus_open_caps_usd'] == '.5'


def test_accounting_override_is_process_local_and_restored_on_failure():
    old = lambda: 'old'
    module = SimpleNamespace(snapshot=old)
    with pytest.raises(ValueError):
        with phase.complete_accounting(module):
            assert module.snapshot is phase.snapshot
            raise ValueError('stop')
    assert module.snapshot is old


def test_unpinned_report_rejected_before_git_or_paid_access():
    with pytest.raises(ValueError, match='report receipt in whole operations source'):
        phase.report_pin(dict(report_adapter_source=dict(path='missing', sha256='missing')), dict(files={}))
