"""§248 A: paired coverage/precision/unconditional comparison, missing stays missing."""
import numpy as np
N=199
DRAWS=5000
SEED=0

def interval(a):
    return np.quantile(a,[.025,.975]).tolist() if len(a) else None

def summary(named,belief):
    known=np.isfinite(named)&np.isfinite(belief)
    n=int(known.sum()); named_n=int(named[known].sum()); hits=int(belief[known].sum())
    return dict(planned=N,observed=n,missing=N-n,abstention=n-named_n,states_value=named_n,states_belief=hits,
        coverage_observed=named_n/n if n else None,precision=hits/named_n if named_n else None,
        unconditional_observed=hits/n if n else None,
        # These are bounds on the full 199, not point estimates treating missing as zero.
        coverage_full199_bounds=[named_n/N,(named_n+N-n)/N],
        unconditional_full199_bounds=[hits/N,(hits+N-n)/N])

def difference(a,b,draws):
    known=np.isfinite(a)&np.isfinite(b)
    d=a[known]-b[known]
    complete=dict(kept=int(known.sum()),estimate=float(d.mean()) if len(d) else None,CI95=None)
    if len(d):
        rng=np.random.default_rng(SEED)
        complete['CI95']=interval(d[rng.integers(0,len(d),(DRAWS,len(d)))].mean(1))
    # Joint original-199 resampling; each output retains its own observed denominator.
    aa=a[draws];bb=b[draws]
    ka=np.isfinite(aa).sum(1);kb=np.isfinite(bb).sum(1);valid=(ka>0)&(kb>0)
    vals=np.nansum(aa[valid],1)/ka[valid]-np.nansum(bb[valid],1)/kb[valid]
    na=np.isfinite(a).sum();nb=np.isfinite(b).sum()
    observed=dict(estimate=float(np.nansum(a)/na-np.nansum(b)/nb) if na and nb else None,
                  CI95=interval(vals),valid_bootstraps=int(valid.sum()),denominator='each output observed, never conditional on naming')
    lo=np.nan_to_num(a,nan=0)-np.nan_to_num(b,nan=1)
    hi=np.nan_to_num(a,nan=1)-np.nan_to_num(b,nan=0)
    return dict(observed=observed,complete_pair=complete,full199_identification_bounds=[float(lo.mean()),float(hi.mean())],
                full199_bootstrap_bound_envelope=[float(np.quantile(lo[draws].mean(1),.025)),float(np.quantile(hi[draws].mean(1),.975))])

def analyze(items, ceiling):
    if len(items)!=N or len({(x['row'],x['item_id']) for x in items})!=N:raise ValueError('exact original199 unique source items')
    items=sorted(items,key=lambda x:(x['row'],x['item_id']))
    identities={(x['row'],x['item_id']) for x in items}
    if len(ceiling)!=N or {(x['row'],x['item_id']) for x in ceiling}!=identities:
        raise ValueError('exact E82 sealed same-model answer census required')
    ceiling=sorted(ceiling,key=lambda x:(x['row'],x['item_id']))
    for x in ceiling:
        values=[x[k] for k in ('answer_value','belief_value','truth_value')]
        if not all(isinstance(v,str) and v for v in values) or values[0]!=values[1] or values[1]==values[2]:
            raise ValueError('original sealed E82 belief-wrong answer/label identity required; no reparse')
    arrays={};rates={}
    truth_arrays={}
    for system in ('oracle','outside'):
        named=[];belief=[];truth=[]
        for x in items:
            z=x['systems'][system];n=z['named'];b=z['belief'];t=z['truth']
            if (n is None)!=(b is None) or n not in (None,0,1) or b not in (None,0,1) or b==1 and n!=1:
                raise ValueError('original complete target-code semantics required')
            if (n is None)!=(t is None) or t not in (None,0,1) or t==1 and n!=1:
                raise ValueError('original complete truth target-code semantics required')
            truth.append(np.nan if t is None else t)
            named.append(np.nan if n is None else n);belief.append(np.nan if b is None else b)
        arrays[system]=(np.array(named,float),np.array(belief,float));rates[system]=summary(*arrays[system])
        truth_arrays[system]=np.array(truth,float)
        rates[system]['truth']=summary(np.array(named,float),truth_arrays[system])
        rates[system]['truth']['states_truth']=rates[system]['truth'].pop('states_belief')
    rates['same_model_ceiling']=summary(np.ones(N),np.ones(N))
    rates['same_model_ceiling']['truth']=summary(np.ones(N),np.zeros(N))
    rates['same_model_ceiling']['truth']['states_truth']=rates['same_model_ceiling']['truth'].pop('states_belief')
    draws=np.random.default_rng(SEED).integers(0,N,(DRAWS,N))
    cov=difference(arrays['oracle'][0],arrays['outside'][0],draws)
    unc=difference(arrays['oracle'][1],arrays['outside'][1],draws)
    table=[[0,0],[0,0]];missing=0
    for a,b in zip(arrays['oracle'][1],arrays['outside'][1]):
        if not np.isfinite([a,b]).all():missing+=1
        else:table[int(a)][int(b)]+=1
    truth_diff=difference(truth_arrays['oracle'],truth_arrays['outside'],draws)
    conditional={target:difference(
        np.where(arrays['oracle'][0]==1, arrays['oracle'][1] if target=='belief' else truth_arrays['oracle'],np.nan),
        np.where(arrays['outside'][0]==1, arrays['outside'][1] if target=='belief' else truth_arrays['outside'],np.nan),draws)['observed']
        for target in ('belief','truth')}
    for v in conditional.values():v['denominator']='each output independently given a stated value'
    ceiling_contrasts={target:difference(arrays['oracle'][1] if target=='belief' else truth_arrays['oracle'],
        np.ones(N) if target=='belief' else np.zeros(N),draws) for target in ('belief','truth')}
    ceiling_given_value={target:difference(np.where(arrays['oracle'][0]==1,
        arrays['oracle'][1] if target=='belief' else truth_arrays['oracle'],np.nan),
        np.ones(N) if target=='belief' else np.zeros(N),draws)['observed'] for target in ('belief','truth')}
    for v in ceiling_given_value.values():v['denominator']='Oracle given a value versus construction ceiling given a value'
    truth_delta=truth_diff['observed']['estimate']
    outside_truth_higher=None if truth_delta is None else truth_delta<0
    ci=unc['observed']['CI95']
    wording='higher precision at lower coverage' if ci is not None and ci[0]<=0<=ci[1] else 'report unconditional and coverage estimates with missingness; never label the sealed precision gap overall'
    return dict(section='248 A',status='EXPLORATORY_POST_HOC',systems=rates,coverage_difference=cov,
        unconditional_difference=unc, truth_unconditional_difference=truth_diff,
        given_value_differences=conditional,oracle_minus_same_model_ceiling=ceiling_contrasts,
        oracle_minus_same_model_ceiling_given_value=ceiling_given_value,
        same_model_ceiling_interpretation='E82 black-box answer defines its belief: construction ceiling, not evidence beyond text',
        outside_defaults_to_truth_clause_eligible=outside_truth_higher,
        truth_wording='outside model has a higher observed unconditional truth-stating rate' if outside_truth_higher else 'omit outside-defaults-to-truth clause',who_states_belief_2x2=table,table_axes=['oracle no/yes','forecast no/yes'],
        table_missing_pairs=missing,reading=wording,bootstrap=dict(draws=DRAWS,seed=SEED,unit='paired original item'),
        caveat='not naming counts as abstention, not a missing judgment; missing never imputed; shared-family confound remains unknown')
