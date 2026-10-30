import json
from types import SimpleNamespace
import pytest
import torch
import candidate81 as C
import parity81 as P
from contract import read


def test_detailed_failure_saved_without_values(tmp_path):
    P.EOS_IDS={9}
    a=[dict(raw='secret generated text',token_ids=[3,9]),dict(raw='same',token_ids=[4,9])]
    b=[dict(raw='different generated text',token_ids=[4,9]),dict(raw='same',token_ids=[4,9,0])]
    with pytest.raises(ValueError,match='differs from serial'):
        P.check_outputs(a,b,tmp_path/'PARITY.json',['opaque1','opaque2'],64)
    result=read(tmp_path/'PARITY.json');r=result['records']
    assert result['status']=='FAIL' and r[0]['first_token_divergence']==0 and not r[0]['raw_text_equal']
    assert r[1]['raw_text_equal'] and not r[1]['token_ids_equal'] and r[1]['first_token_divergence']==2
    assert r[1]['batched_terminal_eos'] and not r[1]['serial_terminal_eos']
    raw=(tmp_path/'PARITY.json').read_text()
    assert 'secret generated text' not in raw and 'different generated text' not in raw and 'token_ids":' not in raw


def test_mixed_length_jobs_keep_tokens_and_all_items():
    xs=[dict(id=str(i),input_ids=[i%9+1]*(i%17+1),max_new_tokens=128 if i<7376 else 32) for i in range(11064)]
    work=C.jobs(xs,64)
    assert len(work)==174 and len(work[0][1])==64
    assert len({len(x['input_ids']) for x in work[0][1]})>=1
    assert sorted(x['id'] for _,chunk in work for x in chunk)==sorted(x['id'] for x in xs)
    assert {id(x) for _,chunk in work for x in chunk}=={id(x) for x in xs}


def test_eight_mixed_items_tiny_hybrid_cpu_parity(tmp_path):
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5ForCausalLM,Qwen3_5TextConfig
    config=Qwen3_5TextConfig(vocab_size=64,hidden_size=32,intermediate_size=64,num_hidden_layers=2,
        num_attention_heads=2,num_key_value_heads=1,head_dim=16,linear_key_head_dim=16,linear_value_head_dim=16,
        linear_num_key_heads=2,linear_num_value_heads=2,layer_types=['linear_attention','full_attention'],
        pad_token_id=0,eos_token_id=63,rope_parameters={'rope_type':'default','rope_theta':10000,
        'partial_rotary_factor':.5,'mrope_section':[1,1,2]})
    torch.manual_seed(7);previous=torch.get_num_threads();torch.set_num_threads(1)
    try:
        b=C.PaddedRuntime(None);b.model=Qwen3_5ForCausalLM(config).eval()
        class Tok:
            pad_token_id=0;eos_token_id=63
            def decode(self,ids,**kwargs):return json.dumps([i for i in ids if i not in (0,63)])
        b.tok=Tok();items=[list(range(1,n+1)) for n in (1,2,3,4,5,7,9,12)]
        for limit in (32,128):
            serial=[b.text([x],limit)[0] for x in items];batch=b.text(items*8,limit)
            P.check_outputs(batch[:8],serial,tmp_path/f'parity{limit}.json',list(map(str,range(8))),64)
            assert all(x==serial[i%8] for i,x in enumerate(batch))
    finally:torch.set_num_threads(previous)


def test_candidate_cannot_run_production(monkeypatch):
    monkeypatch.setattr(C.sys,'argv',['candidate81.py'])
    with pytest.raises(ValueError,match='PROFILE_ONLY'):C.main()
