"""§224 logistic MLE with row effects; paired source-item cluster bootstrap."""
from collections import Counter
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata

DRAWS=2000
SEED=20261029
EXPERIMENTS=('E104_U','E109_44','E101','E100_a')

def fit(X,y,weights=None):
    """Unpenalized MLE; rank/separation/convergence failures remain explicit."""
    w=np.ones(len(y)) if weights is None else np.asarray(weights,float)
    active=w>0
    if len(set(y[active]))<2 or np.linalg.matrix_rank(X[active])<X.shape[1]:return None,'rank_or_single_class'
    def objective(b):
        z=X@b
        return float(np.dot(w,np.logaddexp(0,z)-y*z)), X.T@(w*(expit(z)-y))
    opt=minimize(objective,np.zeros(X.shape[1]),jac=True,method='BFGS',options={'gtol':1e-7,'maxiter':1000})
    b=opt.x;p=expit(X@b);h=X.T@((w*p*(1-p))[:,None]*X)
    # Zero curvature or diverging coefficients indicates no identifiable finite MLE.
    if not np.isfinite(b).all() or np.max(np.abs(b))>40 or np.linalg.eigvalsh(h).min()<1e-8:return None,'separation_or_singular_information'
    if not opt.success and np.max(np.abs(objective(b)[1]))>1e-5:return None,'nonconvergence'
    return b,None

def auc(y,x):
    y=np.asarray(y);x=np.asarray(x);n1=int(y.sum());n0=len(y)-n1
    if not n1 or not n0:return None
    return float((rankdata(x)[y==1].sum()-n1*(n1+1)/2)/(n1*n0))

def rules(b1,b2,ci1,ci2,sds):
    if ci1 is None or ci2 is None or b1 is None or b2 is None:
        return {'R-SL1':'NOT EVALUABLE','falsifier':'NOT EVALUABLE'}
    site= b1>0 and ci1[0]>0
    includes=lambda ci:ci[0]<=0<=ci[1]
    ratio=abs(b1*sds[0])>=2*abs(b2*sds[1])
    return {'R-SL1':'MET' if site and (includes(ci2) or ratio) else 'NOT MET',
            'falsifier':'MET' if b2>0 and ci2[0]>0 and includes(ci1) else 'NOT MET',
            'site_positive_lower':bool(site),'behaviour_CI_includes_zero':includes(ci2),
            'standardized_magnitude_at_least_twice':bool(ratio)}

def model(records,draws=DRAWS):
    levels=sorted({r['row'] for r in records})
    if not records:return dict(status='NOT EVALUABLE',reason='empty analysis sample',rules=rules(None,None,None,None,[0,0]))
    y=np.array([r['y'] for r in records],float)
    raw=np.array([[r['x1'],r['x2']] for r in records],float)
    # SD definition frozen: population SD over the pooled kept observation sample.
    # For per-experiment descriptive models the same convention uses that sample.
    sds=raw.std(axis=0,ddof=0);scale=np.where(sds>0,sds,1.)
    X=np.column_stack([np.ones(len(y)),raw/scale]+[np.array([r['row']==k for r in records],float) for k in levels[1:]])
    b,err=fit(X,y)
    base=dict(n=len(y),items=len({r['cluster_id'] for r in records}),row_levels=levels,reference_row=levels[0],SD=sds.tolist(),SD_ddof=0,
              AUROC_x1_alone=auc(y,raw[:,0]),AUROC_x2_alone=auc(y,raw[:,1]),bootstrap=dict(draws=draws,seed=SEED,unit='source item including all controls and repeated experiments'))
    if err:return dict(base,status='NOT EVALUABLE',reason=err,rules=rules(None,None,None,None,sds))
    groups=sorted({r['cluster_id'] for r in records});lookup={g:i for i,g in enumerate(groups)}
    gi=np.array([lookup[r['cluster_id']] for r in records]);rng=np.random.default_rng(SEED);samples=[];fail=Counter()
    for _ in range(draws):
        w=np.bincount(rng.integers(0,len(groups),len(groups)),minlength=len(groups))[gi]
        bb,err=fit(X,y,w)
        if err:fail[err]+=1
        else:samples.append(bb[1:3]/scale)
    beta=b[1:3]/scale
    # Never discard failed replicates then assert a confirmatory CI.
    ci=np.quantile(samples,[.025,.975],axis=0).T.tolist() if not fail else [None,None]
    return dict(base,status='COMPLETE' if not fail else 'NOT EVALUABLE',coefficients=dict(x1=float(beta[0]),x2=float(beta[1])),
                standardized_coefficients=(beta*sds).tolist(),CI95=dict(x1=ci[0],x2=ci[1]),
                bootstrap_failures=dict(fail),valid_bootstrap_draws=len(samples),
                row_intercepts={k:float(b[0]+(0 if i==0 else b[2+i])) for i,k in enumerate(levels)},
                rules=rules(float(beta[0]),float(beta[1]),ci[0],ci[1],sds))

def bins(records):
    if not records:return []
    x=np.array([r['x1'] for r in records]);edges=np.unique(np.quantile(x,np.linspace(0,1,6)))
    ids=np.digitize(x,edges[1:-1],right=True);out=[]
    for i in sorted(set(ids)):
        for flip in (0,1):
            rs=[r for j,r in enumerate(records) if ids[j]==i and r['x2']==flip]
            if rs:out.append(dict(bin=int(i),behaviour_flip=flip,n=len(rs),mean_x1=float(np.mean([r['x1'] for r in rs])),y_rate=float(np.mean([r['y'] for r in rs]))))
    return out

def analyze(records,draws=DRAWS):
    if len({r['id'] for r in records})!=len(records):raise ValueError('duplicate observation')
    for r in records:
        if r['experiment'] not in EXPERIMENTS or r['y'] not in (None,0,1) or r['x2'] not in (0,1) or not np.isfinite(r['x1']):raise ValueError('invalid normalized observation')
    kept=[r for r in records if r['y'] is not None]
    return dict(experiment='E111',planned=len(records),kept=len(kept),UNPARSEABLE=len(records)-len(kept),
                pooled=model(kept,draws),R_SL2={e:dict(model=model([r for r in kept if r['experiment']==e],draws),bins=bins([r for r in kept if r['experiment']==e])) for e in EXPERIMENTS},
                pooled_bins=bins(kept),missing_by_experiment={e:sum(r['y'] is None for r in records if r['experiment']==e) for e in EXPERIMENTS})

def figure(result,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(12,7),squeeze=False)
    panels=[('Pooled',result['pooled_bins'])]+[(e,result['R_SL2'][e]['bins']) for e in EXPERIMENTS]
    for ax,(name,data) in zip(axes.flat,panels):
        for flip,color in [(0,'#4267ac'),(1,'#cc6335')]:
            bs=[x for x in data if x['behaviour_flip']==flip]
            ax.scatter([x['mean_x1'] for x in bs],[x['y_rate'] for x in bs],color=color,label=f'Flip {flip}')
        ax.set(title=name,xlabel='Site shift (binned)',ylabel='Target-statement rate',ylim=(-.03,1.03));ax.legend()
    axes.flat[-1].set_visible(False)
    fig.tight_layout();fig.savefig(path);plt.close(fig)
