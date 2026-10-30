"""New regenerated E110 source epoch: four fresh claims, concurrent stages/watches."""
from pathlib import Path
import json,subprocess,time,os,fcntl,sys
from datetime import datetime
R=Path(__file__).resolve().parents[3];H=R/'cache/g_agreement/i2/e110_dev2_filter_v1';API='/Users/guivff/repl/tools/runpod_api.sh'
read=lambda p:json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);q=p.with_suffix('.new');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def child(home,name,args=()):
 with(home/(name+'.driver.private.log')).open('ab')as f:return subprocess.run([sys.executable,'-B',str(home/name),*args],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True).returncode

def capacity():
 q='query { myself { networkVolumes { id dataCenterId } pods { desiredStatus costPerHr createdAt } } dataCenters { id gpuAvailability(input:{gpuCount:1,secureCloud:true}) { gpuTypeId available } } }'
 while True:
  r=subprocess.run(['bash',API,q],capture_output=True,text=True,timeout=45);assert r.returncode==0;d=json.loads(r.stdout);assert not d.get('errors');allpods=d['data']['myself']['pods'];pods=[x for x in allpods if x['desiredStatus']=='RUNNING'];assert all(x.get('costPerHr')is not None for x in pods),'UNKNOWN_RATE_HOLD'
  v=next(x for x in d['data']['myself']['networkVolumes']if x['id']=='5on6935gne');stock=any(g['gpuTypeId']=='NVIDIA H200'and g['available']for dc in d['data']['dataCenters']if dc['id']==v['dataCenterId']for g in dc['gpuAvailability']);assert time.time()<1793286000,'FILTER_CUTOFF_NO_NEW_CREATE';newest=max((datetime.fromisoformat(x['createdAt'].replace('Z','+00:00')).timestamp()for x in allpods if x.get('createdAt')),default=0);spacing_ok=time.time()>=newest+180;hourly=sum(float(x['costPerHr'])for x in pods);write(H/'CURRENT_CAPACITY.private.json',dict(at=time.time(),running=len(pods),actual_hourly_usd=hourly,target_H200_stock=bool(stock),preclaim_spacing180_verified=spacing_ok,next_upper_hourly=5.29,ceiling=80))
  if stock and spacing_ok and len(pods)<19 and hourly+5.29<=80:return
  time.sleep(30)

def main():
 os.umask(0o077);lock=(H/'BATCH_DISPATCH.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);plan=read(H/'CAP_PLAN.json');assert plan['effective_total_cap_seconds']==3600 and sum(x['cap_seconds']for x in plan['shards'])==3600 and all(x['cap_seconds']==900 for x in plan['shards']) and plan['whole_four_shard_upper_usd']<=25 and read(H/'PROJECTION_PUBLICATION.json')['shared_commit']
 refused=read(H/'shard0/ALLOCATION.private.json');assert refused['status']=='FAILED_RECONCILE_DO_NOT_REPLAY'and not refused.get('pod_id')
 assert (H/'DEV2_BATCH_ONCE_INTENT.json').exists()and(H/'DEV2_UNCLAIMED_CONTINUATION_ONCE_INTENT.json').exists()
 operational=read(H/'OPERATIONAL_HOMES.json');assert operational['shards']==['shard0b','shard1b','shard2','shard3']
 assert read(H/'shard0b/ALLOCATION.private.json')['status']=='WORKER_STARTED_ORIGINAL_DEADLINE'
 assert(H/'shard0b/TERMINAL_WATCH_ONCE_INTENT.json').exists()
 for name in operational['shards'][1:]:
  home=H/name;assert not(home/'CREATE_ONCE_INTENT.json').exists()and not(home/'ALLOCATION.private.json').exists()and not(home/'ENGINE_ONCE_INTENT.json').exists()and not(home/'TERMINAL_WATCH_ONCE_INTENT.json').exists()
 assert read(H/'POST_E84_CLOSE_STATE.private.json')['status']=='HOLD_NO_FURTHER_CREATES'
 with(H/'DEV2_REMAINING123_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),source_epoch=plan['bank_seal_sha256'],original_refused_claim_preserved=True,only_new_unallocated_homes=True,total_new_gpu_seconds=3600),f)
 state=dict(status='LAUNCHING_NEW_SOURCE_FOUR_QUARTERS',started_epoch=time.time(),shards=[]);processes=[]
 for e in plan['shards'][1:]:
  i=e['shard'];home=H/operational['shards'][i];row=dict(shard=i,status='WAITING_LIVE_CAPACITY_BEFORE_ANY_CREATE_CLAIM');state['shards'].append(row);write(H/'REMAINING123_STATE.private.json',state);capacity()
  assert not(home/'CREATE_ONCE_INTENT.json').exists();code=child(home,'allocate_once.py',['--allocate-once']);s=read(home/'ALLOCATION.private.json')if(home/'ALLOCATION.private.json').exists()else{}
  if code:row.update(status='ADMISSION_HOLD_RECONCILE_NO_REPLAY',exit_code=code);state['status']='HOLD_NO_FURTHER_CREATES';write(H/'REMAINING123_STATE.private.json',state);raise RuntimeError('ACTUAL_ADMISSION_HOLD')
  assert s['status']=='ARMED_WAITING_INDEPENDENT_PARENT_EXIT_PROOF'and s['hard_deadline_epoch']==s['created_epoch']+e['cap_seconds'];assert child(home,'arm_durable_once.py')==0
  with(home/'STAGE_DRIVER.private.log').open('ab')as f:p=subprocess.Popen([sys.executable,'-B',str(home/'stage_and_start.py')],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  with(home/'WATCH_DRIVER.private.log').open('ab')as f:w=subprocess.Popen([sys.executable,'-B',str(R/'results/g_agreement/i2/e110_dev2_remaining_watch227.py'),'--experiment',f'E110_DEV2_S{i}'],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  processes.append((i,p));row.update(status='ORIGINAL_GUARDED_STAGE_AND_TERMINAL_WATCH_ACTIVE',stage_pid=p.pid,watch_pid=w.pid,created_epoch=s['created_epoch'],original_deadline=s['hard_deadline_epoch']);write(H/'REMAINING123_STATE.private.json',state)
 for i,p in processes:
  code=p.wait();next(x for x in state['shards']if x['shard']==i).update(stage_exit=code,status='WORKER_STARTED_ORIGINAL_DEADLINE'if code==0 else'STAGE_FAILURE_RETRIEVE_CLOSE');write(H/'REMAINING123_STATE.private.json',state)
 state.update(status='ALL_FOUR_STAGE_DRIVERS_DONE_SEPARATE_EXACT_WATCHERS_OWN_TERMINALS',finished_epoch=time.time());write(H/'REMAINING123_STATE.private.json',state);print('Four new regenerated-source filter stage drivers complete; each has exact terminal watcher')
if __name__=='__main__':main()
