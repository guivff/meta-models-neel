"""I-2 E110 exact-public filter one-shot provider admission; no import side effects."""
import os,json,time,subprocess,hashlib,math,re,sys
from pathlib import Path
from datetime import datetime
from refresh_budget import refresh
HOME=Path(__file__).resolve().parent
API=Path('/Users/guivff/repl/tools/runpod_api.sh')
MAIN=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/.claude/worktrees/phase-r-integration-8abda6')
OPS=MAIN/'results/g_agreement/r/pod_tools/ws2_offvolume.sh'
LOCK=HOME/'deploy_lock.sh'
STATE=HOME/'ALLOCATION.private.json'
QUERY='query { myself { networkVolumes { id size dataCenterId } pods { id name desiredStatus createdAt costPerHr } } gpuTypes { id lowestPrice(input:{gpuCount:1}) { uninterruptablePrice } } dataCenters { id gpuAvailability(input:{gpuCount:1,secureCloud:true}) { gpuTypeId available } } }'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(x):
 p=STATE.with_suffix('.new');p.write_text(json.dumps(x,indent=2)+'\n');p.chmod(0o600);p.replace(STATE)
def run(args,timeout=60):
 p=subprocess.run([str(v) for v in args],cwd=MAIN,capture_output=True,timeout=timeout,start_new_session=True)
 with (HOME/'COMMANDS.private.jsonl').open('a') as f:
  f.write(json.dumps(dict(at=time.time(),code=p.returncode,stdout=p.stdout.decode(errors='replace'),stderr=p.stderr.decode(errors='replace')))+'\n');os.chmod(f.name,0o600)
 assert p.returncode==0,'COMMAND_FAILED';return p.stdout.decode()
def api(q):
 x=json.loads(run(['bash',API,q],45));assert not x.get('errors'),'PROVIDER_ERROR';return x['data']
def check(proof,meta,now):
 assert meta['experiment']=='E110_FILTER_AMEND1' and meta['prior_probe_gpu_seconds']==0 and meta['cap_seconds']==2616
 assert meta['fresh_extract_cpu_import_pass'] and meta['synthetic_tests_pass']==8
 assert 0<=now-proof['checked_epoch']<120 and proof['projection_posted']
 assert proof['GPU_upper_with_candidate_usd']<2500 and proof['pool_upper_with_candidate_usd']<=900
 assert proof['candidate_GPU_upper_usd']==meta['gpu_forecast_upper_usd']==5.85
 assert sha(Path(proof['private_admission_path']))==proof['private_admission_sha256']
 assert __import__('datetime').datetime.now(__import__('datetime').timezone.utc)<__import__('datetime').datetime.fromisoformat('2026-10-29T23:00:00+00:00')
 for name,key in [('source.tar.gz','source_archive_sha256'),('PUBLIC_FILTER_INPUTS.tar.gz','input_archive_sha256')]:assert sha(HOME/name)==meta[key]
 assert not(HOME/'ENGINE_ONCE_INTENT.json').exists()

def allocate():
 os.umask(0o077);meta=json.loads((HOME/'PREPARATION.json').read_text());proof=refresh(HOME);check(proof,meta,time.time())
 with (HOME/'CREATE_ONCE_INTENT.json').open('x') as f:json.dump(dict(run_id=meta['run_id'],at=time.time(),source_sha=sha(__file__)),f)
 state=dict(run_id=meta['run_id'],status='PRECREATE',allocator_pid=os.getpid(),allocator_sha=sha(__file__),claim_once=True)
 save(state);locked=False
 try:
  locked=True;run(['bash',LOCK,'acquire',meta['run_id'],meta['run_id']],60)
  d=api(QUERY);a=d['myself'];assert not any(p['name']==meta['run_id'] for p in a['pods']),'PRIOR_POD'
  assert sum(p['desiredStatus']=='RUNNING' for p in a['pods'])<19,'RUNNING_POD_CEILING'
  wait_started=time.time()
  while True:
   newest=max((datetime.fromisoformat(p['createdAt'].replace('Z','+00:00')).timestamp()for p in a['pods']if p.get('createdAt')),default=0)
   delay=max(0,newest+180-time.time())
   if delay<=0:break
   assert time.time()-wait_started<840,'DEPLOY_SPACING_WAIT_LIMIT'
   state.update(status='WAITING_SPACING_BEFORE_CREATE',wait_started=wait_started);save(state)
   run(['bash',LOCK,'release',meta['run_id']]);locked=False
   time.sleep(min(15,delay+1))
   proof=refresh(HOME);check(proof,meta,time.time());locked=True;run(['bash',LOCK,'acquire',meta['run_id'],meta['run_id']],60)
   d=api(QUERY);a=d['myself'];assert not any(p['name']==meta['run_id']for p in a['pods']),'PRIOR_POD'
   assert sum(p['desiredStatus']=='RUNNING'for p in a['pods'])<19,'RUNNING_POD_CEILING'

  v=next(v for v in a['networkVolumes'] if v['id']=='5on6935gne');assert v['size']==150
  assert any(g['gpuTypeId']=='NVIDIA H200' and g['available'] for dc in d['dataCenters'] if dc['id']==v['dataCenterId'] for g in dc['gpuAvailability']),'NO_STOCK'
  quote=next(g for g in d['gpuTypes'] if g['id']=='NVIDIA H200')['lowestPrice']['uninterruptablePrice'];assert 0<float(quote)<=5.29
  assert sum(float(p.get('costPerHr') or 0) for p in a['pods'] if p['desiredStatus']=='RUNNING')+float(quote)<=80,'KNOWN_HOURLY_LIMIT_FULL_BEFORE_CREATE'
  proof=refresh(HOME);check(proof,meta,time.time());state.update(status='CREATE_SENT_ONCE_OUTCOME_UNCERTAIN',request_epoch=time.time());save(state)
  raw=run(['bash',OPS,'deploy-vol','NVIDIA H200',v['id'],meta['run_id']],90);ident=raw.strip().splitlines()[-1];assert re.fullmatch('[a-z0-9]{6,30}',ident),'UNKNOWN_CREATE_RESPONSE'
  state.update(pod_id=ident,status='CREATED');save(state)
  pod=api('query { pod(input:{podId:'+json.dumps(ident)+'}) { id name desiredStatus costPerHr createdAt gpuCount containerDiskInGb volumeInGb } }')['pod']
  state['provider_creation']=pod;save(state)
  assert pod['name']==meta['run_id'] and pod['gpuCount']==1 and pod['desiredStatus']=='RUNNING' and 0<float(pod['costPerHr'])<=5.29
  created=datetime.fromisoformat(pod['createdAt'].replace('Z','+00:00')).timestamp();state.update(created_epoch=created,hard_deadline_epoch=created+meta['cap_seconds']);save(state)
  run(['bash',LOCK,'release',meta['run_id']]);locked=False
  address=run(['bash',OPS,'addr',ident],270).strip();assert re.fullmatch(r'[0-9.]+:[0-9]+',address)
  state['address']=address;save(state)
  remain=math.floor(state['hard_deadline_epoch']-time.time());assert remain>60
  run(['bash',OPS,'guards',ident,address,max(1,remain-30),45],150)
  run(['bash',OPS,'hold',ident,meta['run_id'],30],30)
  state.update(status='ARMED_WAITING_INDEPENDENT_PARENT_EXIT_PROOF',finished_epoch=time.time());save(state)
  print('E110 exact-public filter allocation and original-deadline guard installation complete; private identity saved')
 except BaseException as e:
  state.update(failure=type(e).__name__,status='FAILED_RECONCILE_DO_NOT_REPLAY');save(state)
  if state.get('pod_id'):
   try:api('mutation { podStop(input:{podId:'+json.dumps(state['pod_id'])+'}) { id desiredStatus } }');state['stop_requested_epoch']=time.time();save(state)
   except:pass
  raise
 finally:
  if locked:run(['bash',LOCK,'release',meta['run_id']])
if __name__=='__main__':
 assert sys.argv[1:]==['--allocate-once'],'EXPLICIT_ACTION_REQUIRED';allocate()
