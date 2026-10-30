from datetime import timedelta
import numpy as np
import pytest
from .analysis import fit,model,analyze,rules,auc,bins
from .adapter import vector,target_shift,target_statement,admission,DEADLINE,EXPERIMENTS

def synthetic(n=240):
    rng=np.random.default_rng(13);x=rng.normal(size=n);b=rng.integers(0,2,n);y=rng.binomial(1,1/(1+np.exp(-(.8*x+.2*b))))
    return [dict(id=str(i),cluster_id=str(i//2),experiment='E101',row='a' if i%3 else 'b',x1=float(x[i]),x2=int(b[i]),y=int(y[i])) for i in range(n)]

def test_rules_magnitudes_and_positive_site_gate():
    r=rules(1,-4,[.2,2],[-5,-3],[1,1]);assert r['R-SL1']=='NOT MET'
    assert rules(3,-1,[.2,4],[-2,-.1],[1,1])['R-SL1']=='MET'
    assert rules(-3,1,[-4,-.1],[.2,2],[1,1])['R-SL1']=='NOT MET'
    assert rules(.1,1,[-.1,.2],[.2,2],[1,1])['falsifier']=='MET'
    assert rules(1,1,[.2,2],[0,2],[1,1])['R-SL1']=='MET'
    assert rules(1,1,None,[0,2],[1,1])['R-SL1']=='NOT EVALUABLE'

def test_pooled_sd_and_reproducible_cluster_bootstrap():
    rows=synthetic();a=model(rows,20);b=model(rows,20)
    assert a==b and a['items']==120
    assert np.allclose(a['SD'],np.std([[r['x1'],r['x2']] for r in rows],axis=0))
    assert a['status']=='COMPLETE'
    assert np.allclose(a['standardized_coefficients'],np.array(list(a['coefficients'].values()))*a['SD'])

def test_rank_and_separation_fail_explicitly():
    X=np.column_stack([np.ones(20),np.arange(20),np.arange(20)])
    assert fit(X,np.arange(20)%2)[0] is None
    X=X[:,:2];assert fit(X,(np.arange(20)>9).astype(float))[0] is None

def test_missing_dropped_counted_not_zero():
    rows=synthetic();rows[0]['y']=None
    a=analyze(rows,4);assert a['UNPARSEABLE']==1 and a['kept']==239
    assert a['missing_by_experiment']['E101']==1
    assert a['R_SL2']['E109_44']['model']['reason']=='empty analysis sample'

def test_auc_and_bins():
    assert auc([0,1,0,1],[0,1,0,1])==1
    assert auc([0,1],[1,1])==.5
    assert auc([1,1],[0,1]) is None
    rows=synthetic();assert sum(b['n'] for b in bins(rows))==len(rows)

def test_y_both_values_states_target():
    c=dict(id='j',category='states_value',values=['A','B'],evidence='both')
    assert target_statement(c,'A','both','j')==1
    c.update(category='silent',values=[],evidence='');assert target_statement(c,'A','nothing','j')==0
    c.update(category='UNPARSEABLE');assert target_statement(c,'A','nothing','j') is None
    with pytest.raises(ValueError):target_statement(c,'A','nothing','wrong')

def test_reconstruction_and_probe_orientation():
    h=np.array([1.,2.]);v=vector(h,'E101_reconstructed',dict(unit=[1.,0.],alpha=2,raw_norm=3,sigma=-1))
    assert np.array_equal(v,[-5,2])
    assert target_shift(h,v,np.array([2.,1.]),1)==-12
    assert target_shift(h,v,np.array([2.,1.]),0)==12
    assert np.array_equal(vector(h,'donor',dict(vector=[3,4])),[3,4])
    with pytest.raises(ValueError):vector(h,'E101_reconstructed',dict(unit=[2,0],alpha=2,raw_norm=3,sigma=-1))

def test_deadline_and_full_scope():
    no109=set(EXPERIMENTS)-{'E109_44'}
    with pytest.raises(ValueError):admission(no109,False,DEADLINE-timedelta(seconds=1),READY)
    admission(no109,False,DEADLINE,READY);admission(EXPERIMENTS,True,DEADLINE-timedelta(days=1),READY)
    with pytest.raises(ValueError):admission(no109,True,DEADLINE,READY)

def test_duplicate_observations_rejected():
    r=synthetic()
    with pytest.raises(ValueError):analyze(r+[r[0]],1)

def test_full_registered_bootstrap():
    a=model(synthetic())
    assert a['bootstrap']['draws']==2000 and a['bootstrap']['seed']==20261029
    assert a['valid_bootstrap_draws']+sum(a['bootstrap_failures'].values())==2000


def test_original_standardized_probe_shift():
    from .adapter import effective_weights
    w=np.array([2.,3.]);sd=np.array([4.,2.]);mu=np.array([10.,-1.]);h=np.array([2.,5.]);hp=np.array([6.,3.])
    effective=effective_weights(w,'standardized',sd)
    assert np.isclose(target_shift(h,hp,effective,1),np.dot((hp-mu)/sd,w)-np.dot((h-mu)/sd,w))
    assert np.array_equal(effective_weights(w,'none'),w)
    with pytest.raises(ValueError):effective_weights(w,'standardized',[0,1])


READY={'flip_seal_available':True,'probe_lineage_available':True}

def test_e100_correction_deadline_and_inputs():
    from .adapter import E100_DEADLINE
    absent=set(EXPERIMENTS)-{'E100_a'}
    for status in ({'flip_seal_available':False,'probe_lineage_available':True},{'flip_seal_available':True,'probe_lineage_available':False}):
        with pytest.raises(ValueError):admission(absent,True,E100_DEADLINE-timedelta(seconds=1),status)
        admission(absent,True,E100_DEADLINE,status)
        with pytest.raises(ValueError):admission(EXPERIMENTS,True,E100_DEADLINE,status)
    admission(EXPERIMENTS,True,E100_DEADLINE-timedelta(hours=1),READY)
    with pytest.raises(ValueError):admission(absent,True,E100_DEADLINE,READY)
    with pytest.raises(ValueError):admission(EXPERIMENTS,True,E100_DEADLINE)


def test_direct_user_exclusion_supersedes_cutoff():
    from .adapter import E100_DEADLINE
    scope=set(EXPERIMENTS)-{'E100_a'}
    admission(scope,True,E100_DEADLINE-timedelta(hours=1),exclude_e100_by_user=True)
    with pytest.raises(ValueError):admission(EXPERIMENTS,True,E100_DEADLINE,exclude_e100_by_user=True)
    with pytest.raises(ValueError):admission(scope-{'E101'},True,E100_DEADLINE,exclude_e100_by_user=True)
