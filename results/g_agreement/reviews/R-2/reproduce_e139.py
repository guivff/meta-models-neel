"""Independent E139 CPU review arithmetic; no reconstructor or author imports.
Reward pinning is a separate source audit, never certified by a boolean here.
"""
import math
import numpy as np
from common.stats import bootstrap_ci


def paired_gain(rows, *, draws, seed):
    """Frozen20-item true-minus-neutral reward, paired item resampling.

    Caller independently verifies original reward space, orientation, grafts,
    score/source references and frozen settings before passing actual results.
    Explicit missing scores stay unknown; no fit or model call occurs here.
    """
    if len(rows)!=20 or len({x['id'] for x in rows})!=20:
        raise ValueError('exact20 frozen unique source items required')
    # The frozen owner packet order defines seeded draw indices. Do not re-sort
    # identities after scoring: verify the original ordered source binding first.
    rows=list(rows);values=[]
    for x in rows:
        a,b=x['true'],x['neutral']
        if a is None or b is None:values.append(np.nan);continue
        if not math.isfinite(a) or not math.isfinite(b):raise ValueError('finite scores or explicit null')
        values.append(a-b)
    a=np.asarray(values,float);known=int(np.isfinite(a).sum())
    if known==0:return dict(planned=20,kept=0,missing=20,estimate=None,CI95=None,undefined_draws=draws)
    draws_seen=[]
    def metric(ix):
        v=a[ix];v=v[np.isfinite(v)];r=float(v.mean()) if len(v) else np.nan
        draws_seen.append(r);return r
    point,lo,hi=bootstrap_ci(np.arange(20),fn=metric,n_boot=draws,seed=seed)
    return dict(planned=20,kept=known,missing=20-known,estimate=point,
                CI95=[lo,hi] if np.isfinite([lo,hi]).all() else None,
                undefined_draws=sum(not math.isfinite(v) for v in draws_seen[:draws]))


def instrument_gate(control_intervals, *, reward_label):
    """At least one positive control; no structural inference on failure/unknown."""
    if reward_label not in ('training reward','proxy reward'):
        raise ValueError('explicit source-reviewed reward/proxy label required')
    if set(control_intervals)!={'language','fact_recall'}:
        raise ValueError('both frozen reportable controls required')
    passed=[];unknown=[]
    for state,ci in control_intervals.items():
        if ci is None:unknown.append(state);continue
        if len(ci)!=2 or not all(math.isfinite(x) for x in ci) or ci[0]>ci[1]:
            raise ValueError('valid item-bootstrap interval required')
        if ci[0]>0:passed.append(state)
    status='PASS' if passed else 'PENDING: incomplete controls' if unknown else 'NOT EVALUABLE (instrument)'
    return dict(status=status,structural_reading_allowed=bool(passed),
                positive_controls=sorted(passed),unknown_controls=sorted(unknown),reward_label=reward_label)


def delta_u(dev_rebuilds, dev_labels, original, appended, *, draws, seed):
    """Independent §251cl1 class-gap fraction, fixed DEV direction/bootstrap."""
    dev=np.asarray(dev_rebuilds,float);labels=np.asarray(dev_labels)
    original=np.asarray(original,float)
    if dev.ndim!=2 or labels.shape!=(len(dev),) or set(labels.tolist())!={0,1}:
        raise ValueError('two frozen DEV span classes required')
    if original.shape!=(20,dev.shape[1]) or not np.isfinite(dev).all() or not np.isfinite(original).all():
        raise ValueError('complete20-item/common-space rebuilds required')
    if set(appended)!={'true','false','neutral'}:raise ValueError('three frozen append conditions')
    gap=np.mean(dev[labels==1],axis=0)-np.mean(dev[labels==0],axis=0)
    gap2=float(gap@gap)
    if not math.isfinite(gap2) or gap2<=0:raise ValueError('NOT EVALUABLE: zero DEV class gap')
    out={}
    for name,values in appended.items():
        values=np.asarray(values,float)
        if values.shape!=original.shape or not np.isfinite(values).all():raise ValueError('paired finite append vectors')
        # Algebraically <difference,d>/<gap,d> = <difference,gap>/||gap||².
        fractions=(values-original)@gap/gap2
        point,lo,hi=bootstrap_ci(fractions,n_boot=draws,seed=seed)
        out[name]=dict(mean=point,CI95=[lo,hi])
    return out
