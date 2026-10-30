import numpy as np
import pytest
import torch
from projects.g_agreement.r_bench.remainder_r2b_live import PrefillTaps,oracle_score,oracle_free


def blocks():return torch.nn.ModuleList([torch.nn.Identity() for _ in range(8)])


def test_taps_compact_prefill_only_and_hooks_removed():
    b=blocks();h=torch.arange(24.).reshape(2,3,4)
    with PrefillTaps(b,2) as tap:
        for block in b:h=block(h)
        for block in b:block(torch.ones(2,1,4))
    arrays=tap.arrays(candidate_pairs=False)
    assert set(arrays)=={2,4,6}
    assert all(x.shape==(2,4) and x.dtype==np.float16 for x in arrays.values())
    assert all(len(x._forward_hooks)==0 for x in b)


def test_ablation_only_prefill_position_and_preserves_other_tokens():
    b=blocks();h=torch.ones(2,3,4);u=np.array([1.,0,0,0]);mu=np.zeros(4)
    with PrefillTaps(b,2,selected=4,mean=mu,normal=u) as tap:
        x=h.clone()
        for block in b:x=block(x)
        decoded=torch.ones(2,1,4)
        for block in b:decoded=block(decoded)
    assert torch.equal(h,torch.ones_like(h))
    assert torch.equal(x[:,:2],h[:,:2])
    assert torch.equal(x[:,2,0],torch.zeros(2))
    assert torch.equal(decoded,torch.ones_like(decoded))
    assert tap.ablation_calls==1
    assert (tap.arrays()[4][:,0]==0).all()


def test_missing_tap_decoy_names_block():
    with PrefillTaps(blocks(),2) as tap:pass
    with pytest.raises(ValueError,match='block 2'):tap.arrays()


def test_candidate_dependent_decoy_names_block():
    b=blocks()
    with PrefillTaps(b,2) as tap:
        h=torch.arange(24.).reshape(2,3,4)
        for block in b:h=block(h)
    with pytest.raises(ValueError,match='block 2'):tap.arrays(candidate_pairs=True)


def test_bad_ablation_decoy_and_exception_cleanup():
    b=blocks()
    with pytest.raises(ValueError,match='block 4'):
        with PrefillTaps(b,2,selected=4,mean=np.zeros(4),normal=np.ones(4)):
            h=torch.ones(2,3,4)
            for block in b:h=block(h)
    assert all(not x._forward_hooks for x in b)
    with pytest.raises(ValueError,match='block 7'):PrefillTaps(b,2,selected=7)


def test_guard_fails_before_reader_access():
    def denied():raise RuntimeError('decoy booking denied')
    with pytest.raises(RuntimeError,match='decoy booking'):
        oracle_score(None,[1],[('a','b')],44,denied)
    with pytest.raises(RuntimeError,match='decoy booking'):
        oracle_free(None,None,44,denied)


def test_random_control_matches_each_item_displacement_not_random_projection():
    h=torch.tensor([[[0.,0.,0.,0.],[0.,0.,0.,0.],[3.,20.,0.,0.]],
                    [[0.,0.,0.,0.],[0.,0.,0.,0.],[-2.,7.,0.,0.]]])
    outputs=[]
    for direction,magnitude in [([1.,0,0,0],None),([0.,1,0,0],[1.,0,0,0])]:
        b=blocks()
        with PrefillTaps(b,2,selected=4,mean=np.zeros(4),normal=direction,magnitude_normal=magnitude):
            x=h.clone()
            for block in b:x=block(x)
        outputs.append(x)
    assert torch.equal((outputs[0]-h).norm(dim=-1),(outputs[1]-h).norm(dim=-1))
    assert torch.equal(outputs[1][:,2,0],h[:,2,0])
    assert torch.equal(outputs[0][:,:2],h[:,:2])


@pytest.mark.parametrize('magnitude',[[2.,0,0,0],[0.,1,0,0]])
def test_invalid_random_magnitude_decoy_names_block(magnitude):
    b=blocks()
    with pytest.raises(ValueError,match='block 4'):
        with PrefillTaps(b,2,selected=4,mean=np.zeros(4),normal=[0.,1,0,0],magnitude_normal=magnitude):
            h=torch.ones(2,3,4)
            for block in b:h=block(h)
