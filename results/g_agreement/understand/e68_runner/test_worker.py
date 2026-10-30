import sys,time
from pathlib import Path
from contextlib import nullcontext
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import worker
from worker import *
from smoke_profile import TinyBackend,TinyOracle,TinyModel

class TinyLate(TinyBackend):
 capture_at=LateBackend.capture_at
 def load_oracle(self):
  super().load_oracle();self.oracle.base=lambda:nullcontext();self.oracle.tok.encode=lambda text,**kw:[2] if text==' beta' else [1]
  self.oracle.model.get_input_embeddings=lambda:self.oracle.model.emb

def smoke(out,e):
 import torch,mats.capture
 out.mkdir();b=TinyLate();old=mats.capture.capture
 def tiny_capture(model,prompts,layers,positions,**kw):
  assert all(p==[len(t)-1] for t,p in zip(prompts,positions));model(torch.tensor(prompts))
  return {l:torch.ones((len(prompts),1,5120))*l for l in layers}
 mats.capture.capture=tiny_capture
 try:
  items=[dict(id=f'{e}:{i}',base_item_id=str(i),feature='unit_system' if e in ('E70','E72') else 'container_after_move',split='test',text='stub',ids=[1],read_index=0) for i in range(9)]
  if e=='E68':
   items=[dict(x,id=x['id']+':'+p,position=p) for x in items for p in POSITIONS];items+=[dict(items[0],id='dev',split='dev')]
  if e=='E69':items=[dict(x,arm=a,alpha_token_id=1,beta_token_id=2,id=x['id']+a) for x in items for a in ('own','swap')]
  if e=='E70':
   items=[dict(x,vector_index=i,dose=1,sign=1,carrier_id=str(i),direction_id='d') for i,x in enumerate(items)];np.save(out/'vectors.npy',np.full((len(items),5120),3,np.float32))
  inputs=out;budget=Budget(out,{e:100000},time.time()+100000,dict(oracle_setup=.01,oracle_native_8_items=.01,nla_setup=.01,nla_native_8_items=.01));acquire(dict(experiment=e),items,b,budget,out,inputs,dict(experiment=e))
  records=read(out/'RECORDS.json');n=sum(x['split']=='test' for x in items)
  assert len(records)==n*(1 if e=='E69' else 2)
  assert (out/'capture/CAPTURE_SEAL.json').exists()
  if e=='E69':assert b.loads==['oracle'] and all('score' in x for x in records)
  elif e=='E72':assert b.loads==['oracle'] and {x['source_layer'] for x in records}=={36,40} and all(x['reader_native_layer']==44 for x in records)
  else:assert b.loads==['oracle','nla']
  if e=='E70':assert np.array_equal(np.load(out/'capture/acts44.npy'),np.load(out/'vectors.npy'))
 finally:mats.capture.capture=old

def test_every_stage(tmp_path):
 for e in CAPS:smoke(tmp_path/e,e)

def test_reject_private_and_invalid_grid():
 x=dict(id='x',base_item_id='x',feature='container_after_move',split='test',text='stub',ids=[1],read_index=0,position='registered')
 validate_items('E68',[x])
 with pytest.raises(ValueError):validate_items('E68',[dict(x,label=1)])
 with pytest.raises(ValueError):validate_items('E68',[dict(x,read_index=1)])
 with pytest.raises(ValueError):validate_items('E68',[x],full=True)

def test_no_fit_retains_pilots(tmp_path):
 class Small(Budget):
  def forecast(self,*args):raise NoFit('synthetic cap')
 b=TinyLate();b.load_oracle();(tmp_path/'jobs').mkdir();items=[dict(id=str(i),feature='row',split='test') for i in range(24)];jobs=jobs_for('E68',items,{l:np.zeros((24,5120),np.float32) for l in (42,44)});budget=Small(tmp_path,{'E68':1000},time.time()+1000,{})
 with pytest.raises(NoFit):run_jobs(jobs,b,budget,tmp_path)
 assert len(list((tmp_path/'jobs').glob('*.json')))==2 and b.loads==['oracle']

def test_behaviour_rules_swap_is_control():
 from analyze69 import rules
 xs=[];labels={}
 for row in range(13):
  for arm in ('own','swap'):
   for i in range(84):
    y=i%2;k=f'{row}:{arm}:{i}';labels[k]=y;xs.append(dict(id=k,feature=str(row),base_item_id=str(i),arm=arm,score=y if arm=='own' else 1-y))
 r=rules(xs,labels);assert r['R_B1']=='MET' and not r['falsifier'] and r['rows_required']==10
 assert all(x['swapped_AUROC_against_A']==0 and x['swapped_AUROC_against_B']==1 for x in r['rows'].values())

def test_ratified_three_row_test_grid():
 items=[]
 for row in sorted(ROWS68):
  for split in ('dev','test'):
   for i in range(84):
    for j,p in enumerate(POSITIONS):
     items.append(dict(id=f'{row}:{split}:{i}:{p}',base_item_id=f'{row}:{split}:{i}',feature=row,split=split,text='synthetic',ids=[1,2,3],read_index=j,position=p))
 validate_items('E68',items,full=True)
 assert len(items)==1512 and sum(x['feature']=='topic_twin' for x in items)==504
 with pytest.raises(ValueError):validate_items('E68',items[:-1],full=True)
 with pytest.raises(ValueError):validate_items('E68',[dict(items[0],feature='arith_compare')])

def test_measured_self_admission_and_overrun(tmp_path,monkeypatch):
 import budget68
 monkeypatch.setattr(budget68.time,'time',lambda:900.)
 jobs=[dict(number=i,phase='oracle_native' if i<95 else 'nla_native') for i in range(190)]
 seed=dict(oracle_native_8_items=13.205892875092104,nla_native_8_items=19.425992050906643,nla_setup=666.3990328619257)
 b=Budget(tmp_path,{'E68':5664},5664.,seed);b.observed={'oracle_native':[13.205892875092104]}
 r=b.forecast(jobs,{0:[],1:[]});assert r['status']=='ADMIT' and r['future_nla_setup_included'] and r['margin']==1.25
 b.observed['nla_native']=[90.]
 with pytest.raises(NoFit):b.forecast(jobs,{0:[],1:[]})

def test_probe_requires_dev_and_separate_units():
 from probe import validate_cpu_grid
 xs=[dict(id=f'{s}:{i}',feature='row|registered',split=s,label=i%2) for s in ('dev','test') for i in range(84)]
 validate_cpu_grid(xs)
 with pytest.raises(ValueError):validate_cpu_grid([x for x in xs if x['split']=='test'])
 with pytest.raises(ValueError):validate_cpu_grid(xs+[xs[0]])

def test_probe_fit_ignores_test_labels():
 from cpu_capture import compute
 xs=[dict(id=f'{s}:{i}',feature='cell',split=s,label=i%2) for s in ('dev','test') for i in range(84)]
 h=np.asarray([[2*x['label']-1,1.] for x in xs],dtype=np.float32)
 first,_=compute(xs,h)
 changed=[dict(x,label=1-x['label']) if x['split']=='test' else dict(x) for x in xs]
 second,_=compute(changed,h)
 assert first==second and len(first)==84
