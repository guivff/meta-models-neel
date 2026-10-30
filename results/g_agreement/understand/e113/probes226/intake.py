"""Exact E113 sealed split-layout intake; finalized after capture, before CPU claim."""
from pathlib import Path
import hashlib,json
import numpy as np
from probes import ROWS,POSITIONS,validate_ids
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def verify(root,seal):
 d=read(Path(root)/seal)
 for f,h in d['files'].items():
  p=Path(root)/f;assert p.resolve().is_relative_to(Path(root).resolve());assert sha(p)==h,f
 return d
def ordered_labels(order,labels):
 assert len(labels)==1008 and len({x['id'] for x in labels})==1008
 by={x['id']:x for x in labels};answer={}
 assert set(order)=={r+':'+s for r in ROWS for s in ['dev','test']}
 seen=[]
 for r in ROWS:
  ids={};base={}
  for s in ['dev','test']:
   group=order[r+':'+s];assert len(group)==84
   ids[s]=[x['id'] for x in group];base[s]=[x['base_id'] for x in group];ys=[]
   for x in group:
    a=by[x['id']]
    assert x['row']==r and x['split']==s and x['block']==44
    assert isinstance(x['first_token_id'],int) and x['first_token_id']>=0
    assert all(x[k]==a[k] for k in ['id','base_id','row','split'])
    assert a['bank']==('E57' if r in ROWS[:3] else 'E56' if r=='fact_recall' else 'E59')
    assert a['label'] in [0,1];ys.append(a['label']);seen.append(x['id'])
   assert ys.count(0)==ys.count(1)==42;answer[r+':'+s]=np.asarray(ys,dtype=int)
  validate_ids(ids['dev'],ids['test']);validate_ids(base['dev'],base['test'])
 assert len(set(seen))==1008 and set(seen)==set(by)
 return answer
def preflight(plan):
 for p,h in plan['pins'].items():assert sha(p)==h,p
 cap=Path(plan['capture_root']);layout=Path(plan['layout_root']);labs=Path(plan['label_root'])
 output=verify(cap,'OUTPUT_SEAL.json');split=verify(layout,'LAYOUT_SEAL.json');label=verify(labs,'LABEL_SEAL.json')
 assert output['experiment']=='E113' and output['status']=='COMPLETE' and not output['judging']
 assert output['input_sha256']==plan['input_sha256'] and output['source_sha256']==plan['source_sha256']
 assert split['source_output_sha256']==sha(cap/'OUTPUT_SEAL.json') and split['bit_identical_items']==1008
 assert split['scientific_values_transformed'] is False and split['probe_fits']==0
 assert label['input_sha256']==plan['input_sha256']
 fmt=read(cap/'CAPTURE_FORMAT.json')
 assert fmt['layers']==list(range(64)) and fmt['positions']==list(POSITIONS)
 assert fmt['injected_position']==24 and fmt['first_generated_position']==56==len(fmt['carrier_ids'])
 assert fmt['source_layer']==44 and fmt['alpha']==16000 and fmt['transform']=='unit' and fmt['dtype']=='float32'
 custody=read(plan['custody_receipt']);assert custody['status']=='COMPLETE_CLOSED'
 assert all(p['status']=='EXITED' for p in custody['pods'])
 receipt=read(plan['pull_receipt']);assert receipt['verified'] is True and receipt['status']=='COMPLETE'
 order=read(layout/'ORDER.json');index=read(cap/'INDEX.json')
 assert len(index)==1008 and len({x['id'] for x in index})==1008
 assert {x['id']:x for x in index}=={x['id']:x for xs in order.values() for x in xs}
 return ordered_labels(order,read(labs/'LABELS.json'))
def load_split(layout,row,split):
 a=np.load(Path(layout)/(row+'_'+split+'.npy'),mmap_mode='r',allow_pickle=False)
 assert a.shape==(84,64,2,5120) and a.dtype==np.float32
 assert np.isfinite(a).all(),row+':'+split
 return a
