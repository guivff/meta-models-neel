"""E115 frozen descriptive metrics. No file IO, fitting, or real-data execution."""
import numpy as np
from sklearn.metrics import roc_auc_score

def j_fraction(h, mean, basis):
    x=np.asarray(h,dtype=np.float64)-np.asarray(mean,dtype=np.float64)
    q=np.asarray(basis,dtype=np.float64)
    if x.ndim!=2 or q.ndim!=2 or x.shape[1]!=q.shape[0]: raise ValueError('shape')
    if not np.isfinite(x).all() or not np.isfinite(q).all(): raise ValueError('finite')
    den=np.sum(x*x,axis=1)
    if np.any(den<=1e-12): raise ValueError('zero centered norm')
    return np.sum((x@q)**2,axis=1)/den

def paired_summary(steered, random, draws=2000, seed=20261029):
    a=np.asarray(steered,dtype=float);b=np.asarray(random,dtype=float)
    if a.ndim!=1 or a.shape!=b.shape or not len(a) or not np.isfinite(a).all() or not np.isfinite(b).all(): raise ValueError('paired finite coverage')
    def auc(x,y):return float(roc_auc_score(np.r_[np.ones(len(x)),np.zeros(len(y))],np.r_[x,y]))
    rng=np.random.default_rng(seed);ix=rng.integers(0,len(a),size=(draws,len(a)))
    samples=[auc(a[i],b[i]) for i in ix]
    return dict(n=len(a),steered_mean=float(a.mean()),random_mean=float(b.mean()),auroc=auc(a,b),auroc_ci=np.quantile(samples,[.025,.975]).tolist(),steered_mean_ci=np.quantile(a[ix].mean(1),[.025,.975]).tolist(),random_mean_ci=np.quantile(b[ix].mean(1),[.025,.975]).tolist())
