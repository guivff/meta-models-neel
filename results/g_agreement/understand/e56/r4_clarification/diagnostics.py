"""§172 R4 clarification1: CPU-only dev probe margins and nearest-test cosine distances."""
import sys,json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'job'))
from contract56 import ROOT,read,verify,sha,require

def row_diagnostics(scores,vectors,variants,arms,test):
 scores=np.asarray(scores,float);vectors=np.asarray(vectors,float);test=np.asarray(test,float)
 require(np.isfinite(scores).all() and np.isfinite(vectors).all() and np.isfinite(test).all(),'finite diagnostics')
 ni=np.linalg.norm(vectors,axis=1);nt=np.linalg.norm(test,axis=1);require((ni>0).all() and (nt>0).all(),'nonzero cosine vectors')
 distances=1-(vectors/ni[:,None])@(test/nt[:,None]).T;nearest=distances.argmin(axis=1);d=distances[np.arange(len(vectors)),nearest]
 ix={(v,a):i for i,(v,a) in enumerate(zip(variants,arms))};require(set(ix)=={(v,a) for v in ('A','B') for a in ('full','J','nonJ')},'six injected vectors per row')
 margins={a:float(scores[ix['A',a]]-scores[ix['B',a]]) for a in ('J','nonJ')};ratio=None if margins['J']<=0 else margins['nonJ']/margins['J']
 gap={v:abs(float(d[ix[v,'nonJ']]-d[ix[v,'J']])) for v in ('A','B')}
 return {'probe_margins_A_minus_B':margins,'probe_margin_ratio_nonJ_over_J':ratio,'nearest_real_test':[{ 'variant':v,'arm':a,'distance':float(d[i]),'test_index':int(nearest[i])} for i,(v,a) in enumerate(zip(variants,arms))],'arm_distance_difference_by_class':gap,'information_matched':ratio is not None and ratio>=.8,'comparably_on_distribution':all(x<=.05+1e-12 for x in gap.values()),'eligible':ratio is not None and ratio>=.8 and all(x<=.05+1e-12 for x in gap.values())}

def compute(spec):
 import torch
 sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
 from mats.probes import fit_logreg
 torch.set_num_threads(1);torch.manual_seed(20261026)
 for entry in spec['files'].values():require(sha(entry['path'])==entry['sha256'],'diagnostic input pin')
 private=[json.loads(x) for x in Path(spec['files']['metadata']['path']).read_text().splitlines()];by={x['id']:x for x in private};order=read(spec['files']['order']['path']);require(set(order)==set(by),'complete dev/test capture bank')
 h=np.load(spec['files']['acts44']['path'],mmap_mode='r');require(h.shape==(len(order),5120),'raw block44 bank');items=[by[k] for k in order]
 ip=Path(spec['injection_inputs']);verify(ip,'INPUT_SEAL.json',spec['injection_input_seal_sha256']);inj=read(ip/'injection/ITEMS.json')['items'];v=np.load(ip/'injection/INPUT_VECTORS.npz')['activations'];values=read(ip/'injection/PLAN.json')['rows'];out={}
 for row,(a,b) in values.items():
  train=[i for i,x in enumerate(items) if x['feature']==row and x['split']=='dev'];test=[i for i,x in enumerate(items) if x['feature']==row and x['split']=='test'];require(train and test,'dev and test row available')
  require(all(items[i]['value'] in (a,b) for i in train+test),'class values frozen');y=torch.tensor([int(items[i]['value']==a) for i in train]);require(set(y.tolist())=={0,1},'both dev classes')
  model=fit_logreg(torch.from_numpy(np.asarray(h[train]).copy()),y);units=[x for x in inj if x['row']==row];vv=v[[x['index'] for x in units]];scores=model.decision(torch.from_numpy(vv.copy())).numpy();diag=row_diagnostics(scores,vv,[x['variant'] for x in units],[x['arm'] for x in units],h[test])
  for d,x in zip(diag['nearest_real_test'],units):d.update(vector_id=x['id'],nearest_test_id=order[test[d.pop('test_index')]])
  out[row]=diag
 return out
