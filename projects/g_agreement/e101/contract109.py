"""§222 capture contract; no labels, probe fitting, cohort selection or judging."""
import hashlib
import numpy as np
from .contract import read,write,sha,verify
SEED=20261029
DOSES={'fact_recall':8.,'language_plan':2.}
CAPTURE=(44,48,52,56,60)
READ=(44,52,60)
CONDITIONS=('unhooked','steered','random')
DIRECTION_SHA='6a905cbfe83f0c3db6a3ad376490052eeab638a83362c799a655e4b35a3a8e9c'
FIELDS={'id','base_id','row','split','condition','alpha','ids','read_index','delta_index'}


def identity(split,row,base,condition):return hashlib.sha256(f'E109:{split}:{row}:{base}:{condition}'.encode()).hexdigest()


def validate(items,deltas,m):
    if (m['experiment']!='E109' or m['seed']!=SEED or m['capture_blocks']!=list(CAPTURE)
        or m['oracle_blocks']!=list(READ) or m['direction_sha256']!=DIRECTION_SHA
        or m['write_block']!=40 or m['read_token_patched'] is not False):raise ValueError('registered E109 sites/directions')
    rows=m['rows']
    if not rows or len(rows)!=len(set(rows)) or not set(rows)<=DOSES.keys():raise ValueError('registered rows')
    if len(items)!=len(rows)*84*2*3 or len({x['id'] for x in items})!=len(items):raise ValueError('84 dev/test complete three-condition rows')
    if deltas.shape!=(len(rows)*84*2*2,5120) or deltas.dtype!=np.float32 or not np.isfinite(deltas).all():raise ValueError('finite aligned original E104 deltas')
    used=[]
    for row in rows:
        for split in ('dev','test'):
            xs=[x for x in items if x['row']==row and x['split']==split]
            bases={x['base_id'] for x in xs}
            if len(xs)!=252 or len(bases)!=84:raise ValueError('84 unique frozen items per row/split')
            for base in bases:
                group=[x for x in xs if x['base_id']==base]
                if len(group)!=3 or {x['condition'] for x in group}!=set(CONDITIONS):raise ValueError('all three conditions')
                if any(x['ids']!=group[0]['ids'] for x in group):raise ValueError('same unchanged prompt')
                for x in group:
                    if set(x)!=FIELDS or x['id']!=identity(split,row,base,x['condition']) or x['alpha']!=DOSES[row]:raise ValueError('public fixed-dose identity')
                    if (len(x['ids'])<9 or x['read_index']!=len(x['ids'])-1
                        or any(type(t)is not int or t<0 for t in x['ids'])):raise ValueError('eight existing prior positions')
                    ix=x['delta_index']
                    if x['condition']=='unhooked':
                        if ix is not None:raise ValueError('unhooked is never a zero-vector intervention')
                    else:
                        if type(ix)is not int or not 0<=ix<len(deltas):raise ValueError('delta index')
                        used.append(ix)
                hooked=[x for x in group if x['condition']!='unhooked']
                norms=[np.linalg.norm(deltas[x['delta_index']].astype(np.float64)) for x in hooked]
                if min(norms)<=0 or not np.isclose(*norms,rtol=1e-6):raise ValueError('matched random injection norm')
    if sorted(used)!=list(range(len(deltas))):raise ValueError('exact one-use original deltas')


def load(root):
    seal=verify(root,'INPUT_SEAL.json',sha(root/'INPUT_SEAL.json'))
    files={'MANIFEST.json','items.json','deltas.npy'}
    if seal['experiment']!='E109' or seal['labels_on_pod'] is not False or set(seal['files'])!=files or {p.name for p in root.iterdir()}!=files|{'INPUT_SEAL.json'}:raise ValueError('public label-free E109 members only')
    m=read(root/'MANIFEST.json');xs=read(root/'items.json');d=np.load(root/'deltas.npy',allow_pickle=False)
    validate(xs,d,m);return xs,dict(deltas=d,manifest=m)
