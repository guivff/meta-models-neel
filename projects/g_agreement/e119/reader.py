"""Our implementation of lens B; remote safetensors/README are inert data only."""
import json,re
from pathlib import Path
import numpy as np
CONTRACT_PATH=Path(__file__).with_name('contract.json')

def contract():return json.loads(CONTRACT_PATH.read_text())

def embed(model,ids,slot,vectors):
    import torch
    h=torch.as_tensor(vectors,device=ids.device).float()
    if h.ndim!=2 or len(h)!=len(ids) or not bool(torch.isfinite(h).all()) or bool((h.norm(dim=-1)==0).any()):raise ValueError('finite nonzero native residuals')
    e=model.get_input_embeddings()(ids).clone()
    if not 0<=slot<ids.shape[1] or h.shape[1]!=e.shape[-1]:raise ValueError('single slot/dimension')
    e[:,slot]=(contract()['read']['alpha']*h/h.norm(dim=-1,keepdim=True)).to(e.dtype)
    return e

def carrier(tok,layer):
    if type(layer)is not int or not 0<=layer<64:raise ValueError('zero-based source layer0..63')
    cfg=contract()['read']
    for cp in range(0x3200,0x3400):
        char=chr(cp);single=tok(char,add_special_tokens=False)['input_ids']
        if len(single)!=1:continue
        rendered=tok.apply_chat_template([dict(role='user',content=cfg['prompt'].format(layer=layer,char=char))],tokenize=True,add_generation_prompt=True,enable_thinking=False)
        ids=list(rendered['input_ids'] if hasattr(rendered,'keys') else rendered)
        slots=[i for i,k in enumerate(ids) if k==single[0]]
        if len(slots)==1:return ids,slots[0]
    raise ValueError('no unique single-token slot in full chat carrier')

def lora_state(state):
    """Exact name mapping, no guessing/partial tensor match."""
    expected_buffers={'injector._layer_norms','injector._scale'}
    if {k for k in state if 'lora_' not in k}!=expected_buffers:raise ValueError('unexpected non-LoRA checkpoint tensors')
    weights={k.removeprefix('lm.'):v for k,v in state.items() if 'lora_' in k}
    if not weights or any(not k.startswith('lm.base_model.model.') for k in state if 'lora_' in k):raise ValueError('exact exported lm prefix')
    if tuple(state['injector._layer_norms'].shape)!=(64,) or tuple(state['injector._scale'].shape)!=():raise ValueError('documented injector buffers')
    if not bool((state['injector._layer_norms']==1000).all()) or float(state['injector._scale'])!=1.:raise ValueError('unit alpha1000 injector buffer contract')
    return weights

def load(base,weights):
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import LoraConfig,get_peft_model
    from projects.g_agreement.e100.contract import sha
    c=contract()
    if sha(weights)!=c['checkpoint']['weights_sha256']:raise ValueError('immutable weight content')
    if Path(base).name!=c['base']['revision']:raise ValueError('exact README base snapshot revision')
    state=load_file(str(weights),device='cpu');mapped=lora_state(state)
    modules=sorted({k.rsplit('.lora_',1)[0].split('.')[-1] for k in mapped})
    if modules!=c['lora']['target_modules']:raise ValueError('frozen exact linear module set')
    model=AutoModelForCausalLM.from_pretrained(base,local_files_only=True,trust_remote_code=False,dtype=torch.bfloat16,device_map='cuda').eval()
    tok=AutoTokenizer.from_pretrained(base,local_files_only=True,trust_remote_code=False)
    model=get_peft_model(model,LoraConfig(r=16,lora_alpha=32,lora_dropout=0.,target_modules=modules,bias='none',task_type='CAUSAL_LM'))
    actual={n for n,_ in model.named_parameters() if 'lora_' in n}
    if actual!=set(mapped):raise ValueError('every exported LoRA tensor must map exactly; no inert adapter')
    parameters=dict(model.named_parameters())
    with torch.no_grad():
        for name,v in mapped.items():
            if parameters[name].shape!=v.shape or not bool(torch.isfinite(v).all()):raise ValueError('finite exact LoRA tensor shape')
            parameters[name].copy_(v.to(parameters[name].device,parameters[name].dtype))
    model.eval()
    return model,tok,dict(lora_tensors=len(mapped),injector_buffers={k:state[k].tolist() for k in ('injector._scale','injector._layer_norms')},buffer_policy='unit transform alpha1000 fixed by README; no scaled/per-layer norm transform')

def read(model,tok,vectors,layer):
    import torch
    ids0,slot=carrier(tok,layer);ids=torch.tensor([ids0]*len(vectors),device=model.get_input_embeddings().weight.device)
    with torch.inference_mode():
        e=embed(model,ids,slot,np.array(vectors,copy=True));tokens=model.generate(inputs_embeds=e,attention_mask=torch.ones_like(ids),do_sample=False,max_new_tokens=128,pad_token_id=tok.pad_token_id or tok.eos_token_id)
    return [dict(raw=t.strip(),text=t.strip(),token_ids=ids,source_layer=layer) for t,ids in zip(tok.batch_decode(tokens,skip_special_tokens=True),tokens.detach().cpu().tolist())]

def nondegenerate(value):
    words={w.casefold() for w in re.findall(r'[^\W\d_]+',value['text'],flags=re.UNICODE)}
    ids=value['token_ids'];run=best=0;last=None
    for token in ids:
        run=run+1 if token==last else 1;best=max(best,run);last=token
    return len(words)>=2 and bool(ids) and best<=contract()['smoke']['max_identical_token_run']
