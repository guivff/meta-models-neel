from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import e7_batched as B,e7_parity as P
from projects.g_agreement.understand.cpu import dump,read,sha,seal,verify


@pytest.mark.parametrize('matches,n',[(9,10),(8,10),(47,52),(46,52),(43,52),(0,10)])
def test_parity_rate_is_descriptive_at_any_agreement(matches,n):
    a=[[1]*40 for _ in range(n)];b=[row.copy() for row in a]
    for i in range(matches,n):b[i][0]=9
    r=P.parity_metrics(a,b,['a']*n,['b']*n)
    assert r['accepted'] and r['first32_identical_count']==matches and r['thresholds'] is None
    assert r['raw_text_identical_rate']==0  # full text parity is descriptive, not an extra gate


@pytest.mark.parametrize('first',[0,31,32,77,100])
def test_first_divergence_is_descriptive(first):
    a=[[7]*128 for _ in range(10)];b=[r.copy() for r in a]
    for r in b:r[first]=8
    m=P.parity_metrics(a,b,['a']*10,['b']*10)
    assert m['median_first_divergence_position0_based']==first and m['accepted']


def test_identical_early_EOS_is_no_divergence_and_length_change_is_mismatch():
    r=P.parity_metrics([[7,2]],[[7,2]],['x'],['x'])
    assert r['accepted'] and r['rows'][0]['first_divergence_position0_based'] is None
    assert r['median_first_divergence_position0_based']==128
    r=P.parity_metrics([[7,2]],[[7,7,2]],['x'],['x x'])
    assert r['accepted'] and r['rows'][0]['first_divergence_position0_based']==1


def test_c97_previous_observed_rates_do_not_veto_a_passing_input_audit():
    a=[[1]*128 for _ in range(52)];b=[r.copy() for r in a]
    for row in b[:9]:row[0]=9
    for row in b[9:38]:row[77]=8
    r=P.parity_metrics(a,b,['a']*52,['b']*52)
    assert r['first32_identical_count']==43 and r['median_first_divergence_position0_based']==77
    assert r['all_tokens_identical_rate']==14/52 and r['accepted'] and r['parity_is_descriptive']


def test_left_mask_and_multistream_position_checks():
    import torch
    P.check_left_mask(torch.tensor([[0,0,1,1],[0,1,1,1]]))
    P.check_left_mask(torch.ones((2,4)))  # fixed NLA prompts have zero padding
    with pytest.raises(P.ParityNoFit):P.check_left_mask(torch.tensor([[1,1,0,0]]))
    with pytest.raises(P.ParityNoFit):P.check_left_mask(torch.tensor([[0,1,0,1]]))
    expected=torch.arange(4).expand(2,-1);active=torch.ones_like(expected,dtype=torch.bool)
    assert P.check_positions(expected,expected,active)
    assert P.check_positions(expected[:1],expected,active)  # native shared batch positions
    assert P.check_positions(expected[:1].unsqueeze(0).repeat(4,1,1),expected,active)
    assert P.check_positions(expected.unsqueeze(0).repeat(4,1,1),expected,active)  # Qwen text +3RoPE streams
    with pytest.raises(P.ParityNoFit):P.check_positions(expected+1,expected,active)


def test_consumed_positions_can_be_verified_at_native_rotary_when_forward_omits_them():
    import torch
    nla=SimpleNamespace(tok=SimpleNamespace(padding_side='left'),prompt_ids=[1,7,3],marker=1)
    audit=P.GenerationAudit(nla);ids=torch.tensor([[1,7,3]]*2)
    audit.begin({'input_ids':ids,'attention_mask':torch.ones_like(ids)})
    audit.before_forward(None,(),{'input_ids':ids,'attention_mask':None})
    pos=torch.arange(3).reshape(1,1,3).expand(3,2,3)
    audit.before_rotary(None,(torch.zeros((2,3,4)),pos),{});audit.finish()
    assert audit.report()['calls'][0]['position_steps_verified']==1
    audit.begin({'input_ids':ids,'attention_mask':torch.ones_like(ids)})
    audit.before_forward(None,(),{'input_ids':ids,'attention_mask':None})
    with pytest.raises(P.ParityNoFit):audit.finish()


def test_audit_runs_with_actual_PEFT_generate_and_cleans_up_hooks():
    import common,torch
    from transformers import LlamaConfig,LlamaForCausalLM
    from peft import LoraConfig,get_peft_model
    from mats.readers.nla import NLA
    torch.manual_seed(713)
    model=LlamaForCausalLM(LlamaConfig(vocab_size=24,hidden_size=16,intermediate_size=32,num_hidden_layers=2,
        num_attention_heads=2,num_key_value_heads=2,pad_token_id=0,eos_token_id=2)).eval()
    av=get_peft_model(model,LoraConfig(r=2,lora_alpha=2,target_modules=['q_proj'],task_type='CAUSAL_LM')).eval()
    class Tok:
        pad_token_id=0
        def batch_decode(self,seqs,**kw):return [' '.join(map(str,r.tolist())) for r in seqs]
    nla=NLA(av,Tok(),None,None,{},[1,3,7],2,'cpu');model.model.layers[1].register_forward_hook(nla._hook)
    before=len(model._forward_pre_hooks);r=B.verify_generation_parity(nla,torch.randn(2,16))
    assert r['accepted'] and all(a['forward_steps']>0 for a in r['padding_verification'].values())
    assert len(model._forward_pre_hooks)==before


def test_padding_no_fit_receipt_persists_before_science(tmp_path,monkeypatch):
    h=np.zeros((10,2));native=SimpleNamespace(tok=SimpleNamespace())
    def capture(n,h,batch,**kwargs):raise P.ParityNoFit('NO_FIT: invalid attention mask')
    monkeypatch.setattr(B,'generation_with_tokens',capture)
    with pytest.raises(P.ParityNoFit):B.verify_generation_parity(native,h,tmp_path/'GENERATION_PARITY.json')
    verify(tmp_path,'GENERATION_PARITY_SEAL.json')
    assert read(tmp_path/'GENERATION_PARITY.json')['status']=='NO_FIT'
    assert 'NO_FIT' in (tmp_path/'PARITY_RESULTS.md').read_text()


def test_failed_input_audit_is_terminal_NO_FIT_with_zero_science(tmp_path,monkeypatch):
    from projects.g_agreement.understand.tests.test_e7_batched import bare_gate
    from projects.g_agreement.understand.e7_batched_runtime import PHASES
    g=bare_gate(tmp_path/'e7',{k:3 for k in PHASES})
    class Collection:
        def __init__(self,*args):pass
        def setup(self):
            r={'status':'NO_FIT','accepted':False,'error':'invalid attention mask','n':10}
            P.save_report(tmp_path/'GENERATION_PARITY.json',r)
            raise P.ParityNoFit('NO_FIT: invalid attention mask')
        def generation(self,*args):raise AssertionError('production must not start')
    monkeypatch.setattr(B,'Collection',Collection)
    resident=SimpleNamespace(current=None,events=[],loads={'decoder':1,'nla':1})
    B.execute(SimpleNamespace(out=tmp_path),resident,g,{})
    assert read(tmp_path/'solo.json')['status']=='NO_FIT'
    run=read(tmp_path/'e7/run.json');assert run['elapsed_science_seconds']==0 and run['first_science_epoch'] is None
    verify(tmp_path);verify(tmp_path,'GENERATION_PARITY_SEAL.json')


def test_results_append_does_not_recompute_or_change_scientific_metrics(tmp_path,monkeypatch):
    import sys
    collection=tmp_path/'collection';collection.mkdir();analysis=tmp_path/'analysis';analysis.mkdir()
    r=P.parity_metrics([[1]*40]*10,[[1]*40]*10,['a']*10,['a']*10)
    P.save_report(collection/'GENERATION_PARITY.json',r)
    seal(collection,['GENERATION_PARITY.json','GENERATION_PARITY_SEAL.json'],'TEST_COLLECTION')
    dump(analysis/'metrics.json',{'original':True});(analysis/'RESULTS.md').write_text('Frozen prediction and scientific assessment.\n')
    seal(analysis,['metrics.json','RESULTS.md'],'EXPLORATORY_E7_ANALYSIS_SEALED');original=sha(analysis/'metrics.json')
    monkeypatch.setattr(sys,'argv',['parity','--collection',str(collection),'--results',str(analysis/'RESULTS.md')]);P.main()
    assert sha(analysis/'metrics.json')==original
    assert 'First32-token agreement: 10/10' in (analysis/'RESULTS.md').read_text()
    verify(analysis)
