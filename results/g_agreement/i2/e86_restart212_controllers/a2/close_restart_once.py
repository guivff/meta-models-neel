"""Close only the exact terminal E99 read allocation; creation-to-first EXITED once."""
import sys,json,time,hashlib,os,signal,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import allocate_once as a
H=a.HOME

def inspect(pid):
 p=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
 return p.stdout.strip() if p.returncode==0 else None

def main():
 s=json.loads(a.STATE.read_text());pull=json.loads((H/('FULL_PULL_VERIFIED.json' if (H/'FULL_PULL_VERIFIED.json').exists() else 'PULL_VERIFIED.json')).read_text());assert pull['verified'] and pull['status'] in ['COMPLETE','PROFILE_ONLY']
 m=json.loads((H/'PREPARATION.json').read_text());assert m['experiment']=='E86' and m['mode']=='read' and s['run_id']==m['run_id']
 exit_record=json.loads((H/('full_terminal_pull/EXIT_FULL.json' if pull['status']=='COMPLETE' else 'terminal_pull/EXIT.json')).read_text());assert exit_record.get('code')==0,'SUCCESSFUL_EXIT_REQUIRED'
 if pull['status']=='COMPLETE':assert pull['exact_released_test_ids'] and pull['full_scientific_outputs']==800
 else:
  assert pull['profile_source_input_assignment_verified'] and not (H/'FULL_READ_ONCE_INTENT.json').exists()
  profile=json.loads((H/'terminal_pull/outputs/MEASURED_PROFILE.json').read_text());assert time.time()+profile['forecast_seconds']>=s['hard_deadline_epoch']-15,'ELIGIBLE_FULL_READ_MUST_NOT_BE_LEFT_IDLE'
 review=json.loads((H/'QUEUE_REVIEW.private.json').read_text())
 assert review['run_id']==s['run_id'] and review['original_deadline_epoch']==s['hard_deadline_epoch']
 assert review['no_eligible_queued_job'] is True and review['reason'] and 0<=time.time()-review['checked_epoch']<300,'FRESH_ACTUAL_QUEUE_REVIEW_REQUIRED'
 with (H/'CLOSE_ONCE_INTENT.json').open('x') as f:json.dump(dict(at=time.time(),run_id=s['run_id']),f)
 gd=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r/offvolume')/s['pod_id']/'mac_guard';g=dict(x.split('=',1) for x in (gd/'state').read_text().splitlines() if '=' in x)
 owned=[]
 for kind in ['hardstop','watchdog']:
  for key in [kind+'_pid',kind+'_caffeinate_pid']:
   pid=int(g[key]);cmd=inspect(pid);assert cmd is not None and s['pod_id'] in cmd and 'ws2_'+kind+'.sh' in cmd,'OWNED_GUARD_IDENTITY';owned.append((pid,cmd))
 ab=json.loads((H/'ABSOLUTE_GUARD.private.json').read_text());cmd=inspect(ab['pid']);assert cmd and 'absolute_stop.py' in cmd;owned.append((ab['pid'],cmd))
 q='query { pod(input:{podId:'+json.dumps(s['pod_id'])+'}) { id name desiredStatus createdAt costPerHr gpuCount } }'
 def observe():
  x=a.api(q)['pod']
  if x is not None:assert x['id']==s['pod_id'] and x['name']==s['run_id'] and x['createdAt']==s['provider_creation']['createdAt'] and x['gpuCount']==1
  return x
 p=observe();assert p is not None
 queue=dict(at=time.time(),pod_id=s['pod_id'],reason=review['reason'],no_eligible_queued_job=True)
 (H/'QUEUE_BEFORE_STOP.private.json').write_text(json.dumps(queue,indent=2)+'\n')
 with Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i2/results/g_agreement/i2/HANDOFF.md').open('a') as f:f.write('\n'+str(time.time())+' E86 section212 read restart COMPLETE verified; scientific outputs retained and queue reviewed before exact allocation closes exact EXITED twice→termination/query-null→retire owned guards, cost creation-firstEXITED once.\n')
 if p['desiredStatus']!='EXITED':a.api('mutation { podStop(input:{podId:'+json.dumps(s['pod_id'])+'}) { id desiredStatus } }')
 first=None
 for _ in range(30):
  p=observe()
  if p is not None and p['desiredStatus']=='EXITED':first=time.time();break
  time.sleep(2)
 assert first is not None,'STOP_UNCONFIRMED_NO_TERMINATE'
 (H/'FIRST_EXITED.private.json').write_text(json.dumps(dict(at=first,pod=p),indent=2)+'\n')
 assert observe()['desiredStatus']=='EXITED'
 with (H/'TERMINATE_ONCE_INTENT.json').open('x') as f:json.dump(dict(at=time.time(),EXITED_twice=True),f)
 a.api('mutation { podTerminate(input:{podId:'+json.dumps(s['pod_id'])+'}) }')
 assert observe() is None,'QUERY_NULL_NOT_CONFIRMED'
 durable=json.loads((H/'DURABLE_GUARD_LABEL.json').read_text());assert durable['label']=='com.mats.i2.e86.read.restart.a2.stop' and durable['original_deadline']==s['hard_deadline_epoch']
 subprocess.run(['launchctl','remove',durable['label']],capture_output=True)
 retired=[]
 for pid,cmd in owned:
  if inspect(pid)==cmd:
   os.kill(pid,signal.SIGTERM);time.sleep(.1)
   if inspect(pid)==cmd:os.kill(pid,signal.SIGKILL);time.sleep(.1)
  assert inspect(pid)!=cmd,'OWNED_GUARD_REMAINS';retired.append(dict(pid=pid,owned_absent=True))
 result=dict(experiment='E86',run_id=s['run_id'],status=pull['status']+'_TERMINATED_QUERY_NULL_GUARDS_RETIRED',created_epoch=s['created_epoch'],first_EXITED_epoch=first,gpu_seconds=first-s['created_epoch'],gpu_usd=(first-s['created_epoch'])*float(s['provider_creation']['costPerHr'])/3600,conservative_extras_upper_usd=2,actual_hourly_rate=float(s['provider_creation']['costPerHr']),reservation_released_usd=m['gpu_forecast_upper_usd'],partial_readouts_unopened=True,output_seal_sha256=pull['output_seal_sha256'],guard_processes_retired=len(retired),no_replay=True)
 (H/'CLOSEOUT.json').write_text(json.dumps(result,indent=2)+'\n');s.update(status=result['status'],closed_epoch=time.time());a.save(s);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
