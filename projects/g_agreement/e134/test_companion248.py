import pytest
from .companion248 import analyze

def fixture():
    rows=[dict(id=str(i),item_id=str(i),truth='A',readings=r)for i,r in enumerate([{44:'A',52:'A',60:'B'},{44:None,52:'B',60:'A'},{44:None,52:None,60:None},{44:'B',52:'B',60:'A'}])]
    counts={'PALL':(2,1,3),'P44':(1,1,2),'P52':(1,2,3),'P60':(2,1,3)}
    original={'scores':{r:{'metrics':{k:dict(count=v,denominator=4)for k,v in zip(('accuracy','false_claim_rate','coverage'),n)}}for r,n in counts.items()}}
    return rows,original

def test_pairing_table_denominators_and_frozen_conservative():
    rows,original=fixture();x=analyze(rows,original,draws=40)
    assert x['outcome_table']['counts']==[[1,1,0],[1,0,0],[0,0,1]]
    assert x['paired_differences']['accuracy_PALL_minus_P60']['estimate']==0
    assert x['precision_given_claim']['P44']['estimate']==.5
    assert x['PAGREE']['metrics']['coverage']['count']==0
    assert x['PAGREE']['precision_given_claim']['Wilson95']is None
    assert sum(map(sum,x['outcome_table']['counts']))==4
    original['scores']['P44']['metrics']['accuracy']['count']=2
    with pytest.raises(ValueError,match='aggregate mismatch'):analyze(rows,original,draws=2)

def test_paired_identical_outputs_have_zero_difference_interval():
    rows=[dict(id=str(i),item_id=str(i),truth='A',readings={44:v,52:v,60:v})for i,v in enumerate(['A','B',None])]
    original={'scores':{r:{'metrics':{k:dict(count=v,denominator=3)for k,v in [('accuracy',1),('false_claim_rate',1),('coverage',2)]}}for r in ('PALL','P44','P52','P60')}}
    x=analyze(rows,original,draws=40)
    assert all(v['item_bootstrap95']==[0.,0.]for v in x['paired_differences'].values())
    assert x['PAGREE']['precision_given_claim']['estimate']==.5
