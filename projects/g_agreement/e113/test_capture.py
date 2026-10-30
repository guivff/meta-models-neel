from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.e101.runner import dependencies
dependencies()
from mats.readers.olens import OracleLens
from projects.g_agreement.e113.capture import capture_lens

class Layer(torch.nn.Module):
    def forward(self,x):return x+.1*torch.cumsum(x,dim=1)
class Tiny(torch.nn.Module):
    def __init__(self,fail=False):
        super().__init__();torch.manual_seed(7);self.emb=torch.nn.Embedding(8,4);self.layers=torch.nn.ModuleList([Layer() for _ in range(3)]);self.config=SimpleNamespace(num_hidden_layers=3);self.history=[];self.fail=fail
    def get_input_embeddings(self):return self.emb
    def forward(self,inputs_embeds,attention_mask,use_cache=False,logits_to_keep=1):
        x=inputs_embeds;states=[]
        for b in self.layers:x=b(x);states.append(x.detach().clone())
        self.history.append(states)
        if self.fail:raise RuntimeError('synthetic crash')
        return SimpleNamespace(logits=torch.cat([x,x],dim=-1)[:,-logits_to_keep:])
    def generate(self,inputs_embeds,attention_mask,do_sample,max_new_tokens,pad_token_id):
        assert not do_sample and max_new_tokens==1
        return self.forward(inputs_embeds,attention_mask).logits[:,-1].argmax(-1)[:,None]


def lens(model):
    o=OracleLens(model,SimpleNamespace(pad_token_id=0,eos_token_id=1),device='cpu')
    o._slots[44]=([1,2,3],1);return o


def test_actual_native_embedding_and_generated_position_all_layers():
    m=Tiny();o=lens(m);h=np.array([[1,2,3,4],[4,3,2,1]],np.float32);before=h.tobytes()
    states,tokens,meta=capture_lens(o,h)
    assert states.shape==(2,3,2,4) and states.dtype==np.float32 and h.tobytes()==before
    assert len(m.history)==2 and meta['injected_position']==1 and meta['first_generated_position']==3
    for layer in range(3):
        assert np.array_equal(states[:,layer,0],m.history[0][layer][:,1].numpy())
        assert np.array_equal(states[:,layer,1],m.history[1][layer][:,3].numpy())
    assert tokens.shape==(2,1) and all(not b._forward_hooks for b in m.layers)
    native=o._embed(torch.tensor([[1,2,3]]*2),1,torch.from_numpy(h))
    assert torch.allclose(native[:,1],16000*torch.from_numpy(h)/torch.linalg.vector_norm(torch.from_numpy(h),dim=1,keepdim=True))


def test_failure_removes_all_lens_hooks():
    m=Tiny(fail=True)
    with pytest.raises(RuntimeError):capture_lens(lens(m),np.ones((1,4),np.float32))
    assert all(not b._forward_hooks for b in m.layers)


def test_eos_first_token_still_has_real_processed_state():
    m=Tiny();m.generate=lambda **kw:(m.forward(kw['inputs_embeds'],kw['attention_mask']),torch.ones((len(kw['inputs_embeds']),1),dtype=torch.long))[1]
    states,tokens,meta=capture_lens(lens(m),np.ones((1,4),np.float32))
    assert tokens[0,0]==1 and states.shape==(1,3,2,4) and len(m.history)==2


def test_native_container_identity_and_stop_receipt():
    from projects.g_agreement.e113.protocol import native_identity,stop_result
    assert native_identity(b'OTHER=unused\0RUNPOD_POD_ID=actualpod\0')=='actualpod'
    assert native_identity(b'OTHER=unused\0')==''
    assert stop_result({'podStop':{'id':'actualpod','desiredStatus':'EXITED'}},'actualpod')['desiredStatus']=='EXITED'
    with pytest.raises(ValueError):stop_result({'podStop':{'id':'wrong'}},'actualpod')


def test_preload_cost_does_not_reset_total_custody_allowance():
    from projects.g_agreement.e113.protocol import cap_valid
    a=dict(prior_seconds=101,cap_seconds=1339,pod_created_epoch=1000,absolute_deadline_epoch=2339)
    assert cap_valid(a)
    assert not cap_valid(dict(a,cap_seconds=1440,absolute_deadline_epoch=2440))
    assert not cap_valid(dict(a,prior_seconds=-1))
