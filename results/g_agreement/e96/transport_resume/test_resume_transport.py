import json
from decimal import Decimal
from pathlib import Path
import pytest
from projects.g_agreement.e96 import resume_transport as rt
from projects.g_agreement.e96.judge import ROOT
from projects.g_agreement.understand.blind_judge.run import route_modules

@pytest.fixture
def fixture(tmp_path,monkeypatch):
 api,privacy,protocol,io=route_modules(json.loads((ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json').read_text()))
 monkeypatch.setattr(api.Client,'one',api.Client.one);monkeypatch.setattr(io,'digest',io.digest)
 monkeypatch.setattr(api,'CAP',Decimal('1'));monkeypatch.setattr(api.P,'payload',lambda stage,items,taxonomy=None:{'max_tokens':64,'items':items});monkeypatch.setattr(api.P,'validate',lambda stage,value,items,taxonomy=None:value);monkeypatch.setattr(api.privacy,'check_wire',lambda *a:None);monkeypatch.setattr(rt.time,'sleep',lambda seconds:None)
 return api,protocol,io,tmp_path

def body(protocol,error=False,tokens=0,cost=0):
 choice={'finish_reason':'error' if error else 'stop','message':{'content':None if error else json.dumps({'ok':True})}}
 if error:choice['error']={'code':429,'metadata':{'error_type':'rate_limit_exceeded'}}
 return {'provider':protocol.PROVIDER_NAME,'model':protocol.MODEL,'usage':{'prompt_tokens':tokens,'completion_tokens':tokens,'total_tokens':tokens*2,'cost':cost},'choices':[choice]}

def test_success_cache_reused_and_error_gets_distinct_reserved_retry(fixture):
 api,protocol,io,root=fixture;sent=[];responses=[body(protocol,True),body(protocol,False,5,.0001)]
 client=api.Client(root,'dummy',send=lambda wire:(sent.append(wire) or (200,responses[len(sent)-1])))
 first=client.one('stage',[{'id':'x'}]);assert first['status']=='MISSING'
 original_response=(root/'stage'/(first['id']+'.response.json')).read_bytes()
 rt.patch_client(api,io,protocol);second=client.one('stage',[{'id':'x'}])
 assert second['status']=='OK' and second['id']==rt.retry_id(first['id'],1) and sent[0]==sent[1]
 assert (root/'stage'/(first['id']+'.response.json')).read_bytes()==original_response
 assert (root/'stage'/(first['id']+'.uncharged_rate_reconciliation.json')).exists()
 assert client.one('stage',[{'id':'x'}])==second and len(sent)==2
 book,done=client.ledger.totals();assert set(book)==done and len(book)==2

def test_charged_or_nonzero_output_errors_are_not_retried(fixture):
 api,protocol,io,root=fixture;sent=[];client=api.Client(root,'dummy',send=lambda wire:(sent.append(wire) or (200,body(protocol,True,1,.00001))))
 rt.patch_client(api,io,protocol);r=client.one('stage',[{'id':'charged'}]);assert r['status']=='MISSING' and len(sent)==1
 assert not list(root.rglob('*.uncharged_rate_reconciliation.json'))

def test_uncertain_reserved_retry_is_never_resent(fixture):
 api,protocol,io,root=fixture;sent=[];client=api.Client(root,'dummy',send=lambda wire:(sent.append(wire) or (200,body(protocol,True))))
 first=client.one('stage',[{'id':'x'}]);assert client.ledger.reserve(rt.retry_id(first['id'],1),Decimal('.01'))
 rt.patch_client(api,io,protocol)
 with pytest.raises(RuntimeError,match='uncertain'):client.one('stage',[{'id':'x'}])
 assert len(sent)==1

def test_max_four_identical_wire_retries(fixture):
 api,protocol,io,root=fixture;sent=[];client=api.Client(root,'dummy',send=lambda wire:(sent.append(wire) or (200,body(protocol,True))))
 rt.patch_client(api,io,protocol);r=client.one('stage',[{'id':'x'}]);assert r['status']=='MISSING' and len(sent)==5 and all(x==sent[0] for x in sent)
 assert len(list(root.rglob('*.response.json')))==5
 client.one('stage',[{'id':'x'}]);assert len(sent)==5

def test_runtime_changes_only_actual_response_id_audit():
 f,original,patched=rt.runtime();before="result=client.one(stage,batch);response=";after="result=client.one(stage,batch);rid=result['id'];response="
 assert patched.replace(after,before,1)==original
 assert f.__globals__['__file__']==str(ROOT/'projects/g_agreement/e96/judge.py')


def test_existing_e80_policy_ignores_incomplete_content_without_using_it(fixture):
 api,protocol,io,root=fixture
 saved={'http_status':200,'response':body(protocol,True)}
 saved['response']['choices'][0]['message']['content']='{"records":[{"incomplete_provider_payload":true}]}'
 assert rt.proven_uncharged_rate_error(saved,protocol)
 saved['response']['usage']['cost']=.00001
 assert not rt.proven_uncharged_rate_error(saved,protocol)
