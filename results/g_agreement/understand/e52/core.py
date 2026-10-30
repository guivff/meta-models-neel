"""Registered E52 statistics. No reader-outcome access in this module."""
import numpy as np
from scipy.stats import rankdata,mannwhitneyu,pointbiserialr
SEED=20261027

def auroc(scores,y):
    scores=np.asarray(scores,dtype=np.float64);y=np.asarray(y)
    if scores.ndim!=1 or len(y)!=len(scores) or not np.isfinite(scores).all() or set(y)!={0,1}:raise ValueError('finite binary scores required')
    p=int(y.sum());n=len(y)-p
    return float((rankdata(scores)[y==1].sum()-p*(p+1)/2)/(p*n))

def g3(best_ranks,y):
    ranks=np.asarray(best_ranks);y=np.asarray(y)
    if ranks.shape!=(len(y),2) or not np.isfinite(ranks).all() or np.any(ranks<0):raise ValueError('two full-vocabulary ranks required')
    scores=-np.log10(ranks+1.)
    def stat(labels):return (auroc(scores[:,0],labels)+auroc(scores[:,1],1-labels))/2
    observed=stat(y);rng=np.random.default_rng(SEED)
    null=np.array([stat(rng.permutation(y)) for _ in range(200)])
    upper=float(np.quantile(null,.975))
    return {'status':'EVALUABLE','auroc':observed,'per_side_auroc':[auroc(scores[:,0],y),auroc(scores[:,1],1-y)],
        'permutations':200,'null_seed':SEED,'null_mean':float(null.mean()),'null_band95':np.quantile(null,[.025,.975]).tolist(),
        'permutation_p_plus_one':float((1+sum(null>=observed))/201),'readable':bool(observed>=.65 and observed>upper)}

def enrich(acts,y,q,null):
    x=np.asarray(acts,dtype=np.float64);y=np.asarray(y)
    if x.shape!=(len(y),5120) or set(y)!={0,1} or not np.isfinite(x).all():raise ValueError('finite block44 binary activations')
    means=np.stack([x[y==k].mean(0) for k in (1,0)]);d=means[0]-means[1];norm=float(np.linalg.norm(d))
    if norm==0:raise ValueError('zero class-mean difference; no defined unit direction')
    d/=norm;values={}
    for r in (384,1536):
        observed=float(np.square(d@np.asarray(q[:,:r],dtype=np.float64)).sum()/(r/5120));ref=np.array(null[str(r)]['values'])
        values[str(r)]={'enrichment':observed,'z':float((observed-ref.mean())/ref.std(ddof=1)),
            'percentile':float(100*(sum(ref<observed)+.5*sum(ref==observed))/len(ref)),
            'random_null_n':200,'random_null_mean':float(ref.mean()),'random_null_sample_sd':float(ref.std(ddof=1))}
    return values,means,d,norm

def label(enrichment,readability):
    a,b=[enrichment[str(r)]['enrichment'] for r in (384,1536)]
    readable=readability.get('readable') is True
    if (a>=1.5 and b>=1.5) or readable:return 'IN-J'
    if a<=1.2 and b<=1.2 and not readable:return 'OUT-J'
    return 'DIFFUSE'

def rule_r2(records):
    eligible=[r for r in records if r['class']=='structure' and r['probe_auroc']>=.85]
    a=[];b=[];used=[]
    for r in eligible:
        if r.get('unprompted_mention_rate') is not None:
            sayable=r['unprompted_mention_rate']>=.10;measure='unprompted mention'
        elif r.get('forced_choice_auroc') is not None:
            sayable=r['forced_choice_auroc']>=.80;measure='forced choice (off-distribution); no readouts'
        else:continue
        (a if sayable else b).append(r['E1536']);used.append({'row':r['row'],'sayable':sayable,'measure':measure})
    if not a or not b:return {'status':'NOT EVALUABLE','met':None,'reason':'both sayability groups required','rows':used}
    p=float(mannwhitneyu(a,b,alternative='greater',method='auto').pvalue)
    rho=float(pointbiserialr([1]*len(a)+[0]*len(b),a+b).statistic)
    if not np.isfinite(rho):return {'status':'NOT EVALUABLE','met':None,'reason':'constant enrichment','rows':used}
    return {'status':'EVALUABLE','met':bool(p<.05 and rho>=.4),'one_sided_p':p,'point_biserial_rho':rho,'rows':used}
