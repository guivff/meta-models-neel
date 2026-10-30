"""E26 raw-cosine ranking and registered R1/R2; CPU-only functions."""
import numpy as np
from scipy.stats import rankdata
from .e21_analyse import cosine


def raw_scores(recon,activations):
    return np.stack([cosine(recon,np.broadcast_to(h,np.asarray(recon).shape)) for h in activations])


def item_measures(scores,categories,values,truth,k=10):
    """Average ranks; a boundary tie shares top-k mass equally, without ordering bias."""
    scores=np.asarray(scores,float);categories=np.asarray(categories);values=np.asarray(values)
    if scores.ndim!=2 or len(categories)!=scores.shape[1] or len(values)!=len(categories) or len(truth)!=len(scores):
        raise ValueError('aligned candidate/item grid required')
    if not np.isfinite(scores).all() or scores.shape[1]<k:raise ValueError('finite bank with at least10 candidates required')
    result=[]
    for s,y in zip(scores,truth):
        boundary=np.sort(s)[-k];strict=s>boundary;tied=s==boundary
        weight=strict.astype(float)+tied*(k-int(strict.sum()))/int(tied.sum())
        ranks=rankdata(-s,method='average');own=(categories=='continuation')&(values==y)
        desc=(categories=='description')&(values==y)
        if not own.any() or not desc.any():raise ValueError('own-value continuation and description candidates required')
        result.append({'M1':float(weight[own].sum()/k),'M3':float(weight[categories=='description'].sum()/k),
                       'best_true_description_rank':float(ranks[desc].min()),
                       'median_own_continuation_rank':float(np.median(ranks[own]))})
    return result


def summarize(items,n_boot=2000,seed=20261025):
    x={k:np.array([r[k] for r in items]) for k in items[0]}
    def stats(ix):
        d=float(np.median(x['best_true_description_rank'][ix]));c=float(np.median(x['median_own_continuation_rank'][ix]))
        return np.array([x['M1'][ix].mean(),d,c,d-c,x['M3'][ix].mean()])
    point=stats(np.arange(len(items)));rng=np.random.default_rng(seed)
    boot=np.stack([stats(ix) for ix in rng.integers(0,len(items),(n_boot,len(items)))])
    lo,hi=np.quantile(boot,[.025,.975],axis=0)
    names=('M1','best_true_description_median_rank','own_continuation_median_rank','M2_rank_difference','M3')
    out={k:{'estimate':float(v),'ci95':[float(l),float(h)]} for k,v,l,h in zip(names,point,lo,hi)}
    out.update(R1=bool(point[0]>=.65 and lo[0]>.50),R2=bool(point[3]>0 and lo[3]>0),n_items=len(items),n_boot=n_boot,seed=seed)
    return out
