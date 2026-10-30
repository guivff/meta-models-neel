from copy import deepcopy
from types import SimpleNamespace
import pytest
from . import e121_channel as channel
from .e121_intake import make_units
from .transport import ROOT, frozen_wire
from ..run import payload
from ..judgment_adapter402 import render_record


def fixture():
    records, original, items = [], [], []
    for i in range(84):
        for condition in ('steered', 'random'):
            ident = str(i)+condition
            items.append(dict(id=ident, base_id=str(i), condition=condition, alpha=8, row='fact_recall'))
            original.append(dict(id='old'+ident, opaque_id='oldopaque'+ident, item_id=str(i), condition=condition,
                alpha=8, row='fact_recall', arm='U', reader='oracle', flipped=True, target='B' if i%2 else 'A',
                property='A stated city', values={'A': ['Cedar'], 'B': ['Maple']}))
            records.append((dict(member='raw.json', keys=[len(records), 'text']),
                dict(id='native'+ident, item_id=ident, base_id=str(i), condition=condition, source_layer=42, reader='nla',
                     text='' if i==0 else 'The city is Cedar.', malformed=i==0, truncated=i==1)))
    return records[::-1], original, items


def test_complete_literal_source_join_no_order_inference_or_candidate_reordering():
    records, original, items = fixture()
    rubric = (ROOT/'results/g_agreement/understand/e114/JUDGE_RUBRIC_COPY.md').read_text()
    units, joins = make_units(records, original, items, rubric)
    assert len(units) == len(joins) == 168
    assert all(j['native_id'] != j['source_input_id'] for j in joins)
    assert sum(u['data']['readout'] == '' for u in units) == 2
    assert all(u['data']['values'] == {'A': ['Cedar'], 'B': ['Maple']} for u in units)
    by = {u['id']: u for u in units}
    for j in joins:
        assert by[j['id']]['data']['values'] == original[j['original_private_index']]['values']
        assert j['steered_letter'] == original[j['original_private_index']]['target']


@pytest.mark.parametrize('fault', ['partial', 'wrong_hook', 'wrong_reader', 'wrong_source_item'])
def test_no_partial_source_or_new_scope(fault):
    records, original, items = deepcopy(fixture())
    if fault == 'partial': records.pop()
    if fault == 'wrong_hook': items[0]['alpha'] = 9
    if fault == 'wrong_reader': records[0][1]['reader'] = 'oracle'
    if fault == 'wrong_source_item': records[0][1]['base_id'] = 'unknown'
    with pytest.raises(ValueError): make_units(records, original, items, 'rubric')


def test_exact_E104_wire_schema_and_no_private_fields_or_rubric_substitution():
    rubric = (ROOT/'results/g_agreement/understand/e114/JUDGE_RUBRIC_COPY.md').read_text()
    unit = make_units(*fixture(), rubric)[0][0]
    p = SimpleNamespace(MODEL='google/gemini-3.1-flash-lite', PROVIDER='google-vertex/global', PROVIDER_NAME='Google')
    call, validate = channel.original104_call(unit, p)
    assert frozen_wire(call, p) == payload([render_record(unit['data'], rubric)], rubric, 'E56', p)
    assert channel.CAP == 1
    bad = deepcopy(unit); bad['data']['target'] = 'A'
    with pytest.raises(ValueError): channel.original104_call(bad, p)
    bad = deepcopy(unit); bad['rubric'] += ' changed'
    with pytest.raises(ValueError): channel.original104_call(bad, p)


def test_worker_only_process_local_and_terminal_null_preserved(monkeypatch):
    monkeypatch.setattr(channel, 'source_gate', lambda: None)
    names = ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE', 'write')
    saved = {n: getattr(channel.registered, n) for n in names}; caps = dict(channel.transport.CAPS)
    with channel.worker():
        assert channel.transport.CAPS['E121'] == 1
        assert channel.registered.normalized_code('original104', dict(status='UNPARSEABLE', result=None)) is None
    assert channel.transport.CAPS == caps
    assert all(getattr(channel.registered, n) is v for n, v in saved.items())
