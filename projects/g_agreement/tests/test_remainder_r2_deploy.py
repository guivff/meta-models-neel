import copy
import json
import os
from pathlib import Path
import pytest
from projects.g_agreement.r_bench import remainder_r2_deploy as R

RUN=Path('/workspace/remainder/r2/booked-run')


def test_portable_inventory_and_paths(tmp_path):
    path=tmp_path/'results/g_agreement/r/remainder/r2/deployment_inputs.json';path.parent.mkdir(parents=True)
    item={'path':'cache/g_agreement/r/states/f/chat_L42.npy','bytes':12,'sha256':'a'*64}
    obj={'input_files':[item],'input_bytes':12,'input_file_count':1};path.write_text(json.dumps(obj))
    assert R.inputs(tmp_path)==obj
    for p in ('/etc/passwd','../other.npy','.env'):
        path.write_text(json.dumps({**obj,'input_files':[{**item,'path':p}]}))
        with pytest.raises(ValueError):R.inputs(tmp_path)
    R.check_path('pod123',RUN)
    for pod,run in [('bad;',RUN),('pod123',Path('/workspace/activation-readers')),('pod123',RUN/'../other')]:
        with pytest.raises(ValueError):R.check_path(pod,run)


def test_guard_binds_id_original_interval_and_reserve(tmp_path,monkeypatch):
    monkeypatch.setattr(R,'check_path',lambda *a:None)
    rec={'experiment':'r2','pod':'pod123','started_epoch':100,'deadline_epoch':1300}
    R.write(tmp_path/'guard.json',rec);(tmp_path/'ARMED').touch()
    assert R.guard('pod123',tmp_path,b'RUNPOD_POD_ID=pod123\0',now=200,check_processes=False)['deadline_epoch']==1300
    with pytest.raises(ValueError,match='MISMATCH'):R.guard('pod123',tmp_path,b'RUNPOD_POD_ID=other\0',now=200,check_processes=False)
    with pytest.raises(ValueError,match='reserve'):R.guard('pod123',tmp_path,b'RUNPOD_POD_ID=pod123\0',now=1000,check_processes=False)
    R.write(tmp_path/'guard.json',{**rec,'deadline_epoch':1301})
    with pytest.raises(ValueError,match='cap'):R.guard('pod123',tmp_path,b'RUNPOD_POD_ID=pod123\0',now=200,check_processes=False)


def measurement():
    g={'guard_sha256':'g','started_epoch':100,'deadline_epoch':1300}
    rec={'pod':'pod123','run_dir':str(RUN),'guard_sha256':'g','deadline_epoch':1300,'measured_on':'Mac','probe_sha256':'a'*64,
         'samples':[{'bytes':R.PROBE_BYTES,'seconds':s,'sha256':'a'*64} for s in (1,2)],
         'bytes_per_second':R.PROBE_BYTES/2,'measured_epoch':200}
    return rec,g


def test_measurement_requires_two_real_same_run_slow_rate_samples():
    rec,g=measurement();assert R.validate_measurement(rec,'pod123',RUN,g,now=300)==R.PROBE_BYTES/2
    for change in ({'bytes_per_second':R.PROBE_BYTES},{'guard_sha256':'new'},{'measured_on':'pod'},{'measured_epoch':99},{'samples':rec['samples'][:1]}):
        with pytest.raises(ValueError):R.validate_measurement({**rec,**change},'pod123',RUN,g,now=300)
    bad=copy.deepcopy(rec);bad['samples'][0]['sha256']='b'*64
    with pytest.raises(ValueError,match='checksum'):R.validate_measurement(bad,'pod123',RUN,g,now=300)


def test_chain_order_same_deadline_and_own_id_before_credentials():
    commands=R.phase_commands('pod123',RUN,1300,1000)
    assert [n for n,_ in commands]==['cold-setup','preflight','live-smoke','capture']
    assert '--setup-only' in commands[0][1]
    for name,cmd in commands[2:]:
        assert cmd[cmd.index('--deadline-epoch')+1]=='1300'
        assert cmd[cmd.index('--guard-dir')+1]==str(RUN)
    assert '--measured-pull-bytes-per-second' in commands[2][1]
    script=R.emit('pod123',RUN)
    assert script.index('POD ID MISMATCH')<script.index('source /workspace/.env')
    assert 'trap ' not in script and 'selfstop' not in script and 'HF_TOKEN=' not in script
    assert 'exec python3 -m '+R.MODULE in script


def test_bundle_uses_owned_hardlinks_and_omits_credentials(tmp_path):
    root=tmp_path/'repo';run=tmp_path/'run'
    source=root/'cache/g_agreement/r/remainder/r2/capture/data.npy';source.parent.mkdir(parents=True);source.write_bytes(b'owned-array')
    run.mkdir();(run/'.env').write_text('secret');(run/'job.log').write_text('operation log')
    result=R.bundle(run,root)
    dest=run/'deliverables/cache/g_agreement/r/remainder/r2/capture/data.npy'
    assert os.path.samefile(source,dest) and result['files']==2
    assert not (run/'deliverables/operations/.env').exists()
    assert (run/'deliverables/operations/job.log').read_text()=='operation log'
    (source.parent/'bad').symlink_to(source)
    with pytest.raises(ValueError,match='Symlink'):R.bundle(run,root)


def test_probe_is_incompressible_size_checked_and_cannot_be_reused(tmp_path,monkeypatch):
    monkeypatch.setattr(R,'guard',lambda *args:{'guard_sha256':'g','deadline_epoch':1300})
    rec=R.prepare_probe('pod123',tmp_path)
    assert rec['bytes']==R.PROBE_BYTES and rec['sha256']==R.sha(tmp_path/'bandwidth_probe.bin')
    assert (tmp_path/'bandwidth_probe.bin').stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError,match='already exists'):R.prepare_probe('pod123',tmp_path)


def test_disk_gate_checks_free_headroom_and_fixed_200gb_even_on_large_host():
    good=R.disk_projection(46e9,90e9,110e9,2.02e9)
    assert good['ready'] and good['allocated_disk_bytes']==200_000_000_000
    assert not R.disk_projection(46e9,50e9,110e9,2.02e9)['ready']
    assert not R.disk_projection(80e9,500e9,110e9,2.02e9)['ready']
    assert not R.disk_projection(46e9,120e9,110e9,2.02e9,same_filesystem=False)['ready']
    assert R.disk_projection(46e9,120e9,110e9,2.02e9,same_filesystem=False)['publication_copies']==2
    with pytest.raises(ValueError):R.disk_projection(float('nan'),90e9,110e9,2.02e9)
