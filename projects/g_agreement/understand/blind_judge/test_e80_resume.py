"""Offline: an uncharged provider error (HTTP 200, finish_reason error, cost 0) is retried once under a new id."""
import json
from decimal import Decimal
import pytest
from projects.g_agreement.readerbench.io import read
from . import e80_resume as resume
from .run import route_modules


@pytest.fixture
def e10(tmp_path, monkeypatch):
    api, privacy, protocol, io = route_modules(read(resume.channel.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'))
    monkeypatch.setattr(api, 'CAP', Decimal('1'))
    monkeypatch.setattr(api.P, 'payload', lambda stage, items, taxonomy=None: {'max_tokens': 64, 'items': items})
    monkeypatch.setattr(api.P, 'validate', lambda stage, value, items, taxonomy=None: value)
    monkeypatch.setattr(api.privacy, 'check_wire', lambda *a: None)
    monkeypatch.setattr(io, 'digest', io.digest)
    monkeypatch.setattr(api.Client, 'one', api.Client.one)
    return api, io, tmp_path


def body(api, finish='stop', cost=0.0001, tokens=5):
    return {'provider': api.P.PROVIDER_NAME, 'model': api.P.MODEL, 'usage': {'cost': cost, 'prompt_tokens': tokens, 'completion_tokens': tokens},
            'choices': [{'finish_reason': finish, 'message': {'content': json.dumps({'ok': True})}}]}


def test_uncharged_error_retried_once_under_new_id(e10):
    api, io, root = e10;items = [{'id': 'a', 'readout': 'x'}];plan = [body(api, 'error', 0, 0), body(api)];sent = []
    client = api.Client(root, 'k', send=lambda wire: (sent.append(wire) or (200, plan[len(sent)-1])))
    first = client.one('E80c_attempt0', items)  # reproduce: cached MISSING, settled at USD 0
    assert first['status'] == 'MISSING' and first['reason'] == 'truncated/refused response'
    book, done = client.ledger.totals();assert first['id'] in done and book[first['id']] == 0
    assert client.one('E80c_attempt0', items) == first and len(sent) == 1  # plain rerun: cached, stops again
    resume.patch_client(api, io)
    second = client.one('E80c_attempt0', items)
    assert second['status'] == 'OK' and second['id'] == resume.retry_id(first['id'], 1) and len(sent) == 2
    assert (root/'E80c_attempt0'/(second['id']+'.response.json')).exists()
    assert client.one('E80c_attempt0', items) == second and len(sent) == 2  # cached; never resent
    book, done = client.ledger.totals();assert set(book) == done


def test_charged_or_other_failures_untouched(e10):
    api, io, root = e10;sent = []
    client = api.Client(root, 'k', send=lambda wire: (sent.append(wire) or (200, body(api, 'length'))));resume.patch_client(api, io)
    r = client.one('E80c_attempt0', [{'id': 'b', 'readout': 'y'}])
    assert r['status'] == 'MISSING' and client.one('E80c_attempt0', [{'id': 'b', 'readout': 'y'}]) == r and len(sent) == 1
    assert not resume.uncharged_provider_error({'http_status': 200, 'response': body(api, 'error', 0.001, 3)})
    assert not resume.uncharged_provider_error({'http_status': 429, 'response': {}})


def test_unresolved_retry_never_resent_and_terminal_dir_protected(e10, tmp_path):
    api, io, root = e10;items = [{'id': 'c', 'readout': 'z'}];sent = []
    client = api.Client(root, 'k', send=lambda wire: (sent.append(wire) or (200, body(api, 'error', 0, 0))))
    first = client.one('E80c_attempt0', items);resume.patch_client(api, io)
    new = resume.retry_id(first['id'], 1);assert client.ledger.reserve(new, Decimal('0.001'))  # retry cut off mid-flight
    assert client.one('E80c_attempt0', items)['reason'] == 'PRIOR_RESERVED_NO_RESPONSE_NO_RETRY' and len(sent) == 1
    d = tmp_path/'E80c';d.mkdir();(d/'START.json').write_text('{}')
    kept = resume.set_aside(d);assert kept.exists() and not d.exists() and (kept/'START.json').exists()
    t = tmp_path/'E80';t.mkdir();(t/'JUDGMENTS.json').write_text('[]')
    with pytest.raises(Exception, match='terminal'):resume.set_aside(t)


def test_charged_length_truncation_is_terminal_without_retry(tmp_path):
    def saved(finish, cost):
        return {'http_status': 200, 'response': {'usage': {'cost': cost}, 'choices': [{'finish_reason': finish, 'message': {'content': '{"x'}}]}}
    trunc = tmp_path/'a.response.json';trunc.write_text(json.dumps(saved('length', 0.0063)))
    schema = tmp_path/'b.response.json';schema.write_text(json.dumps(saved('stop', 0.0001)))
    shim = resume.TerminalOnTruncation()
    attempts = []
    for attempt in shim.range(3):  # mirrors the channel's per-record attempt loop
        attempts.append(attempt);r = shim.read(trunc)
        assert r['response']['choices'][0]['finish_reason'] == 'stop'  # presented as completed, so recorded UNPARSEABLE
    assert attempts == [0] and len(shim.truncations) == 1  # terminal: no retry
    assert json.loads(trunc.read_text())['response']['choices'][0]['finish_reason'] == 'length'  # saved evidence untouched
    attempts = []
    for attempt in shim.range(3):  # ordinary schema failures keep the channel's two retries
        attempts.append(attempt);shim.read(schema)
    assert attempts == [0, 1, 2] and len(shim.truncations) == 1
    assert not resume.charged_length_truncation({'http_status': 200, 'response': {'usage': {}, 'choices': [{'finish_reason': 'length'}]}})
