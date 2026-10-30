"""Independent one-shot P/gate allocators: caps and exact posted payload bind creation."""
import json,datetime,time,pathlib,subprocess,os,plistlib
from decimal import Decimal
from .custody import query,write,sha
P=pathlib.Path

def launch(root):
 if (root/'STATE.json').exists() or (root/'CREATE_REQUEST.json').exists():raise ValueError('existing allocation/request; reconcile never duplicate')
 pre=json.loads((root/'PREFLIGHT.json').read_text());ad=json.loads((root/'ALLOCATION_ADMISSION.json').read_text());now=time.time()
 if not ad['launch_admitted'] or not ad['posted_shared_commit'] or now-datetime.datetime.fromisoformat(ad['as_of_utc']).timestamp()>600:raise ValueError('fresh posted admission required')
 if pre['phase']!='gate' or ad['phase']!=pre['phase'] or ad['cap_seconds']>1800:raise ValueError('registered separate phase cap')
 for n,h in pre['files'].items():
  if sha(root/n)!=h:raise ValueError('CPU preflight payload changed '+n)
 hardware=ad.get('gpu_type','H200')
 if hardware not in ('H200','B200'):raise ValueError('registered H200/B200 only')
 max_rate=Decimal('5.29') if hardware=='H200' else Decimal('7.99')
 data=query('query { myself { pods { id name desiredStatus costPerHr } } gpuTypes(input:{id:"NVIDIA '+hardware+'"}) { id securePrice } }');pods=data['myself']['pods'];name=ad['pod_name'];rate=Decimal(str(data['gpuTypes'][0]['securePrice']))
 if any(p['name']==name for p in pods):raise ValueError('existing unique name; no duplicate')
 allowed=set(ad.get('evidenced_pod_ids',[]));parallel=set(ad.get('parallel_pod_names',[]))
 if any(p['desiredStatus']=='RUNNING' and p['id'] not in allowed and p['name'] not in parallel for p in pods):raise ValueError('unreconciled new runningallocation; refresh global receipt beforeCREATE')
 if rate>max_rate or sum((Decimal(str(p['costPerHr'])) for p in pods if p['desiredStatus']=='RUNNING'),Decimal(0))+rate>80:raise ValueError('provider quote/hourly headroom')
 with (root/'CREATE_REQUEST.json').open('x') as f:json.dump({'requested_epoch':now,'name':name,'phase':pre['phase'],'posted_shared_commit':ad['posted_shared_commit']},f)
 env=dict(os.environ,WS2_DEPLOY_LOG=str(root/'DEPLOYS.jsonl'))
 try:x=subprocess.run(['bash','/private/tmp/e96-i4-durable/guard_scripts/ws2_offvolume.sh','deploy-vol','NVIDIA '+hardware,'5on6935gne',name],env=env,capture_output=True,text=True,timeout=90)
 except subprocess.TimeoutExpired as exc:
  write(root/'AMBIGUOUS_CREATE.json',{'name':name,'epoch':time.time(),'action':'query unique name before ANYresubmission'})
  x=type('Result',(),{'returncode':124,'stdout':'','stderr':'CREATEtimeout; reconcileuniquename/noresubmit'})()
 (root/'ALLOCATION.log').write_text(x.stdout+x.stderr);pod=x.stdout.strip().splitlines()[-1] if x.returncode==0 and x.stdout.strip() else None
 if not pod or not pod.isalnum():
  matches=[p for p in query('query { myself { pods { id name } } }')['myself']['pods'] if p['name']==name]
  if len(matches)==1:pod=matches[0]['id']
  else:raise RuntimeError('provider refused/ambiguous; existingrequestpreserved, reconcilebeforeanyretry')
 p=query('query { pod(input:{podId:"'+pod+'"}) { id name createdAt gpuCount costPerHr } }')['pod']
 if p['name']!=name or p['gpuCount']!=1:raise ValueError('provider allocation identity')
 created=datetime.datetime.fromisoformat(p['createdAt'].replace('Z','+00:00')).timestamp();s={'experiment':'E106','phase':pre['phase'],'pod_id':pod,'pod_name':name,'created_utc':p['createdAt'],'created_epoch':created,'deadline_epoch':created+ad['cap_seconds'],'rate':p['costPerHr'],'gpu_type':hardware,'status':'GUARDED_STAGING','cap_seconds':ad['cap_seconds']};write(root/'STATE.json',s)
 if Decimal(str(p['costPerHr']))>max_rate:
  query('mutation { podStop(input:{podId:"'+pod+'"}) { id } }');query('mutation { podTerminate(input:{podId:"'+pod+'"}) }');raise RuntimeError('actualpriceexceedsadmission; newownedpodterminatedbeforestage')
 worker=json.loads((root/'ADMISSION_TEMPLATE.json').read_text());worker.update(created_epoch=created,deadline_epoch=s['deadline_epoch']-120,external_guard_armed=True,incremental_backup_armed=True);write(root/'ADMISSION.json',worker)
 for mode in ['hardstop','supervise','stage']:
  label='com.mats.e106.i4.'+ad['slot_label']+'.'+mode;script=root/('stage.py' if mode=='stage' else 'custody.py');args=['/usr/bin/caffeinate','-i','/opt/homebrew/bin/python3.12',str(script)]+([str(root)] if mode=='stage' else [mode,str(root)])
  config={'Label':label,'ProgramArguments':args,'RunAtLoad':True,'KeepAlive':False if mode=='stage' else {'SuccessfulExit':False},'WorkingDirectory':str(root),'StandardOutPath':str(root/(mode+'.log')),'StandardErrorPath':str(root/(mode+'.log')),'EnvironmentVariables':{'PATH':'/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'}};file=root/(mode+'.plist');file.write_bytes(plistlib.dumps(config));result=subprocess.run(['launchctl','bootstrap','gui/'+str(os.getuid()),str(file)],capture_output=True)
  if result.returncode:
   query('mutation { podStop(input:{podId:"'+pod+'"}) { id } }');raise RuntimeError('service failed; own allocation stopped')
  check=subprocess.run(['launchctl','print','gui/'+str(os.getuid())+'/'+label],capture_output=True)
  if check.returncode:raise RuntimeError('service verification failed')
  write(root/(mode+'_SERVICE.json'),{'label':label,'verified':True,'original_created_epoch':created})
 print(json.dumps({'phase':s['phase'],'pod_id':pod,'created_utc':p['createdAt'],'cap_seconds':ad['cap_seconds'],'services':3}))
if __name__=='__main__':
 import sys
 launch(P(sys.argv[1]))
