"""I-5 bounded provider lifecycle. No generation retry or deadline renewal."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,plistlib,re,signal,subprocess,sys,tarfile,time,fcntl
API='/Users/guivff/repl/tools/runpod_api.sh'
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');os.chmod(t,0o600);os.replace(t,p)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for z in iter(lambda:f.read(1048576),b''):h.update(z)
 return h.hexdigest()
def api(q):
 r=subprocess.run([API,q],capture_output=True,text=True,timeout=40);d=json.loads(r.stdout)
 if d.get('errors')or'data'not in d:raise RuntimeError('Provider API error; no credential output')
 return d['data']
def pod(pid):return api('query { pod(input: {podId: '+json.dumps(pid)+'}) { id name desiredStatus createdAt costPerHr runtime { ports { ip isIpPublic privatePort publicPort } } } }')['pod']
def identity(p,state):
 if p is not None and(p['id']!=state['pod_id']or p['createdAt']!=state['createdAt']):raise ValueError('Exact provider identity mismatch')
def epoch(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def stop(state):
 p=pod(state['pod_id']);identity(p,state)
 if p is not None and p['desiredStatus']!='EXITED':api('mutation { podStop(input: {podId: '+json.dumps(state['pod_id'])+'}) { id desiredStatus } }')
def label(run,role):return 'com.activation-readers.i5.'+run.name+'.'+role
def service(run,role,args):
 name=label(run,role);p=run/(role+'.plist');value=dict(Label=name,ProgramArguments=args,RunAtLoad=True,KeepAlive=False,StandardOutPath=str(run/(role+'.stdout')),StandardErrorPath=str(run/(role+'.stderr')),EnvironmentVariables={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin'})
 with p.open('wb')as f:plistlib.dump(value,f)
 os.chmod(p,0o600);subprocess.run(['launchctl','bootstrap','gui/'+str(os.getuid()),str(p)],check=True,capture_output=True)
 return name

def guard(run,role):
 state=read(run/'STATE.json');deadline=state['deadline_epoch']-(30 if role=='hardstop'else 2)
 p=pod(state['pod_id']);identity(p,state);write(run/(role+'.ready.json'),dict(pid=os.getpid(),pod_id=state['pod_id'],createdAt=state['createdAt'],deadline_epoch=deadline,authenticated=True))
 while time.time()<deadline:
  if(run/'CLOSED.json').exists():return
  time.sleep(min(5,max(0,deadline-time.time())))
 while True:
  try:
   stop(state);p=pod(state['pod_id']);identity(p,state)
   if p is None or p['desiredStatus']=='EXITED':write(run/(role+'.done.json'),dict(pod_id=state['pod_id'],verified_epoch=time.time(),status='NULL'if p is None else'EXITED'));return
  except Exception as e:write(run/(role+'.alert.json'),dict(type=type(e).__name__,epoch=time.time()))
  time.sleep(5)

def ssh(state,script,timeout=45):
 host,port=state['addr'].split(':');cmd=['ssh','-i',str(Path.home()/'.ssh/id_ed25519_runpod'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(Path(state['run'])/'known_hosts'),'-o','ConnectTimeout=15','-o','ServerAliveInterval=10','-p',port,'root@'+host,'/usr/bin/python3','-']
 r=subprocess.run(cmd,input=script,capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError('Own-pod SSH command failed')
 return r.stdout

def upload(state,local,remote,timeout):
 host,port=state['addr'].split(':');cmd=['scp','-q','-i',str(Path.home()/'.ssh/id_ed25519_runpod'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(Path(state['run'])/'known_hosts'),'-P',port,str(local),'root@'+host+':'+remote+'.part']
 subprocess.run(cmd,check=True,capture_output=True,timeout=timeout)
 ssh(state,"import pathlib,hashlib,os\np=pathlib.Path("+repr(remote+'.part')+")\nassert hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(sha(local))+"\nos.replace(p,"+repr(remote)+")\n")

def archive(state,final=False):
 run=Path(state['run']);name=('final'if final else'incremental')+'.pax.tar.gz';tmp=run/(name+'.part');host,port=state['addr'].split(':');remote=state['remote']
 cmd=['ssh','-i',str(Path.home()/'.ssh/id_ed25519_runpod'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(run/'known_hosts'),'-p',port,'root@'+host,'tar --format=pax -czf - -C '+remote+' out worker.log assignment.json']
 with tmp.open('wb')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.PIPE,timeout=120)
 if r.returncode:raise RuntimeError('Archive transfer failed')
 os.chmod(tmp,0o600)
 with tarfile.open(tmp)as t:
  members={m.name:m for m in t.getmembers()if m.isfile()}
  seal=json.load(t.extractfile('out/CAPTURE_SEAL.json'))if'out/CAPTURE_SEAL.json'in members else None
  if final:
   if seal is None:raise ValueError('Missing final capture seal; preserve archive, do not terminate')
   for n,h in seal['files'].items():
    if hashlib.sha256(t.extractfile('out/'+n).read()).hexdigest()!=h:raise ValueError('Archived capture member changed')
   if seal['sites']!=[42]or seal['reader_outputs']!=0:raise ValueError('Capture-only site/custody')
 os.replace(tmp,run/name);write(run/(name+'.receipt.json'),dict(path=str(run/name),sha256=sha(run/name),verified_epoch=time.time(),capture_status=seal.get('status')if seal else None))
 return seal

def close(run,state,verified):
 stop(state)
 for _ in range(30):
  p=pod(state['pod_id']);identity(p,state)
  if p is None or p['desiredStatus']=='EXITED':break
  time.sleep(2)
 else:raise RuntimeError('Provider EXITED unverified')
 if verified:
  api('mutation { podTerminate(input: {podId: '+json.dumps(state['pod_id'])+'}) }')
  for _ in range(30):
   if pod(state['pod_id'])is None:break
   time.sleep(2)
  else:raise RuntimeError('Provider termination unverified')
 write(run/'CLOSED.json',dict(pod_id=state['pod_id'],createdAt=state['createdAt'],verified_epoch=time.time(),provider_query_null=verified,archive_verified=verified,charged_seconds_upper=time.time()-state['created_epoch'],gpu_type=state['gpu_type'],rate=state['rate']))
 for role in ['hardstop','backstop']:
  subprocess.run(['launchctl','bootout','gui/'+str(os.getuid())+'/'+label(run,role)],capture_output=True)


def controller(run):
 plan=read(run/'PLAN.json');state=None;verified=False;deploy_lock=(run.parent/'DEPLOY.lock').open('a');fcntl.flock(deploy_lock.fileno(),fcntl.LOCK_EX)
 if(run/'STATE.json').exists():raise RuntimeError('No automatic controller relaunch/deployment retry')
 for n,h in plan['payload_hashes'].items():
  if sha(run/n)!=h:raise ValueError('Frozen payload mutation')
 if sha(plan['retained44_path'])!=plan['retained44_sha256']:raise ValueError('Original Oracle capture changed')
 if time.time()>plan['admission_expires_epoch']or plan['projected_upper_usd']>1500:raise ValueError('Fresh budget admission required')
 pods=api('query { myself { pods { id name desiredStatus createdAt costPerHr } } }')['myself']['pods'];live=[x for x in pods if x['desiredStatus']=='RUNNING']
 if len(live)>=20 or {x['id']for x in live}-set(plan['known_live_ids']):raise ValueError('Refresh global liabilities/ceiling')
 newest=max([epoch(x['createdAt'])for x in pods]+[0])
 if time.time()-newest<60:raise ValueError('Deployment spacing; no allocation')
 try:
  # Existing persistent provider deploy implementation, byte-pinned mirror.
  env=dict(os.environ,WS2_REPO=str(run),WS2_MAIN_CHECKOUT=str(run),WS2_DEPLOY_LOG=str(run/'deploy.jsonl'),WS2_MAC_CACHE=str(run/'stock_pulls'))
  for gpu in plan['gpu_types']:
   write(run/'DEPLOY_REQUEST.json',dict(gpu=gpu,epoch=time.time(),name=plan['pod_name']))
   r=subprocess.run(['bash',str(run/'ops/ws2_offvolume.sh'),'deploy-vol',gpu,plan['volume'],plan['pod_name']],env=env,capture_output=True,text=True,timeout=70)
   candidate=r.stdout.strip().splitlines()[-1]if r.stdout.strip()else''
   if r.returncode==0 and re.fullmatch('[a-z0-9]{6,30}',candidate):break
   # Definitive no-ID provider rejection only; unknown outcomes are not reissued.
   found=[x for x in api('query { myself { pods { id name desiredStatus createdAt costPerHr } } }')['myself']['pods']if x['name']==plan['pod_name']]
   if found:candidate=found[-1]['id'];break
  else:write(run/'NO_ALLOCATION.json',dict(reason='No authorized GPU stock',epoch=time.time()));return
  p=pod(candidate);created=epoch(p['createdAt']);state=dict(run=str(run),pod_id=candidate,createdAt=p['createdAt'],created_epoch=created,deadline_epoch=created+plan['cap_seconds'],gpu_type=gpu.removeprefix('NVIDIA ')if hasattr(gpu,'removeprefix')else gpu.replace('NVIDIA ',''),gpu_id=gpu,rate=p['costPerHr'],remote='/workspace/e97r42');write(run/'STATE.json',state);fcntl.flock(deploy_lock.fileno(),fcntl.LOCK_UN)
  if p['costPerHr']>plan['quoted_rates'][gpu]+1e-6:raise ValueError('Price exceeded fresh quote')
  for role in ['hardstop','backstop']:service(run,role,['/usr/bin/python3',str(run/'controller.py'),'guard','--run',str(run),'--role',role])
  until=time.time()+30
  while not all((run/(r+'.ready.json')).exists()for r in ['hardstop','backstop']):
   if time.time()>until:raise RuntimeError('Independent provider guards not armed')
   time.sleep(1)
  for role in ['hardstop','backstop']:
   ready=read(run/(role+'.ready.json'));os.kill(ready['pid'],0)
   if ready['pod_id']!=candidate or ready['deadline_epoch']>state['deadline_epoch']:raise ValueError('Guard identity/deadline')
  while True:
   p=pod(candidate);identity(p,state);ports=(p.get('runtime')or{}).get('ports')or[];entry=next((x for x in ports if x['privatePort']==22 and x['isIpPublic']),None)
   if entry:state['addr']=entry['ip']+':'+str(entry['publicPort']);write(run/'STATE.json',state);break
   if time.time()>created+240:raise TimeoutError('SSH startup')
   time.sleep(5)
  # Invoke the verified stock Mac guards too; independent launchd guards stay armed.
  remaining=max(1,int(state['deadline_epoch']-30-time.time()));env['WS2_MAC_GUARD_DIR']=str(run/'stock_guards')
  r=subprocess.run(['bash',str(run/'ops/ws2_macguard.sh'),'arm',candidate,state['addr'],str(remaining),'999','/workspace/e97r42/worker.pid','/workspace/e97r42/out'],env=env,capture_output=True,text=True,timeout=45)
  (run/'stock_guard.log').write_text(r.stdout)
  if r.returncode:raise RuntimeError('Verified persistent stock guards failed')
  stock=dict(x.split('=',1)for x in(run/'stock_guards/state').read_text().splitlines()if'='in x)
  for key in ['watchdog_pid','watchdog_caffeinate_pid']:
   try:os.kill(int(stock[key]),signal.SIGTERM)
   except ProcessLookupError:pass
  if int(stock['deadline'])>state['deadline_epoch']:raise ValueError('Stock guard exceeds fixed deadline')
  ssh(state,"from pathlib import Path\nPath('/workspace/e97r42').mkdir(exist_ok=True)\n")
  for n in ['source.tar.gz','inputs.tar.gz','assets.json']:upload(state,run/n,state['remote']+'/'+n,max(1,min(360,int(created+540-time.time()))))
  ass=dict(experiment='E97_CAPTURE42_V2',gpu_count=1,gpu_type=state['gpu_type'],cap_seconds=plan['cap_seconds'],pod_id=candidate,pod_created_epoch=created,absolute_deadline_epoch=state['deadline_epoch'],daily_budget_verified=True,projected_daily_USD=plan['projected_upper_usd'],assets=dict(path=state['remote']+'/assets.json',sha256=plan['payload_hashes']['assets.json']))
  argv=['/weights/venv-kernels/bin/python','/workspace/projects/g_agreement/e97/capture42.py','--inputs',state['remote']+'/inputs','--assets',state['remote']+'/assets.json','--assignment',state['remote']+'/assignment.json','--out',state['remote']+'/out','--source-seal','/workspace/E97_CAPTURE42_SOURCE.json','--source-sha',plan['source_seal_sha256']]
  script="import pathlib,subprocess,json,os\nr=pathlib.Path('/workspace/e97r42')\nsubprocess.run(['tar','xzf',str(r/'source.tar.gz'),'-C','/workspace'],check=True)\nsubprocess.run(['tar','xzf',str(r/'inputs.tar.gz'),'-C',str(r)],check=True)\nassert not any('PRIVATE'in p.name or'DO_NOT_STAGE'in p.name for p in (r/'inputs').rglob('*'))\na="+repr(ass)+"\n(r/'assignment.json').write_text(json.dumps(a))\nassert not(r/'worker.started').exists()\n(r/'worker.started').write_text('once')\nenv=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',RUNPOD_POD_ID="+repr(candidate)+")\nf=(r/'worker.log').open('wb')\np=subprocess.Popen("+repr(argv)+",stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True,cwd='/workspace')\n(r/'worker.pid').write_text(str(p.pid))\nprint('WORKER_STARTED')\n"
  write(run/'ASSIGNMENT.json',ass);write(run/'LAUNCH_REQUESTED.json',dict(epoch=time.time()));reply=ssh(state,script,timeout=40)
  if'WORKER_STARTED'not in reply:raise RuntimeError('Worker start unverified')
  write(run/'WORKER_STARTED.json',dict(epoch=time.time(),pod_id=candidate));last=0
  while True:
   status=json.loads(ssh(state,"import pathlib,os,json\nr=pathlib.Path('/workspace/e97r42');pid=int((r/'worker.pid').read_text())\ntry:os.kill(pid,0);alive=True\nexcept ProcessLookupError:alive=False\nprint(json.dumps(dict(alive=alive,seal=(r/'out/CAPTURE_SEAL.json').exists(),progress=json.loads((r/'out/PROGRESS.json').read_text())if(r/'out/PROGRESS.json').exists()else None)))\n"));write(run/'PROGRESS.json',dict(epoch=time.time(),**status))
   if status['seal']or not status['alive']or time.time()>state['deadline_epoch']-150:break
   if time.time()-last>120 and status['progress']:
    try:archive(state)
    except Exception as e:write(run/'INCREMENTAL_ERROR.json',dict(type=type(e).__name__,epoch=time.time()))
    last=time.time()
   time.sleep(15)
  seal=archive(state,True);verified=True
  if sha(plan['retained44_path'])!=plan['retained44_sha256']:raise ValueError('Retained Oracle capture changed')
  reply=ssh(state,"import pathlib,shutil,json\nr=pathlib.Path('/workspace/e97r42');shutil.rmtree(r/'inputs')\nfor n in ['source.tar.gz','inputs.tar.gz']:(r/n).unlink(missing_ok=True)\nprint(json.dumps(dict(inputs_absent=not(r/'inputs').exists())))\n")
  write(run/'CLEANUP.json',json.loads(reply));write(run/'RESULT.json',dict(status=seal['status'],pod_id=candidate,archive=str(run/'final.pax.tar.gz'),archive_sha256=sha(run/'final.pax.tar.gz'),gpu_type=state['gpu_type'],original44_unchanged=True))
 except BaseException as e:
  write(run/'FAILURE.json',dict(type=type(e).__name__,epoch=time.time(),message=str(e)[:160]))
  if state is None and(run/'DEPLOY_REQUEST.json').exists():
   for _ in range(24):
    try:
     found=[x for x in api('query { myself { pods { id name desiredStatus createdAt costPerHr } } }')['myself']['pods']if x['name']==plan['pod_name']]
     if found:
      p=found[-1];state=dict(run=str(run),pod_id=p['id'],createdAt=p['createdAt'],created_epoch=epoch(p['createdAt']),deadline_epoch=epoch(p['createdAt'])+plan['cap_seconds'],gpu_type=gpu.replace('NVIDIA ',''),gpu_id=gpu,rate=p['costPerHr'],remote='/workspace/e97r42');write(run/'STATE.json',state);break
    except Exception:pass
    time.sleep(5)
  if state:
   try:archive(state,True);verified=True
   except Exception:pass
 finally:
  if state:
   if verified and not(run/'CLEANUP.json').exists():
    try:
     reply=ssh(state,"import pathlib,shutil,json\nr=pathlib.Path('/workspace/e97r42');shutil.rmtree(r/'inputs',ignore_errors=True)\nfor n in ['source.tar.gz','inputs.tar.gz']:(r/n).unlink(missing_ok=True)\nprint(json.dumps(dict(inputs_absent=not(r/'inputs').exists())))\n");write(run/'CLEANUP.json',json.loads(reply))
    except Exception:pass
   clean=(run/'CLEANUP.json').exists()and read(run/'CLEANUP.json').get('inputs_absent')is True
   while True:
    try:close(run,state,verified and clean);break
    except Exception as e:write(run/'CLOSE_ALERT.json',dict(type=type(e).__name__,epoch=time.time()));time.sleep(5)
   stock_path=run/'stock_guards/state'
   if stock_path.exists():
    stock=dict(x.split('=',1)for x in stock_path.read_text().splitlines()if'='in x)
    for key in ['hardstop_pid','hardstop_caffeinate_pid','watchdog_pid','watchdog_caffeinate_pid']:
     try:
      pid=int(stock[key]);args=subprocess.check_output(['ps','-o','args=','-p',str(pid)],text=True)
      if str(run/'stock_guards')in args:os.kill(pid,signal.SIGTERM)
     except(Exception,):pass

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['guard','run']);p.add_argument('--run',type=Path,required=True);p.add_argument('--role',choices=['hardstop','backstop']);a=p.parse_args()
 if a.mode=='guard':guard(a.run,a.role)
 else:controller(a.run)
