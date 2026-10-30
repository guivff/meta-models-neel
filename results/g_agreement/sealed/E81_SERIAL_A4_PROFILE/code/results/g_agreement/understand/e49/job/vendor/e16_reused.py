"""Frozen E12/E16 prompt definitions, extracted verbatim on 2026-10-25.

Authority and source hashes: UPSTREAM_SOURCE.json. This module imports no model
or tokenizer library at import time. E33 reuses W1's token-SUM paired log odds.
"""
ARMS=('activation_only','text_activation','text_only','text_wrong_activation')

CONTEXT_PREFIX=(
    'The following is the source text up to and including the read position.\n'
    '<source_text>\n{text}\n</source_text>\n\n'
)

def user_message(native_request,text,arm):
    if arm not in ARMS:raise ValueError('unknown E12 arm')
    return native_request if arm=='activation_only' else CONTEXT_PREFIX.format(text=text)+native_request

def carrier(tok,native_request,text,arm,marker_token_id):
    content=user_message(native_request,text,arm)
    output=tok.apply_chat_template([{'role':'user','content':content}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
    ids=list(output['input_ids'] if hasattr(output,'keys') else output)
    slots=[i for i,t in enumerate(ids) if t==marker_token_id]
    if len(slots)!=1:raise ValueError('injection marker must occur once;do not repair or drop context')
    return ids,slots[0]

def activation_for(arm,recipient,wrong):
    if arm not in ARMS:raise ValueError('unknown E12 arm')
    if arm=='text_only':return None  # Keep placeholder's own embedding. Zero-vector injection is not equivalent.
    return wrong if arm=='text_wrong_activation' else recipient

def base_head(tok,text):
    # E12's exact source wrapper, no native-reader instruction, placeholder or injection.
    ids=tok.apply_chat_template([{'role':'user','content':CONTEXT_PREFIX.format(text=text)}],
        tokenize=True,add_generation_prompt=True,enable_thinking=False)
    return list(ids['input_ids'] if hasattr(ids,'keys') else ids)

E16_BASE_SCORES_SOURCE = 'def base_scores(reader,records,pairs):\n    """Both candidates share a forward; E12 right-pad/equal-head machinery, no slot/injection."""\n    import torch\n    tok=reader.tok;model=reader.model;heads=[base_head(tok,r[\'text\']) for r in records]\n    if len({len(x) for x in heads})!=1:raise ValueError(\'base context batches require equal head lengths\')\n    headlen=len(heads[0]);answers=[]\n    with reader.base(),torch.inference_mode():\n        for pair in pairs:\n            cands=[tok.encode(c,add_special_tokens=False) for c in pair]\n            if any(not c for c in cands):raise ValueError(\'empty candidate\')\n            length=headlen+max(map(len,cands));ids=torch.full((2*len(records),length),tok.pad_token_id or 0,device=reader.device,dtype=torch.long);mask=torch.zeros_like(ids)\n            for i,head in enumerate(heads):\n                for j,cand in enumerate(cands):\n                    s=head+cand;ids[2*i+j,:len(s)]=torch.tensor(s,device=reader.device);mask[2*i+j,:len(s)]=1\n            logits=model(input_ids=ids,attention_mask=mask,logits_to_keep=length-headlen+1,use_cache=False).logits\n            lp=torch.log_softmax(logits[:,:-1].float(),dim=-1);v=lp.gather(-1,ids[:,headlen:].unsqueeze(-1)).squeeze(-1)\n            answers.append([float(v[2*i,:len(cands[0])].sum()-v[2*i+1,:len(cands[1])].sum()) for i in range(len(records))])\n    return np.asarray(answers,float).T'

def reference_base_scores(reader, records, pairs):
    """Call E16's exact scorer; only the injected namespace resolves dependencies."""
    import numpy as np
    namespace = {"np": np, "base_head": base_head}
    exec(compile(E16_BASE_SCORES_SOURCE, "upstream:e16_worker.base_scores", "exec"), namespace)
    return namespace["base_scores"](reader, records, pairs)
