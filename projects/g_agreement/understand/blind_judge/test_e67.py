import json
from types import SimpleNamespace
import pytest
from . import e67
from . import later_runner as r


def item():return dict(id='a'*32,prompt='A synthetic cat sits.',readout='There is a cat.',rubric='Frozen claims rubric')
def code():return dict(id='a'*32,claims=[dict(claim='The input contains a cat.',verdict='SUPPORTED')],generic=False)


def test_claim_schema_and_generic():
    x=item();c=code();e67.validate_code(c,x)
    e67.validate_code(dict(c,claims=[],generic=True),x)
    for bad in [dict(c,claims=c['claims']*6),dict(c,generic=True),dict(c,claims=[]),
                dict(c,claims=[dict(claim='x',verdict='TRUE')]),dict(c,reader='oracle')]:
        with pytest.raises(ValueError):e67.validate_code(bad,x)
    assert r.classify([x],dict(records=[c]),'E67')[0]['status']=='KEPT'


def test_wire_and_same_retry_rules():
    x=item();w=r.channel_payload([x],x['rubric'],'E67',SimpleNamespace(MODEL='m',PROVIDER='p'))
    assert json.loads(w['messages'][1]['content'])==[x]
    fields=w['response_format']['json_schema']['schema']['properties']['records']['items']['properties']
    assert set(fields)=={'id','claims','generic'} and fields['claims']['maxItems']==5
    calls=[]
    def send(xs,attempt):
        calls.append(attempt);return r.classify(xs,dict(records=[dict(code(),generic=True)]),'E67')
    out=r.judge([x],send)
    assert calls==[0,1,2] and out[0]['status']=='UNPARSEABLE' and out[0]['code'] is None


def test_source_gate_before_packet_access(tmp_path):
    from projects.g_agreement.readerbench.io import write,sha
    b=tmp_path/'budget';write(b,dict(issuer='integrator',verified=True,bank='E67',date_zurich='2026-10-27',
        reservation_included=True,allocation_id='separate',reserved_judging_usd='5',daily_committed_including_reservation_usd='232.16'))
    c=tmp_path/'receipt';write(c,dict(issuer='integrator',verified=True,experiment='E67',separate_shuffled_packets=True,packet_id='packet_0',analysis_seals=[]))
    spec=dict(bank='E67',packet_id='packet_0',budget_receipt=str(b),budget_receipt_sha256=sha(b),receipt=str(c),receipt_sha256=sha(c))
    with pytest.raises(ValueError,match='source analyses'):e67.admission(spec)
    d=json.loads(b.read_text());d['reserved_judging_usd']='15';write(b,d);spec['budget_receipt_sha256']=sha(b)
    with pytest.raises(ValueError,match='USD5'):e67.admission(spec)


@pytest.mark.parametrize("wave", [1,2])
def test_dispatch_isolated_five_dollar_ledger(tmp_path,monkeypatch,wave):
    import sys
    from decimal import Decimal
    from projects.g_agreement.readerbench.io import read,write,sha
    for name in list(sys.modules):
        if name.startswith('_authorized_e10_judge'):monkeypatch.delitem(sys.modules,name)
    route=read(r.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    api,privacy,p,io=r.route_modules(route)
    monkeypatch.setattr(r,'route_modules',lambda route:(api,privacy,p,io))
    monkeypatch.setattr(r,'LEDGER',tmp_path/'e67_only')
    proof=tmp_path/'proof';write(proof,dict(verified_at='synthetic',private_input_output_logging=False,openrouter_use_inputs_outputs=False))
    route=dict(route,privacy_proof=str(proof),privacy_proof_sha256=sha(proof))
    monkeypatch.setattr(privacy,'check_route',lambda key:None)
    sent=[]
    class Response:
        status_code=200
        def json(self):return dict(provider=p.PROVIDER_NAME,model=p.MODEL,usage=dict(cost=.001),choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(records=[code()]))))])
    def post(url,**kw):sent.append(kw['json']);return Response()
    monkeypatch.setattr(api.requests,'post',post)
    r.dispatch(dict(bank='E67',channel='claims',wave=wave,packet_id='packet_0',packet_seal_sha256='synthetic'),[item()],item()['rubric'],route,'synthetic-test-only')
    assert api.CAP==Decimal('5') and len(sent)==1
    assert sent[0]['provider']['only']==['google-vertex/global'] and sent[0]['provider']['zdr'] is True
    book=api.Ledger(r.LEDGER/'ledger.jsonl')
    assert book.reserve('fills-cap',Decimal('4.999')) and not book.reserve('over-cap',Decimal('.001'))
    job='E67_packet_0_judgments' if wave==1 else 'E67_wave_2_packet_0_judgments'
    assert (r.LEDGER/job/'RESULT_SEAL.json').exists()
    assert read(r.LEDGER/job/'RESULT_SEAL.json')['wave']==wave


def test_wave_ledgers_share_remaining_total(tmp_path,monkeypatch):
    from decimal import Decimal
    from projects.g_agreement.readerbench.io import read
    monkeypatch.setattr(e67,'LEDGER',tmp_path/'e67_5usd')
    route=read(r.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    api,_,_,_=r.route_modules(route);api.CAP=Decimal('5')
    first=api.Ledger(e67.wave_ledger(1)/'ledger.jsonl')
    assert first.reserve('wave1',Decimal('.42'))
    assert e67.remaining_cap(api,2)==Decimal('4.58')
    api.CAP=e67.remaining_cap(api,2)
    second=api.Ledger(e67.wave_ledger(2)/'ledger.jsonl')
    assert second.reserve('wave2',Decimal('4.58'))
    assert not second.reserve('extra',Decimal('.001'))
    assert e67.remaining_cap(api,1)==Decimal('.42')
    assert e67.wave_number({})==1
    for bad in (0,3,True,'2'):
        with pytest.raises(ValueError):e67.wave_number(dict(wave=bad))
