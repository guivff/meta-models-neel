"""§214: fixed T-donor orientation; paired item contrast and baseline sign flips."""
import numpy as np
from common.stats import bootstrap_ci
POSITIVE=('format_plan','language_plan','fact_recall')
MISSED=('nesting_depth','indent_level','page_range_digit')
ROWS=POSITIVE+MISSED
DRAWS,SEED=2000,20261027

def statistic(values):
    x=np.asarray(values,float)
    if not len(x):return dict(estimate=None,CI95=None,n=0)
    if not np.isfinite(x).all():raise ValueError('non-finite contrast; never drop test items')
    point,lo,hi=bootstrap_ci(x,n_boot=DRAWS,seed=SEED)
    return dict(estimate=point,CI95=[lo,hi],n=len(x))

def count(tests,n):
    p=sum(x is True for x in tests);u=sum(x is None for x in tests)
    return dict(status='MET' if p>=n else 'NOT EVALUABLE' if p+u>=n else 'NOT MET',passing=p,unknown=u,required=n)

def evaluate(stats):
    completed=validate_completed(stats)
    def positive(row):
        d=stats[row]['delta']
        return None if d['estimate'] is None or d['CI95'] is None else bool(d['estimate']>0 and d['CI95'][0]>0)
    gate=count([positive(r) for r in POSITIVE if r in completed],2)
    tests=[];falsifiers=[]
    for row in MISSED:
        if row not in completed:
            falsifiers.append(None)
            continue
        good=positive(row);rate=stats[row]['flip_difference']['estimate'];ci=stats[row]['delta']['CI95']
        tests.append(False if good is False or rate is not None and round(rate,12)<.20 else None if good is None or rate is None else True)
        falsifiers.append(None if ci is None else bool(ci[0]<=0))
    result=count(tests,2)
    if gate['status']!='MET':result=dict(status='NOT EVALUABLE',reason='positive-control gate not met',ungated=result)
    return dict(positive_control_gate=gate,**{'R-BT1':result},falsifier=count(falsifiers,3))

def validate_completed(rows):
    rows=set(rows)
    if not set(ROWS)-{'indent_level','fact_recall'}<=rows<=set(ROWS):
        raise ValueError('only amendment2 restart rows may be NOT RUN')
    return rows

def analyze(records,completed_rows=ROWS):
    completed=validate_completed(completed_rows)
    if {x['row'] for x in records}!=completed:raise ValueError('exact completed row set')
    result=dict(experiment='E105',authority='§214 with amendment2',bootstrap=dict(draws=DRAWS,seed=SEED,unit='item',paired=True,backend='common/stats.py'),
                contrast_orientation='T donor value minus other, fixed across T/S/0',flip_definition='strict sign reversal relative to own unpatched baseline; zeros are not flips',rows={})
    for row in ROWS:
        if row not in completed:continue
        xs=sorted([x for x in records if x['row']==row],key=lambda x:x['item_id'])
        if len(xs)!=84 or len({x['item_id'] for x in xs})!=84:raise ValueError('exact84 unique test items each row')
        c={condition:np.array([x['contrasts'][condition] for x in xs],float) for condition in ('T','S','0')}
        if not all(np.isfinite(v).all() for v in c.values()):raise ValueError('non-finite contrast')
        flips={k:((c[k]>0)&(c['0']<0))|((c[k]<0)&(c['0']>0)) for k in ('T','S')}
        result['rows'][row]=dict(delta=statistic(c['T']-c['S']),contrasts={k:statistic(v) for k,v in c.items()},
            flip_T=statistic(flips['T'].astype(float)),flip_S=statistic(flips['S'].astype(float)),flip_difference=statistic(flips['T'].astype(float)-flips['S'].astype(float)),
            baseline_ties=int((c['0']==0).sum()),T_ties=int((c['T']==0).sum()),S_ties=int((c['S']==0).sum()),n=84)
    result['not_run_operational']=[r for r in ROWS if r not in completed]
    result['rules']=evaluate(result['rows'])
    result['caveats']=['nesting_depth prefix bias and page_range_digit0/84 baseline affect sign flips, not the paired continuous delta','R-BT1 includes the registered flip-difference>=.20 condition; no additional CI gate is imposed on that difference']
    result['interpretation']='the transplanted bookkeeping value is not used at this site; E100 missed-row silence is not evidence of a reader-side blind spot' if result['rules']['falsifier']['status']=='MET' else 'see positive-control gate and R-BT1; no reader-side claim if gate fails'
    return result
