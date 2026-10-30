"""Frozen E96 arithmetic; no filesystem reads, labels or analysis on import.

S is correct-only minus wrong-only. Both values and silence score0. Registered
item bootstraps pair each scaffold with the same item's saved greedy score.
R-SC1 requires one reader/aggregator to qualify on three distinct MISSED rows;
rows cannot be accumulated across different aggregators or readers.
"""
import hashlib
import numpy as np

SEED=20261028
DRAWS=2000


def seed_for(key):return SEED+int.from_bytes(hashlib.sha256(key.encode()).digest()[:4],'big')


def signed(values,truth):
    if values is None:return None
    if truth not in ('A','B') or any(v not in ('A','B') for v in values) or len(set(values))!=len(values):raise ValueError('canonical A/B codes required')
    if len(values)!=1:return 0
    return 1 if values[0]==truth else -1


def paired(scaffold,greedy,key):
    if len(scaffold)!=len(greedy):raise ValueError('paired item grid')
    pairs=[(s,g) for s,g in zip(scaffold,greedy) if s is not None and g is not None]
    if len(pairs)<2:return {'status':'NOT EVALUABLE','n':len(pairs),'reason':'fewer than2 jointly resolved items'}
    x=np.asarray(pairs,dtype='float64');delta=x[:,0]-x[:,1];rng=np.random.default_rng(seed_for(key));means=[]
    for start in range(0,DRAWS,100):
        ix=rng.integers(len(delta),size=(min(100,DRAWS-start),len(delta)));means.extend(delta[ix].mean(axis=1))
    return {'status':'EVALUABLE','n':len(pairs),'S_scaffold':float(x[:,0].mean()),'S_greedy':float(x[:,1].mean()),'delta':float(delta.mean()),'CI95':np.quantile(means,[.025,.975]).tolist(),'draws':DRAWS,'seed':seed_for(key),'dropped_unresolved_pairs':len(scaffold)-len(pairs)}


def rules(rows):
    # One row entry per bank/property/reader; each has majority/recon comparisons.
    units=[]
    for reader in ('oracle','nla'):
        for aggregator in ('majority','recon'):
            missed=[r for r in rows if r['reader']==reader and r['greedy_status']=='MISSED']
            qualifying=[r for r in missed if r[aggregator]['status']=='EVALUABLE' and r[aggregator]['delta']>=.15 and r[aggregator]['CI95'][0]>0]
            missing=[r for r in missed if r[aggregator]['status']!='EVALUABLE']
            count=len(qualifying)
            status='MET' if count>=3 else 'NOT EVALUABLE' if count+len(missing)>=3 else 'NOT MET'
            units.append({'reader':reader,'aggregator':aggregator,'status':status,'qualifying_rows':[r['bank']+'/'+r['row'] for r in qualifying],'count':count,'greedy_MISSED_rows':len(missed),'missing_rows':[r['bank']+'/'+r['row'] for r in missing]})
    rsc='MET' if any(u['status']=='MET' for u in units) else 'NOT EVALUABLE' if any(u['status']=='NOT EVALUABLE' for u in units) else 'NOT MET'
    violations=[];unknown=[]
    for r in rows:
        for agg in ('majority','recon'):
            d=r[agg]
            if d['status']!='EVALUABLE':unknown.append([r['bank'],r['row'],r['reader'],agg]);continue
            if (r['greedy_status']=='MISSED' and d['delta']>=.10) or (r['greedy_status']=='REPORTED' and abs(d['delta'])>.10):violations.append([r['bank'],r['row'],r['reader'],agg,d['delta']])
    falsifier='NOT MET' if violations else 'NOT EVALUABLE' if unknown else 'MET'
    hypotheses=[]
    for reader in ('oracle','nla'):
        for agg in ('majority','recon'):
            selected=[r for r in rows if r['reader']==reader]
            groups={label:[r[agg]['delta'] for r in selected if r['J_group']==label and r[agg]['status']=='EVALUABLE'] for label in ('IN-J','OUT-J')}
            if not all(groups.values()):hypotheses.append({'reader':reader,'aggregator':agg,'status':'NOT EVALUABLE','reason':'missing IN-J or OUT-J group'});continue
            difference=float(np.mean(groups['IN-J'])-np.mean(groups['OUT-J']))
            hypotheses.append({'reader':reader,'aggregator':agg,'status':'MET' if difference>=.10 else 'NOT MET','mean_delta_IN_J':float(np.mean(groups['IN-J'])),'mean_delta_OUT_J':float(np.mean(groups['OUT-J'])),'difference':difference,'rows_IN_J':len(groups['IN-J']),'rows_OUT_J':len(groups['OUT-J']),'missing_rows':sum(r[agg]['status']!='EVALUABLE' for r in selected),'is_decision_rule':False})
    return {'R_SC1':{'status':rsc,'strata':units},'falsifier':{'status':falsifier,'violations':violations,'missing_cells':unknown},'H_SC2':hypotheses}
