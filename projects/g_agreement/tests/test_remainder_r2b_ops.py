import subprocess,time
import pytest
from projects.g_agreement.r_bench import remainder_r2b_ops as O


def test_bootstrap_syntax_and_immutable_id_decoys(tmp_path):
    now=time.time();b=dict(experiment='R2-B',gpu_count=1,confirmed_by='integrator',handoff_line='synthetic',pod='decoy-test-pod',network_volume_id='w9182om1pd',segment_id='test-segment',allocation_start=now,segment_start=now,segment_deadline=now+5000,pull_reserve=300)
    script=O.bootstrap(b,'/workspace/remainder/r2b/test-segment')
    path=tmp_path/'bootstrap.sh';path.write_text(script)
    subprocess.run(['bash','-n',str(path)],check=True)
    assert script.index('POD ID MISMATCH')<script.index('mkdir -p')
    assert 'rest.runpod.io/v1/pods/' in script and 'networkVolumeId' in script
    assert 'refuse to renew' in script
    assert 'stop' not in script.splitlines()[-1].lower()
    with pytest.raises(ValueError,match='decoy'):
        O.bootstrap(b,'/workspace/decoy')
