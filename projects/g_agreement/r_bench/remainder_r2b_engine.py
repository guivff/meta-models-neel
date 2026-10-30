"""Offline native collection engine for R2-B. Always guarded; no allocation/API.

Cells contain frozen item text, source row/path and carrier protocol. An engine
is scoped to one reader so the 27B target and NLA are not loaded concurrently.
"""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import numpy as np
from projects.g_agreement.r_bench import remainder_r2b as D,remainder_r2b_live as L


def validate_oracle_assets(assets):
    import json
    from projects.g_agreement.core import config as C
    expected={'target_revision':C.TARGET_MODEL_SHA,'oracle_revision':C.OLENS_SHA}
    for key,value in expected.items():
        if assets.get(key)!=value:raise ValueError(f'Unpinned {key}: {assets.get(key)}')
    config=json.loads((Path(assets['target'])/'config.json').read_text())
    config=config.get('text_config',config)
    if config.get('num_hidden_layers')!=assets.get('decoder_depth'):
        raise ValueError(f'Frozen decoder depth mismatch: {assets.get("decoder_depth")}')
    if config.get('hidden_size')!=5120:raise ValueError(f'Wrong source/Oracle width: {config.get("hidden_size")}')
    # HF snapshot paths bind cached assets to the published frozen revisions.
    for key,revision in [('target',C.TARGET_MODEL_SHA),('oracle_adapter',C.OLENS_SHA)]:
        if revision not in Path(assets[key]).parts:raise ValueError(f'Unbound snapshot path: {assets[key]}')


@contextmanager
def oracle_system(reader,layer,fact):
    from projects.g_agreement.core import model as M
    old=reader.carrier(layer);_,_,char,char_id=old
    ids=M.chat_ids(reader.target.tokenizer,[{'role':'system','content':fact},
        {'role':'user','content':reader.prompt.format(layer=layer,char=char)}])
    slots=[i for i,x in enumerate(ids) if x==char_id]
    if len(slots)!=1:raise ValueError('Positive-system marker collision')
    reader._carriers[layer]=(ids,slots[0],char,char_id)
    try:yield
    finally:reader._carriers[layer]=old


class Engine:
    def __init__(self,reader,assets,guard):
        self.kind=reader;self.assets=assets;self.guard=guard;self.reader=None;self.target=None
        self.matrix_cache={}
    def load(self):
        import os
        # No implicit downloads in a paid segment. All paths must be staged/pinned.
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
        self.guard()
        from projects.g_agreement.core import model as M,readers as Readers
        if self.kind=='olens':validate_oracle_assets(self.assets)
        required=('nla_base','nla_adapter') if self.kind=='nla' else ('target','oracle_adapter')
        for key in required:
            if not Path(self.assets[key]).is_dir():raise ValueError(f'Missing pinned asset: {key}')
        if self.kind=='nla':
            self.reader=Readers.NLAReader().bind(base_dir=self.assets['nla_base'],adapter_dir=self.assets['nla_adapter'])
        else:
            self.target=M.load_target(model_id=self.assets['target'],revision=None)
            if self.kind=='olens':self.reader=Readers.OLensReader(sampling={'do_sample':False}).bind(self.target,adapter_dir=self.assets['oracle_adapter'])
            # Oracle consumes captured source states; taught adapters belong only
            # to source-model forwards, never to the Oracle model instance.
            if self.kind=='source':
                from peft import PeftModel
                for recipe in ('sft','sft_dpo'):
                    path=self.assets['taught_'+recipe]
                    if not Path(path).is_dir():raise ValueError(f'Missing taught adapter: {recipe}')
                    if isinstance(self.target.model,PeftModel):self.target.model.load_adapter(path,adapter_name='planted_'+recipe)
                    else:self.target.model=PeftModel.from_pretrained(self.target.model,path,adapter_name='planted_'+recipe)
        self.guard()
        if self.kind=='olens' and len(M.blocks(self.target.model))!=self.assets['decoder_depth']:
            raise ValueError(f'Oracle depth differs from frozen manifest: {len(M.blocks(self.target.model))}')
    def close(self):
        from projects.g_agreement.core import model as M
        obj=self.reader if self.kind=='nla' else self.target
        if obj is not None:M.unload(obj)
        self.reader=None;self.target=None;self.matrix_cache.clear()
    def state(self,cell,layer):
        import torch
        p=cell['state_paths'][str(layer)]
        if p not in self.matrix_cache:self.matrix_cache[p]=np.load(p,mmap_mode='r',allow_pickle=False)
        x=np.asarray(self.matrix_cache[p][cell['state_row']],dtype=np.float32).copy()
        if x.shape!=(5120,) or not np.isfinite(x).all():raise ValueError(f'Invalid state: {cell["item_id"]}')
        return torch.from_numpy(x)
    def execute(self,cell):
        self.guard()
        if cell['reader']!=self.kind:raise ValueError(f'Reader phase mismatch: {cell["reader"]}')
        if self.reader is None and self.target is None:self.load()
        if self.kind=='source':return self.source(cell)
        if self.kind=='olens':return self.oracle(cell)
        if self.kind=='nla':return self.nla(cell)
        raise ValueError(f'Unknown reader: {self.kind}')
    def source(self,cell):
        import torch
        from projects.g_agreement.core import model as M
        from projects.g_agreement.r_bench.planted_facts.collect import adapter_ctx_for
        layers=cell['tap_blocks'];arm=cell['arm'];store={}
        if arm in ('natural','shuffled','sham','mean_ablation','random_ablation','wrong_candidates'):
            return {'source':'cached'}, {l:self.state(cell,l).numpy().astype(np.float16) for l in layers}
        text=cell['input_text'];system=cell.get('system')
        if arm=='positive_system':system=cell['positive_fact']
        ids=M.render_item(self.target.tokenizer,text,system);handles=[]
        for layer in layers:
            def hook(_m,_i,out,layer=layer):
                h=out[0] if isinstance(out,tuple) else out
                store[layer]=h[0,-1,:].detach().to(torch.float16).cpu().numpy()
            handles.append(M.blocks(self.target.model)[layer].register_forward_hook(hook))
        try:
            with adapter_ctx_for(self.target.model,cell['recipe']),torch.no_grad():
                self.guard();self.target.model(input_ids=torch.tensor([ids],device=self.target.device),use_cache=False,logits_to_keep=1)
        finally:
            for h in handles:h.remove()
        if set(store)!=set(layers):raise ValueError(f'Source tap coverage: {cell["item_id"]}')
        return {'head_sha256':D.digest(ids),'source':'text_forward'},store
    def oracle(self,cell):
        from contextlib import nullcontext
        item=cell['item'];layer=44;arm=cell['arm'];h=self.state(cell,layer)
        self.target.model.set_adapter('default')  # Oracle adapter, never the taught adapter
        head=None
        if arm in ('rebuilt','text_only'):
            head=L.text_head(self.reader,layer,cell['input_text'])
        if arm=='prompt_only':
            raise ValueError('Prompt-only belongs to target phase, not Oracle carrier')
        pairs=[tuple(cell.get('candidates',item['primary']['candidates']))]
        ablation=cell.get('ablation')
        context=oracle_system(self.reader,layer,cell['positive_fact']) if arm=='positive_system' else nullcontext()
        with context:
            scores,taps=L.oracle_score(self.reader,h.unsqueeze(0),pairs,layer,self.guard,head_override=head,ablation=ablation)
            # Reverse candidate order on the same head; average orientation-correct LOs.
            reversed_scores,_=L.oracle_score(self.reader,h.unsqueeze(0),[(pairs[0][1],pairs[0][0])],layer,self.guard,head_override=head,ablation=ablation)
            payload=scores[0];payload['lo']=(payload['lo']-reversed_scores[0]['lo'])/2
            if cell.get('generate'):
                payload['generation']=L.oracle_free(self.reader,h,layer,self.guard,head_override=head,ablation=ablation)
        return payload,{k:x[0] for k,x in taps.items()}
    def nla(self,cell):
        from projects.g_agreement.core import model as M,scoring_lo as LO
        import torch
        h=self.state(cell,42);pairs=[tuple(cell.get('candidates',cell['item']['primary']['candidates']))]
        family=cell['nla_family']
        if cell['arm'] in ('natural','shuffled','sham','wrong_candidates'):
            rows,taps=L.nla_score(self.reader,h.unsqueeze(0),pairs,family,self.guard)
        elif cell['arm'] in ('text_only','rebuilt'):
            ids=list(self.reader.ids);slot=self.reader.marker
            text_tokens=LO.encode(self.reader.tokenizer,cell['input_text'])
            if not text_tokens:raise ValueError('Empty NLA text control')
            base=ids[:slot]+text_tokens+ids[slot+1:]
            head=base+LO.encode(self.reader.tokenizer,LO.NLA_PREFIX)
            templates=LO.templates_for(family)
            if len(templates)!=1:raise ValueError(f'Unfrozen NLA template: {family}')
            tokens=[head+LO.encode(self.reader.tokenizer,templates[0].format(X=x)) for x in pairs[0]]
            self.reader._vec['v']=None
            pad=self.reader.tokenizer.pad_token_id
            if pad is None:pad=self.reader.tokenizer.eos_token_id
            with L.PrefillTaps(M.blocks(self.reader.model),len(base)-1) as tap:
                self.guard();lp=LO._summed_logprobs(self.reader.model,tokens,len(head),pad,next(self.reader.model.parameters()).device)
            rows=[dict(lp_A=lp[0],lp_B=lp[1],lo=lp[0]-lp[1],head_sha256=D.digest(base))]
            taps=tap.arrays(candidate_pairs=True)
        else:raise ValueError(f'Unsupported NLA arm: {cell["arm"]}')
        return rows[0],{k:x[0] for k,x in taps.items()}


def execute_manifest(manifest,reader,writer,engine,guard):
    """Same orchestration for real engine and isolated synthetic decoy tests."""
    expected=[c for c in manifest['cells'] if c['reader']==reader]
    if not expected:raise ValueError(f'Empty requested phase: {reader}')
    if set(writer.expected)!={D.digest(c) for c in expected}:raise ValueError(f'Writer phase inventory differs: {reader}')
    try:
        for cell in expected:
            guard();payload,arrays=engine.execute(cell)
            writer.append(cell,payload,arrays)
        return writer.finish()
    finally:engine.close()
