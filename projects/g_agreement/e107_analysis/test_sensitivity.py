from copy import deepcopy
import pytest
from . import sensitivity as s


def fixture():
    items=[dict(id=str(i),systems={'outside':{'belief':1,'truth':0,'named':True},'oracle':{'belief':0,'named':True}}) for i in range(6)]
    audit=dict(redacted_records=5,affected=[dict(id=str(i),original_readout_sha256='a'*64,judge_readout_sha256='b'*64) for i in range(5)])
    plans=[dict(inventory_id=str(i),target='belief') for i in range(5)]
    mapping=dict(all_affected_mapped=True,affected=[dict(opaque_id=str(i),inventory_id=str(i),target='belief',plan_index=i) for i in range(5)])
    return items,audit,mapping,plans


def test_exact_mapping():
    assert s.affected_items(*fixture())==set(map(str,range(5)))


@pytest.mark.parametrize('bad',['duplicate','plan','hash','missing'])
def test_reject_bad_custody(bad):
    items,audit,mapping,plans=fixture()
    if bad=='duplicate':mapping['affected'][1]=mapping['affected'][0]
    if bad=='plan':plans[0]['inventory_id']='wrong'
    if bad=='hash':audit['affected'][0]['original_readout_sha256']='bad'
    if bad=='missing':audit['affected'].pop()
    with pytest.raises(Exception):s.affected_items(items,audit,mapping,plans)


def test_mask_readout_keep_pair_and_primary(monkeypatch):
    items,*_=fixture();before=deepcopy(items)
    monkeypatch.setattr(s,'analyze',lambda xs,rows:xs)
    result=s.sensitivity(items,[],{'0'})['results']
    assert items==before and len(result)==6
    assert all(v is None for v in result[0]['systems']['outside'].values())
    assert result[0]['systems']['oracle']==items[0]['systems']['oracle']
    assert result[1:]==items[1:]
