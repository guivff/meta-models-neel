from pathlib import Path
import json,numpy as np,torch,pytest
from projects.g_agreement.e101.runner import dependencies
dependencies()
from projects.g_agreement.e101.test_e104 import Tiny104,Layer
class Tiny(Tiny104):
    def __init__(self):
        super().__init__();self.layers=torch.nn.ModuleList([Layer(i)for i in range(64)]);self.config.num_hidden_layers=64
def seq():return [list(range(1,13))]
from projects.g_agreement.e127.runner import capture_answer_batch,greedy_three,batches,LAYERS
from projects.g_agreement.e127.inputs import load
from projects.g_agreement.e100.contract import sha

class Tok:
    eos_token_id=None
    def decode(self,ids,skip_special_tokens):return ' '.join(map(str,ids))

def item():return dict(id='synthetic',base_id='synthetic',row='fact_recall',condition='context_update',ids=seq()[0],read_index=11,candidate_ids=[[[3],[4]]])

def test_original_unhooked_capture_actual44_52_60_and_three_greedy_steps():
    m=Tiny();x=item();before=m.emb(torch.tensor([x['ids']])).detach();result=capture_answer_batch(m,Tok(),[x])
    assert set(result['captures'])==set(LAYERS)and result['intervention_installed']is False
    assert len(result['answers'][0]['token_ids'])==3 and m.calls==4
    for l,h in result['captures'].items():assert np.array_equal(h,m.snapshots[0][l][:,11].numpy())
    assert all(torch.equal(s[40][0,:12],before[0])for s in m.snapshots)
    assert all(not b._forward_hooks for b in m.layers)

def test_greedy_respects_eos_without_filling_tokens_or_sampling():
    class EOS(Tok):eos_token_id=0
    m=Tiny()
    def fixed(sequences,positions,step):
        assert step==0;return torch.tensor([[[5.,0.,0.,0.,0.]]])
    r=greedy_three(m,EOS(),[item()],fixed);assert r[0]['token_ids']==[0]and m.calls==0

def test_actual_packet_cpu_targets_and_exact_length_unrelated_neutral():
    root=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e127-inputs-v2/inputs');xs,manifest=load(root,sha(root/'INPUT_SEAL.json'))
    jj=list(batches(xs));assert sum(map(len,jj))==252 and manifest['fallback_value_count']==0
    ptr=json.loads((root.parent/'cpu_only/LABELS.PRIVATE.json').read_text());assert len(ptr)==84
    for x in ptr:
        assert x['entity']!=x['neutral_entity']and x['new_value']!=x['old_value']and x['prefix_tokens']>0
        assert x['new_value_source']=='original E104 sealed steer target'
    assert all(not {'old_value','new_value','label','target'}&set(x)for x in xs)

def test_original_e104_targets_none_prompts_and_frozen_pairs_unchanged():
    root=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e127-inputs-v2/inputs');xs,_=load(root,sha(root/'INPUT_SEAL.json'))
    ptr=json.loads((root.parent/'cpu_only/LABELS.PRIVATE.json').read_text());source=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops/e104U_test_bind/fact_recall');parent={x['base_id']:x for x in json.loads((source/'items.json').read_text())if x['condition']=='steered'}
    by={x['id']:x for x in xs}
    for p in ptr:
        original=parent[p['original_base_id']];none=by[p['condition_ids']['none']]
        assert none['ids']==original['ids']and none['read_index']==original['read_index']
        assert all(by[ident]['candidate_ids']==original['candidate_ids']for ident in p['condition_ids'].values())

def test_new_schedule_no_hooks_full_readout_census_and_operator():
    c=json.loads(Path(__file__).with_name('config.json').read_text())
    assert c['hook_enabled']is False and c['cells']==252 and c['oracle_readouts']==756 and c['oracle_layers']==[44,52,60]
    assert c['launch']['creation_cutoff']=='2026-10-30T04:00:00+01:00'and c['launch']['stop_and_seal_cutoff']=='2026-10-30T08:00:00+01:00'
    assert c['labels_on_pod']is False and c['launch']['owner']=='Track Q'and c['launch']['planning_GPU_hours']==.5
