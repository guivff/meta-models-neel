import numpy as np
import torch
from projects.g_agreement.e101.test_e101 import Tiny
from projects.g_agreement.e101.anomaly212 import observe_patch,plain_behaviour
from projects.g_agreement.e101.acquisition import behaviour


def test_observer_proves_real_mutation_both_blocks_and_cleans_hooks():
    for block in (42,44):
        model=Tiny();model.layers.append(torch.nn.Identity());model.config.num_hidden_layers=46;xs=[dict(base_id='dev',row='format_plan',ids=[1,2],read_index=1,block=block,candidate_ids=[[[3],[4]]])]
        h=model.emb(torch.tensor([2])).detach().numpy()
        before,after=observe_patch(model,xs,h+2)
        assert np.array_equal(before,h) and np.allclose(after-before,2)
        assert all(not b._forward_hooks and not b._forward_pre_hooks for b in model.layers)
        # A zero delta must fail the nonzero finding, so a no-op cannot pass silently.
        before,after=observe_patch(model,xs,h)
        assert np.linalg.norm(after-before)==0


def test_plain_baseline_matches_natural_replacement_full_frozen_score():
    model=Tiny();x=dict(base_id='dev',row='nesting_depth',ids=[1,2],read_index=1,block=44,candidate_ids=[[[3],[3,4]]])
    natural=model.emb(torch.tensor([2])).detach().numpy()
    plain=plain_behaviour(model,[x])[0]
    patched=behaviour(model,[x],natural,'continuation')[0]
    assert plain['pair_logprobs']==patched['pair_logprobs']
    assert plain['pair_logprobs'][0][0]>plain['pair_logprobs'][0][1]
