import ast
import builtins
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from projects.g_agreement.blindspot import protocol as P


def assignment(tmp_path):
    root=tmp_path/'repo';(root/'projects/g_agreement').mkdir(parents=True)
    (root/P.BRIEF).write_text('registered test fixture')
    a={'issuer':'integrator','pod_id':'test-pod','experiment':'W1','previous_gpu_seconds':0,'brief_pushed':True,'brief_registered':True,'brief_commit':'a'*40,'source_commit':'b'*40,'brief_sha256':P.sha(root/P.BRIEF),'source_files':P.code_hashes(root),'provider_created_epoch':0,'deadline_epoch':1000,'allocated_gpu_seconds':1000,'external_hardstop_verified':True}
    path=tmp_path/'assignment.json';P.dump(path,a)
    return root,path,a


def test_admission_requires_published_brief_and_correct_pod(tmp_path):
    root,path,a=assignment(tmp_path)
    assert P.admit(path,root,now=10,pod_id='test-pod')['pod_id']=='test-pod'
    with pytest.raises(ValueError,match='RunPod'): P.admit(path,root,now=10,pod_id='other')
    a['brief_pushed']=False;P.dump(path,a)
    with pytest.raises(ValueError,match='pushed'): P.admit(path,root,now=10,pod_id='test-pod')


@pytest.mark.parametrize('change',[{'deadline_epoch':1100},{'provider_created_epoch':50},{'brief_registered':False},{'source_files':{}},{'external_hardstop_verified':False}])
def test_gate_rejects_invalid_receipts(tmp_path,change):
    root,path,a=assignment(tmp_path);a.update(change);P.dump(path,a)
    with pytest.raises(ValueError):P.admit(path,root,now=10,pod_id='test-pod')


def test_gate_rejects_expiry_and_changed_brief(tmp_path):
    root,path,a=assignment(tmp_path)
    with pytest.raises(ValueError,match='reserve'):P.admit(path,root,now=900,pod_id='test-pod')
    (root/P.BRIEF).write_text('edited after registration')
    with pytest.raises(ValueError,match='bytes'):P.admit(path,root,now=10,pod_id='test-pod')


@pytest.mark.parametrize('experiment,cap', [('W1',7200),('W5',1800),('W1b',3600)])
def test_registered_caps_include_previous_provider_custody(tmp_path,experiment,cap):
    root,path,a=assignment(tmp_path)
    a.update(experiment=experiment,allocated_gpu_seconds=cap,deadline_epoch=cap)
    P.dump(path,a)
    assert P.admit(path,root,now=10,pod_id='test-pod',experiment=experiment)
    a['previous_gpu_seconds']=1
    P.dump(path,a)
    with pytest.raises(ValueError,match='cap'):P.admit(path,root,now=10,pod_id='test-pod',experiment=experiment)


def test_admission_binds_committed_bank_before_capture(tmp_path):
    root,path,a=assignment(tmp_path)
    (root/'projects/g_agreement/manifest').mkdir()
    P.dump(root/'projects/g_agreement/manifest/assets.json',{'target':{'files_needed':{'tokenizer.json_sha256':'d'*64}}})
    a['source_files']=P.code_hashes(root);P.dump(path,a)
    bank=tmp_path/'bank';bank.mkdir()
    P.dump(bank/'manifest.json',{'source_files':P.code_hashes(root),'tokenizer_sha256':'d'*64})
    P.seal(bank,['manifest.json'],'INPUTS_FROZEN')
    with pytest.raises(ValueError,match='manifest'):P.admit(path,root,now=10,pod_id='test-pod',bank=bank)
    a.update(manifest_sha256=P.sha(bank/'manifest.json'),manifest_committed=True,manifest_commit='c'*40)
    P.dump(path,a)
    assert P.admit(path,root,now=10,pod_id='test-pod',bank=bank)
    with pytest.raises(ValueError,match='experiment'):P.admit(path,root,now=10,pod_id='test-pod',bank=bank,experiment='W5')


def test_score_tampering_rejected_before_label_open(tmp_path,monkeypatch):
    from projects.g_agreement.blindspot.run import analyse
    target=tmp_path/'target';target.mkdir()
    (target/'scores').write_text('original')
    P.seal(target,['scores'],'SCORES_SEALED_TEST')
    (target/'scores').write_text('changed')
    labels=tmp_path/'labels'
    original=Path.read_text
    def guarded(path,*a,**kw):
        assert path!=labels,'labels opened before score validation'
        return original(path,*a,**kw)
    monkeypatch.setattr(Path,'read_text',guarded)
    args=SimpleNamespace(target=target,nla=tmp_path/'nla',bank=tmp_path/'bank',labels=labels,out=tmp_path/'out')
    with pytest.raises(ValueError,match='seal mismatch'):analyse(args)


def test_no_infra_or_modal_imports():
    root=Path(__file__).resolve().parents[1]
    for path in list(root.glob('*.py'))+[P.ROOT/'common/__init__.py',P.ROOT/'projects/g_agreement/w_claims/ar.py']:
        tree=ast.parse(path.read_text())
        for n in ast.walk(tree):
            if isinstance(n,ast.Import): names=[a.name for a in n.names]
            elif isinstance(n,ast.ImportFrom):names=[n.module or '']
            else:continue
            assert all('infra' not in x.split('.') and not any(p.endswith('_modal') or p=='modal' for p in x.split('.')) for x in names)


def test_plan_and_help_do_not_import_model_libraries(monkeypatch,capsys):
    from projects.g_agreement.blindspot.run import main
    old=builtins.__import__
    def checked(name,*a,**kw):
        assert name.split('.')[0] not in {'torch','transformers','peft','oracle_lens'},name
        return old(name,*a,**kw)
    monkeypatch.setattr(builtins,'__import__',checked)
    main(['plan'])
    assert 'BLOCKED' in capsys.readouterr().out


def test_failed_real_worker_cannot_load_a_model(tmp_path,monkeypatch):
    from projects.g_agreement.blindspot.run import target_phase
    old=builtins.__import__
    def checked(name,*a,**kw):
        assert name.split('.')[0] not in {'torch','transformers','peft'},name
        return old(name,*a,**kw)
    monkeypatch.setattr(builtins,'__import__',checked)
    path=tmp_path/'assignment.json';P.dump(path,{'issuer':'wrong'})
    with pytest.raises(ValueError,match='integrator'):
        target_phase(SimpleNamespace(assignment=path))


def test_explicit_integrator_staging_does_not_consume_science_cap(tmp_path):
    root,path,a=assignment(tmp_path)
    a.update(allocated_gpu_seconds=8100.326,science_cap_gpu_seconds=7200,
             staging_allowance_seconds=900.326,deadline_epoch=8100.326)
    P.dump(path,a)
    assert P.admit(path,root,now=10,pod_id="test-pod")
    a["science_cap_gpu_seconds"]=7201; P.dump(path,a)
    with pytest.raises(ValueError,match="cap"):
        P.admit(path,root,now=10,pod_id="test-pod")
    a.update(science_cap_gpu_seconds=7200,staging_allowance_seconds=899)
    P.dump(path,a)
    with pytest.raises(ValueError,match="staging"):
        P.admit(path,root,now=10,pod_id="test-pod")


def science_assignment(tmp_path):
    root,path,a=assignment(tmp_path)
    a.update(allocated_gpu_seconds=1900,deadline_epoch=1900,
             science_cap_gpu_seconds=1000,staging_allowance_seconds=900)
    P.dump(path,a)
    return root,path,P.admit(path,root,now=10,pod_id="test-pod")


def test_first_science_not_creation_plus_setup_controls_stop(tmp_path):
    root,path,a=science_assignment(tmp_path)
    assert P.science_deadline(a,now=100)==900  # setup only; no science marker yet
    assert not Path(a['_science_clock_path']).exists()
    assert P.science_deadline(a,start=True,now=100)==1100
    # The former creation + 1900 - reserve deadline would allow 620 extra seconds.
    with pytest.raises(TimeoutError,match='science deadline'):
        P.science_deadline(a,start=True,now=1100)


def test_science_start_cannot_reset_between_phases_or_processes(tmp_path):
    root,path,a=science_assignment(tmp_path)
    assert P.science_deadline(a,start=True,now=100)==1100
    second=P.admit(path,root,now=600,pod_id='test-pod')
    assert P.science_deadline(second,start=True,now=700)==1100
    assert json.loads(Path(a['_science_clock_path']).read_text())['first_science_epoch']==100
    with pytest.raises(TimeoutError):P.admit(path,root,now=1100,pod_id='test-pod')


def test_science_must_start_within_setup_and_respects_absolute_stop(tmp_path):
    root,path,a=science_assignment(tmp_path)
    with pytest.raises(TimeoutError,match='setup allowance'):
        P.science_deadline(a,start=True,now=900)
    assert P.science_deadline(a,start=True,now=850)==1720  # absolute minus reserve


def test_changed_assignment_cannot_rebind_existing_science_clock(tmp_path):
    root,path,a=science_assignment(tmp_path)
    P.science_deadline(a,start=True,now=100)
    receipt=json.loads(path.read_text());receipt['source_commit']='d'*40;P.dump(path,receipt)
    with pytest.raises(ValueError,match='clock'):
        P.admit(path,root,now=200,pod_id='test-pod')


def test_science_checkpoint_rearms_inflight_signal_before_forward(tmp_path,monkeypatch):
    root,path,a=science_assignment(tmp_path)
    alarms=[]
    monkeypatch.setattr(P.time,'time',lambda:100)
    monkeypatch.setattr(P.signal,'signal',lambda *args:None)
    monkeypatch.setattr(P.signal,'setitimer',lambda *args:alarms.append(args))
    with P.compute_window(a):
        assert alarms[-1][1]==800  # setup gate
        P.science_checkpoint(a)
        assert alarms[-1][1]==1000  # science starts now, not creation + allowance
    assert alarms[-1][1]==0 and '_compute_timer_active' not in a


def test_w5_completion_increase_cannot_enable_recapture_entrypoint(tmp_path):
    root,path,a=assignment(tmp_path)
    a.update(experiment='W5',run_kind=P.W5_COMPLETION_KIND,budget_amendment_commit=P.W5_COMPLETION_AMENDMENT,
             allocated_gpu_seconds=4500,deadline_epoch=4500,science_cap_gpu_seconds=3600,staging_allowance_seconds=900)
    P.dump(path,a)
    with pytest.raises(ValueError,match='scoring-only'):P.admit(path,root,now=10,pod_id='test-pod')
    assert P.admit(path,root,now=10,pod_id='test-pod',run_kind=P.W5_COMPLETION_KIND)
    a['science_cap_gpu_seconds']=3601;P.dump(path,a)
    with pytest.raises(ValueError,match='cap'):P.admit(path,root,now=10,pod_id='test-pod',run_kind=P.W5_COMPLETION_KIND)
