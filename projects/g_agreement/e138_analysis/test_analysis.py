import pytest
from .analysis import analyze, validate

def rows():
    return [dict(item_id=str(i),row='fact_recall',block=44,donor_id=str((i+1)%84),recipient_old='old'+str(i),donor_old='old'+str((i+1)%84),arms=dict(clean='recipient-old',donor='donor-old',random='none')) for i in range(84)]

def test_donor_primary_and_none_beside_each_arm():
    r=analyze(rows())
    assert r['donor_primary']=='MET' and r['random_withdrawal']=='NOT MET'
    assert r['arms']['random']['none']['estimate']==1
    assert r['arms']['donor']['none']['estimate']==0
    assert r['contrasts']['donor']['CI95']==[-1.,-1.]

def test_random_cannot_supply_positive_evidence():
    xs=rows()
    for x in xs:x['arms']['donor']='none'
    r=analyze(xs)
    assert r['donor_primary']=='NOT MET' and r['random_withdrawal']=='NOT MET'

def test_random_overrides_wording_even_with_positive_donor():
    xs=rows()
    for x in xs[:17]:x['arms']['random']='recipient-old'
    r=analyze(xs)
    assert r['donor_primary']=='MET' and r['random_withdrawal']=='MET'
    assert r['reading']=='withdraw stale-readout wording'

def test_random_missing_does_not_change_donor_reading():
    xs=rows()
    for x in xs:x['arms']['random']=None
    r=analyze(xs)
    assert r['donor_primary']=='MET' and r['random_withdrawal']=='NOT EVALUABLE'
    assert r['arms']['random']['none']['estimate'] is None

def test_donor_threshold_boundaries_and_observed_denominators():
    xs=rows()
    for i,x in enumerate(xs):x['arms']['donor']='recipient-old' if i<4 else 'donor-old' if i<36 else 'none' if i<80 else None
    r=analyze(xs)
    assert r['arms']['donor']['recipient-old']['estimate']==.05
    assert r['arms']['donor']['donor-old']['estimate']==.40
    assert r['donor_primary']=='MET' and not r['donor_positive_robust_to_missing']
    assert r['arms']['donor']['none']['missing_n']==4

@pytest.mark.parametrize('change',['duplicate','partial','self_donor','same_value','block','code','arm'])
def test_rejects_unbound_census_and_codes(change):
    xs=rows()
    if change=='duplicate':xs[-1]=xs[0]
    if change=='partial':xs.pop()
    if change=='self_donor':xs[0]['donor_id']='0'
    if change=='same_value':xs[0]['donor_old']=xs[0]['recipient_old']
    if change=='block':xs[0]['block']=52
    if change=='code':xs[0]['arms']['donor']='dual'
    if change=='arm':del xs[0]['arms']['random']
    with pytest.raises(ValueError):validate(xs)

def test_missing_all_is_unknown_not_none():
    xs=rows()
    for x in xs:x['arms']={a:None for a in x['arms']}
    r=analyze(xs)
    assert r['donor_primary']==r['random_withdrawal']=='NOT EVALUABLE'
    assert r['arms']['donor']['none']['full84_missing_bounds']==[0.,1.]


def test_dual_values_preserved_not_credited_as_exclusive_or_none():
    xs=rows();xs[0]['arms']['donor']=['recipient-old','donor-old']
    xs[1]['arms']['random']=[]
    r=analyze(xs);d=r['arms']['donor']
    assert d['dual_or_multiple']['k']==1 and d['recipient-old']['k']==0
    assert d['donor-old']['k']==83 and d['none']['k']==0
    assert d['recipient_mentioned']['k']==1 and d['donor_mentioned']['k']==84
    assert r['arms']['random']['none']['k']==84
