import sys,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
import pytest
from worker import *

def bank():
 xs=[]
 for arm,rows,cells in [('A',sorted(A_ROWS),['none']+[f'{d}:{a}' for d in ('J','perp','random') for a in (.25,.5,1,2,4)]),('B',sorted(B_ROWS),['none','J','perp','random'])]:
  for row in rows:
   for cell in cells:
    for i in range(84):
     x=dict(id=f'{arm}:{row}:{cell}:{i}',base_item_id=f'{row}:{i}',feature=row,arm=arm,cell=cell,vector_index=len(xs))
     if arm=='B':x.update(ids=[1,2,3],read_index=2)
     xs.append(x)
 return xs

def test_frozen_grids_and_no_labels():
 xs=bank();h=np.ones((4704,5120),np.float32);validate(xs,h)
 assert sum(len(j['indices']) for j in jobs(xs) if j['kind']=='continuation')==672
 with pytest.raises(ValueError):validate([dict(x,label=1) for x in xs],h)
 xs[0]['cell']='other'
 with pytest.raises(ValueError):validate(xs,h)

class Model(torch.nn.Module):
 def __init__(self):super().__init__();self.layers=torch.nn.ModuleList([torch.nn.Identity() for _ in range(45)]);self.emb=torch.nn.Embedding(10,5120);self.config=SimpleNamespace(num_hidden_layers=45);self.seen=[]
 def get_input_embeddings(self):return self.emb
 def forward(self,input_ids,**kw):
  assert kw['use_cache'] is False and kw['logits_to_keep']==1
  z=self.layers[44](self.emb(input_ids));self.seen.append(z.detach().clone());decode=self.layers[44](torch.zeros((len(input_ids),1,5120)));self.seen.append(decode)
  return SimpleNamespace(logits=torch.arange(100000,dtype=torch.float).reshape(1,1,100000).repeat(len(input_ids),1,1))
class Tok:
 pad_token_id=0
 def batch_decode(self,x,**kw):return ['continuation']*len(x)
 def encode(self,x,**kw):return [1]

def test_patch_prefill_only_and_cleanup():
 m=Model();xs=[dict(ids=[1,2,3],read_index=2,feature='format_plan')]*2;h=np.full((2,5120),7,np.float32);result=patched_logits(m,Tok(),xs,h)
 assert torch.all(m.seen[0][:,2]==7) and torch.all(m.seen[1]==0)
 assert torch.equal(m.seen[0][:,0],m.emb(torch.ones(2,dtype=torch.long)))
 assert not m.layers[44]._forward_hooks and len(result)==2 and len(result[0]['pair_logits'])==1
 class Bad(Model):
  def forward(self,**kw):raise RuntimeError('synthetic failure')
 m=Bad()
 with pytest.raises(RuntimeError):patched_logits(m,Tok(),xs,h)
 assert not m.layers[44]._forward_hooks

def test_every_stage_and_discard_warmups(tmp_path,monkeypatch):
 import worker
 xs=bank();h=np.full((4704,5120),2,np.float32);calls=[]
 class B:
  oracle=SimpleNamespace(tok=Tok())
  def load_oracle(self):pass
  def native_one(self,r,h):calls.append(('native',h.copy()));return [[dict(text='native')] for _ in h]
  def continuation(self,xs,h):calls.append(('continuation',h.copy()));return [dict(text='continuation',token_ids=[1]) for _ in xs]
 assert acquire(xs,h,B(),Clock(tmp_path,time.time()+100000),tmp_path)
 assert not np.array_equal(calls[0][1],h[:8]) and not np.array_equal(calls[1][1],h[:8])
 done=read(tmp_path/'COMPLETED.json');jj=read(tmp_path/'JOB_GRID.json');assert len(done)==len(jj)
 assert sum(len(read(tmp_path/'jobs'/f'{i:06d}.json')) for i,j in enumerate(jj) if j['kind']=='native')==4704
 assert sum(len(read(tmp_path/'jobs'/f'{i:06d}.json')) for i,j in enumerate(jj) if j['kind']=='continuation')==672
 assert len(read(tmp_path/'PHASE_TIMINGS.json'))==3+len(jj)

def test_mean_admission_excludes_warmups(tmp_path,monkeypatch):
 import worker
 monkeypatch.setattr(worker.time,'time',lambda:100.)
 c=Clock(tmp_path,220);c.cost={'native':[1,1,10],'continuation':[1]};jj=[dict(kind='native')]*10
 assert c.forecast(jj,set())
 assert read(tmp_path/'FORECAST.json')['mean_real_batch_seconds']['native']==4

class TinyBackend:
 oracle=SimpleNamespace(tok=Tok())
 def load_oracle(self):pass
 def native_one(self,r,h):return [[dict(text='synthetic native')] for _ in h]
 def continuation(self,xs,h):return [dict(text='synthetic continuation',token_ids=[1]) for _ in xs]
