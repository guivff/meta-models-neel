import json
from pathlib import Path
from contextlib import contextmanager
import numpy as np
import pytest
from projects.g_agreement.understand import packed as R,core as K,e5,e6,e8
from projects.g_agreement.blindspot import protocol as P


def test_all_e5_pairs_and_native_query_limitation_frozen():
    specs=e5.phrasings()
    assert set(specs)==set(e5.FEATURES)
    for spec in specs.values():
        assert len(spec['kinds'])==8 and len(set(spec['kinds']))==8
        for reader,_ in K.READERS:
            assert len(spec[reader])==8 and all(a!=b for a,b in spec[reader])
        assert not spec['jlens_supported']


def test_independent_science_clocks_do_not_use_pod_creation_or_reset(tmp_path,monkeypatch):
    monkeypatch.setattr(R.signal,'setitimer',lambda *args:None)
    for name in R.ORDER:(tmp_path/name).mkdir()
    one=R.Window('E5',tmp_path/'E5',10000,'pod',now=lambda:100)
    two=R.Window('E8',tmp_path/'E8',10000,'pod',now=lambda:1700)
    assert one.deadline==1180 and two.deadline==5300
    assert json.loads((tmp_path/'E8/EXPERIMENT_CLOCK.json').read_text())['first_science_epoch']==1700
    with pytest.raises(FileExistsError):R.Window('E5',tmp_path/'E5',10000,'pod',now=lambda:2000)


def test_scope_gate_cannot_borrow_from_another_experiment(tmp_path,monkeypatch):
    monkeypatch.setattr(R.signal,'setitimer',lambda *args:None)
    window=R.Window('E5',tmp_path,10000,'pod',now=lambda:100)
    with pytest.raises(R.BudgetStop,match='NO_FIT'):window.gate(2000,[])
    assert window.first==100 and window.deadline==1180


def test_gain_does_not_select_linear_range_after_outcome_or_flip_sign():
    r=e8.gains([0,1,2,0,-1,-2],1.5)
    assert r['low_dose_gain']==pytest.approx(2) and r['dose_reaching_A_median']==1
    assert e8.gains([0,-1,-2,-4,-8,-16],1)['dose_reaching_A_median'] is None


def test_script_proxies_and_refusal_markers():
    assert e6.behaviour('prose_paren',') then (')==1
    assert e6.behaviour('prose_paren','( then )')==0
    assert e6.behaviour('prose_paren','no bracket')==.5
    assert e6.behaviour('python_indent','tail\n    x')==1
    assert e6.behaviour('python_indent','tail\n            x')==0
    assert e6.behaviour('list_depth','- item')==1
    assert e6.behaviour('list_depth','    - item')==0
    assert e6.format_status('I cannot continue this')=='EXPLICIT_CONTINUATION_REFUSAL'
    assert e6.format_status('<explanation> a cell')=='DESCRIPTIVE_FORMAT_MARKER'


def test_pack_orchestrates_in_order_and_loads_models_once(tmp_path,monkeypatch):
    import torch,time
    from types import SimpleNamespace
    import mats.readers.nla,mats.readers.jlens
    monkeypatch.setattr(R.signal,'setitimer',lambda *args:None)
    monkeypatch.setattr(torch.cuda,'synchronize',lambda:None)
    monkeypatch.setenv('RUNPOD_POD_ID','test-pod')
    children={};spec={r:[['a','b'],['c','d']] for r,_ in K.READERS}
    spec['jlens_supported']=False
    for name in R.ORDER:
        child=tmp_path/name;child.mkdir()
        for site in (42,44):np.save(child/f'acts{site}.npy',np.ones((2,2),np.float32))
        P.jsonl(child/'items.input.jsonl',[{'id':str(i),'feature':'fixture'} for i in range(2)])
        P.dump(child/'templates.json',{'fixture':spec})
        P.dump(child/'plan.json',{'features':['fixture'],'source_files':{}})
        P.seal(child,['acts42.npy','acts44.npy','items.input.jsonl','templates.json','plan.json'],'TEST')
        children[name]={'input_seal_sha256':P.sha(child/'INPUT_SEAL.json')}
    plan={'source_files':{},'order':list(R.ORDER),'per_experiment_caps':R.CAPS,'children':children}
    P.dump(tmp_path/'plan.json',plan)
    P.seal(tmp_path,[str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*') if p.is_file()],'TEST')
    now=time.time();a={'issuer':'integrator','experiment':'PACKED','pod_id':'test-pod','source_files':{},
        'plan_sha256':P.sha(tmp_path/'plan.json'),'previous_gpu_seconds':0,'provider_created_epoch':now-1,
        'deadline_epoch':now+7900,'allocated_gpu_seconds':7980,'science_cap_gpu_seconds':6480,'staging_allowance_seconds':1500,
        'brief_registered':True,'brief_pushed':True,'manifest_committed':True,'external_hardstop_verified':True}
    assignment=tmp_path/'assignment.json';P.dump(assignment,a)
    loads=[];model=SimpleNamespace(carrier=lambda *_:None)
    monkeypatch.setattr(W:=R.W,'_assets',lambda _: {'nla':'cached-nla','jlens':'cached-jlens'})
    monkeypatch.setattr(W,'_load_oracle',lambda *_:loads.append('olens') or model)
    monkeypatch.setattr(mats.readers.nla,'load_nla',lambda **_:loads.append('nla') or model)
    monkeypatch.setattr(mats.readers.jlens,'load_jlens',lambda *a,**k:loads.append('jlens') or model)
    model.model=model;model.tok=model
    monkeypatch.setattr(K,'score',lambda *a:None)
    @contextmanager
    def context(*_):yield model
    monkeypatch.setattr(e6,'continuation_reader',context);monkeypatch.setattr(e6,'generate',lambda *a:[])
    order=[]
    monkeypatch.setattr(R,'work',lambda name,*a:order.append(name) or {'experiment':name,'status':'SEALED'})
    R.run(tmp_path,assignment,tmp_path/'assets',tmp_path/'output')
    assert loads==['olens','nla','jlens'] and order==['E5','E8','E6']
