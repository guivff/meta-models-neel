"""§172 clarification3,259db20a: NLA-only length/stop change; unchanged native adapter/prompt."""
import numpy as np
CLOSE='</explanation>'


def native_nla(nla,h,k,batch=8):
    import torch
    from transformers import StoppingCriteria,StoppingCriteriaList
    from mats.readers.nla import extract_explanation
    class ClosedExplanation(StoppingCriteria):
        def __init__(self,prompt_length):self.prompt_length=prompt_length
        def __call__(self,input_ids,scores,**kwargs):
            # Decode generated suffix only. Supports arbitrary tokenizer splits of the closing tag.
            texts=nla.tok.batch_decode(input_ids[:,self.prompt_length:],skip_special_tokens=True)
            return torch.tensor([CLOSE in text for text in texts],device=input_ids.device,dtype=torch.bool)
    acts=torch.from_numpy(np.array(h,copy=True)).reshape(-1,h.shape[-1]).float()
    rows=acts.repeat_interleave(k,dim=0);records=[]
    with torch.no_grad():
        for start in range(0,len(rows),batch):
            v=rows[start:start+batch].to(nla.device)
            ids=torch.tensor([nla.prompt_ids]*len(v),device=nla.device)
            with nla._inject(v):
                output=nla.av.generate(input_ids=ids,attention_mask=torch.ones_like(ids),do_sample=False,max_new_tokens=512,pad_token_id=nla.tok.pad_token_id,stopping_criteria=StoppingCriteriaList([ClosedExplanation(len(nla.prompt_ids))]))
            for raw in nla.tok.batch_decode(output[:,len(nla.prompt_ids):],skip_special_tokens=True):
                payload=extract_explanation(raw)
                records.append({'raw':raw,'text':payload if payload is not None else raw,'malformed':payload is None,'truncated':CLOSE not in raw,'native_max_new_tokens':512,'native_stop':CLOSE})
    if len(records)!=len(h)*k:raise ValueError('native NLA output grid')
    return [records[i*k:(i+1)*k] for i in range(len(h))]


def truncation_summary(records,row_key='feature'):
    rows={}
    for x in records:
        row=x[row_key];d=rows.setdefault(row,{'outputs':0,'truncated':0})
        d['outputs']+=1;d['truncated']+=int(CLOSE not in x['raw'])
    for d in rows.values():
        d['rate']=d['truncated']/d['outputs'];d['flag_over_10_percent']=d['truncated']*10>d['outputs']
    return {'definition':'raw output lacks </explanation>','rows':rows}
