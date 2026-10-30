"""§236 natural-context update: original E109 capture, no intervention, three-token answer."""
from types import FunctionType
import numpy as np
from projects.g_agreement.e101 import runner109
LAYERS=(44,52,60)
# Same original code and globals, isolated layer configuration; no global mutation.
_natural=FunctionType(runner109.natural_capture.__code__,dict(runner109.natural_capture.__globals__,CAPTURE=LAYERS))


def pairs_from_logits(logits,items):
    """Frozen E104 single-token pairs, recorded beside answers without orientation."""
    import torch
    lp=torch.log_softmax(logits.float(),dim=-1);records=[]
    for z,p,x in zip(logits,lp,items):
        if any(len(c)!=1 for pair in x['candidate_ids']for c in pair):raise ValueError('original single-token contrast pairs')
        records.append(dict(pair_logits=[[float(z[a[0]]),float(z[b[0]])]for a,b in x['candidate_ids']],
                            pair_logprobs=[[float(p[a[0]]),float(p[b[0]])]for a,b in x['candidate_ids']]))
    return records


def greedy_three(model,tok,items,forward=None):
    """No sampling/cache; full-prefix recomputation preserves a supplied U prefill callback."""
    import torch
    if not items or len({len(x['ids'])for x in items})!=1:raise ValueError('equal unpadded prompts')
    sequences=[list(x['ids'])for x in items];positions=[x['read_index']for x in items]
    if any(p!=len(s)-1 for p,s in zip(positions,sequences)):raise ValueError('frozen original final read token')
    eos=getattr(tok,'eos_token_id',None);eos=set(eos if isinstance(eos,(list,tuple))else []if eos is None else [eos])
    generated=[[]for _ in items];done=[False]*len(items);first=None
    for step in range(3):
        if forward is None:
            ids=torch.tensor(sequences,device=model.get_input_embeddings().weight.device)
            with torch.inference_mode():z=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,logits_to_keep=1).logits[:,0].float()
        else:z=forward(sequences,positions,step)[:,0].float()
        if not torch.isfinite(z).all():raise ValueError('finite greedy logits')
        if step==0:first=pairs_from_logits(z,items)
        chosen=z.argmax(-1).cpu().tolist()
        for i,t in enumerate(chosen):
            if not done[i]:generated[i].append(t);done[i]=t in eos
            sequences[i].append(t)
        if all(done):break
    return [dict(id=x['id'],token_ids=ts,text=tok.decode(ts,skip_special_tokens=True),greedy_max_new_tokens=3,**r)for x,ts,r in zip(items,generated,first)]


def capture_answer_batch(model,tok,items):
    if any(x['condition']not in ('context_update','neutral_prefix','none')for x in items):raise ValueError('E127 three unchanged conditions')
    captures=_natural(model,items)
    answers=greedy_three(model,tok,items)
    return dict(captures=captures,answers=answers,read_norms={str(L):np.linalg.norm(v.astype(np.float64),axis=-1).tolist()for L,v in captures.items()},intervention_installed=False)


def batches(items,size=8):
    groups={}
    for x in items:groups.setdefault((x['condition'],len(x['ids'])),[]).append(x)
    for _,xs in sorted(groups.items()):
        for i in range(0,len(xs),size):yield xs[i:i+size]
