import numpy as np
import pytest
from .build import fit_arrays

def sample():
    xs=[dict(row=r,split='dev',label=y,original_id=f'{r}{y}{i:02}') for r in ('fact_recall','language_plan') for y in (0,1) for i in range(42)]
    acts=np.stack([np.full(5120,3*x['label']+(.1 if x['row']=='language_plan' else 0)) for x in xs])
    return xs,acts

def test_e101_difference_orientation_and_unit():
    xs,a=sample();out=fit_arrays(xs,a)
    for d,u,n in out.values():
        np.testing.assert_allclose(d,3);np.testing.assert_allclose(np.linalg.norm(u),1);np.testing.assert_allclose(u*n,d)
    ix=np.arange(len(xs))[::-1]
    rev=fit_arrays([xs[i] for i in ix],a[ix])
    for r in out:np.testing.assert_array_equal(out[r][0],rev[r][0])

def test_reject_test_substitution_and_nan():
    xs,a=sample();xs[0]['split']='test'
    with pytest.raises(ValueError):fit_arrays(xs,a)
    xs,a=sample();a[0,0]=np.nan
    with pytest.raises(ValueError):fit_arrays(xs,a)
