from pathlib import Path
from types import SimpleNamespace
import json,time
import numpy as np
import pytest
import torch
from projects.g_agreement.blindspot import w12_run as R,protocol as P
from projects.g_agreement.understand import e24_analysis as A
BANK=P.ROOT/'cache/g_agreement/blindspot/w12-reader-stage'
PLAN=P.ROOT/'results/g_agreement/blindspot/w12/launch/RUN_PLAN.json'

def test_release_binding():
    plan=json.loads(PLAN.read_text());R.verify_release(BANK,plan)
    with pytest.raises(ValueError):R.verify_release(BANK,{**plan,'freeze_sha256':'bad'})

def test_budget():
    end,F=R.budget(0,100,20,2880);assert F==120 and end==540
    with pytest.raises(ValueError):R.budget(0,2500,20,2880)
    with pytest.raises(ValueError):R.budget(0,1000,20,500)

@pytest.mark.parametrize('gate_ok',[True,False])
def test_mock_worker_grid_and_gate_stop(tmp_path,monkeypatch,gate_ok):
    plan=json.loads(PLAN.read_text());plan['source_files']={};pp=tmp_path/'plan.json';P.dump(pp,plan)
    q=tmp_path/'assignment.json';now=time.time();P.dump(q,dict(issuer='integrator',experiment='W12',pod_id='p',plan_sha256=P.sha(pp),previous_gpu_seconds=0,source_published=True,external_hardstop_verified=True,release_seals_verified=True,provider_created_epoch=now-1,deadline_epoch=now+2800))
    gate=json.loads((BANK/'W1_GATE.json').read_text());refs=iter(x['reference'] if gate_ok else 0 for x in gate.values());monkeypatch.setattr(A,'auc',lambda *a:next(refs))
    captures=[]
    class Engine:
        def __init__(self,*a):pass
        def capture(self,items):captures.append(1);return {l:torch.arange(len(items)).float().reshape(-1,1) for l in (42,44)}
        def score(self,reader,h,pairs):return torch.stack([h[:,0],h[:,0]+1])
    monkeypatch.setattr(R,'Engine',Engine);monkeypatch.setattr(R.sys,'prefix','/weights/venv');monkeypatch.setenv('RUNPOD_POD_ID','p')
    monkeypatch.setattr(torch.cuda,'synchronize',lambda:None);monkeypatch.setattr(R.signal,'signal',lambda *a:None);monkeypatch.setattr(R.signal,'setitimer',lambda *a:None)
    args=SimpleNamespace(bank=BANK,plan=pp,assignment=q,assets=tmp_path/'assets',out=tmp_path/'out')
    if gate_ok:
        R.run(args);P.verify(args.out,'SCORE_SEAL.json');rr=P.rows(args.out/'scores.jsonl');assert len(rr)==8064
        assert len({(x['id'],x['reader'],x['arm']) for x in rr})==8064
        true={x['id']:x['scores'] for x in rr if x['reader']=='olens' and x['arm']=='true'};items={x['id']:x for x in P.rows(BANK/'items.input.jsonl')}
        assert all(x['scores']==true[items[x['id']]['donor_id']] for x in rr if x['reader']=='olens' and x['arm']=='mismatched')
        with pytest.raises(FileExistsError):R.run(args)
    else:
        with pytest.raises(ValueError,match='score parity'):R.run(args)
        assert not captures and not (args.out/'scores.jsonl').exists()
