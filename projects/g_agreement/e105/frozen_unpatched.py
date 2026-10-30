def plain_behaviour(model,items):
    """Frozen candidate token-sum score, with no intervention hook installed."""
    import torch
    device=model.get_input_embeddings().weight.device
    out=[]
    for x in items:
        scores=[]
        for pair in x['candidate_ids']:
            pp=[]
            for candidate in pair:
                ids=torch.tensor([x['ids']+candidate[:-1]],device=device)
                with torch.inference_mode():
                    z=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,logits_to_keep=len(candidate)).logits.float()
                    lp=z.log_softmax(-1)
                    pp.append(float(lp[0,torch.arange(len(candidate),device=device),torch.tensor(candidate,device=device)].sum()))
            scores.append(pp)
        out.append(dict(base_id=x['base_id'],row=x['row'],pair_logprobs=scores))
    return out
