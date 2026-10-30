import pytest
from projects.g_agreement.e137.selection import choose,correct

def fixture(n=45,one=20):
    pairs=[];ans={}
    for design,count in [('D1',n),('D2',n),('one_hop',one)]:
        for k in range(count):
            ids=[f'{design}-{k}-{m}'for m in (0,1)]
            pairs.append(dict(subdesign=design,recipients=['Alice','Bob'],previous_holder='Carol',members=[dict(id=i,member=m,current_holder=['Alice','Bob'][m])for m,i in enumerate(ids)]))
            ans.update({ids[0]:' Alice',ids[1]:' Bob'})
    return pairs,ans

def test_both_and_source_order():
    p,a=fixture();a['D1-0-1']='Carol'
    kept,counts,d=choose(p,a,10,'synthetic ruling fixture')
    assert counts['D1']==44 and kept['D1'][0]==['D1-1-0','D1-1-1']
    assert len(kept['D2'])==42 and len(kept['one_hop'])==10 and d['D1_counts']

def test_no_capacity_inference():
    p,a=fixture()
    with pytest.raises(ValueError):choose(p,a,None,'')
    with pytest.raises(ValueError):choose(p,a,20,'synthetic fixture')

def test_screen_only():
    p,a=fixture(19,0)
    assert choose(p,a,0,'synthetic fixture')[2]['action']=='SCREEN_RESULTS_ONLY'

def test_missing_record_refused():
    p,a=fixture(1,0);a.pop(next(iter(a)))
    with pytest.raises(ValueError):choose(p,a,0,'synthetic fixture')

def test_original_parse_multiple_not_correct():
    assert not correct(' Alice and Bob',['Alice','Bob','Carol'],'Alice')
