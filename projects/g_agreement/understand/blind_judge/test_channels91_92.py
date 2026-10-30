import json
import pytest
from projects.g_agreement.readerbench.io import read,sha,write
from . import channels91_92 as c
from . import later_runner as r
from .test_cap_ledger import fixture as cap_fixture


@pytest.mark.parametrize('bank',['E91','E92'])
def test_byte_sealed_blind_adapter_and_original_subsample(tmp_path,bank):
    source=tmp_path/'source';source.mkdir()
    field='concept' if bank=='E91' else 'content'
    items=[dict(id=f'{i:032x}',readout='Not a claim about birds.',**{field:'birds'}) for i in range(8)]
    write(source/'JUDGE_PACKET.json',items)
    write(source/'BLIND_SEAL.json',dict(experiment=bank,n=len(items),complete=True,
        rubric_sha256=sha(c.rubric_path(bank)),files={'JUDGE_PACKET.json':sha(source/'JUDGE_PACKET.json')}))
    spec=dict(bank=bank,source_seal=str(source/'BLIND_SEAL.json'),
        source_seal_sha256=sha(source/'BLIND_SEAL.json'),source_packet=str(source/'JUDGE_PACKET.json'),
        rubric=str(c.rubric_path(bank)))
    out=tmp_path/'converted';c.convert(spec,out)
    assert read(out/'PACKET.json')==items and len(read(out/'ORIGINAL_IDS.json'))==2
    assert (out/'RUBRIC.txt').read_bytes()==c.rubric_path(bank).read_bytes()
    budget=tmp_path/'budget.json';write(budget,dict(bank=bank,issuer='integrator',verified=True,
       reservation_included=True,allocation_id='test',reserved_judging_usd=1,
       daily_committed_including_reservation_usd=33))
    receipt=tmp_path/'receipt.json';write(receipt,dict(bank=bank,issuer='integrator',verified=True,
       authority='5e5e3f40',forecast_gate_verified=True,bank_gate_verified=True,n=len(items),
       packet_seal_sha256=sha(out/'PACKET_SEAL.json'),
       source_seals=[dict(path=spec['source_seal'],sha256=spec['source_seal_sha256'])]))
    run=dict(bank=bank,channel='polarity' if bank=='E91' else 'source',
             packet=str(out),packet_seal_sha256=sha(out/'PACKET_SEAL.json'),
             budget_receipt=str(budget),budget_receipt_sha256=sha(budget),
             receipt=str(receipt),receipt_sha256=sha(receipt),**cap_fixture(tmp_path,bank,'.4'))
    wire,rubric=r.admission(run)
    assert len(wire)==8 and all(set(x)=={'id','rubric','readout'} for x in wire)
    assert all('birds' in x['rubric'] for x in wire)
    (source/'JUDGE_PACKET.json').write_text('tampered')
    with pytest.raises(ValueError):r.admission(run)


@pytest.mark.parametrize('bank,field,positive,empty',[('E91','polarity','NEGATED','NEITHER'),
                                                   ('E92','source','tool','no_one')])
def test_concept_and_source_judgment_validation(bank,field,positive,empty):
    item=dict(id='a'*32,rubric='frozen',readout='The tool said the sentence was negated.')
    good=dict(id=item['id'],evidence='the tool said',**{field:positive})
    assert r.classify([item],dict(records=[good]),bank)[0]['status']=='KEPT'
    assert r.classify([item],dict(records=[dict(good,evidence='missing')]),bank)[0]['status']=='INVALID'
    assert r.classify([item],dict(records=[dict(good,**{field:empty},evidence='')]),bank)[0]['status']=='KEPT'
