import json
from pathlib import Path
import numpy as np
import pytest
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand import once149 as O
from projects.g_agreement.blindspot import w12_analysis149 as W


def test_once_failure_consumes_attempt(tmp_path):
    m=tmp_path/'request.json';lock=tmp_path/'once.lock'
    P.dump(m,{'lock':str(lock),'out':str(tmp_path/'out'),'pins':{str(tmp_path/'missing'):'bad'},'task':'w12'})
    with pytest.raises(FileNotFoundError):O.execute(m)
    assert json.loads(lock.with_suffix('.receipt.json').read_text())['status']=='STOP_OWNER_REQUIRED'
    with pytest.raises(FileExistsError):O.execute(m)


def test_w12_mock_analysis_and_gate(tmp_path,monkeypatch):
    root=P.ROOT;bank=root/'cache/g_agreement/blindspot/w12-reader-stage'
    freeze=root/'results/g_agreement/blindspot/w12/freeze';plan=root/'results/g_agreement/blindspot/w12/launch/RUN_PLAN.json'
    source=tmp_path/'source';source.mkdir();items=P.rows(bank/'items.input.jsonl')
    P.dump(source/'ORDER.json',[x['id'] for x in items]);pd=json.loads(plan.read_text())
    P.dump(source/'BINDING.json',{**{k:pd[k] for k in ('input_seal_sha256','freeze_sha256','values_seal_sha256','predictions_seal_sha256')},'plan_sha256':P.sha(plan)})
    for l in (42,44):np.save(source/f'acts{l}.npy',np.zeros((1008,2),dtype=np.float32))
    P.jsonl(source/'scores.jsonl',[{'id':x['id'],'feature':x['feature'],'reader':r,'layer':l,'arm':arm,'status':'COMPLETE','scores':[0.,0.]} for x in items for r,l in W.READERS.items() for arm in ('true','mismatched')])
    for n,status in [('SCORE_SEAL.json','W12_ASKED_ONLY_COMPLETE'),('CAPTURE_SEAL.json','CAPTURE'),('W1_PARITY_SEAL.json','PASS')]:P.dump(source/n,{'files':{},'status':status})
    called=[]
    def compute(*args,**kwargs):
        called.append(True);assert kwargs['export_dev'] is False
        return [],[],{},[]
    monkeypatch.setattr(W.A,'_analyse_cells',compute)
    W.analyse(bank,source,freeze,plan,tmp_path/'out');assert called
    assert (tmp_path/'out/ANALYSIS_SEAL.json').exists()
    called.clear();P.dump(source/'W1_PARITY_SEAL.json',{'files':{},'status':'FAIL'})
    with pytest.raises(ValueError,match='parity'):W.analyse(bank,source,freeze,plan,tmp_path/'bad')
    assert not called
