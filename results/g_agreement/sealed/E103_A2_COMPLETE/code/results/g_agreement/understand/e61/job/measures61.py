"""§177 descriptive timeline and matched-item ratio summaries; no decoding/judging here."""
import numpy as np

def paired_ratios(probability,mentions):
    """Rows are matched base items; columns think/ignore/none. Mentions are eight-output means."""
    p=np.asarray(probability,float);m=np.asarray(mentions,float)
    if p.shape!=m.shape or p.ndim!=2 or p.shape[1]!=3 or len(p)!=84 or not np.isfinite(p).all() or not np.isfinite(m).all() or ((p<0)|(p>1)|(m<0)|(m>1)).any():raise ValueError('84 matched items x three arms')
    rng=np.random.default_rng(20261027);draws=rng.integers(0,len(p),size=(2000,len(p)))
    def ratio(numerator,denominator):
        point_n=float(numerator.mean());point_d=float(denominator.mean())
        n=numerator[draws].mean(axis=1);d=denominator[draws].mean(axis=1)
        # Never discard zero-denominator bootstrap draws and silently narrow a CI.
        return {'ratio':None if point_d==0 else point_n/point_d,'CI95':None if np.any(d==0) else np.quantile(n/d,[.025,.975]).tolist(),'zero_denominator_draws':int(np.sum(d==0))}
    base=ratio(p[:,1],p[:,2]);reader=ratio(m[:,1],m[:,0])
    return {'base_ignore_over_none':base,'mention_ignore_over_think':reader,'R_W':'NOT EVALUABLE' if base['ratio'] is None or reader['ratio'] is None else ('MET' if round(base['ratio'],12)>=.8 and round(reader['ratio'],12)<=.5 else 'NOT MET'),'falsifier':bool(m[:,1].mean()>=m[:,0].mean()),'items':84,'bootstrap_draws':2000,'bootstrap_seed':20261027}


def timeline_bands(values):
    """Per position, paired item means (decline arm, answer arm), no pooled repeat inference."""
    result={}
    for position,pairs in sorted(values.items()):
        x=np.asarray(pairs,float)
        if x.ndim!=2 or x.shape[1]!=2 or not len(x) or not np.isfinite(x).all() or ((x<0)|(x>1)).any():raise ValueError('paired timeline means')
        rng=np.random.default_rng(20261027);boot=x[rng.integers(0,len(x),size=(2000,len(x)))].mean(axis=1)
        result[position]={'mean':x.mean(axis=0).tolist(),'CI95':np.quantile(boot,[.025,.975],axis=0).tolist(),'difference':float(x[:,0].mean()-x[:,1].mean()),'paired_items':len(x)}
    first=next((p for p,v in sorted(result.items()) if round(v['difference'],12)>=.20),None)
    return {'positions':result,'first_difference_at_least_point_two':first}
