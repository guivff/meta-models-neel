"""One explicitly approved fresh E110 quarter3 attempt; all failed/complete originals immutable."""
from pathlib import Path
import json,subprocess,sys,time,os,fcntl
from e110_dev2_remaining123_closed227 import capacity,child,read,write
R=Path(__file__).resolve().parents[3];H=R/'cache/g_agreement/i2/e110_dev2_filter_v1';home=H/'shard3b'
def main():
 os.umask(0o077);lock=(H/'BATCH_DISPATCH.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 approval=read(R/'results/g_agreement/i2/E110_DEV2_S3_1256_DIRECT_APPROVAL.json');assert approval['new_attempts_authorized']==1 and approval['cap_seconds']==1256 and approval['total_newbank_GPU_seconds_upper']<=3600
 assert read(H/'shard3/TERMINAL_WATCH_COMPLETE.json')['scientific_status']=='NO_FIT'
 for i,n in enumerate(['shard0b','shard1b','shard2']):assert read(H/n/'TERMINAL_WATCH_COMPLETE.json')['scientific_status']=='COMPLETE'
 assert not(home/'CREATE_ONCE_INTENT.json').exists()and not(home/'ALLOCATION.private.json').exists()
 with(H/'S3_APPROVED1256_DRIVER_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),cap_seconds=1256,approval=approval['answer'],old_partial_excluded=True),f)
 write(H/'S3_APPROVED1256_STATE.private.json',dict(status='WAIT_REAL_STOCK_AND_SPACING_BEFORE_CREATE_CLAIM',at=time.time()));capacity()
 assert child(home,'allocate_once.py',['--allocate-once'])==0,'ADMISSION_HOLD_NO_REPLAY'
 state=read(home/'ALLOCATION.private.json');assert state['status']=='ARMED_WAITING_INDEPENDENT_PARENT_EXIT_PROOF'and state['hard_deadline_epoch']==state['created_epoch']+1256
 assert child(home,'arm_durable_once.py')==0
 with(home/'WATCH_DRIVER.private.log').open('ab')as f:w=subprocess.Popen([sys.executable,'-B',str(R/'results/g_agreement/i2/e110_dev2_s3_retry_watch227.py'),'--experiment','E110_DEV2_S3_RETRY'],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 with(home/'STAGE_DRIVER.private.log').open('ab')as f:p=subprocess.Popen([sys.executable,'-B',str(home/'stage_and_start.py')],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 write(H/'S3_APPROVED1256_STATE.private.json',dict(status='ORIGINAL_GUARDED_STAGE_AND_SOLE_WATCH_ACTIVE',at=time.time(),stage_pid=p.pid,watch_pid=w.pid));code=p.wait();write(H/'S3_APPROVED1256_STATE.private.json',dict(status='WORKER_STARTED_ORIGINAL_DEADLINE'if code==0 else'STAGE_FAILURE_RECONCILE_EXACT_GPU_NO_REPLAY',at=time.time(),stage_exit=code))
 assert code==0
if __name__=='__main__':main()
