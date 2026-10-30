"""§226 R-SL0: paired signed-report difference-in-differences, before regression."""
import numpy as np
ROWS=('fact_recall','language_plan')
CELLS=('site_steered','site_random','carried_steered','carried_random')

def analyze(items):
    if len(items)!=168 or len({(x['row'],x['item_id']) for x in items})!=168:raise ValueError('full shared 2x84 census')
    out={};tests=[];rng=np.random.default_rng(20261029)
    for row in ROWS:
        xs=sorted([x for x in items if x['row']==row],key=lambda x:x['item_id'])
        if len(xs)!=84:raise ValueError('84 shared test items per row')
        for x in xs:
            if type(x['site_flip']) is not bool or type(x['carried_flip']) is not bool:raise ValueError('sealed steered behaviour flips')
            if set(x['scores'])!=set(CELLS) or any(v is not None and (type(v) is not int or v not in (-1,0,1)) for v in x['scores'].values()):raise ValueError('four signed scores')
        cohort=[x for x in xs if x['site_flip'] and x['carried_flip']];n=len(cohort)
        z=dict(n_shared=84,n_flipped_both=n,estimate=None,CI95=None,status='NOT EVALUABLE',cells={})
        if n:
            ix=rng.integers(0,n,(2000,n));points=[];draws=[]
            for c in CELLS:
                a=np.array([np.nan if x['scores'][c] is None else x['scores'][c] for x in cohort],float)
                kept=int(np.isfinite(a).sum());b=a[ix];counts=np.isfinite(b).sum(axis=1)
                point=float(np.nansum(a)/kept) if kept else None
                d=np.divide(np.nansum(b,axis=1),counts,out=np.full(2000,np.nan),where=counts>0)
                points.append(point);draws.append(d);z['cells'][c]=dict(S_target=point,kept=kept,missing=n-kept)
            if all(p is not None for p in points):
                z['delta_site']=points[0]-points[1];z['delta_carried']=points[2]-points[3]
                z['estimate']=z['delta_site']-z['delta_carried'];d=draws[0]-draws[1]-draws[2]+draws[3]
                if n>=2 and np.isfinite(d).all():
                    z['CI95']=np.quantile(d,[.025,.975]).tolist()
                    z['status']='MET' if z['estimate']>=.20 and z['CI95'][0]>0 else 'NOT MET'
        tests.append(z['status']);out[row]=z
    status='MET' if 'MET' in tests else 'NOT EVALUABLE' if 'NOT EVALUABLE' in tests else 'NOT MET'
    return dict(R_SL0=status,rows=out,bootstrap=dict(draws=2000,seed=20261029,unit='paired shared item',missing='cell-specific kept denominators; undefined draws invalidate CI'))

def figure(result,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(6,3))
    for i,row in enumerate(ROWS):
        z=result['rows'][row]
        if z['estimate'] is not None:
            ax.plot(z['estimate'],i,'o')
            if z['CI95'] is not None:ax.plot(z['CI95'],[i,i])
    ax.axvline(0,color='grey');ax.axvline(.2,color='grey',linestyle='--')
    ax.set_yticks(range(2),ROWS);ax.set_xlabel('Site minus carried: paired difference in S_target')
    fig.tight_layout();fig.savefig(path);plt.close(fig)
