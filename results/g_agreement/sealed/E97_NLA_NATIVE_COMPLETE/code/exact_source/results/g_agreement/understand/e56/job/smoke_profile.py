"""Execute every profile stage on tiny CPU models; never load production weights."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import time
import numpy as np
import torch
from worker56 import Backend
from profile_single import run_stages,ProfileBudget
from contract56 import dump,require
import parity_gate

class Tok:
 pad_token_id=0
 def encode(self,text,**kw):return [1 if text!=' b' else 2]
 def batch_decode(self,ids,**kw):return ['<explanation>stub</explanation>' for _ in ids]

class TinyModel(torch.nn.Module):
 def __init__(self):
  super().__init__();self.emb=torch.nn.Embedding(16,4);self.head=torch.nn.Linear(4,16);self.calls=0
 def forward(self,input_ids,logits_to_keep=None,**kw):
  self.calls+=1;z=self.head(self.emb(input_ids));return SimpleNamespace(logits=z[:,-logits_to_keep:] if logits_to_keep else z)
 def generate(self,input_ids,**kw):
  require(kw['do_sample'] is False and kw['max_new_tokens']==512,'native NLA generation contract')
  self(input_ids);out=torch.cat([input_ids,torch.ones((len(input_ids),1),dtype=torch.long)],1)
  require(bool(kw['stopping_criteria'](out,None).all()),'NLA closing stop executes');return out

class TinyOracle:
 def __init__(self):self.model=TinyModel();self.tok=Tok();self.score_calls=0;self.native_calls=0
 def paired_logodds_templates(self,acts,layer,pairs,prefix=''):
  # Exercise the real Oracle boundary operation that failed for ndarray.
  expanded=acts.repeat_interleave(2,dim=0);require(isinstance(expanded,torch.Tensor),'tensor scoring input')
  self.model(torch.ones((len(expanded),2),dtype=torch.long));self.score_calls+=1
  return acts[:,0].float().repeat(len(pairs),1)
 def verbalize(self,acts,layer,k,sampling,batch):
  require(isinstance(acts,torch.Tensor) and k==1 and sampling.max_new_tokens==128,'Oracle native contract')
  self.model(torch.ones((len(acts),2),dtype=torch.long));self.native_calls+=1;return [['stub'] for _ in acts]

class TinyNLA:
 def __init__(self):self.av=TinyModel();self.tok=Tok();self.device='cpu';self.prompt_ids=[1];self.injections=0
 @contextmanager
 def _inject(self,v):
  require(isinstance(v,torch.Tensor) and v.ndim==2,'native tensor injection');self.injections+=1;yield

class TinyBackend(Backend):
 def __init__(self):self.loads=[];self.oracle=None;self.nla=None;self.old_oracle=None
 def load_oracle(self):self.loads.append('oracle');self.oracle=TinyOracle();self.old_oracle=self.oracle
 def load_nla(self):self.loads.append('nla');self.nla=TinyNLA()
 def validate_tokenization(self,items):
  for x in items:require(self.oracle.tok.encode(x['text'])==x['ids'],'stub tokenization')
 def capture(self,items):
  self.oracle.model(torch.tensor([x['ids'] for x in items]));return {l:np.ones((len(items),5120),dtype=np.float32) for l in (42,44)}

def smoke(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
 units=[dict(id=f'dev:{i}',feature='stub',split='dev',text='stub',ids=[1]) for i in range(8)]
 items=[dict(id=f'{r}:{i}',feature=r) for r in parity_gate.ROWS for i in range(84)]
 labels={x['id']:i%2 for i,x in enumerate(items)};acts=np.zeros((252,5120),np.float32);acts[:,0]=list(labels.values())
 inputs=(items,labels,{r:{'olens':[[' a',' b'],[' a',' b']]} for r in parity_gate.ROWS},acts,{'reference_auc':dict.fromkeys(parity_gate.ROWS,1.)})
 proofs={}
 for mode in ('all','nla_only_synthetic'):
  dst=out/mode;dst.mkdir();backend=TinyBackend();budget=ProfileBudget(time.time()+1800,dst/'PHASE_TIMINGS.jsonl')
  records,_=run_stages(backend,budget,units,[[' a',' b']],inputs,dst,mode)
  expected={'nla_setup','nla_native','nla_continuation'}
  if mode=='all':expected|={'oracle_setup','parity','capture','oracle_native','oracle_continuation'}
  require(set(budget.observed)==expected,'every phase executes');require(len(records)==(16 if mode=='all' else 8),'single readout grid')
  require(backend.loads==(['oracle','nla'] if mode=='all' else ['nla']),'NLA only never loads Oracle')
  require(backend.nla.av.calls>1 and backend.nla.injections>1,'real NLA native and continuation internals executed')
  proofs[mode]={'phases':sorted(budget.observed),'loads':backend.loads,'readouts':len(records),'status':'PASS'}
 dump(out/'SMOKE_RESULT.json',{'status':'PASS','modes':proofs,'production_model_calls':0});return proofs
