"""New regenerated E110 source epoch: four fresh claims, concurrent stages/watches."""
from pathlib import Path
import json,subprocess,time,os,fcntl,sys
R=Path(__file__).resolve().parents[3];H=R/'cache/g_agreement/i2/e110_dev2_filter_v1';API='/Users/guivff/repl/tools/runpod_api.sh'
read=lambda p:json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);q=p.with_suffix('.new');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def child(home,name,args=()):
 with(home/(name+'.driver.private.log')).open('ab')as f:return subprocess.run([sys.executable,'-B',str(home/name),*args],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True).returncode

def capacity():
 q='query { myself { pods { desiredStatus costPerHr } } }'
 while True:
  r=subprocess.run(['bash',API,q],capture_output=True,text=True,timeout=45);assert r.returncode==0;d=json.loads(r.stdout);assert not d.get('errors');pods=[x for x in d['data']['myself']['pods']if x['desiredStatus']=='RUNNING'];assert all(x.get('costPerHr')is not None for x in pods),'UNKNOWN_RATE_HOLD'
  hourly=sum(float(x['costPerHr'])for x in pods);write(H/'CURRENT_CAPACITY.private.json',dict(at=time.time(),running=len(pods),actual_hourly_usd=hourly,next_upper_hourly=5.29,ceiling=80))
  if len(pods)<19 and hourly+5.29<=80:return
  time.sleep(30)

def main():
 os.umask(0o077);lock=(H/'BATCH_DISPATCH.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);plan=read(H/'CAP_PLAN.json');assert plan['effective_total_cap_seconds']==3600 and sum(x['cap_seconds']for x in plan['shards'])==3600 and all(x['cap_seconds']==900 for x in plan['shards']) and plan['whole_four_shard_upper_usd']<=25 and read(H/'PROJECTION_PUBLICATION.json')['shared_commit']
 with(H/'DEV2_BATCH_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),source_epoch=plan['bank_seal_sha256'],all_previous_outputs_excluded=True),f)
 state=dict(status='LAUNCHING_NEW_SOURCE_FOUR_QUARTERS',started_epoch=time.time(),shards=[]);processes=[]
 for e in plan['shards']:
  i=e['shard'];home=H/f'shard{i}';row=dict(shard=i,status='WAITING_LIVE_CAPACITY_BEFORE_ANY_CREATE_CLAIM');state['shards'].append(row);write(H/'BATCH_STATE.private.json',state);capacity()
  assert not(home/'CREATE_ONCE_INTENT.json').exists();code=child(home,'allocate_once.py',['--allocate-once']);s=read(home/'ALLOCATION.private.json')if(home/'ALLOCATION.private.json').exists()else{}
  if code:row.update(status='ADMISSION_HOLD_RECONCILE_NO_REPLAY',exit_code=code);state['status']='HOLD_NO_FURTHER_CREATES';write(H/'BATCH_STATE.private.json',state);raise RuntimeError('ACTUAL_ADMISSION_HOLD')
  assert s['status']=='ARMED_WAITING_INDEPENDENT_PARENT_EXIT_PROOF'and s['hard_deadline_epoch']==s['created_epoch']+e['cap_seconds'];assert child(home,'arm_durable_once.py')==0
  with(home/'STAGE_DRIVER.private.log').open('ab')as f:p=subprocess.Popen([sys.executable,'-B',str(home/'stage_and_start.py')],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  with(home/'WATCH_DRIVER.private.log').open('ab')as f:w=subprocess.Popen([sys.executable,'-B',str(R/'results/g_agreement/i2/e110_dev2_terminal_watch227.py'),'--experiment',f'E110_DEV2_S{i}'],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  processes.append((i,p));row.update(status='ORIGINAL_GUARDED_STAGE_AND_TERMINAL_WATCH_ACTIVE',stage_pid=p.pid,watch_pid=w.pid,created_epoch=s['created_epoch'],original_deadline=s['hard_deadline_epoch']);write(H/'BATCH_STATE.private.json',state)
 for i,p in processes:
  code=p.wait();state['shards'][i].update(stage_exit=code,status='WORKER_STARTED_ORIGINAL_DEADLINE'if code==0 else'STAGE_FAILURE_RETRIEVE_CLOSE');write(H/'BATCH_STATE.private.json',state)
 state.update(status='ALL_FOUR_STAGE_DRIVERS_DONE_SEPARATE_EXACT_WATCHERS_OWN_TERMINALS',finished_epoch=time.time());write(H/'BATCH_STATE.private.json',state);print('Four new regenerated-source filter stage drivers complete; each has exact terminal watcher')
if __name__=='__main__':main()
