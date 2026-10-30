"""§172 clarification2, 3ada24fb. Whole-item percentile bootstrap, no pseudoreplication."""
import numpy as np

def signed_value(judgment,label):
    if judgment['category']!='states_value':return 0
    values=judgment['values']
    correct='A' if label==1 else 'B'
    return 1 if values==[correct] else (-1 if len(values)==1 else 0)

def rate(item_values):
    x=np.asarray(item_values,float)
    if x.ndim!=2 or x.shape[1]!=1 or not len(x) or not np.isin(x,[-1,0,1]).all():raise ValueError('item x one signed grid')
    means=x.mean(axis=1);rng=np.random.default_rng(20261027)
    boot=means[rng.integers(0,len(means),size=(2000,len(means)))].mean(axis=1)
    return {'S':float(means.mean()),'CI95':np.quantile(boot,[.025,.975]).tolist(),'items':len(means),'readouts':x.size,'bootstrap_draws':2000,'bootstrap_seed':20261027}

def reported(r,threshold=.2):return r['S']>=threshold and r['CI95'][0]>0

def paired_ci(a,b):
    d=np.asarray(a,float)-np.asarray(b,float)
    if d.ndim!=1 or not len(d):raise ValueError('paired item differences')
    rng=np.random.default_rng(20261027)
    return np.quantile(d[rng.integers(0,len(d),size=(2000,len(d)))].mean(axis=1),[.025,.975]).tolist()
