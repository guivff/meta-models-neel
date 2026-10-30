import json,time
from decimal import Decimal
import pytest
from projects.g_agreement.e96 import resume_credit402 as c
from projects.g_agreement.e96.test_resume_transport import fixture,body

def error():return {'error':{'code':402,'metadata':{'reason':'in_flight_budget_exhausted','limit_source':'openrouter_in_flight_budget','provider_name':None,'headers':{'Retry-After':'120'}}}}

def test_exact_refusal_new_reservation_same_wire_and_cache(fixture,monkeypatch):
 api,p,io,root=fixture;sent=[];delays=[];monkeypatch.setattr(c.time,'sleep',lambda x:delays.append(x))
 cli=api.Client(root,'dummy',send=lambda w:(sent.append(w) or ((402,error()) if len(sent)==1 else (200,body(p,False,5,.0001)))))
 c.patch(api,io);r=cli.one('stage',[{'id':'x'}]);assert r['status']=='OK' and len(sent)==2 and sent[0]==sent[1]
 assert 119<=sum(delays)<=120 and not cli.latch.is_set()
 book,done=cli.ledger.totals();assert set(book)==done and len(book)==2
 assert len(list(root.rglob('*.preprovider402_reconciliation.json')))==1
 assert cli.one('stage',[{'id':'x'}])==r and len(sent)==2

@pytest.mark.parametrize('change',[{'id':'generation'}, {'provider':'provider'}, {'usage':{'cost':.01}}, {'choices':[{}]}])
def test_never_reconcile_possible_dispatch_or_charge(change):
 b=error();b.update(change);assert not c.proven({'http_status':402,'response':b})

def test_other402_is_never_retried(fixture):
 api,p,io,root=fixture;sent=[];b=error();b['error']['metadata']['limit_source']='openrouter_credits'
 cli=api.Client(root,'dummy',send=lambda w:(sent.append(w) or (402,b)));c.patch(api,io);assert cli.one('stage',[])['status']=='MISSING' and len(sent)==1
 book,done=cli.ledger.totals();assert set(book)!=done

def test_uncertain_retry_never_resent(fixture):
 api,p,io,root=fixture;sent=[];cli=api.Client(root,'dummy',send=lambda w:(sent.append(w) or (402,error())))
 first=cli.one('stage',[]);cli.ledger.reserve(c.retry_id(first['id'],1),Decimal('.01'));c.patch(api,io)
 with pytest.raises(RuntimeError,match='uncertain'):cli.one('stage',[])
 assert len(sent)==1

def test_four_retry_bound_preserves_all_refusals(fixture):
 api,p,io,root=fixture;sent=[];cli=api.Client(root,'dummy',send=lambda w:(sent.append(w) or (402,error())));c.patch(api,io)
 r=cli.one('stage',[]);assert r['status']=='MISSING' and len(sent)==5
 cli.one('stage',[]);assert len(sent)==5
