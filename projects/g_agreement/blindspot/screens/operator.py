"""Persistent §79 Mac custody; corrected shared guards; no allocation or normal stop."""
from __future__ import annotations
import argparse,json,os,re,signal,subprocess,time
from pathlib import Path
from . import corpus as C,protocol as P

PID_KEYS=('watchdog_pid','watchdog_caffeinate_pid','hardstop_pid','hardstop_caffeinate_pid')

def state(path):return dict(line.split('=',1) for line in Path(path).read_text().splitlines() if '=' in line)
def argv(pid):
 r=subprocess.run(['ps','-o','args=','-p',str(pid)],capture_output=True,text=True);return r.stdout.strip() if r.returncode==0 else None

def booking_check(b,now=None):
 now=time.time() if now is None else now
 if b.get('section')!=79 or not re.fullmatch('[a-z0-9]+',b['pod_id']) or not b.get('integrator_clearance'):raise ValueError('wrong/uncleared S79 booking')
 P.budget_check(b,now)
 return b

def guard_identity(key,args,pod):
 if not args:return False
 return 'caffeinate' in args if 'caffeinate' in key else ('ws2_watchdog.sh '+pod in args if key=='watchdog_pid' else 'ws2_hardstop.sh '+pod in args)

def live_guards(s,pod,getargs=argv):
 if s.get('pod')!=pod:raise ValueError('wrong guard pod')
 for key in PID_KEYS:
  if not str(s.get(key,'')).isdigit() or not guard_identity(key,getargs(s[key]),pod):raise ValueError('dead/unrelated guard '+key)

def retire(s,pod,append,getargs=argv,send=os.kill):
 # Caller must first obtain its own API EXITED proof. Already exited watchdogs are normal.
 for key in PID_KEYS:
  pid=s.get(key)
  if not str(pid).isdigit():raise ValueError('invalid PID '+key)
  args=getargs(pid)
  if args:
   if not guard_identity(key,args,pod):raise ValueError('PID reused/unrelated '+key)
   send(int(pid),signal.SIGTERM);until=time.time()+10
   while getargs(pid):
    if time.time()>until:raise RuntimeError('guard did not retire '+key)
    time.sleep(.1)
  append('GUARD_GONE',key=key,pid=pid)

def request_command(q,pod,digest,ops,addr):
 if q.get('pod_id')!=pod or q.get('booking_sha256')!=digest:raise ValueError('request pod/booking decoy')
 action=q['action']
 if action=='rearm':
  names=[q['pidfile'],*q['outputs']]
  if not q['outputs'] or any(not x.startswith('/workspace/s79/') or '..' in Path(x).parts or not re.fullmatch(r'[A-Za-z0-9_./-]+',x) for x in names):raise ValueError('rearm path decoy')
  return ['bash',str(ops/'ws2_macguard.sh'),'rearm',pod,*names]
 if action in ('pull','release'):
  command=['bash',str(ops/'ws2_offvolume.sh'),action,pod,addr,'s79','s79']
  if action=='release':command+=['s79-integrator-stop-review','10']
  return command
 raise ValueError('unsupported custody request '+action)

def supervise(booking,ops,addr,guard_dir,pull_root):
 booking,ops,gd=map(lambda x:Path(x).resolve(),[booking,ops,guard_dir]);b=booking_check(json.loads(booking.read_text()));pod=b['pod_id'];digest=C.sha(booking)
 if not re.fullmatch(r'[0-9.]+:[0-9]+',addr):raise ValueError('invalid own SSH address')
 gd.mkdir(parents=True,exist_ok=False);env=dict(os.environ,WS2_MAC_GUARD_DIR=str(gd),WS2_MAC_CACHE=str(Path(pull_root).resolve()),WS2_REPO=str(C.ROOT),WS2_MAIN_CHECKOUT=str(C.ROOT),WS2_KEYS_STAGED='0',WD_HF_DIR='/workspace/s79/hf')
 fixed={p.name:C.sha(p) for p in ops.iterdir() if p.is_file()}
 def unchanged():
  if C.sha(booking)!=digest or any(C.sha(ops/n)!=h for n,h in fixed.items()):raise RuntimeError('immutable custody source changed')
 def append(event,**kw):
  with (gd/'supervisor.jsonl').open('a') as f:f.write(C.canonical({'at':time.time(),'pod_id':pod,'event':event,**kw})+'\n')
 def status():
  proof=json.loads(subprocess.check_output(['bash',str(ops/'status_http.sh'),pod],env=env,text=True,timeout=60));assert proof['http_status']==200 and proof['pod_id']==pod;return proof
 def call(command,limit=300,safety=False):
  with (gd/'commands.log').open('a') as log:
   child=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT);end=time.time()+limit if safety else min(time.time()+limit,b['deadline_epoch'])
   while child.poll() is None:
    unchanged()
    if time.time()>=end:
     child.terminate()
     try:child.wait(timeout=5)
     except subprocess.TimeoutExpired:child.kill();child.wait()
     raise TimeoutError('bounded custody command')
    time.sleep(1)
   if child.returncode:raise RuntimeError('custody command failed '+command[2])
 def close(proof):
  if proof['status']!='EXITED':raise ValueError('retire requires own API EXITED')
  if (gd/'state').exists():retire(state(gd/'state'),pod,append)
  append('CLOSED_EXITED_ALL_OWN_GUARDS_GONE',api=proof);C.save(gd/'CLOSED.json',{'status':'EXITED','api':proof,'all_own_guard_pids_gone':True})
 try:
  unchanged();proof=status()
  if proof['status']!='RUNNING':raise RuntimeError('assigned pod is not RUNNING')
  host,port=addr.split(':');native="python3 -c \"import pathlib; x=[v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\\0') if v.startswith(b'RUNPOD_POD_ID=')]; assert x==['"+pod+"']; print('NATIVE_ID_OK')\""
  reply=subprocess.check_output(['ssh','-i',str(Path.home()/'.ssh/id_ed25519_runpod'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-p',port,'root@'+host,native],text=True,timeout=60)
  if reply.strip()!='NATIVE_ID_OK':raise ValueError('native ID mismatch')
  duration=int(b['deadline_epoch']-time.time()-30)
  if duration<=630:raise ValueError('no safe arm reserve')
  call(['bash',str(ops/'ws2_macguard.sh'),'arm',pod,addr,str(duration),'45','/workspace/s79/job.pid','/workspace/s79/job.s79.log','/workspace/s79/results/g_agreement/s79_run/stage/staging_progress.s79.json','/workspace/s79/results/g_agreement/s79_run/native/progress.s79.json'])
  s=state(gd/'state');live_guards(s,pod)
  if int(s['deadline'])>b['deadline_epoch']:raise ValueError('guard hard cap exceeds booking')
  with (gd/'state').open('a') as f:f.write('pull_tree=s79\npull_suffix=s79\n')
  C.save(gd/'ARMED.json',{'actual_http_proof':proof,'native_id':'NATIVE_ID_OK','supervisor_pid':os.getpid(),'booking':b,'booking_sha256':digest,'guard_state':s,'ops_hashes':fixed});append('ARMED',pids=s);print('ARMED '+C.canonical({'supervisor_pid':os.getpid(),'guard_state':s,'actual_http_proof':proof}),flush=True)
  next_pull=time.time()+120;number=0;released=False
  while True:
   unchanged()
   try:live_guards(state(gd/'state'),pod)
   except ValueError:
    proof=status()
    if proof['status']=='EXITED':close(proof);return
    raise
   if released or time.time()>=b['science_deadline_epoch']:
    proof=status()
    if proof['status']=='EXITED':close(proof);return
    if not released:raise TimeoutError('science cutoff reached; final verified pull safety')
   request=gd/'request.json'
   if request.exists():
    number+=1;claimed=gd/f'request.{number:04d}.json';request.rename(claimed);q=json.loads(claimed.read_text());command=request_command(q,pod,digest,ops,addr)
    try:call(command)
    except (RuntimeError,TimeoutError) as e:
     append('REQUEST_FAILED',request=claimed.name,error=str(e))
     if q['action']=='rearm':raise
    else:
     append('REQUEST_VERIFIED',request=claimed.name)
     if q['action']=='release':released=True
   if time.time()>=next_pull and (gd/'PULL_ENABLED').exists():
    try:call(['bash',str(ops/'ws2_offvolume.sh'),'pull',pod,addr,'s79','s79'],limit=240)
    except (RuntimeError,TimeoutError) as e:append('PULL_RETRY',error=str(e))
    else:append('PULL_VERIFIED')
    next_pull=time.time()+120
   time.sleep(5)
 except BaseException as error:
  append('OPERATOR_FAILURE',error=str(error))
  # Stop-only emergency retries may continue after the cap; science never does.
  # Keep custody live while API verification is unavailable, rather than returning
  # and letting a short tool session clean up the independent guards.
  while True:
   try:
    proof=status()
    if proof['status']=='EXITED':close(proof);return
    script=gd/'ws2_macguard.sh' if (gd/'state').exists() else ops/'ws2_macguard.sh'
    command=['bash',str(script),'_safety',pod,'operator_failure'] if (gd/'state').exists() else ['bash',str(script),'_stop',pod]
    call(command,limit=120,safety=True)
   except BaseException as retry_error:
    append('ALERT',reason='Could not verify EXITED; custody/guards remain',error=str(retry_error));print('ALERT: stop/EXITED verification failed; retaining custody and emergency retries',flush=True)
   time.sleep(5)

def main():
 p=argparse.ArgumentParser()
 for k in ['booking','ops','addr','guard-dir','pull-root']:p.add_argument('--'+k,required=True)
 a=p.parse_args();supervise(a.booking,a.ops,a.addr,a.guard_dir,a.pull_root)
if __name__=='__main__':main()
