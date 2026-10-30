import json
import sys
from decimal import Decimal
import pytest

from projects.g_agreement.readerbench.io import read,sha,write
from . import channels81_86 as c
from . import later_runner as r
from .test_cap_ledger import fixture as cap_fixture


def fixture(tmp_path, bank):
    src=tmp_path/'source';src.mkdir()
    rows=[dict(id=f'{j:032x}',readout='Models may be graded — here.') for j in range(4)]
    if bank!='E85':
        for row in rows:row.update(property='answer',values={'A':'true answer','B':'wrong answer'})
    p=src/'JUDGE_PACKET.json';write(p,rows)
    rubric=c.rubric_path(bank)
    seal=src/'BLIND_SEAL.json';write(seal,dict(experiment=bank,n=4,complete=True,
        rubric_sha256=sha(rubric),files={p.name:sha(p)},value_order='truth_then_lie',
        behaviour_gate_verified=True,real_agent_dataset_gate_verified=True))
    spec=dict(bank=bank,source_seal=str(seal),source_seal_sha256=sha(seal),
              source_packet=str(p),rubric=str(rubric));return spec,rows


@pytest.mark.parametrize('bank',sorted(c.BANKS))
def test_format_only_and_source_binding(tmp_path,bank):
    spec,rows=fixture(tmp_path,bank);out=tmp_path/'converted';c.convert(spec,out)
    assert read(out/'PACKET.json')==rows
    assert (out/'RUBRIC.txt').read_bytes()==c.rubric_path(bank).read_bytes()
    assert all(a['id'].encode()==b['id'].encode() and a['readout'].encode()==b['readout'].encode()
               for a,b in zip(rows,read(out/'PACKET.json')))
    with pytest.raises(FileExistsError):c.convert(spec,out)
    with open(spec['source_packet'],'ab') as f:f.write(b' ')
    with pytest.raises(ValueError,match='sealed source'):c.convert(spec,tmp_path/'bad')


@pytest.mark.parametrize('bank',sorted(c.BANKS))
def test_gates_before_packet_and_blind_wire(tmp_path,bank):
    spec,rows=fixture(tmp_path,bank);out=tmp_path/'converted';c.convert(spec,out)
    budget=tmp_path/'budget.json';write(budget,dict(issuer='integrator',verified=True,bank=bank,
        allocation_id='allocation',reservation_included=True,date_zurich='2026-10-28',
        reserved_judging_usd=1,
        daily_committed_including_reservation_usd=270))
    receipt=tmp_path/'receipt.json';write(receipt,dict(issuer='integrator',verified=True,bank=bank,
        authority=c.AUTHORITY[bank],forecast_gate_verified=True,bank_gate_verified=True,n=4,
        packet_seal_sha256=sha(out/'PACKET_SEAL.json'),
        source_seals=[dict(path=spec['source_seal'],sha256=spec['source_seal_sha256'])]))
    job=dict(bank=bank,channel='eval' if bank=='E85' else 'value',budget_receipt=str(budget),
        budget_receipt_sha256=sha(budget),receipt=str(receipt),receipt_sha256=sha(receipt),
        packet=str(out),packet_seal_sha256=sha(out/'PACKET_SEAL.json'),**cap_fixture(tmp_path,bank,'.34'))
    wire,rubric=r.admission(job)
    assert len(wire)==4 and all(set(x)==({'id','readout'} if bank=='E85' else {'id','readout','rubric'}) for x in wire)
    if bank=='E86':assert all('A: true answer\nB: wrong answer' in x['rubric'] for x in wire)
    if bank=='E85':
        good=dict(id=wire[0]['id'],eval_mention=True,evidence='Models may be graded')
        assert r.classify(wire[:1],dict(records=[good]),'S6')[0]['status']=='KEPT'
        assert r.classify(wire[:1],dict(records=[dict(good,evidence='absent')]),'S6')[0]['status']=='INVALID'
    write(receipt,dict(read(receipt),forecast_gate_verified=False))
    job['receipt_sha256']=sha(receipt)
    with pytest.raises(ValueError,match='forecast'):r.admission(job)
    write(budget,dict(read(budget),reserved_judging_usd=200))
    job['budget_receipt_sha256']=sha(budget)
    with pytest.raises(ValueError,match='cap'):r.admission(job)


def test_actual_mock_route_e85(tmp_path,monkeypatch):
    for name in list(sys.modules):
        if name.startswith('_authorized_e10_judge'):monkeypatch.delitem(sys.modules,name)
    route=read(r.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    api,privacy,p,io=r.route_modules(route)
    monkeypatch.setattr(r,'route_modules',lambda route:(api,privacy,p,io))
    monkeypatch.setattr(r,'LEDGER',tmp_path/'e85_judging')
    proof=tmp_path/'proof';write(proof,dict(verified_at='synthetic',private_input_output_logging=False,
                                            openrouter_use_inputs_outputs=False))
    route=dict(route,privacy_proof=str(proof),privacy_proof_sha256=sha(proof))
    monkeypatch.setattr(privacy,'check_route',lambda key:None)
    sent=[];item=dict(id='a'*32,readout='Model is being tested at /tmp/synthetic.txt')
    class Response:
        status_code=200
        def json(self):
            amended='E85 §202' in sent[-1]['messages'][0]['content']
            code=(dict(id=item['id'],eval_mention=True,genre_vocabulary=False,
                       evidence={'self':'Model is being tested','genre':''}) if amended else
                  dict(id=item['id'],eval_mention=True,evidence='Model is being tested'))
            return dict(provider=p.PROVIDER_NAME,model=p.MODEL,usage=dict(cost=.001),
            choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(records=[
                code]))))])
    monkeypatch.setattr(api.requests,'post',lambda url,**kw:(sent.append(kw['json']) or Response()))
    from . import cap_ledger
    from .privacy79 import redact
    monkeypatch.setattr(cap_ledger,'CACHE',tmp_path)
    rubric=c.rubric_path('E85').read_text()
    cleaned,_=redact([item],'E85',addresses=True)
    original=(c.HERE/'E85_RUBRIC.txt').read_text()
    bounded=api.upper(r.channel_payload(cleaned,rubric,'E85_202',p))
    bounded+=api.upper(r.channel_payload(cleaned,original,'S6',p))
    packet=tmp_path/'packet';packet.mkdir();write(packet/'ORIGINAL_IDS.json',[item['id']])
    spec=dict(bank='E85',channel='eval',packet_seal_sha256='test',
              packet=str(packet),
              **cap_fixture(tmp_path,'E85',str(bounded)))
    r.dispatch(spec,[item],
               c.rubric_path('E85').read_text(),route,'synthetic-test-only')
    assert api.CAP==1 and len(sent)==2
    assert set(json.loads(sent[0]['messages'][1]['content'])[0])=={'id','readout'}
    assert '[REDACTED_PATH]' in sent[0]['messages'][1]['content']
    assert sent[0]['provider']['zdr'] and not sent[0]['provider']['allow_fallbacks']
    assert read(r.LEDGER/'E85_eval_judgments/COUNTS.json')['kept']==1
