"""Hook lens block outputs only while processing generated answer tokens."""
import numpy as np

def read(lens,vectors,delta,lens_layer,source_layer=44,blocks=None):
    import torch
    if blocks is None:
        from mats.capture import decoder_blocks
        blocks=decoder_blocks(lens.model)
    h=np.asarray(vectors);d=np.asarray(delta)
    if h.ndim!=2 or d.shape!=h.shape or not np.isfinite(h).all() or not np.isfinite(d).all() or np.any(np.linalg.norm(h.astype(float),axis=1)==0):raise ValueError('finite nonzero carrier and matched delta')
    if not 0<=lens_layer<len(blocks):raise ValueError('actual lens layer')
    ids0,slot=lens.carrier(source_layer);ids=torch.tensor([ids0]*len(h),device=lens.model.get_input_embeddings().weight.device)
    embeds=lens._embed(ids,slot,torch.from_numpy(np.array(h,copy=True)))
    calls=[];norms=[]
    def hook(module,args,out):
        z=out[0] if isinstance(out,tuple) else out
        if not calls:
            if z.shape[:2]!=(len(h),len(ids0)):raise ValueError('native full prefill expected')
            calls.append('prefill_untouched');return out
        if z.shape[:2]!=(len(h),1):raise ValueError('cached generated-token decode only')
        before=z.float();add=torch.as_tensor(np.array(d,copy=True),device=z.device,dtype=z.dtype)[:,None,:]
        patched=z+add;after=patched.float();bn=before.norm(dim=-1);an=after.norm(dim=-1)
        if not bool(torch.isfinite(after).all()) or bool((bn==0).any()):raise ValueError('finite nonzero injection-site norm')
        norms.append(dict(generated_position=len(calls)-1,absolute_position=len(ids0)+len(calls)-1,
            injection_site_norm_before=bn[:,0].detach().cpu().tolist(),injection_site_norm_after=an[:,0].detach().cpu().tolist(),
            norm_ratio=(an/bn)[:,0].detach().cpu().tolist(),actual_delta_norm=(after-before).norm(dim=-1)[:,0].detach().cpu().tolist()))
        calls.append('generated');return (patched,*out[1:]) if isinstance(out,tuple) else patched
    handle=blocks[lens_layer].register_forward_hook(hook)
    try:
        with torch.inference_mode():tokens=lens.model.generate(inputs_embeds=embeds,attention_mask=torch.ones_like(ids),do_sample=False,max_new_tokens=128,use_cache=True,pad_token_id=lens.tok.pad_token_id or lens.tok.eos_token_id)
    finally:handle.remove()
    if not calls or tokens.ndim!=2 or len(tokens)!=len(h):raise ValueError('native greedy result')
    texts=[t.strip() for t in lens.tok.batch_decode(tokens,skip_special_tokens=True)]
    return [dict(raw=text,text=text,token_ids=tok,generated_tokens=len(tok),unique_token_count=len(set(tok)),
                 repeated_token_count=len(tok)-len(set(tok)),empty_text=not bool(text),norm_trace=[dict(n,**{k:v[i] for k,v in n.items() if isinstance(v,list)}) for n in norms],
                 lens_layer=lens_layer,source_layer=source_layer,first_answer_token_selected_before_hook=True)
            for i,(text,tok) in enumerate(zip(texts,tokens.detach().cpu().tolist()))]
