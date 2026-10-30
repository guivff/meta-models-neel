import pytest
from . import rules as r

def row(p,lo=.01):return dict(difference=dict(estimate=p,CI95=None if lo is None else [lo,1]))
def inputs():return ({k:row(.30) for k in r.TRAIN},{k:row(.20) for k in r.HELD},{k:row(-.10) for k in r.CONTENT})

def test_fx1_all_three_conjuncts_inclusive_points():
    a,b,c=inputs();assert r.rules(a,b,c,.20,True,True)['R_FX1']=='MET'
    assert r.rules(a,b,c,.20001,True,True)['R_FX1']=='NOT MET'
    c[r.CONTENT[0]]=row(-.11);assert r.rules(a,b,c,.2,True,True)['R_FX1']=='MET'
    c[r.CONTENT[1]]=row(-.11);assert r.rules(a,b,c,.2,True,True)['R_FX1']=='NOT MET'

def test_train_requires_two_positive_ci_not_just_point():
    a,b,c=inputs();a[r.TRAIN[0]]=row(.3,0)
    assert r.rules(a,b,c,.2,True,True)['R_FX1']=='MET'
    a[r.TRAIN[1]]=row(.3,0)
    assert r.rules(a,b,c,.2,True,True)['R_FX1']=='NOT MET'

def test_transfer_is_two_of_five_point_only():
    a,b,c=inputs();b={k:row(.2 if i<2 else 0,-.5) for i,k in enumerate(r.HELD)}
    assert r.rules(a,b,c,.2,True,True)['R_FX2']=='MET'
    b[r.HELD[0]]=row(.199,-.5)
    assert r.rules(a,b,c,.2,True,True)['R_FX2']=='NOT MET'

def test_decoder_limit_requires_all3_loss_decrease_and_recipe():
    a,b,c=inputs();a={k:row(.10,-.1) for k in r.TRAIN}
    assert r.rules(a,b,c,0,True,True)['falsifier']=='MET'
    assert r.rules(a,b,c,0,False,True)['falsifier']=='NOT MET'
    assert r.rules(a,b,c,0,True,False)['falsifier']=='NOT MET'
    a[r.TRAIN[0]]=row(.101)
    assert r.rules(a,b,c,0,True,True)['falsifier']=='NOT MET'

def test_prior_falsifier_independent_of_loss_component():
    a,b,c=inputs();assert r.rules(a,b,c,.30,False,True)['falsifier']=='MET'
    assert r.rules(a,b,c,.299,False,True)['falsifier']=='NOT MET'

def test_missing_nonvacuous_and_definite_failed_conjunct():
    a,b,c=inputs();assert r.rules(a,b,c,None,True,True)['R_FX1']=='NOT EVALUABLE'
    a={k:row(None,None) for k in r.TRAIN}
    assert r.rules(a,b,c,None,True,True)['falsifier']=='NOT EVALUABLE'
    c={k:row(-1) for k in r.CONTENT}
    assert r.rules(a,b,c,None,True,True)['R_FX1']=='NOT MET'

def test_paired_bootstrap_separate_masks():
    xs=[dict(item_id=str(i),original=(-1 if i%2 else 1),intervention=(-1 if i%2 else 1)) for i in range(84)]
    z=r.paired(xs);assert z['difference']['CI95']==[0,0]
    xs[0]['original']=None
    z=r.paired(xs);assert z['original']['kept']==83 and z['intervention']['kept']==84
    with pytest.raises(ValueError,match='duplicate'):r.paired(xs+[xs[0]])

def test_exact_scope_rejects_e102_content_and_sixth_held_row():
    a,b,c=inputs();b['bracket_depth']=row(.4)
    with pytest.raises(ValueError,match='exact3/5/4'):r.rules(a,b,c,.1,True,True)

def test_placebo_signed_vs_statement_rate_can_reverse_verdict():
    # Always stating alternating A/B on an arbitrary all-A random-vector target
    # gives signedS0 but any-value rate1. §215 needs an explicit choice here.
    a,b,c=inputs()
    assert r.rules(a,b,c,0,True,True)['R_FX1']=='MET'
    assert r.rules(a,b,c,1,True,True)['R_FX1']=='NOT MET'
    assert r.rules(a,b,c,1,True,True)['falsifier']=='MET'
