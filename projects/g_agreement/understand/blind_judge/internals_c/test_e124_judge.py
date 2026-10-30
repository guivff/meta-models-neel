from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
import json
import pytest
from . import e124_judge as judge, accounting233 as accounting
from .transport import frozen_wire, check_privacy
from projects.g_agreement.readerbench.io import write


def units():
    return [dict(id='%032x' % i, model_answer='Cedar', readout='The model will answer Cedar.') for i in (2, 1)]


def test_frozen_model_answer_reference_three_way_rubric_and_blind_order():
    calls = judge.calls_for(units())
    assert calls[0]['id'] < calls[1]['id']
    assert all(x['rendered']['system'] == judge.SYSTEM for x in calls)
    assert json.loads(calls[0]['rendered']['user']) == units()[1]
    assert 'context' not in judge.SYSTEM.lower()
    assert calls[0]['rendered']['schema']['schema']['properties']['verdict']['enum'] == ['YES', 'NO', 'OFF-TOPIC']
    assert judge.CAP == Decimal('3')


@pytest.mark.parametrize('field', ['context', 'condition', 'target', 'belief_stating', 'item_id'])
def test_no_prompt_context_or_private_classification_on_wire(field):
    bad = units(); bad[0][field] = 'PRIVATE'
    with pytest.raises(ValueError): judge.calls_for(bad)


def test_missing_answer_is_not_filled_from_candidate_or_readout():
    bad = units(); bad[0].pop('model_answer')
    with pytest.raises(ValueError): judge.calls_for(bad)
    bad = units(); bad[0]['model_answer'] = None
    with pytest.raises(ValueError): judge.calls_for(bad)
    # A sealed literal empty answer is retained; the owner reports its source status.
    bad = units(); bad[0]['model_answer'] = ''
    assert any(json.loads(x['rendered']['user'])['model_answer'] == '' for x in judge.calls_for(bad))


def test_original_route_and_no_generalized_privacy_exception():
    p = SimpleNamespace(MODEL='google/gemini-3.1-flash-lite', PROVIDER='google-vertex/global')
    call = judge.calls_for(units())[0]; wire = frozen_wire(call, p)
    assert wire['max_tokens'] == 4096 and wire['temperature'] == 0
    assert wire['provider']['only'] == ['google-vertex/global'] and wire['provider']['zdr'] is True
    assert wire['provider']['data_collection'] == 'deny' and wire['provider']['allow_fallbacks'] is False
    def reject(*args): raise ValueError('private wire')
    with pytest.raises(ValueError): check_privacy('E124', call, wire, reject, p)


def test_accounting_only_actual_open_separate3_once(tmp_path, monkeypatch):
    monkeypatch.setattr(accounting, 'SHARED', tmp_path)
    monkeypatch.setattr(accounting, 'bank_actual', lambda root: (Decimal('.2'), Decimal('.1')))
    base = dict(open_banks={}, open_caps_remaining_usd='0', actual_plus_open_caps_usd='.3')
    assert accounting.add_open_233(deepcopy(base)) == dict(base, warning_triggered=False)
    root = tmp_path/'E124'; root.mkdir()
    a = dict(bank='E124', operator='W-internals-C', reservation_included=True, allocation_usd='3', status='OPEN')
    write(root/'ALLOCATION_C.json', a)
    out = accounting.add_open_233(deepcopy(base))
    assert out['actual_plus_open_caps_usd'] == '3.0' and out['open_banks']['E124']['open_usd'] == '2.7'
    assert accounting.add_open_233(deepcopy(out)) == out
    write(root/'ALLOCATION_C.json', dict(a, status='RELEASED'))
    assert accounting.add_open_233(deepcopy(base))['actual_plus_open_caps_usd'] == '.3'
