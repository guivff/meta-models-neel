import copy,json,shutil
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.e127.test_runner import Tiny
from projects.g_agreement.e136 import runner as r
from projects.g_agreement.e100.contract import sha
ROOT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e136-inputs-v1/inputs')

def item(ident='opaque'):
    return dict(id=ident,ids=list(range(1,13)),read_index=11,candidate_ids=[[[3],[4]]])

def test_literal_original_capture_code_and_single_forward_pair_logits_no_edits():
    assert r._natural.__code__ is r.runner109.natural_capture.__code__
    m=Tiny();xs=[item()];result=r.capture_batch(m,xs)
    assert m.calls==1 and result['intervention_installed']is False and result['generation_calls']==0
    assert set(result['captures'])=={44,52,60}
    for L,h in result['captures'].items():assert np.array_equal(h,m.snapshots[0][L][:,11].numpy())
    logits=torch.cat([m.snapshots[0][63][:,-1]]*8,dim=-1)
    expected=r.pairs_from_logits(logits,xs)[0]
    assert result['pair_records'][0]['pair_logits']==expected['pair_logits']
    assert result['pair_records'][0]['pair_logprobs']==expected['pair_logprobs']
    assert result['pair_records'][0]['first_greedy_token_id']==int(logits.argmax(-1)[0])
    natural=m.emb(torch.tensor([xs[0]['ids']])).detach()
    assert torch.equal(m.snapshots[0][40],natural)
    assert not m._forward_hooks and all(not b._forward_hooks for b in m.layers)


def test_exception_removes_all_observation_handles():
    m=Tiny();m.fail_call=1
    with pytest.raises(RuntimeError):r.capture_batch(m,[item()])
    assert not m._forward_hooks and all(not b._forward_hooks for b in m.layers)


def test_batch_inference_pair_ids_and_original_order():
    xs=[item('first'),item('second')];m=Tiny();out=r.capture_batch(m,xs)
    assert m.calls==1 and [v['id']for v in out['pair_records']]==['first','second']
    assert all(v.shape==(2,4)for v in out['captures'].values())

@pytest.mark.parametrize('field',['label','cue','split','correct','pair_id'])
def test_cpu_label_fields_refused(field):
    x=item();x[field]='private'
    with pytest.raises(ValueError,match='public'):r.validate_items([x])


def test_no_candidate_truncation_or_role_order_guess():
    for pairs in [[[[3,4],[5]]],[[[4],[3]]],[[[3],[4]],[[5],[6]]]]:
        x=item();x['candidate_ids']=pairs
        with pytest.raises(ValueError):r.validate_items([x])


def test_mixed_length_refused_before_forward():
    x=item('second');x['ids'].append(13);x['read_index']=12;m=Tiny()
    with pytest.raises(ValueError):r.capture_batch(m,[item(),x])
    assert m.calls==0


def test_complete_actual_bank_original_token_prefix_and_batch_census():
    xs,manifest=r.load(ROOT,r.BANK_SHA)
    assert len(xs)==800 and len(list(r.batches(xs,8)))==116
    original=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e136-bank-v2')
    assert xs==json.loads((original/'inputs/items.json').read_text())
    assert sha(ROOT.parent/'inputs.tar.gz')==sha(original/'PUBLIC_INPUTS.tar.gz')
    assert all(len({len(x['ids'])for x in job})==1 for job in r.batches(xs))
    assert sum(map(len,r.batches(xs)))==800 and manifest['pairs']==400
    with pytest.raises(ValueError):r.load(ROOT,'0'*64)


def test_modified_public_member_rejected(tmp_path):
    shutil.copytree(ROOT,tmp_path/'inputs');f=tmp_path/'inputs/items.json';f.write_text(f.read_text()+' ')
    with pytest.raises(ValueError):r.load(tmp_path/'inputs',r.BANK_SHA)

@pytest.mark.parametrize('L',[44,52,60])
def test_original_native_oracle_sweep_and_no_vector_change(L):
    class Oracle:
        def verbalize(self,vectors,layer,k,sampling,batch):
            assert layer==L and k==1 and batch==8
            assert sampling.max_new_tokens==128 and sampling.temperature==0 and sampling.top_p==1
            assert vectors.shape==(2,5120)
            return [['synthetic first'],['synthetic second']]
    rt=SimpleNamespace(readers=SimpleNamespace(oracle=Oracle()),sweep_batch_size=8)
    v=np.ones((2,5120),np.float32);before=v.copy()
    result=r.oracle_batch(rt,v,L)
    assert [x['text']for x in result]==['synthetic first','synthetic second']
    assert all(x['native_max_new_tokens']==128 for x in result)and np.array_equal(v,before)


def test_config_registered_scope_operator_and_kill_cutoffs():
    c=json.loads(Path(__file__).with_name('config.json').read_text())
    assert c['cap_seconds']==3600 and c['oracle_readouts']==2400 and not c['intervention_hook']
    assert c['packet_kill_cutoff_utc']=='2026-10-30T06:00:00Z'and c['creation_cutoff_utc']=='2026-10-30T10:00:00Z'
    assert c['judging']['max_USD']==2 and c['no_partial_reporting']is True
