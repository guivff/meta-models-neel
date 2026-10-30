import copy
import sys
import time
import numpy as np
import pytest
import worker87 as W
import scope99 as S
from test_worker87 import Tiny87


def fixture():
    items=[]
    for f in S.FAMILIES:
        for i in range(8):
            ps=list(range(8,16))
            if f=='buggy_code':ps=[15]
            if f=='agentic_misalignment':ps=list(range(16))
            items.append(dict(id=f'{f}-{i}',family=f,ids=[1]*16,positions=ps,single_position=15 if f not in ('directed_modulation','jailbreak_recognition') else 7,
                family_layer=(60 if i%2 else 56) if f=='buggy_code' else None,
                placebo_ids=[__import__('hashlib').sha256(f'{f}:{j}'.encode()).hexdigest()[:24] for j in range(i,30,8)] if f in S.PLACEBO else []))
    p=dict(experiment='E99',seed=S.SEED,reduction_step=0,owner_seal_sha256='a'*64,items_sha256='b'*64,shards=4,shard=0,item_ids=[])
    p['item_ids']=[x['id'] for x in S.shard_items(items,p)]
    return items,p


def test_grid_and_complete_sharding():
    items,p=fixture();S.validate(items,p)
    seen=[]
    for shard in range(4):
        q=dict(p,shard=shard);q['item_ids']=[x['id'] for x in S.shard_items(items,q)];S.validate(items,q)
        seen+=q['item_ids']
        for (r,l,f),cs in S.cells(items,q).items():
            for c in cs:
                if c['family']=='agentic_misalignment':assert l in (36,42,44,56)
                if c['family']=='directed_modulation' and c['position']==7:assert l in (42,44) and c['single_site'] and not c['grid']
                if c['family']=='buggy_code':assert l in (42,44,56,60)
    assert sorted(seen)==sorted(x['id'] for x in items) and len(set(seen))==len(seen)
    bad=copy.deepcopy(items);bad[0]['gold']='private'
    with pytest.raises(ValueError):S.validate(bad,p)
    bad=copy.deepcopy(items);bad[0]['placebo_ids']=[]
    with pytest.raises(ValueError):S.validate(bad,p)


def test_reductions_and_random_invariance(monkeypatch):
    monkeypatch.setattr(W,'DIM',8)
    x=dict(family='agentic_misalignment',positions=list(range(128)),single_position=127)
    assert S.positions(x,44,2)==list(range(64,128))
    items,p=fixture();p['reduction_step']=3
    for shard in range(4):
        assert all(x['family']!='jailbreak_recognition' for x in S.shard_items(items,dict(p,shard=shard)))
    c=dict(family='user_modeling',pseudo_id='a'*24,position=8)
    a=S.random_vector(c,3.,8);b=S.random_vector(dict(c,layer=56,reader='oracle'),3.,8)
    assert np.array_equal(a,b) and np.isclose(np.linalg.norm(a),3.)


def test_capture_and_paired_norm_profile(monkeypatch,tmp_path):
    monkeypatch.setattr(W,'DIM',8)
    items,p=fixture();caps=[]
    for i in range(4):
        out=tmp_path/str(i);out.mkdir();b=Tiny87();q=dict(p,shard=i)
        root=S.capture(items,q,b,W.Clock(out,time.time()+3600,{},b),out,dict(shard=i));caps.append(root)
    # Real checkpoint parity stays a live gate; this fixture checks wiring only.
    out=tmp_path/'read';out.mkdir();b=Tiny87()
    S.acquire(items,p,b,W.Clock(out,time.time()+3600,{},b),out,{'staging_seconds':275},caps[0],profile=True)
    report=W.read(out/'MEASURED_PROFILE.json')
    assert report['margin']==1.25 and report['parity_items']==8 and report['profile_outputs_discarded']
    assert all(1<=W.read(f)['n']<=8 for f in out.glob('PARITY_*.json'))
    assert report['first_output_utc']!='unknown'


def test_e99_backend_batch32(monkeypatch):
    import torch
    from types import SimpleNamespace
    sys.path.insert(0,str(W.ROOT/'external/mats-nla-workspace/src'))
    class Oracle:
        def verbalize(self,h,layer,k,sampling,batch):
            assert batch==32 and layer==56 and k==1 and sampling.temperature==0 and sampling.max_new_tokens==128
            return [['fixed'] for _ in h]
    b=W.Backend87(None);b.readers=SimpleNamespace(oracle=Oracle());b.sweep_batch_size=32
    vals=b.sweep('oracle',np.ones((32,5120)),56)
    assert vals[:8]==[b.sweep('oracle',np.ones((1,5120)),56)[0] for _ in range(8)]


def test_admission_requires_sealed_profiles_and_counts_prior(tmp_path):
    import package99 as P
    paths=[]
    for i in range(4):
        d=tmp_path/str(i);d.mkdir();path=d/'MEASURED_PROFILE.json'
        W.write(path,dict(shard=i,items_sha256='a'*64,source_seal_sha256='b'*64,reduction_step=0,
            status='TIMING_ONLY_NOT_SCIENCE',margin=1.25,batch_size=32,parity_items=8,
            parity_counts=dict(oracle=8,nla=8),forecast_seconds=20000))
        W.seal(d,'OUTPUT_SEAL.json',status='PROFILE_ONLY',source_seal_sha256='b'*64)
        paths.append(path)
    P.admit(paths,tmp_path/'admission.json',prior_seconds=7000)
    assert W.read(tmp_path/'admission.json')['status']=='REDUCTION_REQUIRED'
    assert W.read(tmp_path/'admission.json')['next_reduction_step']==1
    paths[0].write_text('{}')
    with pytest.raises(ValueError):P.admit(paths,tmp_path/'bad.json',0)
