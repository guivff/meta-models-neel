"""CPU invariants for E24; no model weights, paid APIs, or scientific outputs."""
from contextlib import nullcontext
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.understand import e24_worker as E, e24_analysis as A
from projects.g_agreement.understand.e24_statements import statement
from projects.g_agreement.blindspot import protocol as P


def forecasts(cost=100.,n=4):
    return [dict(slot=i,layers=ls,plan_sha256='p',capture_seal_sha256='c',provider_created_epoch=0.,
        first_science_epoch=500.,forecast_epoch=1000.,provider_deadline_epoch=10800.,
        tier1={str(l):{c:cost for c in ('C1','C2','C4','C5')} for l in ls},
        C6={str(l):10. for l in ls if l in E.C6_LAYERS},C7={str(l):10. for l in ls if l in E.C7_LAYERS},
        c6_capture_and_transfer_s=200.) for i,ls in enumerate(E.shards(n))]


def test_budget_complete_priority_and_optional():
    x=E.schedule(forecasts(),1100)
    assert x['status']=='FIT' and x['layers_priority']==list(E.PRIORITY)
    assert x['C6'] and x['C7'] and x['reserved_gpu_s']<=43200
    assert all(44 in p['layers'] for p in x['pods'])
    for p in x['pods']:
        assert p['science_cap_s']==min(1.5*p['forecast_s']+360,10800)
        assert 1100+p['remaining_s']<=p['deadline_epoch']


def test_drop_only_suffix_never_claim_or_anchor():
    x=E.schedule(forecasts(900),1100)
    assert x['status']=='FIT' and len(x['layers_priority'])<11
    assert x['layers_priority']==list(E.PRIORITY[:len(x['layers_priority'])])
    assert x['dropped_suffix']==list(E.PRIORITY[len(x['layers_priority']):])
    assert {l for p in x['pods'] for l in p['layers']}==set(x['layers_priority'])
    assert E.schedule(forecasts(10000),1100)['status']=='NO_FIT'


def test_no_optional_displaces_tier1():
    fs=forecasts()
    for f in fs:f['C6']={k:1e6 for k in f['C6']};f['C7']={k:1e6 for k in f['C7']}
    x=E.schedule(fs,1100)
    assert len(x['layers_priority'])==11 and not x['C6'] and not x['C7']


@pytest.mark.parametrize('mutation',[lambda f:f['tier1']['44'].pop('C2'),lambda f:f['tier1']['44'].update(C1=float('nan')),
                                    lambda f:f.update(capture_seal_sha256='other'),lambda f:f.update(forecast_epoch=2000)])
def test_forecast_binding_and_missing_claim_rejected(mutation):
    fs=forecasts();mutation(fs[0])
    with pytest.raises(ValueError):E.schedule(fs,1100)


def test_expired_or_delay_consumed_allocation():
    assert E.schedule(forecasts(),11000)['status']=='NO_FIT'


def test_parity_every_item_not_average():
    x=np.ones((100,4));assert E.parity(x,2*x)['minimum_cosine']==pytest.approx(1)
    bad=x.copy();bad[-1]*=-1
    with pytest.raises(ValueError):E.parity(x,bad)
    with pytest.raises(ValueError):E.parity(x,np.zeros_like(x))


def test_real_w1_capture_hook_grid_terminal_forwards_right_padding():
    class Block(torch.nn.Module):
        def forward(self,h):return h+1
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__();self.weight=torch.nn.Parameter(torch.zeros(1));self.layers=torch.nn.ModuleList([Block() for _ in range(64)]);self.calls=0
        def forward(self,input_ids,attention_mask,logits_to_keep):
            self.calls+=1
            assert input_ids.tolist()==[[3,4,0],[8,9,10]]
            assert attention_mask.tolist()==[[1,1,0],[1,1,1]]
            h=input_ids.float()[:,:,None]
            for b in self.layers:h=b(h)
            return h
    model=Model();engine=object.__new__(E.Engine)
    engine.ol=SimpleNamespace(model=model,tok=SimpleNamespace(pad_token_id=0),base=nullcontext)
    result=engine.capture([{'ids':[3,4]},{'ids':[8,9,10]}],list(E.PRIORITY))
    assert model.calls==len(E.PRIORITY) and set(result)==set(E.PRIORITY)
    for l,h in result.items():assert h[:,0].tolist()==[4+l+1,10+l+1]
    assert all(not b._forward_hooks for b in model.layers)


def test_native_scoring_layer_and_prefix_and_free_settings():
    calls=[]
    class Lens:
        def paired_logodds_templates(self,h,l,pairs,prefix):
            calls.append((h.clone(),l,prefix));return torch.ones(len(pairs),len(h))
        def verbalize(self,h,l,k,sampling,batch):
            assert l==20 and k==1 and sampling.temperature==0 and sampling.max_new_tokens==128 and batch==32
            return [['readout'] for _ in h]
    engine=object.__new__(E.Engine);engine.ol=Lens();h=torch.tensor([[20.],[21.]])
    engine.asked(h,20,[['a','b']]);engine.asked(h[[1,0]],20,[['a','b']],'- ');engine.free(h,20)
    assert calls[0][1:]==(20,'') and calls[1][1:]==(20,'- ')
    assert calls[1][0][:,0].tolist()==[21.,20.]


def test_s14_exact_shift_formula():
    true=torch.tensor([[2.,1.],[4.,1.],[0.,1.],[0.,1.]])
    result=A.statement_shift(true,[1,1,0,0],torch.tensor([1.5,3.]),torch.tensor([0.,3.]))
    assert result['ratio']==pytest.approx(.5) and result['cosine']==pytest.approx(1)
    # Calling authoritative frozen source (pure CPU helper), no Modal import.
    import importlib.util
    path=P.ROOT/'cache/g_agreement/understand/e24/upstream/experiments/14_ar_blindspot/ar_lib.py'
    if path.exists():
        spec=importlib.util.spec_from_file_location('s14_frozen_ar',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        assert result==mod.statement_shift(true,np.array([1,1,0,0]),torch.tensor([1.5,3.]),torch.tensor([0.,3.]))


def test_c7_selection_uses_dev_only_lowest_tie():
    scores=np.array([[1.,1.,0,0,0,0,0,0],[0,0,1,1,1,1,1,1]])
    j,values=A.best_dev([1,0],scores)
    assert j==0 and values[:2]==[1,1]


def test_holm_fixed190_not_only_retained():
    family={str(i):1. for i in range(190)};family['0']=.0001
    assert A.holm(family)['0']==pytest.approx(.019)


def test_blind_packet_twenty_same_items_no_truth_or_layer():
    structure=[f'r{i}' for i in range(19)];items=[];rr={};specs={}
    for f in structure:
        specs[f]={'values':['inside','outside']}
        for j in range(3):
            uid=f'{f}-{j}';items.append({'id':uid,'feature':f,'split':'test'});rr[uid]={'feature':f,'C4':'opaque free text'}
    packet,key=A.blind_packet({44:rr,20:rr},items,specs,structure)
    assert len(packet)==40 and len({x['id'] for x in packet})==40
    assert all(set(x)=={'id','row','A','B','readout'} for x in packet)
    assert {x['source_id'] for x in key if x['layer']==44}=={x['source_id'] for x in key if x['layer']==20}


def test_regex_is_frozen_not_enactment():
    assert statement('prose_paren',')')=='neither'
    assert statement('prose_paren','The excerpt is inside an open parenthesis.')=='A'
    assert statement('prose_paren','It is not inside a parenthesis.')=='neither'
    assert statement('python_string','Inside a string literal. Outside a string literal.')=='both'
    freeze=json.loads((P.ROOT/'results/g_agreement/understand/e24/PREGEN_FREEZE.json').read_text())
    for n,h in freeze['files'].items():assert P.sha(P.ROOT/n)==h


def test_assignment_requires_correction_and_custody_bound():
    p={'source_files':{},'modal14_sha256':'actual'}
    q=dict(issuer='integrator',experiment='E24',pod_id='pod',slot=0,plan_sha256='p',source_files={},previous_gpu_seconds=0,
           pod_count=4,pregen_freeze_published=True,source_published=True,external_hardstop_verified=True,
           provider_created_epoch=0,deadline_epoch=10800,allocated_gpu_seconds=10800,
           modal14_hash_correction_commit='published',modal14_corrected_sha256='actual')
    E.validate_assignment(q,p,'p',0,'pod')
    with pytest.raises(ValueError):E.validate_assignment({**q,'modal14_corrected_sha256':'wrong'},p,'p',0,'pod')
    with pytest.raises(ValueError):E.validate_assignment({**q,'allocated_gpu_seconds':10801},p,'p',0,'pod')


def test_staged_banks_are_bound_exact_scope():
    bank=P.ROOT/'cache/g_agreement/understand/e24-stage-v1'
    if not bank.exists():pytest.skip('local sealed bank not staged')
    P.verify(bank,'INPUT_SEAL.json');items=P.rows(bank/'items.input.jsonl');cont=P.rows(bank/'continuations.jsonl')
    assert len(items)==4704 and len(cont)==2100 and len(P.rows(bank/'c6.input.jsonl'))==600
    assert all(not {'value','label','cluster'}&set(x) for x in items)
    assert all(x['feature'] not in {'latex_item','latex_math','latex_fraction'} for x in cont)
    assert len(json.loads((bank/'c2.json').read_text()))==7


def test_unresolved_rows_do_not_shrink_majority():
    assert A.majority(3,0,7) is False
    assert A.majority(3,1,7) is None
    assert A.majority(4,3,7) is True
    assert A.all_resolved([True,None]) is None
    assert A.all_resolved([False,None]) is False
    assert A.all_resolved([]) is None


def test_cpu_analysis_end_to_end_synthetic(tmp_path,monkeypatch):
    """Complete fake 28-row population, real dev probe fits, shortened test bootstrap."""
    bank=tmp_path/'bank';bank.mkdir();out=tmp_path/'pod';out.mkdir();capture=tmp_path/'capture';capture.mkdir();dest=out/'L44';dest.mkdir()
    scope=json.loads((P.ROOT/'results/g_agreement/understand/e24/SCOPE.json').read_text())
    source=json.loads((P.ROOT/'cache/g_agreement/understand/e24-stage-v1/templates.json').read_text())
    items=[];labels=[];h=[];readouts=[];c5ids=[];c5=[];c2rows=['prose_paren','prose_quote','python_string','python_indent','python_depth','list_depth','table_role']
    for f in scope['rows_c1_c3_c4']:
        for split in ('dev','test'):
            for j in range(84):
                uid=f'{f}:{split}:{j}';y=j%2;items.append({'id':uid,'feature':f,'split':split,'ids':[1]});h.append([float(y),1.])
                labels.append({'id':uid,'feature':f,'split':split,'value':source[f]['values'][0 if y else 1],'cluster':f'{split}:{j//14}','class':source[f]['class']})
                if split=='test':
                    readouts.append({'id':uid,'feature':f,'C1':[0.,0.],'C2':[0.,0.] if f in c2rows else None,'C2_swap':[0.,0.] if f in c2rows else None,'C4':''})
                    if f in scope['rows_c5']:c5ids.append(uid);c5.append([0.,1.])
    P.dump(bank/'SCOPE.json',scope);P.dump(bank/'templates.json',source);P.dump(bank/'c2.json',{f:[['a','b']]*2 for f in c2rows});P.jsonl(bank/'items.input.jsonl',items)
    np.save(bank/'reference44.npy',np.array(h,dtype=np.float32));P.seal(bank,[p.name for p in bank.iterdir()],'TEST')
    lab=tmp_path/'labels.json';P.dump(lab,{'w1':labels,'w1_metrics':{'rows':[{'feature':f,'reader':'olens','layer':44,'true':{'auroc':.6 if f=='prose_paren' else .5}} for f in source]},
        'e15_metrics':[{'feature':f,'valid_pairs':[0,1],'readers':{'olens':{'arms':{'true':{'auroc':.5}}}}} for f in c2rows]})
    ref=tmp_path/'e1b.json';P.dump(ref,{'rows':{f:.5 for f in scope['rows_c5']}})
    plan=tmp_path/'plan.json';P.dump(plan,{'source_files':{},'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'labels_sha256':P.sha(lab),'e1b_reference':str(ref)})
    np.save(capture/'acts44.npy',np.array(h,dtype=np.float32));P.dump(capture/'ORDER.json',[x['id'] for x in items]);P.dump(capture/'BINDING.json',{'plan_sha256':P.sha(plan)})
    E.seal(capture,['acts44.npy','ORDER.json','BINDING.json'],'L44_SEAL.json','TEST');E.seal(capture,['L44_SEAL.json'],'CAPTURE_SEAL.json','TEST')
    P.dump(out/'FORECAST.json',{'slot':0});P.dump(out/'ADMISSION.json',{'pods':[{'layers':[44]}],'layers_priority':[44],'C6':False,'C7':False})
    P.jsonl(dest/'readouts.jsonl',readouts);np.save(dest/'C5.npy',np.array(c5));P.dump(dest/'C5_ORDER.json',c5ids)
    P.dump(dest/'BINDING.json',{'layer':44,'plan_sha256':P.sha(plan),'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
        'capture_layer_seal_sha256':P.sha(capture/'L44_SEAL.json'),'admission_sha256':P.sha(out/'ADMISSION.json')})
    E.seal(dest,[p.name for p in dest.iterdir()],'SCORE_SEAL.json','TEST');E.seal(out,['L44/SCORE_SEAL.json','ADMISSION.json','FORECAST.json'],'SCORE_SEAL.json','TEST')
    monkeypatch.setattr(A,'draws',lambda clusters:[np.arange(len(clusters))]*10)
    a=SimpleNamespace(bank=bank,plan=plan,capture=capture,labels=lab,out=tmp_path/'analysis',outputs=[out],c6_capture=None)
    A.analyse(a);P.verify(a.out,'ANALYSIS_SEAL.json');m=json.loads((a.out/'metrics.json').read_text())
    assert m['invalid_R0_rows_uninterpretable_everywhere']==['prose_paren']
    assert 'R6_all_layers' not in m and 'R6' not in m['rules']['44']
    assert sum('C5' in cell for cell in m['layers']['44'].values())==25
    assert all(c['C5_pass'] for f in scope['rows_c5'] for c in m['R0'][f]['anchors'])
    assert len(m['holm'])==190 and len(m['layers']['44'])==28
    assert len(m['rules']['44']['R3_prime']['denominator'])==7
    assert m['rules']['44']['R4']['held'] is None
    assert len(P.rows(a.out/'JUDGE_PACKET.jsonl'))==20
    assert m['layers']['44']['prose_paren']['C3']['auroc']==1
    with pytest.raises(FileExistsError):A.analyse(a)


@pytest.mark.parametrize('true,swap,upper,expected',[(.7,.4,.499,True),(.7,.40001,.49,False),(.7,.4,.5,False),(.699,.3,.4,False),(.8,.5,.49,False)])
def test_clarified_swap_reversal(true,swap,upper,expected):
    assert A.carried_reversal({'C2':{'auroc':true},'C2_swap':{'auroc':swap,'ci95':[0.,upper]}}) is expected


def test_c5_anchor_tolerance():
    assert A.c5_anchor(.73,.70)['C5_pass']
    assert not A.c5_anchor(.73001,.70)['C5_pass']


def test_section130_rejects_superseded_reduced_plan():
    A.validate_scope_authority({})
    A.validate_scope_authority(dict(attempt=2,scope_amendment='4769ca0e',channels=['C1','C2','C3','C4','C5','C6','C7']))
    with pytest.raises(ValueError):A.validate_scope_authority(dict(scope_amendment='d3d91630'))
    with pytest.raises(ValueError):A.validate_scope_authority(dict(channels=['C1','C2','C3','C5']))
