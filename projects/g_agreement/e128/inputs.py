from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,verify

def load(root,digest):
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    if s['experiment']!='E128'or s['labels_on_pod']is not False or set(s['files'])!={'items.json','MANIFEST.json','SCORER.json','deltas.npy'}:raise ValueError('public E128 members')
    xs=read(root/'items.json');d=np.load(root/'deltas.npy',allow_pickle=False);m=read(root/'MANIFEST.json')
    if len(xs)!=336 or len({x['id']for x in xs})!=336 or d.shape!=(336,5120)or d.dtype!=np.float32 or not np.isfinite(d).all()or m['oracle_layers']!=[44,52]:raise ValueError('complete E128 cells/vectors')
    for i,x in enumerate(xs):
        if set(x)!={'id','base_id','row','alpha','condition','ids','read_index','candidate_ids','delta_index'}or x['delta_index']!=i or x['row']!='fact_recall'or x['read_index']!=len(x['ids'])-1:raise ValueError('E128 public field/prefix order')
    all_ids=None
    for alpha in (2,4):
        sets=[]
        for cond in ('steered','random'):
            group=[x for x in xs if x['alpha']==alpha and x['condition']==cond];ids={x['base_id']for x in group}
            if len(group)!=84 or len(ids)!=84:raise ValueError('same84items/allconditions/doses')
            if all_ids is not None and ids!=all_ids:raise ValueError('same cohort at both doses')
            all_ids=ids;sets.append(ids)
        if sets[0]!=sets[1]:raise ValueError('matched random control')
    return xs,d,m
