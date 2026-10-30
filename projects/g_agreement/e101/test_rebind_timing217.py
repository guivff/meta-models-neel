from pathlib import Path
import pytest
from projects.g_agreement.e101.contract import read,write,sha
from projects.g_agreement.e101.rebind_timing217 import transfer
from projects.g_agreement.e101.timing import admit


def seals(tmp_path,changed='timing.py'):
    root='projects/g_agreement/e101/'
    a=tmp_path/'old.json';b=tmp_path/'new.json'
    write(a,dict(experiment='E105',files={root+changed:'a',root+'runner105.py':'same'}))
    files=read(a)['files'];files[root+changed]='b';write(b,dict(experiment='E105',files=files))
    original=tmp_path/'original';original.mkdir()
    profile=original/'MEASURED_PROFILE.json'
    write(profile,dict(status='TIMING_ONLY_NOT_SCIENCE',margin=1.25,source_sha256=sha(a),input_sha256='i',gpu_type='H200',setup_warmup_seconds=10,staging_seconds=15,measured_work_seconds=100,total_seconds_with_margin=1.25*185))
    write(original/'ASSIGNMENT.json',dict(experiment='E105',source_sha256=sha(a),input_sha256='i',gpu_type='H200'))
    return a,b,profile


def test_transfer_preserves_measurements_and_admits_without_gpu_retime(tmp_path):
    a,b,p=seals(tmp_path);original=p.read_bytes();out=tmp_path/'derived'
    proof=transfer(p,a,b,out);q=out/'MEASURED_PROFILE.json'
    assert p.read_bytes()==original and proof['measurements_unchanged'] and proof['GPU_calls']==0
    result=read(q);source=read(p)
    assert all(result[k]==v for k,v in source.items() if k!='source_sha256')
    ass=dict(experiment='E105',gpu_type='H200',profile_sha256=sha(q),cap_seconds=150,timing_cap_policy='standing217',setup_profile_sha256=[])
    assert admit(q,ass,'i',sha(b))['cap_seconds']==150
    with pytest.raises(FileExistsError):transfer(p,a,b,out)


def test_acquisition_change_cannot_transfer(tmp_path):
    a,b,p=seals(tmp_path,'acquisition.py')
    with pytest.raises(ValueError,match='allowlist'):transfer(p,a,b,tmp_path/'out')
    assert not (tmp_path/'out').exists()
