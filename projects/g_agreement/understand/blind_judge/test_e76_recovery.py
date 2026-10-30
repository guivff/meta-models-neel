import json
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace
import pytest
from projects.g_agreement.understand.blind_judge import e76_recovery as m
from projects.g_agreement.understand.blind_judge.run import route_modules
from projects.g_agreement.readerbench.io import read, write

@pytest.fixture
def route(tmp_path):
    api, _, p, io = route_modules({'e10_source':'/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/projects/g_agreement/understand/e10'})
    api.CAP=Decimal('18')
    return api, p, io

def evidence(root, rid, status=429):
    folder=root/'E76_attempt0';folder.mkdir(exist_ok=True)
    write(folder/(rid+'.request.json'), {'upper_usd':'0.01','wire':{}})
    write(folder/(rid+'.response.json'), {'http_status':status,'response':{'error':{'code':status}}})

def test_settlement_idempotent_and_evidence(route,tmp_path):
    api,_,_=route;rid='a'*64
    ledger=api.Ledger(tmp_path/'ledger.jsonl');ledger.reserve(rid,Decimal('.01'));evidence(tmp_path,rid)
    m.settle_rejection(api,tmp_path,'E76_attempt0',rid)
    before=ledger.path.read_bytes();m.settle_rejection(api,tmp_path,'E76_attempt0',rid)
    assert ledger.path.read_bytes()==before and ledger.summary()['unresolved_reserve_usd']=='0'
    body=read(tmp_path/'E76_attempt0'/(rid+'.response.json'));body['response']['id']='generated'
    write(tmp_path/'E76_attempt0'/(rid+'.response.json'),body)
    with pytest.raises(ValueError):m.settle_rejection(api,tmp_path,'E76_attempt0',rid)

@pytest.mark.parametrize('body',[{'http_status':503,'response':{}},{'http_status':429,'response':{'id':'gen','error':{'code':429}}},{'http_status':429,'response':{'usage':{'cost':.01},'error':{'code':429}}}])
def test_no_guessed_zero(body):
    with pytest.raises(ValueError):m.rejected_uncharged(body)

@contextmanager
def guard(api,wire):yield

def test_capped_separately_reserved_retries(route,tmp_path):
    api,p,io=route
    wire={'max_tokens':1};p.payload=lambda *a:wire
    old_check=api.privacy.check_wire;api.privacy.check_wire=lambda *a:None
    try:
        client=api.Client(tmp_path,'unused',send=lambda wire:(429,{'error':{'code':429}}))
        waits=[]
        with pytest.raises(RuntimeError,match='retry limit'):
            m.one_with_backoff(client,api,io,'E76_attempt0',[],wire,guard,waits.append)
        book,done=client.ledger.totals()
        assert len(book)==5 and len(done)==5 and sum(book.values())==0
        assert waits==[5,10,20,40]
        # Cached attempts cannot cause additional network requests on another resume.
        client.send=lambda wire:pytest.fail('duplicate send')
        with pytest.raises(RuntimeError,match='retry limit'):
            m.one_with_backoff(client,api,io,'E76_attempt0',[],wire,guard,lambda x:None)
        assert len(client.ledger.totals()[0])==5
    finally:api.privacy.check_wire=old_check

def test_non429_stops_without_retry(route,tmp_path):
    api,p,io=route;wire={'max_tokens':1};p.payload=lambda *a:wire
    old=api.privacy.check_wire;api.privacy.check_wire=lambda *a:None
    try:
        client=api.Client(tmp_path,'unused',send=lambda wire:(503,{'error':{'code':503}}))
        result,_=m.one_with_backoff(client,api,io,'E76_attempt0',[],wire,guard,lambda x:pytest.fail('backoff on 503'))
        assert result['status']=='MISSING' and len(client.ledger.totals()[0])==1
        assert len(client.ledger.totals()[1])==0
    finally:api.privacy.check_wire=old
