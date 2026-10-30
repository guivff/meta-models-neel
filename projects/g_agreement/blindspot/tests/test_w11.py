"""§87 item invariants, actual dual capture, prospective gates and admission; CPU only."""
from collections import Counter
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.blindspot import w11_items as W
from projects.g_agreement.blindspot import w11_run as R
from projects.g_agreement.blindspot import w11_analysis as A
from projects.g_agreement.blindspot import protocol as P


@pytest.fixture(scope='module')
def tok():
    path=os.environ.get('BLINDSPOT_QWEN_TOKENIZER')
    if not path:pytest.skip('requires local pinned tokenizer')
    return W.load_pinned_tokenizer(path)


@pytest.fixture(scope='module')
def items(tok):return W.build(tok)


def test_real_tokenizer_design_and_all_length_strata(tok,items):
    report=W.verify(tok,items)
    assert report['items']==1200 and report['pairs']==600 and len(report['checks'])==20
    assert all(c['ks_p']==1 and c['mean_token_difference']==0 for c in report['checks'])
    assert Counter(x['feature'] for x in items)==dict.fromkeys(W.NATURAL_PAIRS,120)


@pytest.mark.parametrize('feature',list(W.NATURAL_PAIRS))
def test_all_feature_pairs_have_identical_carriers_and_no_suffix(tok,items,feature):
    row=[x for x in items if x['feature']==feature]
    for a,b in zip(row[::2],row[1::2]):
        start=a['meta']['target_start']
        assert a['ids'][:start]==b['ids'][:start]
        assert len(a['ids'][start:])==len(b['ids'][start:])
        assert a['text'][:a['meta']['target_char_start']]==b['text'][:b['meta']['target_char_start']]
        assert all(x['meta']['read_position']==len(x['ids'])-1 for x in (a,b))
        assert all(x['meta']['pretarget_position']==start-1 for x in (a,b))
        assert all(W.S.extract(x['text'],'prose')[feature] is (x['value']=='present') for x in (a,b))
        assert all(not x['meta']['prefix'].startswith('pad ') for x in (a,b))


@pytest.mark.parametrize('change',['prefix','span_length','suffix','label','pretarget_position'])
def test_verifier_rejects_nonminimal_or_mislabelled_items(tok,items,change):
    bad=copy.deepcopy(items)
    if change=='prefix':bad[1]['ids'][0]+=1
    if change=='span_length':bad[1]['ids'].append(0)
    if change=='suffix':bad[1]['text']+=' extra'
    if change=='label':bad[1]['value']='present'
    if change=='pretarget_position':bad[1]['meta']['pretarget_position']+=1
    with pytest.raises(ValueError):W.verify(tok,bad)


def test_random_donors_ignore_labels_and_preserve_context_and_length(items):
    donor=W.random_donors(items)
    assert donor==W.random_donors([{**x,'value':'inaccessible'} for x in items])
    lookup={x['id']:x for x in items}
    for x in items:
        d=lookup[donor[x['id']]]
        assert (x['feature'],x['cluster'],x['split'],len(x['ids'])//16)==(d['feature'],d['cluster'],d['split'],len(d['ids'])//16)


class FakeModel(torch.nn.Module):
    def __init__(self,leaky=False):
        super().__init__();self.anchor=torch.nn.Parameter(torch.zeros(1))
        self.layers=torch.nn.ModuleList([torch.nn.Identity() for _ in range(45)])
        self.config=SimpleNamespace(num_hidden_layers=45);self.leaky=leaky
    def forward(self,input_ids,attention_mask,logits_to_keep):
        h=torch.stack((input_ids.float(),input_ids.cumsum(-1).float()),-1)
        if self.leaky:h=h+input_ids.sum(-1)[:,None,None]
        for layer in self.layers:h=layer(h)
        return SimpleNamespace()


def test_capture_observes_actual_before_span_position_not_penultimate_and_preserves_causality():
    pair=[{'ids':[1,2,3,4,5],'positions':[1,4]}, {'ids':[1,2,7,8,9],'positions':[1,4]}]
    # Two-token prefix, three-token spans: pretarget index=1, not index=3.
    h=R.capture_dual(FakeModel(),SimpleNamespace(pad_token_id=0),pair,lambda:None)
    assert h[42].shape==(2,2,2)
    assert h[42][:,0].tolist()==[[2.,3.],[2.,3.]]
    assert h[42][:,1,0].tolist()==[5.,9.]
    assert torch.equal(h[42],h[44])
    # An intentionally noncausal fake MUST be visible: no pair-vector copying.
    leaky=R.capture_dual(FakeModel(leaky=True),SimpleNamespace(pad_token_id=0),pair,lambda:None)
    assert not torch.equal(leaky[42][0,0],leaky[42][1,0])


def test_actual_probe_is_chance_for_duplicate_prefixes_and_detects_leak():
    from projects.g_agreement.blindspot.analysis import grouped_probe
    from mats.metrics import auroc_labels
    y=np.tile([0,1],12);groups=np.repeat(np.arange(6),4)
    x=np.repeat(np.arange(12),2)[:,None].astype(float)
    score,_,_=grouped_probe(x,y,groups,np.arange(len(y)))
    assert auroc_labels(score,y)==.5
    leaked=np.column_stack([x,y])
    score,_,_=grouped_probe(leaked,y,groups,np.arange(len(y)))
    assert auroc_labels(score,y)==1
    assert not A.row_decision(.5,1,.5,[1,.5])['evaluable']


def test_registered_rules_do_not_require_nla_to_be_near_probe_and_exclude_failed_gates():
    assert A.row_decision(.70,.85,.40,[.48,.52])['confirms']
    assert not A.row_decision(.5,1,.39,[.5,.5])['evaluable']
    assert not A.row_decision(.5,1,.61,[.5,.5])['evaluable']
    assert not A.row_decision(.5,.84,.5,[.5,.5])['evaluable']
    rows=[{'feature':str(i),'evaluable':i<7,'confirms':i<5} for i in range(10)]
    result=A.summary(rows)
    assert result['rate']['n']==7 and result['rate']['k']==5 and result['status']=='CONFIRMED'
    assert A.summary([])['status']=='NOT EVALUABLE'


@pytest.mark.parametrize('forecast',[0,-1,float('inf'),float('nan'),3601])
def test_invalid_or_unfittable_forecast_rejected(forecast):
    with pytest.raises(ValueError):R.allocation(forecast)


def test_allocation_is_capped_formula():
    assert R.allocation(1000)==1860
    assert R.allocation(2160)==3600
    assert R.allocation(3000)==3600


def test_freeze_stage_frozen_phrasing_identity_and_persistent_clock(tok,tmp_path):
    bank,frozen,stage=[tmp_path/n for n in ('bank','freeze','stage')]
    W.freeze(tok,os.environ['BLINDSPOT_QWEN_TOKENIZER'],bank,frozen,stage)
    P.verify(stage,'INPUT_SEAL.json')
    assert not list(stage.glob('*DO_NOT_STAGE*'))
    assert (stage/'templates.json').read_bytes()==(P.ROOT/W.W84/'templates.json').read_bytes()
    items,donors,specs=R.inputs(stage)
    assert len(items)==len(donors)==1200 and len(specs)==10
    manifest=json.loads((stage/'manifest.json').read_text())
    a={'issuer':'integrator','experiment':'W11','pod_id':'unit-test',
        'brief_registered':True,'brief_pushed':True,'manifest_committed':True,'external_hardstop_verified':True,
        'source_commit':'a'*40,'brief_commit':manifest['registration']['commit'],'manifest_commit':'b'*40,
        'source_files':W.source_hashes(),'manifest_sha256':P.sha(stage/'manifest.json'),
        'section87_sha256':P.sha(P.ROOT/W.SECTION),'science_cap_gpu_seconds':3600,'staging_allowance_seconds':1500,
        'provider_created_epoch':95,'deadline_epoch':5195,'allocated_gpu_seconds':5100,'previous_gpu_seconds':0}
    path=tmp_path/'assignment.json';P.dump(path,a)
    admitted=R.admit(path,stage,now=100,pod_id='unit-test')
    assert not Path(admitted['_science_clock_path']).exists()
    assert P.science_deadline(admitted,start=True,now=105)==3705
    assert P.science_deadline(admitted,now=115)==3705
    with pytest.raises(ValueError,match='no duplicate'):R.admit(path,stage,now=115,pod_id='unit-test')


def test_incomplete_score_grid_is_rejected_before_label_file_is_opened(tok,tmp_path):
    bank,frozen,stage=[tmp_path/n for n in ('bank','freeze','stage')]
    W.freeze(tok,os.environ['BLINDSPOT_QWEN_TOKENIZER'],bank,frozen,stage)
    items,_,_=R.inputs(stage);outputs=tmp_path/'output';outputs.mkdir()
    for site in (42,44):
        for prefix in ('','pretarget.'):
            np.save(outputs/f'{prefix}acts{site}.npy',np.zeros((1200,2),dtype=np.float32))
    P.dump(outputs/'items.order.json',[x['id'] for x in items])
    P.dump(outputs/'provenance.json',{'input_seal_sha256':P.sha(stage/'INPUT_SEAL.json'),'source_files':W.source_hashes()})
    P.dump(outputs/'FORECAST.json',{'status':'FIT'})
    R.seal_named(outputs,['acts42.npy','acts44.npy','pretarget.acts42.npy','pretarget.acts44.npy','items.order.json','provenance.json'],
                 'CAPTURE_SEAL.json','W11_CAPTURE_SEALED')
    scores=[{'id':x['id'],'reader':name,'layer':site,'arm':arm,'status':'COMPLETE','scores':[0,0]}
            for x in items for name,site in R.READERS for arm in ('true','random_donor')]
    P.jsonl(outputs/'scores.jsonl',scores[:-1])
    R.seal_named(outputs,['scores.jsonl','CAPTURE_SEAL.json','provenance.json','items.order.json','FORECAST.json'],
                 'SCORE_SEAL.json','SCORES_SEALED_W11_BEFORE_LABEL_JOIN')
    with pytest.raises(ValueError,match='incomplete/duplicate reader grid'):
        A.analyse(stage,outputs,tmp_path/'must-not-be-read.jsonl',tmp_path/'analysis')
