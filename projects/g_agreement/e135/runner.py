"""§244 deviation1 E104 fact_recall U unchanged, only dose6 only and read layers44/52."""
import numpy as np
from projects.g_agreement.e101.intervention104 import intervene_forward
from projects.g_agreement.e127.runner import greedy_three
LAYERS=(44,52)


def capture_answer_batch(model,tok,items,deltas):
    if not items or len({(x['alpha'],x['condition'],len(x['ids']))for x in items})!=1:raise ValueError('homogeneous dose/condition/unpadded batch')
    if any(x['alpha']not in (6,)or x['condition']not in ('steered','random')for x in items):raise ValueError('registered E135 doses/control')
    d=np.asarray(deltas);before=d.tobytes();captures={L:[]for L in LAYERS};metrics=[]
    def forward(sequences,positions,step):
        logits,m,_=intervene_forward(model,sequences,positions,d,'U',1,observe=step==0,captures=captures if step==0 else None)
        if m is not None:metrics.extend(m)
        return logits
    answers=greedy_three(model,tok,items,forward)
    if d.tobytes()!=before or len(metrics)!=len(items)or any(len(v)!=1 for v in captures.values()):raise ValueError('immutable dose delta and one prefix capture')
    arrays={L:v[0]for L,v in captures.items()}
    return dict(captures=arrays,answers=answers,injection_metrics=metrics,
      calibration=calibration_records(items,d,metrics),
      read_norms={str(L):np.linalg.norm(v.astype(np.float64),axis=-1).tolist()for L,v in arrays.items()},intervention_installed=True,write_block=40)


def batches(items,size=8):
    groups={}
    for x in items:groups.setdefault((x['alpha'],x['condition'],len(x['ids'])),[]).append(x)
    for _,xs in sorted(groups.items()):
        for i in range(0,len(xs),size):yield xs[i:i+size]


def calibration_records(items,deltas,metrics):
    """Raw natural per-site norms from unchanged U hook; no extra model call.

    W-mech2 computes the median across 84*8 natural write-site norms and ratios.
    Historical doses are arithmetic rescalings of the same composed delta, never
    new captures. Record both directions; analysis must not duplicate the cohort.
    """
    if len(items)!=len(metrics) or len(items)!=len(deltas):
        raise ValueError('aligned calibration records')
    records=[]
    for x,d,m in zip(items,deltas,metrics):
        sites=m['injection_sites']
        if [s['position'] for s in sites]!=list(range(x['read_index']-8,x['read_index'])) or any(s['block']!=40 for s in sites):
            raise ValueError('original eight block40 positions')
        norms=[s['before_norm'] for s in sites]
        dn=float(np.linalg.norm(np.asarray(d,dtype=np.float64)))
        if not np.isfinite(norms).all() or min(norms)<=0 or not np.isfinite(dn) or dn<=0:
            raise ValueError('finite positive calibration norms')
        records.append(dict(id=x['id'],base_id=x['base_id'],alpha=x['alpha'],condition=x['condition'],
            write_block=40,positions=[s['position'] for s in sites],natural_site_l2=norms,
            composed_delta_l2=dn,unscaled_d_l2=dn/x['alpha'],reference_delta_l2={str(a):dn*a/x['alpha'] for a in (2,4,6,8)},
            reference_policy='arithmetic only; no historical model rerun',
            denominator_policy='median individual site L2 across same84items x8positions; CPU owner computes'))
    return records
