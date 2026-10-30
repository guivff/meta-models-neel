"""Pool-only grouped fitting for R2-B. No data is loaded at import."""
from __future__ import annotations
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import balanced_accuracy_score
from projects.g_agreement.r_bench import remainder_r2b as D

GRID=(.01,.1,1.,10.)


def validate_training(x,y,groups,test_groups):
    x=np.asarray(x);y=np.asarray(y);groups=np.asarray(groups)
    if x.ndim!=2 or len(x)!=len(y) or len(y)!=len(groups) or not np.isfinite(x).all():
        raise ValueError('Invalid training array')
    if set(y)!={0,1}:raise ValueError('Training labels lack both classes')
    D.audit_split(set(groups),set(test_groups))
    if len(set(groups))<2:raise ValueError('Insufficient independent training groups')
    return x,y,groups


def grouped_splits(y,groups):
    y=np.asarray(y);groups=np.asarray(groups)
    for count in range(min(5,len(set(groups))),1,-1):
        splits=list(StratifiedGroupKFold(n_splits=count,shuffle=True,random_state=D.SEED).split(np.zeros(len(y)),y,groups))
        if all(set(y[train])=={0,1} and set(y[val])=={0,1} for train,val in splits):return splits
    raise ValueError('No group-disjoint folds contain both labels')


def fit_pool(x,y,groups,test_groups):
    x,y,groups=validate_training(x,y,groups,test_groups)
    splits=grouped_splits(y,groups)
    best=None
    for c in GRID:
        scores=np.empty(len(y),dtype=float)
        for train,val in splits:
            scaler=StandardScaler().fit(x[train])
            fit=LogisticRegression(C=c,solver='lbfgs',max_iter=1000,random_state=D.SEED).fit(scaler.transform(x[train]),y[train])
            if fit.n_iter_.max()>=fit.max_iter:raise ValueError(f'LR did not converge C={c}')
            scores[val]=fit.decision_function(scaler.transform(x[val]))
        # Pool-only OOF threshold; tie closest to zero then lower threshold.
        thresholds=np.unique(np.r_[0,scores])
        threshold=min(thresholds,key=lambda t:(-balanced_accuracy_score(y,scores>=t),abs(t),t))
        accuracy=balanced_accuracy_score(y,scores>=threshold)
        if best is None or accuracy>best[0]:best=(accuracy,c,float(threshold))
    accuracy,c,threshold=best
    scaler=StandardScaler().fit(x)
    fit=LogisticRegression(C=c,solver='lbfgs',max_iter=1000,random_state=D.SEED).fit(scaler.transform(x),y)
    if fit.n_iter_.max()>=fit.max_iter:raise ValueError('Final LR did not converge')
    return dict(C=c,threshold=threshold,pool_validation_accuracy=float(accuracy),
                mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),
                coef=fit.coef_[0].tolist(),intercept=float(fit.intercept_[0]),
                raw_normal=D.raw_normal(fit.coef_[0],scaler.scale_).tolist(),
                train_groups=sorted(set(map(str,groups))))


def predict(fit,x):
    x=np.asarray(x,dtype=float)
    score=((x-np.asarray(fit['mean']))/np.asarray(fit['scale']))@np.asarray(fit['coef'])+fit['intercept']
    return score,(score>=fit['threshold']).astype(int)


def fit_fixed_transfer(x,y,groups,test_groups):
    """Approved reverse-family fallback: fixed C, no inner validation claim."""
    x=np.asarray(x);y=np.asarray(y);groups=np.asarray(groups)
    if x.ndim!=2 or len(x)!=len(y) or len(y)!=len(groups) or not np.isfinite(x).all() or set(y)!={0,1}:
        raise ValueError('Invalid transfer training array')
    D.audit_split(set(groups),set(test_groups))
    scaler=StandardScaler().fit(x)
    fit=LogisticRegression(C=1.,solver='lbfgs',max_iter=1000,random_state=D.SEED).fit(scaler.transform(x),y)
    if fit.n_iter_.max()>=fit.max_iter:raise ValueError('Transfer LR did not converge')
    return dict(C=1.,threshold=0.,pool_validation_accuracy=None,selection='forward-block transfer',
                mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=fit.coef_[0].tolist(),
                intercept=float(fit.intercept_[0]),raw_normal=D.raw_normal(fit.coef_[0],scaler.scale_).tolist(),
                train_groups=sorted(set(map(str,groups))))
