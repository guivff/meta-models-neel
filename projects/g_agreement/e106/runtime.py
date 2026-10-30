"""Pinned E106 native readers, fixed prompt prefix, and differentiable NLA injection."""
import copy,json
from pathlib import Path
from projects.g_agreement.e96.reconstructor_check import digest

NLA_REV='5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f'
NLA_ADAPTER='b54e23e4e36dbd04023b307e3abfd4618b5db2b31b8e7c650a957ebb1c90c358'


def verify_assets(a,reader,check):
    manifest=json.loads(Path(a[reader+'_manifest']).read_text())
    key='model' if reader=='oracle' else 'nla'
    root=Path(a[key]);source=Path(manifest[key])
    revision='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9' if reader=='oracle' else NLA_REV
    if manifest['revisions'][key]!=revision:raise ValueError('revision')
    count=0
    for f in manifest['files']:
        p=Path(f['path'])
        if not p.is_relative_to(source):continue
        rel=p.relative_to(source)
        if reader=='nla' and not (rel.parts[0] in ['av_base','nla_meta.yaml'] or str(rel).startswith('av_rl_adapters/iter_000400/')):continue
        check()
        if digest(root/rel)!=f['sha256']:raise ValueError('asset bytes: '+str(rel))
        count+=1
    if count==0:raise ValueError('empty assets')
    adapter=Path(a['olens']) if reader=='oracle' else root/'av_rl_adapters/iter_000400'
    expected='7d4b301e002246af3c3f2bb6e768f8fa62f8aac2c231a0bd02a8d4f9ecafd9aa' if reader=='oracle' else NLA_ADAPTER
    if digest(adapter/'adapter_model.safetensors')!=expected:raise ValueError('adapter bytes')


def load(a,reader):
    if reader=='oracle':
        import torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        from mats.readers.olens import load_olens
        model=AutoModelForCausalLM.from_pretrained(a['model'],dtype=torch.bfloat16,device_map='cuda',local_files_only=True).eval()
        tok=AutoTokenizer.from_pretrained(a['model'],local_files_only=True)
        return load_olens(model,tok,lora_dir=a['olens'])
    from mats.readers.nla import load_nla
    return load_nla(root=a['nla'],load_ar=False,enable_thinking=False)


def prefix_nla(nla,prefix):
    from mats.readers.nla import _render_prompt
    meta=copy.deepcopy(nla.meta)
    meta['prompt_templates']['actor']=prefix+meta['prompt_templates']['actor']
    ids,marker=_render_prompt(nla.tok,meta,False)
    nla.meta=meta;nla.prompt_ids=ids;nla.marker=marker


def generate(reader,lens,h,prefix=''):
    import numpy as np
    import torch
    if reader=='oracle':
        from mats.readers.nla import Sampling
        if prefix:
            lens.prompt=prefix+lens.prompt;lens._slots.clear()
        raw=lens.verbalize(torch.as_tensor(np.array(h,copy=True)),44,k=1,sampling=Sampling(temperature=0,top_p=1.,top_k=0,max_new_tokens=128),batch=len(h))
        return [{'raw':x[0],'text':x[0],'malformed':False,'truncated':None} for x in raw]
    if prefix:prefix_nla(lens,prefix)
    from transformers import StoppingCriteria,StoppingCriteriaList
    from mats.readers.nla import extract_explanation
    class Closed(StoppingCriteria):
        def __call__(self,ids,scores,**kw):
            texts=lens.tok.batch_decode(ids[:,len(lens.prompt_ids):],skip_special_tokens=True)
            return torch.tensor(['</explanation>' in x for x in texts],device=ids.device,dtype=torch.bool)
    v=torch.as_tensor(np.array(h,copy=True),device=lens.device).float()
    ids=torch.tensor([lens.prompt_ids]*len(v),device=lens.device)
    with torch.no_grad(),lens._inject(v):
        out=lens.av.generate(input_ids=ids,attention_mask=torch.ones_like(ids),do_sample=False,max_new_tokens=512,pad_token_id=lens.tok.pad_token_id,stopping_criteria=StoppingCriteriaList([Closed()]))
    raw=lens.tok.batch_decode(out[:,len(lens.prompt_ids):],skip_special_tokens=True)
    return [{'raw':x,'text':extract_explanation(x) or x,'malformed':extract_explanation(x) is None,'truncated':'</explanation>' not in x} for x in raw]


def differentiable_hook(nla):
    """Replace the native in-place hook; preserve its arithmetic and native marker."""
    import torch
    def hook(_mod,_inp,out):
        h=out[0] if isinstance(out,tuple) else out;v=nla._vec.get('v')
        if v is None or h.shape[1]<=nla.marker:return out
        if v.shape[0]!=h.shape[0]:raise ValueError('injection batch')
        hp=h[:,nla.marker,:]
        vu=v.to(h.device,torch.float32);vu=(vu/(vu.norm(dim=-1,keepdim=True)+1e-9)).to(h.dtype)
        updated=h.clone();updated[:,nla.marker,:]=hp+hp.norm(dim=-1,keepdim=True)*vu
        return (updated,)+out[1:] if isinstance(out,tuple) else updated
    found=0
    for mod in nla.av.modules():
        for key,fn in list(mod._forward_hooks.items()):
            if getattr(fn,'__self__',None) is nla and getattr(fn,'__name__','')=='_hook':
                del mod._forward_hooks[key];mod.register_forward_hook(hook);found+=1
    if found!=1:raise ValueError('exactly one original NLA hook required')


def attach_rank16(nla):
    from peft import LoraConfig
    name='e106_repair'
    old=nla.av.active_adapter
    if isinstance(old,list):
        if len(old)!=1:raise ValueError('one pinned starting adapter')
        old=old[0]
    cfg=nla.av.peft_config[old]
    if cfg.r!=64:raise ValueError('original pinned adapter rank64')
    nla.av.add_adapter(name,LoraConfig(r=16,lora_alpha=16,lora_dropout=0.,bias='none',target_modules=sorted(cfg.target_modules),init_lora_weights=True))
    # LoraModel supports an additive active-adapter list; preserve original factors,
    # avoid merging/rounding the pinned rank64 update into bf16 base weights.
    nla.av.base_model.set_adapter([old,name])
    active=[]
    for n,p in nla.av.named_parameters():
        train=('.lora_A.'+name+'.' in n or '.lora_B.'+name+'.' in n)
        p.requires_grad_(train)
        if train:active.append((n,p))
    if not active:raise ValueError('new rank16 parameters absent')
    if any(p.detach().count_nonzero().item() for n,p in active if '.lora_B.' in n):
        raise ValueError('new adapter is not initially a zero update')
    differentiable_hook(nla)
    return dict(active)
