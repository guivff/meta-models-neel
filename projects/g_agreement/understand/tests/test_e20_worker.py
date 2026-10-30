"""CPU acquisition invariants, no model calls or source scientific scores."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import time
import numpy as np
import pytest
import torch
from projects.g_agreement.understand import e20_worker as E


def test_gate_boundary_and_population():
    items=[]; labels={}; records={}
    for row in E.ROWS:
        for y in (0,1):
            for j in range(40):
                i=f'{row}-{y}-{j}';items.append(dict(id=i,feature=row,split='dev',distance=2));labels[i]=y
                records[i]={'positive_count':8 if y and j<24 else 0}
    # 24 perfect positives + 16 ties yields exactly .80.
    assert all(v['status']=='EVALUABLE' and v['auroc']==.8 for v in E.gate(items,records,labels).values())
    records['fact_once-1-23']['positive_count']=0
    assert E.gate(items,records,labels)['fact_once']['status']=='NOT EVALUABLE'
    with pytest.raises(ValueError):E.gate(items,records,{**labels,'test-id':1})


def test_budget_counts_previous_and_refuses_no_fit():
    x=E.allocation(100,1000,206)
    assert x['forecast_total_s']==1306 and x['allocation_total_s']==2319
    assert E.allocation(100,7000,206)['status']=='NO_FIT'


def test_environment_and_carry_forward():
    p={'previous_science_seconds':206.,'previous_setup_seconds':165.}
    q={**p,'issuer':'integrator','experiment':'E20','pod_id':'pod','plan_sha256':'hash',
       'external_hardstop_verified':True,'items_published':True,'parser_freeze_published':True}
    E.validate_assignment(q,p,'hash','/weights/venv-kernels','pod')
    for prefix in ('/weights/venv','/usr'):
        with pytest.raises(ValueError):E.validate_assignment(q,p,'hash',prefix,'pod')
    with pytest.raises(ValueError):E.validate_assignment({**q,'previous_science_seconds':0},p,'hash','/weights/venv-kernels','pod')
    E.validate_assignment({**q,'w12_away':False},p,'hash','/weights/venv-kernels','pod')


def test_teacher_forcing_layout_keeps_recipient_context():
    seq,starts,lengths,owner=E.consequence_layout([1,2],[3],[
        {'intervening_ids':[4,5],'candidates':[[6],[7]]},
        {'intervening_ids':[8],'candidates':[[9,10],[11,12]]}])
    assert seq==[[1,2,3,4,5,6],[1,2,3,4,5,7],[1,2,3,8,9,10],[1,2,3,8,11,12]]
    assert starts==[5,5,4,4] and lengths==[1,1,2,2] and owner==[0,0,1,1]


def test_teacher_forcing_predictive_positions_and_multitoken():
    class Model:
        def __call__(self,inputs_embeds,attention_mask,logits_to_keep,use_cache):
            n=inputs_embeds.shape[0]; width=len(logits_to_keep)
            # Distribution depends on position: a one-token indexing error changes answer.
            grid=torch.arange(16,dtype=torch.float32)[None,None,:]
            logits=-(grid-logits_to_keep[None,:,None].float())**2
            return SimpleNamespace(logits=logits.expand(n,width,16))
    class OL:
        device='cpu'; model=Model()
        tok=SimpleNamespace(pad_token_id=0,encode=lambda s,**kw:[3])
        def carrier(self,l):return [1,2],1
        def _embed(self,ids,slot,acts):
            assert acts[:,0].tolist()==[100,100,200,200]
            return ids
    engine=object.__new__(E.Engine);engine.ol=OL()
    items=[{'intervening_ids':[4,5],'candidates':[[6],[7]]}, {'intervening_ids':[8],'candidates':[[9,10],[11,12]]}]
    values=engine.consequence(items,torch.tensor([[100.],[200.]]))
    expected=[]
    for start,cs in [(5,[[6],[7]]),(4,[[9,10],[11,12]])]:
        scores=[]
        for c in cs:
            scores.append(sum(float(torch.log_softmax(-(torch.arange(16).float()-(start-1+k))**2,0)[t]) for k,t in enumerate(c)))
        expected.append(scores[0]-scores[1])
    assert values==pytest.approx(expected)


@pytest.mark.parametrize('failed_row',[None,'python_string'])
def test_full_acquisition_once_with_mock_engine(tmp_path,monkeypatch,failed_row):
    bank=tmp_path/'bank';bank.mkdir();out=tmp_path/'out'; model=tmp_path/'model';model.mkdir();(model/'tokenizer.json').write_text('{}')
    items=[];labels=[]
    for row in E.ROWS:
        for pair in range(120):
            for distance in (2,4,8,16,32,48):
                for y in (0,1):
                    i=f'{row}:{pair}:{distance}:{y}'
                    x=dict(id=i,feature=row,split='dev' if pair<40 else 'test',distance=distance,ids=[1,2],
                        random_donor_id=i,opposite_donor_id=f'{row}:{pair}:{distance}:{1-y}')
                    items.append(x)
                    if pair<40 and distance==2:labels.append(dict(id=i,split='dev',distance=2,label=y))
    E.P.jsonl(bank/'items.input.jsonl',items);E.P.dump(bank/'phrasings.json',{})
    E.P.dump(bank/'INPUT_SEAL.json',{'files':{n:E.P.sha(bank/n) for n in ['items.input.jsonl','phrasings.json']}})
    labelpath=tmp_path/'dev.jsonl';E.P.jsonl(labelpath,labels)
    plan={'previous_science_seconds':206.,'previous_setup_seconds':165.,'input_seal_sha256':E.P.sha(bank/'INPUT_SEAL.json'),
        'dev_labels_sha256':E.P.sha(labelpath),'source_files':{},'tokenizer_sha256':E.P.sha(model/'tokenizer.json'),
        'parser_sha256':'parser','parser_freeze_sha256':'freeze'}
    planpath=tmp_path/'plan.json';E.P.dump(planpath,plan)
    q={**plan,'issuer':'integrator','experiment':'E20','pod_id':'pod','plan_sha256':E.P.sha(planpath),
        'items_published':True,'parser_freeze_published':True,'external_hardstop_verified':True,
        'provider_created_epoch':time.time(),'deadline_epoch':time.time()+10000}
    assignment=tmp_path/'assignment.json';E.P.dump(assignment,q)
    class Engine:
        def __init__(self,*_):pass
        def base(self,batch):
            return [dict(id=x['id'],feature=x['feature'],positive_count=(8*int(x['id'][-1]) if x['feature']!=failed_row else 0)) for x in batch]
        def capture(self,batch):return torch.ones((len(batch),2))
        def lens(self,batch,acts):
            E.P.verify(out,'VALIDITY_SEAL.json')
            assert all(x['feature']!=failed_row for x in batch)
            assert all(x[k] in acts for x in batch for k in ('id','random_donor_id','opposite_donor_id'))
            return [dict(id=x['id']) for x in batch]
    monkeypatch.setattr(E,'Engine',Engine);monkeypatch.setattr(E.W,'_assets',lambda *a,**k:{'model':str(model)})
    monkeypatch.setattr(sys,'prefix','/weights/venv-kernels');monkeypatch.setenv('RUNPOD_POD_ID','pod')
    monkeypatch.setattr(torch.cuda,'synchronize',lambda:None)
    E.run(SimpleNamespace(bank=bank,out=out,plan=planpath,assignment=assignment,dev_labels=labelpath,assets=tmp_path/'assets'))
    for seal in ['VALIDITY_SEAL.json','CAPTURE_SEAL.json','SCORE_SEAL.json']:E.P.verify(out,seal)
    base=E.P.rows(out/'base.jsonl');lens=E.P.rows(out/'lens.jsonl')
    assert len(base)==len({x['id'] for x in base})==5760
    assert len(lens)==len({x['id'] for x in lens})==(5760 if failed_row is None else 4320)
    assert np.load(out/'acts44.npy').shape==(5760,2)
    assert len(E.P.rows(out/'base.partial.jsonl'))==5760
    assert json.loads((out/'RECEIPT.json').read_text())['previous_science_seconds']==206
    with pytest.raises(FileExistsError):E.run(SimpleNamespace(bank=bank,out=out,plan=planpath,assignment=assignment,dev_labels=labelpath,assets=tmp_path/'assets'))


def test_bands_average_scores_before_auc_and_holm():
    from projects.g_agreement.understand.e20_analysis import band_scores,pair_auc,holm,summarize
    v=np.zeros((2,2,6));v[:,0,:]=1
    assert pair_auc(band_scores(v,'near'))==1
    v[:,:,4:]=.5
    draws=np.array([[0,1],[0,0],[1,1]])
    s=summarize(v,draws)
    assert s['near']['auroc']==1 and s['far']['auroc']==.5
    assert s['near_minus_far']['difference']==.5
    assert s['near_minus_far']['p_one_sided']==.25
    assert holm({'a':.01,'b':.04,'c':1.})=={'a':.03,'b':.08,'c':1.}
    v[:,:,3]=1000 # d16 must be excluded from both bands
    assert pair_auc(band_scores(v,'near'))==1 and pair_auc(band_scores(v,'far'))==.5


def test_lens_controls_swap_only_activation_keep_context(monkeypatch):
    from mats.readers.olens import OracleLens
    engine=object.__new__(E.Engine)
    class OL:
        def verbalize(self,h,layer,k,sampling,batch):
            assert layer==44 and sampling.max_new_tokens==16
            return [[')' for _ in range(k)] for _ in h]
        def paired_logodds_templates(self,h,layer,pairs):return torch.tensor([[2.,3.],[4.,5.]])
    engine.ol=OL();engine.phrasings={'prose_paren':[('a','b'),('c','d')]}
    items=[{'id':'a','feature':'prose_paren','random_donor_id':'r','opposite_donor_id':'b','intervening_ids':[9]},
           {'id':'b','feature':'prose_paren','random_donor_id':'r','opposite_donor_id':'a','intervening_ids':[9]}]
    acts={k:torch.tensor([v]) for k,v in [('a',1.),('b',2.),('r',3.)]};seen=[]
    def consequence(xs,h):
        assert xs is items and [x['intervening_ids'] for x in xs]==[[9],[9]]
        seen.append(h[:,0].tolist());return h[:,0].tolist()
    engine.consequence=consequence
    out=engine.lens(items,acts)
    assert seen==[[1,2],[3,3],[2,1]]
    assert out[0]['positive_count']==4 and out[0]['asked']==[2.,4.]
    assert out[0]['consequence']=={'true':1.,'random_donor':3.,'opposite_donor':2.}
