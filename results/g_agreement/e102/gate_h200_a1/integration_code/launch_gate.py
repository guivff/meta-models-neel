"""One gate-only allocation with fresh posted admission and CORE headroom.

No production training command. Duplicate/ambiguous allocations fail closed.
Every service uses non-Documents files and the original provider creation time.
"""
import datetime,json,os,pathlib,plistlib,subprocess,time,types
from decimal import Decimal as D
from .gate_custody import query,write,sha
P=pathlib.Path
ROOT=P('/private/tmp/e102-i4-gate-a1')
NAME='e102-i4-oracle-gate-a1'

def launch(root=ROOT):
 if (root/'STATE.json').exists() or (root/'CREATE_REQUEST.json').exists():raise ValueError('existing gate allocation/request; never duplicate')
 admission=json.loads((root/'POSTED_ADMISSION.json').read_text())
 if time.time()-datetime.datetime.fromisoformat(admission['as_of_utc']).timestamp()>600:raise ValueError('fresh admission required')
 if not admission['posted_shared_commit'] or not admission['gate_only'] or admission['training_admitted'] or not admission['core_priority_checked']:raise ValueError('posted gate-only CORE-priority admission required')
 if D(str(admission['projected_all_track_upper_usd']))>1500:raise ValueError('worker gate conservative1500compatibility bound; refresh beforelaunch')
 if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime.fromisoformat('2026-10-29T12:00:00+01:00'):raise ValueError('feasibility deadline expired')
 plan=json.loads((root/'STAGING_PLAN.json').read_text())
 for n,h in plan['files'].items():
  if sha(root/n)!=h:raise ValueError('exact staging payload changed')
 gpu=admission['gpu_type']
 if gpu not in ('B200','H200'):raise ValueError('authorized GPU type only')
 data=query('query { myself { pods { id name desiredStatus costPerHr } } gpuTypes(input:{id:"NVIDIA '+gpu+'"}) { id securePrice } }')
 pods=data['myself']['pods']
 if any(p['name']==NAME for p in pods):raise ValueError('gate pod already exists; reconcile')
 active=[p for p in pods if p['desiredStatus']=='RUNNING'];hourly=sum((D(str(p['costPerHr'])) for p in active),D(0));quote=D(str(data['gpuTypes'][0]['securePrice']))
 allowed=set(admission['existing_active_names'])
 if not {p['name'] for p in active}<=allowed:raise ValueError('new allocation since posted all-track reconciliation; refresh')
 if quote>D(str(admission['quote_usd_hour'])) or hourly+quote+D(str(admission['core_reserved_hourly_headroom_usd']))>D(str(admission['provider_hourly_limit_usd'])):raise ValueError('price/provider/CORE headroom changed; noCREATE')
 root.chmod(0o700)
 with (root/'CREATE_REQUEST.json').open('x') as f:json.dump({'name':NAME,'requested_epoch':time.time(),'posted_admission_sha256':sha(root/'POSTED_ADMISSION.json'),'gate_only':True},f)
 env=dict(os.environ,WS2_DEPLOY_LOG=str(root/'DEPLOYS.jsonl'))
 try:
  result=subprocess.run(['bash','/private/tmp/e96-i4-durable/guard_scripts/ws2_offvolume.sh','deploy-vol','NVIDIA '+gpu,'5on6935gne',NAME],env=env,capture_output=True,text=True,timeout=90)
 except subprocess.TimeoutExpired as exc:
  # CREATE may have succeeded: reconcile the unique name; never resubmit.
  def decoded(value):return value.decode() if isinstance(value,bytes) else (value or '')
  result=types.SimpleNamespace(returncode=124,stdout=decoded(exc.stdout),stderr=decoded(exc.stderr)+'\nCREATE timeout; reconciliation required')
 (root/'ALLOCATION.log').write_text(result.stdout+result.stderr)
 pod=result.stdout.strip().splitlines()[-1] if result.returncode==0 and result.stdout.strip() else None
 if not pod or not pod.isalnum():
  matches=[p for p in query('query { myself { pods { id name } } }')['myself']['pods'] if p['name']==NAME]
  if len(matches)==1:pod=matches[0]['id']
  elif not matches and result.returncode not in (0,124):
   (root/'CREATE_REQUEST.json').rename(root/('NO_ALLOCATION_'+str(time.time_ns())+'.json'));raise RuntimeError('definitive no-ID refusal; no gate model attempt')
  else:raise RuntimeError('ambiguous allocation; no resubmission')
 p=query('query { pod(input:{podId:"'+pod+'"}) { id name createdAt costPerHr gpuCount } }')['pod']
 if p['id']!=pod or p['name']!=NAME or p['gpuCount']!=1:raise ValueError('allocation identity')
 created=datetime.datetime.fromisoformat(p['createdAt'].replace('Z','+00:00')).timestamp()
 state={'experiment':'E102_GATE','pod_id':pod,'pod_name':NAME,'created_utc':p['createdAt'],'created_epoch':created,'rate':p['costPerHr'],'gpu_type':gpu,'status':'GUARDED_STAGING','cap_seconds':3600,'hard_deadline_epoch':created+3600,'gate_only':True,'training_admitted':False,'worker_archive_sha256':admission['worker_archive_sha256']}
 write(root/'STATE.json',state)
 worker={'experiment':'E102_GATE','pod_id':pod,'gpu_count':1,'external_guard_armed':True,'input_seal_sha256':admission['input_seal_sha256'],'created_epoch':created,'deadline_epoch':created+3420,'projected_all_track_upper_usd':admission['projected_all_track_upper_usd'],'gate_only':True,'production_training_admitted':False}
 write(root/'ADMISSION.json',worker);plan['files']['ADMISSION.json']=sha(root/'ADMISSION.json');write(root/'STAGING_PLAN.json',plan)
 if D(str(p['costPerHr']))>quote:
  query('mutation { podStop(input:{podId:"'+pod+'"}) { id } }');raise RuntimeError('actual quote exceedsadmission; stopped beforeworker')
 for mode in ('hardstop','supervise','stage'):
  label='com.mats.e102.i4.gate.'+mode;script=root/('gate_stage.py' if mode=='stage' else 'gate_custody.py');args=['/usr/bin/caffeinate','-i','/opt/homebrew/bin/python3.12',str(script)]+([str(root)] if mode=='stage' else [mode,str(root)])
  config={'Label':label,'ProgramArguments':args,'RunAtLoad':True,'KeepAlive':{'SuccessfulExit':False} if mode!='stage' else False,'ThrottleInterval':10,'WorkingDirectory':str(root),'StandardOutPath':str(root/(mode+'.log')),'StandardErrorPath':str(root/(mode+'.log')),'EnvironmentVariables':{'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','PYTHONDONTWRITEBYTECODE':'1'}}
  file=root/(mode+'.plist');file.write_bytes(plistlib.dumps(config));r=subprocess.run(['launchctl','bootstrap','gui/'+str(os.getuid()),str(file)],capture_output=True,text=True)
  if r.returncode:
   query('mutation { podStop(input:{podId:"'+pod+'"}) { id } }');raise RuntimeError('service registration failed; ownnewpodstopped before scientific retry')
  if subprocess.run(['launchctl','print','gui/'+str(os.getuid())+'/'+label],capture_output=True).returncode:raise RuntimeError('guardservice notverified')
  write(root/(mode+'_SERVICE.json'),{'label':label,'verified_epoch':time.time(),'original_created_epoch':created})
 print(json.dumps({'status':'ONE_GPU_GATE_GUARDED_STAGING','pod_id':pod,'gpu_type':gpu,'original_created_utc':p['createdAt'],'maximum_seconds':3600,'production_training':False}))

if __name__=='__main__':launch()
