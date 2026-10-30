"""Exact E15 operational functions; no scientific loader imports."""
import math

def native_score(name,obj,h,pairs):
    if name=='olens':return obj.paired_logodds_templates(h,44,pairs,prefix='- ')
    from mats.readers.nla import paired_logodds_templates
    return paired_logodds_templates(obj,h,pairs,prefix='',batch=32)

def valid_pairs(dev_aurocs):
    return [j for j,v in enumerate(dev_aurocs) if v is not None and math.isfinite(v) and v>=.80]

def base_score(ol,items,pairs):
    """Base text plus candidates; right padding and exact predictive positions."""
    import torch
    columns=[];device=next(ol.model.parameters()).device
    with ol.base(),torch.no_grad():
        for a,b in pairs:
            candidates=[ol.tok.encode(s,add_special_tokens=False) for s in (a,b)]
            if len(candidates[0])!=len(candidates[1]):raise ValueError('candidate token mismatch')
            k=len(candidates[0]);seqs=[x['ids']+c for x in items for c in candidates]
            lengths=torch.tensor([len(x['ids']) for x in items for _ in candidates],device=device)
            n=max(map(len,seqs));ids=torch.full((len(seqs),n),ol.tok.pad_token_id or 0,dtype=torch.long,device=device);mask=torch.zeros_like(ids)
            for j,s in enumerate(seqs):ids[j,:len(s)]=torch.tensor(s,device=device);mask[j,:len(s)]=1
            positions=lengths[:,None]-1+torch.arange(k,device=device)[None,:]
            keep=torch.unique(positions,sorted=True)
            output=ol.model(input_ids=ids,attention_mask=mask,logits_to_keep=keep,use_cache=False)
            rows=torch.arange(len(seqs),device=device)[:,None]
            logits=output.logits[rows,torch.searchsorted(keep,positions)].float()
            targets=ids.gather(1,positions+1)
            values=torch.log_softmax(logits,-1).gather(-1,targets[:,:,None]).squeeze(-1).sum(1).reshape(-1,2)
            columns.append((values[:,0]-values[:,1]).cpu())
    return torch.stack(columns)
