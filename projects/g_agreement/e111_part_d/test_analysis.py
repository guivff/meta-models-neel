import pytest
from .analysis import features,analyze

def test_geometry_and_orientation():
    z=features([0,0],[3,4],[2,0],1)
    assert z==dict(displacement_norm=5,probe_projection=3,probe_logit_shift=6)
    assert features([0,0],[3,4],[2,0],0)['probe_projection']==-3

def rows():
    return [dict(id=f'{e}-{i}',row='synthetic',experiment=e,y=int(e=='E101'),probe_logit_shift=float(i),displacement_norm=float(i)) for e in ('E101','E104_U') for i in range(20)]

def test_matched_gap():
    z=analyze(rows());assert z['status']=='POST HOC EXPLORATORY'
    assert z['rows']['synthetic']['probe_logit_shift']['overlap_weighted_gap']==1

def test_ties_and_missing_not_zero():
    xs=rows()
    for x in xs:x['probe_logit_shift']=0;x['y']=None if x['experiment']=='E101' else 0
    z=analyze(xs)['rows']['synthetic']['probe_logit_shift']
    assert z['overlap_weighted_gap'] is None and z['bins'][0]['arms']['E101']['missing']==20

def test_duplicate_and_invalid_geometry():
    with pytest.raises(ValueError):analyze(rows()+[rows()[0]])
    with pytest.raises(ValueError):features([0],[1],[0],1)
