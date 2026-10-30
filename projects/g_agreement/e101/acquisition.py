"""E79 prefill patch, extended to both registered blocks and frozen continuations."""
import numpy as np


def batches(items, size=8):
    if size < 1: raise ValueError('positive batch size')
    groups={}
    for i,x in enumerate(items): groups.setdefault((x['row'] if 'row' in x else '',x['block'],len(x['ids']),tuple(tuple(len(c) for c in pair) for pair in x.get('candidate_ids',[]))),[]).append(i)
    return [v[k:k+size] for _,v in sorted(groups.items()) for k in range(0,len(v),size)]


def patched_forward(model, sequences, positions, vectors, block, keep):
    """Exactly one patch per forward; caller must disable all adapters."""
    import torch
    from mats.capture import decoder_blocks
    h=np.asarray(vectors)
    if block not in (42,44) or h.ndim!=2 or len(h)!=len(sequences) or not np.isfinite(h).all():
        raise ValueError('finite aligned vectors and registered block')
    if len({len(s) for s in sequences})!=1 or not sequences or not sequences[0]:
        raise ValueError('equal-length nonempty sequences')
    if len(positions)!=len(h) or any(type(p)!=int or not 0<=p<len(s) for p,s in zip(positions,sequences)):
        raise ValueError('patch positions')
    tokens=torch.tensor(sequences,device=model.get_input_embeddings().weight.device)
    seen=[]
    def hook(module,args,out):
        if seen: raise RuntimeError('repeated patch hook')
        z=out[0] if isinstance(out,tuple) else out
        if z.shape[:2]!=tokens.shape or z.shape[-1]!=h.shape[1]: raise ValueError('prefill shape')
        z=z.clone();v=torch.as_tensor(np.array(h,copy=True),device=z.device,dtype=z.dtype)
        for i,p in enumerate(positions): z[i,p]=v[i]
        seen.append(True)
        return (z,*out[1:]) if isinstance(out,tuple) else z
    handle=decoder_blocks(model)[block].register_forward_hook(hook)
    try:
        with torch.inference_mode():
            logits=model(input_ids=tokens,attention_mask=torch.ones_like(tokens),use_cache=False,logits_to_keep=keep).logits.float()
            if not torch.isfinite(logits).all(): raise ValueError('non-finite model output')
    finally: handle.remove()
    if len(seen)!=1 or logits.shape[:2]!=(len(h),keep): raise ValueError('exactly one patch and expected logits')
    return logits


def behaviour(model,items,vectors,mode,*,forward=None):
    """Return raw next-token pairs and optional summed continuation log probabilities.

    Candidate order stays frozen. No labels, target orientation, thresholding or dose
    selection occur here. Literal first-token mode intentionally keeps shared tokens.
    """
    import torch
    if mode not in ('next_token','continuation'): raise ValueError('explicit scoring ruling required')
    if len({(x['block'],len(x['ids'])) for x in items})!=1: raise ValueError('homogeneous batch')
    if any(x['read_index']!=len(x['ids'])-1 for x in items): raise ValueError('frozen prompt read token')
    # Alternate forward implementations own their write sites. The read index
    # identifies the frozen scoring prefix, not a mandatory intervention site.
    forward=patched_forward if forward is None else forward
    block=items[0]['block'];positions=[x['read_index'] for x in items]
    logits=forward(model,[x['ids'] for x in items],positions,vectors,block,1)[:,0]
    out=[]
    for x,z in zip(items,logits):
        pairs=x['candidate_ids']
        if not pairs or any(len(p)!=2 or any(not c or any(type(t)!=int or not 0<=t<len(z) for t in c) for c in p) for p in pairs):
            raise ValueError('frozen nonempty candidate token sequences')
        out.append(dict(pair_logits=[[float(z[a[0]]),float(z[b[0]])] for a,b in pairs]))
    if mode=='next_token': return out
    # Group candidates by total length, preserving exact unpadded prompts.
    groups={}
    for i,x in enumerate(items):
        out[i]['pair_logprobs']=[[None,None] for _ in x['candidate_ids']]
        for j,pair in enumerate(x['candidate_ids']):
            for side,cand in enumerate(pair): groups.setdefault(len(cand),[]).append((i,j,side,cand))
    for length,entries in groups.items():
        for start in range(0,len(entries),8):
            sub=entries[start:start+8]
            seq=[items[i]['ids']+c[:-1] for i,_,_,c in sub]
            zz=forward(model,seq,[positions[i] for i,_,_,_ in sub],np.asarray(vectors)[[i for i,_,_,_ in sub]],block,length)
            lp=torch.log_softmax(zz,dim=-1)
            for n,(i,j,side,c) in enumerate(sub):
                score=lp[n,torch.arange(length,device=lp.device),torch.tensor(c,device=lp.device)].sum()
                out[i]['pair_logprobs'][j][side]=float(score)
    return out
