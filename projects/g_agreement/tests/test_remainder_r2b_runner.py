import json
import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r2b as D,remainder_r2b_runner as R


def booking():return dict(experiment='R2-B',gpu_count=1,confirmed_by='integrator',handoff_line='test booking',pod='fake',network_volume_id='w9182om1pd',segment_id='s1',allocation_start=0,segment_start=0,segment_deadline=5400,pull_reserve=300)


def test_booking_decoys():
    assert R.validate_booking(booking(),1)
    for field,value,match in [('experiment','decoy','booking'),('segment_deadline',R.TOTAL+1,'deadline'),('pull_reserve',0,'reserve'),('network_volume_id','../decoy','network_volume_id')]:
        b=booking();b[field]=value
        with pytest.raises(ValueError,match=match):R.validate_booking(b,1)


def test_volume_and_registration_decoys():
    with pytest.raises(ValueError,match='decoy'):R.validate_volume(booking(),dict(pod='decoy',network_volume_id='w9182om1pd',http_status=200,mounted=True))
    with pytest.raises(ValueError,match='manifest'):R.validate_registration(dict(section=36,pushed_before_compute=True,prereg_commit='a'*40,manifest_sha256='wrong'),{'cells':[]})
    with pytest.raises(ValueError,match='decoy'):R.validate_guard_process(2,'bash decoy fake','', 'fake','watchdog')


def test_writer_derived_paths_and_named_decoys(tmp_path):
    c={'item':'x','arm':'natural','tap_blocks':[2,4,6]};m={'cells':[c]};p=D.stamp('fake','abc','a'*64,'test')
    w=R.RunWriter(tmp_path,m,p)
    with pytest.raises(ValueError,match='decoy'):w.path('decoy.json')
    with pytest.raises(ValueError,match='Missing cells'):w.finish()
    w.append(c,{'score':.5},{k:np.ones(4,dtype=np.float16) for k in c['tap_blocks']})
    with pytest.raises(ValueError,match='Duplicate cell'):w.append(c,{}, {})
    (w.root/'decoy.txt').write_text('unowned')
    with pytest.raises(ValueError,match='decoy.txt'):w.finish()
    (w.root/'decoy.txt').unlink();assert w.finish()
    row=json.loads((w.root/'rows.jsonl').read_text());assert row['run_id']==p['run_id']
    assert str(w.root).startswith(str(tmp_path/'test'))


def test_process_isolation_and_payload_decoy(tmp_path):
    c={'item':'x','tap_blocks':[]};m={'cells':[c]}
    p=D.stamp('fake','abc','a'*64,'test');w=R.RunWriter(tmp_path,m,p)
    with pytest.raises(ValueError,match='provenance'):w.append(c,{'run_id':'decoy'}, {})
    with pytest.raises(FileExistsError):R.RunWriter(tmp_path,m,p)
    other=R.RunWriter(tmp_path,m,D.stamp('fake','abc','a'*64,'smoke'));assert other.root!=w.root


def test_release_requires_bytes_not_boolean(tmp_path):
    (tmp_path/'state').write_bytes(b'original')
    m={'files':{'state':R.sha(tmp_path/'state')},'compact_files':{'results':'abc'}}
    receipt={'verified_on':'Mac','pod':'fake','network_volume_id':'w9182om1pd','volume_manifest_sha256':D.digest(m),'compact_files':{'results':'abc'}}
    writes=[];calls=[]
    result=R.verified_release(booking(),receipt,m,tmp_path,lambda:calls.append(1),writes.append)
    assert result['guards_retained'] and not result['custody_transferred'] and len(calls)==2
    (tmp_path/'state').write_bytes(b'decoy')
    with pytest.raises(ValueError,match='state'):R.verified_release(booking(),receipt,m,tmp_path,lambda:None,writes.append)


def test_catch_all_write_isolation_names_decoy(tmp_path):
    from pathlib import Path
    with pytest.raises(ValueError,match='DECOY_OUTSIDE'):
        (tmp_path.parent/'DECOY_OUTSIDE').write_text('must not write')


def test_custody_decoy_names_foreign_owner():
    with pytest.raises(ValueError,match='decoy'):
        R.validate_custody(booking(),dict(pod='decoy',segment_id='s1'))
    with pytest.raises(ValueError,match='decoy'):
        R.validate_custody(booking(),dict(pod='fake',segment_id='s1',confirmed_by='integrator',handoff_line='decoy unacknowledged',previous_guards_retired=False))


def test_measured_pull_reserve_rejects_foreign_and_stale_decoys():
    import time
    b=booking();b['allocation_start']=time.time()-10
    proof=dict(pod='fake',bytes=8*1024*1024,bytes_per_second=1024**2,sha256='a'*64,measured_epoch=time.time())
    assert R.measured_reserve(b,proof)>b['pull_reserve']
    with pytest.raises(ValueError,match='decoy'):
        R.measured_reserve(b,dict(proof,pod='decoy'))
    with pytest.raises(ValueError,match='-99'):
        R.measured_reserve(b,dict(proof,measured_epoch=-99))


def test_release_extra_output_decoy(tmp_path):
    out=tmp_path/'outputs';out.mkdir();(out/'data').write_text('x')
    m=dict(files={'outputs/data':R.sha(out/'data')},compact_files={'outputs/data':R.sha(out/'data')})
    receipt=dict(pod='fake',network_volume_id='w9182om1pd',verified_on='Mac',volume_manifest_sha256=D.digest(m),compact_files=m['compact_files'])
    (out/'decoy').write_text('new')
    with pytest.raises(ValueError,match='decoy'):R.verified_release(booking(),receipt,m,tmp_path,lambda:None,lambda r:None)


def test_pull_reserve_allows_only_release_not_science():
    b=booking()
    with pytest.raises(ValueError,match='reserve'):R.validate_booking(b,5300)
    assert R.validate_booking(b,5300,science=False)
    with pytest.raises(ValueError,match='deadline'):R.validate_booking(b,5401,science=False)


def test_live_guard_native_id_and_immutable_booking_decoys(monkeypatch):
    import time
    from pathlib import Path
    from types import SimpleNamespace
    now=time.time();b=dict(booking(),allocation_start=now-1,segment_start=now-1,segment_deadline=now+5000)
    run='/workspace/remainder/r2b/test';plan={'cells':[]}
    text={run+'/booking.json':json.dumps(b),run+'/manifest.json':json.dumps(plan),
          run+'/registration.json':json.dumps(dict(section=36,pushed_before_compute=True,prereg_commit='a'*40,manifest_sha256=D.digest(plan))),
          run+'/bandwidth.json':json.dumps(dict(pod='fake',bytes=8*1024*1024,bytes_per_second=1024**3,sha256='a'*64,measured_epoch=now)),
          run+'/volume.json':json.dumps(dict(pod='fake',network_volume_id='w9182om1pd',http_status=200,mounted=True)),
          run+'/custody.json':json.dumps(dict(pod='fake',segment_id='s1',confirmed_by='integrator',handoff_line='ack',previous_guards_retired=True)),
          '/proc/1/environ':'RUNPOD_POD_ID=fake\0'}
    for pid,kind in [(12,'hardstop'),(13,'watchdog')]:
        text[run+'/'+kind+'.pid']=str(pid);text[run+'/'+kind+'.log']='fake armed: credential (check http 200)'
        text[f'/proc/{pid}/cmdline']=f'bash\0ws2_{kind}.sh\0fake\0'
    original_text=Path.read_text;original_bytes=Path.read_bytes;original_stat=Path.stat
    monkeypatch.setattr(Path,'read_text',lambda p,*a,**kw:text[str(p)] if str(p) in text else original_text(p,*a,**kw))
    monkeypatch.setattr(Path,'read_bytes',lambda p:text[str(p)].encode() if str(p) in text else original_bytes(p))
    monkeypatch.setattr(Path,'stat',lambda p,*a,**kw:SimpleNamespace(st_dev=1) if str(p) in (run,'/workspace') else original_stat(p,*a,**kw))
    monkeypatch.setattr(R.os.path,'ismount',lambda p:True);monkeypatch.setattr(R.os,'kill',lambda *args:None)
    guard=R.LiveGuard(run);guard()
    text['/proc/1/environ']='RUNPOD_POD_ID=decoy-native\0'
    with pytest.raises(ValueError,match='decoy-native'):guard()
    text['/proc/1/environ']='RUNPOD_POD_ID=fake\0';text[run+'/booking.json']=json.dumps(dict(b,handoff_line='decoy-change'))
    with pytest.raises(ValueError,match='Booking changed'):guard()


def test_three_hour_single_gpu_budget_and_volume_decoys():
    b=dict(booking(),segment_deadline=R.TOTAL)
    assert R.validate_booking(b,1)
    for changes,match in [({'segment_deadline':R.TOTAL+1},'deadline'),
                          ({'gpu_count':2},'gpu_count: 2'),
                          ({'network_volume_id':'decoy-off-volume'},'decoy-off-volume')]:
        with pytest.raises(ValueError,match=match):R.validate_booking(dict(b,**changes),1)
    # Moving segment start must never renew the allocation budget.
    with pytest.raises(ValueError,match='deadline'):
        R.validate_booking(dict(b,segment_start=100,segment_deadline=R.TOTAL+100),101)


def test_verified_completion_is_stop_ready(tmp_path):
    (tmp_path/'data').write_text('complete')
    m=dict(files={'data':R.sha(tmp_path/'data')},compact_files={'data':R.sha(tmp_path/'data')})
    receipt=dict(pod='fake',network_volume_id=R.NETWORK_VOLUME,verified_on='Mac',volume_manifest_sha256=D.digest(m),compact_files=m['compact_files'])
    saved=[]
    result=R.verified_release(booking(),receipt,m,tmp_path,lambda:None,saved.append)
    assert result['status']=='VERIFIED_READY_TO_STOP' and result['guards_retained']
    assert saved==[result]
