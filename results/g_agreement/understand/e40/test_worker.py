"""Tiny mocked orchestration checks: ordering, seals and failure classification."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import worker as w


def test_output_claim_creates_parents_and_cannot_be_reused(tmp_path,monkeypatch):
    monkeypatch.setattr(w,'ROOT',tmp_path)
    out=tmp_path/w.OUT
    w.claim(out,'a'*64,'b'*64)
    assert out.is_dir() and (out.parent/'TRAINING.RUN_ONCE.json').exists()
    with pytest.raises(FileExistsError):w.claim(out,'a'*64,'b'*64)
    with pytest.raises(ValueError):w.claim(out.parent/'different','a'*64,'b'*64)


@pytest.mark.parametrize('exception,expected,category',[
    (None,'PASS',None),(ValueError('invalid'),'INCOMPLETE','VALIDITY_NO_RETRY'),
    (OSError('disk'),'INCOMPLETE','OPERATIONAL'),(w.NoFit('time'),'NO_FIT','OPERATIONAL')])
def test_execute_seals_calibration_before_any_update_and_uses_filtered_gate_only(tmp_path,monkeypatch,exception,expected,category):
    code=tmp_path/'code';code.mkdir();(code/w.REQUEST).write_text('{}')
    monkeypatch.setattr(w,'HERE',code)
    out=tmp_path/'cache'/'out';out.mkdir(parents=True)
    assignment_path=tmp_path/'assignment.json';assignment_path.write_text('{}')
    a=SimpleNamespace(out=out,sources=tmp_path/'sources',assignment=assignment_path)
    events=[]
    class C:
        science_limit=None
        forecast_components={}
        status='SETUP'
        def check(self):pass
        def begin(self):events.append('begin')
        def admit(self,**kwargs):events.append('admit')
        def record(self):return {'status':self.status}
    monkeypatch.setattr(w,'verify_sources',lambda *args:None)
    monkeypatch.setattr(w,'load_target',lambda clock:(object(),{}))
    monkeypatch.setattr(w,'capture44',lambda *args,**kwargs:None)
    monkeypatch.setattr(torch.cuda,'reset_peak_memory_stats',lambda:None)
    monkeypatch.setattr(torch.cuda,'max_memory_allocated',lambda:0)
    monkeypatch.setattr(torch.cuda,'synchronize',lambda:None)
    monkeypatch.setattr(torch.cuda,'empty_cache',lambda:None)
    monkeypatch.setattr(torch.cuda,'is_initialized',lambda:False)
    monkeypatch.setattr(w,'chunks',lambda x:iter(()))
    monkeypatch.setattr(w,'documents',lambda p:iter(()))
    monkeypatch.setattr(w,'captured_stream',lambda *args,**kwargs:iter(()))
    buffer=torch.ones((8,2));norms=np.arange(1.,9.)
    monkeypatch.setattr(w,'collect_calibration',lambda stream:(buffer,norms,None))
    real_calibrate=w.calibrate
    monkeypatch.setattr(w,'calibrate',lambda x:real_calibrate(x,d_model=2,expected=8))
    def pilot(*args,**kwargs):
        assert (out/'CALIBRATION_SEAL.json').exists()
        events.append('pilots');return [.1]*3,[.1]*3
    monkeypatch.setattr(w,'pilots',pilot)
    monkeypatch.setattr(w,'tighten_alarm',lambda clock:events.append('alarm'))
    class Raw:
        def to(self,device):return torch.ones((4,2))
    monkeypatch.setattr(w,'eligible_batches',lambda *args,**kwargs:iter([Raw()]))
    class Trainer:
        tokens_seen=0;steps=0
        def __init__(self,**kwargs):
            assert (out/'CALIBRATION_SEAL.json').exists()
            assert kwargs=={'scale':real_calibrate(norms,d_model=2,expected=8)['scale'],'device':'cuda'}
            events.append('fresh_trainer')
        def step(self,*args,**kwargs):
            events.append('training')
            if exception is not None:raise exception
            self.tokens_seen=100_000_000;self.steps=24415
        def checkpoint_tensors(self):events.append('checkpoint');return {'tiny':torch.ones(1)}
        def completed_manifest(self):return {'training_tokens':self.tokens_seen}
    monkeypatch.setattr(w,'Trainer',Trainer)
    monkeypatch.setattr(w,'ScaledSAE',lambda *args,**kwargs:object())
    def gate(*args,**kwargs):
        assert (out/'GATE.RUN_ONCE.json').exists()
        assert (out/'layer44.e40.sae.pt').exists()
        events.append('gate')
        return {'filtered':{'passed':True,'n_tokens':49700,'fvu':.2},
                'all_tokens':{'passed':False,'n_tokens':50000,'fvu':.9}}
    monkeypatch.setattr(w,'evaluate_gate',gate)
    rc=w.execute(a,{}, {'sources_sha256':'a'*64},C(),None,None)
    result=json.loads((out/'GATE_RESULT.json').read_text())
    assert result['status']==expected and result['failure_category']==category
    assert result['scientific_retry_allowed'] is False
    assert result['decomposition_calls']==0
    seal=json.loads((out/'OUTPUT_SEAL.json').read_text())
    assert all(w.sha(out/n)==s for n,s in seal['files'].items())
    if exception is None:
        assert rc==0 and events==['begin','pilots','admit','alarm','fresh_trainer','training','checkpoint','gate']
    else:
        assert rc==2 and 'gate'not in events and 'checkpoint'not in events
