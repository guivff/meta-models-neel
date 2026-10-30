import pytest
from . import adapter as a

def contract():
    return dict(E85_bank_seal_sha256=a.E85_BANK_SHA,schema='E122_CONTINUATION_CONTRASTS_V1',dev_quartets=50,test_quartets=100,contrasts=[dict(id=str(i),positive=dict(token_ids=[10+i,20+i]),negative=dict(token_ids=[30+i])) for i in range(4)])

def test_frozen_schema_mapping_no_mutation():
    import copy
    d=contract();before=copy.deepcopy(d);xs=a.contrasts(d)
    assert d==before
    assert xs[0]['candidate_ids']==[[[10,20],[30]]]
    assert [x['id'] for x in xs]==['0','1','2','3']
    assert xs[0]['candidate_ids_sha256']==a.digest([[[10,20],[30]]])

def test_bad_tokens_and_split():
    d=contract();d['contrasts'][0]['positive']['token_ids']=[]
    with pytest.raises(ValueError):a.contrasts(d)
    d=contract();d['dev_quartets']=49
    with pytest.raises(ValueError):a.contrasts(d)

def test_nonfinite_raw_pairs():
    assert a.pair_score([-3,-5])==2
    with pytest.raises(ValueError):a.pair_score([float('nan'),-5])
