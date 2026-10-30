"""Pure label-free policies; scalar values only, source normalization is separate."""
from collections import Counter
import math
import numpy as np
LAYERS=(44,52,60)
FIXED=('P44','P52','P60')
ADAPTIVE=('PALL','PLATE','PSTAB','PAGREE')
RULES=FIXED+ADAPTIVE
DRAWS=2000
SEED=20261030

def predict(rule, readings):
    """Absent key = unavailable layer; None = available but no scalar assertion."""
    if rule not in RULES: raise ValueError('unknown rule')
    if any(k not in LAYERS for k in readings): raise ValueError('unexpected layer')
    if any(v is not None and not isinstance(v,str) for v in readings.values()): raise ValueError('scalar string or None required')
    if rule in FIXED:return readings.get(int(rule[1:]))
    ordered=[readings[l] for l in LAYERS if l in readings]
    stated=[v for v in ordered if v is not None]
    if not stated:return None
    if rule=='PLATE':return stated[-1]
    if rule=='PAGREE':return stated[0] if len(set(stated))==1 else None
    if rule=='PALL':
        counts=Counter(stated); maximum=max(counts.values())
        return next(v for v in reversed(stated) if counts[v]==maximum)
    # Consecutive available layer positions, not consecutive nonempty assertions.
    for a,b in zip(ordered,ordered[1:]):
        if a is not None and a==b:return a
    return stated[-1]

def wilson(k,n):
    if n==0:return None
    z=1.959963984540054; p=k/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0.,c-h),min(1.,c+h)]

def score(rows,rule,draws=DRAWS,seed=SEED,include_truth_strata=True):
    if len({x['id'] for x in rows})!=len(rows):raise ValueError('duplicate item')
    # Missing fixed-layer capture is not silently converted into a reader abstention.
    eligible=[x for x in rows if rule not in FIXED or int(rule[1:]) in x['readings']]
    if any(not isinstance(x['truth'],str) for x in eligible):raise ValueError('bound scalar truth required')
    n=len(eligible)
    if not n:return dict(total=len(rows),eligible=0,unavailable=len(rows),metrics=None)
    pred=[predict(rule,x['readings']) for x in eligible]
    arr=np.array([[p==x['truth'],p is not None and p!=x['truth'],p is not None] for p,x in zip(pred,eligible)],dtype=float)
    groups={}
    for j,x in enumerate(eligible):groups.setdefault(x.get('item_id',x['id']),[]).append(j)
    mask=np.array([x.get('accuracy_eligible',True) for x in eligible],dtype=bool)
    if any(type(x.get('accuracy_eligible',True)) is not bool for x in eligible):raise ValueError('accuracy eligibility boolean')
    units=list(groups.values());rng=np.random.default_rng(seed);boot=np.full((draws,3),np.nan)
    for j in range(draws):
        indices=[ix for unit in rng.integers(0,len(units),len(units)) for ix in units[unit]]
        boot[j,1:]=arr[indices,1:].mean(axis=0)
        ai=np.array(indices)[mask[indices]]
        if len(ai):boot[j,0]=arr[ai,0].mean()
    metrics={}
    for j,name in enumerate(('accuracy','false_claim_rate','coverage')):
        selected=arr[mask,j] if j==0 else arr[:,j];denom=len(selected);k=int(selected.sum());valid=boot[:,j][np.isfinite(boot[:,j])]
        metrics[name]=dict(count=k,denominator=denom,estimate=k/denom if denom else None,Wilson95=wilson(k,denom),item_bootstrap95=np.quantile(valid,[.025,.975]).tolist() if len(valid) else None,defined_bootstrap_draws=len(valid),undefined_bootstrap_draws=draws-len(valid))
    result=dict(total=len(rows),eligible=n,unavailable=len(rows)-n,metrics=metrics)
    if include_truth_strata:
        bases=tuple(sorted({x.get('truth_basis','behaviour-verified') for x in rows}))
        result['truth_basis_scores']={basis:score([x for x in rows if x.get('truth_basis','behaviour-verified')==basis],rule,draws,seed,False) for basis in bases}
        result['truth_basis_scope']='MIXED; see separate strata' if len(bases)>1 else bases[0]
    return result

def choose(scores,rules,types):
    # Equal state-type weights; no selection by sample count or held-out labels.
    evaluable=[r for r in rules if all(scores[t][r]['metrics'] is not None and scores[t][r]['metrics']['accuracy']['estimate'] is not None for t in types)]
    if not evaluable:raise ValueError('no candidate evaluable on every training type')
    values={r:float(np.mean([scores[t][r]['metrics']['accuracy']['estimate'] for t in types])) if r in evaluable else None for r in rules}
    return max(evaluable,key=lambda r:values[r]),values

def evaluate(by_type,draws=DRAWS):
    if set(by_type)!={f'T{i}' for i in range(1,7)}:raise ValueError('exact T1-T6 required; T7 never enters selection')
    from .matcher import coverage_gate
    gate=coverage_gate(by_type['T4'])
    types=tuple(t for t in sorted(by_type) if t!='T4' or gate['passes']); scores={t:{r:score(by_type[t],r,draws) for r in RULES} for t in sorted(by_type)}
    if not gate['passes']:
        for r in ('PAGREE','PSTAB'):
            scores['T4'][r]=dict(total=len(by_type['T4']),eligible=0,unavailable=0,metrics=None,status='NOT_EVALUABLE',reason='T4 exact-one matcher coverage below 70% at a compared block')
    loo={}
    for held in types:
        train=[t for t in types if t!=held]; a,av=choose(scores,ADAPTIVE,train);f,fv=choose(scores,FIXED,train)
        am=scores[held][a]['metrics'];fm=scores[held][f]['metrics']
        delta=am['accuracy']['estimate']-fm['accuracy']['estimate'] if am is not None and fm is not None and am['accuracy']['estimate'] is not None and fm['accuracy']['estimate'] is not None else None
        loo[held]=dict(training_types=train,adaptive=a,fixed=f,adaptive_training_mean=av,fixed_training_mean=fv,heldout_adaptive=scores[held][a],heldout_fixed=scores[held][f],accuracy_difference=delta)
    a,av=choose(scores,ADAPTIVE,types);f,fv=choose(scores,FIXED,types)
    return dict(T4_matcher=gate,selection_types=list(types),excluded_selection_types=[] if gate['passes'] else ['T4'],scores=scores,leave_one_type_out=loo,selection=dict(adaptive=a,fixed=f,adaptive_type_means=av,fixed_type_means=fv),reading=dict(improvements_at_least_point10=sum(x['accuracy_difference'] is not None and x['accuracy_difference']>=.10-1e-12 for x in loo.values()),nonpositive=sum(x['accuracy_difference'] is not None and x['accuracy_difference']<=0 for x in loo.values()),not_evaluable=sum(x['accuracy_difference'] is None for x in loo.values())),bootstrap=dict(draws=draws,seed=SEED,unit='original item within state type, conditions clustered',selection_refit=False),exploratory=True)
