import json
from decimal import Decimal
import pytest
from projects.g_agreement.e96 import resume_funded212 as f
from projects.g_agreement.e96.test_resume_transport import fixture,body

def setup_case(api,io,root,monkeypatch):
 stage=root/f.STAGE;stage.mkdir();wire=api.P.payload(f.STAGE,[{'id':'x'}],None)
 b={'http_status':402,'response':{'error':{'code':402,'metadata':{'limit_source':'openrouter_credits','provider_name':None}}}}
 p=stage/(f.REFUSAL+'.response.json');p.write_text(json.dumps(b));monkeypatch.setattr(f,'RESPONSE_SHA',f.digest(p))
 (stage/(f.REFUSAL+'.request.json')).write_text(json.dumps({'wire':wire}));(stage/(f.REFUSAL+'.result.json')).write_text(json.dumps({'id':f.REFUSAL,'status':'MISSING','reason':'HTTP_402'}));monkeypatch.setattr(io,'digest',lambda value:f.REFUSAL)
 return stage

def test_identical_wire_single_new_reservation_cache_preserved(fixture,monkeypatch):
 api,p,io,root=fixture;stage=setup_case(api,io,root,monkeypatch);sent=[];cli=api.Client(root,'dummy',send=lambda w:(sent.append(w) or (200,body(p,False,5,.0001))));cli.ledger.reserve(f.REFUSAL,Decimal('.01'));cli.ledger.settle(f.REFUSAL,0);old=(stage/(f.REFUSAL+'.response.json')).read_bytes();f.patch(api,io)
 r=cli.one(f.STAGE,[{'id':'x'}]);assert r['status']=='OK' and r['id']==f.RETRY and len(sent)==1
 assert cli.one(f.STAGE,[{'id':'x'}])==r and len(sent)==1 and (stage/(f.REFUSAL+'.response.json')).read_bytes()==old

def test_uncertain_funded_retry_never_resent(fixture,monkeypatch):
 api,p,io,root=fixture;setup_case(api,io,root,monkeypatch);cli=api.Client(root,'dummy',send=lambda w:pytest.fail('send'));cli.ledger.reserve(f.REFUSAL,Decimal('.01'));cli.ledger.settle(f.REFUSAL,0);cli.ledger.reserve(f.RETRY,Decimal('.01'));f.patch(api,io)
 with pytest.raises(RuntimeError,match='uncertain'):cli.one(f.STAGE,[{'id':'x'}])

def test_changed_response_rejected(fixture,monkeypatch):
 api,p,io,root=fixture;stage=setup_case(api,io,root,monkeypatch);(stage/(f.REFUSAL+'.response.json')).write_text('{}')
 with pytest.raises(ValueError,match='exact saved'):f.check_response(stage)

def test_changed_wire_never_sent(fixture,monkeypatch):
 api,p,io,root=fixture;setup_case(api,io,root,monkeypatch);cli=api.Client(root,'dummy',send=lambda w:pytest.fail('send'));cli.ledger.reserve(f.REFUSAL,Decimal('.01'));cli.ledger.settle(f.REFUSAL,0);f.patch(api,io)
 with pytest.raises(ValueError,match='wire changed'):cli.one(f.STAGE,[{'id':'different'}])
