import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch
import pytest
from projects.g_agreement.r_bench import remainder_r6_deploy as R


def test_emit_is_detached_chain_ready_and_checks_own_id_before_env():
    s=R.emit('r6','pod',Path('/workspace/remainder/r6/run'),cold=True)
    assert s.index('POD ID MISMATCH')<s.index('source /workspace/.env')
    assert '--cold-setup' in s and 'job.pid' in s and 'exec python3' in s
    assert 'trap ' not in s and 'stop' not in s and '/Users/' not in s
    subprocess.run(['bash','-n'],input=s,text=True,check=True)
    with pytest.raises(ValueError):R.emit('r6','p',Path('/workspace/remainder/r5/run'))


def test_science_chain_has_all_coverage_phases_and_fresh_budget():
    assert R.science_phases('r6')==['recovery-preflight','recovery-smoke','recovery-full','generation-preflight','generation-smoke','generation-full','audit']
    assert R.science_phases('r3')==['generation-preflight','generation-smoke','generation-full','audit']
    a=R.phase_command('generation-full','r3','p',Path('/run'),850,python='/run/venv/bin/python')
    assert a[0]=='/run/venv/bin/python' and a[-1]=='850' and '--available-cohort' in a and '--allow-recaptured-states' in a and 'r3-sampling' in a
    with pytest.raises(ValueError,match='budget'):R.phase_command('generation-full','r3','p',Path('/run'),300)


def test_r3_missing_recovery_blocks_before_setup(tmp_path):
    with pytest.raises(ValueError,match='before cold setup'):R.prerequisite('r3',root=tmp_path)
    R.prerequisite('r6',root=tmp_path)
    p=tmp_path/'m.jsonl';p.write_text(json.dumps({'case':'C4','pair_id':'C4-00','arm':'focal','states':{'42':{'path':'missing.npy','index_path':'idx.json'}}})+'\n')
    with pytest.raises(ValueError,match='absent'):R.prerequisite('r3','m.jsonl',tmp_path)


def test_payload_verification_and_relative_paths(tmp_path):
    path=tmp_path/'data';path.write_bytes(b'original')
    inv={'experiment':'r6','input_files':[{'path':'data','bytes':8,'sha256':R.sha(path)}]}
    R.write(tmp_path/'results/g_agreement/r/remainder/r6/deployment_inputs.json',inv)
    assert R.verify_payload('r6',tmp_path)==inv
    path.write_bytes(b'changed!')
    with pytest.raises(ValueError,match='changed'):R.verify_payload('r6',tmp_path)
    for p in ('/Users/absolute','../escape'):
        with pytest.raises(ValueError,match='relative'):R.relative(p)


def test_guard_keeps_original_cap_and300s_reserve(tmp_path):
    R.write(tmp_path/'guard.json',{'pod':'p','experiment':'r6','started_epoch':100,'deadline_epoch':1300})
    (tmp_path/'ARMED').touch()
    for name in ('watchdog','hardstop'):
        (tmp_path/f'{name}.log').write_text('armed: p');(tmp_path/f'{name}.pid').write_text(str(os.getpid()))
    assert R.validate_guard('r6','p',tmp_path,now=200,env=b'RUNPOD_POD_ID=p\0')['deadline_epoch']==1300
    with pytest.raises(ValueError,match='reserve'):R.validate_guard('r6','p',tmp_path,now=1000,env=b'RUNPOD_POD_ID=p\0')
    with pytest.raises(ValueError,match='ID MISMATCH'):R.validate_guard('r6','q',tmp_path,now=200,env=b'RUNPOD_POD_ID=p\0')


def test_timeout_finds_separate_cold_child_process_groups(tmp_path):
    def stat(pid,ppid,group):
        p=tmp_path/str(pid);p.mkdir();(p/'stat').write_text(f'{pid} (process with spaces) S {ppid} {group} 0 0 0')
    stat(10,1,10);stat(11,10,11);stat(12,11,11);stat(13,12,13);stat(20,1,20)
    assert R.descendant_groups(10,tmp_path)=={10,11,13}


def test_scientific_children_do_not_inherit_api_credentials():
    source={'RUNPOD_API_KEY':'fixture-provider','HF_TOKEN':'fixture-hf','HF_HOME':'/workspace/cache','HF_HUB_CACHE':'/workspace/customhub'}
    setup=R.phase_environment('cold-setup',source);science=R.phase_environment('generation-full',source)
    assert 'RUNPOD_API_KEY' not in setup and setup['HF_TOKEN']=='fixture-hf'
    assert 'RUNPOD_API_KEY' not in science and 'HF_TOKEN' not in science
    assert science['HF_HUB_OFFLINE']==science['TRANSFORMERS_OFFLINE']=='1'
    assert science['HF_HUB_CACHE']=='/workspace/customhub' and source['HF_TOKEN']=='fixture-hf'


def test_joint_commands_preserve_standalone_cap_and_parked_profile():
    run=Path('/workspace/remainder/r2_r6/run')
    for phase in ('recovery-smoke','recovery-full','generation-smoke','generation-full'):
        cmd=R.phase_command(phase,'r6','p',run,4200,joint_run=True)
        assert '--joint-run' in cmd
        assert cmd[cmd.index('--guard-dir')+1]==str(run)
        assert cmd[cmd.index('--budget-seconds')+1]=='4200'
        assert 'r3-sampling' not in cmd
        with pytest.raises(ValueError,match='budget'):
            R.phase_command(phase,'r6','p',run,4200)
    for remaining in (300,5401,float('nan'),float('inf'),True):
        with pytest.raises(ValueError,match='budget'):
            R.phase_command('generation-full','r6','p',run,remaining,joint_run=True)
    with pytest.raises(ValueError,match='parked'):
        R.phase_command('generation-full','r3','p',run,4200,joint_run=True)
    assert R.CAP==1200
