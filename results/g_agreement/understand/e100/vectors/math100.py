"""CPU vector algebra and manipulation measurements; no inference or labels on pods."""
import numpy as np


def unit(x):
    x=np.asarray(x,dtype=np.float64);n=np.linalg.norm(x)
    if not np.isfinite(x).all() or not np.isfinite(n) or n<=1e-12:raise ValueError('finite nonzero direction required')
    return x/n


def directions(dev,labels,q,rng):
    labels=np.asarray(labels);dev=np.asarray(dev,np.float64)
    if set(labels.tolist())!={0,1} or dev.ndim!=2:raise ValueError('binary dev classes required')
    d=dev[labels==1].mean(0)-dev[labels==0].mean(0)
    j=q@(q.T@d);perp=d-j
    r=rng.normal(size=len(d));r-=d*(r@d)/(d@d)
    return d,dict(d=unit(d),d_J=unit(j),d_perp=unit(perp),r=unit(r))


def random_basis(dim=5120,rank=384,seed=20261028):
    if not 0<rank<dim:raise ValueError('proper random rank')
    z=np.random.default_rng(seed).standard_normal((dim,rank))
    q,r=np.linalg.qr(z,mode='reduced');q*=np.where(np.diag(r)<0,-1.,1.)
    return q


def pair_other(ids,labels,seed=20261028):
    if len(ids)!=len(set(ids)) or len(ids)!=len(labels) or set(labels)!={0,1}:raise ValueError('unique binary test items')
    rng=np.random.default_rng(seed);partners=[]
    for i,label in enumerate(labels):
        eligible=[j for j,other in enumerate(labels) if other!=label]
        partners.append(int(rng.choice(eligible)))
    return partners


def manipulation(h,h_prime,w,sd,target_label=None):
    """Raw linear-logit shift, optional target-oriented shift, and norm distortion.

    The existing standardized dev probe has decision ((h-mu)/sd)@w+b.
    Mu and intercept cancel in the difference; this is not a probability shift.
    Caller joins target labels only on CPU after opaque outputs return.
    """
    h=np.asarray(h,np.float64);hp=np.asarray(h_prime,np.float64)
    w=np.asarray(w,np.float64);sd=np.asarray(sd,np.float64)
    if h.shape!=hp.shape or h.ndim!=2 or w.shape!=(h.shape[1],) or sd.shape!=w.shape:raise ValueError('aligned cells and probe')
    if not all(np.isfinite(x).all() for x in [h,hp,w,sd]) or (sd<=0).any():raise ValueError('finite probe and activations')
    denom=np.linalg.norm(h,axis=1)
    if (denom<=0).any():raise ValueError('nonzero original norm')
    shift=(hp-h)@(w/sd);ratio=np.linalg.norm(hp,axis=1)/denom
    result=dict(probe_logit_shift=shift,norm_ratio=ratio,norm_ratio_above_1_5=ratio>1.5)
    if target_label is not None:
        target=np.asarray(target_label)
        if target.shape!=(len(h),) or not np.isin(target,[0,1]).all():raise ValueError('CPU binary target labels')
        result['target_signed_probe_logit_shift']=shift*(2*target-1)
    return result
