import copy
import pytest
from . import contrast as c

def fixture():
    return [dict(row=r,item_id=str(i),site_flip=True,carried_flip=i<50,scores=dict(site_steered=1,site_random=0,carried_steered=0,carried_random=0)) for r in c.ROWS for i in range(84)]

def test_shared_double_flip_and_paired_difference():
    z=c.analyze(fixture());assert z['R_SL0']=='MET'
    for r in c.ROWS:assert z['rows'][r]['n_flipped_both']==50 and z['rows'][r]['CI95']==[1,1]

def test_four_cell_sign_and_cancellation():
    xs=fixture()
    for x in xs:x['scores'].update(carried_steered=1)
    assert c.analyze(xs)['R_SL0']=='NOT MET'
    for x in xs:x['scores']['carried_random']=1
    assert c.analyze(xs)['R_SL0']=='MET'

def test_at_least_one_row_and_missing():
    xs=fixture()
    for x in xs:
        if x['row']==c.ROWS[1]:x['site_flip']=False
    assert c.analyze(xs)['R_SL0']=='MET'
    for x in xs:x['scores']['site_steered']=None
    assert c.analyze(xs)['R_SL0']=='NOT EVALUABLE'

def test_full_census_not_regression_available_subset():
    with pytest.raises(ValueError):c.analyze(fixture()[:-1])
    xs=fixture();xs[0]['scores']['extra']=1
    with pytest.raises(ValueError):c.analyze(xs)

def test_deterministic_bootstrap_and_pairing():
    xs=fixture()
    for i,x in enumerate(xs):x['scores']['site_steered']=1 if i%2 else -1
    a=c.analyze(xs);assert a==c.analyze(copy.deepcopy(xs))
    assert a['rows'][c.ROWS[0]]['CI95'][0]<0 and a['R_SL0']=='NOT MET'
