import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import followup_packed as P
from projects.g_agreement.understand import followup_runtime as R
from projects.g_agreement.understand.cpu import dump,sha,seal,verify


def test_projection_auroc_ties_and_orientation():
    from projects.g_agreement.understand.e1_projection_auroc import projection_auroc
    assert projection_auroc([1,1,1,1],[1,1,0,0])==.5
    assert projection_auroc([0,1,2,3],[1,1,0,0])==0
    assert projection_auroc([0,1,2,3],[0,0,1,1])==1


def test_greedy16_preserves_eos_argmax_without_stopping_or_padding():
    import torch
    class Tok:
        pad_token_id=0;eos_token_id=2
        def decode(self,ids,**kw):assert kw['skip_special_tokens'] is False;return 'RAW_EOS'*len(ids)
    class Model:
        device='cpu'
        def generate(self,input_ids,attention_mask,**kw):
            assert kw['max_new_tokens']==16 and kw['min_new_tokens']==0
            assert kw['eos_token_id'] is None and kw['forced_eos_token_id'] is None
            assert kw['do_sample'] is False and kw['num_beams']==1
            return torch.cat([input_ids,torch.full((len(input_ids),16),2)],dim=1)
    result=P.greedy16(Model(),Tok(),[{'id':'x','feature':'f','ids':[1,2]}])
    assert result[0]['ids']==[2]*16 and result[0]['text']=='RAW_EOS'*16
    with pytest.raises(ValueError,match='padding'):P.greedy16(Model(),Tok(),[{'ids':[1]},{'ids':[1,2]}])


def test_window_model_never_fits_test_vocabulary():
    from projects.g_agreement.understand.followup_analyse import window_scores
    train=['aaa','aab','bbb','bba']*3;y=[1,1,0,0]*3
    scores,n=window_scores(train,y,['aaa','bbb','UNSEEN_UNIQUE_TEST_SYMBOL'])
    _,m=window_scores(train,y,['aaa'])
    assert n==m and scores[0]>scores[1]


def test_oracle_reuses_target_backbone_without_loading_base_again(monkeypatch):
    import common
    from mats.readers import olens
    class Model:
        def to(self,device):assert device=='cuda';return self
    model=Model();tok=object();calls=[];result=object()
    def attach(**kw):calls.append(kw);return result
    monkeypatch.setattr(olens,'load_olens',attach)
    resident=object.__new__(P.Residents);resident.objects={'target':(model,tok)};resident.assets={'olens':'adapter'};resident.events=[]
    assert resident.load('olens') is result
    assert calls==[{'model':model,'tok':tok,'lora_dir':'adapter'}]
    assert 'target' not in resident.objects
    with pytest.raises(RuntimeError,match='no base reload'):resident.load('olens')


def test_gate_caps_source_integrity_and_no_clock_reset(tmp_path,monkeypatch):
    import time
    now=time.time();monkeypatch.setattr(R,'ROOT',tmp_path);monkeypatch.setattr(R,'STOP',now+5000)
    for name in [R.BRIEF,*R.REQUIRED]:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('frozen')
    forecasts={k:100. for k in ['olens_native','olens_context','nla_native','nla_context']}
    a={'issuer':'integrator','experiment':'E12','gpu_count':1,'pod_id':'fake','external_hardstop_verified':True,'hold_renewer_verified':True,'brief_registered':True,'brief_pushed':True,'brief_sha256':sha(tmp_path/R.BRIEF),'source_files':{n:sha(tmp_path/n) for n in R.REQUIRED},'allocated_gpu_seconds':900.,'previous_gpu_seconds':0.,'smoke_forecast_seconds':400.,'deadline_epoch':now+3000,'provider_created_epoch':now-10,'packed_science_seconds':1500.,'setup_allowance_seconds':2400.,'phase_forecast_seconds':forecasts,'forecast_method':'warmed_median_next_3_real_units'}
    path=tmp_path/'a.json';dump(path,a);g=R.Gate(path,'E12');g.setup_callback=lambda:None;g.start();started=g.started;g.start();assert g.started==started
    assert g.allocation==360  # no guessed or separately loaded forecast is used
    g.state_path=tmp_path/'CLOCK.json'
    g.measured('olens_native',[1.,3.,2.],50,3);assert g.phases['olens_native']['median_seconds']==2
    assert g.allocation==510
    g.measured('olens_context',[2.,2.,2.],50,3)
    assert g.allocation==660 and g.started==started
    assert json.loads(g.state_path.read_text())['first_science_epoch']==g.first_science_epoch
    assert json.loads(g.state_path.read_text())['science_cap_seconds']==660
    with pytest.raises(ValueError,match='repeated'):g.measured('olens_context',[2.,2.,2.],50,3)
    dump(path,{**a,'allocated_gpu_seconds':4000.})
    with pytest.raises(ValueError,match='cap'):R.Gate(path,'E12')
    dump(path,a);(tmp_path/next(iter(R.REQUIRED))).write_text('changed')
    with pytest.raises(ValueError,match='source'):R.Gate(path,'E12')


def test_context_scoring_matches_both_native_readers_and_true_no_injection():
    import common,torch
    from mats.readers.olens import OracleLens
    from mats.readers.nla import NLA,paired_logodds_templates
    class Tok:
        pad_token_id=0
        def encode(self,s,**kwargs):return {'A':[3,5],'B':[4],'<explanation>\n':[6]}.get(s,[1])
        def apply_chat_template(self,turns,**kw):return [1,9,7,2] if '<source_text>' in turns[0]['content'] else [1,7,2]
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__();self.embed=torch.nn.Embedding(12,4);self.head=torch.nn.Linear(4,12,bias=False)
            self.model=torch.nn.Module();self.model.layers=torch.nn.ModuleList([torch.nn.Identity(),torch.nn.Identity()])
        def get_input_embeddings(self):return self.embed
        def forward(self,input_ids=None,inputs_embeds=None,attention_mask=None,logits_to_keep=None,**kw):
            h=self.embed(input_ids) if inputs_embeds is None else inputs_embeds
            for block in self.model.layers:h=block(h)
            self.last=h.detach().clone();logits=self.head(h.cumsum(1))
            return SimpleNamespace(logits=logits[:,-logits_to_keep:])
    torch.manual_seed(3);tok=Tok();model=Model();h=torch.tensor([[1.,2,0,0],[-1.,1,0,2]])
    records=[{'text':'source'},{'text':'source'}];spec={'request':'NATIVE','marker_token_id':7};pair=('A','B')
    ol=OracleLens(model,tok,alpha=2.,device='cpu');ol._slots[44]=([1,7,2],1)
    native=ol.paired_logodds(h,44,*pair).numpy()
    custom=P.context_pair(ol,'olens',records,h,spec,pair,'activation_only')
    assert np.allclose(native,custom,atol=1e-6)
    P.context_pair(ol,'olens',records,None,spec,pair,'text_only')
    assert torch.allclose(model.last[:,2,:],model.embed(torch.tensor([7]*4)))
    P.context_pair(ol,'olens',records,h,spec,pair,'text_activation')
    expected=(2*h/h.norm(dim=1,keepdim=True)).repeat_interleave(2,0)
    assert torch.allclose(model.last[:,2,:],expected)
    nla=NLA(model,tok,None,None,{},[1,7,2],1,'cpu');model.model.layers[1].register_forward_hook(nla._hook)
    native=paired_logodds_templates(nla,h,[pair]).numpy()[0]
    custom=P.context_pair(nla,'nla',records,h,spec,pair,'activation_only')
    assert np.allclose(native,custom,atol=1e-6)
    P.context_pair(nla,'nla',records,h,spec,pair,'text_activation')
    original=model.embed(torch.tensor([7]*4));v=h.repeat_interleave(2,0)
    expected=original+original.norm(dim=1,keepdim=True)*(v/(v.norm(dim=1,keepdim=True)+1e-9))
    assert torch.allclose(model.last[:,2,:],expected)
    P.context_pair(nla,'nla',records,None,spec,pair,'text_only')
    assert torch.allclose(model.last[:,2,:],original)
    assert len(model.model.layers[1]._forward_hooks)==1  # custom hook removed; native hook preserved


def test_packed_order_one_load_each_and_continuation_sealed_before_ar(tmp_path,monkeypatch):
    import torch
    from projects.g_agreement.w_claims import ar as AR
    from projects.g_agreement.understand.e12 import ARMS
    inp=tmp_path/'inputs';out=tmp_path/'out';out.mkdir();b=inp/'e1b';b.mkdir(parents=True);e=inp/'e12';e.mkdir()
    items=[{'id':str(i),'feature':'f','ids':[i+1]} for i in range(80)]
    P.jsonl(b/'items.input.jsonl',items);dump(b/'test_ids.json',[r['id'] for r in items[40:]])
    dump(b/'generation_units.json',[{'indices':list(range(s,s+16)),'length':1} for s in range(0,80,16)])
    dump(b/'INPUT_SEAL.json',{'files':{}})
    es=[{'id':str(i),'feature':'f','text':'source','wrong_activation_index':39-i} for i in range(40)]
    P.jsonl(e/'items.input.jsonl',es);dump(e/'templates.json',{'f':{'olens':[['A','B'],['A','B']],'nla':[['A','B'],['A','B']]}})
    modeldir=tmp_path/'model';modeldir.mkdir();(modeldir/'tokenizer.json').write_text('tok')
    nladir=tmp_path/'nla';(nladir/'av_base').mkdir(parents=True);(nladir/'av_base/tokenizer.json').write_text('tok')
    specs={n:{'request':'NATIVE','marker_token_id':7,'tokenizer_json_sha256':sha(modeldir/'tokenizer.json')} for n in ['olens','nla']};dump(e/'provenance.json',{'native_carriers':specs})
    for name in ['olens','nla']:
        units={'native':[{'arm':ARMS[0],'feature':'f','indices':list(range(s,min(40,s+8)))} for s in range(0,40,8)],'context':[{'arm':arm,'feature':'f','indices':list(range(s,min(40,s+8)))} for arm in ARMS[1:] for s in range(0,40,8)]}
        dump(e/(name+'_units.json'),units)
    for layer in [42,44]:np.save(e/f'acts{layer}.npy',np.ones((40,5120),dtype=np.float32))
    dump(e/'INPUT_SEAL.json',{'files':{}})
    class G:
        def __init__(self):self.started=None;self.allocation=9999;self.phases={}
        def setup_guard(self):assert self.started is None
        def start(self):
            if self.started is None:self.started=__import__('time').monotonic();self.first_science_epoch=1
        def guard(self):pass
        def write_state(self):pass
        def measured(self,name,t,n,c):self.phases[name]={'timings':t}
    class Tok:
        def encode(self,*a,**kw):return [1]*16
        def decode(self,*a,**kw):return 'neutral'
    class FakeResidents:
        def __init__(self):
            self.gates={t:G() for t in ['E1b','E12']};self.objects={};self.loads={};self.events=[];self.current=None;self.completed_science=0
            self.assets={'model':str(modeldir),'nla':str(nladir)}
        def get(self,name):
            if name not in self.objects:
                assert self.gates[self.current].started is None
                self.loads[name]=self.loads.get(name,0)+1
                self.objects[name]=(object(),Tok(),None) if name=='ar' else ((object(),Tok()) if name=='target' else SimpleNamespace(tok=Tok(),carrier=lambda x:([1,7,2],1),prompt_ids=[1,7,2],marker=1))
            return self.objects[name]
        def release(self,name):self.objects.pop(name,None)
        def park(self,name):pass
    seen=[]
    def greedy(_m,_t,rs):return [{'id':r['id'],'feature':'f','text':'continued','ids':[1]*16} for r in rs]
    def recon(_m,_t,texts):
        if texts[0]!='neutral':verify(out/'e1b/continuations');seen.extend(texts)
        return torch.ones((len(texts),5120))
    monkeypatch.setattr(P,'greedy16',greedy);monkeypatch.setattr(AR,'reconstruct',recon);monkeypatch.setattr(P,'carrier',lambda *a:([1,7,2],1))
    def score(_r,name,u,rs,h,templates,spec):return [{'id':rs[i]['id'],'reader':name,'arm':u['arm'],'scores':[1.,1.],'score':1.} for i in u['indices']]
    monkeypatch.setattr(P,'score_unit',score)
    resident=FakeResidents();P.execute(SimpleNamespace(inputs=inp,out=out),resident)
    assert resident.loads=={'target':1,'ar':1,'olens':1,'nla':1}
    assert len(seen)==40
    assert json.loads((out/'packed.json').read_text())['status']=={'E1b':'COMPLETE','E12':'COMPLETE'}
    assert json.loads((out/'e1b/ar/ids.json').read_text())==[str(i) for i in range(40,80)]
