"""Lossless loading of W-mechanism-B's per-row public vector package.
No private labels, signs, probe parameters, token mappings or source identities.
"""
from pathlib import Path
import numpy as np
from .contract import read,require,ROWS

def load(root,seal,shard):
 root=Path(root).resolve();manifest=read(root/'MANIFEST.json');rows=manifest['rows']
 if isinstance(rows,dict):rows=[dict(v,row=k) for k,v in rows.items()]
 require(manifest['parts']==['a','b'] and manifest['parts_c_d']=='WITHDRAWN_NOT_RUN' and manifest['seed']==20261028 and manifest['rank']==384 and manifest['dimension']==5120 and manifest['basis_shape']==[5120,384],'current registered a/b owner contract')
 require(seal['labels_on_pod'] is False and seal.get('parts',manifest['parts'])==['a','b'],'public label-free a/b seal')
 by={r['row']:r for r in rows};require(len(by)==len(rows) and set(by) in (set(ROWS[shard]),set().union(*[set(x) for x in ROWS.values()])),'all8 frozen owner rows')
 def path(name):
  p=(root/name).resolve();require(p.is_relative_to(root) and str(p.relative_to(root)) in seal['files'],'array/join must be sealed public member');return p
 def array(name):return np.load(path(name),allow_pickle=False)
 items=[];h44=[];h42=[]
 for row,count in ROWS[shard].items():
  r=by[row];require(r['group']==shard and r['items']==count==84 and len(r['ids'])==count and len(set(r['ids']))==count,'whole row owner contract')
  pairs=read(path(r['pairings']));require([p['id'] for p in pairs]==r['ids'] and [p['slot'] for p in pairs]==list(range(count)),'frozen pairing order')
  offset=len(items)
  for p in pairs:
   require(0<=p['donor_slot']<count and p['donor_id']==r['ids'][p['donor_slot']],'opaque donor mapping')
   items.append(dict(id=p['id'],row=row,slot=offset+p['slot'],row_slot=p['slot'],donor_slot=offset+p['donor_slot']))
  h44.append(array(r['h44']));h42.append(array(r['h42']))
 arrays=dict(H44=np.concatenate(h44),H42=np.concatenate(h42),BASIS_J=array('Q_J.npy'),BASIS_R=array('Q_R.npy'))
 return items,arrays
