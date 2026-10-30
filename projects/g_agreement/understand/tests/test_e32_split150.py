import pytest,numpy as np,torch
from types import SimpleNamespace
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand import e32_split150 as R
@pytest.mark.parametrize('content_ok',[True,False])
def test_split_complete_grid_and_content_gate(tmp_path,monkeypatch,content_ok):
    import json
    from projects.g_agreement.blindspot import protocol as P
    b=tmp_path/'bank';b.mkdir();items=[];refs={};pairs={'w1':{},'e30':{}}
    for i in range(25):
        f=f'r{i}';refs[f]={'D':1.,'class':'semantic' if i<9 else 'structure'}
        for cs in pairs:pairs[cs][f]=[['a','b'],['c','d']]
        for j in range(84):items.append(dict(id=f'{f}:{j}',feature=f,text='t',ids=[1],label=j%2,cluster=str(j//14)))
    P.jsonl(b/'items.jsonl',items);P.dump(b/'pairs.json',pairs);P.dump(b/'references.json',refs);P.dump(b/'DONORS.json',{})
    np.save(b/'reference44.npy',np.ones((2100,2),dtype=np.float32));P.seal(b,[p.name for p in b.iterdir()],'TEST')
    plan=tmp_path/'plan.json';P.dump(plan,{'remaining_gpu_seconds':3600,'science_cap_seconds':3600,'capture_assignment_sha256':'capture','source_files':{},'input_seal_sha256':P.sha(b/'INPUT_SEAL.json'),'high_D_rows':[f'r{i}' for i in range(9,17)]})
    assets=tmp_path/'assets.json';P.dump(assets,{})
    assignment=tmp_path/'assignment.json';now=R.time.time()
    P.dump(assignment,dict(issuer='integrator',experiment='E32',pod_id='test',plan_sha256=P.sha(plan),assets_manifest_sha256=P.sha(assets),previous_gpu_seconds=0,external_hardstop_verified=True,source_published=True,provider_created_epoch=now-1,deadline_epoch=now+3700,science_cap_seconds=3600,gate_assets_manifest_sha256=P.sha(assets)))
    class Fake:
        def __init__(self,*a):self.tok=SimpleNamespace(encode=lambda *a,**k:[62])
        def capture(self,items):
            self.last_capture_metadata=[{'id':x['id'],'capture_mode':mode,'padding_length':0} for x in items]
            return {l:torch.ones(2100,2) for l in range(64)}
        def score(self,group,pairs,arm,*a):return [float(x['label']) if arm=='A' or content_ok else 0. for x in group]
    capture=tmp_path/'capture';capture.mkdir()
    for l in range(64):np.save(capture/f'acts{l}.npy',np.ones((2100,2),dtype=np.float32))
    P.dump(capture/'CAPTURE_SEAL.json',{'files':{}})
    monkeypatch.setattr(R,'verify_capture',lambda *a:None)
    def gate(bank,assets,out,plan):P.dump(out/'SCORE_PARITY_SEAL.json',{'files':{},'status':'PASS'})
    monkeypatch.setattr(R,'score_parity',gate);monkeypatch.setattr(R.sys,'prefix','/weights/venv-kernels')
    monkeypatch.setattr(R,'Engine',Fake);monkeypatch.setenv('RUNPOD_POD_ID','test');monkeypatch.setattr(torch.cuda,'is_available',lambda:True);monkeypatch.setattr(torch.cuda,'synchronize',lambda:None)
    monkeypatch.setattr(R.signal,'signal',lambda *a:None);monkeypatch.setattr(R.signal,'setitimer',lambda *a:None)
    out=tmp_path/'out';R.run(SimpleNamespace(plan=plan,bank=b,assignment=assignment,assets=assets,out=out,capture=capture,gate_bank=b,gate_assets=assets))
    if content_ok:
        P.verify(out,'SCORE_SEAL.json');assert len(P.rows(out/'scores.jsonl'))==25200
    else:
        P.verify(out,'GATE_SEAL.json');assert not (out/'SCORE_SEAL.json').exists()
        assert all(x['arm']=='A' or refs[x['feature']]['class']=='semantic' for x in P.rows(out/'gate_scores.jsonl'))


@pytest.mark.parametrize('delta',[.019,.021])
def test_score_parity_threshold(tmp_path,monkeypatch,delta):
    bank=tmp_path/'gate';bank.mkdir();out=tmp_path/'out';out.mkdir()
    P.dump(bank/'W1_GATE.json',{r:{'indices':[0,1],'pairs':[['a','b'],['c','d']],'labels':[0,1],'reference':.7} for r in ('prose_paren','python_string','prose_sentiment')})
    np.save(bank/'W1_GATE44.npy',np.ones((2,2),dtype=np.float32));P.seal(bank,[p.name for p in bank.iterdir()],'TEST')
    monkeypatch.setattr(R.W,'_assets',lambda *a,**k:{})
    monkeypatch.setattr(R.W,'_load_oracle',lambda *a:SimpleNamespace(paired_logodds_templates=lambda *a:torch.ones((2,2))))
    monkeypatch.setattr(R,'auc',lambda *a:.7+delta);monkeypatch.setattr(torch.cuda,'empty_cache',lambda:None)
    if delta>.02:
        with pytest.raises(ValueError,match='score parity failed'):R.score_parity(bank,tmp_path,out,{'score_gate_input_seal_sha256':P.sha(bank/'INPUT_SEAL.json')})
        assert R.E.read(out/'SCORE_PARITY_SEAL.json')['status']=='FAIL'
    else:
        R.score_parity(bank,tmp_path,out,{'score_gate_input_seal_sha256':P.sha(bank/'INPUT_SEAL.json')})
        assert R.E.read(out/'SCORE_PARITY_SEAL.json')['status']=='PASS'


def test_two_stage_analysis_failure_keeps_guard(tmp_path):
    from projects.g_agreement.understand.e32_analysis150 import run
    spec=tmp_path/'spec';P.dump(spec,{'lock':str(tmp_path/'lock'),'pins':{str(tmp_path/'absent'):'bad'}})
    with pytest.raises(FileNotFoundError):run(spec,P.sha(spec))
    with pytest.raises(FileExistsError):run(spec,P.sha(spec))
