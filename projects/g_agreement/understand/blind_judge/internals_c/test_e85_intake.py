import pytest
from .e85_intake import make_units


def fixture():
    public=[dict(id=str(i),reader_allowed=True,split='test',prompt='SYSTEM retained\nUSER frozen source')for i in range(400)]
    records=[(dict(member='batch.json',keys=[i,'text']),dict(id=f'{i}:{r}',unit_id=str(i),reader=r,repeat=0,text='The model is being evaluated.',malformed=True))for i in range(400)for r in ('oracle','nla')]
    return public,records


def test_all800_original_source_text_and_seeded200_no_factor_labels_sent():
    public,records=fixture();units,joins,audit,raw=make_units(public,records,'original S6')
    assert len(units)==1000 and len(joins)==800 and sum(x['kind']=='s6'for x in units)==200
    assert all(x['data']['source_text']==public[0]['prompt']for x in units if x['kind']=='eval85')
    assert all(set(x['data'])==({'id','source_text','readout'}if x['kind']=='eval85'else{'id','readout'})for x in units)
    assert audit['redacted_records']==0 and not raw


def test_missing_native_or_dev_source_cannot_silently_reduce_scope():
    public,records=fixture()
    with pytest.raises(ValueError):make_units(public,records[:-1],'original')
    public[0]['split']='dev'
    with pytest.raises(ValueError):make_units(public,records,'original')
