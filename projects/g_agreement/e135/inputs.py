from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,verify

def load(root,digest):
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    if s['experiment']!='E135'or s['labels_on_pod']is not False or set(s['files'])!={'items.json','MANIFEST.json','SCORER.json','deltas.npy'}:raise ValueError('public E135 members')
    xs=read(root/'items.json');d=np.load(root/'deltas.npy',allow_pickle=False);m=read(root/'MANIFEST.json')
    if len(xs)!=168 or len({x['id']for x in xs})!=168 or d.shape!=(168,5120)or d.dtype!=np.float32 or not np.isfinite(d).all()or m['oracle_layers']!=[44,52]:raise ValueError('complete E135 cells/vectors')
    for i,x in enumerate(xs):
        if set(x)!={'id','base_id','row','alpha','condition','ids','read_index','candidate_ids','delta_index'}or x['delta_index']!=i or x['row']!='fact_recall'or x['read_index']!=len(x['ids'])-1:raise ValueError('E135 public field/prefix order')
    all_ids=None
    for alpha in (6,):
        sets=[]
        for cond in ('steered','random'):
            group=[x for x in xs if x['alpha']==alpha and x['condition']==cond];ids={x['base_id']for x in group}
            if len(group)!=84 or len(ids)!=84:raise ValueError('same84items/allconditions/doses')
            if all_ids is not None and ids!=all_ids:raise ValueError('same cohort at all doses')
            all_ids=ids;sets.append(ids)
        if sets[0]!=sets[1]:raise ValueError('matched random control')
    by={}
    for x in xs:
        if x['base_id'] in by:
            old=by[x['base_id']]
            if any(x[k]!=old[k] for k in ('ids','read_index','candidate_ids')):
                raise ValueError('unchanged matched prompt/read/pair')
        else:by[x['base_id']]=x
        if len(x['ids'])<9 or any(len(c)!=1 for pair in x['candidate_ids'] for c in pair):
            raise ValueError('eight sites and original single-token contrasts')
    if m['doses']!=[6] or m['cells']!=168 or m['total_readouts']!=336:
        raise ValueError('registered census')
    return xs,d,m
