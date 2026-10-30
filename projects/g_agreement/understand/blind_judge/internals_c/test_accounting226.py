from decimal import Decimal
from copy import deepcopy
from . import accounting226 as a
from projects.g_agreement.readerbench.io import write


def test_only_actual_open_allocations_add_residual_once(tmp_path, monkeypatch):
    monkeypatch.setattr(a, 'SHARED', tmp_path)
    monkeypatch.setattr(a, 'bank_actual', lambda root: (Decimal('.3'), Decimal('.2')))
    base = dict(open_banks={}, open_caps_remaining_usd='0', actual_plus_open_caps_usd='.5')
    for bank, cap, status in [('E114', 2, 'OPEN'), ('E100e', 3, 'RELEASED')]:
        root = tmp_path/bank
        root.mkdir()
        write(root/'ALLOCATION_C.json', dict(bank=bank, operator='W-internals-C',
            reservation_included=True, allocation_usd=cap, status=status))
    result = a.add_open_226(deepcopy(base))
    assert result['actual_plus_open_caps_usd'] == '2.0' and result['open_caps_remaining_usd'] == '1.5'
    assert set(result['open_banks']) == {'E114'}
    assert a.add_open_226(deepcopy(result)) == result


def test_queued_authorization_is_not_an_open_allocation(tmp_path, monkeypatch):
    monkeypatch.setattr(a, 'SHARED', tmp_path)
    base = dict(open_banks={}, open_caps_remaining_usd='0', actual_plus_open_caps_usd='2')
    assert a.add_open_226(deepcopy(base))['actual_plus_open_caps_usd'] == '2'
