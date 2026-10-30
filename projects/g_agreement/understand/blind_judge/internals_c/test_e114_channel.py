from types import SimpleNamespace
import pytest
from . import e114_channel as e
from .transport import ROOT, frozen_wire
from ..run import payload
from ..judgment_adapter402 import render_record

P = SimpleNamespace(MODEL='google/gemini-3.1-flash-lite', PROVIDER='google-vertex/global', PROVIDER_NAME='Google')


def fixture():
    rubric = (ROOT/'results/g_agreement/understand/e114/JUDGE_RUBRIC_COPY.md').read_text()
    return dict(id='a'*32, kind='original57', rubric=rubric,
        data=dict(id='a'*32, property='Current nesting depth', values=dict(A='3', B='4'), readout='The depth is 3.'))


def test_original57_literal_wire_and_schema_equality():
    unit = fixture()
    call, validate = e.original57_call(unit, P)
    expected = payload([render_record(unit['data'], unit['rubric'])], unit['rubric'], 'E56', P)
    assert frozen_wire(call, P) == expected
    validate(dict(records=[dict(id=unit['id'], category='states_value', values=['A'], evidence='The depth is 3.')]))
    assert str(e.CAP) == '2'


def test_no_private_metadata_or_amended_rubric_allowed():
    unit = fixture()
    unit['data']['gold'] = 'A'
    with pytest.raises(ValueError):
        e.original57_call(unit, P)
    unit = fixture()
    unit['rubric'] += '\nnew instruction'
    with pytest.raises(ValueError):
        e.original57_call(unit, P)


def test_worker_changes_only_current_process_and_restores_originals(monkeypatch):
    monkeypatch.setattr(e, 'source_gate', lambda: None)
    before = {name: getattr(e.registered, name) for name in
              ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE')}
    caps = dict(e.transport.CAPS)
    with e.worker():
        assert e.transport.CAPS['E114'] == e.CAP
        assert e.registered.HERE == e.transport.HERE/'E114'
        assert e.registered.normalized_code('original57', dict(status='UNPARSEABLE', result=None)) is None
    assert e.transport.CAPS == caps
    assert all(getattr(e.registered, name) is value for name, value in before.items())
