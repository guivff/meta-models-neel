"""Cold deployment contract tests; no installs, model downloads, APIs or SSH."""
from pathlib import Path
from types import SimpleNamespace
import json
import time
import pytest
from projects.g_agreement.r_bench import remainder_cold_setup as c


def test_exact_pinned_assets_and_subfolders():
    r5=c.assets('r5');r4=c.assets('r4');r2=c.assets('r2')
    assert len(r5)==2 and len(r4)==5 and len(r2)==3
    assert r2==c.assets('r3')==c.assets('r6')
    assert r5[0]['revision']=='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
    assert r5[1]['patterns']==['olens_s3d_rl600/*']
    nla=next(x for x in r4 if x['repo']=='ceselder/qwen3.6-27b-nla-rl')
    assert nla['patterns']==['av_base/*','av_rl_adapters/iter_000400/*','nla_meta.yaml']
    assert all(len(x['revision'])==40 for x in r4)
    assert all('ar_' not in x for x in nla['patterns'])


def test_runtime_gate_preserves_image_cuda_torch():
    c.require_runtime((3,12),'2.8.0+cu128','12.8')
    with pytest.raises(ValueError,match='Python'): c.require_runtime((3,11),'2.8.0+cu128','12.8')
    with pytest.raises(ValueError,match='torch'): c.require_runtime((3,12),'2.9.0','12.8')
    with pytest.raises(ValueError,match='torch'): c.require_runtime((3,12),'2.8.0',None)
    assert not any(x.startswith('torch=') for x in c.PINS)


def test_disk_requires_large_filesystem_and_actual_room(tmp_path):
    good=SimpleNamespace(total=200_000_000_000,free=150_000_000_000)
    assert c.disk_preflight('r4',tmp_path,good)['minimum_free_bytes']==140_000_000_000
    assert c.disk_preflight('r5',tmp_path,good)['minimum_free_bytes']==75_000_000_000
    with pytest.raises(ValueError): c.disk_preflight('r4',tmp_path,SimpleNamespace(total=200_000_000_000,free=130_000_000_000))
    with pytest.raises(ValueError): c.disk_preflight('r5',tmp_path,SimpleNamespace(total=100_000_000_000,free=90_000_000_000))


def test_chain_keeps_system_torch_and_existing_science(tmp_path):
    commands=c.phases('r4','p',tmp_path,python='python3')
    assert [n for n,_ in commands]==['venv','dependencies','assets','science']
    assert '--system-site-packages' in commands[0][1]
    assert '--constraint' in commands[1][1] and '--no-input' in commands[1][1]
    assert 'projects.g_agreement.r_bench.remainder_deploy' in commands[-1][1]
    assert [n for n,_ in c.phases('r2','p',tmp_path,setup_only=True)]==['venv','dependencies','assets']
    with pytest.raises(ValueError): c.phases('r6','p',tmp_path)


def test_emit_id_check_before_sourcing_without_credential_transfer():
    text=c.emit('r4','p',Path('/workspace/remainder/r4/unique'))
    assert text.index('POD ID MISMATCH')<text.index('source /workspace/.env')
    assert 'RUNPOD_API_KEY=' not in text and 'HF_TOKEN=' not in text
    assert 'trap ' not in text and 'selfstop' not in text
    assert 'echo $$' in text and 'R_GIT_SHA=' in text
    with pytest.raises(ValueError): c.emit('r4','p',Path('/workspace/remainder/r5/run'))


def test_pull_reserve_prevents_child_start(tmp_path,monkeypatch):
    monkeypatch.setattr(c,'guard',lambda *args:({},b'guard'))
    monkeypatch.setattr(c.subprocess,'Popen',lambda *args,**kwargs:pytest.fail('Must not launch'))
    with pytest.raises(RuntimeError,match='Pull reserve'):
        c.bounded(['no-command'],'r4','p',tmp_path,b'guard',time.time()+299)


def test_setup_failure_is_durable_and_never_claims_science(tmp_path,monkeypatch):
    run=tmp_path/'run';root=run/'repo';root.mkdir(parents=True)
    monkeypatch.setattr(c,'ROOT',root)
    monkeypatch.setattr(c,'guard',lambda *args:({'deadline_epoch':time.time()+1200},b'guard'))
    def fail(): raise ValueError('runtime rejected')
    monkeypatch.setattr(c,'require_runtime',fail)
    assert c.run('r2','p',run,setup_only=True)==1
    status=json.loads((run/'cold_status.json').read_text())
    assert status['state']=='FAILED' and status['error']=='runtime rejected'
    assert (run/'COLD_SETUP_FAILED').exists() and not (run/'DONE').exists()
    assert (run/'deliverables/operations/cold_status.json').exists()
    with pytest.raises(ValueError,match='retry'): c.run('r2','p',run,setup_only=True)


def test_setup_only_reports_authoritative_cache_without_science(tmp_path,monkeypatch):
    run=tmp_path/'run';root=run/'repo';root.mkdir(parents=True)
    monkeypatch.setattr(c,'ROOT',root)
    monkeypatch.setattr(c,'guard',lambda *args:({'deadline_epoch':time.time()+1200},b'guard'))
    monkeypatch.setattr(c,'require_runtime',lambda:{'torch':'2.8.0+cu128'})
    monkeypatch.setattr(c,'disk_preflight',lambda *args:{'free_bytes':200_000_000_000})
    monkeypatch.setattr(c,'phases',lambda *args,**kwargs:[])
    monkeypatch.setenv('HF_HOME','/workspace/explicit-hf')
    monkeypatch.setenv('HF_HUB_CACHE','/workspace/explicit-hub')
    assert c.run('r3','p',run,setup_only=True)==0
    status=json.loads((run/'cold_status.json').read_text())
    assert status['hf_home']=='/workspace/explicit-hf' and status['hf_hub_cache']=='/workspace/explicit-hub'
    assert (run/'COLD_SETUP_DONE').exists() and not (run/'DONE').exists()
    assert (run/'torch_constraint.txt').read_text()=='torch==2.8.0+cu128\n'


def test_sigterm_raises_into_bounded_cleanup():
    import signal
    with pytest.raises(RuntimeError,match='interrupted'):
        c.interrupted(signal.SIGTERM,None)


def test_descendant_groups_include_nested_sessions_only(tmp_path):
    # /proc stat: pid (comm) state ppid pgrp ...
    for pid,parent,group in [(10,1,10),(20,10,20),(30,20,30),(40,1,40)]:
        folder=tmp_path/str(pid);folder.mkdir()
        (folder/'stat').write_text(f'{pid} (worker with space) S {parent} {group} 0')
    assert c.descendant_groups(10,tmp_path)=={10,20,30}
