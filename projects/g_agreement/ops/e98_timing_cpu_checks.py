from pathlib import Path
import tempfile,json,importlib.util,math,sys
sys.path.insert(0,'projects/g_agreement/ops');import i5_e98_reader_controller as C;import i5_e98_timing_worker as W
p=dict(phase='reader',cap_seconds=32400,prior_gpu_seconds=580.1988520622253,GO_git_verified=True,same_pod_retained_timing=True,authorization_commit='c093f98992403210d86a5f6865015018c170d6af',gpu_types=['NVIDIA H200'],projected_upper_usd=1800)
C.validate_plan(p)
for change in [dict(GO_git_verified=False),dict(same_pod_retained_timing=False),dict(cap_seconds=36000),dict(prior_gpu_seconds=0),dict(gpu_types=['NVIDIA B200'])]:
 try:C.validate_plan(dict(p,**change));raise AssertionError('Invalid unmeasured/cumulative/GO/hardware plan')
 except ValueError:pass
ass=dict(pod_id='owned',deadline_epoch=10000,custody_start_epoch=100,timing_deadline_epoch=1000)
a=dict(experiment='E98',pod_id='owned',admitted_epoch=500,deadline_epoch=100+math.ceil(120+1.25*2000),cap_seconds=math.ceil(120+1.25*2000),max_measured_setup_seconds=120,measured_work_seconds=2000)
W.validate_admission(a,ass,500)
for change in [dict(deadline_epoch=20000),dict(admitted_epoch=1001),dict(pod_id='other'),dict(cap_seconds=2600)]:
 try:W.validate_admission(dict(a,**change),ass,500);raise AssertionError('Invalid admission accepted')
 except ValueError:pass
# No second sample can begin until the first actual record is present and a valid measured admission releases the pause.
from types import SimpleNamespace
with tempfile.TemporaryDirectory()as td:
 root=Path(td);out=root/'out';(out/'records').mkdir(parents=True);first=out/'records/retained.json';first.write_text('{"fixture":true}')
 calls=[];timer=SimpleNamespace(cancel=lambda:calls.append('cancel'))
 class Clock:
  def __init__(self):self.out=out;self.samples=[2.0];self.deadline=10000
  def fits(self,remaining):calls.append('original');return True
 def write(path,value):Path(path).write_text(json.dumps(value))
 worker=SimpleNamespace(Clock=Clock,write=write)
 original_time=W.time.time;original_sleep=W.time.sleep
 W.time.time=lambda:500
 def release(seconds):
  assert first.exists()and len(list((out/'records').iterdir()))==1 and calls==['original'];(root/'MEASURED_PRODUCTION.json').write_text(json.dumps(a))
 W.time.sleep=release
 try:W.install(worker,ass,timer);clock=worker.Clock();assert clock.fits(2183);assert clock.samples==[2.0]and clock.deadline==a['deadline_epoch']and first.read_text()=='{"fixture":true}';assert calls==['original','cancel','original']
 finally:W.time.time=original_time;W.time.sleep=original_sleep
print('11 timing/cumulative/GO/retained-sample CPU gates PASS')

with tempfile.TemporaryDirectory()as td:
 r=Path(td);state=dict(pod_id='owned',createdAt='fixture',created_epoch=0,deadline_epoch=3000);(r/'STATE.json').write_text(json.dumps(state))
 saved=(C.C.read,C.C.write,C.C.pod,C.C.identity,C.C.stop,C.time.time,C.time.sleep)
 def probe(admission):
  now=[100.0];stopped=[]
  if admission is None:(r/'MEASURED_PRODUCTION.json').unlink(missing_ok=True)
  else:(r/'MEASURED_PRODUCTION.json').write_text(json.dumps(admission))
  C.C.read=lambda path:json.loads(Path(path).read_text());C.C.write=lambda path,value:Path(path).write_text(json.dumps(value));C.C.pod=lambda pid:None;C.C.identity=lambda *a:None;C.C.stop=lambda state:stopped.append(now[0]);C.time.time=lambda:now[0];C.time.sleep=lambda seconds:now.__setitem__(0,now[0]+seconds)
  C.guard(r,'hardstop');return stopped[0]
 try:
  a=dict(pod_id='owned',createdAt='fixture',admitted_epoch=100,deadline_epoch=600,cap_seconds=600)
  assert 570<=probe(a)<=572
  assert 870<=probe(None)<=872
  assert probe(dict(a,deadline_epoch=4000,cap_seconds=4000))==100
  assert probe(dict(a,admitted_epoch=901))==100
 finally:C.C.read,C.C.write,C.C.pod,C.C.identity,C.C.stop,C.time.time,C.time.sleep=saved
print('4 virtual-clock provider guard shortening/failclosed tests PASS')
