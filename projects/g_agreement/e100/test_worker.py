import json,time
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from .contract import ROWS,cells,jobs,validate
from .interventions import transform,ratios,upstream
from .worker import original,acquire,validate_assignment

def fixture(shard):
 items=[]
 for row,n in ROWS[shard].items():
  offset=len(items)
  for i in range(n):items.append(dict(id=f'opaque-{offset+i}',row=row,slot=offset+i,row_slot=i,donor_slot=offset+(i+42)%n))
 rng=np.random.default_rng(7);h=rng.normal(size=(len(items),4));q=np.eye(4)[:,:2]
 return items,dict(H44=h,H42=h+3,BASIS_J=q,BASIS_R=np.eye(4)[:,2:])

@pytest.mark.parametrize('shard,total',[('reported',4200),('missed',2520)])
def test_exact_current_grid_labels_and_no_withdrawn_modes(shard,total):
 items,a=fixture(shard);validate(items,a,shard,4,2);jj=jobs(items,shard)
 assert sum(len(j['indices']) for j in jj)==total
 assert {j['condition'] for j in jj}=={'transplant','J_swap','perp_J_swap','R_swap','perp_R_swap'}
 assert all(j['mode'] in ('transplant','swap') for j in jj)
 bad=[dict(x,label=1) for x in items]
 with pytest.raises(ValueError):validate(bad,a,shard,4,2)
 with pytest.raises(ValueError):validate(items[:-1],a,shard,4,2)

def test_transplant_and_both_complements_no_scale():
 h=np.array([[1.,2.,3.,4.]]);donor=np.array([[5.,6.,7.,8.]]);q=np.eye(4)[:,:2]
 assert np.array_equal(transform(h,donor,'transplant'),donor)
 assert np.array_equal(transform(h,donor,'swap',q),[[5,6,3,4]])
 assert np.array_equal(transform(h,donor,'swap',q,True),[[1,2,7,8]])
 assert np.array_equal(transform(h,donor,'swap',np.eye(4)[:,2:]),[[1,2,7,8]])
 assert np.array_equal(transform(h,donor,'swap',q)+transform(h,donor,'swap',q,True),h+donor)
 assert ratios(h,2*h)[0]==2

def test_injection_math_retained_only_as_withdrawn_helper():
 h=np.ones((2,4),dtype=np.float64);d=np.full_like(h,2.123456789)
 for alpha in (.5,1,2,4):assert np.array_equal(transform(h,h,'injection',delta=d,alpha=alpha),(h+alpha*d).astype(np.float32))
 assert not any(c['mode']=='injection' for c in cells('reported','format_plan','oracle'))

class Block(torch.nn.Module):
 def __init__(self,index,tuple_output=False):super().__init__();self.index=index;self.tuple_output=tuple_output;self.seen=[]
 def forward(self,z):
  out=z+0.01*(self.index+1);self.seen.append(out.detach().clone());return (out,'metadata') if self.tuple_output else out
class Tiny(torch.nn.Module):
 def __init__(self,fail=False):
  super().__init__();self.emb=torch.nn.Embedding(8,4);self.layers=torch.nn.ModuleList([Block(i,i in (28,36,44)) for i in range(46)]);self.fail=fail
 def get_input_embeddings(self):return self.emb
 def forward(self,input_ids,attention_mask,use_cache):
  assert not use_cache;z=self.emb(input_ids)
  for i,block in enumerate(self.layers):
   if self.fail and i==32:raise RuntimeError('tiny failure')
   z=block(z);z=z[0] if isinstance(z,tuple) else z
  return z
@pytest.mark.parametrize('block',[28,36])
def test_withdrawn_upstream_prototype_real_tiny_forward_and_hook_cleanup(block):
 m=Tiny();items=[dict(ids=[1,2,3],read_index=2)]*2;delta=np.ones((2,4),np.float64)
 baseline=m.emb(torch.tensor([1,2,3]))[-1].detach().numpy()+sum(.01*(i+1) for i in range(45))
 h,norm=upstream(m,items,delta,block,2,blocks=m.layers)
 assert np.allclose(h,baseline+2,atol=1e-5) and all(x>0 for x in norm)
 assert not m.layers[28]._forward_hooks and not m.layers[36]._forward_hooks and not m.layers[44]._forward_hooks
 # Other tokens passed to the next layer unchanged by the patch.
 before=m.layers[block].seen[0];after=m.layers[block+1].seen[0]-.01*(block+2)
 assert torch.allclose(before[:,:2],after[:,:2]) and torch.allclose(before[:,2]+2,after[:,2])
 assert not m.layers[45].seen

def test_hook_cleanup_on_real_failure():
 m=Tiny(fail=True)
 with pytest.raises(RuntimeError):upstream(m,[dict(ids=[1,2],read_index=1)],np.ones((1,4)),28,1,blocks=m.layers)
 assert not any(b._forward_hooks for b in m.layers)

class B:
 def __init__(self):self.calls=[]
 def load_oracle(self):pass
 def load_nla(self):pass
 def native_one(self,r,h):self.calls.append((r,h.copy()));return [[dict(text='synthetic',raw='synthetic')] for _ in h]

@pytest.mark.parametrize('shard,total',[('reported',4200),('missed',2520)])
def test_full_synthetic_acquisition_uses_original_clock_and_native_layers(tmp_path,shard,total):
 items,a=fixture(shard);b=B();m=original();c=m.Clock(tmp_path,time.time()+10000)
 assert acquire(items,a,shard,b,c,tmp_path,'H200')
 jj=json.loads((tmp_path/'JOB_GRID.json').read_text());done=json.loads((tmp_path/'COMPLETED.json').read_text());assert done==list(range(len(jj)))
 records=[x for p in sorted((tmp_path/'jobs').glob('*.json')) for x in json.loads(p.read_text())]
 assert len(records)==total and len({r['id'] for r in records})==total
 assert all(r['basis_block']==44 and r['read_block']==(44 if r['reader']=='oracle' else 42) and r['gpu_type']=='H200' and r['repeat']==0 for r in records)
 assert all(r['norm_over_1_5']==(r['norm_ratio']>1.5) for r in records)
 assert len([x for x in c.events if 'warmup_discarded' in x['phase']])==4
 assert set(c.cost)=={'oracle:8','oracle:4','nla:8','nla:4'}
 assert all(len(c.cost[k])==sum(j['phase']==k for j in jj) for k in c.cost)
 # First NLA transplant really uses H42 donor, not H44.
 r=next(x for x in records if x['reader']=='nla' and x['condition']=='transplant');i=next(x for x in items if x['id']==r['item_id'])
 assert r['norm_ratio']==pytest.approx(float(np.linalg.norm(a['H42'][i['donor_slot']].astype(np.float32))/np.linalg.norm(a['H42'][i['slot']])))

def test_forecast_no_fit_preserves_pilots_and_stops(tmp_path):
 items,a=fixture('missed');m=original();c=m.Clock(tmp_path,time.time()+10000)
 # Force a retained phase mean larger than custody after each actual synthetic call.
 original_call=c.call
 def call(kind,fn):
  result=original_call(kind,fn)
  if kind in c.cost:c.cost[kind][-1]=10000
  return result
 c.call=call
 assert not acquire(items,a,'missed',B(),c,tmp_path,'H200')
 assert len(json.loads((tmp_path/'COMPLETED.json').read_text()))==4
 assert json.loads((tmp_path/'FORECAST.json').read_text())['status']=='NO_FIT'

def test_hardware_record_requires_full_shard_binding(monkeypatch):
 monkeypatch.setenv('RUNPOD_POD_ID','fixture');a=dict(experiment='E100',shard='reported',stage='ab',gpu_count=1,gpu_type='B200',input_seal_sha256='i',source_seal_sha256='s',assets_sha256='a',cap_seconds=100,prior_seconds=0,authorized_cumulative_seconds=100,custody_start_epoch=1,pod_created_epoch=1,absolute_deadline_epoch=101,daily_budget_verified=True,projected_daily_USD=1,daily_budget_USD=2,allocation_verified=True,row_gpu_types={r:'B200' for r in ROWS['reported']},pod_id='fixture')
 validate_assignment(a,'reported','i','s','a');a['row_gpu_types']['format_plan']='H200'
 with pytest.raises(ValueError):validate_assignment(a,'reported','i','s','a')
