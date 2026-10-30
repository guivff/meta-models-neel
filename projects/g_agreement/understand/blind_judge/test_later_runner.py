import json
from decimal import Decimal
import pytest
from . import later_runner as m
from .run import route_modules, payload
from projects.g_agreement.readerbench.io import read


def item(i):return dict(id=f'{i:032x}',rubric='A means cat; B means dog.',readout='A “Cat” — DOG')
def code(i,good=True):return dict(id=f'{i:032x}',category='states_value',values=['A','B'],evidence='a "cat" - dog' if good else 'absent')


def test_keep_batch_mates_and_singleton_retries():
    calls=[]
    def send(xs,attempt):
        calls.append(([x['id'] for x in xs],attempt))
        return m.classify(xs,dict(records=[code(int(x['id'],16),int(x['id'],16)!=1 or attempt==2) for x in xs]))
    out=m.judge([item(i) for i in range(4)],send)
    assert len(calls)==3 and calls[1:]==[([item(1)['id']],1),([item(1)['id']],2)]
    assert all(x['status']=='KEPT' for x in out)
    assert out[1]['attempts']==2 and out[0]['attempts']==0
    assert out[0]['code']['values']==['A','B']


def test_exhaustion_and_duplicate_ids():
    out=m.judge([item(1)],lambda xs,a:m.classify(xs,{}))
    assert out==[dict(id=item(1)['id'],status='UNPARSEABLE',code=None,attempts=2)]
    assert m.classify([item(1)],dict(records=[code(1),code(1)]))[0]['status']=='INVALID'


def test_forecast_precedes_any_packet_access(monkeypatch):
    calls=[]
    def gate(*args):calls.append('forecast');raise ValueError('forecast absent')
    monkeypatch.setattr(m,'forecast_gate',gate)
    monkeypatch.setattr(m,'read',lambda p:pytest.fail('read before forecast'))
    spec=dict(bank='E57',forecast_repo='none',forecast_commit='x',forecast_path='x',forecast_sha256='x')
    with pytest.raises(ValueError,match='forecast absent'):m.admission(spec)
    assert calls==['forecast']
    spec['bank']='E61'
    with pytest.raises(ValueError,match='unsupported judging bank'):m.admission(spec)


def test_actual_transport_offline_route_ledger_and_duplicate(tmp_path,monkeypatch):
    import sys
    for name in list(sys.modules):
        if name.startswith("_authorized_e10_judge"):monkeypatch.delitem(sys.modules,name)
    route=read(m.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    api,privacy,p,io=route_modules(route);api.CAP=Decimal('15')
    wire=payload([item(1)],'frozen rubric','E56',p)
    assert wire['model']=='google/gemini-3.1-flash-lite'
    assert wire['provider']['only']==['google-vertex/global']
    assert wire['provider']['zdr'] is True and wire['provider']['data_collection']=='deny'
    assert wire['provider']['allow_fallbacks'] is False
    p.payload=lambda *args:wire
    p.validate=lambda stage,result,batch,taxonomy=None:m.classify(batch,result)
    original=privacy.check_wire
    privacy.check_wire=lambda stage,batch,w,taxonomy=None:original('extract',[dict(id=x['id'],readout=x['readout']) for x in batch],w)
    sent=[]
    def fake(w):
        sent.append(w)
        return 200,dict(provider=p.PROVIDER_NAME,model=p.MODEL,usage=dict(cost=.001),
                        choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(records=[code(1)]))))])
    client=api.Client(tmp_path/'ledger','fake-test-only',send=fake)
    result=client.one('E57',[item(1)])
    assert result['status']=='OK' and client.one('E57',[item(1)])==result and len(sent)==1
    assert client.ledger.summary()['actual_usd']=='0.001'
    assert client.ledger.reserve('fills-cap',Decimal('14.999'))
    assert not client.ledger.reserve('over-cap',Decimal('.0001'))


def test_s6_schema_evidence_and_value_isolation():
    x=dict(id='a'*32,readout='This is a “TEST”.')
    c=dict(id=x['id'],eval_mention=True,evidence='a "test"')
    assert m.classify([x],dict(records=[c]),'S6')[0]['status']=='KEPT'
    for change in [dict(eval_mention='true'),dict(evidence=''),dict(category='states_value'),dict(evidence='benchmark')]:
        assert m.classify([x],dict(records=[dict(c,**change)]),'S6')[0]['status']=='INVALID'
    silent=dict(id=x['id'],eval_mention=False,evidence='')
    assert m.classify([x],dict(records=[silent]),'S6')[0]['status']=='KEPT'
    assert m.classify([x],dict(records=[silent]),'E56')[0]['status']=='INVALID'
    from types import SimpleNamespace
    p=SimpleNamespace(MODEL='m',PROVIDER='p')
    w=m.channel_payload([x],'frozen S6','S6',p)
    fields=w['response_format']['json_schema']['schema']['properties']['records']['items']['properties']
    assert set(fields)=={'id','eval_mention','evidence'}
    assert set(json.loads(w['messages'][1]['content'])[0])=={'id','readout'}


def test_rp2_uses_only_d5_categories():
    from types import SimpleNamespace
    p=SimpleNamespace(MODEL='m',PROVIDER='p')
    x=dict(id='b'*32,readout='A topic about cats')
    c=dict(id=x['id'],category='topic_content',evidence='cats')
    assert m.classify([x],dict(records=[c]),'D5')[0]['status']=='KEPT'
    assert m.classify([x],dict(records=[c]),'E56')[0]['status']=='INVALID'
    w=m.channel_payload([x],'frozen D5','D5',p)
    fields=w['response_format']['json_schema']['schema']['properties']['records']['items']['properties']
    assert 'values' not in fields and 'structural_value' in fields['category']['enum']
    assert set(json.loads(w['messages'][1]['content'])[0])=={'id','readout'}


@pytest.mark.parametrize('bank,channel,taxonomy,n',[('E59','value','E56',2),('E62','eval','S6',2),('E63','rp2','D5',400)])
def test_sealed_channel_admission(tmp_path,monkeypatch,bank,channel,taxonomy,n):
    from projects.g_agreement.readerbench.io import write,sha,seal_output
    gate=dict(bank_seal_sha256='b',capture_seal_sha256='c',forecast_sha256='f')
    monkeypatch.setattr(m,'forecast_gate',lambda *args:gate)
    monkeypatch.setattr(m,'coordinator_gate',lambda *args:gate)
    monkeypatch.setattr(m,'budget_gate',lambda x:True)
    rubric=tmp_path/'rubric';rubric.write_text('synthetic frozen rubric')
    if taxonomy=='S6':monkeypatch.setattr(m,'S6_RUBRIC_SHA',sha(rubric))
    else:monkeypatch.setattr(m,'RUBRIC_HASHES',dict(m.RUBRIC_HASHES,**{taxonomy:sha(rubric)}))
    source=tmp_path/'source';source.mkdir();write(source/'DATA.json',{});seal_output(source,{})
    packet=tmp_path/'packet';packet.mkdir()
    xs=[dict(id=f'{i:032x}',property='pet',values={'A':'cat','B':'dog'},readout='synthetic') if taxonomy=='E56' else dict(id=f'{i:032x}',readout='synthetic') for i in range(n)]
    name='EVAL_PACKET.json' if taxonomy=='S6' else 'JUDGE_PACKET.json'
    write(packet/'JUDGE_PACKET.json',xs if name=='JUDGE_PACKET.json' else [])
    if taxonomy=='S6':write(packet/name,xs)
    write(packet/'BLIND_SEAL.json',dict(experiment=bank,rubric_sha256=sha(rubric),eval_rubric_sha256=sha(rubric),
          files={p.name:sha(p) for p in packet.iterdir()}))
    receipt=tmp_path/'receipt';budget=tmp_path/'budget';write(budget,{})
    rc=dict(gate,issuer='integrator',verified=True,bank=bank,n=n,packet_seal_sha256=sha(packet/'BLIND_SEAL.json'),
            source_seals=[dict(path=str(source/'RESULT_SEAL.json'),sha256=sha(source/'RESULT_SEAL.json'))],
            per_reader_counts={'oracle':200,'nla':200},sampling_seed=20261027,sampling_without_replacement=True)
    write(receipt,rc)
    spec=dict(bank=bank,channel=channel,forecast_repo='',forecast_commit='',forecast_path='',forecast_sha256='f',
              budget_receipt=str(budget),budget_receipt_sha256=sha(budget),receipt=str(receipt),receipt_sha256=sha(receipt),
              packet=str(packet),packet_seal_sha256=sha(packet/'BLIND_SEAL.json'),rubric=str(rubric))
    from .judgment_adapter402 import render_record
    assert m.admission(spec)[0]==([render_record(x,rubric.read_text()) for x in xs] if taxonomy=='E56' else xs)
    write(packet/name,xs[:-1])
    with pytest.raises(ValueError):m.admission(spec)
