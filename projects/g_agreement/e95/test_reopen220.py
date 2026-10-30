import hashlib
import json
import pytest
from projects.g_agreement.e95.reopen220 import MISSED,evaluate


def seal(tmp_path, name, value, **meta):
    tmp_path.mkdir(parents=True,exist_ok=True)
    p=tmp_path/name;p.write_text(json.dumps(value))
    s=tmp_path/('ANALYSIS_SEAL.json' if name=='RESULTS.json' else 'DEPTH_SEAL.json')
    s.write_text(json.dumps(dict(files={name:hashlib.sha256(p.read_bytes()).hexdigest()},**meta)))
    return s


def inputs(tmp_path,status='MET',count=0):
    a=seal(tmp_path/'a','RESULTS.json',dict(R_L1=dict(status=status)),experiment='E87',status='COMPLETE_ONCE')
    rows={r:{'class':'consumed' if i<count else 'never'} for i,r in enumerate(MISSED)}
    rows['topic_twin']={'class':'late'};rows['loop_direction']={'class':'consumed'}
    d=seal(tmp_path/'d','DEPTH_PROFILE.json',dict(experiment='E87',rows=rows))
    return a,d


def test_pending_and_partial_or(tmp_path):
    assert evaluate()['status']=='WAITING_E87_ANALYSIS_SEAL'
    a,d=inputs(tmp_path,status='NOT MET')
    assert evaluate(a)['status']=='REOPEN_E95_DEVIATION_2'


@pytest.mark.parametrize('count,expected',[(1,'KEEP_NOT_RUN'),(2,'REOPEN_E95_DEVIATION_2')])
def test_exact_missed_threshold_controls_ignored(tmp_path,count,expected):
    assert evaluate(*inputs(tmp_path,count=count))['status']==expected


def test_no_negative_decision_until_depth_sealed(tmp_path):
    a,d=inputs(tmp_path)
    assert evaluate(a)['status']=='WAITING_E87_DEPTH_SEAL'


def test_control_failure_does_not_become_not_met(tmp_path):
    assert evaluate(*inputs(tmp_path,status='NOT EVALUABLE (a positive control failed)'))['status']=='KEEP_NOT_RUN'


def test_tamper_fails_before_gate(tmp_path):
    a,d=inputs(tmp_path,count=2)
    (d.parent/'DEPTH_PROFILE.json').write_text('{}')
    with pytest.raises(AssertionError):evaluate(a,d)
