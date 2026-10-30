import json
import sys
from decimal import Decimal
import pytest
from projects.g_agreement.readerbench.io import read,write,sha,verify
from . import channels66_68 as c
from . import later_runner as r
from .test_cap_ledger import fixture as cap_fixture


def fixture(tmp_path,bank):
    n=c.COUNTS[bank] or 3;src=tmp_path/'source';src.mkdir()
    rows=[dict(id=f'{i:032x}',readout='  “é”\r\nopen bracket — topic\t') for i in range(n)]
    if bank in ('E68','E76'):
        for x in rows:x.update(property='property\r\n',values={'A':['a','é'],'B':'b'})
    p=src/('BLIND_PACKET.jsonl' if bank=='E66' else 'JUDGE_PACKET.json')
    p.write_bytes(('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n').encode() if bank=='E66' else json.dumps(rows,ensure_ascii=False).encode())
    s=src/'SEAL.json';rubric=c.rubric_path(bank)
    write(s,dict(n=n,status='BLIND_PACKET_READY',packet_sha256=sha(p)) if bank=='E66' else dict(experiment=bank,rubric_sha256=sha(rubric),files={p.name:sha(p)}))
    return dict(bank=bank,source_seal=str(s),source_seal_sha256=sha(s),source_packet=str(p),rubric=str(rubric)),rows


@pytest.mark.parametrize('bank',['E66','E68','E76'])
def test_conversion_preserves_frozen_records_and_rubric(tmp_path,bank):
    spec,rows=fixture(tmp_path,bank);out=tmp_path/'out';c.convert(spec,out)
    assert read(out/'PACKET.json')==rows
    assert (out/'RUBRIC.txt').read_bytes()==c.rubric_path(bank).read_bytes()
    verify(out/'PACKET_SEAL.json',sha(out/'PACKET_SEAL.json'))
    with pytest.raises(FileExistsError):c.convert(spec,out)
    with open(spec['source_packet'],'ab') as f:f.write(b' ')
    with pytest.raises(ValueError,match='packet hash'):c.convert(spec,tmp_path/'bad')
    assert not (tmp_path/'bad').exists()


def code66(item):
    return dict(id=item['id'],**{q:False for q in c.QUESTIONS},evidence={q:'' for q in c.QUESTIONS})


def test_six_questions_validation_and_individual_retry():
    items=[dict(id='a'*32,readout='Open “bracket”'),dict(id='b'*32,readout='other')]
    good=code66(items[0]);good['S2']=True;good['evidence']['S2']='open "bracket"'
    response={'records':[good,{'id':items[1]['id']}]}
    states=r.classify(items,response,'E66');assert [x['status'] for x in states]==['KEPT','INVALID']
    sent=[]
    def send(batch,attempt):
        sent.append(([x['id'] for x in batch],attempt))
        return r.classify(batch,response if attempt==0 else {},'E66')
    result=r.judge(items,send)
    assert result[0]['status']=='KEPT' and result[1]['status']=='UNPARSEABLE'
    assert sent[1:]==[([items[1]['id']],1),([items[1]['id']],2)]
    good['S2']=1
    assert r.classify(items[:1],{'records':[good]},'E66')[0]['status']=='INVALID'


@pytest.mark.parametrize('bank',['E66','E68','E76'])
def test_cap_and_actual_mock_wire(tmp_path,monkeypatch,bank):
    for name in list(sys.modules):
        if name.startswith('_authorized_e10_judge'):monkeypatch.delitem(sys.modules,name)
    route=read(r.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    api,privacy,p,io=r.route_modules(route)
    monkeypatch.setattr(r,'route_modules',lambda route:(api,privacy,p,io))
    monkeypatch.setattr(r,'LEDGER',tmp_path/(bank+'_3usd'))
    proof=tmp_path/'proof';write(proof,dict(verified_at='synthetic',private_input_output_logging=False,openrouter_use_inputs_outputs=False))
    route=dict(route,privacy_proof=str(proof),privacy_proof_sha256=sha(proof));monkeypatch.setattr(privacy,'check_route',lambda key:None)
    rubric=c.rubric_path(bank).read_bytes().decode();item=dict(id='a'*32,readout=' “é”\r\ntext ')
    if bank=='E66':item['readout']+=' /tmp/synthetic.txt'
    code=code66(item) if bank=='E66' else dict(id=item['id'],category='silent',values=[],evidence='')
    if bank in ('E68','E76'):item=c.render_record(dict(item,property='p',values={'A':['x','y'],'B':'z'}),rubric)
    sent=[]
    from . import cap_ledger
    if bank=='E76':monkeypatch.setattr(cap_ledger,'CACHE',tmp_path)
    class Response:
        status_code=200
        def json(self):return dict(provider=p.PROVIDER_NAME,model=p.MODEL,usage=dict(cost=.001),choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(records=[code]))))])
    def post(url,**kw):sent.append(kw['json']);return Response()
    monkeypatch.setattr(api.requests,'post',post)
    spec=dict(bank=bank,channel='structure' if bank=='E66' else 'placebo' if bank=='E76' else 'value',packet_seal_sha256='synthetic')
    if bank=='E76':spec.update(cap_fixture(tmp_path,bank,str(api.upper(r.channel_payload([item],rubric,'E56',p)))))
    r.dispatch(spec,[item],rubric,route,'synthetic-test-only')
    cap=Decimal('1') if bank=='E76' else Decimal('6') if bank=='E68' else Decimal('3')
    assert api.CAP==cap and len(sent)==1
    from .privacy79 import redact
    expected,audit=redact([item],bank)
    wire=sent[0];assert json.loads(wire['messages'][1]['content'])==expected
    assert read(r.LEDGER/(bank+'_judgments')/'PATH_REDACTION_AUDIT.json')['redacted_records']==(1 if bank=='E66' else 0)
    assert read(r.LEDGER/(bank+'_judgments')/'JUDGE_COPY.json')==expected
    assert wire['messages'][0]['content'].startswith(rubric)
    assert wire['provider']['only']==['google-vertex/global'] and wire['provider']['zdr'] is True and wire['provider']['allow_fallbacks'] is False and wire['provider']['data_collection']=='deny'
    book=api.Ledger(r.LEDGER/'ledger.jsonl')
    assert book.reserve('fills-cap',cap-Decimal('.001')) and not book.reserve('over-cap',Decimal('.001'))
    assert (r.LEDGER/(bank+'_judgments')/'RESULT_SEAL.json').exists()


def test_e66_allocation_stays_inside_shared_fifteen():
    b=dict(issuer='integrator',verified=True,bank='E66',allocation_id='test',reservation_included=True,reserved_judging_usd=3,date_zurich='2026-10-27',daily_committed_including_reservation_usd=30,shared_15usd_committed_including_reservation_usd=15,exclusive_3usd_reservation_within_shared_15usd=True)
    c.budget_gate('E66',b)
    with pytest.raises(ValueError):c.budget_gate('E66',dict(b,shared_15usd_committed_including_reservation_usd=15.01))
    with pytest.raises(ValueError):c.budget_gate('E66',dict(b,reserved_judging_usd=5))


@pytest.mark.parametrize('bank',['E66','E68','E76'])
def test_complete_admission_and_wrong_rubric_rejected(tmp_path,bank):
    conv,rows=fixture(tmp_path,bank);out=tmp_path/'out';c.convert(conv,out)
    b=tmp_path/'budget.json';write(b,dict(issuer='integrator',verified=True,bank=bank,allocation_id='test',reservation_included=True,reserved_judging_usd=1 if bank=='E76' else 6 if bank=='E68' else 3,date_zurich='2026-10-28' if bank=='E76' else '2026-10-27',daily_committed_including_reservation_usd=30,shared_15usd_committed_including_reservation_usd=15,exclusive_3usd_reservation_within_shared_15usd=True))
    receipt=tmp_path/'receipt.json';write(receipt,dict(issuer='integrator',verified=True,bank=bank,n=len(rows),authority='23a2e5c9' if bank=='E66' else '§194' if bank=='E76' else 'd147b2fe',pool='placebo',frozen_row_expansion_verified=True,packet_seal_sha256=sha(out/'PACKET_SEAL.json'),source_seals=[dict(path=conv['source_seal'],sha256=conv['source_seal_sha256'])]))
    spec=dict(bank=bank,channel='structure' if bank=='E66' else 'placebo' if bank=='E76' else 'value',budget_receipt=str(b),budget_receipt_sha256=sha(b),receipt=str(receipt),receipt_sha256=sha(receipt),packet=str(out),packet_seal_sha256=sha(out/'PACKET_SEAL.json'))
    if bank=='E76':spec.update(cap_fixture(tmp_path,bank,'.34'))
    items,rubric=r.admission(spec);assert len(items)==len(rows)
    assert all(x['id']==y['id'] and x['readout'].encode()==y['readout'].encode() for x,y in zip(items,rows))
    (out/'RUBRIC.txt').write_text('wrong')
    with pytest.raises(ValueError):r.admission(spec)


def test_shared_parent_reservation_is_real_and_not_double_counted(tmp_path):
    route=read(r.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json');api,_,_,_=r.route_modules(route)
    c.reserve_parent(api,tmp_path);c.reserve_parent(api,tmp_path)
    ledger=api.Ledger(tmp_path/'later_banks_15usd/ledger.jsonl');book,_=ledger.totals()
    assert book=={'E66_EXCLUSIVE_3USD_ALLOCATION':Decimal('3')}
    old=api.CAP
    try:
        api.CAP=Decimal('15');assert ledger.reserve('other',Decimal('12'))
        assert not ledger.reserve('over',Decimal('.001'))
    finally:api.CAP=old


@pytest.mark.parametrize('bank,allowed,rejected',[('E68',6,3),('E66',3,6)])
def test_legacy_allocation_unchanged(bank,allowed,rejected):
    b=dict(issuer='integrator',verified=True,bank=bank,allocation_id='test',reservation_included=True,reserved_judging_usd=allowed,date_zurich='2026-10-28' if bank=='E76' else '2026-10-27',daily_committed_including_reservation_usd=30,shared_15usd_committed_including_reservation_usd=15,exclusive_3usd_reservation_within_shared_15usd=True)
    c.budget_gate(bank,b)
    with pytest.raises(ValueError):c.budget_gate(bank,dict(b,reserved_judging_usd=rejected))
    with pytest.raises(ValueError):c.budget_gate(bank,dict(b,daily_committed_including_reservation_usd=allowed-1))
