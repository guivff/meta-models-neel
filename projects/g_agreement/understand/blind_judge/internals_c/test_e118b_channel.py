from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
import json
import pytest

from . import e118b_channel as c, accounting231 as accounting
from .transport import frozen_wire, check_privacy, decode
from projects.g_agreement.e118_analysis.adapter import SYSTEM
from projects.g_agreement.readerbench.io import read, write, sha, verify


def units():
    return [dict(id='%032x' % i, context='The stated place is Cedar.', readout='Cedar is the stated place.') for i in (2, 1)]


def test_exact_frozen_prompt_schema_and_private_field_rejection():
    calls = c.calls_for(units())
    assert calls[0]['id'] < calls[1]['id']
    assert all(x['rendered']['system'] == SYSTEM for x in calls)
    assert json.loads(calls[0]['rendered']['user']) == units()[1]
    for field in ('condition', 'belief_stating', 'target', 'source_id'):
        bad = units()
        bad[0][field] = 'PRIVATE'
        with pytest.raises(ValueError):
            c.calls_for(bad)


@pytest.mark.parametrize('bad', [[], [dict(id='not_opaque', context='c', readout='r')],
    [dict(id='0'*32, context='', readout='r')]])
def test_invalid_or_empty_unit_packet_stops(bad):
    with pytest.raises(ValueError):
        c.calls_for(bad)


def test_same_route_no_path_exception_and_charged_length_terminal():
    protocol = SimpleNamespace(MODEL='google/gemini-3.1-flash-lite', PROVIDER='google-vertex/global', PROVIDER_NAME='Google Vertex')
    call = c.calls_for(units())[0]
    wire = frozen_wire(call, protocol)
    assert all(wire['provider'][k] == v for k, v in dict(only=['google-vertex/global'],
        order=['google-vertex/global'], allow_fallbacks=False, data_collection='deny', zdr=True,
        require_parameters=True, max_price={'completion': 1.5, 'prompt': .25}).items())
    def reject(*args):
        raise ValueError('blocked')
    with pytest.raises(ValueError):
        check_privacy('E118', call, wire, reject, protocol)
    saved = dict(http_status=200, response=dict(provider=protocol.PROVIDER_NAME, model=protocol.MODEL,
        usage=dict(cost=.001), choices=[dict(finish_reason='length', message=dict(content='partial'))]))
    terminal, _ = decode(call, saved, protocol)
    assert terminal['status'] == 'UNPARSEABLE' and terminal['result'] is None


def test_no_cap_borrow_or_schema_retry_and_no_duplicate_units():
    assert c.CAP == Decimal('1')
    for bank, cap in [('E118', '2'), ('E107', '1')]:
        with pytest.raises(ValueError):
            c.E118bTransport(None, None, dict(bank=bank, allocation_usd=cap), 'synthetic')
    bad = units()
    bad[1]['id'] = bad[0]['id']
    with pytest.raises(ValueError):
        c.calls_for(bad)


def fake_channel(tmp_path, terminals=None, fail_at=None):
    class Fake:
        invocations = []
        def __init__(self, path, digest, admission, key):
            self.calls = read(path.parent/'CALLS.json')
            self.root = tmp_path/'physical'
            self.routes = {'approved': True}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def summary(self):
            return dict(actual_usd='.0002', unresolved_upper_usd='0')
        def call(self, ident, validator):
            self.invocations.append(ident)
            if fail_at == len(self.invocations):
                raise ValueError('unknown charge; stop bank')
            raw = self.root/'ledger/E118_judging'/(ident+'.response.json')
            raw.parent.mkdir(parents=True, exist_ok=True)
            write(raw, dict(saved=True))
            value = dict(verdict='YES')
            validator(value)
            status = (terminals or {}).get(ident, 'KEPT')
            return dict(id=ident, status=status, result=value if status == 'KEPT' else None,
                request_id=ident, response_sha256=sha(raw)), dict(verified=True)
    return Fake


def phase(tmp_path, monkeypatch):
    dest = tmp_path/'belief_wrong_consistency_judging'
    dest.mkdir()
    write(dest/'CALLS.json', c.calls_for(units()))
    write(dest/'ADMISSION.json', dict(bank='E118'))
    write(dest/'INPUT_SEAL.json', dict(files={'CALLS.json': sha(dest/'CALLS.json')}))
    source = tmp_path/'SOURCE.json'
    write(source, dict(synthetic=True))
    monkeypatch.setattr(c, 'SOURCE', source)
    return dest


def test_full_loop_seals_actual_call_phase_not_directory_and_no_replay(tmp_path, monkeypatch):
    dest = phase(tmp_path, monkeypatch)
    fake = fake_channel(tmp_path, {units()[0]['id']: 'UNPARSEABLE'})
    seal = c.acquire(dest, {}, fake, 'synthetic')
    verify(seal, sha(seal))
    assert read(dest/'outputs/COUNTS.json')['status_counts'] == {'KEPT': 1, 'UNPARSEABLE': 1}
    assert read(dest/'outputs/PROGRESS.json')['completed'] == 2
    assert all('/E118_judging/' in x['path'] for x in read(dest/'outputs/RAW_RESPONSE_BINDINGS.json'))
    assert len(fake.invocations) == 2
    c.acquire(dest, {}, fake, 'synthetic')
    assert len(fake.invocations) == 2


def test_unknown_failure_keeps_saved_response_and_has_no_complete_seal(tmp_path, monkeypatch):
    dest = phase(tmp_path, monkeypatch)
    fake = fake_channel(tmp_path, fail_at=2)
    with pytest.raises(ValueError):
        c.acquire(dest, {}, fake, 'synthetic')
    assert read(dest/'outputs/STATUS.json')['status'] == 'STOPPED'
    assert not (dest/'outputs/JUDGMENT_SEAL.json').exists()
    assert len(list((tmp_path/'physical/ledger/E118_judging').glob('*.response.json'))) == 1


def test_new_accounting_only_concrete_open_combined_cap_once(tmp_path, monkeypatch):
    monkeypatch.setattr(accounting, 'SHARED', tmp_path)
    monkeypatch.setattr(accounting, 'bank_actual', lambda root: (Decimal('.3'), Decimal('.2')))
    base = dict(open_banks={}, open_caps_remaining_usd='0', actual_plus_open_caps_usd='.5')
    assert accounting.add_open_231(deepcopy(base)) == dict(base, warning_triggered=False)
    for bank, cap, status in [('E120', 2, 'OPEN'), ('E121', 1, 'RELEASED')]:
        root = tmp_path/bank
        root.mkdir()
        write(root/'ALLOCATION_C.json', dict(bank=bank, allocation_usd=cap,
            operator='W-internals-C', reservation_included=True, status=status))
    out = accounting.add_open_231(deepcopy(base))
    assert out['actual_plus_open_caps_usd'] == '2.0' and out['open_banks']['E120']['open_usd'] == '1.5'
    assert accounting.add_open_231(deepcopy(out)) == out
