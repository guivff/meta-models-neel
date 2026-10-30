"""§182 C: full-series demeaned lag1..8 ACF, then equal mean across items."""
import numpy as np


def item_acf(projection):
    x=np.asarray(projection,dtype=np.float64)
    if x.ndim!=1 or not np.isfinite(x).all():
        raise ValueError('one finite unpadded projection series required')
    if len(x)<16:
        return {'status':'SKIPPED_SHORT','reason':'fewer than16 content-through-read positions; section182 clarification1','n_positions':len(x)}
    centered=x-x.mean();denom=float(centered@centered)
    if denom==0:
        return {'status':'NOT EVALUABLE','reason':'constant projection; demeaned ACF denominator is zero','n_positions':len(x)}
    acf=[float(centered[:-lag]@centered[lag:]/denom) for lag in range(1,9)]
    return {'status':'EVALUABLE','n_positions':len(x),'lags':list(range(1,9)),
            'acf':acf,'mean_lag_acf':float(np.mean(acf))}


def row_coherence(item_activations,probe_direction):
    w=np.asarray(probe_direction,dtype=np.float64)
    if w.shape!=(5120,) or not np.isfinite(w).all() or not np.any(w):
        raise ValueError('sealed nonzero finite block44 probe direction required')
    items=[]
    for item_id,h in item_activations:
        h=np.asarray(h)
        if h.ndim!=2 or h.shape[1]!=5120 or not np.isfinite(h).all():
            raise ValueError('all valid prompt positions by5120 required')
        items.append({'id':item_id,**item_acf(np.asarray(h,dtype=np.float64)@w)})
    if len({x['id'] for x in items})!=len(items):raise ValueError('duplicate item ID')
    skipped=[x['id'] for x in items if x['status']=='SKIPPED_SHORT']
    eligible=[x for x in items if x['status']!='SKIPPED_SHORT']
    undefined=[x['id'] for x in eligible if x['status']!='EVALUABLE']
    if not eligible or undefined:
        return {'status':'NOT EVALUABLE','C':None,'reason':'no eligible items or undefined ACF in an eligible item',
                'undefined_items':undefined,'skipped_short_items':skipped,'n_skipped_short':len(skipped),'items':items}
    return {'status':'EVALUABLE','C':float(np.mean([x['mean_lag_acf'] for x in eligible])),
            'n_items':len(eligible),'n_items_total':len(items),'skipped_short_items':skipped,'n_skipped_short':len(skipped),'items':items}
