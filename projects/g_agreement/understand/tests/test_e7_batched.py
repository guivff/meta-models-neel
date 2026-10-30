from pathlib import Path
from types import SimpleNamespace
import time
import numpy as np
import pytest
from projects.g_agreement.understand import e7_batched as B
from projects.g_agreement.understand.e7_batched_runtime import Gate,budget,PHASES,PRIOR_SCIENCE
from projects.g_agreement.understand.cpu import read,dump,sha,verify


def test_admission_requires_dated_ruling_prior_budget_and_pinned_source(tmp_path,monkeypatch):
    from projects.g_agreement.understand import e7_batched_runtime as R
    monkeypatch.setattr(R,'ROOT',tmp_path);monkeypatch.setattr(R,'STOP',time.time()+20000)
    names=['projects/g_agreement/understand/'+n+'.py' for n in ['e7_batched','e7_batched_runtime','e7_parity','e7_solo','worker','packed','analyse','cpu']]
    for name in names+[R.BRIEF]:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('registered')
    now=time.time();a={'issuer':'integrator','experiment':'E7','gpu_count':1,'pod_id':'fake',
        'external_hardstop_verified':True,'hold_renewer_verified':True,'brief_registered':True,'brief_pushed':True,'conditional_7200_ruling_recorded':True,
        'brief_sha256':sha(tmp_path/R.BRIEF),'source_files':{n:sha(tmp_path/n) for n in names},'allocated_gpu_seconds':7200-PRIOR_SCIENCE,
        'previous_gpu_seconds':PRIOR_SCIENCE,'provider_created_epoch':now-10,'setup_deadline_epoch':now+2390,'deadline_epoch':now+9000,
        'setup_allowance_seconds':2400,'forecast_method':'four_phase_warmed_median_next_3_retained_units'}
    p=tmp_path/'a.json';dump(p,a);g=Gate(p,{k:3 for k in PHASES});assert g.allocation==pytest.approx(360-PRIOR_SCIENCE)
    for change in [{'conditional_7200_ruling_recorded':False},{'previous_gpu_seconds':0},{'allocated_gpu_seconds':7200}]:
        dump(p,{**a,**change})
        with pytest.raises(ValueError):Gate(p,{k:3 for k in PHASES})
    dump(p,a);(tmp_path/names[0]).write_text('tampered')
    with pytest.raises(ValueError,match='source'):Gate(p,{k:3 for k in PHASES})


def test_tiny_native_NLA_generation_batch32_matches8_exactly_with_tail_and_EOS():
    import common,torch
    from transformers import LlamaConfig,LlamaForCausalLM
    from mats.readers.nla import NLA
    torch.manual_seed(713)
    class Tok:
        pad_token_id=0
        def batch_decode(self,seqs,skip_special_tokens=True):
            return [' '.join(str(t) for t in row.tolist() if not skip_special_tokens or t not in [0,1,2]) for row in seqs]
    config=LlamaConfig(vocab_size=32,hidden_size=24,intermediate_size=48,num_hidden_layers=2,
        num_attention_heads=4,num_key_value_heads=2,max_position_embeddings=256,pad_token_id=0,bos_token_id=1,eos_token_id=2)
    # Marker at the last prompt token makes the tiny two-block model sensitive to each vector.
    model=LlamaForCausalLM(config).eval();nla=NLA(model,Tok(),None,None,{},[1,3,7],2,'cpu')
    model.model.layers[1].register_forward_hook(nla._hook);h=torch.randn(52,24)
    big,bt=B.generation_with_tokens(nla,h,32);small,st=B.generation_with_tokens(nla,h,8)
    assert big==small and bt==st and len(big)==52
    assert len({tuple(t) for t in bt})>1  # distinct injected vectors remain independently conditioned
    report=B.verify_generation_parity(nla,h[:32])
    assert report['status']=='PASS_INPUT_AUDIT'
    assert all(a['padding_side']=='left' and a['forward_steps']>0 for a in report['padding_verification'].values())
    assert all(c['position_steps_verified']>0 and c['attention_mask_all_ones'] for a in report['padding_verification'].values() for c in a['calls'])
    model.lm_head=torch.nn.Linear(24,32,bias=True)
    with torch.no_grad():model.lm_head.weight.zero_();model.lm_head.bias.zero_();model.lm_head.bias[2]=30
    big,bt=B.generation_with_tokens(nla,h,32);small,st=B.generation_with_tokens(nla,h,8)
    assert big==small and bt==st==[[2]]*52


def test_parity_measures_invisible_token_changes_without_rejecting(monkeypatch):
    def values(_n,_h,batch,**kwargs):return [['same decoded string']],[[7 if batch==32 else 8]]
    monkeypatch.setattr(B,'generation_with_tokens',values)
    r=B.verify_generation_parity(SimpleNamespace(tok=SimpleNamespace()),np.zeros((1,2)))
    assert r['accepted'] and r['first32_identical_rate']==0 and r['raw_text_identical_rate']==1


@pytest.mark.parametrize('forecast,ceiling',[(1000,2880),(2880,2880),(2880.1,7200),(6000,7200)])
def test_conditional_budget_and_prior_science(forecast,ceiling):
    selected,cumulative,allocation=budget(forecast,PRIOR_SCIENCE,7200-PRIOR_SCIENCE)
    assert selected==ceiling
    assert cumulative==min(1.5*forecast+360,ceiling)
    assert allocation+PRIOR_SCIENCE==pytest.approx(cumulative)


def bare_gate(out,counts):
    g=object.__new__(Gate);g.assignment={'setup_deadline_epoch':time.time()+2400,'deadline_epoch':time.time()+10000};g.experiment='E7'
    g.started=None;g.setup_complete=False;g.setup_callback=lambda:None;g.previous=PRIOR_SCIENCE;g.reserved=7200-PRIOR_SCIENCE
    g.samples={k:[] for k in PHASES};g.completed={k:0 for k in PHASES};g.movements={};g.counts=counts;g.state_status='SETUP';g.out=out
    g.allocation=budget(0,g.previous,g.reserved)[2];return g


def test_full_forecast_requires_all_four_and_counts_residency(tmp_path):
    g=bare_gate(tmp_path,{k:10 for k in PHASES});g.start();start=g.started
    for _ in range(3):g.record('readouts',1.)
    with pytest.raises(ValueError,match='all four'):g.admit_remaining()
    for key in ['prepare','decoder','scores']:
        for _ in range(3):g.record(key,1.)
    g.movement('decoder',2.);g.movement('scores',3.);r=g.admit_remaining()
    assert r['F_seconds']==50 and r['remaining_forecast_seconds']==33 and r['fit']
    assert set(r['phases'])==set(PHASES) and all(len(v['timed_unit_seconds'])==3 for v in r['phases'].values())
    g.start();assert g.started==start
    assert read(tmp_path/'FULL_WARMED_FORECAST.json')['all_four_phases_measured'] is True
    verify(tmp_path,'FORECAST_SEAL.json')


def test_full_forecast_over_two_hours_stops_and_keeps_receipt(tmp_path):
    g=bare_gate(tmp_path,{k:1000 for k in PHASES});g.start()
    for phase in PHASES:
        for _ in range(3):g.record(phase,3.)
    g.movement('decoder',1.);g.movement('scores',1.)
    with pytest.raises(TimeoutError,match='NO_FIT'):g.admit_remaining()
    r=read(tmp_path/'FULL_WARMED_FORECAST.json')
    assert r['coordinator_extension_used'] and r['cumulative_cap_seconds']==7200 and not r['fit']
    verify(tmp_path,'FORECAST_SEAL.json')


def test_schedule_preserves_original_batches_and_closes_pilot_dependencies():
    n=100;pairs=[{'id':str(i),'feature':'f','recipient':i,'donor':99-i,'random':(i+50)%n} for i in range(12)]
    s=B.schedule(n,pairs)
    assert sum(s['generation_units'],[])==list(range(n))
    assert sum(s['decoder_units'],[])==list(range(2*n))
    assert sum(s['score_units'],[])==list(range(6*len(pairs)))
    generated={i for k in s['pilot_generation_units'] for i in s['generation_units'][k]}
    decoded={i for k in s['pilot_decoder_units'] for i in s['decoder_units'][k]}
    for k in s['pilot_decoder_units']:
        assert all(pos<n or pos-n in generated for pos in s['decoder_units'][k])
    for k in s['pilot_score_units']:
        for pos in s['score_units'][k]:
            pair=pairs[s['score_records'][pos]['index']]
            assert all(i in decoded and i+n in decoded for i in [pair['recipient'],pair['donor'],pair['random']])


def test_complete_E7_only_retains_pilot_once_and_matches_canonical_science(tmp_path,monkeypatch):
    import torch
    inp=tmp_path/'inputs/e7';inp.mkdir(parents=True);out=tmp_path/'out';out.mkdir();n=100
    ids=[str(i) for i in range(n)];pairs=[{'id':str(i),'feature':'f','recipient':i,'donor':99-i,'random':(i+50)%n} for i in range(12)]
    dump(inp/'ids.json',ids);dump(inp/'templates.json',{'f':{'nla':[['A','B'],['A2','B2']]}});B.W.jsonl(inp/'pairs.input.jsonl',pairs)
    B.W.jsonl(inp/'ol.input.jsonl',[{'id':key,'text':'OL'+key} for key in ids]);h=np.zeros((n,5120),np.float32);h[:,0]=np.arange(n);np.save(inp/'acts42.npy',h)
    files=['ids.json','templates.json','pairs.input.jsonl','ol.input.jsonl','acts42.npy'];dump(inp/'INPUT_SEAL.json',{'files':{p:sha(inp/p) for p in files}})
    assets=tmp_path/'assets.json';dump(assets,{});assign=tmp_path/'assign';assign.mkdir();dump(assign/'e7.json',{})
    s=B.schedule(n,pairs);counts={'readouts':len(s['generation_units']),'prepare':len(s['decoder_units']),'decoder':len(s['decoder_units']),'scores':len(s['score_units'])}
    root=out/'e7';g=bare_gate(root,counts)
    class Decoder:
        def reconstruct(self,texts,batch):
            assert batch==8
            return torch.tensor([[float(t[3:] if t.startswith('NLA') else t[2:])+(0.25 if t.startswith('NLA') else 0)]*5120 for t in texts])
    class Residents:
        def __init__(self):self.loads={};self.objects={};self.events=[];self.current=None;self.gates={'E7':g}
        def get(self,name):
            assert name in ['decoder','nla']
            if name not in self.objects:
                assert g.started is None;self.loads[name]=self.loads.get(name,0)+1;self.objects[name]=Decoder() if name=='decoder' else object()
            return self.objects[name]
    def setup(c):c.resident.get('decoder');c.resident.get('nla')
    production_batches=[]
    def gen(_n,h,batch=32):
        production_batches.append(batch)
        return [['<explanation>NLA'+str(int(v[0]))+'</explanation>'] for v in h]
    def scorer(_n,rs,arms,templates):return [{**r,'score':float(arms[r['arm']][r['index'],0])} for r in rs]
    monkeypatch.setattr(B.Collection,'setup',setup);monkeypatch.setattr(B,'generate',gen);monkeypatch.setattr(B,'score',scorer)
    resident=Residents();B.execute(SimpleNamespace(inputs=inp.parent,out=out,assets=assets,assignments=assign),resident,g,s)
    assert read(out/'solo.json')['status']=='COMPLETE'
    assert resident.loads=={'decoder':1,'nla':1}
    assert production_batches and set(production_batches)=={32}
    assert read(root/'decoder/ids.json')==[prefix+':'+key for prefix in ['ol','nla'] for key in ids]
    recon=np.load(root/'decoder/recon.npy');assert np.allclose(recon[:n,0],np.arange(n));assert np.allclose(recon[n:,0],np.arange(n)+.25)
    assert np.allclose(np.load(root/'scores/delta.npy'),.25)
    result=B.W.rows(root/'scores/scores.jsonl');assert len(result)==6*len(pairs)
    canonical=B.W.e7_arms(recon[:n],recon[n:],pairs)
    assert all(r['score']==float(canonical[r['arm']][r['index'],0]) for r in result)
    assert read(root/'FULL_WARMED_FORECAST.json')['all_four_phases_measured']
    assert read(root/'run.json')['science_clock_resets']==0
    verify(root);verify(root/'readouts');verify(root/'decoder');verify(root/'scores')
