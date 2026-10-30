import sys,time
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker112 import acquire,validate,Clock,read,CONDITIONS,CAPTURE_SHA

class Tiny80c:
    def sync(self):pass
    def load_oracle(self):pass
    def load_nla(self):pass
    def native(self,reader,h):return [[dict(raw='<explanation>synthetic</explanation>',text='synthetic')] for _ in h]


def test_one_condition_exact518_each_and_no_old_arms(tmp_path):
    items=[dict(id=str(i),feature='test') for i in range(518)]
    vectors={(l,'PCA1_ablated'):np.ones((518,4),np.float32) for l in (42,44)}
    b=Tiny80c();clock=Clock(tmp_path,time.time()+3600,dict(oracle_setup=0,nla_setup=0,oracle_native=0,nla_native=0),b)
    acquire(items,vectors,b,clock,tmp_path)
    assert read(tmp_path/'COUNTS.json')==dict(new_readouts=1036,none_new_readouts=0,oracle=518,nla=518)
    rr=[r for f in (tmp_path/'jobs').glob('*.json') if not f.name.endswith('SEAL.json') for r in read(f)]
    assert len(rr)==len({r['id'] for r in rr})==1036
    assert {r['condition'] for r in rr}=={'PCA1_ablated'} and {r['repeat'] for r in rr}=={0}
    assert {(r['reader'],r['layer']) for r in rr}=={('oracle',44),('nla',42)}
    assert len([e for e in clock.events if 'warmup' in e['phase']])==2


def test_only_registered_full_public_grid_passes(tmp_path):
    items=[dict(id=str(i),feature='test') for i in range(518)]
    plan=dict(experiment='E112',conditions=['PCA1_ablated'],capture_seal_sha256=CAPTURE_SHA,vector_seal_sha256='a'*64,item_ids=[x['id'] for x in items])
    for l in (42,44):np.save(tmp_path/f'PCA1_ablated{l}.npy',np.ones((518,5120),np.float32))
    assert set(validate(tmp_path,plan,items))=={(42,'PCA1_ablated'),(44,'PCA1_ablated')}
    with pytest.raises(ValueError):validate(tmp_path,dict(plan,conditions=['J_ablated']),items)
    with pytest.raises(ValueError):validate(tmp_path,plan,items[:-1])


def test_supplied_vectors_are_never_mutated(tmp_path):
    class Mutator(Tiny80c):
        def native(self,reader,h):h[0,0]+=1;return super().native(reader,h)
    items=[dict(id=str(i),feature='test') for i in range(518)]
    vectors={(l,'PCA1_ablated'):np.ones((518,4),np.float32) for l in (42,44)}
    b=Mutator();clock=Clock(tmp_path,time.time()+3600,dict(oracle_setup=0,nla_setup=0,oracle_native=0,nla_native=0),b)
    with pytest.raises(ValueError,match='unchanged vectors'):acquire(items,vectors,b,clock,tmp_path)
