"""E94 value-code validation, generalized to two layers of one reader (§233)."""
from collections import Counter
import numpy as np
from results.g_agreement.understand.e94.score94 import value_class, fraction, require

ROWS={'fact_recall':84,'language_plan':50}
CONDITIONS=('steered','random','unhooked')
LAYERS=(44,52)
DRAWS=2000
SEED=20261028  # unchanged E94 item-bootstrap seed


def values(code):
    # Retain values, rather than E94's collapsed correct/wrong/no-mention class.
    value_class(code,'A')
    return None if code['category']=='UNPARSEABLE' else frozenset(code['values'])


def disagreement(left,right):
    a,b=values(left),values(right)
    if a is None or b is None:return None
    return int(a!=b)  # unequal stated sets, or exactly one states a value


def stale(code,old):
    require(old in ('A','B'),'original binary old value')
    v=values(code)
    # E109/core.score singleton old-value criterion; dual-value reports are not
    # exclusive old-value reports, but remain stated values for disagreement.
    return None if v is None else int(v==frozenset([old]))


def auc(positive,negative):
    if not positive or not negative:return None
    # Exact Mann-Whitney AUROC for a binary score, with half credit for ties.
    return float((np.mean(positive)+1-np.mean(negative))/2)


def disposition(estimate,ci,fpr):
    if estimate is None or ci is None or fpr is None:return 'NOT EVALUABLE'
    return 'MET' if estimate>=.80 and ci[0]>.70 and fpr<=.15 else 'NOT MET'


def summarize(records,draws=DRAWS):
    require(len(records)==len({x['item_id'] for x in records}) and bool(records),'unique source items')
    require(type(draws)is int and draws>0,'positive bootstrap draws')
    units=[];audit={c:Counter() for c in CONDITIONS}
    for item in records:
        require(item['old_value'] in ('A','B') and set(item['conditions'])==set(CONDITIONS),'old value/full conditions')
        u={'item_id':item['item_id']}
        for c in CONDITIONS:
            codes=item['conditions'][c]
            require(set(codes)=={'44','52'},'exact two source layers')
            d=disagreement(codes['44'],codes['52']);is_stale=stale(codes['44'],item['old_value'])
            u[c]=(d,is_stale)
            audit[c]['planned_items']+=1
            audit[c]['missing_44']+=values(codes['44']) is None
            audit[c]['missing_52']+=values(codes['52']) is None
            audit[c]['either_layer_missing']+=d is None
            audit[c]['parseable_pairs']+=d is not None
            audit[c]['known_stale_44']+=is_stale==1
            audit[c]['unknown_stale_44']+=is_stale is None
            audit[c]['stale_score_missing']+=is_stale==1 and d is None
        units.append(u)

    def scores(sample):
        positive=[x['steered'][0] for x in sample if x['steered'][1]==1 and x['steered'][0] is not None]
        negative=[x['unhooked'][0] for x in sample if x['unhooked'][0] is not None]
        random=[x['random'][0] for x in sample if x['random'][0] is not None]
        return positive,negative,random
    pos,neg,rnd=scores(units);estimate=auc(pos,neg)
    rng=np.random.default_rng(SEED);samples=[]
    for _ in range(draws):
        picked=[units[i] for i in rng.integers(0,len(units),len(units))]
        pp,nn,_=scores(picked);v=auc(pp,nn)
        if v is not None:samples.append(v)
    ci=np.quantile(samples,[.025,.975]).tolist() if samples else None
    fpr=fraction(sum(neg),len(neg));tpr=fraction(sum(pos),len(pos))
    status=disposition(estimate,ci,fpr['rate'])
    met=status=='MET'
    return dict(n_source_items=len(units),missing={c:dict(v) for c,v in audit.items()},
                AUROC=dict(estimate=estimate,CI95=ci,n_stale=len(pos),n_unhooked=len(neg),binary_score=True,ties='half credit'),
                false_positive_rate=fpr,stale_detection_rate=tpr,
                random_direction_control=dict(disagreement=fraction(sum(rnd),len(rnd)),AUROC_vs_unhooked=auc(rnd,neg),decision_rule=False),
                R_DIS1=status,
                reading='not usable' if estimate is not None and estimate<=.60 else 'usable staleness flag' if met else 'registered usability criterion not established',
                bootstrap=dict(draws=draws,defined_draws=len(samples),undefined_draws=draws-len(samples),seed=SEED,unit='source item; all conditions/layers resampled together',CI='paired item percentile95'),
                handling='UNPARSEABLE excluded only from affected pair; never zero. Steered non-stale excluded from positive class; all parseable unhooked retained. No complete-case filter across conditions.')


def analyze(data,draws=DRAWS):
    require(set(data)==set(ROWS),'both registered rows')
    for row,n in ROWS.items():require(len(data[row])==n,'original sealed row cohort size')
    return dict(experiment='E123',reader='oracle',layers=list(LAYERS),rows={row:summarize(data[row],draws) for row in ROWS},
                decision_scope='R-DIS1 separately per row; random direction descriptive; no pooled or best-layer selection',
                rule=dict(AUROC_min=.80,AUROC_lower_strictly_above=.70,unhooked_FPR_max=.15,unusable_AUROC_max=.60))
