"""EXPLORATORY operational tests on synthetic data only."""
import numpy as np
from sklearn.linear_model import LogisticRegression
import logistic as m

def test_fit_matches_independent_sklearn():
 rng=np.random.default_rng(7);x=rng.normal(size=(80,4));y=rng.integers(0,2,80)
 beta=m.fit(np.column_stack([np.ones(80),x]),y)
 other=LogisticRegression(C=1,solver='lbfgs',tol=1e-12,max_iter=1000).fit(x,y)
 assert np.max(np.abs(beta-np.r_[other.intercept_,other.coef_[0]]))<1e-6

def test_held_out_scaling_and_determinism():
 cat=np.array(['content','bookkeeping']*8);j=np.arange(16,dtype=float);y=np.array([0,1,0,0,1,0,1,1]*2)
 train=np.arange(16)!=15;x=m.design(cat,j,train,True)
 assert abs(x[train,-1].mean())<1e-12 and abs(x[train,-1].std()-1)<1e-12
 assert x[15,-1]>x[14,-1]
 p=m.loo(cat,j,y,True);assert np.array_equal(p,m.loo(cat,j,y,True));assert np.isfinite(p).all() and ((p>0)&(p<1)).all()

def test_metrics_and_single_class():
 y=np.array([0,0,1,1]);p=np.array([.1,.2,.8,.9]);assert m.ba(y,p)==1
 assert m.ba(np.array([1,1]),np.array([.2,.8]))is None
 assert np.allclose(m.loss(y,np.ones(4)*.5),np.log(2))
