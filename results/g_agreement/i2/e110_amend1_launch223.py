"""One authorized E110 parallel restart; serial fresh creates, concurrent stages.
Each child retains its own creation-bound cap and independent/durable guards.
"""
from pathlib import Path
import subprocess,json,os,time,fcntl,hashlib
R=Path(__file__).resolve().parents[3];BASE=R/'cache/g_agreement/i2/e110_filter_amend1_v1'
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);q=p.with_suffix('.new');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def run(h,name,args=()):
 with(h/(name+'.driver.private.log')).open('ab')as log:
  p=subprocess.run(['python3','-B',str(h/name),*args],cwd=R,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 return p.returncode

def main():
 os.umask(0o077);lock=(BASE/'BATCH_DISPATCH.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert read(BASE/'PROJECTION_PUBLICATION.json')['shared_commit']
 with(BASE/'RESTART_BATCH_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),authority='aa8438c71',prior192excluded=True),f)
 state=dict(status='LAUNCHING_ORIGINAL_FOUR_SHARDS',started_epoch=time.time(),shards=[]);children=[];write(BASE/'BATCH_STATE.private.json',state)
 for i in range(4):
  h=BASE/f'shard{i}';assert not(h/'CREATE_ONCE_INTENT.json').exists();row=dict(shard=i,status='FRESH_ADMISSION_AND_ALLOCATION');state['shards'].append(row);write(BASE/'BATCH_STATE.private.json',state)
  code=run(h,'allocate_once.py',['--allocate-once']);s=read(h/'ALLOCATION.private.json')if(h/'ALLOCATION.private.json').exists()else{}
  if code:
   row.update(status='ALLOCATION_HOLD_RECONCILE_NO_REPLAY',exit_code=code);state['status']='HOLD_NO_FURTHER_CREATES';write(BASE/'BATCH_STATE.private.json',state);raise RuntimeError('ALLOCATION_HOLD_RECONCILE')
  assert s['status']=='ARMED_WAITING_INDEPENDENT_PARENT_EXIT_PROOF' and s['hard_deadline_epoch']==s['created_epoch']+2616
  row.update(status='ORIGINAL_DUAL_GUARDS_ARMED',created_epoch=s['created_epoch'],original_deadline_epoch=s['hard_deadline_epoch']);write(BASE/'BATCH_STATE.private.json',state)
  assert run(h,'arm_durable_once.py')==0,'DURABLE_GUARD_HOLD'
  log=(h/'STAGE_DRIVER.private.log').open('ab');p=subprocess.Popen(['python3','-B',str(h/'stage_and_start.py')],cwd=R,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);log.close();children.append((i,p));row.update(status='GUARDED_STAGING',stage_driver_pid=p.pid);write(BASE/'BATCH_STATE.private.json',state)
 for i,p in children:
  code=p.wait();state['shards'][i].update(stage_exit=code,status='WORKER_STARTED_ORIGINAL_DEADLINE'if code==0 else'STAGE_FAILURE_RETRIEVE_CLOSE');write(BASE/'BATCH_STATE.private.json',state)
 state['status']='ALL_FOUR_STAGE_DRIVERS_TERMINAL_WORKERS_OWN_ORIGINAL_CLOCKS';state['finished_epoch']=time.time();write(BASE/'BATCH_STATE.private.json',state);print('E110 four-shard stage launch orchestration finished; workers retain original clocks')
if __name__=='__main__':main()
