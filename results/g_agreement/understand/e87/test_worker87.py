import sys
import time
from pathlib import Path
import numpy as np
import pytest
import worker87 as W

class Tiny87:
    def __init__(self):self.calls=[]
    def sync(self):pass
    def load_oracle(self):self.calls.append('oracle_setup')
    def load_nla(self):self.calls.append('nla_setup')
    def confirm_layers(self):return list(range(20,61,4))
    def warm_capture(self):self.calls.append('capture_warmup')
    def capture_all(self,item,layers):
        self.calls.append(('capture',tuple(layers)))
        return {l:np.ones((len(item['ids']),W.DIM),np.float32)*(l+1) for l in layers}
    def sweep(self,reader,vectors,layer):
        self.calls.append(('read',reader,layer))
        return [dict(raw='<explanation>synthetic</explanation>',text='synthetic',malformed=False) for _ in vectors]

def fixture(row=0):
    items=[dict(id=f'synthetic-{row}-{i}',global_index=row*30+i,ids=[1]*16,read_index=15,reuse44=False) for i in range(30)]
    plan=dict(experiment='E87',seed=W.SEED,layers=list(W.LAYERS),oracle_positions=16,nla_positions=8,
              shard=0,row_indices=[row],item_ids=[x['id'] for x in items])
    return items,plan

def test_trained_range_and_short_prompts():
    sys.path.insert(0,str(W.ROOT/'external/mats-nla-workspace/src'))
    from mats.readers.olens import TRAINED_LAYERS
    assert set(W.LAYERS)<=set(TRAINED_LAYERS)
    items,p=fixture();W.validate(items,p)
    items[0]['ids']=[1]*12;items[0]['read_index']=11
    W.validate(items,p)
    items[0]['ids']=[];items[0]['read_index']=-1
    with pytest.raises(ValueError):W.validate(items,p)

def test_full_grid_stage_order_and_reuse(monkeypatch,tmp_path):
    monkeypatch.setattr(W,'DIM',8)
    items,p=fixture();items[0]['reuse44']=True
    inp=tmp_path/'in';inp.mkdir();(inp/'reuse44').mkdir()
    np.save(inp/'reuse44'/f"{items[0]['id']}.npy",np.ones((16,8),np.float16))
    out=tmp_path/'out';out.mkdir();b=Tiny87()
    seeds={k:0 for k in ('oracle_setup','capture','placebo_build','oracle_native','nla_setup','nla_native')}
    c=W.Clock(out,time.time()+3600,seeds,b)
    original=b.sweep
    def sweep(*args):
        assert (out/'capture/CAPTURE_SEAL.json').exists()
        return original(*args)
    b.sweep=sweep
    W.acquire(inp,items,p,b,c,out,dict(experiment='E87'))
    assert W.read(out/'COUNTS.json')==dict(oracle=6720,nla=240)
    capcalls=[x for x in b.calls if isinstance(x,tuple) and x[0]=='capture']
    assert 44 not in capcalls[0][1] and 44 in capcalls[1][1]
    records=[x for f in (out/'jobs').glob('oracle_real_20*.json') for x in W.read(f)]
    assert len(records)==30*16 and {x['position'] for x in records}==set(range(16))
    records=[x for f in (out/'jobs').glob('nla_real*.json') for x in W.read(f)]
    assert {x['position'] for x in records}==set(range(8,16))
    assert all('warmup' not in k for k in c.observed)

def test_placebo_shard_invariance_and_norms(monkeypatch,tmp_path):
    monkeypatch.setattr(W,'DIM',8)
    xs,p=fixture();ys,q=fixture(1);allitems=xs+ys
    real={l:np.random.default_rng(l).standard_normal((60,16,8)).astype(np.float32) for l in W.LAYERS}
    a=tmp_path/'full';a.mkdir();b=tmp_path/'shard';b.mkdir()
    full=W.placebo(real,allitems,a)
    part=W.placebo({l:h[30:] for l,h in real.items()},ys,b)
    for l in W.LAYERS:
        assert np.array_equal(full[l][30:],part[l])
        target=np.median(np.linalg.norm(real[l][30:].astype(np.float64),axis=-1),axis=0)
        assert np.allclose(np.linalg.norm(part[l].astype(np.float64),axis=-1),target[None],rtol=1e-6)

def test_layer_argument_reaches_oracle(monkeypatch):
    import torch
    from types import SimpleNamespace
    sys.path.insert(0,str(W.ROOT/'external/mats-nla-workspace/src'))
    class Oracle:
        def verbalize(self,h,layer,k,sampling,batch):
            assert layer==60 and k==1 and batch==8 and sampling.temperature==0 and sampling.max_new_tokens==128
            return [['stub'] for _ in h]
    b=W.Backend87(None);b.readers=SimpleNamespace(oracle=Oracle())
    assert len(b.sweep('oracle',np.ones((8,5120)),60))==8


def test_short_positions_and_matched_placebo(monkeypatch,tmp_path):
    monkeypatch.setattr(W,'DIM',8)
    items,p=fixture()
    for x in items:x['ids']=[1]*12;x['read_index']=11
    W.validate(items,p)
    out=tmp_path/'short';out.mkdir();b=Tiny87()
    seeds={k:0 for k in ('oracle_setup','capture','placebo_build','oracle_native','nla_setup','nla_native')}
    W.acquire(tmp_path,items,p,b,W.Clock(out,time.time()+3600,seeds,b),out,dict(experiment='E87'))
    assert W.read(out/'COUNTS.json')==dict(oracle=30*12*7*2,nla=30*8)
    for arm in ('real','placebo'):
        rows=[x for f in (out/'jobs').glob(f'oracle_{arm}_56_*.json') for x in W.read(f)]
        assert len(rows)==360 and {x['position'] for x in rows}==set(range(12))
        assert {x['position_offset'] for x in rows}==set(range(-11,1))
    assert np.all(np.load(out/'capture/placebo56.npy')[:,:4]==0)
