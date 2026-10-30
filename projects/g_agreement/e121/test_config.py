import json
from pathlib import Path
import numpy as np
import torch
from projects.g_agreement.e101 import intervention104
from projects.g_agreement.e101.test_e104 import Tiny104,item
from projects.g_agreement.e101.runner import dependencies
dependencies()
from native_nla512 import native_nla

def config():return json.loads(Path(__file__).with_name('nla.json').read_text())

def test_exact_cohort_dose_native_reader_and_no_extra_oracle():
    c=config();assert c['items']==168 and c['base_items']==84 and c['readouts']==168
    assert c['conditions']==['steered','random'] and c['capture']['alpha']==8 and c['capture']['write_block']==40
    assert c['reader']['native_layer']==42 and c['reader']['k']==1 and c['reader']['max_new_tokens']==512
    assert c['labels_on_pod'] is False and c['capture']['read_token_patched'] is False
    assert c['capture']['delta'].startswith('sealed original') and c['reader']['setup'].startswith('load_nla only')

def test_original_u_hook_captures42_and_never_patches_read_token(monkeypatch):
    monkeypatch.setattr(intervention104,'READ_BLOCK',config()['capture']['module_parameters']['READ_BLOCK'])
    class Offset(torch.nn.Module):
        def forward(self,x):return x+7
    m=Tiny104();m.layers[43]=Offset();x=item('U');delta=np.ones((1,4),np.float32)
    _,metrics,h=intervention104.intervene_forward(m,[x['ids']],[x['read_index']],delta,'U',1)
    baseline,patched=m.snapshots;assert np.array_equal(h,patched[42][:,9].numpy()) and not np.array_equal(h,patched[44][:,9].numpy())
    change=(patched[40]-baseline[40])[0].numpy();assert np.allclose(change[1:9],delta[0]) and np.all(change[[0,9]]==0)
    assert metrics[0]['read_site']['block']==42 and len(metrics[0]['injection_sites'])==8
    assert all(not layer._forward_hooks for layer in m.layers)

def test_random_and_steered_apply_sealed_delta_once(monkeypatch):
    monkeypatch.setattr(intervention104,'READ_BLOCK',42)
    for d in (np.array([[8.,0,0,0]],np.float32),np.array([[0,8.,0,0]],np.float32)):
        m=Tiny104();x=item('U');before=d.copy();intervention104.intervene_forward(m,[x['ids']],[9],d,'U',1)
        change=(m.snapshots[1][40]-m.snapshots[0][40])[0].numpy()
        assert np.allclose(change[1:9],d[0],atol=1e-6) and np.array_equal(d,before)


def test_actual_native_nla_greedy512_stop_and_supplied_vectors():
    import contextlib
    from types import SimpleNamespace
    seen=[]
    class Tok:
        pad_token_id=0
        def batch_decode(self,ids,**kw):return ['<explanation>synthetic stated fact</explanation>']*len(ids)
    class AV:
        def generate(self,input_ids,attention_mask,do_sample,max_new_tokens,pad_token_id,stopping_criteria):
            assert not do_sample and max_new_tokens==512 and attention_mask.eq(1).all()
            out=torch.cat((input_ids,torch.ones((len(input_ids),2),dtype=torch.long)),dim=1)
            assert bool(stopping_criteria[0](out,None).all());return out
    @contextlib.contextmanager
    def inject(v):seen.append(v.clone());yield
    nla=SimpleNamespace(tok=Tok(),av=AV(),device='cpu',prompt_ids=[1,2,3],_inject=inject)
    h=np.array([[1,2,3,4],[4,3,2,1]],np.float32);before=h.copy();values=native_nla(nla,h,k=1,batch=8)
    assert len(values)==2 and all(len(x)==1 and x[0]['native_stop']=='</explanation>' and x[0]['native_max_new_tokens']==512 and not x[0]['truncated'] for x in values)
    assert np.array_equal(seen[0].numpy(),h) and np.array_equal(h,before)
