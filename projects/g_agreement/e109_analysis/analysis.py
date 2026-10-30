"""§222: dev-only logistic probes and sealed-cohort paired Oracle reports."""
import warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from common.stats import wilson
from projects.g_agreement.e104_analysis.rules import statistic,rule
ROWS=('fact_recall','language_plan');LAYERS=(44,48,52,56,60);READS=(44,52,60)

def fit(dev,labels):
    x=np.asarray(dev,dtype=float);y=np.asarray(labels)
    if x.ndim!=2 or len(x)!=84 or y.shape!=(84,) or set(y)!={0,1} or not np.isfinite(x).all():raise ValueError('84 finite unhooked dev and binary labels')
    # Same fixed C/max_iter/seed as common.probes.fit_logistic_probe. No test fitting.
    model=LogisticRegression(C=1.,max_iter=2000,random_state=0,solver='lbfgs')
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning);model.fit(x,y)
    return model

def classify_rules(probes,oracle,old44):
    arrival=[];decoder=[];never=[];falsifier=[];per={}
    for row in ROWS:
        p=probes[row];s=oracle[row]
        tests=[p[l]>=.70 and s[l]['estimate']>=.30 and s[l]['CI95'][0]>0 if s[l]['estimate'] is not None and s[l]['CI95'] is not None else None for l in (52,60)]
        ar1=rule(tests);ar2=p[44]>=.70 and old44[row]<.30;ar3=all(p[l]<.50 for l in LAYERS)
        f=None if s[44]['estimate'] is None or s[44]['CI95'] is None else p[44]>=.70 and s[44]['estimate']>=.30 and s[44]['CI95'][0]>0
        per[row]={'R-AR1':ar1,'R-AR2':rule([bool(ar2)]),'R-AR3':rule([bool(ar3)]),'falsifier':rule([None if f is None else bool(f)])}
        arrival.extend(tests);decoder.append(bool(ar2));never.append(bool(ar3));falsifier.append(None if f is None else bool(f))
    return dict(per_row=per,**{'R-AR1':rule(arrival),'R-AR2':rule(decoder),'R-AR3':rule(never),'falsifier':rule(falsifier)})

def analyze(data,old44):
    out={};ps={};os={}
    for row in ROWS:
        d=data[row];ids=d['test_ids'];cohort=set(d['cohort']);n=84 if row=='fact_recall' else 50
        if len(ids)!=84 or len(set(ids))!=84 or len(d['dev_ids'])!=84 or set(ids)&set(d['dev_ids']) or len(cohort)!=n or not cohort<=set(ids):raise ValueError('original dev/test/cohort identities')
        targets=np.asarray(d['targets']);mask=np.array([i in cohort for i in ids]);ps[row]={};os[row]={};out[row]={}
        if targets.shape!=(84,) or not set(targets)<={0,1}:raise ValueError('binary original steered targets')
        if set(d['layers'])!=set(LAYERS):raise ValueError('all five capture layers')
        for layer in LAYERS:
            z=d['layers'][layer];model=fit(z['dev_unhooked'],d['dev_labels']);report={'probe':{}}
            for cond in ('unhooked','steered','random'):
                x=np.asarray(z['test'][cond],float)
                if x.shape!=(84,model.n_features_in_) or not np.isfinite(x).all():raise ValueError('full finite hooked/unhooked test')
                k=int((model.predict(x)[mask]==targets[mask]).sum());p,lo,hi=wilson(k,n)
                report['probe'][cond]=dict(flips=k,n=n,estimate=p,CI95=[lo,hi])
            ps[row][layer]=report['probe']['steered']['estimate']
            if layer in READS:
                cells=z['oracle'];sv={i:cells['steered'][j] for j,i in enumerate(ids) if i in cohort};rv={i:cells['random'][j] for j,i in enumerate(ids) if i in cohort}
                if any(len(cells[c])!=84 for c in ('steered','random')):raise ValueError('full Oracle grid')
                report['oracle']=dict(steered=statistic(sv),random=statistic(rv),difference=statistic(sv,rv),missing={c:sum(v is None for v in vs.values()) for c,vs in [('steered',sv),('random',rv)]})
                os[row][layer]=report['oracle']['difference']
            elif 'oracle' in z:raise ValueError('no Oracle at48/56')
            out[row][layer]=report
    return dict(experiment='E109',rows=out,rules=classify_rules(ps,os,old44),bootstrap=dict(draws=2000,seed=20261028,unit='sealed-cohort paired item'),probe=dict(C=1,max_iter=2000,seed=0,solver='lbfgs',fit='unhooked dev only',scaling='none'),E104_sealed_difference=old44)
