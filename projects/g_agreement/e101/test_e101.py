import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
from projects.g_agreement.e101.acquisition import patched_forward,behaviour,batches
from projects.g_agreement.e101.contract import select,committed_dose

class Tiny(torch.nn.Module):
    def __init__(self):
        super().__init__();self.emb=torch.nn.Embedding(8,4);self.layers=torch.nn.ModuleList([torch.nn.Identity() for _ in range(45)]);self.config=SimpleNamespace(num_hidden_layers=45);self.seen=[]
    def get_input_embeddings(self):return self.emb
    def forward(self,input_ids,attention_mask,use_cache,logits_to_keep):
        assert not use_cache and attention_mask.eq(1).all()
        x=self.emb(input_ids)
        for layer in self.layers:x=layer(x)
        self.seen.append(x.detach().clone())
        logits=torch.cat((x,x),dim=-1)
        return SimpleNamespace(logits=logits[:,-logits_to_keep:])

def test_patch_both_blocks_and_cleanup():
    for block in (42,44):
        m=Tiny();v=np.full((2,4),7,np.float32)
        patched_forward(m,[[1,2],[3,4]],[1,1],v,block,1)
        assert torch.all(m.seen[-1][:,1]==7)
        assert not m.layers[block]._forward_hooks
        def fail(*args,**kwargs):raise RuntimeError('crash')
        m.forward=fail
        with pytest.raises(RuntimeError):patched_forward(m,[[1,2],[3,4]],[1,1],v,block,1)
        assert not m.layers[block]._forward_hooks

def test_nonfinite_fatal():
    m=Tiny()
    m.forward=lambda **kw:SimpleNamespace(logits=torch.full((1,1,8),float('nan')))
    with pytest.raises(ValueError):patched_forward(m,[[1]],[0],np.ones((1,4)),44,1)
    assert not m.layers[44]._forward_hooks

def test_continuations_shared_prefix_and_batch_parity():
    torch.manual_seed(1);m=Tiny();x=dict(block=42,ids=[1,2],read_index=1,candidate_ids=[[[3],[3,4]]]);h=np.ones((2,4),np.float32)
    r=behaviour(m,[x,x],h,'continuation')
    assert r==[behaviour(m,[x],h[:1],'continuation')[0]]*2
    assert r[0]['pair_logits'][0][0]==r[0]['pair_logits'][0][1]
    assert r[0]['pair_logprobs'][0][0]>r[0]['pair_logprobs'][0][1]
    assert all(not layer._forward_hooks for layer in m.layers)

def dev():
    xs=[];rr=[];key={str(i):dict(split='dev',row='format_plan',contrast_target_sign=1 if i%2 else -1) for i in range(10)}
    for a in (.5,1.,2.,4.):
        for i in range(10):
            ident=f'{a}:{i}';xs.append(dict(id=ident,base_id=str(i),row='format_plan',block=44,alpha=a,condition='steered',candidate_ids=[[[1],[2]]]))
            yes=i<(7 if a>=2 else 6);score=key[str(i)]['contrast_target_sign']*(1 if yes else -1)
            rr.append(dict(id=ident,pair_logits=[[score,0.]]))
    return xs,rr,key

def test_smallest_dose_strict_target_side_and_complete_grid():
    xs,rr,key=dev();result=select(xs,rr,key,'next_token',10)
    assert result['format_plan:44']['alpha']==2.
    with pytest.raises(ValueError):select(xs,rr[:-1],key,'next_token',10)
    with pytest.raises(ValueError):select(xs+[xs[0]],rr+[rr[0]],key,'next_token',10)
    for r in rr:r['pair_logits']=[[0.,0.]]
    assert select(xs,rr,key,'next_token',10)['format_plan:44']['alpha'] is None
    key['0']['split']='test'
    with pytest.raises(ValueError):select(xs,rr,key,'next_token',10)

def test_test_barrier_rejects_uncommitted_receipt(tmp_path):
    p=tmp_path/'dose.json';p.write_text('{}')
    with pytest.raises(ValueError):committed_dose(tmp_path,p,'not-a-commit','x')

def test_equal_length_groups():
    xs=[dict(block=b,ids=list(range(n))) for b,n in [(44,3),(42,2),(44,2),(44,3)]]
    groups=batches(xs,2)
    assert sorted(i for g in groups for i in g)==list(range(4))
    assert all(len({(xs[i]['block'],len(xs[i]['ids'])) for i in g})==1 for g in groups)

def test_runner_complete_both_readers_and_logits(tmp_path):
    from projects.g_agreement.e101.runner import acquire,dependencies
    old,_,_,_,_=dependencies()
    xs=[dict(id=str(i),row='format_plan',block=b,ids=[1,2],read_index=1,candidate_ids=[[[3],[4]]]) for i,b in enumerate((42,44))]
    class Runtime:
        def __init__(self):self.readers=self;self.model=None;self.tok=None;self.loaded=[];self.base=Tiny()
        def load_base(self):self.loaded.append('base')
        def load_oracle(self):self.loaded.append('oracle')
        def load_nla(self):self.loaded.append('nla')
        def subject(self):
            import contextlib
            return self.base,None,contextlib.nullcontext()
        def native_one(self,reader,h):return [[dict(text=reader)] for _ in h]
    import time
    rt=Runtime();status=acquire(xs,np.ones((2,4),np.float32),rt,old.Clock(tmp_path,time.time()+3600),tmp_path,'test','next_token')
    assert status=='COMPLETE' and rt.loaded==['base','oracle','nla']
    import json
    assert len(json.loads((tmp_path/'COMPLETED.json').read_text()))==4

def test_cpu_composition_target_sign_and_no_labels():
    from projects.g_agreement.e101.materialize import compose
    records=[dict(id=str(i),row='format_plan',split='dev',ids=[1],candidate_ids=[[[2],[3]]],label=i%2,contrast_target_sign=1 if i%2==0 else -1) for i in range(84)]
    u=np.zeros(5120);u[0]=1;r=np.zeros(5120);r[1]=1
    carriers={('format_plan',b):{str(i):np.ones(5120) for i in range(84)} for b in (42,44)}
    direction={('format_plan',b):u for b in (42,44)};norms={k:2. for k in direction}
    xs,h,key,_=compose(records,carriers,direction,norms,{42:r,44:r},'dev',ruling_commit='2bdde763')
    assert len(xs)==672 and h.shape==(672,5120)
    assert h[0,0]==2 and h[4,0]==0
    assert all('label' not in x and 'contrast_target_sign' not in x for x in xs)
    assert key['0']['split']=='dev'


