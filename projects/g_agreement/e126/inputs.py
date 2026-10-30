"""Sealed public E126 packet and callable adapter for Track Q's outer custody."""
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,verify
from .hook import LAYERS

def load(root,digest):
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    expected={'items.json','MANIFEST.json','SCORERS.json','upstream.npy','unhooked.npy','steered.npy','random.npy','earlier.npy'}
    if s['experiment']!='E126' or s['labels_on_pod'] is not False or set(s['files'])!=expected or {p.name for p in root.iterdir()}!=expected|{'INPUT_SEAL.json'}:raise ValueError('sealed label-free E126 packet only')
    m=read(root/'MANIFEST.json');xs=read(root/'items.json');n=len(xs)
    if n!=134 or len({x['id']for x in xs})!=n or m['layers']!=list(LAYERS)or m['cells']!=4020 or m['seed']!=20261029:raise ValueError('frozen E126 grid')
    if {r:sum(x['row']==r for x in xs)for r in ('fact_recall','language_plan')}!={'fact_recall':84,'language_plan':50}:raise ValueError('original cohort')
    for i,x in enumerate(xs):
        if set(x)!={'id','row','ids','read_index','candidate_ids','vector_index'}or x['vector_index']!=i or x['read_index']!=len(x['ids'])-1 or not 8<x['read_index']<2**24:raise ValueError('public immutable scoring prefix')
        if not x['candidate_ids']or any(len(pair)!=2 or any(not c or any(type(t)is not int or t<0 for t in c)for c in pair)for pair in x['candidate_ids']):raise ValueError('frozen continuation pairs')
    shapes={'upstream':(n,5120),'unhooked':(n,5,5120),'steered':(n,5,5120),'random':(n,5,2,5120),'earlier':(n,5,2)}
    data={k:np.load(root/(k+'.npy'),allow_pickle=False)for k in shapes}
    for k,a in data.items():
        if a.shape!=shapes[k]or not np.isfinite(a).all()or a.dtype!=(np.int64 if k=='earlier'else np.float32):raise ValueError('finite original vectors/control arrays')
    if not np.allclose(np.linalg.norm(data['random'],axis=-1),1,atol=1e-6):raise ValueError('fixed unit random controls')
    for i,x in enumerate(xs):
        if np.any(data['earlier'][i]<0)or np.any(data['earlier'][i]>=x['read_index']-8):raise ValueError('nonsteered earlier positions')
    return xs,data

def cell(item,block,direction,control):
    return dict(item,input_id=item['id'],id=f"{item['id']}:{block}:{direction}:{control}",block=block,direction=direction,control=control)

def payload(items,data):
    if not items:return np.empty((0,15361),np.float32)
    rows=[]
    for x in items:
        j=x['vector_index'];l=LAYERS.index(x['block']);d=('restore','insert').index(x['direction'])
        target=data['unhooked'if x['direction']=='restore'else'steered'][j,l]
        rows.append(np.concatenate((data['upstream'][j],target,data['random'][j,l,d],[data['earlier'][j,l,d]])))
    return np.asarray(rows,dtype=np.float32)

def jobs(items,size=8):
    for L in LAYERS:
        for direction in ('restore','insert'):
            for control in ('read','earlier','random'):
                groups={}
                for x in items:
                    key=(x['row'],len(x['ids']),tuple(tuple(len(c)for c in p)for p in x['candidate_ids']))
                    groups.setdefault(key,[]).append(cell(x,L,direction,control))
                for k,xs in sorted(groups.items()):
                    for start in range(0,len(xs),size):yield xs[start:start+size]
