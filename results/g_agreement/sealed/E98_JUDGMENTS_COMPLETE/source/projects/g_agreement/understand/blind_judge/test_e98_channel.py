import pytest
from .e98_channel import channels
from .rubric202 import original_ids,BASE,amended

def candidates(n):return [dict(id=f'{i:032x}',property=dict(definition='Original property',values=dict(A='a',B='b')),readout='native unchanged') for i in range(n)]

@pytest.mark.parametrize('n',[0,1,4,5,2016])
def test_unresolved_only_original_rubrics_and_sampling(n):
    xs=candidates(n);primary,old=channels(xs)
    assert len(primary[1])==n and len(old[1])==(n+3)//4
    if n:assert sorted(x['id'] for x in old[1])==original_ids([x['id'] for x in xs],'E98')
    assert primary[2].encode()==amended() and old[2]==BASE.read_text()
    assert [x['readout'] for x in primary[1]]==[x['readout'] for x in xs]


def test_no_target_metadata_or_invented_binary_count_values():
    xs=candidates(1);xs[0]['label']=1
    with pytest.raises(ValueError):channels(xs)
    xs=candidates(1);xs[0]['property']['values']={'count':'twelve'}
    with pytest.raises(ValueError):channels(xs)


def test_registered_cap_is_ten_and_source_count_rows_retained(tmp_path,monkeypatch):
    from decimal import Decimal
    from . import e98_channel as e
    from projects.g_agreement.readerbench.io import write,sha
    assert e.CAP==Decimal('10')
    monkeypatch.setattr(e,'sources',lambda:None)
    source=tmp_path/'native';source.mkdir();write(source/'COMPLETE.json',dict(status='COMPLETE'))
    write(source/'OUTPUT_SEAL.json',dict(status='COMPLETE',files={'COMPLETE.json':sha(source/'COMPLETE.json')}))
    calls=candidates(4);ids=[f'{i:032x}' for i in range(2184)]
    counts=[dict(id=i,source_measure='unchanged original count_item') for i in ids[2016:]]
    resolved=[dict(id=i) for i in ids[4:2016]]
    for name,data in [('CANDIDATES.PRIVATE.json',calls),('NATIVE_IDS.json',ids),('COUNT_MEASURES.json',counts),('REGEX_RESOLVED.json',resolved)]:write(tmp_path/name,data)
    write(tmp_path/'INPUT_SEAL.json',dict(experiment='E98',status='FROZEN_READY',labels_cpu_only=True,native_per_reader_counts={'oracle':2184},registered_rows=26,binary_items=1932,nonbinary_items=252,registered_count_items=168,mention_only_items=84,judge_unresolved_items=4,regex_resolved_items=2012,native_seal_sha256=sha(source/'OUTPUT_SEAL.json'),source_seals=[dict(seal=str(source/'OUTPUT_SEAL.json'),sha256=sha(source/'OUTPUT_SEAL.json'))],files={name:sha(tmp_path/name) for name in ['CANDIDATES.PRIVATE.json','NATIVE_IDS.json','COUNT_MEASURES.json','REGEX_RESOLVED.json']}))
    bank=e.E98Bank(tmp_path/'INPUT_SEAL.json',sha(tmp_path/'INPUT_SEAL.json'))
    assert len(bank.cpu_counts)==168 and len(bank.cpu_resolved)==2012 and len(bank.channels[0][1])==4
    assert bank.cpu_counts==counts
