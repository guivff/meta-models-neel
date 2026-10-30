"""One fresh ≤1440s H200; independent guards, public-only staging, verified pull."""
import datetime,hashlib,json,os,shlex,signal,subprocess,sys,time
from pathlib import Path
D=Path(os.environ['E113_OPERATOR_DIR']).resolve()
REPO=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmechc')
OPS=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops')
TOOLS=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/.claude/worktrees/phase-r-integration-8abda6/results/g_agreement/r/pod_tools')
API=Path.home()/'repl/tools/runpod_api.sh'
SSH=['ssh','-o','StrictHostKeyChecking=no','-o','ConnectTimeout=20','-o','BatchMode=yes','-o','LogLevel=ERROR','-i',str(Path.home()/'.ssh/id_ed25519_runpod')]
IMAGE='runpod/pytorch@sha256:0a360022e8de4375af99430f84e8b38951acc397252163a37ceac7204d01be35'
SOURCE=Path(os.environ['E113_SOURCE_DIR']).resolve()
INPUT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e113-inputs-v1')
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def log(s):
 with (D/'OPERATOR.log').open('a') as f:f.write(datetime.datetime.now(datetime.timezone.utc).isoformat()+' '+s+'\n')
 print(s,flush=True)
def run(cmd,**kw):return subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=kw.pop('timeout',120),**kw).stdout.strip()
def api(q):
 x=json.loads(run(['bash',str(API),q]));assert not x.get('errors'),str(x.get('errors'))[:160];return x['data']
def remote(cmd,timeout=90):
 x=json.loads((D/'private_connection.json').read_text());return run(SSH+['-p',str(x['port']),'root@'+x['host'],cmd],timeout=timeout)
def guard(pod,end):
 idle=None
 while True:
  try:
   p=api('query { pod(input:{podId:"%s"}) { id desiredStatus } }'%pod)['pod']
   if not p or p['desiredStatus']!='RUNNING':return
   if time.time()>=end:
    api('mutation { podStop(input:{podId:"%s"}) { id desiredStatus } }'%pod);return
   if len(sys.argv)>4 and sys.argv[4]=='idle' and (D/'private_connection.json').exists():
    util=int(remote('nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits').splitlines()[0]);idle=(idle or time.time()) if util==0 else None
    if idle and time.time()-idle>900:
     api('mutation { podStop(input:{podId:"%s"}) { id desiredStatus } }'%pod);return
  except Exception:pass
  time.sleep(min(20,max(1,end-time.time())))
def main():
 prior=float(os.environ.get('E113_PRIOR_SECONDS','0'));cap=int(1440-prior);assert cap>0
 if (D/'POD.json').exists():raise RuntimeError('pod already allocated; adopt monitoring, never recreate')
 src=json.loads((SOURCE/'PACKAGE.json').read_text());binding=json.loads((REPO/'results/g_agreement/understand/e113/INPUT_BINDING.json').read_text())
 assert sha(SOURCE/'source.tar.gz')==src['archive_sha256'] and sha(INPUT/'inputs.tar.gz')==binding['archive_sha256']
 gates=run(['python3',str(OPS/'gate.py'),str(cap)]);assert 'TRACKQ_GATE OK' in gates
 data=api('query { gpuTypes { id securePrice } myself { pods { id desiredStatus costPerHr } } }')
 quote=next(g for g in data['gpuTypes'] if g['id']=='NVIDIA H200')['securePrice'];assert 0<quote<=8
 active=[p for p in data['myself']['pods'] if p['desiredStatus']=='RUNNING'];assert sum(p['costPerHr'] or 0 for p in active)+quote<=80
 book={}
 ledger=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/.claude/worktrees/phase-r-integration-8abda6/results/g_agreement/compute.jsonl')
 for line in ledger.read_text().splitlines():
  try:x=json.loads(line)
  except Exception:continue
  if str(x.get('timestamp','')).startswith(('2026-10-27','2026-10-28','2026-10-29')) and not x.get('correction_of'):
   value=x.get('usd',0);value=value if isinstance(value,(int,float)) else 0;key=x.get('pod_id') or x.get('experiment','unknown');book[key]=max(book.get(key,0),value)
 global_upper=sum(book.values())+24*sum(p['costPerHr'] or 0 for p in active)+quote*.4
 assert global_upper<2500
 save('BUDGET.json',dict(trackQ_gate=gates,current_H200_quote=quote,new_max_USD=quote*.4,global_conservative_upper=global_upper,global_cap=2500,active_hourly=sum(p['costPerHr'] or 0 for p in active),hourly_cap=80))
 log(gates);log('Quote/gates PASS; max new GPU exposure USD'+str(round(quote*.4,3)))
 env=dict(os.environ,WS2_IMAGE=IMAGE,WS2_DEPLOY_LOG=str(D/'DEPLOYS.jsonl'))
 pod=run(['bash',str(TOOLS/'ws2_offvolume.sh'),'deploy-vol','NVIDIA H200','5on6935gne','mats-e113-c'],env=env)
 assert pod.isalnum()
 p=api('query { pod(input:{podId:"%s"}) { id createdAt costPerHr desiredStatus imageName } }'%pod)['pod']
 start=datetime.datetime.fromisoformat(p['createdAt'].replace('Z','+00:00')).timestamp();end=start+cap
 assert p['costPerHr']<=8 and 'sha256:0a360022' in p['imageName']
 save('POD.json',dict(p,cap_seconds=cap,prior_seconds=prior,absolute_deadline_epoch=end,source_commit=run(['git','rev-parse','HEAD'],cwd=REPO),image_pin=IMAGE))
 own=OPS/'run_E113_C_preload2';own.mkdir(exist_ok=False);(own/'pod.id').write_text(f'{pod} {start} {p["createdAt"]} {end}\n')
 guards=[]
 for name,when,mode in [('hardstop',end-15,''),('backstop',end,''),('idle_guard',end,'idle')]:
  f=(D/(name+'.log')).open('w');argv=['caffeinate','-i',sys.executable,__file__,'guard',pod,str(when)]
  if mode:argv.append(mode)
  guards.append(subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=f,stderr=f,start_new_session=True))
 save('GUARDS.json',dict(pod_id=pod,pids=[g.pid for g in guards],hardstop=end-15,backstop=end));log('Created '+pod+'; independent guards armed')
 status='FAILED';verified=False
 try:
  for _ in range(60):
   ports=(api('query { pod(input:{podId:"%s"}) { id runtime { ports { ip isIpPublic privatePort publicPort } } } }'%pod)['pod'].get('runtime') or {}).get('ports') or []
   port=next((x for x in ports if x['privatePort']==22 and x['isIpPublic']),None)
   if port:save('private_connection.json',dict(host=port['ip'],port=port['publicPort']));break
   time.sleep(3)
  assert (D/'private_connection.json').exists(),'no SSH address'
  actual=remote("python3 -c "+shlex.quote("from pathlib import Path; d=dict(x.split(bytes([61]),1) for x in Path('/proc/1/environ').read_bytes().split(bytes([0])) if bytes([61]) in x); print(d.get(b'RUNPOD_POD_ID',b'').decode())"))
  assert actual==pod and all(g.poll() is None for g in guards)
  remote('mkdir -p /workspace/e113/hf_home')
  conn=json.loads((D/'private_connection.json').read_text());scp=['scp','-q','-o','StrictHostKeyChecking=no','-o','BatchMode=yes','-i',str(Path.home()/'.ssh/id_ed25519_runpod'),'-P',str(conn['port'])]
  assets=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/r_ops/xfer_E101_format_plan_dev/assets.json');(D/'ASSETS.json').write_bytes(assets.read_bytes())
  staged=[(SOURCE/'source.tar.gz','source.tar.gz'),(INPUT/'inputs.tar.gz','inputs.tar.gz'),(D/'ASSETS.json','assets.json')]
  for local,name in staged:run(scp+[str(local),'root@'+conn['host']+':/workspace/e113/'+name],timeout=120)
  checks='\n'.join(sha(path)+'  '+name for path,name in staged)+'\n'
  remote('cd /workspace/e113 && printf %s '+shlex.quote(checks)+' | sha256sum -c --quiet && tar xzf source.tar.gz && tar xzf inputs.tar.gz')
  code='import json,torch,transformers,peft,numpy,safetensors; print(json.dumps(dict(torch=torch.__version__,cuda=torch.version.cuda,transformers=transformers.__version__,peft=peft.__version__,numpy=numpy.__version__,safetensors=safetensors.__version__,gpu=torch.cuda.get_device_name(0))))'
  stack=json.loads(remote('/weights/venv-kernels/bin/python -c '+shlex.quote(code)));save('STACK.json',stack)
  ass=dict(experiment='E113',pod_id=pod,pod_created_epoch=start,cap_seconds=cap,prior_seconds=prior,absolute_deadline_epoch=end,
     input_sha256=binding['input_sha256'],source_sha256=src['source_sha256'],assets_sha256=sha(D/'ASSETS.json'),
     gpu_type='H200',gpu_count=1,hardware_authority='cb76843cc777c90e3fab8056f2f0abab68731e3d',
     analysis_unit_gpu_types={r:'H200' for r in binding.get('rows',[]) or ['nesting_depth','indent_level','page_range_digit','fact_recall','format_plan','language_plan']},
     daily_budget_verified=True,image_digest=IMAGE.split('@')[1],stack_sha256=sha(D/'STACK.json'))
  save('ASSIGNMENT.json',ass);run(scp+[str(D/'ASSIGNMENT.json'),'root@'+conn['host']+':/workspace/e113/assignment.json'])
  argv=['/weights/venv-kernels/bin/python','-m','projects.g_agreement.e113.runner','--inputs','inputs','--input-sha',binding['input_sha256'],'--assets','assets.json','--assignment','assignment.json','--source-seal',src['source_seal'],'--source-sha',src['source_sha256'],'--out','out']
  command='cd /workspace/e113 && RUNPOD_POD_ID='+pod+' PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/workspace/e113/hf_home nohup '+shlex.join(argv)+' > worker.log 2>&1 < /dev/null & echo started'
  try:remote(command)
  except subprocess.TimeoutExpired:log('Launch-confirmation timeout; adopt monitor, no worker relaunch')
  log('Native Oracle internal capture dispatched; ≤1440s original custody')
  pull=D/'pull';pull.mkdir(exist_ok=True);rsync=['rsync','-az','--partial','-e',shlex.join(SSH+['-p',str(conn['port'])]),'root@'+conn['host']+':/workspace/e113/out/',str(pull)+'/']
  while time.time()<end-165:
   try:
    exists=remote('test -f /workspace/e113/out/OUTPUT_SEAL.json && echo SEALED || true',timeout=30)
    subprocess.run(rsync,capture_output=True,timeout=65)
    if (pull/'PROGRESS.json').exists():
     progress=json.loads((pull/'PROGRESS.json').read_text());log('Captured '+str(progress['completed_items'])+'/1008; remaining forecast '+str(round(progress['remaining_seconds'],1))+'s')
    else:log('Native model setup in progress; custody remaining '+str(round(end-time.time()))+'s')
    if exists=='SEALED':break
   except Exception as e:log('Monitor transient '+type(e).__name__)
   time.sleep(20)
  run(rsync,timeout=max(30,min(120,end-time.time()-20)))
  sums=remote('cd /workspace/e113/out && find . -type f -exec sha256sum {} +',timeout=60);(D/'PULL_SUMS').write_text(sums+'\n')
  for line in sums.splitlines():
   digest,name=line.split(None,1);assert sha(pull/name.removeprefix('./'))==digest,name
  verified=True
  if (pull/'OUTPUT_SEAL.json').exists():status=json.loads((pull/'OUTPUT_SEAL.json').read_text())['status']
  (D/'worker.log').write_text(remote('cat /workspace/e113/worker.log',timeout=30))
  save('PULL_RECEIPT.json',dict(pod_id=pod,verified=True,status=status,files=len(sums.splitlines())))
  remote('rm -rf /workspace/e113/inputs /workspace/e113/inputs.tar.gz')
  log('Final capture pull verified; status '+status)
 except BaseException as e:
  save('OPERATOR_FAILURE.json',dict(type=type(e).__name__,message=str(e)[:500]));log('Operator failure '+type(e).__name__+'; guard/cap preserved')
  raise
 finally:
  stopped=api('mutation { podStop(input:{podId:"%s"}) { id desiredStatus } }'%pod)['podStop']
  for _ in range(12):
   actual=api('query { pod(input:{podId:"%s"}) { id desiredStatus } }'%pod)['pod']
   if not actual or actual['desiredStatus']=='EXITED':break
   time.sleep(2)
  elapsed=time.time()-start;save('CLOSED.json',dict(pod_id=pod,status=(actual or {}).get('desiredStatus','GONE'),seconds=elapsed,gpu_hours=elapsed/3600,usd=elapsed/3600*p['costPerHr'],rate=p['costPerHr'],verified_pull=verified,worker_status=status))
  (own/'closed').write_text('closed')
  for g in guards:
   try:os.killpg(g.pid,signal.SIGTERM)
   except ProcessLookupError:pass
  log('Exact pod stopped; custody '+str(round(elapsed,1))+'s; '+status)
 if not verified or status!='COMPLETE':raise RuntimeError('E113 incomplete; preserve sealed partial custody, no automatic retry')
if __name__=='__main__':
 if sys.argv[1:2]==['guard']:guard(sys.argv[2],float(sys.argv[3]))
 else:main()
