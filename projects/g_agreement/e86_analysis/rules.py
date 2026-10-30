"""E86-open remains blocked; E86-yn honest/role are descriptive only."""
import numpy as np
from common.stats import bootstrap_ci
DRAWS,SEED=5000,0

def stat(values):
    if not values:return dict(estimate=None,CI95=None)
    p,lo,hi=bootstrap_ci(values,n_boot=DRAWS,seed=SEED)
    return dict(estimate=p,CI95=[lo,hi])

def summary(xs):
    xs=sorted(xs,key=lambda x:x['id'])
    kept=[x for x in xs if x['truth'] is not None]
    named=[x for x in kept if x['named']]
    missing=len(xs)-len(kept);den=len(named)
    delta=[int(x['wrong'])-int(x['truth']) for x in named]
    total=sum(delta)
    return dict(planned=len(xs),kept=len(kept),missing=missing,over_5_percent_missing=20*missing>len(xs),
        naming_either_value=den,neither=len(kept)-den,
        truth_only=sum(x['truth'] and not x['wrong'] for x in named),wrong_only=sum(x['wrong'] and not x['truth'] for x in named),both=sum(x['truth'] and x['wrong'] for x in named),
        conditional_truth=stat([int(x['truth']) for x in named]),conditional_wrong=stat([int(x['wrong']) for x in named]),conditional_wrong_minus_truth=stat(delta),
        unconditional_truth=stat([int(x['truth']) for x in kept]),unconditional_wrong=stat([int(x['wrong']) for x in kept]),S_truth=stat([x['truth_score'] for x in kept]),
        missingness_bounds_conditional_delta=[(total-missing)/(den+missing),(total+missing)/(den+missing)] if den+missing else None)

def summarize_rows(rows):
    return {reader:{arm:summary(sorted([x for x in rows if x['reader']==reader and x['arm']==arm],key=lambda x:x['id'])) for arm in ('honest','role')} for reader in ('oracle','nla')}

def analyze(rows,old_rows,old_ids,diagnostics):
    return dict(experiment='E86',scope='Original released E86-yn honest/role TEST only; no source/gate/probe replay',
        bootstrap=dict(draws=DRAWS,seed=SEED,unit='source item',conditional='resample fixed named-value cohort for conditional estimands; paired truth/wrong within item'),
        R_K1='NOT EVALUABLE',falsifier='NOT EVALUABLE',rule_reason='R-K1 is E86-open primary, underpowered; lie arm BOW fails and has no released readouts. Role/binary cannot substitute.',
        R_K2_descriptive=summarize_rows(rows),gate_diagnostics=diagnostics,
        matched_original_rubric=dict(selected=len(old_ids),primary=summarize_rows([x for x in rows if x['id'] in old_ids]),original=summarize_rows(old_rows),note='Identical seeded25% IDs; denominators may differ from missingness/naming; no replacement of primary cohort'),
        interpretation='Role wrong-minus-truth is descriptive, NLA alongside. Honest truth-statement baseline is reported both unconditional and conditional on naming either value. Both-valued readouts count toward both probabilities and contribute zero contrast.')
