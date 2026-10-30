"""Read-layer arithmetic and genuine upstream block-output prefill intervention."""
import numpy as np
from .contract import require,DIRECTIONS

def ratios(before,after):
 den=np.linalg.norm(before,axis=1);require(np.all(den>0),'nonzero norm denominator');r=np.linalg.norm(after,axis=1)/den
 require(np.isfinite(r).all(),'finite norm ratios');return r

def transform(h,donor,mode,basis=None,complement=False,delta=None,alpha=None):
 h=np.asarray(h,dtype=np.float64);donor=np.asarray(donor,dtype=np.float64)
 require(h.shape==donor.shape and np.isfinite(h).all() and np.isfinite(donor).all(),'carrier/donor grid')
 if mode=='transplant':out=donor.copy()
 elif mode=='swap':
  require(basis is not None and basis.shape[0]==h.shape[1],'swap basis')
  projected=(donor-h)@basis@basis.T
  out=donor-projected if complement else h+projected
 elif mode=='injection':
  require(delta is not None and delta.shape==h.shape and alpha in (.5,1,2,4),'sealed signed full-norm delta and dose')
  out=h+alpha*delta
 else:raise ValueError('unknown read-layer intervention')
 require(np.isfinite(out).all(),'finite patched activations');return np.asarray(out,dtype=np.float32)

class Captured(Exception):pass

def upstream(model,items,delta,block,alpha,blocks=None):
 """Inject at28/36 read token, propagate through subject blocks, capture output44.
 Adapter-off context belongs to the caller. Stop at44; do not decode a subject answer.
 """
 import torch
 require(block in (28,36) and alpha in (1,2),'registered upstream cell')
 require(len(items)==len(delta)>0 and len({len(x['ids']) for x in items})==1,'equal-length prefill, no padding')
 if blocks is None:
  from mats.capture import decoder_blocks
  blocks=decoder_blocks(model)
 ids=torch.tensor([x['ids'] for x in items],device=model.get_input_embeddings().weight.device)
 positions=[x['read_index'] for x in items];require(all(p==ids.shape[1]-1 for p in positions),'read token ends frozen prefix')
 seen=[];captured=[];norm=[]
 def patch(module,args,out):
  if seen:return out
  z=out[0] if isinstance(out,tuple) else out;require(z.shape[:2]==ids.shape,'full prefill patch only');v=torch.as_tensor(np.array(delta,copy=True),device=z.device,dtype=z.dtype)
  require(v.shape==(len(items),z.shape[-1]) and bool(torch.isfinite(v).all()),'upstream delta shape')
  original=torch.stack([z[i,p].float() for i,p in enumerate(positions)]);z=z.clone()
  for i,p in enumerate(positions):z[i,p]=z[i,p]+alpha*v[i]
  edited=torch.stack([z[i,p].float() for i,p in enumerate(positions)])
  norm.extend(ratios(original.cpu().numpy(),edited.cpu().numpy()).tolist());seen.append(True)
  return (z,*out[1:]) if isinstance(out,tuple) else z
 def capture(module,args,out):
  require(len(seen)==1,'upstream patch precedes44 capture');z=out[0] if isinstance(out,tuple) else out
  require(z.shape[:2]==ids.shape,'full downstream prefill');v=torch.stack([z[i,p].float() for i,p in enumerate(positions)])
  require(bool(torch.isfinite(v).all()),'finite downstream activations');captured.append(v.cpu().numpy().copy());raise Captured()
 handles=[]
 try:
  handles.append(blocks[block].register_forward_hook(patch));handles.append(blocks[44].register_forward_hook(capture))
  with torch.inference_mode():
   try:model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False)
   except Captured:pass
 finally:
  for handle in handles:handle.remove()
 require(len(seen)==1 and len(captured)==1,'exactly one upstream patch/capture');return captured[0],norm
