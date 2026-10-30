from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
import pytest
from . import transport217c2_e79b as m, parallel_funded as parallel, operational217 as ops
from .run import route_modules
from projects.g_agreement.readerbench.io import read, write, sha

P = SimpleNamespace(PROVIDER_NAME='Google', MODEL='google/gemini-3.1-flash-lite')


def error(cost=0, code=429, finish='error'):
    return dict(http_status=200, response=dict(provider=P.PROVIDER_NAME, model=P.MODEL,
                id='synthetic-generation', usage=dict(cost=cost), choices=[dict(finish_reason=finish,
                error=dict(code=code), message=dict(content='{"records":[{"id":"opaque","category":"silent"}]}'))]))


@pytest.mark.parametrize('code,finish', [(429,'stop'), (503,'stop'), (499,'error')])
def test_explicit_zero_provider_error_eligible(code, finish):
    assert m.eligible(error(code=code,finish=finish),P)


@pytest.mark.parametrize('change', ['charged','unknown','nan','bool','wrongroute','402','length','success'])
def test_no_broadening(change):
    x=error()
    if change in ('charged','unknown','nan','bool'): x['response']['usage']['cost']={'charged':.01,'unknown':None,'nan':'NaN','bool':False}[change]
    if change=='wrongroute':x['response']['provider']='other'
    if change=='402':x['http_status']=402
    if change in ('length','success'):
        c=x['response']['choices'][0];c.pop('error');c['finish_reason']='length' if change=='length' else 'stop'
    assert not m.eligible(x,P)


def setup(tmp_path, monkeypatch):
    api,privacy,p,io=route_modules(read(m.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'))
    monkeypatch.setattr(api,'CAP',Decimal('15'))
    monkeypatch.setattr(p,'payload',lambda stage,items,taxonomy=None:dict(max_tokens=64,items=items))
    monkeypatch.setattr(p,'validate',lambda stage,value,items,taxonomy=None:[dict(id=x['id'],status='KEPT',code=dict(id=x['id'],category='silent',values=[],evidence='')) for x in items])
    monkeypatch.setattr(privacy,'check_wire',lambda *a:None)
    slots=[];monkeypatch.setattr(parallel,'claim_slot',slots.append)
    bank=SimpleNamespace(SHARED=tmp_path,patch_api=parallel.patch_api,audit_response=ops.audit_response,
                         truncated=ops.truncated,judge=ops.judge,adapt=ops.adapt)
    (tmp_path/'E79_ARM_B/judgments').mkdir(parents=True)
    (tmp_path/'E79_ARM_B/ledger').mkdir()
    monkeypatch.setattr(io,'digest',lambda value:__import__('hashlib').sha256(('originalstage:originalinput:'+value).encode()).hexdigest())
    return api,p,io,bank,slots


def test_saved_failure_resume_cached_success_separate_reservations_and_idempotency(tmp_path,monkeypatch):
    api,p,io,bank,slots=setup(tmp_path,monkeypatch);sent=[];items=[dict(id='opaque')]
    def send(wire):
        sent.append(deepcopy(wire))
        if len(sent)==1:return 200,error()['response']
        return 200,dict(provider=P.PROVIDER_NAME,model=P.MODEL,usage=dict(cost=.00001),choices=[dict(finish_reason='stop',message=dict(content='{}'))])
    client=api.Client(tmp_path/'E79_ARM_B/ledger','synthetic',send=send)
    failed=client.one('stage',items);assert failed['status']=='MISSING'
    raw=client.root/'stage'/(failed['id']+'.response.json');rawsha=sha(raw)
    # A preceding verified request is already cached and must not be sent again.
    good=client.one('prior',[dict(id='prior')]);assert good['status']=='OK'
    sleeps=[]
    with m.installed(bank,sleep=sleeps.append,clock=lambda:0,verify_source=False):
        bank.patch_api(api,io,'E79_ARM_B')
        assert client.one('prior',[dict(id='prior')])==good
        result=client.one('stage',items)
        assert result['status']=='OK' and result['id']!=failed['id']
        assert len(sent)==3 and sent[0]==sent[2] and sleeps==[30]
        assert client.one('stage',items)==result and len(sent)==3 and sleeps==[30]
    assert sha(raw)==rawsha
    book,done=client.ledger.totals();assert len(book)==len(done)==3
    assert client.ledger.summary()['actual_usd']=='0.00002'
    audit=read(tmp_path/'E79_ARM_B/judgments/TRANSPORT217C2.json')
    assert len(next(iter(audit.values()))['attempts'])==2


def test_two_retries_exhaust_to_missing_no_schema_retry_and_partial_never_kept(tmp_path,monkeypatch):
    api,p,io,bank,slots=setup(tmp_path,monkeypatch);sent=[];sleeps=[];items=[dict(id='opaque',readout='synthetic')]
    def send(wire):sent.append(wire);return 200,error()['response']
    client=api.Client(tmp_path/'E79_ARM_B/ledger','synthetic',send=send)
    with m.installed(bank,sleep=sleeps.append,clock=lambda:0,verify_source=False):
        bank.patch_api(api,io,'E79_ARM_B')
        def dispatch(batch,attempt):
            assert attempt==0
            result=client.one('stage',batch)
            saved=read(client.root/'stage'/(result['id']+'.response.json'))
            assert bank.audit_response(saved,p)['transport_exhausted']
            return bank.truncated(batch)
        terminal=bank.judge(items,dispatch)
        assert len(sent)==3 and sleeps==[30,60]
        assert terminal[0]['code'] is None and terminal[0]['terminal_reason']==m.REASON and terminal[0]['attempts']==0
        flat,audit=bank.adapt(terminal,items)
        assert flat[0]['category']=='UNPARSEABLE' and audit[0]['terminal_reason']==m.REASON
        # Replaying the cached failed chain never sends or sleeps again.
        assert bank.judge(items,dispatch)==terminal and len(sent)==3 and sleeps==[30,60]
    book,done=client.ledger.totals();assert len(book)==len(done)==3


@pytest.mark.parametrize('kind',['charged','402','unknown'])
def test_changed_failure_stops_no_extra_retry(tmp_path,monkeypatch,kind):
    api,p,io,bank,slots=setup(tmp_path,monkeypatch);sent=[]
    def send(wire):
        sent.append(wire)
        if len(sent)==1:return 200,error()['response']
        x=error(cost={'charged':.00001,'402':0,'unknown':None}[kind]);return (402 if kind=='402' else 200),x['response']
    client=api.Client(tmp_path/'E79_ARM_B/ledger','synthetic',send=send)
    with m.installed(bank,sleep=lambda _:None,clock=lambda:0,verify_source=False):
        bank.patch_api(api,io,'E79_ARM_B')
        if kind=='unknown':
            with pytest.raises(ValueError,match='known charge settled'):client.one('stage',[dict(id='opaque')])
            assert len(sent)==2
            return
        result=client.one('stage',[dict(id='opaque')])
        assert len(sent)==2
        saved=read(client.root/'stage'/(result['id']+'.response.json'))
        with pytest.raises((ValueError,TypeError,__import__('decimal').InvalidOperation)):
            bank.audit_response(saved,p)


@pytest.mark.parametrize('trigger',['pause','expiry'])
def test_expiry_and_shared_credit_pause_during_backoff_prevent_send(tmp_path,monkeypatch,trigger):
    api,p,io,bank,slots=setup(tmp_path,monkeypatch);sent=[]
    def send(wire):sent.append(wire);return 200,error()['response']
    clock=[0]
    def pause(delay):
        if trigger=='pause':write(tmp_path/'PAUSED_402.json',dict(paused=True))
        else:clock[0]=m.EXPIRY
    client=api.Client(tmp_path/'E79_ARM_B/ledger','synthetic',send=send)
    with m.installed(bank,sleep=pause,clock=lambda:clock[0],verify_source=False):
        bank.patch_api(api,io,'E79_ARM_B')
        with pytest.raises(ValueError,match='shared402pause|standing authorization expired'):client.one('stage',[dict(id='opaque')])
    assert len(sent)==1



def test_final_seal_binds_prospective_transport_source_and_diagnostic(tmp_path,monkeypatch):
    api,p,io,bank,slots=setup(tmp_path,monkeypatch)
    source=tmp_path/'source';source.mkdir();write(source/'SOURCE_SEAL.json',dict(synthetic=True));monkeypatch.setattr(m,'HERE',source)
    seal=tmp_path/'E79_ARM_B/judgments/JUDGMENT_SEAL.json'
    with m.installed(bank,verify_source=False):write(seal,dict(files={}))
    receipt=read(seal)
    assert receipt['transport217c2_finalized'] is True
    assert receipt['transport217c2_source_seal_sha256']==sha(source/'SOURCE_SEAL.json')
    assert receipt['files']['TRANSPORT217C2.json']==sha(seal.parent/'TRANSPORT217C2.json')
