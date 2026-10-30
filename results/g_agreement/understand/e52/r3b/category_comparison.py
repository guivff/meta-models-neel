"""Deferred §181 paired category baseline; no file I/O or outcome loading on import."""
import numpy as np
CATEGORIES={'content','plan','bookkeeping','delimiter','syntactic','format'}


def category_prediction(category):
    if category not in CATEGORIES:raise ValueError('missing or unknown frozen E58a category')
    return 'REPORTED' if category in ('content','plan') else 'MISSED'


def balanced_accuracy(truth,prediction):
    y=np.asarray(truth,dtype=np.int8);p=np.asarray(prediction,dtype=np.int8)
    if y.shape!=p.shape or y.ndim!=1 or not np.isin(y,[0,1]).all() or not np.isin(p,[0,1]).all():
        raise ValueError('same-length binary truth/prediction vectors required')
    if set(y.tolist())!={0,1}:return None
    return float(np.mean([np.mean(p[y==k]==k) for k in (0,1)]))


def compare(rows,draws=2000,seed=20261027):
    """One reader's forecasted gated rows; preserve bank/cell identity and paired draws."""
    keys=[(r['bank'],r['row']) for r in rows]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate forecast unit')
    if not rows:raise ValueError('no forecasted gated rows')
    if any(r['truth'] not in ('REPORTED','MISSED') or r['j_prediction'] not in ('REPORTED','MISSED') for r in rows):
        raise ValueError('complete sealed truth and J forecast required')
    if type(draws)!=int or draws<1:raise ValueError('positive bootstrap draw count required')
    cat=[category_prediction(r['category']) for r in rows]
    y=np.array([r['truth']=='REPORTED' for r in rows],dtype=np.int8)
    j=np.array([r['j_prediction']=='REPORTED' for r in rows],dtype=np.int8)
    c=np.array([x=='REPORTED' for x in cat],dtype=np.int8)
    n=len(y);positive=int(y.sum());negative=n-positive
    jb=balanced_accuracy(y,j);cb=balanced_accuracy(y,c)
    accuracy=float(np.mean(j==y));constant=max(positive,negative)/n
    samples=[];invalid=0;rng=np.random.default_rng(seed)
    for _ in range(draws):
        ix=rng.integers(0,n,n);a=balanced_accuracy(y[ix],j[ix]);b=balanced_accuracy(y[ix],c[ix])
        if a is None or b is None:invalid+=1;continue
        samples.append((a,b,a-b))
    intervals=None
    if samples:
        q=np.quantile(np.asarray(samples),[.025,.975],axis=0)
        intervals={name:q[:,i].tolist() for i,name in enumerate(['J_balanced_accuracy','category_balanced_accuracy','J_minus_category_balanced_accuracy'])}
    eligible=n>=20 and positive>=5 and negative>=5 and intervals is not None
    delta=jb-cb if jb is not None and cb is not None else None
    original=bool(jb>=.70 and intervals['J_balanced_accuracy'][0]>.50 and accuracy-constant>=.10) if eligible else None
    incremental=bool(delta>=.05 and intervals['J_minus_category_balanced_accuracy'][0]>0) if eligible else None
    return {'status':'EVALUABLE' if eligible else 'NOT EVALUABLE','n':n,'reported':positive,'missed':negative,
        'J_balanced_accuracy':jb,'category_balanced_accuracy':cb,'J_minus_category_balanced_accuracy':delta,
        'J_accuracy':accuracy,'category_accuracy':float(np.mean(c==y)),
        'better_constant_accuracy':constant,'J_accuracy_minus_better_constant':accuracy-constant,
        'bootstrap':{'unit':'bank/row-or-cell','paired':True,'draws':draws,'seed':seed,
            'valid_draws':len(samples),'single_truth_class_draws':invalid,'percentile95':intervals},
        'original_R3b_met':original,'workspace_incremental_support':incremental,
        'finding':'NOT EVALUABLE' if not eligible else 'J-forecast adds beyond category' if incremental else 'J-fraction adds nothing beyond the kind of information',
        'falsifier':bool(jb<=.55) if eligible else None,
        'rows':[dict(r,category_prediction=p) for r,p in zip(rows,cat)]}
