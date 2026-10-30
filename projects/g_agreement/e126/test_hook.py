from types import SimpleNamespace
import numpy as np,torch,pytest
from projects.g_agreement.e101.runner import dependencies
dependencies()
from projects.g_agreement.e101.test_e104 import Tiny104,Layer
from projects.g_agreement.e126.hook import forward,score_batch,controls,LAYERS

class Tiny(Tiny104):
    def __init__(self,fail_call=None):
        super().__init__(fail_call);self.layers=torch.nn.ModuleList([Layer(i)for i in range(64)]);self.config.num_hidden_layers=64

def payload(direction='restore',block=52):
    earlier,u=controls('frozen-id',11,block,4,direction)
    return np.concatenate([np.array([.5,-.2,.1,.3]),np.array([1.,2,3,4]),u,[earlier]]).astype('float32')[None]
def seq():return [list(range(1,13))]

@pytest.mark.parametrize('block',LAYERS)
@pytest.mark.parametrize('direction',['restore','insert'])
def test_actual_block_output_replacement_and_exact_upstream_composition(block,direction):
    m=Tiny();p=payload(direction,block);before=p.copy();forward(m,seq(),[11],p,block,1,direction=direction,control='read')
    s=m.snapshots[-1];assert torch.equal(s[block][0,11],torch.tensor([1.,2,3,4]))
    # U is applied only on restore and never directly to its read token.
    raw=m.emb(torch.tensor(seq())).detach();diff=s[40]-raw
    if direction=='restore':assert torch.allclose(diff[0,3:11],torch.tensor(p[0,:4]).expand(8,4),atol=1e-6)
    else:assert torch.equal(s[40],raw)
    assert torch.equal(s[40][0,11],raw[0,11]) and np.array_equal(p,before)
    assert all(not z._forward_hooks for z in m.layers)

def test_earlier_control_excludes_eight_steered_sites_and_preserves_read_at_patch_block():
    m=Tiny();p=payload('insert');q=int(p[0,-1]);forward(m,seq(),[11],p,52,1,direction='insert',control='earlier')
    assert 0<=q<3 and torch.equal(m.snapshots[-1][52][0,q],torch.tensor([1.,2,3,4]))
    assert torch.equal(m.snapshots[-1][52][0,11],m.snapshots[-1][51][0,11])

def test_random_control_has_actual_primary_delta_norm_no_target_replacement():
    m=Tiny();p=payload('insert');out=[];forward(m,seq(),[11],p,52,1,direction='insert',control='random',observations=out)
    a=out[0];assert a['delta_norm']==pytest.approx(a['reference_read_replacement_delta_norm'],rel=1e-6)
    assert not torch.equal(m.snapshots[-1][52][0,11],torch.tensor([1.,2,3,4]))

def test_original_continuation_branch_repeats_fixed_read_patch_not_last_appended_token():
    m=Tiny();x=dict(id='opaque',row='fact_recall',block=52,direction='restore',control='read',ids=seq()[0],read_index=11,candidate_ids=[[[3],[4,5]]])
    r=score_batch(m,[x],payload());assert set(r[0])>={'pair_logits','pair_logprobs','patch'}
    assert all(torch.equal(s[52][0,11],torch.tensor([1.,2,3,4]))for s in m.snapshots)
    assert m.calls==3 and all(not z._forward_hooks for z in m.layers)

def test_rng_deterministic_and_no_global_rng_consumption():
    a,u=controls('id',22,44,4,'restore');b,v=controls('id',22,44,4,'restore')
    assert a==b and np.array_equal(u,v) and np.linalg.norm(u)==pytest.approx(1.)
    assert not np.array_equal(u,controls('id',22,52,4,'restore')[1])

def test_hooks_cleaned_on_downstream_failure_and_invalid_earlier_rejected():
    m=Tiny(fail_call=1)
    with pytest.raises(RuntimeError):forward(m,seq(),[11],payload(),44,1,direction='restore',control='read')
    assert all(not z._forward_hooks for z in m.layers)
    m=Tiny();p=payload();p[0,-1]=10
    with pytest.raises(ValueError):forward(m,seq(),[11],p,52,1,direction='restore',control='earlier')
    assert all(not z._forward_hooks for z in m.layers)

def test_whole_public_packet_and_exact4020_no_baseline_jobs():
    import json
    from pathlib import Path
    from projects.g_agreement.e126.inputs import load,jobs,payload as pack
    from projects.g_agreement.e100.contract import sha
    root=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e126-inputs-v1/inputs')
    xs,data=load(root,sha(root/'INPUT_SEAL.json'));jj=list(jobs(xs));cells=[x for j in jj for x in j]
    assert len(cells)==4020 and len({x['id']for x in cells})==4020
    for L in LAYERS:
        for d in ('restore','insert'):
            for c in ('read','earlier','random'):assert sum(x['block']==L and x['direction']==d and x['control']==c for x in cells)==134
    for j in jj:
        p=pack(j,data);assert p.shape==(len(j),15361)
        for x,v in zip(j,p):
            assert np.array_equal(v[:5120],data['upstream'][x['vector_index']])
            h=data['unhooked'if x['direction']=='restore'else'steered'][x['vector_index'],LAYERS.index(x['block'])]
            assert np.array_equal(v[5120:10240],h)
