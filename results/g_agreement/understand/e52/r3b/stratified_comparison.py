"""§181 clarification3: row-weighted within-category BA and conditional null."""
import numpy as np
from category_comparison import CATEGORIES,balanced_accuracy,compare
PERMUTATIONS=1000
SEED=20261027


def within_category(rows):
    keys=[(r['bank'],r['row']) for r in rows]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate bank/row-or-cell')
    for r in rows:
        if r.get('category') not in CATEGORIES:raise ValueError('frozen E58a category required for every row')
        if r.get('truth') not in ('REPORTED','MISSED') or r.get('j_prediction') not in ('REPORTED','MISSED'):
            raise ValueError('sealed binary truth and J forecast required')
    strata=[];excluded=[];arrays=[]
    for category in sorted({r['category'] for r in rows}):
        rr=sorted([r for r in rows if r['category']==category],key=lambda r:(r['bank'],r['row']))
        y=np.array([r['truth']=='REPORTED' for r in rr],dtype=np.int8)
        p=np.array([r['j_prediction']=='REPORTED' for r in rr],dtype=np.int8)
        stat={'category':category,'n':len(rr),'reported':int(y.sum()),'missed':int(len(y)-y.sum())}
        if len(rr)<4 or set(y.tolist())!={0,1}:
            stat['reason']='fewer than4 rows' if len(rr)<4 else 'only one truth class'
            excluded.append(stat);continue
        stat['balanced_accuracy']=balanced_accuracy(y,p)
        strata.append(stat);arrays.append((y,p))
    n=sum(s['n'] for s in strata)
    if not strata:
        return {'status':'NOT EVALUABLE','qualified_strata':0,'n':0,'stratified_balanced_accuracy':None,
                'criterion_met':None,'strata':strata,'excluded_strata':excluded,
                'reason':'no E58a category has at least4 rows and both truth classes'}
    weights=np.array([s['n']/n for s in strata])
    observed=float(weights@np.array([s['balanced_accuracy'] for s in strata]))
    rng=np.random.default_rng(SEED);null=[]
    for _ in range(PERMUTATIONS):
        scores=[balanced_accuracy(rng.permutation(y),p) for y,p in arrays]
        null.append(float(weights@np.array(scores)))
    cutoff=float(np.quantile(null,.95));met=bool(observed>=.65 and observed>cutoff)
    status='CONFIRMATORY' if len(strata)>=3 else 'DESCRIPTIVE'
    return {'status':status,'qualified_strata':len(strata),'n':n,
        'stratified_balanced_accuracy':observed,'criterion_met':met,
        'finding':('J predicts reportability within kinds of information' if met else 'within-category criterion not met'),
        'strata':strata,'excluded_strata':excluded,
        'permutation':{'count':PERMUTATIONS,'seed':SEED,'shuffled':'truth labels within each fixed E58a category',
            'predictions_fixed':True,'weighting':'stratum row counts / total qualifying rows',
            'percentile95':cutoff,'p_greater_equal_plus_one':float((1+np.sum(np.asarray(null)>=observed))/(PERMUTATIONS+1)),
            'null_balanced_accuracy':null}}


def score_forecasts_by_reader(rows_by_reader):
    """Deferred analysis entry: always report original, category and within-category tests."""
    if set(rows_by_reader)!={'oracle','nla'}:raise ValueError('both registered readers required')
    return {reader:{'pooled_and_category':compare(rows),'within_category':within_category(rows)}
            for reader,rows in rows_by_reader.items()}
