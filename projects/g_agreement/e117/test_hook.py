from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.e101.runner import dependencies
dependencies()
from mats.readers.olens import OracleLens
from .hook import read

class Layer(torch.nn.Module):
    def forward(self,x):return (x+1,'unchanged tuple tail')
class Tiny(torch.nn.Module):
    def __init__(self,fail=False):
        super().__init__();self.emb=torch.nn.Embedding(8,4);self.layers=torch.nn.ModuleList([Layer(),Layer()]);self.history=[];self.fail=fail
    def get_input_embeddings(self):return self.emb
    def step(self,x):
        for b in self.layers:
            x,tail=b(x);assert tail=='unchanged tuple tail'
        self.history.append(x.clone())
        if self.fail and len(self.history)==2:raise RuntimeError('synthetic failure')
        return x
    def generate(self,inputs_embeds,attention_mask,do_sample,max_new_tokens,use_cache,pad_token_id):
        assert not do_sample and use_cache and max_new_tokens==128
        self.step(inputs_embeds)
        for i in range(3):self.step(torch.ones((len(inputs_embeds),1,4)))
        return torch.tensor([[2,3,4,5]]*len(inputs_embeds))

def lens(m):
    tok=SimpleNamespace(pad_token_id=0,eos_token_id=1,batch_decode=lambda x,**kw:['tiny synthetic readout']*len(x))
    o=OracleLens(m,tok,device='cpu');o._slots[44]=([1,2,3],1);return o

def test_prefill_untouched_every_generated_token_patched_and_tuple_preserved():
    m=Tiny();o=lens(m);h=np.ones((2,4),np.float32);delta=np.array([[1,0,0,0],[-1,0,0,0]],np.float32);before=h.copy()
    expected=o._embed(torch.tensor([[1,2,3]]*2),1,torch.from_numpy(h))+1+1
    result=read(o,h,delta,0,blocks=m.layers)
    assert torch.equal(m.history[0],expected)
    for z in m.history[1:]:assert torch.equal(z,torch.tensor([[[4,3,3,3]],[[2,3,3,3]]]))
    assert np.array_equal(h,before) and np.array_equal(delta,np.array([[1,0,0,0],[-1,0,0,0]],np.float32))
    for i,r in enumerate(result):
        assert len(r['norm_trace'])==3 and [n['absolute_position'] for n in r['norm_trace']]==[3,4,5]
        assert all(n['actual_delta_norm']==1 for n in r['norm_trace'])
        assert r['token_ids']==[2,3,4,5] and r['first_answer_token_selected_before_hook']
    assert all(not b._forward_hooks for b in m.layers)

def test_zero_delta_exact_native_and_signed_doses():
    h=np.ones((1,4),np.float32)
    for alpha in (1,2,4):
        a=Tiny();read(lens(a),h,np.array([[alpha,0,0,0]],np.float32),0,blocks=a.layers)
        b=Tiny();read(lens(b),h,np.array([[-alpha,0,0,0]],np.float32),0,blocks=b.layers)
        assert float(a.history[1][0,0,0]-b.history[1][0,0,0])==2*alpha
    m=Tiny();r=read(lens(m),h,np.zeros_like(h),0,blocks=m.layers)
    assert all(x['norm_ratio']==1 and x['actual_delta_norm']==0 for x in r[0]['norm_trace'])

def test_error_cleanup_and_invalid_vectors():
    m=Tiny(fail=True)
    with pytest.raises(RuntimeError):read(lens(m),np.ones((1,4),np.float32),np.ones((1,4),np.float32),0,blocks=m.layers)
    assert all(not b._forward_hooks for b in m.layers)
    with pytest.raises(ValueError):read(lens(Tiny()),np.zeros((1,4)),np.ones((1,4)),0,blocks=m.layers)


def test_sealed_loader_accepts_owner_row_local_slots_without_reordering(tmp_path):
    from projects.g_agreement.e100.contract import write,sha
    from .runner import load,ROWS
    items=[dict(id=str(i),row=ROWS[i//84],slot=i%84) for i in range(336)]
    h=np.ones((336,5120),np.float32);d=np.zeros((336,3,5120),np.float32);d[:,0,0]=1;d[:,1,0]=-1;d[:,2,1]=1
    np.save(tmp_path/'H44.npy',h);np.save(tmp_path/'DELTAS.npy',d)
    write(tmp_path/'items.json',items);write(tmp_path/'MANIFEST.json',dict(experiment='E117',direction_source='E113 sealed dev fits; no refit',alphas=[1,2,4],arms=['T','W','R'],rows={r:dict(lens_layer=48,gap=1,selection_seal_sha256='synthetic') for r in ROWS}))
    def seal():
        write(tmp_path/'INPUT_SEAL.json',dict(experiment='E117',labels_on_pod=False,files={p.name:sha(p) for p in tmp_path.iterdir() if p.name!='INPUT_SEAL.json'}));return sha(tmp_path/'INPUT_SEAL.json')
    xs,hh,dd,m=load(tmp_path,seal());assert xs==items and np.array_equal(hh,h) and np.array_equal(dd,d)
    for i,x in enumerate(items):x['slot']=i
    write(tmp_path/'items.json',items);assert load(tmp_path,seal())[0]==items
    items[84]['slot']=17;write(tmp_path/'items.json',items)
    with pytest.raises(ValueError,match='item slots'):load(tmp_path,seal())


def test_forecast_covers_unseen_rows_and_short_final_batches():
    from .runner import whole_grid_forecast
    f=whole_grid_forecast(396,1,[2.],1000,3000,1100)
    assert f['pending_calls']==395 and f['remaining_work_bound_seconds']==790
    assert f['projected_total_cap_seconds']==1.25*(100+790)+60
    assert f['status']=='ADMIT'

def test_forecast_uses_global_max_not_mean_and_original_staging():
    from .runner import whole_grid_forecast
    f=whole_grid_forecast(10,2,[2.,10.],1000,2000,1300)
    assert f['max_observed_call_seconds']==10 and f['remaining_work_bound_seconds']==80
    assert f['projected_total_cap_seconds']==1.25*(300+80)+60
    assert f['custody_start_epoch']==1000

def test_forecast_nofit_no_partial_grid_admission_or_clock_reset():
    from .runner import whole_grid_forecast
    f=whole_grid_forecast(396,1,[10.],1000,2800,1500)
    assert f['status']=='NO_FIT' and f['pending_calls']==395 and f['absolute_deadline_epoch']==2800
    with pytest.raises(ValueError):whole_grid_forecast(396,0,[],1000,2800,1500)


def test_completed_full_grid_not_rejected_by_prospective_margin():
    from .runner import whole_grid_forecast
    f=whole_grid_forecast(396,396,[10.],1000,2800,2700)
    assert f['status']=='COMPLETE' and f['pending_calls']==0
