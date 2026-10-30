from .accounting_overlay import supplement


def test_active_full_cap_adds_remaining_without_double_counting_physical_cost():
    base=dict(open_banks={},open_caps_remaining_usd='20',actual_plus_open_caps_usd='120')
    result=supplement(base,150,3,2,True)
    assert result['actual_plus_open_caps_usd']=='265' and result['open_caps_remaining_usd']=='165'
    again=supplement(result,150,3,2,True)
    assert again['actual_plus_open_caps_usd']=='265'


def test_completed_phase_releases_remaining_allocation_not_physical_actual():
    base=dict(open_banks={},open_caps_remaining_usd='20',actual_plus_open_caps_usd='120')
    active=supplement(base,150,3,2,True)
    result=supplement(active,150,3,2,False)
    assert result['actual_plus_open_caps_usd']=='120' and result['open_caps_remaining_usd']=='20'


def test_new_concrete_cap_counts_only_remaining_and_not_twice(tmp_path,monkeypatch):
    import json
    from . import accounting_overlay as module
    from projects.g_agreement.readerbench.io import write
    monkeypatch.setattr(module,'SHARED',tmp_path)
    root=tmp_path/'E112';root.mkdir();(root/'ledger').mkdir()
    write(root/'ALLOCATION_C.json',dict(bank='E112',operator='W-internals-C',reservation_included=True,allocation_usd=3,status='OPEN'))
    rows=[dict(event='reserve',id='paid',usd='1',at=1),dict(event='settle',id='paid',usd='.5',at=2),dict(event='reserve',id='pending',usd='1',at=3)]
    (root/'ledger/ledger.jsonl').write_text('\n'.join(json.dumps(x)for x in rows)+'\n')
    base=dict(open_banks={},open_caps_remaining_usd='20',actual_plus_open_caps_usd='120')
    result=module.add_concrete_extras(base)
    assert result['open_banks']['E112']['open_usd']=='1.5' and result['actual_plus_open_caps_usd']=='121.5'
    assert module.add_concrete_extras(result)['actual_plus_open_caps_usd']=='121.5'


def test_queued_or_released_bank_is_not_an_active_allowance(tmp_path,monkeypatch):
    from . import accounting_overlay as module
    from projects.g_agreement.readerbench.io import write
    monkeypatch.setattr(module,'SHARED',tmp_path)
    root=tmp_path/'E84';root.mkdir()
    write(root/'ALLOCATION_C.json',dict(status='RELEASED'))
    base=dict(open_banks={},open_caps_remaining_usd='20',actual_plus_open_caps_usd='120')
    assert module.add_concrete_extras(base)['actual_plus_open_caps_usd']=='120'
    assert 'E110' not in base['open_banks']
