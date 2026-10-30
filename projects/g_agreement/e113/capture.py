"""Native lens injection, greedy first token, actual residual at both sites."""
import numpy as np


def capture_lens(lens,vectors,layer=44):
    import torch
    from mats.capture import decoder_blocks
    h=np.asarray(vectors)
    if h.ndim!=2 or not len(h) or not np.isfinite(h).all() or np.any(np.linalg.norm(h.astype(np.float64),axis=1)==0):raise ValueError('finite nonzero sealed activations')
    blocks=decoder_blocks(lens.model);ids0,slot=lens.carrier(layer)
    ids=torch.tensor([ids0]*len(h),device=lens.model.get_input_embeddings().weight.device)
    embeds=lens._embed(ids,slot,torch.from_numpy(np.array(h,copy=True)))
    values={i:[[],[]] for i in range(len(blocks))};phase=[0];handles=[]
    def observe(block):
        def hook(module,args,output):
            z=output[0] if isinstance(output,tuple) else output
            expected=len(ids0)+phase[0]
            if z.shape[:2]!=(len(h),expected):raise ValueError('full carrier/first-token state shape')
            position=slot if phase[0]==0 else len(ids0)
            values[block][phase[0]].append(z[:,position].float().detach().cpu().numpy().copy())
        return hook
    try:
        for i,b in enumerate(blocks):handles.append(b.register_forward_hook(observe(i)))
        with torch.inference_mode():
            token=lens.model.generate(inputs_embeds=embeds,attention_mask=torch.ones_like(ids),do_sample=False,
                 max_new_tokens=1,pad_token_id=lens.tok.pad_token_id or lens.tok.eos_token_id)
            if token.shape!=(len(h),1):raise ValueError('exactly one native greedy token')
            phase[0]=1
            extended=torch.cat((embeds,lens.model.get_input_embeddings()(token)),dim=1)
            lens.model(inputs_embeds=extended,attention_mask=torch.ones(extended.shape[:2],dtype=torch.long,device=ids.device),
                 use_cache=False,logits_to_keep=1)
    finally:
        for handle in handles:handle.remove()
    if any(len(v)!=1 for pair in values.values() for v in pair):raise ValueError('exactly one capture at every layer/site')
    states=np.stack([np.stack([v[0] for v in values[b]],axis=1) for b in values],axis=1)
    if not np.isfinite(states).all():raise ValueError('finite lens residuals')
    return states,token.detach().cpu().numpy(),dict(layers=list(values),positions=['injected_activation','first_generated_token'],
       injected_position=slot,first_generated_position=len(ids0),carrier_ids=ids0,source_layer=layer,
       alpha=lens.alpha,transform='unit',first_generated_capture='full forward on native injected carrier plus its actual greedy first token; not the last carrier token')
