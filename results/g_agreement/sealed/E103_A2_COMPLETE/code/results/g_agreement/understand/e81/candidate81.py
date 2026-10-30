"""CPU-reviewable 6fa mixed-length candidate; PROFILE_ONLY, never a launch approval.

Original left-padding helper is preserved in batching_6fa.py. The real-item
parity gate is retained; its synthetic byte_parity helper is never used here.
"""
import sys
import worker81 as W
from runtime import Runtime
from batching_6fa import left_padded
from batch_parity import trim_generated
import parity81


class PaddedRuntime(Runtime):
    def text(self,sequences,max_new_tokens=128):
        import torch
        W.require(max_new_tokens in (32,128),'frozen greedy text length')
        model,tok,cm=self.subject()
        pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        tokens,mask=left_padded(sequences,pad,model.get_input_embeddings().weight.device)
        with cm,torch.inference_mode():
            out=model.generate(input_ids=tokens,attention_mask=mask,do_sample=False,
                max_new_tokens=max_new_tokens,pad_token_id=pad)
        eos=getattr(getattr(model,'generation_config',None),'eos_token_id',None)
        if eos is None:eos=tok.eos_token_id
        eos=set(eos if isinstance(eos,(list,tuple)) else [eos])-{None}
        parity81.EOS_IDS=eos
        rows=[trim_generated(x,eos) for x in out[:,tokens.shape[1]:].cpu().tolist()]
        return [dict(raw=tok.decode(x,skip_special_tokens=True),token_ids=x) for x in rows]


def jobs(items,batch_size):
    W.require(type(batch_size)is int and 32<=batch_size<=64 and batch_size%8==0,'batch32..64 divisible by8')
    groups={}
    for x in items:groups.setdefault(x['max_new_tokens'],[]).append(x)
    return [(limit,xs[i:i+batch_size]) for limit,group in sorted(groups.items(),reverse=True)
            for xs in [sorted(group,key=lambda x:len(x['input_ids']),reverse=True)]
            for i in range(0,len(xs),batch_size)]


def install():
    import batch_parity
    W.Runtime=PaddedRuntime;W.jobs=jobs
    batch_parity.check_outputs=parity81.check_outputs


def main():
    W.require('--profile-only' in sys.argv or '--help' in sys.argv,'candidate is PROFILE_ONLY; production forbidden')
    install();W.main()

if __name__=='__main__':main()
