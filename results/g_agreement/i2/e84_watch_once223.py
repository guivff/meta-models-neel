"""Exact-owned E84 capture/gate/terminal watcher; one claim, immutable clocks."""
from pathlib import Path
import json,subprocess,sys,time,os,hashlib,tarfile,math,datetime
R=Path(__file__).resolve().parents[3];H=R/'cache/g_agreement/i2/e84_frozen6c223_v1';sys.path.insert(0,str(H));import stage_and_start as st
read=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def ssh(s,program,timeout=45):return st.ssh(s,program,timeout)
def transfer_capture(s):
 with(H/'CAPTURE_PULL_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),run_id=s['run_id']),f)
 host,port=s['address'].split(':');cmd=['ssh','-i',str(st.KEY),'-p',port,'-o','BatchMode=yes','-o','ConnectTimeout=15','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','root@'+host,'bash -s'];archive=H/'CAPTURE_PULL.private.tar'
 program=f"cd {s['remote_dir']}\n/weights/venv-kernels/bin/python - <<'REMOTE'\nimport tarfile,sys,json\nfrom pathlib import Path\np=Path('outputs/capture');assert json.loads((p/'CAPTURE_SEAL.json').read_text())['status']=='COMPLETE'\nwith tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as t:\n for f in sorted(p.iterdir()):\n  assert f.is_file()and not f.is_symlink();t.add(f,arcname=f.name,recursive=False)\nREMOTE\n"
 with archive.open('xb')as f:q=subprocess.run(cmd,input=program.encode(),stdout=f,stderr=subprocess.PIPE,timeout=90)
 assert q.returncode==0
 dest=H/'capture_cpu_once';dest.mkdir(exist_ok=False)
 with tarfile.open(archive)as t:
  for m in t.getmembers():assert m.isfile()and not m.issym()and not m.islnk()and Path(m.name).name==m.name
  t.extractall(dest)
 seal=read(dest/'CAPTURE_SEAL.json')
 for n,d in seal['files'].items():assert sha(dest/n)==d
 assert seal['items']==300 and seal['blocks']==[44,42]
 write(H/'CAPTURE_PULL_VERIFIED.json',dict(capture_sha256=sha(dest/'CAPTURE_SEAL.json'),archive_sha256=sha(archive),verified=True))
 return dest

def main():
 os.umask(0o077)
 with(H/'WATCH_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),source_sha256=sha(__file__),pid=os.getpid()),f)
 release_sent=False
 while True:
  s=read(H/'ALLOCATION.private.json');assert s['run_id']=='mats-i2-e84-frozen6c-20261029-a1' and s['hard_deadline_epoch']==s['created_epoch']+3600
  if s['status']=='STAGING':
   assert time.time()<s['created_epoch']+930,'ORIGINAL_SETUP900_STAGE_RECONCILE';time.sleep(10);continue
  assert s['status']=='WORKER_STARTED_ORIGINAL_DEADLINE','STAGE_FAILED_RECONCILE_EXACT_GPU'
  program=f"cd {s['remote_dir']}\n/weights/venv-kernels/bin/python - <<'REMOTE'\nfrom pathlib import Path\nimport json\nprint(json.dumps(dict(exit=Path('EXIT.json').exists(),capture=Path('outputs/capture/CAPTURE_SEAL.json').exists(),seal=Path('outputs/OUTPUT_SEAL.json').exists())))\nREMOTE\n"
  flags=json.loads(ssh(s,program).strip());write(H/'WATCH_PROGRESS.json',dict(at=time.time(),flags=flags,release_sent=release_sent,original_deadline=s['hard_deadline_epoch']))
  if flags['exit']:break
  if flags['capture']and not release_sent:
   capture=transfer_capture(s);gate=R/'results/g_agreement/i2/e84_cpu_gate223.py';public=H/'PUBLIC_INPUTS.json';labels=R.parent/'wt-wtext/results/g_agreement/understand/e84/cache/revived_bank_2026-10-29_v1/LABELS.PRIVATE.json'
   assert sha(gate)=='0d8df87a17ac02ec40d534902ccf75ca6537a9b0db45324644b8069004cf7f2a','EXACT_PRE_OUTPUT_CPU_GATE_SOURCE'
   q=subprocess.run(['/Users/guivff/Documents/Neel_Exploration/activation-readers/.venv/bin/python','-B',str(gate),'--capture',str(capture),'--public',str(public),'--labels',str(labels),'--out',str(H/'cpu_gate_once')],cwd=R,capture_output=True,timeout=180)
   (H/'CPU_GATE.private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,'CPU_GATE_FAILURE_NO_REPLAY'
   release=H/'cpu_gate_once/PUBLIC_RELEASE.json';d=read(release);assert d['capture_seal_sha256']==sha(capture/'CAPTURE_SEAL.json')and d['labels_cpu_only']is True
   with(H/'RELEASE_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),public_release_sha256=sha(release)),f)
   host,port=s['address'].split(':');q=subprocess.run(['scp','-i',str(st.KEY),'-P',port,'-o','BatchMode=yes','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null',str(release),'root@'+host+':'+s['remote_dir']+'/CPU_GATE_RELEASE.json'],capture_output=True,timeout=30);assert q.returncode==0;release_sent=True
  assert time.time()<s['hard_deadline_epoch']+60,'ORIGINAL_DEADLINE_RECONCILE_REQUIRED';time.sleep(15)
 q=subprocess.run([sys.executable,'-B',str(H/'pull_terminal_once.py')],cwd=R,capture_output=True,timeout=180);(H/'TERMINAL_PULL_DRIVER.private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
 # Inspect current own queue before closing. E110 minimum gate and E85 consumed
 # NO_FIT cannot provide a new admitted job; later queues have no prepared GO.
 status=read(R/'results/g_agreement/i2/STATUS.json');assert status['E110_amend1']['state']=='NOT_RUN_MINIMUM_NATIVE_BELIEF_WRONG_GATE'
 assert status['E85_production4300']['scientific_status']=='NO_FIT'
 write(H/'QUEUE_REVIEW.private.json',dict(run_id=s['run_id'],original_deadline_epoch=s['hard_deadline_epoch'],checked_epoch=time.time(),no_eligible_queued_job=True,status_sha256=sha(R/'results/g_agreement/i2/STATUS.json'),reason='E84 exact worker terminal, retrieval verified; current E110 minimum gate NOTRUN and E85 approved attempt NOFIT/consumed, no eligible source-bound admitted I2 stage queued for this original remaining allocation. Later registered programmes have no actual GO. No source switch or clock rearm.'))
 q=subprocess.run([sys.executable,'-B',str(H/'close_terminal_once.py')],cwd=R,capture_output=True,timeout=150);(H/'CLOSE_DRIVER.private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
 d=read(H/'CLOSEOUT.json');upper=math.ceil((d['gpu_usd']+2)*100)/100;ledger=R/'results/g_agreement/compute.jsonl';rows=[json.loads(x)for x in ledger.read_text().splitlines()if x.strip()];assert not any(x.get('run_id')==s['run_id']for x in rows)
 with(H/'BOOK_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),upper=upper),f)
 d['closed_all_in_upper_usd']=upper;rel='results/g_agreement/i2/E84_FROZEN6C_CLOSEOUT223.json';write(R/rel,d)
 with ledger.open('a')as f:f.write(json.dumps(dict(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),track='I-2',experiment='E84',run_id=s['run_id'],gpu_seconds=d['gpu_seconds'],usd=d['gpu_usd'],conservative_extras_upper_usd=2,closed_all_in_upper_usd=upper,closeout_receipt=rel,booked_once=True))+'\n')
 for rel in ['results/g_agreement/i2/STATUS.json','cache/g_agreement/i2/ACTIVE_CONTROLLER_HANDOFF.json']:
  p=R/rel;x=read(p);assert x['closed_all_in_upper_usd']>=302.95 and x['GPU_budget_window_closed_upper_usd']>=280.41;x.update(i2_reservations_usd=max(0,x['i2_reservations_usd']-7.29),closed_all_in_upper_usd=round(x['closed_all_in_upper_usd']+upper,2),GPU_budget_window_closed_upper_usd=round(x['GPU_budget_window_closed_upper_usd']+upper,2));x['E84_frozen6c'].update(state=d['status'],scientific_status=d['scientific_status'],closeout_receipt='results/g_agreement/i2/E84_FROZEN6C_CLOSEOUT223.json');write(p,x)
 write(H/'WATCH_TERMINAL.json',dict(status='COMPLETE_EXACT_OWNED_RETRIEVED_CLOSED_BOOKED_ONCE',scientific_status=d['scientific_status'],upper=upper,publication_required=True));print('E84 exact-owned terminal retrieval/closure/booking complete; publish original science next')
if __name__=='__main__':main()
