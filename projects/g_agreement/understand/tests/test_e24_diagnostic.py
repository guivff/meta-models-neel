import json
from contextlib import nullcontext
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand import e24_diagnostic as D


def row(cos=1.,best=None):
    return {'id':'x','cosine':cos,'reference_index':0,'best_reference_index':best}


@pytest.mark.parametrize('b,c,d,best,cause',[(.5,.5,.5,1,'alignment'),(.5,1.,.5,0,'batching'),(.5,.5,1.,0,'environment')])
def test_registered_causes(b,c,d,best,cause):
    result=D.diagnose({'a':[row()],'b':[row(b,best)],'c':[row(c)],'d':[row(d)]})
    assert result['cause']==cause and result['relaunch_eligible'] and not result['automatic_relaunch']


def test_original_failure_stops_without_other_arms():
    assert D.diagnose({'a':[row(.998)]})['status']=='REFERENCE_FAILURE_STOP'


@pytest.mark.parametrize('b,c,d,best',[(1.,1.,1.,None),(.5,.5,.5,0),(.5,1.,1.,0)])
def test_no_failure_no_rescue_or_multiple_causes_inconclusive(b,c,d,best):
    assert D.diagnose({'a':[row()],'b':[row(b,best)],'c':[row(c)],'d':[row(d)]})['status']=='INCONCLUSIVE'


def test_records_padding_and_global_best_match():
    ref=np.array([[1.,0.],[0.,1.],[-1.,0.]])
    batch=[{'id':'background','feature':'f','ids':[1,2,3,4]}, {'id':'x','feature':'f','ids':[1,2]}]
    rr,v=D.records_for(np.array([[0,1],[-1,0]]),batch,{'x':{'reference_index':0}},ref,['ref0','ref1','ref2'],{'unit':'u','start':32},'b')
    assert len(rr)==1 and rr[0]['padding_length']==2 and rr[0]['batch_position']==1
    assert rr[0]['cosine']==-1 and rr[0]['best_reference_index']==2 and rr[0]['best_cosine']==1


def test_capture_a_calls_original_and_stops_before_scoring():
    def original(items,donors,templates,ol,jl,batch,on_capture):
        assert batch==32
        on_capture({44:torch.ones(len(items),2)})
        pytest.fail('must stop before any scoring')
    h=D.capture_batch('a',None,[{'id':'x'}],SimpleNamespace(capture_and_score=original))
    assert h.shape==(1,2)


@pytest.mark.parametrize('arm,size',[('b',8),('c',1),('d',8)])
def test_e24_exact_capture_except_registered_batch_one(monkeypatch,arm,size):
    import mats.capture
    calls=[]
    def capture(model,seqs,layers,positions,batch_size,pad_id):
        calls.append((layers,positions,batch_size,pad_id));return {44:torch.ones(len(seqs),1,2)}
    monkeypatch.setattr(mats.capture,'capture',capture)
    ol=SimpleNamespace(base=nullcontext,model=object(),tok=SimpleNamespace(pad_token_id=0))
    D.capture_batch(arm,ol,[{'ids':[1,2]}],None)
    assert calls==[(list(D.PRIORITY),[[-1]],size,0)]


def test_shared_clock_never_resets_on_environment_switch():
    q={'provider_created_epoch':0,'deadline_epoch':2160}
    assert D.deadline(q,None,0)==1500
    assert D.deadline(q,{'first_science_epoch':100},101)==1900
    assert D.deadline(q,{'first_science_epoch':100},1000)==1900
    assert D.deadline(q,{'first_science_epoch':1400},1500)==1980


def test_frozen_sample_and_original_neighbours():
    b=P.ROOT/'cache/g_agreement/understand/e24d-stage-v1'
    if not b.exists():pytest.skip('sealed local bank unavailable')
    P.verify(b,'INPUT_SEAL.json');selection=json.loads((b/'selected.json').read_text());layout=json.loads((b/'layout.json').read_text())
    assert len(selection)==300 and len({x['id'] for x in selection})==300 and len({x['row'] for x in selection})==28
    for arm,batches in layout.items():
        seen=[uid for bb in batches for uid in bb['ids'] if uid in {x['id'] for x in selection}]
        assert len(seen)==300 and set(seen)=={x['id'] for x in selection}
        assert all(len(bb['ids'])<=({'a':32,'b':8,'c':1,'d':8}[arm]) for bb in batches)
    assert layout['b']==layout['d']
