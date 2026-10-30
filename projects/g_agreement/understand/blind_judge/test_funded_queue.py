import json
import pytest
from . import funded_queue as q
from projects.g_agreement.readerbench.io import write,read,sha

def test402_persists_pause_and_preserves_evidence(tmp_path,monkeypatch):
    monkeypatch.setattr(q,'CACHE',tmp_path)
    r=tmp_path/'response.json';write(r,dict(http_status=402,response={'error':{'code':402}}))
    with pytest.raises(q.CreditPause):q.credit_gate(read(r),r,'E87','stage','a'*64)
    assert read(tmp_path/'PAUSED_402.json')['response_sha256']==sha(r)
    assert read(tmp_path/'PAUSED_402.json')['retry'] is False

def test_queue_never_starts_next_bank_after402(tmp_path,monkeypatch):
    monkeypatch.setattr(q,'CACHE',tmp_path);monkeypatch.setattr(q,'HERE',tmp_path);monkeypatch.setattr(q,'source_gate',lambda:None)
    write(tmp_path/'SOURCE_SEAL.json',{'fixture':True});write(tmp_path/'BANK_INPUTS.json',{'fixture':True})
    write(tmp_path/'ADMISSION.json',dict(source_seal_sha256=sha(tmp_path/'SOURCE_SEAL.json'),inputs_sha256=sha(tmp_path/'BANK_INPUTS.json')))
    monkeypatch.setenv('OPENROUTER_API_KEY','synthetic-test-only');calls=[]
    def execute(bank,a,key):calls.append(bank);raise q.CreditPause('fixture')
    monkeypatch.setattr(q,'execute_bank',execute)
    with pytest.raises(q.CreditPause):q.run()
    assert calls==['E87'] and read(tmp_path/'QUEUE_STATUS.json')['status']=='PAUSED_402'

def test402_latch_prevents_any_dispatch_on_restart(tmp_path,monkeypatch):
    monkeypatch.setattr(q,'CACHE',tmp_path);monkeypatch.setattr(q,'HERE',tmp_path);monkeypatch.setattr(q,'source_gate',lambda:None)
    write(tmp_path/'SOURCE_SEAL.json',{});write(tmp_path/'BANK_INPUTS.json',{})
    write(tmp_path/'ADMISSION.json',dict(source_seal_sha256=sha(tmp_path/'SOURCE_SEAL.json'),inputs_sha256=sha(tmp_path/'BANK_INPUTS.json')))
    write(tmp_path/'PAUSED_402.json',{'fixture':True})
    monkeypatch.setattr(q,'execute_bank',lambda *args:pytest.fail('must not dispatch'))
    with pytest.raises(ValueError,match='credit pause'):q.run()
