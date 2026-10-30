"""Base text/forward paths and the existing native reader implementations."""
import contextlib
import gc
import sys
import numpy as np
from contract import ROOT, require

class Runtime:
    def __init__(self, assets):
        self.assets = assets
        self.model = self.tok = self.readers = None

    def sync(self):
        import torch
        if torch.cuda.is_available():
            torch.cuda.synchronize()

    def load_base(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        sys.path.insert(0, str(ROOT))
        from projects.g_agreement.blindspot.run import _assets
        require(torch.cuda.is_available() and torch.cuda.device_count() == 1, 'one CUDA device')
        a = _assets(self.assets, names=('model',))
        self.model = AutoModelForCausalLM.from_pretrained(a['model'], dtype=torch.bfloat16,
                                                       device_map='cuda', local_files_only=True).eval()
        self.tok = AutoTokenizer.from_pretrained(a['model'], local_files_only=True)

    def load_oracle(self):
        import torch
        self.model = self.tok = None
        gc.collect()
        torch.cuda.empty_cache()
        sys.path.insert(0, str(ROOT / 'results/g_agreement/understand/e56/job'))
        from worker56 import Backend
        self.readers = Backend(ROOT, self.assets, {'gpu_type': 'H200'})
        self.readers.load_oracle()

    def load_nla(self):
        self.readers.load_nla()

    def subject(self):
        if self.model is not None:
            return self.model, self.tok, contextlib.nullcontext()
        return self.readers.oracle.model, self.readers.oracle.tok, self.readers.oracle.base()

    def check_tokens(self, items):
        _, tok, _ = self.subject()
        require(all(tok.encode(x['text'], add_special_tokens=False) == x['ids'] for x in items), 'frozen tokenizer mismatch')

    def token_batch(self, sequences):
        import torch
        require(len({len(x) for x in sequences}) == 1, 'equal-length batches only')
        model, tok, cm = self.subject()
        tokens = torch.tensor(sequences, device=model.get_input_embeddings().weight.device)
        return model, tok, cm, tokens

    def next_token(self, sequences):
        """Full-vocabulary greedy answer, not a forced-choice approximation."""
        import torch
        model, tok, cm, tokens = self.token_batch(sequences)
        with cm, torch.inference_mode():
            logits = model(input_ids=tokens, attention_mask=torch.ones_like(tokens),
                           use_cache=False, logits_to_keep=1).logits[:, -1].float()
            top = logits.argmax(-1)
            probabilities = logits.softmax(-1).gather(1, top[:, None]).squeeze(1)
        return [dict(token_id=int(t), decoded=tok.decode([int(t)]), probability=float(p))
                for t, p in zip(top.cpu(), probabilities.cpu())]

    def text(self, sequences, max_new_tokens=128):
        import torch
        require(max_new_tokens in (32,128),'frozen greedy text length')
        model, tok, cm, tokens = self.token_batch(sequences)
        with cm, torch.inference_mode():
            out = model.generate(input_ids=tokens, attention_mask=torch.ones_like(tokens),
                                 do_sample=False, max_new_tokens=max_new_tokens,
                                 pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id)
        suffix = out[:, tokens.shape[1]:].cpu()
        from batch_parity import trim_generated
        eos=getattr(getattr(model,'generation_config',None),'eos_token_id',None)
        if eos is None:eos=tok.eos_token_id
        eos=set(eos if isinstance(eos,(list,tuple)) else [eos])
        rows=[trim_generated(x.tolist(),eos) for x in suffix]
        return [dict(raw=tok.decode(x, skip_special_tokens=True), token_ids=x) for x in rows]

    def capture(self, items):
        import torch
        sys.path.insert(0, str(ROOT / 'external/mats-nla-workspace/src'))
        from mats.capture import capture
        self.check_tokens(items)
        model, tok, cm = self.subject()
        with cm, torch.inference_mode():
            values = capture(model, [x['ids'] for x in items], (42, 44),
                             [[x['read_index']] for x in items], batch_size=8, pad_id=tok.pad_token_id or 0)
        return {layer: values[layer][:, 0].float().cpu().numpy() for layer in (42, 44)}

    def native(self, reader, vectors, sampled=False):
        if not sampled:
            batch=getattr(self,'native_batch_size',8)
            if batch==8:return self.readers.native_one(reader, vectors)
            require(32<=batch<=64,'native batch size')
            if reader=='nla':
                from native_nla512 import native_nla
                return native_nla(self.readers.nla,vectors,k=1,batch=batch)
            import torch
            from mats.readers.nla import Sampling
            with torch.inference_mode():
                groups=self.readers.oracle.verbalize(torch.as_tensor(np.array(vectors,copy=True)),44,k=1,
                    sampling=Sampling(temperature=0,top_p=1.,top_k=0,max_new_tokens=128),batch=batch)
            require(all(len(g)==1 for g in groups),'one actual greedy readout')
            return [[dict(raw=g[0],text=g[0],malformed=False)] for g in groups]
        import torch
        from mats.readers.nla import Sampling
        require(reader == 'oracle', 'E83 Oracle only')
        # One vector/job gives exactly eight stochastic samples, not eight greedy copies.
        with torch.inference_mode():
            groups = self.readers.oracle.verbalize(torch.as_tensor(np.array(vectors, copy=True)), 44, k=8,
                sampling=Sampling(temperature=1.0, top_p=0.95, top_k=0, max_new_tokens=128), batch=8)
        return [[dict(raw=s, text=s, malformed=False) for s in group] for group in groups]

    def synthetic(self, length=32):
        _, tok, _ = self.subject()
        token = tok.encode(' the', add_special_tokens=False)[0]
        return [[token] * length for _ in range(8)]

    def warm_capture(self):
        _, tok, _ = self.subject()
        xs = [dict(id='synthetic-'+str(i), text=tok.decode(ids), ids=ids, read_index=len(ids)-1)
              for i,ids in enumerate(self.synthetic())]
        self.capture(xs)  # discarded; no real item or output file

    def seed(self, seed):
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
