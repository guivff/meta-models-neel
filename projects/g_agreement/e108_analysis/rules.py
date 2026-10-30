"""§219 choice reading, frozen before outputs. CPU only."""
from collections import Counter
import numpy as np
from common.stats import bootstrap_ci
from projects.g_agreement.understand.wmech2.core import require
CATEGORIES=('sport','animal','colour','country','fruit','musical instrument','city','profession','vegetable','bird','vehicle','number 1–10')
ARMS=('immediate','delayed')
DRAWS,SEED=5000,0

def interval(values,fn=np.mean):
    if not len(values):return dict(estimate=None,CI95=None)
    p,lo,hi=bootstrap_ci(values,fn,n_boot=DRAWS,seed=SEED)
    return dict(estimate=p if np.isfinite(p) else None,CI95=[lo,hi] if np.isfinite([lo,hi]).all() else None)

def mean(x):return float(np.nanmean(x)) if np.isfinite(x).any() else np.nan

def loo_modes(items):
    """Category-wide LOO, across both arms as §219 says 'in that category'.

    Canonical member IDs supplied by blind ground-truth extraction; no lexical
    guessing from continuations. Ties: lexicographically first canonical ID.
    Each prompt-arm is one item; the other arm remains in the reference pool.
    """
    counts={c:Counter(x['choice'] for x in items if x['category']==c) for c in CATEGORIES}
    result={}
    for x in items:
        c=counts[x['category']].copy();c[x['choice']]-=1
        candidates=[k for k,v in c.items() if v>0]
        guess=min(candidates,key=lambda k:(-c[k],k)) if candidates else None
        result[x['id']]=None if guess is None else int(guess==x['choice'])
    return result

def comparison(items,reader,modes):
    xs=sorted(items,key=lambda x:x['id']);arrays={}
    for system in (reader,'outside','mode'):
        arrays[system]=np.array([modes[x['id']] if system=='mode' else x['hits'][system] for x in xs],float)
    out={'rates':{},'counts':{}}
    for k,v in arrays.items():
        out['rates'][k]=interval(np.arange(len(xs)),lambda ix:mean(v[ix]))
        out['counts'][k]=dict(total=len(xs),kept=int(np.isfinite(v).sum()),missing=int(np.isnan(v).sum()))
    # Resample one common item index; recompute max of both baseline rates
    # inside each draw. Fixed LOO predictions are scored, never refitted to duplicates.
    out['difference']=interval(np.arange(len(xs)),lambda ix:mean(arrays[reader][ix])-max(mean(arrays['mode'][ix]),mean(arrays['outside'][ix])) if np.isfinite([mean(arrays[k][ix]) for k in arrays]).all() else np.nan)
    return out

def verdict(d):
    p,ci=d['estimate'],d['CI95']
    return dict(R_CH1='NOT EVALUABLE' if p is None or ci is None else 'MET' if round(p,12)>=.15 and ci[0]>0 else 'NOT MET',falsifier='NOT EVALUABLE' if p is None else 'MET' if p<=0 else 'NOT MET')

def analyze(items,placebo):
    valid=[x for x in items if x['choice_status']=='ONE'];modes=loo_modes(valid)
    out=dict(experiment='E108',authority='§219',bootstrap=dict(draws=DRAWS,seed=SEED,unit='prompt-arm item',paired_systems=True),excluded={k:sum(x['choice_status']==k for x in items) for k in ('NONE','MULTIPLE','UNPARSEABLE')},readers={},placebo={},J_fraction={})
    for reader in ('oracle','nla'):
        tables={}
        for arm in ARMS:
            for cat in (*CATEGORIES,'non_number','all'):
                xs=[x for x in valid if x['arm']==arm and (cat=='all' or cat=='non_number' and x['category']!=CATEGORIES[-1] or x['category']==cat)]
                tables[arm+':'+cat]=comparison(xs,reader,modes)
        out['readers'][reader]=dict(cells=tables,rules=verdict(tables['delayed:non_number']['difference']),confirmatory=reader=='oracle')
        vals=np.array([x['hits'][reader] for x in sorted(placebo,key=lambda x:x['id'])],float)
        out['placebo'][reader]=dict(rate=interval(np.arange(len(vals)),lambda ix:mean(vals[ix])),total=len(vals),missing=int(np.isnan(vals).sum()))
    for cat in CATEGORIES:
        for arm in ARMS:
            xs=[x for x in valid if x['category']==cat and x['arm']==arm]
            vals=np.array([x['J_fraction'] for x in xs],float)
            out['J_fraction'][arm+':'+cat]=dict(mean=mean(vals) if np.isfinite(vals).any() else None,kept=int(np.isfinite(vals).sum()),missing=int(np.isnan(vals).sum()))
    out['R_CH2']='Descriptive immediate/delayed, number/non-number, per-category J fraction with corresponding hit rates; no new decision threshold.'
    return out
