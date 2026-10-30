import json
from pathlib import Path
import numpy as np,torch
from projects.g_agreement.e127.test_runner import Tiny,Tok,seq
from projects.g_agreement.e128.runner import capture_answer_batch,batches,LAYERS
from projects.g_agreement.e128.inputs import load
from projects.g_agreement.e100.contract import sha

def item(alpha=2,condition='steered'):
    return dict(id='synthetic',row='fact_recall',alpha=alpha,condition=condition,ids=seq()[0],read_index=11,candidate_ids=[[[3],[4]]])

def test_unchanged_U_hook_greedy_three_captures_both_blocks_and_live_norms():
    for alpha in (2,4):
        for condition in ('steered','random'):
            m=Tiny();d=np.array([[.2,-.4,.1,.3]],np.float32)*alpha;before=d.copy()
            r=capture_answer_batch(m,Tok(),[item(alpha,condition)],d)
            assert set(r['captures'])=={44,52}and len(r['answers'][0]['token_ids'])==3 and m.calls==4
            natural=m.snapshots[0][40][0,:12]
            for state in m.snapshots[1:]:
                diff=state[40][0,:12]-natural
                assert torch.allclose(diff[3:11],torch.from_numpy(d).expand(8,4),atol=1e-6)
                assert torch.equal(diff[[0,1,2,11]],torch.zeros((4,4)))
            for L,h in r['captures'].items():assert np.array_equal(h,m.snapshots[1][L][:,11].numpy())
            assert r['injection_metrics'][0]['injection_norm_after']!=r['injection_metrics'][0]['read_norm_after']
            assert 'pair_logprobs'in r['answers'][0]and np.array_equal(before,d)
            assert all(not b._forward_hooks for b in m.layers)

def test_actual_packet_dose_scaling_same_random_directions_original_prompts_pairs():
    root=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e128-inputs-v1/inputs');xs,d,m=load(root,sha(root/'INPUT_SEAL.json'));assert sum(map(len,batches(xs)))==336
    source=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops/e104U_test_bind/fact_recall');parent={x['id']:x for x in json.loads((source/'items.json').read_text())};raw=np.load(source/'deltas.npy',allow_pickle=False)
    ptr=json.loads((root.parent/'cpu_only/ORIGINAL_POINTERS.PRIVATE.json').read_text());assert len(ptr)==336
    for x,p in zip(xs,ptr):
        o=parent[p['original_item_id']];assert x['ids']==o['ids']and x['read_index']==o['read_index']and x['candidate_ids']==o['candidate_ids']
        assert np.array_equal(d[x['delta_index']],raw[o['delta_index']]*(x['alpha']/8))
    for alpha in (2,4):
        by={(x['base_id'],x['condition']):x['delta_index']for x in xs if x['alpha']==alpha}
        for base in {x['base_id']for x in xs}:assert np.isclose(np.linalg.norm(d[by[base,'steered']]),np.linalg.norm(d[by[base,'random']]),rtol=1e-6)
    assert all(not {'label','target','old_value','new_value'}&set(x)for x in xs)

def test_full_84_by2dose_by2control_by2reader_cells_and_no_new_alpha8():
    root=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e128-inputs-v1/inputs');xs,d,m=load(root,sha(root/'INPUT_SEAL.json'))
    assert m['total_readouts']==672 and m['steered_readouts']==m['random_readouts']==336 and {x['alpha']for x in xs}=={2,4}
    assert len({x['base_id']for x in xs})==84 and LAYERS==(44,52)
    c=json.loads(Path(__file__).with_name('config.json').read_text());assert c['launch']['priority']=='LAST'and c['launch']['planning_GPU_hours']==.4
    assert c['launch']['creation_cutoff']=='2026-10-30T04:00:00+01:00'and c['launch']['stop_and_seal_cutoff']=='2026-10-30T08:00:00+01:00'
