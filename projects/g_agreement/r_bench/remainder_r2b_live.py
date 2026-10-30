"""R2-B native Oracle scoring, prefill taps and mean-ablation machinery.

Imports no model weights. Caller must pass an already verified booking guard;
all real forwards recheck it. This backend is not a complete launch CLI.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
from pathlib import Path
import numpy as np
from projects.g_agreement.r_bench import remainder_r2b as D


class PrefillTaps:
    """Save just the last carrier position; never candidate/generated tokens.

One intervention in prefill only. Clone outputs to avoid mutating shared views.
Captured post-ablation states permit a manipulation check in the same forward.
"""
    def __init__(self, blocks, position, selected=None, mean=None, normal=None, magnitude_normal=None):
        self.blocks=blocks; self.position=position
        self.layers=D.tap_blocks(len(blocks)); self.selected=selected
        self.mean=mean; self.normal=normal; self.magnitude_normal=magnitude_normal; self.handles=[]
        self.values={k:[] for k in self.layers}; self.ablation_calls=0; self.displacements=[]
        if position < 1: raise ValueError(f'Invalid prefill position {position}')
        if selected is not None and selected not in self.layers:
            raise ValueError(f'Unregistered ablation block {selected}')

    def __enter__(self):
        import torch
        for layer in self.layers:
            def hook(_module,_inputs,out,layer=layer):
                h=out[0] if isinstance(out,tuple) else out
                if h.shape[1]<=self.position:
                    return out  # autoregressive single-token decode; no re-ablation
                if layer==self.selected:
                    mu=torch.as_tensor(self.mean,device=h.device,dtype=torch.float32)
                    u=torch.as_tensor(self.normal,device=h.device,dtype=torch.float32)
                    if mu.shape!=(h.shape[-1],) or u.shape!=mu.shape or not torch.isfinite(mu).all() or not torch.isfinite(u).all() or not torch.isclose(u.norm(),u.new_tensor(1.),atol=1e-5):
                        raise ValueError(f'Invalid ablation vector at block {layer}')
                    q=u if self.magnitude_normal is None else torch.as_tensor(self.magnitude_normal,device=h.device,dtype=torch.float32)
                    if q.shape!=u.shape or not torch.isfinite(q).all() or not torch.isclose(q.norm(),q.new_tensor(1.),atol=1e-5):
                        raise ValueError(f'Invalid magnitude normal at block {layer}')
                    if self.magnitude_normal is not None and not torch.isclose(q@u,q.new_tensor(0.),atol=1e-5):
                        raise ValueError(f'Nonorthogonal random control at block {layer}')
                    h=h.clone(); v=h[:,self.position,:].float()
                    # Random control uses the decoded component's signed magnitude,
                    # not its own projection, so each item's displacement is matched.
                    magnitude=(v-mu)@q
                    changed=(v-magnitude.unsqueeze(-1)*u).to(h.dtype)
                    self.displacements.extend([dict(intended_l2=float(a),realized_l2=float(b)) for a,b in zip(magnitude.abs().detach().cpu(),(changed.float()-v).norm(dim=-1).detach().cpu())])
                    h[:,self.position,:]=changed
                    out=(h,*out[1:]) if isinstance(out,tuple) else h
                    self.ablation_calls+=1
                self.values[layer].append(h[:,self.position,:].detach().to(torch.float16).cpu())
                return out
            self.handles.append(self.blocks[layer].register_forward_hook(hook))
        return self

    def __exit__(self,*args):
        for handle in self.handles:handle.remove()
        self.handles=[]

    def arrays(self, candidate_pairs=False):
        import torch
        result={}
        for layer,values in self.values.items():
            if not values:raise ValueError(f'Missing prefill tap block {layer}')
            x=torch.cat(values)
            if candidate_pairs:
                if len(x)%2 or not torch.equal(x[0::2],x[1::2]):
                    raise ValueError(f'Candidate-dependent prefill tap block {layer}')
                x=x[0::2]
            result[layer]=x.numpy()
        if self.selected is not None and not self.ablation_calls:
            raise ValueError(f'Ablation never fired block {self.selected}')
        return result


def text_head(reader, layer, text):
    """Replace the native marker token by literal text; no activation injection.

This fixed carrier manipulation is distinct from a positive-system-prompt arm.
Record head SHA and truncation in the job manifest before use.
"""
    from projects.g_agreement.core.scoring_lo import encode
    ids,slot,_,_=reader.carrier(layer)
    if not isinstance(text,str) or not text.strip():raise ValueError('Empty text control')
    tokens=encode(reader.target.tokenizer,text)
    if not tokens:raise ValueError('Empty text tokenization')
    return list(ids[:slot])+tokens+list(ids[slot+1:])


def oracle_score(reader, states, pairs, layer, guard, batch=16, head_override=None, ablation=None):
    """Native bullet likelihoods plus compact taps. One head per batch bucket."""
    import torch
    from projects.g_agreement.core import model as M, scoring_lo as LO
    if len(states)!=len(pairs) or batch<2:raise ValueError('Invalid scoring batch')
    guard()  # must precede any embeddings/model call
    t=reader.target; ids,slot,_,_=reader.carrier(layer)
    head=list(ids if head_override is None else head_override)
    dev=next(t.model.parameters()).device; embed=t.model.get_input_embeddings()
    pad=t.tokenizer.pad_token_id
    if pad is None:pad=t.tokenizer.eos_token_id
    rows=[];taps={k:[] for k in D.tap_blocks(len(M.blocks(t.model)))}
    for start in range(0,len(pairs),max(1,batch//2)):
        guard(); subset=pairs[start:start+max(1,batch//2)]
        token_rows=[head+LO.encode(t.tokenizer,LO.OLENS_BULLET.format(X=c)) for pair in subset for c in pair]
        def embed_fn(ids_t):
            e=embed(ids_t).clone()
            for i in range(len(subset)):
                v=states[start+i].to(dev).float()
                for j in (2*i,2*i+1):e[j,slot,:]=(reader.alpha*v/v.norm().clamp_min(1e-9)).to(e.dtype)
            return e
        with PrefillTaps(M.blocks(t.model),len(head)-1,**(ablation or {})) as hook:
            lp=LO._summed_logprobs(t.model,token_rows,len(head),pad,dev,
                                  embed_fn=embed_fn if head_override is None else None)
        for k,x in hook.arrays(candidate_pairs=True).items():taps[k].append(x)
        for i,pair in enumerate(subset):
            rows.append(dict(lp_A=lp[2*i],lp_B=lp[2*i+1],lo=lp[2*i]-lp[2*i+1],
                             candidates=list(pair),head_sha256=D.digest(head),read_site=layer,
                             displacement=hook.displacements[2*i] if hook.displacements else None))
    return rows,{k:np.concatenate(v) for k,v in taps.items()}


def oracle_free(reader,state,layer,guard,head_override=None,ablation=None):
    import torch
    from projects.g_agreement.core import model as M
    from projects.g_agreement.core.generate import generate_ids
    guard()
    t=reader.target;ids,slot,_,_=reader.carrier(layer)
    head=list(ids if head_override is None else head_override)
    dev=next(t.model.parameters()).device
    kwargs={}
    if head_override is None:
        with torch.no_grad():
            e=t.model.get_input_embeddings()(torch.tensor([head],device=dev)).clone()
            v=state.to(dev).float();e[0,slot,:]=(reader.alpha*v/v.norm().clamp_min(1e-9)).to(e.dtype)
        kwargs['inputs_embeds']=e
    with PrefillTaps(M.blocks(t.model),len(head)-1,**(ablation or {})) as hook:
        result=generate_ids(t.model,t.tokenizer,head,max_new_tokens=128,
                            sampling={'do_sample':False},seed=D.SEED,adapter_enabled=True,**kwargs)
    hook.arrays()  # assert all registered blocks fired, including ablation
    return dict(raw_output=result.raw_output,finish_reason=result.finish_reason,
                n_new_tokens=result.n_new_tokens,wall_s=result.wall_s,
                head_sha256=D.digest(head),read_site=layer)


def nla_score(reader,states,pairs,family,guard,batch=16):
    """Native NLA scoring with taps at final carrier token, before prefix/candidates."""
    from projects.g_agreement.core import model as M,scoring_lo as LO
    guard()
    if len(LO.templates_for(family))!=1:
        raise ValueError(f'NLA requires one frozen template: {family}')
    with PrefillTaps(M.blocks(reader.model),len(reader.ids)-1) as hook:
        rows=LO.lo_nla(reader,states,pairs,family,batch=batch)
    return rows,hook.arrays(candidate_pairs=True)
