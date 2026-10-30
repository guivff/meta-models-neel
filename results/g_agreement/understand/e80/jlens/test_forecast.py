"""E80 synthetic operational tests. Never opens real captures or outcomes."""
import hashlib,json
import numpy as np
import pytest
import forecast as f

def fixture():
 public=[];targets=[]
 for family,n in f.COUNTS.items():
  for k in range(n):
   i=f'E80:{family}:{k:03d}';public.append(dict(id=i,family=family,ids=[2,3,4],plan_positions=[1,2],read_position=2,read_token_id=4));targets.append(dict(id=i,family=family,item_targets=['x'],target_first_token_ids=[1]))
 return public,targets

def test_exact_best_rank_and_any_target():
 x=np.arange(20,dtype=np.float32);r=f.summarise_logits(x,[0,15,15]);assert r['visible_top10']and r['best_target_rank0']==4 and r['best_target_rank1']==5
 assert not f.summarise_logits(x,[0,1])['visible_top10']

def test_tie_membership_is_not_inferred_from_rank():
 x=np.zeros(20);r=f.summarise_logits(x,[15],np.arange(10));assert r['best_target_rank0']==0 and not r['visible_top10']

def test_inventory_primary_position_and_all_families():
 p,t=fixture();f.validate_items(p,t)
 p[0]['read_position']=1
 with pytest.raises(AssertionError):f.validate_items(p,t)

def test_duplicate_or_missing_targets_rejected():
 p,t=fixture();t[-1]['id']=t[0]['id']
 with pytest.raises(AssertionError):f.validate_items(p,t)
 p,t=fixture();t[0]['item_targets']=[]
 with pytest.raises(AssertionError):f.validate_items(p,t)

def test_capture_custody_and_token_binding(tmp_path):
 p,t=fixture();order=[dict(id=x['id'],read_position=x['read_position'],token_ids_sha256=hashlib.sha256(json.dumps(x['ids'],separators=(',',':')).encode()).hexdigest())for x in p]
 op=tmp_path/'order.json';op.write_text(json.dumps(order));ap=tmp_path/'acts.npy';np.save(ap,np.ones((518,5120),dtype=np.float16))
 ref=lambda q:dict(path=str(q),sha256=f.sha(q))
 m=dict(experiment='E80',layer=44,site='decoder_block_output',issuer='integrator',reader_outputs_opened=False,readers_held_until_forecast_commit=True,capture_inputs_sha256='synthetic',order=ref(op),activations=ref(ap))
 o,a=f.validate_capture(m,p,'synthetic');assert len(o)==518 and a.shape==(518,5120)
 m['reader_outputs_opened']=True
 with pytest.raises(AssertionError):f.validate_capture(m,p,'synthetic')
 m['reader_outputs_opened']=False;order[0]['read_position']=0;op.write_text(json.dumps(order));m['order']=ref(op)
 with pytest.raises(AssertionError):f.validate_capture(m,p,'synthetic')

def test_nonfinite_and_out_of_vocab_rejected():
 with pytest.raises(AssertionError):f.summarise_logits(np.array([0.,np.nan]),[0])
 with pytest.raises(AssertionError):f.summarise_logits(np.ones(12),[12])

def test_two_lens_batch_alignment_and_transforms():
 import torch
 from types import SimpleNamespace
 p,t=fixture();p=p[:19];t=t[:19];order=[dict(id=r['id'])for r in p]
 for x in t:x['target_first_token_ids']=[19]
 reader=SimpleNamespace(j=-torch.eye(3),norm=torch.nn.Identity(),wu=torch.arange(60,dtype=torch.float32).reshape(20,3))
 acts=np.ones((19,3),dtype=np.float32);rows=f.score_activations(acts,order,p,t,reader)
 assert [r['id']for r in rows]==[r['id']for r in order]
 assert all(r['logit']['visible_top10'] and not r['J']['visible_top10']for r in rows)
 assert all(r['logit']['best_target_rank0']==0 and r['J']['best_target_rank0']==19 for r in rows)
