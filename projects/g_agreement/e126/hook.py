"""§235 read-token restoration/insertion, composed with the unchanged E104 U hook."""
import hashlib
import numpy as np
from projects.g_agreement.e101.acquisition import behaviour
from projects.g_agreement.e101.intervention104 import intervene_forward
LAYERS=(44,48,52,56,60)
SEED=20261029


def controls(identity,read_position,block,dimension,direction):
    """Freeze implementation RNG before output; exclude all eight U write positions."""
    if block not in LAYERS or read_position<=8 or dimension<1 or direction not in ('restore','insert'):raise ValueError('registered sites/direction and eligible earlier token')
    seed=int.from_bytes(hashlib.sha256(f'E126:{SEED}:{identity}:{block}:{direction}'.encode()).digest()[:8],'big')
    rng=np.random.default_rng(seed);earlier=int(rng.integers(0,read_position-8))
    unit=rng.standard_normal(dimension);unit=(unit/np.linalg.norm(unit)).astype(np.float32)
    return earlier,unit


def forward(model,sequences,read_positions,payload,block,keep,*,direction,control,observations=None):
    """payload rows: [signed upstream delta, replacement residual, random unit, earlier position].

    The same rows are replicated by the original E101 continuation scorer. The
    upstream delta already includes alpha/sign and is applied ONCE at each U site.
    Replacement occurs at decoder OUTPUT, never at the next block's input by offset.
    """
    import torch
    from mats.capture import decoder_blocks
    p=np.asarray(payload)
    if block not in LAYERS or direction not in ('restore','insert') or control not in ('read','earlier','random'):
        raise ValueError('registered E126 cell')
    if p.ndim!=2 or len(p)!=len(sequences) or (p.shape[1]-1)%3 or not np.isfinite(p).all():raise ValueError('finite E126 payload')
    d=(p.shape[1]-1)//3
    if not sequences or len({len(s)for s in sequences})!=1 or len(read_positions)!=len(sequences) or any(type(q)is not int or not 8<q<len(s)for q,s in zip(read_positions,sequences)):
        raise ValueError('equal unpadded sequences and original read positions')
    earlier=p[:,-1]
    if np.any(earlier!=np.floor(earlier)) or any(not 0<=q<r-8 for q,r in zip(earlier,read_positions)):raise ValueError('earlier positions exclude U sites/read token')
    units=p[:,2*d:3*d]
    if control=='random' and not np.allclose(np.linalg.norm(units,axis=1),1.,atol=1e-6):raise ValueError('unit random direction')
    seen=[];metrics=[]
    def patch(module,args,output):
        if seen:raise RuntimeError('one full prefill patch per call')
        z=output[0] if isinstance(output,tuple) else output
        if z.shape!=(len(sequences),len(sequences[0]),d):raise ValueError('aligned E126 residual shape')
        edited=z.clone();target=torch.as_tensor(p[:,d:2*d].copy(),device=z.device,dtype=torch.float32)
        read=torch.stack([z[i,q].float()for i,q in enumerate(read_positions)])
        delta=target-read
        for i,r in enumerate(read_positions):
            q=int(earlier[i])if control=='earlier'else r
            before=z[i,q].float()
            if control=='random':
                value=before+torch.linalg.vector_norm(delta[i])*torch.as_tensor(units[i].copy(),device=z.device)
            else:value=target[i]
            edited[i,q]=value.to(z.dtype)
            after=edited[i,q].float();bn=float(torch.linalg.vector_norm(before));an=float(torch.linalg.vector_norm(after))
            metrics.append(dict(block=block,position=q,read_position=r,control=control,direction=direction,
                delta_norm=float(torch.linalg.vector_norm(after-before)),reference_read_replacement_delta_norm=float(torch.linalg.vector_norm(delta[i])),
                before_norm=bn,after_norm=an,norm_ratio=an/bn if bn>0 else None,upstream_hook_installed=direction=='restore'))
        if not torch.isfinite(edited).all():raise ValueError('nonfinite E126 residual')
        seen.append(True)
        return (edited,*output[1:])if isinstance(output,tuple)else edited
    h=decoder_blocks(model)[block].register_forward_hook(patch)
    try:
        if direction=='restore':
            logits,_,_=intervene_forward(model,sequences,read_positions,p[:,:d].copy(),'U',keep,observe=False)
        else:
            ids=torch.tensor(sequences,device=model.get_input_embeddings().weight.device)
            with torch.inference_mode():logits=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,logits_to_keep=keep).logits.float()
        if len(seen)!=1 or logits.shape[:2]!=(len(sequences),keep) or not torch.isfinite(logits).all():raise ValueError('one E126 patch and finite scored logits')
    finally:h.remove()
    if observations is not None:observations.extend(metrics)
    return logits


def score_batch(model,items,payload):
    """Frozen E101 summed continuation pairs AND prefix logits, no reader or labels."""
    if not items or len({(x['block'],x['direction'],x['control'],len(x['ids']))for x in items})!=1:raise ValueError('homogeneous E126 batch')
    if any(x['read_index']!=len(x['ids'])-1 for x in items):raise ValueError('original scoring prefix')
    x=items[0];observed=[];before=np.asarray(payload).tobytes()
    def call(m,sequences,positions,values,block,keep):
        return forward(m,sequences,positions,values,block,keep,direction=x['direction'],control=x['control'],observations=observed if not observed else None)
    records=behaviour(model,items,payload,'continuation',forward=call)
    if len(observed)!=len(items)or np.asarray(payload).tobytes()!=before:raise ValueError('prefix metrics and immutable supplied states')
    return [dict(r,id=i['id'],input_id=i.get('input_id',i['id']),vector_index=i.get('vector_index'),block=i['block'],direction=i['direction'],control=i['control'],**{'patch':m})for i,r,m in zip(items,records,observed)]
