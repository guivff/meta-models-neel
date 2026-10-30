from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.e100.contract import write,sha
from .reader import contract,embed,carrier,lora_state,nondegenerate,CONTRACT_PATH
from .runner import production_gate

def test_frozen_checkpoint_base_read_contract():
    c=contract();assert c['checkpoint']['revision']=='6ef38c85bc1096ea6e5b8e88e0c0c28cf6f9d30f'
    assert c['checkpoint']['subfolder']=='final_olens_lensB/lens_rl_step150' and c['checkpoint']['remote_code'] is False
    assert c['base']['revision']=='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
    assert c['read']['alpha']==1000 and c['read']['transform']=='unit' and c['read']['prompt_kind']=='concepts_raw'
    assert c['read']['max_new_tokens']==128 and c['read']['do_sample'] is False

class Tiny(torch.nn.Module):
    def __init__(self):super().__init__();self.emb=torch.nn.Embedding(8,4)
    def get_input_embeddings(self):return self.emb

def test_slot_replacement_unit_alpha1000_no_other_embedding_changes():
    m=Tiny();ids=torch.tensor([[1,2,3],[1,2,3]]);h=np.array([[3,4,0,0],[0,0,6,8]],np.float32);before=h.copy();e=embed(m,ids,1,h)
    assert torch.allclose(e[:,1],torch.tensor([[600,800,0,0],[0,0,600,800]],dtype=e.dtype))
    assert torch.allclose(e[:,1].norm(dim=-1),torch.tensor([1000.,1000.]))
    assert torch.equal(e[:,0],m.emb(ids)[:,0]) and torch.equal(e[:,2],m.emb(ids)[:,2]) and np.array_equal(h,before)
    with pytest.raises(ValueError):embed(m,ids,1,np.zeros_like(h))

class Tok:
    def __init__(self):self.calls=[]
    def __call__(self,char,**kw):return {'input_ids':[ord(char)-0x3200+2]}
    def apply_chat_template(self,messages,**kw):
        self.calls.append((messages,kw));char=messages[0]['content'].split('<activation>')[1][0];ident=ord(char)-0x3200+2
        return [1,ident,ident,5] if ident==2 else [1,ident,5]

def test_exact_layer_chat_prompt_and_full_context_slot_uniqueness():
    tok=Tok();ids,slot=carrier(tok,52);assert ids==[1,3,5] and slot==1 and len(tok.calls)==2
    assert 'layer 52' in tok.calls[-1][0][0]['content']
    assert tok.calls[-1][1]==dict(tokenize=True,add_generation_prompt=True,enable_thinking=False)
    with pytest.raises(ValueError):carrier(tok,64)

def test_exact_tensor_prefix_buffers_and_mapping():
    s={'injector._layer_norms':torch.ones(64)*1000,'injector._scale':torch.tensor(1.),'lm.base_model.model.model.layers.0.x.lora_A.default.weight':torch.ones(16,4)}
    assert set(lora_state(s))=={'base_model.model.model.layers.0.x.lora_A.default.weight'}
    s['unexpected']=torch.tensor(1)
    with pytest.raises(ValueError):lora_state(s)

def test_precommitted_nondegeneracy_gate():
    assert nondegenerate(dict(text='- French language',token_ids=[2,3,4]))
    for v in [dict(text='',token_ids=[]),dict(text='word word word',token_ids=[1,1]),dict(text='two words',token_ids=[2]*16)]:assert not nondegenerate(v)

def test_production_refuses_absent_failed_or_mismatched_smoke(tmp_path):
    with pytest.raises(ValueError):production_gate(None,None,'source')
    write(tmp_path/'READOUTS.json',[dict(text='two words',token_ids=[2,3])]*4)
    s=dict(experiment='E119',status='PASS',items=4,split='dev',contract_sha256=sha(CONTRACT_PATH),weights_sha256=contract()['checkpoint']['weights_sha256'],source_sha256='source',files={'READOUTS.json':sha(tmp_path/'READOUTS.json')})
    write(tmp_path/'SMOKE_SEAL.json',s);production_gate(tmp_path,sha(tmp_path/'SMOKE_SEAL.json'),'source')
    with pytest.raises(ValueError):production_gate(tmp_path,sha(tmp_path/'SMOKE_SEAL.json'),'other source')
    s['status']='NOT_RUN_OPERATIONAL_FAILED_SMOKE';write(tmp_path/'SMOKE_SEAL.json',s)
    with pytest.raises(ValueError):production_gate(tmp_path,sha(tmp_path/'SMOKE_SEAL.json'),'source')
