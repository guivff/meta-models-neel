"""§213: norm-preserving read-site edits and upstream edits at eight prior sites."""
import numpy as np
from .acquisition import behaviour

WRITE_BLOCK={'N':44,'U':40}
READ_BLOCK=44
NORM_CONVENTION='L2 norm of concatenated write-site residuals'


def write_positions(arm,read_positions):
    if arm not in WRITE_BLOCK:raise ValueError('registered E104 arm')
    if any(type(p)is not int or p<0 or (arm=='U' and p<8) for p in read_positions):
        raise ValueError('U needs all eight existing positions before the read token')
    return [[p] if arm=='N' else list(range(p-8,p)) for p in read_positions]


def _norm(v):
    import torch
    return torch.linalg.vector_norm(v.float(),dim=-1)


def intervene_forward(model,sequences,read_positions,deltas,arm,keep,*,observe=True,captures=None,natural_read=None):
    """Deltas are precomposed alpha*raw_norm*sigma*unit; no labels on GPU.

    U adds the same delta at each of eight preceding positions, never the read
    token. N renormalizes the live natural residual, then casts to model dtype.
    Observations describe actual tensors after that cast. For U an unedited pass
    supplies the natural block44 read vector; it is never substituted into the
    intervened pass. The subsequent block44 vector is produced by the model.
    """
    import torch
    from mats.capture import decoder_blocks
    delta=np.asarray(deltas)
    if (not sequences or len({len(s) for s in sequences})!=1 or not sequences[0]
        or delta.ndim!=2 or len(delta)!=len(sequences) or not np.isfinite(delta).all()
        or len(read_positions)!=len(sequences) or any(p>=len(s) for p,s in zip(read_positions,sequences))
        or type(keep)is not int or not 1<=keep<=len(sequences[0])):raise ValueError('finite aligned E104 prefill')
    sites=write_positions(arm,read_positions);blocks=decoder_blocks(model)
    tokens=torch.tensor(sequences,device=model.get_input_embeddings().weight.device)
    natural=[];read_vectors=[];write_before=[];write_after=[];seen=[]
    def take(z,positions):return torch.stack([z[i,p].float() for i,p in enumerate(positions)])
    def natural_hook(module,args,output):
        z=output[0] if isinstance(output,tuple) else output
        natural.append(take(z,read_positions).detach().cpu().numpy())
    if natural_read is not None:
        reference=np.asarray(natural_read)
        if arm!='U' or not observe or reference.shape!=delta.shape or not np.isfinite(reference).all():
            raise ValueError('aligned unhooked read reference for U observations')
        natural.append(reference.copy())
    if observe and arm=='U' and natural_read is None:
        handle=blocks[READ_BLOCK].register_forward_hook(natural_hook)
        try:
            with torch.inference_mode():model(input_ids=tokens,attention_mask=torch.ones_like(tokens),use_cache=False,logits_to_keep=1)
        finally:handle.remove()
        if len(natural)!=1:raise ValueError('one natural read-site observation')
    def patch(module,args,output):
        if seen:raise ValueError('exactly one full-prefill E104 patch')
        z=output[0] if isinstance(output,tuple) else output
        if z.shape[:2]!=tokens.shape or z.shape[-1]!=delta.shape[1]:raise ValueError('E104 residual shape')
        original=torch.stack([z[i,ps].float() for i,ps in enumerate(sites)])
        v=torch.as_tensor(np.array(delta,copy=True),device=z.device,dtype=torch.float32)
        edited=original+v[:,None,:]
        if arm=='N':
            before_norm=_norm(original);after_norm=_norm(edited)
            if not torch.isfinite(after_norm).all() or bool((after_norm==0).any()) or bool((before_norm==0).any()):
                raise ValueError('undefined norm-preserving zero vector')
            edited=edited*(before_norm/after_norm)[:,:,None]
        if not torch.isfinite(edited).all():raise ValueError('non-finite E104 edit')
        z=z.clone()
        for i,ps in enumerate(sites):z[i,ps]=edited[i].to(z.dtype)
        if observe:
            write_before.append(original.detach().cpu().numpy())
            write_after.append(torch.stack([z[i,ps].float() for i,ps in enumerate(sites)]).detach().cpu().numpy())
            if arm=='N':natural.append(original[:,0,:].detach().cpu().numpy())
        seen.append(True)
        return (z,*output[1:]) if isinstance(output,tuple) else z
    def capture_read(module,args,output):
        z=output[0] if isinstance(output,tuple) else output
        read_vectors.append(take(z,read_positions).detach().cpu().numpy())
    handles=[]
    try:
        if captures is not None:
            if not captures or any(type(l)is not int or not 40<l<len(blocks) or v for l,v in captures.items()):
                raise ValueError('empty downstream capture lists at existing blocks')
            def downstream(layer):
                def hook(module,args,output):
                    z=output[0] if isinstance(output,tuple) else output
                    captures[layer].append(take(z,read_positions).detach().cpu().numpy())
                return hook
            for layer in captures:handles.append(blocks[layer].register_forward_hook(downstream(layer)))
        handles.append(blocks[WRITE_BLOCK[arm]].register_forward_hook(patch))
        if observe:handles.append(blocks[READ_BLOCK].register_forward_hook(capture_read))
        with torch.inference_mode():
            logits=model(input_ids=tokens,attention_mask=torch.ones_like(tokens),use_cache=False,logits_to_keep=keep).logits.float()
            if not torch.isfinite(logits).all():raise ValueError('non-finite E104 logits')
    finally:
        for handle in handles:handle.remove()
    if len(seen)!=1 or logits.shape[:2]!=(len(sequences),keep):raise ValueError('one E104 patch and expected output shape')
    if not observe:return logits,None,None
    if len(natural)!=1 or len(read_vectors)!=1 or len(write_before)!=1:raise ValueError('complete E104 site observations')
    metrics=[]
    for i,(before,after,read_before,read_after) in enumerate(zip(write_before[0],write_after[0],natural[0],read_vectors[0])):
        bn=np.linalg.norm(before.astype(np.float64),axis=-1);an=np.linalg.norm(after.astype(np.float64),axis=-1)
        rb=float(np.linalg.norm(read_before.astype(np.float64)));ra=float(np.linalg.norm(read_after.astype(np.float64)))
        ib=float(np.linalg.norm(before.astype(np.float64)));ia=float(np.linalg.norm(after.astype(np.float64)))
        if not np.isfinite([rb,ra,ib,ia]).all() or min(rb,ra,ib,ia)<=0 or np.any(bn==0):raise ValueError('finite nonzero observed norm denominators')
        metrics.append(dict(injection_sites=[dict(block=WRITE_BLOCK[arm],position=p,before_norm=float(b),after_norm=float(a),norm_ratio=float(a/b),off_distribution=bool(a/b>1.5)) for p,b,a in zip(sites[i],bn,an)],
            injection_norm_before=ib,injection_norm_after=ia,norm_ratio=ia/ib,injection_norm_convention=NORM_CONVENTION,
            read_site=dict(block=READ_BLOCK,position=read_positions[i],before_norm=rb,after_norm=ra,norm_ratio=ra/rb),
            read_norm_before=rb,read_norm_after=ra,read_norm_ratio=ra/rb,off_distribution=ia/ib>1.5,
            injection_any_site_over_1_5=bool(np.any(an/bn>1.5)),read_over_1_5=ra/rb>1.5))
    return logits,metrics,read_vectors[0]


def behaviour104(model,items,deltas,mode='continuation'):
    """Use the E101 frozen scorer with an explicit alternate write-site forward."""
    if not items or len({x['arm'] for x in items})!=1:raise ValueError('one E104 arm per batch')
    arm=items[0]['arm'];observed=[]
    def forward(m,sequences,read_positions,values,block,keep):
        if block!=WRITE_BLOCK[arm]:raise ValueError('arm/write-block binding')
        logits,metrics,vectors=intervene_forward(m,sequences,read_positions,values,arm,keep,observe=not observed)
        if metrics is not None:observed.append((metrics,vectors))
        return logits
    records=behaviour(model,items,deltas,mode,forward=forward)
    if len(observed)!=1:raise ValueError('exactly one prefix observation per behaviour cell')
    metrics,vectors=observed[0]
    return [dict(r,**metric) for r,metric in zip(records,metrics)],vectors
