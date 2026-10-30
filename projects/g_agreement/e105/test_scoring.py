import numpy as np
import pytest
import torch
from projects.g_agreement.e101.test_e101 import Tiny
from . import scoring as S


def item(condition,index=None):
    return dict(id=condition,inventory_id='i',base_id='base',row='nesting_depth',block=44,condition=condition,
        ids=[1,2],read_index=1,candidate_ids=[[[3],[3,4]],[[5],[6,7]]],vector_index=index,
        donor_id=None if condition=='0' else 'donor')


def test_supplied_absolute_residual_reaches_next_block_no_normalisation():
    model=Tiny();model.layers.append(torch.nn.Identity());model.config.num_hidden_layers=46
    seen=[]
    handle=model.layers[45].register_forward_pre_hook(lambda m,args:seen.append(args[0].detach().clone()))
    vectors=np.full((1,4),7.,np.float32);before=vectors.copy()
    out=S.score_batch(model,[item('T',0)],vectors)
    handle.remove()
    assert seen and all(torch.all(x[:,1]==7) for x in seen)
    assert np.array_equal(vectors,before) and set(out[0])=={'id','inventory_id','base_id','row','condition','block','vector_index','pair_logprobs'}
    assert all(not x._forward_hooks for x in model.layers)


def test_unpatched_baseline_never_installs_intervention_and_matches_natural(monkeypatch):
    torch.manual_seed(1);model=Tiny();natural=model.emb(torch.tensor([2])).detach().numpy()
    expected=S.score_batch(model,[item('T',0)],natural)[0]['pair_logprobs']
    monkeypatch.setattr(model.layers[44],'register_forward_hook',lambda *a,**k:pytest.fail('baseline installed a hook'))
    plain=S.score_batch(model,[item('0')],np.empty((0,4)))[0]['pair_logprobs']
    assert plain==expected and plain[0][0]>plain[0][1] # shared-prefix token-sum scorer stays frozen


def test_batch_serial_parity_and_baseline_separation():
    torch.manual_seed(2);model=Tiny();xs=[item('T',0),item('S',1)];v=np.array([[1,2,3,4],[4,3,2,1]],np.float32)
    batched=S.score_batch(model,xs,v)
    assert batched==[S.score_batch(model,[x],v)[0] for x in xs]
    with pytest.raises(ValueError,match='separate'):S.score_batch(model,[xs[0],item('0')],v)
    all_items=xs+[item('0')];groups=list(S.batches(all_items))
    assert sorted(i for g in groups for i in g)==[0,1,2] and all(len({all_items[i]['condition']=='0' for i in g})==1 for g in groups)


def test_nonfinite_baseline_is_fatal():
    model=Tiny()
    model.forward=lambda **kw:type('O',(),{'logits':torch.full((1,kw['logits_to_keep'],8),float('nan'))})()
    with pytest.raises(ValueError,match='finite'):S.score_batch(model,[item('0')],np.empty((0,4)))
