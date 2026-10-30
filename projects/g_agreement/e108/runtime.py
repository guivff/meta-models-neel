"""E56/E57 Runtime binding; only the new registered base greedy64 limit is added."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/late198'))
from runtime import Runtime

class Runtime108(Runtime):
    def text64(self,sequences):
        import torch
        from batch_parity import trim_generated
        model,tok,cm,tokens=self.token_batch(sequences)
        with cm,torch.inference_mode():
            out=model.generate(input_ids=tokens,attention_mask=torch.ones_like(tokens),do_sample=False,
                max_new_tokens=64,pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id)
        eos=getattr(getattr(model,'generation_config',None),'eos_token_id',None)
        if eos is None:eos=tok.eos_token_id
        eos=set(eos if isinstance(eos,(list,tuple)) else [eos])-{None}
        rows=[trim_generated(x.tolist(),eos) for x in out[:,tokens.shape[1]:].cpu()]
        return [dict(raw=tok.decode(x,skip_special_tokens=True),token_ids=x) for x in rows]
