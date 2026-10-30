"""§231 POST HOC exploratory matched read-site displacement, no confirmatory rule."""
import numpy as np
from projects.g_agreement.understand.wmech2 import core as c

def features(h,hp,w,target):
    h,hp,w=map(lambda x:np.asarray(x,float),(h,hp,w))
    c.require(h.ndim==1 and h.shape==hp.shape==w.shape and all(np.isfinite(x).all() for x in (h,hp,w)),'aligned finite source vectors')
    c.require(target in (0,1) and np.linalg.norm(w)>0,'oriented nonzero probe')
    d=hp-h;shift=float((2*target-1)*np.dot(w,d))
    return dict(displacement_norm=float(np.linalg.norm(d)),probe_projection=shift/float(np.linalg.norm(w)),probe_logit_shift=shift)

def analyze(rows):
    c.unique(rows)
    c.require(all(x['experiment'] in ('E101','E104_U') and (x['y'] is None or x['y'] in (0,1)) for x in rows),'site/carried source only')
    result={}
    for row in sorted({x['row'] for x in rows}):
        xs=[x for x in rows if x['row']==row];result[row]={}
        c.require({x['experiment'] for x in xs}=={'E101','E104_U'},'both groups per row')
        for axis in ('probe_logit_shift','displacement_norm'):
            values=np.array([x[axis] for x in xs],float);c.require(np.isfinite(values).all(),'finite matched feature')
            # Five pooled quantile bins, fixed here before this post-hoc calculation.
            # Unique interior boundaries avoid splitting ties; right-closed via searchsorted.
            edges=np.unique(np.quantile(values,[.2,.4,.6,.8]));bins=[]
            for k in range(len(edges)+1):
                group=[x for x in xs if np.searchsorted(edges,x[axis],side='left')==k];arms={}
                for experiment in ('E101','E104_U'):
                    arm=[x for x in group if x['experiment']==experiment];known=[x for x in arm if x['y'] is not None]
                    arms[experiment]=dict(total=len(arm),kept=len(known),missing=len(arm)-len(known),report_rate=sum(x['y'] for x in known)/len(known) if known else None)
                a,b=arms['E101'],arms['E104_U'];matched=a['kept']>0 and b['kept']>0
                bins.append(dict(index=k,lower=None if k==0 else float(edges[k-1]),upper=None if k==len(edges) else float(edges[k]),arms=arms,matched=matched,gap=a['report_rate']-b['report_rate'] if matched else None,weight=min(a['kept'],b['kept']) if matched else 0))
            weight=sum(b['weight'] for b in bins)
            result[row][axis]=dict(boundaries=edges.tolist(),bins=bins,overlap_weighted_gap=sum(b['gap']*b['weight'] for b in bins if b['matched'])/weight if weight else None,overlap_weight=weight)
    return dict(experiment='E111',part='d',status='POST HOC EXPLORATORY',authority='§231',rows=result,method='Separate within-row pooled quintile bins for logit shift and displacement norm; tied boundaries collapsed; unmatched bins retained, not pooled; gap weights min(known site,known carried)',interpretation='Persistent gaps indicate matched features do not capture reader response, not knowledge of intervention history; closing gaps are compatible with a dose difference. No confirmatory threshold or p-value.')
