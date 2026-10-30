"""§236 E104 fact_recall U unchanged, only dose2/4 and read layers44/52."""
import numpy as np
from projects.g_agreement.e101.intervention104 import intervene_forward
from projects.g_agreement.e127.runner import greedy_three
LAYERS=(44,52)


def capture_answer_batch(model,tok,items,deltas):
    if not items or len({(x['alpha'],x['condition'],len(x['ids']))for x in items})!=1:raise ValueError('homogeneous dose/condition/unpadded batch')
    if any(x['alpha']not in (2,4)or x['condition']not in ('steered','random')for x in items):raise ValueError('registered E128 doses/control')
    d=np.asarray(deltas);before=d.tobytes();captures={L:[]for L in LAYERS};metrics=[]
    def forward(sequences,positions,step):
        logits,m,_=intervene_forward(model,sequences,positions,d,'U',1,observe=step==0,captures=captures if step==0 else None)
        if m is not None:metrics.extend(m)
        return logits
    answers=greedy_three(model,tok,items,forward)
    if d.tobytes()!=before or len(metrics)!=len(items)or any(len(v)!=1 for v in captures.values()):raise ValueError('immutable dose delta and one prefix capture')
    arrays={L:v[0]for L,v in captures.items()}
    return dict(captures=arrays,answers=answers,injection_metrics=metrics,
      read_norms={str(L):np.linalg.norm(v.astype(np.float64),axis=-1).tolist()for L,v in arrays.items()},intervention_installed=True,write_block=40)


def batches(items,size=8):
    groups={}
    for x in items:groups.setdefault((x['alpha'],x['condition'],len(x['ids'])),[]).append(x)
    for _,xs in sorted(groups.items()):
        for i in range(0,len(xs),size):yield xs[i:i+size]
