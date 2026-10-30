from copy import deepcopy
from types import SimpleNamespace
import pytest
from . import e120c_channel as channel
from .e120c_intake import make_units
from .banks import load_judge85
from .transport import frozen_wire


def fixture():
    items = [dict(id=str(i), vector_index=i) for i in range(400)]
    contexts = {str(i): ('Original source '+str(i), {'original': True}) for i in range(400)}
    records = [(dict(member='raw.json', keys=[2*i+j, 'text']),
        dict(id=str(i)+'_'+arm, item_id=str(i), condition=arm, reader='oracle', source_layer=44,
            text='' if i==0 else 'No, there is no indication.'))
        for i in range(400) for j, arm in enumerate(('targeted', 'sham'))]
    return records[::-1], items, contexts


def test_full800_original_context_no_labels_and_empty_readouts_retained():
    units, joins = make_units(*fixture())
    assert len(units) == len(joins) == 800
    assert sum(x['data']['readout'] == '' for x in units) == 2
    assert all(set(x['data']) == {'id', 'source_text', 'readout'} and x['rubric'] is None for x in units)
    assert {x['arm'] for x in joins} == {'targeted', 'sham'}


@pytest.mark.parametrize('fault', ['partial', 'duplicate', 'wrong_reader', 'wrong_layer', 'missing_context'])
def test_no_partial_grid_or_source_substitution(fault):
    records, items, contexts = deepcopy(fixture())
    if fault == 'partial': records.pop()
    if fault == 'duplicate': records[0] = records[1]
    if fault == 'wrong_reader': records[0][1]['reader'] = 'nla'
    if fault == 'wrong_layer': records[0][1]['source_layer'] = 52
    if fault == 'missing_context': contexts.pop('0')
    with pytest.raises(ValueError): make_units(records, items, contexts)


def test_exact_judge205_message_schema_route_and_no_gold_metadata():
    unit = make_units(*fixture())[0][0]
    call, validate = channel.original205_call(unit, None)
    p = SimpleNamespace(MODEL='google/gemini-3.1-flash-lite', PROVIDER='google-vertex/global')
    wire = frozen_wire(call, p)
    assert wire['messages'] == load_judge85().messages(unit['data']['source_text'], unit['data']['readout'])
    assert wire['provider']['zdr'] is True and wire['provider']['data_collection'] == 'deny' and wire['provider']['allow_fallbacks'] is False
    assert channel.CAP == 2
    bad = deepcopy(unit); bad['data']['addressed'] = True
    with pytest.raises(ValueError): channel.original205_call(bad, None)


def test_process_only_override_and_no_missing_zero(monkeypatch):
    monkeypatch.setattr(channel, 'source_gate', lambda: None)
    names = ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE', 'write')
    saved = {n: getattr(channel.registered, n) for n in names}; caps = dict(channel.transport.CAPS)
    with channel.worker():
        assert channel.transport.CAPS['E120'] == 2
        assert channel.registered.normalized_code('eval85', dict(status='UNPARSEABLE', result=None)) is None
    assert channel.transport.CAPS == caps
    assert all(getattr(channel.registered, n) is v for n, v in saved.items())
