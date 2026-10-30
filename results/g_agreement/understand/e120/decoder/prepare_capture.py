"""Operational normalization of native E120ab delivery; no fitting or statistics."""
from pathlib import Path
import os,json,hashlib
import numpy as np

def normalized(index,fmt,dev_ids,test_ids):
 assert len(index)==600 and len({r['id'] for r in index})==600
 assert fmt['layers']==list(range(64)) and fmt['positions']==['injected_activation','first_generated_token'] and fmt['source_layer']==44
 assert fmt['first_generated_position']==len(fmt['carrier_ids']) and fmt['first_generated_position']>fmt['injected_position']
 assert fmt['alpha']==16000 and fmt['transform']=='unit'
 assert fmt['first_generated_capture']=='full forward on native injected carrier plus its actual greedy first token; not the last carrier token'
 ix={r['id']:dict(r,source_layer=fmt['source_layer'],injected_position=fmt['injected_position'],first_generated_position=fmt['first_generated_position']) for r in index}
 order={split:[ix[i] for i in ids] for split,ids in [('dev',dev_ids),('test',test_ids)]}
 assert len(dev_ids)==200 and len(test_ids)==400 and set(dev_ids).isdisjoint(test_ids) and set(dev_ids+test_ids)==set(ix)
 for split,rows in order.items():assert all(r['split']==split and r['block']==44 and type(r['first_token_id']) is int and r['first_token_id']>=0 for r in rows)
 return [ix[r['id']] for r in index],order

def write(p,d):p.write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+'\n')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return h.hexdigest()
def prepare(raw,layout):
 raw=Path(raw);layout=Path(layout);read=lambda p:json.loads(p.read_text());seal=read(raw/'OUTPUT_SEAL.json')
 assert sha(raw/'OUTPUT_SEAL.json')=='3f2ed06568eb3d0538554ae252aebf09c46a7e48154cf2769c498c17ff61d1af'
 assert seal['experiment']=='E120' and seal['part']=='ab' and seal['status']=='COMPLETE' and seal['judging'] is False and seal['labels_cpu_only'] is True
 for name,h in seal['files'].items():
  p=(raw/name).resolve();assert p.is_relative_to(raw.resolve()) and sha(p)==h,name
 dec=raw/'decoder';fmt=read(dec/'CAPTURE_FORMAT.json');index,order=normalized(read(dec/'INDEX.json'),fmt,read(dec/'DEV_ORDER.json'),read(dec/'TEST_ORDER.json'))
 # Byte comparisons only; no probe/test metric. Verify original per-batch arrays vs delivered splits.
 for split,n in [('dev',200),('test',400)]:
  x=np.load(dec/(split+'.npy'),mmap_mode='r',allow_pickle=False);assert x.shape==(n,64,2,5120) and x.dtype==np.float32
  for i,r in enumerate(order[split]):
   a=np.load(dec/r['member'],mmap_mode='r',allow_pickle=False)[r['vector_index_in_file']]
   assert a.dtype==np.float32 and a.shape==(64,2,5120) and np.isfinite(a).all() and np.array_equal(a.view(np.uint32),x[i].view(np.uint32)),r['id']
  del x
 assert not layout.exists();layout.mkdir(parents=True)
 for split in ('dev','test'):os.link(dec/(split+'.npy'),layout/(split+'.npy'))
 write(layout/'INDEX.NORMALIZED.json',index);write(layout/'ORDER.json',order)
 write(layout/'LAYOUT_SEAL.json',dict(source_output_sha256=sha(raw/'OUTPUT_SEAL.json'),bit_identical_items=600,scientific_values_transformed=False,metadata_positions='CODE_DERIVED_FROM_ORIGINAL_CAPTURE_FORMAT_NOT_INDEPENDENT_TRACE',files={n:sha(layout/n) for n in ['dev.npy','test.npy','ORDER.json','INDEX.NORMALIZED.json']}))
 return layout
if __name__=='__main__':
 import sys
 print(prepare(sys.argv[1],sys.argv[2]))
