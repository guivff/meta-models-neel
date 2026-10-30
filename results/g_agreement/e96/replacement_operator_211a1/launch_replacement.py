"""One-shot allocation under deviation2; require a fresh posted admission receipt."""
import argparse,datetime,json,os,pathlib,plistlib,subprocess,time,types
from decimal import Decimal
from .replacement_custody import query,sha,write,provider
P=pathlib.Path
ROOT=P('/private/tmp/e96-i4-slot1-r1')
def launch(root=ROOT):
 unpark=root/'UNPARKED_211_AMENDMENT1.json'
 if (root/'PARKED_211.json').exists() and not unpark.exists():raise ValueError('replacement parked under§211; no amendment receipt')
 if unpark.exists() and json.loads(unpark.read_text()).get('authority_commit')!='7a3545305c906d516404a7a83f2c868b1547d9a0':raise ValueError('unparking authority mismatch')
 if (root/'STATE.json').exists() or (root/'CREATE_REQUEST.json').exists():raise ValueError('one replacement allocation only; reconcile existing request')
 admission=json.loads((root/'ADMISSION.json').read_text());now=time.time()
 if now-datetime.datetime.fromisoformat(admission['as_of_utc']).timestamp()>600:raise ValueError('fresh posted admission required')
 if not admission['posted_shared_commit'] or not admission['launch_admitted']:raise ValueError('posted admission not admitted')
 if unpark.exists():
  if not admission.get('all_core_running_or_sealed') or admission.get('parked_pool_cap_usd')!=900 or Decimal(str(admission.get('parked_pool_committed_with_this_usd',901)))>900:raise ValueError('CORE readiness and parked900 pool gate')
  if now>=datetime.datetime.fromisoformat('2026-10-30T00:00:00+01:00').timestamp():raise ValueError('new launch deadline expired')
 if Decimal(str(admission['conservative_programme_with_replacement_usd']))>1500:raise ValueError('global1500ceiling')
 pre=json.loads((root/'PREFLIGHT.json').read_text())
 for n,h in pre['control_plane_files'].items():
  if sha(root/n)!=h:raise ValueError('preflight payload changed '+n)
 data=query('query { myself { pods { id name desiredStatus costPerHr } } gpuTypes(input:{id:"NVIDIA H200"}) { id securePrice } }')
 pods=data['myself']['pods'];name='e96-i4-slot1-replacement-once-20261028'
 if any(p['name']==name for p in pods):raise ValueError('replacement pod already exists; never duplicate')
 rate=Decimal(str(data['gpuTypes'][0]['securePrice']));hourly=sum((Decimal(str(p['costPerHr'])) for p in pods if p['desiredStatus']=='RUNNING'),Decimal(0))
 if rate>Decimal('5.29') or hourly+rate>80:raise ValueError('current quote/provider hourly gate; no allocation submitted')
 root.chmod(0o700)
 with (root/'CREATE_REQUEST.json').open('x') as f:json.dump({'requested_epoch':now,'name':name,'authority':'2bdde763','admission_sha256':sha(root/'ADMISSION.json')},f)
 env=dict(os.environ,WS2_DEPLOY_LOG=str(root/'DEPLOYS.jsonl'))
 cmd=['bash','/private/tmp/e96-i4-durable/guard_scripts/ws2_offvolume.sh','deploy-vol','NVIDIA H200','5on6935gne',name]
 try:r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=90)
 except subprocess.TimeoutExpired as exc:
  def decoded(v):return v.decode() if isinstance(v,bytes) else (v or '')
  r=types.SimpleNamespace(returncode=124,stdout=decoded(exc.stdout),stderr=decoded(exc.stderr)+'\nCREATE timeout; reconcile unique name, never resubmit')
 (root/'ALLOCATION.log').write_text(r.stdout+r.stderr)
 pod=r.stdout.strip().splitlines()[-1] if r.returncode==0 and r.stdout.strip() else None
 if not pod or not pod.isalnum():
  matches=[p for p in query('query { myself { pods { id name } } }')['myself']['pods'] if p['name']==name]
  if len(matches)==1:pod=matches[0]['id']
  elif not matches and r.returncode not in (0,124):
   # Definitive no-ID rejection is availability, not a failed scientific rerun.
   (root/'CREATE_REQUEST.json').rename(root/('NO_ALLOCATION_'+str(time.time_ns())+'.json'))
   raise RuntimeError('provider refused before creation; no replacement attempt consumed')
  else:raise RuntimeError('allocation ambiguous; do not resubmit')
 p=query('query { pod(input:{podId:"'+pod+'"}) { id name desiredStatus createdAt costPerHr gpuCount } }')['pod']
 if p['name']!=name or p['gpuCount']!=1:raise ValueError('allocation identity')
 created=datetime.datetime.fromisoformat(p['createdAt'].replace('Z','+00:00')).timestamp()
 state={'experiment':'E96','slot':1,'attempt':'replacement-once','authority_commit':'2bdde763','pod_id':pod,'pod_name':name,'created_utc':p['createdAt'],'created_epoch':created,'rate':p['costPerHr'],'gpu_type':'H200','cap_seconds':14400,'hard_deadline_epoch':created+14400,'source_seal_sha256':pre['unchanged_source_seal_sha256'],'archive_sha256':pre['unchanged_worker_archive_sha256'],'status':'GUARDED_STAGING','admission_sha256':sha(root/'ADMISSION.json')}
 write(root/'STATE.json',state)
 assignment=json.loads((root/'ORIGINAL_ASSIGNMENT.json').read_text());assignment.update(pod_id=pod,created_epoch=created,deadline_epoch=created+13920,projected_all_track_upper_usd=admission['conservative_programme_with_replacement_usd'],forecast_source='REPLACEMENT_ADMISSION.json',replacement_authority='2bdde763',maximum_attempts=1)
 write(root/'ASSIGNMENT.json',assignment)
 # Separate launchd services survive tool sessions. Only temporary/native-home paths.
 for mode in ('hardstop','supervise','stage'):
  label='com.mats.e96.i4.r1.'+mode;script=root/('replacement_stage.py' if mode=='stage' else 'replacement_custody.py')
  args=['/usr/bin/caffeinate','-i','/opt/homebrew/bin/python3.12',str(script)]+([str(root)] if mode=='stage' else [mode,str(root)])
  config={'Label':label,'ProgramArguments':args,'RunAtLoad':True,'KeepAlive':{'SuccessfulExit':False} if mode!='stage' else False,'ThrottleInterval':10,'WorkingDirectory':str(root),'StandardOutPath':str(root/(mode+'.log')),'StandardErrorPath':str(root/(mode+'.log')),'EnvironmentVariables':{'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'}}
  file=root/(mode+'.plist');file.write_bytes(plistlib.dumps(config))
  result=subprocess.run(['launchctl','bootstrap','gui/'+str(os.getuid()),str(file)],capture_output=True,text=True)
  if result.returncode:
   query('mutation { podStop(input:{podId:"'+pod+'"}) { id } }');raise RuntimeError('service registration failed; own new pod stopped, no worker retry')
  check=subprocess.run(['launchctl','print','gui/'+str(os.getuid())+'/'+label],capture_output=True,text=True)
  if check.returncode:raise RuntimeError('service verification failed')
  write(root/(mode+'_SERVICE.json'),{'label':label,'verified_epoch':time.time(),'registered':True,'original_created_epoch':created})
 if p['costPerHr']>5.29:
  query('mutation { podStop(input:{podId:"'+pod+'"}) { id } }');raise RuntimeError('actual quote exceeds admitted ceiling; stop')
 print(json.dumps({'pod_id':pod,'status':'OWNED_H200_REPLACEMENT_GUARDED_STAGING','cap_seconds':14400,'services':3,'original_created_utc':p['createdAt']}))
if __name__=='__main__':launch()
