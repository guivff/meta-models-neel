from decimal import Decimal
from types import SimpleNamespace
import pytest
from .run import payload, route_modules
from projects.g_agreement.readerbench.scoring import validate_judgments


def test_payload_blind_and_exact_route():
    items = [{'id': 'opaque', 'property': 'kind', 'values': {}, 'readout': 'some text'}]
    p = SimpleNamespace(MODEL='google/gemini-3.1-flash-lite', PROVIDER='google-vertex/global')
    wire = payload(items, 'frozen rubric', 'D5', p)
    assert wire['provider']['only'] == ['google-vertex/global']
    assert wire['provider']['zdr'] and not wire['provider']['allow_fallbacks']
    assert wire['provider']['data_collection'] == 'deny'
    assert wire['temperature'] == 0 and wire['reasoning']['effort'] == 'minimal'
    import json
    assert set(json.loads(wire['messages'][1]['content'])[0]) == {'id', 'readout'}
    props = wire['response_format']['json_schema']['schema']['properties']['records']['items']['properties']
    assert 'structural_value' in props['category']['enum'] and 'states_value' not in props['category']['enum']
    assert 'values' not in props
    props54 = payload(items, 'rubric', 'E56', p)['response_format']['json_schema']['schema']['properties']['records']['items']['properties']
    assert 'values' in props54 and 'names_property_without_value' in props54['category']['enum']


def test_real_transport_ledger_cap_and_no_retry(tmp_path):
    from pathlib import Path
    source = Path(__file__).resolve().parents[5]/'wt-wtext/projects/g_agreement/understand/e10'
    api, privacy, protocol, io = route_modules({'e10_source': str(source)})
    ledger = api.Ledger(tmp_path/'ledger.jsonl')
    assert ledger.reserve('first', Decimal('4.99'))
    assert not ledger.reserve('over', Decimal('.02'))
    with pytest.raises(RuntimeError):
        ledger.reserve('first', Decimal('.001'))
    ledger.settle('first', '.01')
    assert ledger.summary()['cap_usd'] == '5'
    assert ledger.summary()['actual_usd'] == '0.01'


def test_invalid_grid_does_not_become_codes():
    packet = [{'id': 'x', 'readout': 'cat'}]
    with pytest.raises(ValueError):
        validate_judgments(packet, [{'id': 'x', 'category': 'topic_content', 'evidence': 'dog'}], 'D5')
    with pytest.raises(ValueError):
        validate_judgments(packet, [], 'D5')


def test_continuation_never_resends_failed_or_successful_requests(tmp_path, monkeypatch):
    from pathlib import Path
    source = Path(__file__).resolve().parents[5]/'wt-wtext/projects/g_agreement/understand/e10'
    api, privacy, protocol, io = route_modules({'e10_source': str(source)})
    calls = []
    def wire(stage, items, taxonomy=None):
        return payload(items, 'rubric', 'D5', protocol)
    def validate(stage, result, items, taxonomy=None):
        validate_judgments(items, result['records'], 'D5')
        return result['records']
    monkeypatch.setattr(protocol, 'payload', wire)
    monkeypatch.setattr(protocol, 'validate', validate)
    monkeypatch.setattr(privacy, 'check_wire', lambda *args: None)
    def send(w):
        calls.append(w)
        import json
        item = json.loads(w['messages'][1]['content'])[0]
        evidence = 'not present' if item['id'] == 'bad' else 'cat'
        return 200, {'model': protocol.MODEL, 'provider': protocol.PROVIDER_NAME,
            'usage': {'cost': .001}, 'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps({'records': [{'id': item['id'], 'category': 'topic_content', 'evidence': evidence}]})}}]}
    client = api.Client(tmp_path, 'synthetic', send=send)
    for ident in ('bad', 'good'):
        items = [{'id': ident, 'property': 'kind', 'values': {}, 'readout': 'cat'}]
        first = client.one('D5_E49', items)
        assert client.one('D5_E49', items) == first
    assert len(calls) == 2
    assert client.ledger.summary()['actual_usd'] == '0.002'
