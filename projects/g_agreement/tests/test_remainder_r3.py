import numpy as np
import pandas as pd
import pytest
from projects.g_agreement.r_bench import remainder_r3 as r


def test_calibration_never_accepts_test_labels_and_selection_is_pool_only():
    rng=np.random.default_rng(4); y=np.tile([0,1],32)
    x=np.column_stack([y*4-2, rng.normal(size=64), rng.normal(size=64), rng.normal(size=64)])
    t=x[:20]
    arms, fits=r.aggregate(x,y,t,'two')
    assert next(f['reader'] for f in fits if f['native_selected'])=='jlens'
    changed,_=r.aggregate(x,y,t[::-1],'two')
    for variant in r.VARIANTS:
        for method in r.METHODS:
            np.testing.assert_allclose(arms[variant][method][0][::-1],changed[variant][method][0])


def test_majority_and_ties_follow_native_votes():
    y=np.tile([0,1],16); x=np.tile((2*y-1)[:,None],(1,4)).astype(float)
    t=np.array([[1,1,-1,-1],[1,1,1,-1],[-1,-1,-1,1]])
    arms,_=r.aggregate(x,y,t,'two')
    np.testing.assert_array_equal(arms['native']['majority'][0],[.5,.75,.25])
    np.testing.assert_array_equal(arms['native']['majority'][1],[False,True,False])


def test_no_reliability_uses_uniform_and_keeps_arms_finite():
    y=np.tile([0,1],16); x=np.zeros((32,4)); arms,_=r.aggregate(x,y,np.zeros((6,4)),'two')
    for variant in r.VARIANTS:
        for method in r.METHODS:
            assert np.isfinite(arms[variant][method][0]).all()


def test_ece_has_correct_boundary_and_weights():
    assert r.ece([0,1],[0,1])==0
    assert r.ece([0,1],[1,0])==1
    assert r.ece([0,1],[.5,.5])==0
    assert r.ece([0,1],[.5,.5],[3,1])==.25


def test_insufficient_pool_fails():
    with pytest.raises(AssertionError): r.aggregate(np.zeros((20,4)),np.tile([0,1],10),np.zeros((1,4)),'two')


def test_smoke_requires_all_cells():
    with pytest.raises(AssertionError,match='SMOKE FAILED'):
        r.assert_coverage(pd.DataFrame({'native_majority_p':[.5]}))


def test_identical_methods_have_zero_paired_effect_under_both_bootstraps():
    frame=pd.DataFrame({'dataset':['a']*8+['b']*8,'corpus_group':['c']*16,
                        'text_hash':[str(i) for i in range(8)]*2})
    for reference in r.REFERENCES: frame[reference]=np.tile([0,1],8)
    for variant in r.VARIANTS:
        for method in r.METHODS:
            frame[f'{variant}_{method}_p']=np.tile([.2,.8],8)
            frame[f'{variant}_{method}_vote']=np.tile([0,1],8)
    point,samples,schema=r.bootstrap_group(frame,20,3)
    for values in [point,*samples.values()]:
        np.testing.assert_allclose(values[...,0],1)
        np.testing.assert_allclose(values[...,1],.2)
