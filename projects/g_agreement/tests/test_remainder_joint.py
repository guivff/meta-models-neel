import copy
import json
import os
from pathlib import Path
import subprocess
import time
import pytest
from projects.g_agreement.r_bench import remainder_joint as J, remainder_r2_capture as C, remainder_r2_deploy as D


def record():
    return {'schema_version':2,'experiment':'r2_r6','mode':'warm_r2_r6_volume','network_volume_id':'vol123','pod':'pod123','started_epoch':100,'deadline_epoch':5500}


def test_joint_guard_exact_original_clock_opt_in_only():
    g=record();J.validate_joint_guard(g,'pod123',5500,200)
    C.validate_guard(g,'pod123',5500,200,joint_run=True)
    with pytest.raises(ValueError):C.validate_guard(g,'pod123',5500,200)
    for change in ({'started_epoch':99},{'mode':'cold'},{'experiment':'r6'},{'schema_version':3},{'deadline_epoch':float('nan')}):
        with pytest.raises(ValueError):J.validate_joint_guard({**g,**change},'pod123',5500,200)
    for deadline,now in ((5501,200),(5499,200),(5500,5200),(5500,99)):
        with pytest.raises(ValueError):J.validate_joint_guard(g,'pod123',deadline,now)


def test_guard_requires_rule9_live_pids_and_own_id(tmp_path,monkeypatch):
    monkeypatch.setattr(J,'check_path',lambda *a:None);J.write(tmp_path/'guard.json',record());(tmp_path/'ARMED').touch()
    monkeypatch.setattr(J,'require_volume',lambda *a:None)
    seen=[];monkeypatch.setattr(J.os,'kill',lambda pid,sig:seen.append((pid,sig)))
    for name in ('watchdog','hardstop'):
        (tmp_path/f'{name}.pid').write_text('123');(tmp_path/f'{name}.log').write_text('pod123 armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)')
    g=J.guard('pod123',tmp_path,env_bytes=b'RUNPOD_POD_ID=pod123\0',now=200)
    assert len(seen)==2 and g['guard_sha256']==J.sha(tmp_path/'guard.json')
    with pytest.raises(ValueError,match='MISMATCH'):J.guard('other',tmp_path,env_bytes=b'RUNPOD_POD_ID=pod123\0',now=200)
    (tmp_path/'watchdog.log').write_text('pod123 armed: old unchecked credential')
    with pytest.raises(ValueError,match='rule 9'):J.guard('pod123',tmp_path,env_bytes=b'RUNPOD_POD_ID=pod123\0',now=200)


def test_inventory_deduplicates_and_rejects_conflicting_hashes(tmp_path):
    a={'path':'cache/shared.npy','bytes':16,'sha256':'a'*64};b={'path':'cache/r6.npy','bytes':12,'sha256':'b'*64}
    for exp,rows in (('r2',[a]),('r6',[a,b])):J.write(tmp_path/f'results/g_agreement/r/remainder/{exp}/deployment_inputs.json',{'input_files':rows})
    inv=J.inputs(tmp_path);assert inv['input_file_count']==2 and inv['input_bytes']==28
    J.write(tmp_path/'results/g_agreement/r/remainder/r6/deployment_inputs.json',{'input_files':[{**a,'sha256':'f'*64}]})
    with pytest.raises(ValueError,match='Conflicting'):J.inputs(tmp_path)


def checkpoint_fixture(tmp_path,monkeypatch):
    run=tmp_path/'run';local=tmp_path/'mac';rel='cache/g_agreement/r/remainder/r2/probes/per_fact.json'
    for root in (run/'r2_checkpoint',local):
        p=root/rel;p.parent.mkdir(parents=True);p.write_bytes(b'captured tap bytes')
    g={**record(),'guard_sha256':'a'*64,'started_epoch':time.time()-100,'deadline_epoch':time.time()+1000}
    entry={'bytes':len(b'captured tap bytes'),'sha256':J.sha(local/rel)}
    m={'pod':'pod123','run_dir':str(run),'guard_sha256':g['guard_sha256'],'deadline_epoch':g['deadline_epoch'],'files':{rel:entry},'bytes':entry['bytes']}
    raw=root_path=run/'repo';state_rel=J.R2_PREFIX+'/capture/tap20.npy';state=raw/state_rel;state.parent.mkdir(parents=True);state.write_bytes(b'volume-only state')
    volume={'pod':'pod123','network_volume_id':g['network_volume_id'],'guard_sha256':g['guard_sha256'],'run_dir':str(run),'files':{state_rel:{'bytes':state.stat().st_size,'sha256':J.sha(state)}}}
    J.write(run/'volume_states.json',volume);m['volume_states_sha256']=J.sha(run/'volume_states.json')
    monkeypatch.setattr(J,'require_volume',lambda *a:None)
    original=J.verify_volume_states
    monkeypatch.setattr(J,'verify_volume_states',lambda pod,run,g:original(pod,run,g,root=raw))
    J.write(run/'r2_checkpoint.json',m)
    receipt=J.mac_receipt(local,run/'r2_checkpoint.json',platform='darwin');J.write(run/'r2_mac_receipt.json',receipt)
    return run,local,g,receipt,rel


def test_receipt_hashes_actual_mac_bytes_not_boolean(tmp_path,monkeypatch):
    run,local,g,receipt,rel=checkpoint_fixture(tmp_path,monkeypatch)
    assert receipt['files'][rel]['sha256']==J.sha(local/rel)
    with pytest.raises(FileNotFoundError):J.require_r2_checkpoint('pod123',run,g)
    J.write(run/'R2_MAC_VERIFIED',{'volume_states_sha256':J.sha(run/'volume_states.json'),'receipt_sha256':J.sha(run/'r2_mac_receipt.json'),'checkpoint_sha256':J.sha(run/'r2_checkpoint.json'),
        'remote_file_identities':J.checkpoint_identities(run/'r2_checkpoint',receipt['files'])})
    assert J.require_r2_checkpoint('pod123',run,g)['checkpoint_sha256']==J.sha(run/'r2_checkpoint.json')
    (local/rel).write_bytes(b'changed same bytes')
    with pytest.raises(ValueError,match='differ'):J.mac_receipt(local,run/'r2_checkpoint.json',platform='darwin')
    with pytest.raises(ValueError,match='Mac'):J.mac_receipt(local,run/'r2_checkpoint.json',platform='linux')
    J.write(run/'r2_mac_receipt.json',{'mac_verified':True})
    with pytest.raises(ValueError):J.require_r2_checkpoint('pod123',run,g)


def test_wait_rehashes_actual_remote_bytes_before_marker(tmp_path,monkeypatch):
    run,local,g,receipt,rel=checkpoint_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(J,'guard',lambda *a,**kw:g)
    J.wait_checkpoint('pod123',run,g,b'guard')
    assert (run/'R2_MAC_VERIFIED').is_file()
    (run/'R2_MAC_VERIFIED').unlink();p=run/'r2_checkpoint'/rel;p.write_bytes(b'x'*p.stat().st_size)
    with pytest.raises(ValueError,match='hash changed'):J.wait_checkpoint('pod123',run,g,b'guard')
    assert not (run/'R2_MAC_VERIFIED').exists()


def test_commands_have_one_deadline_and_no_download_or_sampling():
    run=Path('/workspace/remainder/r2_r6/test')
    cmds=J.r2_commands('pod123',run,5500,1e9)
    assert [x[0] for x in cmds]==['r2-preflight','r2-live-smoke','r2-capture','r2-audit','r2-probes']
    for name,cmd in cmds[1:3]:assert '--joint-run' in cmd and cmd[cmd.index('--deadline-epoch')+1]=='5500'
    script=J.emit('pod123',run,Path('/workspace/venv/bin/python'))
    assert 'pip install' not in script and 'source /workspace/.env' not in script and 'trap ' not in script
    assert 'unset RUNPOD_API_KEY' in script and 'HF_HUB_OFFLINE=1' in script
    assert subprocess.run(['bash','-n'],input=script,text=True).returncode==0
    boot=J.bootstrap('pod123','test',100,volume_id='vol123')
    assert 'DEADLINE=5500' in boot and 'REMAINING=$((DEADLINE-$(date +%s)-40))' in boot
    assert boot.index('POD ID MISMATCH')<boot.index('mkdir -p')
    assert subprocess.run(['bash','-n'],input=boot,text=True).returncode==0


@pytest.mark.parametrize('failure',[None,'r2-capture','r2-probes','checkpoint'])
def test_production_execute_r2_first_and_checkpoint_gates_all_r6(tmp_path,monkeypatch,failure):
    run=tmp_path/'run';root=run/'repo';root.mkdir(parents=True);J.write(run/'guard.json',record());J.write(run/'pull_bandwidth.json',{})
    monkeypatch.setattr(J,'ROOT',root);g={**record(),'deadline_epoch':time.time()+5000,'guard_sha256':'g'}
    monkeypatch.setattr(J,'guard',lambda *a,**kw:g);monkeypatch.setattr(J,'inputs',lambda:{'input_files':[]})
    monkeypatch.setattr(J,'verify_inputs',lambda:{});monkeypatch.setattr(J,'warm_environment',lambda:{'offline':True})
    monkeypatch.setattr(D,'validate_measurement',lambda *a:1e9);monkeypatch.setattr(J,'snapshot',lambda *a:None)
    order=[]
    def bounded(command,*a,**kw):
        module=command[command.index('-m')+1];phase=command[command.index('--phase')+1] if '--phase' in command else 'audit'
        name='r2-probes' if module.endswith('remainder_r2_probe') else ('r2-' if module.endswith('remainder_r2_capture') else 'r6-')+phase;order.append(name)
        if name in ('r2-capture','r2-audit'):assert kw['reserve']>J.RESERVE
        if name==failure:raise RuntimeError('forced R2 failure')
        if name=='r2-live-smoke':J.write(root/J.R2_PREFIX/'live_smoke.json',{'projected_tap_bytes':1,'projected_audit_seconds':.01})
        if name=='r2-capture':J.write(root/J.R2_PREFIX/'capture_complete.json',{'projected_tap_bytes':1,'audit_seconds':.01})
    monkeypatch.setattr(J,'bounded',bounded)
    def checkpoint(*a,**kw):order.append('r2-checkpoint-published')
    def wait(*a):
        order.append('mac-byte-verification')
        if failure=='checkpoint':raise ValueError('receipt checksum mismatch')
        return {'receipt_sha256':'verified'}
    monkeypatch.setattr(J,'make_checkpoint',checkpoint);monkeypatch.setattr(J,'wait_checkpoint',wait)
    monkeypatch.setattr(J,'require_r2_checkpoint',lambda *a: {'receipt_sha256':'verified'})
    rc=J.execute('pod123',run)
    assert order[:3]==['r2-preflight','r2-live-smoke','r2-capture']
    if failure:
        assert rc==1 and not any(x.startswith('r6-') for x in order)
    else:
        assert rc==0 and order[3:7]==['r2-audit','r2-probes','r2-checkpoint-published','mac-byte-verification']
        assert all(x.startswith('r6-') for x in order[7:])


def test_cpu_smoke_produces_every_registered_arm(tmp_path):
    result=J.smoke(tmp_path/'smoke.json')
    assert (result['r2_score_rows'],result['r2_arm_cells'],result['r6_report_rows'],result['r6_arm_cells'])==(48,72,80,80)
    assert result['kind']=='synthetic_cpu_only' and not result['live_launch_authorized_by_smoke']


def test_joint_budget_transfers_compact_results_not_full_volume_states():
    b=J.checkpoint_budget({'projected_tap_bytes':11_559_813_120,'projected_audit_seconds':10},100_000_000)
    assert b['states_stay_on_volume'] and b['transfer_seconds']==30 and b['capture_reserve_seconds']==430
    with pytest.raises(ValueError,match='15 GB'):J.checkpoint_budget({'projected_tap_bytes':14_000_000_000,'projected_audit_seconds':10},1e8)


def test_already_present_late_mac_receipt_rejected(tmp_path,monkeypatch):
    run,local,g,receipt,rel=checkpoint_fixture(tmp_path,monkeypatch)
    m=J.read(run/'r2_checkpoint.json');m['mac_receipt_deadline_epoch']=time.time()-1;J.write(run/'r2_checkpoint.json',m)
    monkeypatch.setattr(J,'guard',lambda *a,**kw:g)
    with pytest.raises(ValueError,match='after verification cutoff'):J.wait_checkpoint('pod123',run,g,b'guard')
    assert not (run/'R2_MAC_VERIFIED').exists()


def test_final_receipts_reuse_only_unchanged_verified_hardlinks(tmp_path,monkeypatch):
    run,local,g,receipt,rel=checkpoint_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(J,'guard',lambda *a,**kw:g);J.wait_checkpoint('pod123',run,g,b'guard')
    final=tmp_path/'mac-final';remote=run/'deliverables'
    for dest,source in ((final,local),(remote,run/'r2_checkpoint')):
        p=dest/rel;p.parent.mkdir(parents=True);os.link(source/rel,p)
        (dest/'r6.jsonl').write_text('new R6 report')
    r=J.final_mac_receipt(final,local,run/'r2_mac_receipt.json',platform='darwin')
    J.write(run/'final_mac_receipt.json',r)
    assert J.verify_final('pod123',run,run/'final_mac_receipt.json')['complete']
    (remote/'r6.jsonl').write_text('changed R6 report')
    with pytest.raises(ValueError,match='differs'):J.verify_final('pod123',run,run/'final_mac_receipt.json')
    (local/rel).write_bytes(b'x'*len(b'captured tap bytes'))
    with pytest.raises(ValueError,match='verified tap changed'):J.final_mac_receipt(final,local,run/'r2_mac_receipt.json',platform='darwin')


def test_volume_state_corruption_blocks_r6_without_transferring_states(tmp_path,monkeypatch):
    run,local,g,receipt,rel=checkpoint_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(J,'guard',lambda *a,**kw:g)
    raw=run/'repo'/J.R2_PREFIX/'capture/tap20.npy';raw.write_bytes(b'wrong volume bytes')
    with pytest.raises(ValueError,match='Volume state checksum'):J.wait_checkpoint('pod123',run,g,b'guard')
    assert not (run/'R2_MAC_VERIFIED').exists()
    assert all('/capture/' not in p for p in receipt['files'])


def test_volume_booking_required_and_raw_states_omitted_from_snapshot(tmp_path):
    with pytest.raises(ValueError,match='network volume'):J.bootstrap('pod123','test',100)
    g=record();J.write(tmp_path/'volume.json',{'pod':'pod123','network_volume_id':None,'http_status':200,'mount_path':'/workspace'})
    with pytest.raises(ValueError,match='off-volume'):J.require_volume('pod123',tmp_path,g)
    run=tmp_path/'run';run.mkdir();root=run/'repo'
    for rel in (J.R2_PREFIX+'/capture/chunk/tap20.npy',J.R2_PREFIX+'/capture_smoke/chunk/tap20.npy',J.R2_PREFIX+'/probes/per_fact.json'):
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
    dest=J.snapshot(run,root)
    assert not list(dest.rglob('tap*.npy'))
    assert (dest/J.R2_PREFIX/'probes/per_fact.json').is_file()


def test_checkpoint_contains_results_and_volume_hashes_but_no_states(tmp_path,monkeypatch):
    run=tmp_path/'run';root=run/'repo';g={**record(),'guard_sha256':'g','deadline_epoch':time.time()+2000}
    monkeypatch.setattr(J,'guard',lambda *a,**kw:g);monkeypatch.setattr(J,'require_volume',lambda *a:None)
    audited=[];monkeypatch.setattr(C,'audit',lambda *a:audited.append(True))
    code=root/'projects/g_agreement/r_bench/remainder_r2_probe.py';code.parent.mkdir(parents=True);code.write_text('# fixture')
    capture=root/J.R2_PREFIX/'capture';capture.mkdir(parents=True);(capture/'tap20.npy').write_bytes(b'full state bytes stay on volume')
    J.write(root/J.R2_PREFIX/'capture_manifest.json',{'fixture':True})
    J.write(root/J.R2_PREFIX/'capture_complete.json',{'kind':'live','pod':'pod123','guard_sha256':'g','coverage':{'status':'PASS','arm_cells':72},'manifest_sha256':'manifest','git_sha':'git','code_sha':'code'})
    J.write(root/J.R2_PREFIX/'probes/complete.json',{'status':'PASS','pod':'pod123','guard_sha256':'g','probe_code_sha':J.sha(code),'manifest_sha256':'manifest','bootstrap_draws':2000,'git_sha':'git','code_sha':'code'})
    J.write(root/J.R2_PREFIX/'probes/per_fact.json',[{'auroc':.8}])
    manifest=J.make_checkpoint('pod123',run,g,root=root)
    assert audited and not any('/capture/' in p for p in manifest['files'])
    assert 'operations/volume_states.json' in manifest['files']
    assert (capture/'tap20.npy').read_bytes()==b'full state bytes stay on volume'
    assert J.verify_volume_states('pod123',run,g,root=root)==manifest['volume_states_sha256']
    J.snapshot(run,root)
    assert not list((run/'deliverables').rglob('tap*.npy'))
    assert os.path.samefile(run/'deliverables/operations/volume_states.json',run/'r2_checkpoint/operations/volume_states.json')
    (capture/'tap20.npy').write_bytes(b'corrupted')
    with pytest.raises(ValueError,match='checksum'):J.verify_volume_states('pod123',run,g,root=root)


def test_verified_checkpoint_cache_invalidates_on_receipt_change(tmp_path,monkeypatch):
    run,local,g,receipt,rel=checkpoint_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(J,'guard',lambda *a,**kw:g);J.wait_checkpoint('pod123',run,g,b'guard')
    first=J.require_r2_checkpoint('pod123',run,g)
    assert J.require_r2_checkpoint('pod123',run,g)==first
    J.write(run/'volume_states.json',{'changed':True})
    with pytest.raises(ValueError,match='proof changed'):J.require_r2_checkpoint('pod123',run,g)
