from copy import deepcopy
from types import SimpleNamespace
import pytest
from . import e120a_channel as channel
from .e120a_intake import make_units
from .banks import load_judge85
from .transport import frozen_wire


def fixture():
    items = [dict(id=str(i), vector_index=i) for i in range(400)]
    contexts = {str(i): ('Original source '+str(i), {'original': True}) for i in range(400)}
    records = [(dict(member='raw.json', keys=[2*i+j, 'text']),
        dict(id=str(i)+'_'+str(b), item_id=str(i), condition=None, reader='oracle', source_layer=b,
            text='' if i==0 else 'No, there is no indication.'))
        for i in range(400) for j, b in enumerate((52,60))]
    return records[::-1], items, contexts


def test_full800_original_context_no_labels_and_empty_readouts_retained():
    units, joins = make_units(*fixture())
    assert len(units) == len(joins) == 800
    assert sum(x['data']['readout'] == '' for x in units) == 2
    assert all(set(x['data']) == {'id', 'source_text', 'readout'} and x['rubric'] is None for x in units)
    assert {x['block'] for x in joins} == {52,60}


@pytest.mark.parametrize('fault', ['partial', 'duplicate', 'wrong_reader', 'wrong_layer', 'missing_context'])
def test_no_partial_grid_or_source_substitution(fault):
    records, items, contexts = deepcopy(fixture())
    if fault == 'partial': records.pop()
    if fault == 'duplicate': records[0] = records[1]
    if fault == 'wrong_reader': records[0][1]['reader'] = 'nla'
    if fault == 'wrong_layer': records[0][1]['source_layer'] = 44
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
    old_expiry, old_retries = channel.transport.EXPIRY, channel.parallel_funded.MAX_429_RETRIES
    saved = {n: getattr(channel.registered, n) for n in names}; caps = dict(channel.transport.CAPS)
    with channel.worker():
        assert channel.transport.CAPS['E120'] == 2
        assert channel.transport.EXPIRY == 1793372400 and channel.parallel_funded.MAX_429_RETRIES == 0
        assert channel.registered.normalized_code('eval85', dict(status='UNPARSEABLE', result=None)) is None
    assert channel.transport.CAPS == caps
    assert channel.transport.EXPIRY == old_expiry and channel.parallel_funded.MAX_429_RETRIES == old_retries
    assert all(getattr(channel.registered, n) is v for n, v in saved.items())


def test_same_lifetime_continuation_cannot_reset_previous_spend():
    v=dict(bank='E120',part='a',lifetime_cap_usd='2',prior_part_c_actual_usd='.39204125',
           remaining_allowance_usd='1.60795875',prior_allocation_status='RELEASED',same_original_allowance=True)
    channel.check_continuation(v)
    with pytest.raises(ValueError):channel.check_continuation(dict(v,remaining_allowance_usd='2'))


def test_expiry_rechecked_at_physical_post_after_pacing(monkeypatch):
    posts=[];req=SimpleNamespace(post=lambda *a,**k:posts.append(a))
    obj=object.__new__(channel.E120Transport)
    obj.api=SimpleNamespace(requests=req)
    monkeypatch.setattr(channel.transport.Transport,'__enter__',lambda self:self)
    monkeypatch.setattr(channel.transport.Transport,'__exit__',lambda self,*args:None)
    channel.E120Transport.__enter__(obj)
    def expired():raise ValueError('expired at physical post')
    monkeypatch.setattr(channel.transport,'unpaused',expired)
    with pytest.raises(ValueError):req.post('https://openrouter.ai/api/v1/chat/completions')
    assert posts==[]
    channel.E120Transport.__exit__(obj,None,None,None)
