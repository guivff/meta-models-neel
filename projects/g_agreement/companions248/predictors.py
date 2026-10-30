"""§248 C fixed item predictors; no outcome-driven feature/threshold selection."""
import warnings
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
DOSES=('2','4','6','8');SEED=0;DRAWS=5000

def min_dose(flips):
    if set(flips)!=set(DOSES) or any(x not in (True,False,None) for x in flips.values()):raise ValueError('four literal pair flips')
    unknown=False
    for d in DOSES:
        if flips[d] is None:unknown=True
        elif flips[d]:return (None,'unknown earlier dose') if unknown else (int(d),'observed')
    return None,'unknown' if unknown else 'no observed flip through8'

def auc_ci(x,y):
    x=np.array(x,float);y=np.array(y,float);keep=np.isfinite(x)&np.isfinite(y);x=x[keep];y=y[keep]
    if len(set(y))<2:return dict(kept=len(y),estimate=None,CI95=None,valid_bootstraps=0)
    rng=np.random.default_rng(SEED);vals=[]
    for _ in range(DRAWS):
        ix=rng.integers(0,len(y),len(y))
        if len(set(y[ix]))==2:vals.append(roc_auc_score(y[ix],x[ix]))
    return dict(kept=len(y),estimate=float(roc_auc_score(y,x)),CI95=np.quantile(vals,[.025,.975]).tolist() if vals else None,valid_bootstraps=len(vals))

def model(x,y):
    scaler=StandardScaler().fit(x);m=LogisticRegression(C=1.,solver='lbfgs',max_iter=2000,random_state=0)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning);m.fit(scaler.transform(x),y)
    return scaler,m

def loo(x,y):
    x=np.array(x,float);y=np.array(y,float);keep=np.isfinite(x).all(1)&np.isfinite(y);x=x[keep];y=y[keep]
    if len(y)<3 or len(set(y))<2:return dict(kept=len(y),auroc=None,reason='insufficient observed classes')
    preds=[]
    for i in range(len(y)):
        train=np.arange(len(y))!=i
        if len(set(y[train]))<2:return dict(kept=len(y),auroc=None,reason='one class in a leave-one-out training fold')
        s,m=model(x[train],y[train]);preds.append(float(m.decision_function(s.transform(x[i:i+1]))[0]))
    s,m=model(x,y)
    return dict(kept=len(y),auroc=float(roc_auc_score(y,preds)),standardized_coefficients=m.coef_[0].tolist(),intercept=float(m.intercept_[0]),
                convention='L2 C1; scaler fitted on each training fold only; no tuning')

def analyze(rows):
    if len(rows)!=84 or len({r['id'] for r in rows})!=84:raise ValueError('original84 E104 IDs')
    rows=sorted(rows,key=lambda r:r['id']);table=[];cross=[[0,0],[0,0]];cross_missing=0
    for r in rows:
        if set(r['codes'])!=set(DOSES):raise ValueError('all four doses, explicit missing permitted')
        for v in r['codes'].values():
            if v['44'] not in ('old','new','dual','neither',None) or v['52_new'] not in (True,False,None):raise ValueError('sealed category only')
        d,status=min_dose(r['flips']);c=r['codes']['8']['44'];y=None if c is None else int(c in ('old','dual'))
        for f in ('unhooked_margin','probe_unhooked','probe_alpha8'):
            if r[f] is not None and not np.isfinite(r[f]):raise ValueError('finite literal margin or missing')
        table.append(dict(r,min_flipping_dose=d,min_dose_status=status,old44_alpha8=y))
        if d is None or y is None:cross_missing+=1
        else:cross[0 if d<=6 else 1][y]+=1
    num=lambda v:np.nan if v is None else v
    y=[num(r['old44_alpha8']) for r in table]
    features={f:[num(r[f]) for r in table] for f in ('min_flipping_dose','unhooked_margin','probe_unhooked','probe_alpha8')}
    aucs={f:auc_ci(x,y) for f,x in features.items()}
    fits={p:loo(list(zip(features['unhooked_margin'],features[p])),y) for p in ('probe_unhooked','probe_alpha8')}
    complement=[r for r in table if r['flips']['4'] is False]
    audit=dict(alpha4_nonflippers=len(complement),old44_at8=sum(r['old44_alpha8']==1 for r in complement),missing_at8=sum(r['old44_alpha8'] is None for r in complement))
    return dict(section='248 C',status='EXPLORATORY_POST_HOC',PRIVATE_TABLE=table,min_dose_by_old44=cross,cross_missing=cross_missing,
                original_alpha4_complement_audit=audit,predictor_auroc=aucs,two_predictor_fits=fits,
                deck_phrase_eligible=aucs['probe_unhooked']['estimate'] is not None and aucs['probe_unhooked']['estimate']>=.80,
                reading='predictive association only; no causal wording',primary_fit='unhooked pair margin plus unhooked probe margin; alpha8 probe fit separate sensitivity')
