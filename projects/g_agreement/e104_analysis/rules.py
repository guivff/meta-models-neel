"""§213 rules: same E101 estimands/cohort, E101+1 seeds, shared stats backend."""
import numpy as np
from common.stats import bootstrap_ci
ROWS=('fact_recall','language_plan')
ARMS=('U','N')
DRAWS,SEED=2000,20261028

def statistic(values,other=None):
    ids=sorted(values)
    if other is not None and set(other)!=set(ids):raise ValueError('paired item identities')
    a=np.array([np.nan if values[i] is None else values[i] for i in ids],float)
    b=None if other is None else np.array([np.nan if other[i] is None else other[i] for i in ids],float)
    def mean(x):return float(np.nanmean(x)) if np.isfinite(x).any() else np.nan
    def fn(ix):return mean(a[ix])-(0 if b is None else mean(b[ix]))
    if not ids:return {'estimate':None,'CI95':None}
    point,lo,hi=bootstrap_ci(np.arange(len(ids)),fn=fn,n_boot=DRAWS,seed=SEED)
    return dict(estimate=point if np.isfinite(point) else None,CI95=[lo,hi] if np.isfinite([lo,hi]).all() else None)

def threshold(stat,value,upper=False):
    if stat['estimate'] is None or stat['CI95'] is None:return None
    return bool(round(stat['estimate'],12)<=value and stat['CI95'][1]<.30) if upper else bool(round(stat['estimate'],12)>=value and stat['CI95'][0]>0)

def rule(tests,all_required=False):
    if not tests:return dict(status='NOT EVALUABLE',eligible=0,reason='no arm/row reaches alpha*')
    p=sum(x is True for x in tests);u=sum(x is None for x in tests);required=len(tests) if all_required else 1
    return dict(status='MET' if p>=required else 'NOT EVALUABLE' if p+u>=required else 'NOT MET',eligible=len(tests),passing=p,unknown=u,required=required)

def analyze(records,selected):
    out=dict(experiment='E104',authority='§213 / 5e075c6a',bootstrap=dict(draws=DRAWS,seed=SEED,unit='item',paired=True,backend='common/stats.py'),cohort='steered_flipped',arms={},rules={})
    tests={};falsifiers=[]
    for arm in ARMS:
        out['arms'][arm]={};tests[arm]=[]
        for row in ROWS:
            alpha=selected[f'{arm}:{row}']['alpha']
            if alpha is None:
                out['arms'][arm][row]=dict(status='NOT EVALUABLE',reason='no dev dose reaches70%',alpha=None);continue
            xs=[x for x in records if x['arm']==arm and x['row']==row]
            st={x['item_id']:x for x in xs if x['condition']=='steered'};ra={x['item_id']:x for x in xs if x['condition']=='random'}
            if len(st)!=84 or set(st)!=set(ra):raise ValueError('full paired84 test items')
            cohort={i for i,x in st.items() if x['flipped']}
            sv={i:x['score'] if i in cohort else None for i,x in st.items()};rv={i:x['score'] if i in cohort else None for i,x in ra.items()}
            delta=statistic(sv,rv)
            z=dict(status='EVALUABLE',alpha=alpha,B=statistic({i:int(x['flipped']) for i,x in st.items()}),B_random=statistic({i:int(x['flipped']) for i,x in ra.items()}),
                S_target=statistic(sv),S_random=statistic(rv),difference=delta,S_all_steered=statistic({i:x['score'] for i,x in st.items()}),S_all_random=statistic({i:x['score'] for i,x in ra.items()}),
                test_n=84,flipped_n=len(cohort),excluded_not_flipped=84-len(cohort),missing={},norms={})
            for condition,values in [('steered',st),('random',ra)]:
                missing=sum(x['score'] is None for x in values.values());masked=sum(values[i]['score'] is None for i in cohort)
                z['missing'][condition]=dict(all_test=missing,flipped_cohort=masked,cohort_kept=len(cohort)-masked,cohort_over5percent=bool(cohort) and masked/len(cohort)>.05)
                z['norms'][condition]={i:dict(norm_ratio=x['norm_ratio'],norm_over_1_5=x['norm_ratio']>1.5,read_norm_ratio=x['read_norm_ratio']) for i,x in values.items()}
            out['arms'][arm][row]=z;tests[arm].append(threshold(delta,.30));falsifiers.append(threshold(delta,.10,upper=True))
    out['rules']={'R-U1':rule(tests['U']),'R-N1':rule(tests['N']),'falsifier':rule(falsifiers,all_required=True)}
    out['interpretation']='the lens reads the injected write at large norm' if out['rules']['falsifier']['status']=='MET' else 'see registered arm rules; no automatic claim from NOT EVALUABLE'
    return out
