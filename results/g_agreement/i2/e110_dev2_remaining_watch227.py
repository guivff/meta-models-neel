"""One exact-owned watcher per new §217c3 native attempt. No scientific rerun."""
from pathlib import Path
import argparse,json,time,subprocess,sys,os,hashlib,math,datetime,fcntl,shutil
R=Path(__file__).resolve().parents[3]
CONFIG={'E110_DEV2_S0': ('e110_dev2_filter_v1/shard0b', 900, 3.33, 'E110_DEV2_FILTER_SHARD0'), 'E110_DEV2_S1': ('e110_dev2_filter_v1/shard1b', 900, 3.33, 'E110_DEV2_FILTER_SHARD1'), 'E110_DEV2_S2': ('e110_dev2_filter_v1/shard2', 900, 3.33, 'E110_DEV2_FILTER_SHARD2'), 'E110_DEV2_S3': ('e110_dev2_filter_v1/shard3', 900, 3.33, 'E110_DEV2_FILTER_SHARD3')}
read=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);q=p.with_suffix('.new');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def main():
 p=argparse.ArgumentParser();p.add_argument('--experiment',choices=CONFIG,required=True);exp=p.parse_args().experiment;relative,cap,reserve,label=CONFIG[exp];h=R/'cache/g_agreement/i2'/relative;sys.path.insert(0,str(h));import stage_and_start as st
 os.umask(0o077)
 with(h/'TERMINAL_WATCH_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),pid=os.getpid(),source_sha256=sha(__file__),experiment=exp),f)
 while True:
  s=read(h/'ALLOCATION.private.json');m=read(h/'PREPARATION.json');assert m['experiment']=='E110_FILTER_DEV2' and s['run_id']==m['run_id']and s['hard_deadline_epoch']==s['created_epoch']+cap
  if s['status']in('ARMED_WAITING_INDEPENDENT_PARENT_EXIT_PROOF','STAGING'):assert time.time()<s['created_epoch']+930,'SETUP900_RECONCILE';time.sleep(10);continue
  assert s['status']=='WORKER_STARTED_ORIGINAL_DEADLINE','STAGE_STATE_RECONCILE'
  q=f"cd {s['remote_dir']}\n/weights/venv-kernels/bin/python - <<'REMOTE'\nimport json\nfrom pathlib import Path\nprint(json.dumps(dict(terminal=Path('EXIT.json').exists(),seal=Path('outputs/OUTPUT_SEAL.json').exists())))\nREMOTE\n";flags=json.loads(st.ssh(s,q,30));write(h/'TERMINAL_WATCH_PROGRESS.json',dict(at=time.time(),flags=flags,original_deadline=s['hard_deadline_epoch']))
  if flags['terminal']:break
  assert time.time()<s['hard_deadline_epoch']+60,'ORIGINAL_DEADLINE_RECONCILE';time.sleep(10)
 for script in ['pull_terminal_once.py']:
  q=subprocess.run([sys.executable,'-B',str(h/script)],cwd=R,capture_output=True,timeout=180);(h/(script+'.driver.private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,'EXACT_TERMINAL_PULL_RECONCILE'
 status=read(R/'results/g_agreement/i2/STATUS.json');write(h/'QUEUE_REVIEW.private.json',dict(run_id=s['run_id'],original_deadline_epoch=s['hard_deadline_epoch'],checked_epoch=time.time(),no_eligible_queued_job=True,status_sha256=sha(R/'results/g_agreement/i2/STATUS.json'),reason='Current exact native worker terminal and verified. Other authorized experiments have separately source-bound new allocation claims/guards; no eligible unclaimed stage has admission/opt-in for this original allocation and remaining clock. No source switch, duplicate acquisition or guard rearm authorized.'))
 q=subprocess.run([sys.executable,'-B',str(h/'close_terminal_once.py')],cwd=R,capture_output=True,timeout=150);(h/'CLOSE_DRIVER.private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,'EXACT_OWNED_CLOSE_RECONCILE'
 close=read(h/'CLOSEOUT.json');upper=math.ceil((close['gpu_usd']+2)*100)/100;lock=(R/'cache/g_agreement/i2/COST_BOOK.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX);ledger=R/'results/g_agreement/compute.jsonl';rows=[json.loads(x)for x in ledger.read_text().splitlines()if x.strip()];assert not any(x.get('run_id')==s['run_id']for x in rows)
 with(h/'BOOK_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),upper=upper),f)
 rel='results/g_agreement/i2/'+label+'_CLOSEOUT.json';close.update(closed_all_in_upper_usd=upper,original_cumulative_prior_seconds=m['prior_probe_gpu_seconds'],cumulative_gpu_seconds=m['prior_probe_gpu_seconds']+close['gpu_seconds']);write(R/rel,close)
 with ledger.open('a')as f:f.write(json.dumps(dict(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),track='I-2',experiment='E110_FILTER_DEV2',run_id=s['run_id'],gpu_seconds=close['gpu_seconds'],usd=close['gpu_usd'],conservative_extras_upper_usd=2,closed_all_in_upper_usd=upper,reservation_released_usd=reserve,closeout_receipt=rel,booked_once=True))+'\n')
 for name in ['results/g_agreement/i2/STATUS.json','cache/g_agreement/i2/ACTIVE_CONTROLLER_HANDOFF.json']:
  p=R/name;x=read(p);x['closed_all_in_upper_usd']=round(x['closed_all_in_upper_usd']+upper,2);x['GPU_budget_window_closed_upper_usd']=round(x['GPU_budget_window_closed_upper_usd']+upper,2);x['i2_reservations_usd']=max(0,round(x['i2_reservations_usd']-reserve,2));x.setdefault('measured_c3_runs',{})[exp]=dict(state='TERMINAL_VERIFIED_CLOSED_BOOKED_ONCE',scientific_status=close['scientific_status'],closeout_receipt=rel,upper_usd=upper,publication_required=True);write(p,x)
 fcntl.flock(lock,fcntl.LOCK_UN);dest=R/'results/g_agreement/sealed'/label;assert not dest.exists();shutil.copytree(h/'terminal_pull/outputs',dest,ignore=shutil.ignore_patterns('ASSIGNMENT.json'));write(h/'TERMINAL_WATCH_COMPLETE.json',dict(at=time.time(),status='TERMINAL_VERIFIED_CLOSED_BOOKED_ONCE',scientific_status=close['scientific_status'],upper_usd=upper,public_seal_directory=str(dest),publication_required=True));print(exp,'terminal retrieved/closed/booked once; publish original science and deliver complete packet if eligible')
if __name__=='__main__':main()
