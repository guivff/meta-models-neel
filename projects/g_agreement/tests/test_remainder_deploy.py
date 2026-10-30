"""Offline deployment safety/portability tests. No network or model loading."""
import json
from pathlib import Path
import time
import pytest
from projects.g_agreement.r_bench import remainder_deploy as d


def test_commands_preserve_one_deadline_and_explicit_pod():
    for exp in ('r4','r5'):
        deadline=1234567890
        commands=d.phase_commands(exp,'own-pod',Path('/workspace/remainder')/exp/'run',deadline,'python')
        assert [x[0] for x in commands]==['environment','preflight','live-smoke','run','audit']
        for _,args in commands[2:4]:
            assert args[args.index('--pod')+1]=='own-pod'
            flag='--deadline-utc' if exp=='r4' else '--deadline-epoch'
            value=args[args.index(flag)+1]
            assert value==('2009-02-13T23:31:30+00:00' if exp=='r4' else str(deadline))
        assert all('analyze' not in args for _,args in commands)


def test_emit_has_first_identity_check_no_stop_or_trap():
    text=d.emit('r4','mypod',Path('/workspace/remainder/r4/run'),'python')
    assert text.index('POD ID MISMATCH') < text.index('cd "$RUN/repo"')
    assert 'trap ' not in text and 'selfstop' not in text and 'hardstop.sh' not in text
    assert 'HF_HUB_OFFLINE=1' in text and 'TRANSFORMERS_OFFLINE=1' in text
    assert text.index('POD ID MISMATCH') < text.index('source /workspace/.env')
    assert 'R_GIT_SHA="$(cat GIT_SHA)"' in text
    assert 'RUNPOD_API_KEY=' not in text and 'HF_TOKEN=' not in text
    assert '--pod mypod' in text
    with pytest.raises(ValueError): d.emit('r4','bad;pod',Path('/workspace/remainder/r4/run'))
    with pytest.raises(ValueError): d.emit('r5','mypod',Path('/workspace/remainder/r4/run'))


def test_guard_identity_and_cap(tmp_path):
    now=time.time()
    g={'pod':'p','experiment':'r5','started_epoch':now-10,'deadline_epoch':now+1700}
    (tmp_path/'guard.json').write_text(json.dumps(g))
    assert d.validate_identity('r5','p',tmp_path,b'RUNPOD_POD_ID=p\0')==g
    with pytest.raises(ValueError): d.validate_identity('r5','p',tmp_path,b'RUNPOD_POD_ID=other\0')
    g['deadline_epoch']=now+1900
    (tmp_path/'guard.json').write_text(json.dumps(g))
    with pytest.raises(ValueError): d.validate_identity('r5','p',tmp_path,b'RUNPOD_POD_ID=p\0')


def test_bundle_only_owned_evidence_and_hashes(tmp_path):
    root=tmp_path/'repo'; run=tmp_path/'run'; run.mkdir()
    a=root/'cache/g_agreement/r/remainder/r4/a.json'; a.parent.mkdir(parents=True); a.write_text('{}')
    other=root/'cache/g_agreement/r/remainder/r5/secret'; other.parent.mkdir(); other.write_text('no')
    (run/'.env').write_text('do not copy')
    (run/'job.log').write_text('log')
    files=d.bundle('r4',run,root)
    assert 'cache/g_agreement/r/remainder/r4/a.json' in files
    assert 'operations/job.log' in files
    assert all('secret' not in f and '.env' not in f for f in files)
    assert not json.loads((run/'pull_manifest.json').read_text())['complete_job']
    a.with_name('link').symlink_to(a)
    with pytest.raises(ValueError): d.bundle('r4',run,root)


def test_source_paths_are_portable_and_whole_arrays(tmp_path):
    root=tmp_path
    p=root/'results/g_agreement/r/remainder/r4/preflight.json'; p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'facts':{'fact':{'state_path':'cache/g_agreement/r/states/fact/chat_L42.npy'}}}))
    paths=d.source_paths('r4',root)
    assert 'cache/g_agreement/r/states/fact/index.json' in paths
    assert len(paths)==6 and all(not Path(x).is_absolute() for x in paths)
    p.write_text(json.dumps({'facts':{'fact':{'state_path':'../../bad'}}}))
    with pytest.raises(ValueError): d.source_paths('r4',root)


def test_cold_assets_are_read_only_failures(tmp_path,monkeypatch):
    monkeypatch.delenv('HF_HUB_CACHE',raising=False)
    r4=d.asset_inventory('r4',tmp_path)
    r5=d.asset_inventory('r5',tmp_path)
    assert len(r4['assets'])==6 and len(r5['assets'])==2
    assert r4['missing'] and r5['missing']
    assert not list(tmp_path.iterdir())


def test_execute_failure_writes_metadata_and_stops_chain(tmp_path,monkeypatch):
    run=tmp_path/'run'; root=run/'repo'; root.mkdir(parents=True)
    (run/'guard.json').write_text('{}')
    (run/'ARMED').touch()
    for name in ('watchdog','hardstop'):
        (run/f'{name}.log').write_text('armed: p')
        (run/f'{name}.pid').write_text(str(d.os.getpid()))
    monkeypatch.setattr(d,'ROOT',root)
    monkeypatch.setattr(d,'validate_identity',lambda *args:{'deadline_epoch':time.time()+600})
    monkeypatch.setattr(d,'phase_commands',lambda *args:[('failure',[d.sys.executable,'-c','raise SystemExit(7)']),('never',['false'])])
    calls=[]
    monkeypatch.setattr(d,'bundle',lambda *args:calls.append('bundle'))
    assert d.execute('r4','p',run)==1
    status=json.loads((run/'job_status.json').read_text())
    assert status['state']=='FAILED' and len(status['phases'])==1
    assert status['phases'][0]['returncode']==7
    assert (run/'FAILED').exists() and not (run/'DONE').exists() and calls
    with pytest.raises(ValueError): d.execute('r4','p',run)


def test_execute_reserves_pull_without_launching(tmp_path,monkeypatch):
    run=tmp_path/'run'; root=run/'repo'; root.mkdir(parents=True)
    (run/'guard.json').write_text('{}')
    (run/'ARMED').touch()
    for name in ('watchdog','hardstop'):
        (run/f'{name}.log').write_text('armed: p')
        (run/f'{name}.pid').write_text(str(d.os.getpid()))
    monkeypatch.setattr(d,'ROOT',root)
    monkeypatch.setattr(d,'validate_identity',lambda *args:{'deadline_epoch':time.time()+299})
    monkeypatch.setattr(d,'bundle',lambda *args:None)
    monkeypatch.setattr(d.subprocess,'Popen',lambda *args,**kwargs:pytest.fail('No phase may launch'))
    assert d.execute('r5','p',run)==1
    assert 'Pull reserve' in json.loads((run/'job_status.json').read_text())['error']
