import json
from decimal import Decimal
from . import parallel_funded as m
from .run import route_modules
from projects.g_agreement.readerbench.io import read,write

def test_shared429_reduces_total_throughput(tmp_path,monkeypatch):
    monkeypatch.setattr(m.f,'CACHE',tmp_path)
    m.rate_limited('E100');first=read(tmp_path/'THROUGHPUT.json')
    m.rate_limited('E87');second=read(tmp_path/'THROUGHPUT.json')
    assert first['interval_seconds']==2 and second['interval_seconds']==4
    assert second['rate_limits']==2 and second['last_rate_limited_bank']=='E87'

def test429_retry_own_reservation_and_unchanged_wire(tmp_path,monkeypatch):
    api,privacy,p,io=route_modules(read(m.f.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'))
    monkeypatch.setattr(api,'CAP',Decimal('1'))
    monkeypatch.setattr(p,'payload',lambda *a:dict(max_tokens=64,items=[{'id':'test'}]))
    monkeypatch.setattr(p,'validate',lambda stage,value,batch,unused=None:value)
    monkeypatch.setattr(privacy,'check_wire',lambda *a:None)
    monkeypatch.setattr(io,'digest',io.digest);monkeypatch.setattr(api.Client,'one',api.Client.one)
    slots=[];cool=[];monkeypatch.setattr(m,'claim_slot',slots.append);monkeypatch.setattr(m,'rate_limited',cool.append)
    sent=[]
    def send(wire):
        sent.append(wire)
        if len(sent)==1:return 429,dict(error={'code':429})
        return 200,dict(provider=p.PROVIDER_NAME,model=p.MODEL,usage=dict(cost=.0001),choices=[dict(finish_reason='stop',message=dict(content='{"ok":true}'))])
    m.patch_api(api,io,'E100');client=api.Client(tmp_path,'synthetic',send=send)
    result=client.one('stage',[{'id':'test'}])
    assert result['status']=='OK' and sent[0]==sent[1] and slots==['E100','E100'] and cool==['E100']
    book,done=client.ledger.totals();assert len(book)==2 and len(done)==1
    result2=client.one('stage',[{'id':'test'}]);assert result2==result and len(sent)==2


def test_pacing_contention_waits_instead_of_stopping_bank(tmp_path,monkeypatch):
    import time
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(m.f,'CACHE',tmp_path)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with m.pacing_lock():
            pending=pool.submit(m.claim_slot,'E100')
            time.sleep(.05)
            assert not pending.done()
        pending.result(timeout=2)
    assert read(tmp_path/'THROUGHPUT.json')['bank_sends']=={'E100':1}
