"""Offline: a request cut off mid-flight is settled at its bound, then resumed once under a new id; no resend of the original."""
import json
from decimal import Decimal
import pytest
from projects.g_agreement.readerbench.io import read
from projects.g_agreement.readerbench.scoring import require  # noqa: F401  (imported for parity with runtime)
from . import wmech2_resume as resume
from .run import route_modules


@pytest.fixture
def e10(tmp_path, monkeypatch):
    plan = read(resume.channel.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    api, privacy, protocol, io = route_modules(plan)
    monkeypatch.setattr(api, 'CAP', Decimal('1'))
    monkeypatch.setattr(api.P, 'payload', lambda stage, items, taxonomy=None: {'max_tokens': 64, 'items': items})
    monkeypatch.setattr(api.P, 'validate', lambda stage, value, items, taxonomy=None: value)
    monkeypatch.setattr(api.privacy, 'check_wire', lambda *a: None)
    monkeypatch.setattr(io, 'digest', io.digest)
    monkeypatch.setattr(api.Client, 'one', api.Client.one)
    return api, io, tmp_path


def ok_send(api, sent):
    def send(wire):
        sent.append(wire)
        return 200, {'provider': api.P.PROVIDER_NAME, 'model': api.P.MODEL, 'usage': {'cost': 0.0001},
                     'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'ok': True})}}]}
    return send


def cut(api, io, root, items):
    """Reproduce the 12:12Z kill: reserve + request saved, then the process dies before any response or result."""
    wire = api.P.payload('E79_attempt1', items);rid = io.digest(io.canonical(wire))
    assert api.Ledger(root/'ledger.jsonl').reserve(rid, api.upper(wire))
    (root/'E79_attempt1').mkdir(parents=True, exist_ok=True)
    io.save(root/'E79_attempt1'/(rid+'.request.json'), {'wire': wire, 'upper_usd': str(api.upper(wire))})
    return rid, wire


def test_cut_off_settles_at_bound_and_resumes_under_new_id(e10):
    api, io, root = e10;items = [{'id': 'a', 'readout': 'x'}];rid, wire = cut(api, io, root, items)
    sent = [];client = api.Client(root, 'k', send=ok_send(api, sent))
    assert client.one('E79_attempt1', items)['reason'] == 'PRIOR_RESERVED_NO_RESPONSE_NO_RETRY' and not sent  # plain resume stops
    record = resume.settle_inflight(api, root, 'E79_attempt1', rid)
    book, done = api.Ledger(root/'ledger.jsonl').totals()
    assert rid in done and book[rid] == api.upper(wire) == Decimal(record['actual_usd'])
    assert resume.settle_inflight(api, root, 'E79_attempt1', rid) == record  # idempotent, no second settle
    resume.patch_client(api, io)
    first = client.one('E79_attempt1', items)
    assert first['status'] == 'OK' and first['id'] == resume.retry_id(rid, 1) and sent == [wire]
    assert (root/'E79_attempt1'/(first['id']+'.response.json')).exists()
    assert client.one('E79_attempt1', items) == first and len(sent) == 1  # cached; never resent
    book, done = api.Ledger(root/'ledger.jsonl').totals()
    assert set(book) == done and sum(1 for k in book if k == rid) == 1


def test_untouched_requests_and_unsettled_retry_stop(e10):
    api, io, root = e10;sent = [];client = api.Client(root, 'k', send=ok_send(api, sent));resume.patch_client(api, io)
    normal = client.one('E79_attempt0', [{'id': 'b', 'readout': 'y'}])
    assert normal['status'] == 'OK' and normal['id'] == io.digest(io.canonical(api.P.payload('', [{'id': 'b', 'readout': 'y'}])))
    items = [{'id': 'c', 'readout': 'z'}];rid, wire = cut(api, io, root, items)
    resume.settle_inflight(api, root, 'E79_attempt1', rid)
    retry = resume.retry_id(rid, 1);assert api.Ledger(root/'ledger.jsonl').reserve(retry, api.upper(wire))  # retry also cut off
    n = len(sent);stop = client.one('E79_attempt1', items)
    assert stop['reason'] == 'PRIOR_RESERVED_NO_RESPONSE_NO_RETRY' and len(sent) == n  # unsettled retry is never resent


def test_settle_refuses_completed_or_unreserved(e10):
    api, io, root = e10;items = [{'id': 'd', 'readout': 'w'}];rid, _ = cut(api, io, root, items)
    io.save(root/'E79_attempt1'/(rid+'.response.json'), {'http_status': 200, 'response': {}})
    with pytest.raises(Exception, match='not in flight'):resume.settle_inflight(api, root, 'E79_attempt1', rid)
    with pytest.raises(Exception, match='saved request'):resume.settle_inflight(api, root, 'E79_attempt1', 'f'*64)


def test_exactly_one_replacement_retry(e10):
    api, io, root = e10;sent = [];client = api.Client(root, 'k', send=ok_send(api, sent));resume.patch_client(api, io)
    items = [{'id': 'e', 'readout': 'v'}];rid, wire = cut(api, io, root, items)
    resume.settle_inflight(api, root, 'E79_attempt1', rid)
    first = resume.retry_id(rid, 1);assert api.Ledger(root/'ledger.jsonl').reserve(first, api.upper(wire))  # the one retry is also cut off
    io.save(root/'E79_attempt1'/(first+'.request.json'), {'wire': wire, 'upper_usd': str(api.upper(wire))})
    resume.settle_inflight(api, root, 'E79_attempt1', first)
    assert resume.MAX_RETRIES == 1
    assert client.one('E79_attempt1', items)['reason'] == 'INFLIGHT_RETRY_LIMIT' and not sent  # no second replacement
