from types import SimpleNamespace
import pytest
from .wmech2_channel import response_audit,budget
from .later_runner import judge,classify
from .judgment_adapter402 import adapt_grid

def test_retry_keeps_batchmates_and_missing():
    items=[dict(id=str(i),readout='blue') for i in range(4)];calls=[]
    def send(batch,attempt):
        calls.append(([x['id'] for x in batch],attempt))
        return classify(batch,dict(records=[dict(id=x['id'],category='states_value',values=['A'],evidence='blue') for x in batch if x['id']!='1']))
    flat,_=adapt_grid(judge(items,send),items)
    assert calls==[(['0','1','2','3'],0),(['1'],1),(['1'],2)]
    assert flat[1]==dict(id='1',category='UNPARSEABLE',values=[],evidence='')

def test_actual_route_cost_and_completion():
    p=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER_NAME='Google')
    body=dict(model=p.MODEL,provider='Google',usage=dict(cost=.01),choices=[dict(finish_reason='stop')])
    assert response_audit(dict(http_status=200,response=body),p)['cost_usd']=='0.01'
    for patch in (dict(model='google/gemini-3.8-flash'),dict(provider='other'),dict(usage={}),dict(choices=[dict(finish_reason='length')])):
        with pytest.raises(Exception):response_audit(dict(http_status=200,response=body|patch),p)

def test_budget_requires_custody_and_global_envelope():
    entry=dict(experiment='E79',seal_sha256='abc')
    r=dict(issuer='integrator',verified=True,bank='E79',packet_seal_sha256='abc',forecast_and_custody_verified=True,
           reservation_included=True,allocation_usd=30,global_judging_committed_including_reservation_usd=100,allocation_authority='registered')
    assert budget(r,entry)==30
    for patch in (dict(reservation_included=False),dict(global_judging_committed_including_reservation_usd=501),dict(packet_seal_sha256='wrong')):
        with pytest.raises(ValueError):budget(r|patch,entry)

def test_end_to_end_runtime_receipt_with_simulated_provider(tmp_path,monkeypatch):
    # Real reserve/settle Client, synthetic content and provider; never sends a request.
    from . import wmech2_channel as c
    from projects.g_agreement.readerbench.io import write,read,sha
    original_modules=c.route_modules
    route_path=c.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'
    route=read(route_path)
    api,privacy,protocol,io=original_modules(route)
    real_client=api.Client
    def fake_send(wire):
        batch=__import__('json').loads(wire['messages'][1]['content'])
        return 200,dict(provider='Google',model=protocol.MODEL,usage=dict(cost=.001),choices=[dict(finish_reason='stop',message=dict(content=__import__('json').dumps(dict(records=[dict(id=x['id'],category='states_value',values=['A'],evidence='blue') for x in batch]))))])
    monkeypatch.setattr(api,'Client',lambda root,key:real_client(root,key,send=fake_send))
    def check_route(key):
        write(io.CACHE/'last_zdr_route_inventory.json',{'data':['synthetic route']});return ['synthetic route']
    monkeypatch.setattr(privacy,'check_route',check_route)
    monkeypatch.setattr(c,'route_modules',lambda route:(api,privacy,protocol,io))
    monkeypatch.setattr(c,'sources',lambda:None)
    monkeypatch.setattr(c,'LEDGER_BASE',tmp_path/'ledger')
    monkeypatch.setattr(c,'HERE',tmp_path)
    write(tmp_path/'SOURCE_SEAL.json',{'test':'synthetic only'})
    entry=dict(experiment='E79',seal_sha256='synthetic')
    item=dict(id='a'*32,readout='blue',rubric='property')
    monkeypatch.setattr(c,'admission',lambda bank:(entry,{'judgments':str(tmp_path/'out')},[item],'rubric',dict(affected=[],redacted_records=0)))
    monkeypatch.setenv('OPENROUTER_API_KEY','synthetic-test-placeholder')
    receipt=tmp_path/'receipt.json'
    write(receipt,dict(issuer='integrator',verified=True,bank='E79',packet_seal_sha256='synthetic',forecast_and_custody_verified=True,
        reservation_included=True,allocation_usd=1,global_judging_committed_including_reservation_usd=1,allocation_authority='synthetic'))
    c.run('E79',receipt)
    seal=read(tmp_path/'out/JUDGMENT_SEAL.json')
    assert seal['route_verified'] and seal['redaction_audit_complete'] and seal['redacted_opaque_ids']==[]
    for name,digest in seal['files'].items():assert sha(tmp_path/'out'/name)==digest
    assert read(tmp_path/'out/COUNTS.json')['cost']['unresolved_reserve_usd']=='0'

def test_d5_terminal_missing_is_not_a_category():
    from .wmech2_channel import terminal_grid
    items=[dict(id='a',readout='blue'),dict(id='b',readout='blue')]
    t=[dict(id='a',status='KEPT',attempts=0,code=dict(id='a',category='topic_content',evidence='blue')),
       dict(id='b',status='UNPARSEABLE',attempts=2,code=None)]
    flat,_=terminal_grid(t,items,'D5')
    assert flat[1]==dict(id='b',category='UNPARSEABLE',evidence='') and 'values' not in flat[0]
