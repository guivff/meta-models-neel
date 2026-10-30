"""§248 C amendment1: post-hoc, pre-computation group checks and fixed models."""
import numpy as np
from sklearn.metrics import roc_auc_score
from projects.g_agreement.e127_analysis.common import rate
from .predictors import model,auc_ci
DRAWS=5000
SEED=0


def group(row):
    f=row['flips']
    if f['4'] is True:return 'easy'
    if f['2'] is False and f['4'] is False and f['6'] is True:return 'resistant'
    return None


def mean_stat(values,binary=False):
    if binary:return rate(values)
    known=[v for v in values if v is not None]
    if any(not np.isfinite(v) for v in known):raise ValueError('finite source quantity or null')
    return dict(planned_n=len(values),n=len(known),missing_n=len(values)-len(known),estimate=float(np.mean(known)) if known else None)


def difference(rows,field):
    # One joint item resample of original84; retain group membership and missingness.
    def delta(rs):
        a=[r[field] for r in rs if group(r)=='easy' and r[field] is not None]
        b=[r[field] for r in rs if group(r)=='resistant' and r[field] is not None]
        return float(np.mean(b)-np.mean(a)) if a and b else None
    rng=np.random.default_rng(SEED);vals=[]
    for _ in range(DRAWS):
        v=delta([rows[i] for i in rng.integers(len(rows),size=len(rows))])
        if v is not None:vals.append(v)
    return dict(estimate=delta(rows),CI95=np.quantile(vals,[.025,.975]).tolist() if vals else None,valid_bootstraps=len(vals),requested_bootstraps=DRAWS,direction='resistant minus easy')


def groups(rows):
    if len(rows)!=84 or len({r['id'] for r in rows})!=84:raise ValueError('original84 unique items')
    rows=sorted(rows,key=lambda r:r['id'])
    if any(set(r['flips'])!={'2','4','6','8'} or any(v is not None and type(v) is not bool for v in r['flips'].values()) for r in rows):raise ValueError('exact literal bool/null dose flags')
    fields=('clean_old44','answer_margin','random_old44_4','random_old44_6','random_old44_8')
    report={}
    for f in fields:
        for r in rows:
            if f!='answer_margin' and r[f] is not None and (type(r[f]) is not int or r[f] not in (0,1)):raise ValueError('original exclusive old indicator or null')
        report[f]={g:mean_stat([r[f] for r in rows if group(r)==g],f!='answer_margin') for g in ('easy','resistant')}
        report[f]['difference']=difference(rows,f)
    return dict(section='248 C amendment1 parts1-2',status='EXPLORATORY_POST_HOC',group_counts={(g or 'unknown_or_other'):sum(group(r)==g for r in rows) for g in ('easy','resistant',None)},quantities=report,seed=SEED,bootstraps=DRAWS,interpretation='Association only; group definitions frozen from E135 source; unknown earlier flips excluded from resistant. No causal wording.')


def displacement(clean,steered):
    if clean is None or steered is None:return None
    a,b=np.asarray(clean,float),np.asarray(steered,float)
    if a.ndim!=1 or a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all() or np.linalg.norm(a)==0:raise ValueError('exact finite matched read-token vectors and nonzero clean norm')
    return float(np.linalg.norm(b-a)/np.linalg.norm(a))


def loo_predictions(x,y):
    x,y=np.asarray(x,float),np.asarray(y,int)
    if len(y)<3 or len(set(y))<2:return None
    pred=[]
    for i in range(len(y)):
        keep=np.arange(len(y))!=i
        if len(set(y[keep]))<2:return None
        s,m=model(x[keep],y[keep]);pred.append(float(m.decision_function(s.transform(x[i:i+1]))[0]))
    return pred


def gain_ci(y,base,aug):
    if base is None or aug is None:return dict(estimate=None,CI95=None,valid_bootstraps=0)
    y,base,aug=map(np.asarray,(y,base,aug));rng=np.random.default_rng(SEED);vs=[]
    for _ in range(DRAWS):
        ix=rng.integers(len(y),size=len(y))
        if len(set(y[ix]))==2:vs.append(float(roc_auc_score(y[ix],aug[ix])-roc_auc_score(y[ix],base[ix])))
    return dict(estimate=float(roc_auc_score(y,aug)-roc_auc_score(y,base)),CI95=np.quantile(vs,[.025,.975]).tolist() if vs else None,valid_bootstraps=len(vs),convention='paired item bootstrap of fixed out-of-fold predictions; no bootstrap refit or in-sample scores')


def models(rows):
    result={}
    for endpoint in ('resistant','old44_alpha8'):
        # All compared models use the SAME complete-case item census per endpoint.
        kept=[]
        for r in rows:
            y=(None if group(r) is None else int(group(r)=='resistant')) if endpoint=='resistant' else r['old44_alpha8']
            fs=[r[k] for k in ('answer_margin','probe_unhooked','displacement8')]
            if y is not None and all(v is not None and np.isfinite(v) for v in fs):kept.append((r['id'],int(y),fs))
        y=[z[1] for z in kept];x=np.array([z[2] for z in kept],float).reshape(-1,3)
        fits={};preds={}
        for name,idx in [('answer',[0]),('probe',[1]),('displacement',[2]),('answer_probe',[0,1]),('answer_displacement',[0,2]),('joint',[0,1,2])]:
            p=loo_predictions(x[:,idx],y);preds[name]=p
            fits[name]=dict(kept=len(y),missing=len(rows)-len(y),loo_auroc=float(roc_auc_score(y,p)) if p is not None else None,loo_auroc_bootstrap=auc_ci(p,y) if p is not None else None)
            if p is not None:
                scaler,fitted=model(x[:,idx],y);fits[name].update(standardized_coefficients=fitted.coef_[0].tolist(),intercept=float(fitted.intercept_[0]))
        gain=gain_ci(y,preds['answer'],preds['answer_probe'])
        eligible=gain['estimate'] is not None and gain['estimate']>=.05 and gain['CI95'] is not None and gain['CI95'][0]>0
        result[endpoint]=dict(models=fits,probe_added_value=gain,probe_added_value_beyond_answer_and_geometry=gain_ci(y,preds['answer_displacement'],preds['joint']),deck_phrase_eligible=eligible)
    # Staleness wording uses its own old44 endpoint, not whichever endpoint looks better.
    return dict(endpoints=result,deck_phrase='the early representation predicts staleness' if result['old44_alpha8']['deck_phrase_eligible'] else 'susceptibility to steering predicts it',exploratory=True,causal=False)
