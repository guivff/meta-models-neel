"""Pinned native readers; no item text is passed to a verbalizer."""
import gc,importlib.metadata,os,sys
from pathlib import Path
import numpy as np
from common76 import *
sys.path.insert(0,str(HERE/'vendor'))


class Backend:
    def __init__(self,assets):
        import torch
        from operational_assets import _assets
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
        require(torch.cuda.is_available() and torch.cuda.device_count()==1 and 'H200' in torch.cuda.get_device_name(),'One H200 required')
        pins=read(HERE/'RUNTIME_PINS.json');names=('torch','transformers','peft','flash-linear-attention','fla-core','causal-conv1d','triton','tokenizers','numpy')
        self.runtime={k:importlib.metadata.version(k) for k in names}
        require(all(self.runtime[k]==pins[k] for k in names),'Pinned native runtime required')
        self.assets=_assets(assets,names=('model','olens','nla'))
        self.oracle=self.nla=None
        self.runtime.update(assets_manifest_sha256=sha(assets),native_layers={'oracle':44,'nla':42},adapter_or_prompt_changes=False)

    def load_oracle(self):
        from operational_assets import _load_oracle
        self.oracle=_load_oracle(self.assets)

    def load_nla(self):
        import torch
        from mats.readers.nla import load_nla
        self.oracle=None;gc.collect();torch.cuda.empty_cache()
        self.nla=load_nla(root=self.assets['nla'],load_ar=False,enable_thinking=False)

    def capture(self,items,batch=64):
        import torch
        from mats.capture import capture
        with self.oracle.base(),torch.no_grad():
            out=capture(self.oracle.model,[x['ids'] for x in items],[42,44],[[-1] for x in items],
                batch_size=batch,pad_id=self.oracle.tok.pad_token_id or 0)
        result={l:out[l][:,0].float().cpu().numpy() for l in (42,44)}
        require(all(x.shape==(len(items),DIM) and np.isfinite(x).all() for x in result.values()),'Finite raw read-point capture required')
        return result

    def native(self,reader,h,batch=32):
        import torch
        if reader=='nla':
            from native_nla512 import native_nla
            return [x[0] for x in native_nla(self.nla,h,k=1,batch=batch)]
        from mats.readers.nla import Sampling
        sampling=Sampling(temperature=0,top_p=1.,top_k=0,max_new_tokens=128)
        with torch.no_grad():out=self.oracle.verbalize(torch.from_numpy(np.array(h,copy=True)),44,k=1,sampling=sampling,batch=batch)
        require(len(out)==len(h) and all(len(x)==1 for x in out),'One greedy Oracle readout per vector required')
        return [{'raw':x[0],'text':x[0],'malformed':False,'native_max_new_tokens':128} for x in out]

    def parity_scores(self,h,pairs):
        """Exact E36 Oracle-descriptive recipe: block44, empty prefix, original batch8."""
        import torch
        with torch.no_grad():
            values=self.oracle.paired_logodds_templates(torch.as_tensor(h),44,pairs,prefix="")
        require(tuple(values.shape)==(2,len(h)) and bool(torch.isfinite(values).all()),'Finite original W1 parity score matrix')
        return values.detach().float().cpu().T.tolist()
