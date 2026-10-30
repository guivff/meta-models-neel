"""E62 native ladder channels, reusing the E56 reader backend without label inputs."""
import sys,json,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
E56=HERE.parents[1]/'e56/job';sys.path.insert(0,str(E56))
from contract56 import ROOT,read,dump,sha,seal,verify,require
from worker56 import Backend,readout_records
from native_nla512 import truncation_summary

def validate_items(items):
 require(items and len({x['id'] for x in items})==len(items),'unique item order')
 for x in items:
  require(not {'label','value'} & x.keys(),'no labels on pod')
  require(x['split'] in ('dev','test') and x['state'] in ('S1','S2','S3','S4','S5','S6'),'registered state/split')
  require(x['rung'] in ([f'C{i}' for i in range(5)] if x['state']=='S6' else [f'L{i}' for i in range(5)]+['L1p','L2p','L4p']),'registered rung')
  require(x['feature']==x['state']+'_'+x['rung'] and bool(x['base_item_id']),'cell and paired base ID')
  lo,hi=x['first_content_index'],x['read_index']
  require(type(lo) is int and type(hi) is int and 0<=lo<=hi<len(x['ids']),'frozen inclusive capture bounds')
  if x['rung'] in ('L4','L4p'):require(type(x['alpha_token_id']) is int and type(x['beta_token_id']) is int and x['alpha_token_id']!=x['beta_token_id'],'frozen distinct answer token IDs')

def capture_batch(backend,items):
 """Right-pad prompts; duplicate only the last gather index, then trim the gather padding."""
 import torch
 from mats.capture import capture
 positions=[list(range(x['first_content_index'],x['read_index']+1)) for x in items]
 width=max(map(len,positions));gather=[p+[p[-1]]*(width-len(p)) for p in positions]
 with backend.oracle.base(),torch.no_grad():
  hs=capture(backend.oracle.model,[x['ids'][:x['read_index']+1] for x in items],[42,44],gather,batch_size=8,pad_id=backend.oracle.tok.pad_token_id or 0)
 full=[];points={42:[],44:[]}
 for i,p in enumerate(positions):
  for layer in points:
   h=hs[layer][i,:len(p)].float().cpu().numpy();require(h.shape==(len(p),5120) and np.isfinite(h).all(),'capture shape/finiteness')
   points[layer].append(h[-1].copy())
   if layer==44:
    v=h.astype(np.float16);require(np.isfinite(v).all(),'fp16 overflow');full.append(v)
 return full,{l:np.stack(v) for l,v in points.items()}

def behaviour(backend,x):
 import torch
 tok=backend.oracle.tok
 require(tok.encode(' alpha',add_special_tokens=False)==[x['alpha_token_id']] and tok.encode(' beta',add_special_tokens=False)==[x['beta_token_id']],'frozen single-token alpha/beta')
 device=backend.oracle.model.get_input_embeddings().weight.device
 ids=torch.tensor([x['ids'][:x['read_index']+1]],device=device)
 with backend.oracle.base(),torch.no_grad():
  z=backend.oracle.model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False).logits[0,-1].float();p=z.softmax(-1)
 a,b=p[x['alpha_token_id']].item(),p[x['beta_token_id']].item()
 return dict(id=x['id'],base_item_id=x['base_item_id'],feature=x['feature'],P_alpha=a,P_beta=b,score=a-b)

def acquire_capture(items,backend,budget,out,binding):
 validate_items(items);backend.validate_tokenization(items)
 cap=Path(out)/'capture';cap.mkdir();offsets=np.zeros(len(items)+1,dtype=np.int64)
 offsets[1:]=np.cumsum([x['read_index']-x['first_content_index']+1 for x in items])
 full=np.lib.format.open_memmap(cap/'all_positions44.npy',mode='w+',dtype=np.float16,shape=(int(offsets[-1]),5120))
 points={l:np.lib.format.open_memmap(cap/f'acts{l}.npy',mode='w+',dtype=np.float32,shape=(len(items),5120)) for l in (42,44)}
 for start in range(0,len(items),8):
  xs=items[start:start+8];spans,readpoints=budget.call('e62_capture_all_positions',lambda:capture_batch(backend,xs),(len(items)-start-1)//8)
  for j,v in enumerate(spans):full[offsets[start+j]:offsets[start+j+1]]=v
  for l in points:points[l][start:start+len(xs)]=readpoints[l]
 full.flush()
 for h in points.values():h.flush()
 np.save(cap/'offsets.npy',offsets);dump(cap/'items.order.json',[x['id'] for x in items])
 dump(cap/'POSITIONS.json',[{k:x[k] for k in ('id','base_item_id','state','rung','split','first_content_index','read_index')} for x in items])
 seal(cap,'CAPTURE_SEAL.json',dict(binding,block=44,full_prompt_interval='first_content_index..read_index inclusive',dtype='float16',offsets='half-open offsets into all_positions44.npy'))
 return cap

def acquire_readers(items,backend,budget,out,cap):
 out=Path(out);points={l:np.load(cap/f'acts{l}.npy',mmap_mode='r') for l in (42,44)}
 test=[i for i,x in enumerate(items) if x['split']=='test'];scores=[]
 for i in test:
  if items[i]['rung']=='L4':scores.append(budget.call('e62_base_behaviour',lambda:behaviour(backend,items[i])))
 dump(out/'BEHAVIOUR.json',scores)
 for reader in ('oracle','nla'):
  if reader=='nla':budget.call('e62_nla_setup',backend.load_nla)
  with (out/(reader+'.native.jsonl')).open('x') as f:
   for start in range(0,len(test),8):
    ix=test[start:start+8];xs=[items[i] for i in ix];layer=44 if reader=='oracle' else 42
    groups=budget.call('e62_'+reader+'_native',lambda:backend.native_one(reader,points[layer][ix]),(len(test)-start-1)//8)
    for r in readout_records(reader,xs,groups,'text'):f.write(json.dumps(r,allow_nan=False)+'\n')
 dump(out/'NLA_TRUNCATION.json',truncation_summary([json.loads(x) for x in (out/'nla.native.jsonl').read_text().splitlines()]))
