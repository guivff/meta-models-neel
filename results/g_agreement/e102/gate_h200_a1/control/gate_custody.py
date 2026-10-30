"""Laptop-only E102 gate custody: no idle stop, no training/retry launcher.

Uses only stdlib. The separately frozen worker generates all GPU evidence. This
module verifies bytes/ordering after pull; it never trains, judges or scores S.
"""
import argparse,datetime,hashlib,json,math,pathlib,shlex,shutil,subprocess,tarfile,tempfile,time
P=pathlib.Path
REMOTE='/workspace/e102-gate'
API=P.home()/'repl/tools/runpod_api.sh'
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def write(p,d):
 p=P(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(p)
def query(q):
 d=json.loads(subprocess.check_output(['bash',str(API),q],text=True,timeout=30))
 if d.get('errors'):raise RuntimeError('provider API error')
 return d['data']
def owned(s):
 p=query('query { pod(input:{podId:"'+s['pod_id']+'"}) { id name desiredStatus createdAt costPerHr gpuCount runtime { ports { ip isIpPublic privatePort publicPort } } } }')['pod']
 if p is not None and (p['id']!=s['pod_id'] or p['name']!=s['pod_name'] or p['createdAt']!=s['created_utc']):raise ValueError('foreign pod identity')
 return p
def ssh(s,cmd,**kw):
 a=s['ssh'];return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2','-i',str(P.home()/'.ssh/id_ed25519_runpod'),'-p',str(a['publicPort']),'root@'+a['ip'],cmd],**kw)
def unpack(archive,dest):
 with tarfile.open(archive) as t:
  for m in t.getmembers():
   if m.name.startswith('/') or '..' in P(m.name).parts or not(m.isfile() or m.isdir()):raise ValueError('unsafe archive')
  t.extractall(dest,filter='data')
def backup(root,s,full=False):
 folder=root/'backups';folder.mkdir(exist_ok=True);archive=folder/(str(time.time_ns())+('.full' if full else '')+'.tar.gz')
 code="import pathlib,tarfile,sys;r=pathlib.Path('/workspace/e102-gate');t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',format=tarfile.PAX_FORMAT);files="
 code+=("[p for p in r.rglob('*') if p.is_file() and (p.is_relative_to(r/'out') or p.relative_to(r).as_posix() in ['job.log','stage.log','ADMISSION.json','ASSETS.json','SOURCE_SEAL.json','WORKER_EXIT.json','STAGE_ERROR.json'])]" if full else "[p for p in (r/'out').rglob('*') if p.is_file() and p.suffix=='.json']")
 code+=";[t.add(p,arcname=str(p.relative_to(r)),recursive=False) for p in sorted(files)];t.close()"
 with archive.with_suffix('.part').open('wb') as f:
  result=ssh(s,'python3 -c '+shlex.quote(code),stdout=f,stderr=subprocess.PIPE,timeout=90)
 if result.returncode:raise RuntimeError('backup transport failure; no normal stop')
 archive.with_suffix('.part').replace(archive);work=P(tempfile.mkdtemp(prefix='backup-check-',dir=root))
 try:
  unpack(archive,work);files={str(p.relative_to(work)):sha(p) for p in work.rglob('*') if p.is_file()}
  # Progress JSON may evolve; each snapshot and its receipt are immutable.
  write(archive.with_suffix('.receipt.json'),{'archive_sha256':sha(archive),'files':files,'scope':'full' if full else 'incremental progress','unscored':True})
 finally:shutil.rmtree(work)
 return archive

def divergence(expected,actual):
 a=expected.encode('utf-8');b=actual.encode('utf-8')
 return next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)) if len(a)!=len(b) else None)
def validate(root,expected,gpu_type):
 out=root/'out';seal=json.loads((out/'OUTPUT_SEAL.json').read_text())
 for n,h in seal['files'].items():
  p=out/n
  if not p.resolve().is_relative_to(out.resolve()) or sha(p)!=h:raise ValueError('gate output hash')
 first=min((p for p in out.rglob('*') if p.is_file() and p.name!='OUTPUT_SEAL.json'),key=lambda p:p.stat().st_mtime_ns)
 result={'status':'GATE_DID_NOT_PASS','first_output_utc':datetime.datetime.fromtimestamp(first.stat().st_mtime,datetime.timezone.utc).isoformat(),'first_output_source':str(first.relative_to(root))+' PAX mtime','gpu_type':gpu_type,'training_admitted':False,'production_checkpoint':'original pinned adapter only; disposable gate adapter never used'}
 parity=json.loads((out/'PARITY.json').read_text()) if (out/'PARITY.json').exists() else []
 want={x['id']:x['expected_text'] for x in expected};seen=set();checks=[]
 for x in parity:
  if x['id'] not in want or x['id'] in seen:raise ValueError('parity ID mismatch')
  seen.add(x['id']);text=want[x['id']]
  if x['expected_sha256']!=hashlib.sha256(text.encode()).hexdigest():raise ValueError('sealed expected text binding')
  d=divergence(text,x['actual']);checks.append({'id':x['id'],'byte_equal':d is None,'first_divergence_utf8_byte':d})
 result['sealed_greedy_comparison']=checks
 if (out/'FAILURE.json').exists():
  result['failure']=json.loads((out/'FAILURE.json').read_text());return result
 report=json.loads((out/'REPORT.json').read_text());loss=json.loads((out/'LOSS.json').read_text());parameters=json.loads((out/'PARAMETERS.json').read_text())
 if len(checks)!=3 or not all(x['byte_equal'] for x in checks):raise ValueError('three byte-exact sealed readouts required')
 if not isinstance(report['base_before_sha256'],str) or len(report['base_before_sha256'])!=64 or any(x not in '0123456789abcdef' for x in report['base_before_sha256']):raise ValueError('base hash format')
 if gpu_type not in parameters.get('gpu',''):raise ValueError('actual GPU type differs from admitted gate')
 if report['status']!='PASS' or report['steps']!=10 or report['base_before_sha256']!=report['base_after_sha256'] or report['adapter_tensors_changed']<=0:raise ValueError('frozen-base/ten-step update proof')
 if parameters['base_requires_grad'] is not False or not parameters['trainable_names'] or any('.lora_A.' not in n and '.lora_B.' not in n for n in parameters['trainable_names']):raise ValueError('only reader LoRA may train')
 if [x['step'] for x in loss]!=list(range(1,11)) or any(not math.isfinite(x['loss']) for x in loss):raise ValueError('ten finite steps required')
 parity_done=(out/'PARITY.json').stat().st_mtime
 if datetime.datetime.fromisoformat(loss[0]['utc']).timestamp()<parity_done:raise ValueError('training before parity completed')
 result.update(status='PASS',steps=10,greedy_reproductions=3,base_frozen=True,adapter='olens_s3d_rl600',adapter_tensors_changed=report['adapter_tensors_changed'],base_parameter_sha256=report['base_after_sha256'],parity_completed_utc=datetime.datetime.fromtimestamp(parity_done,datetime.timezone.utc).isoformat(),first_optimizer_step_utc=loss[0]['utc'],load_and_finite_output_check='three exact sealed generated readouts; ten finite losses and frozen-base/update checks')
 return result

def close(root,s,verified,reason):
 p=owned(s)
 if p is not None and p['desiredStatus']!='EXITED':query('mutation { podStop(input:{podId:"'+s['pod_id']+'"}) { id desiredStatus } }')
 limit=time.time()+90
 while p is not None and p['desiredStatus']!='EXITED':
  if time.time()>limit:raise RuntimeError('stop confirmation timeout')
  time.sleep(3);p=owned(s)
 end=time.time();s.update(status='CLOSED_EXITED',close_reason=reason,archive_verified=verified,first_exit_observed_epoch=end,gpu_hours_upper=(end-s['created_epoch'])/3600,gpu_usd_rate_based_upper=(end-s['created_epoch'])/3600*s['rate']);write(root/'STATE.json',s)
 if verified and p is not None:
  query('mutation { podTerminate(input:{podId:"'+s['pod_id']+'"}) }')
  if owned(s) is not None:raise RuntimeError('termination not confirmed')
  s['status']='TERMINATED';write(root/'STATE.json',s)

def supervise(root):
 s=json.loads((root/'STATE.json').read_text())
 if s.get('status') in ('TERMINATED','CLOSED_EXITED'):return
 expected=json.loads((root/'EXPECTED_PARITY.json').read_text());last=0
 while True:
  p=owned(s)
  if p is None or p['desiredStatus']=='EXITED':raise RuntimeError('unexpected stopped gate; preserve evidence, no retry')
  if not s.get('ssh') and p.get('runtime'):
   s['ssh']=next(x for x in p['runtime']['ports'] if x['privatePort']==22 and x['isIpPublic']);write(root/'STATE.json',s)
  if not s.get('ssh'):time.sleep(5);continue
  try:
   r=ssh(s,'test -f '+REMOTE+'/out/OUTPUT_SEAL.json && echo TERMINAL; test -f '+REMOTE+'/WORKER_EXIT.json && echo EXITED; test -f '+REMOTE+'/STAGE_ERROR.json && echo EXITED; true',capture_output=True,text=True,timeout=15)
   if r.returncode:raise RuntimeError('SSH unavailable')
   if ('EXITED' in r.stdout or (root/'STAGE_ERROR.json').exists()) and 'TERMINAL' not in r.stdout:
    archive=backup(root,s,True);write(root/'GATE_VERIFIED.json',{'status':'GATE_DID_NOT_PASS','first_output_utc':'unknown','first_output_source':'worker/stage exit before readout seal; diagnostics archived','archive_path':str(archive),'archive_sha256':sha(archive),'pod_id':s['pod_id'],'gpu_type':s['gpu_type'],'failure':'explicitworker/stageexit without completion seal; no production authorized'});close(root,s,True,'verified load/stage failure diagnostics; no production');return
   if 'TERMINAL' in r.stdout:
    archive=backup(root,s,True);work=P(tempfile.mkdtemp(prefix='gate-verify-',dir=root))
    try:unpack(archive,work);receipt=validate(work,expected,s['gpu_type'])
    finally:shutil.rmtree(work)
    receipt.update(archive_path=str(archive),archive_sha256=sha(archive),pod_id=s['pod_id']);write(root/'GATE_VERIFIED.json',receipt);close(root,s,True,'complete verified gate evidence; no production authorized');return
   if time.time()-last>=60:
    a=backup(root,s);s.update(last_backup_epoch=time.time(),last_backup_archive=str(a));write(root/'STATE.json',s);last=time.time()
   if time.time()>=s['created_epoch']+3240:close(root,s,False,'gate budget retrieval reserve; no production');return
  except Exception as e:
   with (root/'EVENTS.log').open('a') as f:f.write(datetime.datetime.now(datetime.timezone.utc).isoformat()+' '+type(e).__name__+' '+str(e)+'\n')
   if time.time()>=s['created_epoch']+3240:close(root,s,False,'retrieval failure at original gate reserve');return
  time.sleep(10)

def hardstop(root):
 s=json.loads((root/'STATE.json').read_text())
 while time.time()<s['created_epoch']+3360:
  if json.loads((root/'STATE.json').read_text()).get('status') in ('TERMINATED','CLOSED_EXITED'):return
  time.sleep(min(10,max(0,s['created_epoch']+3360-time.time())))
 close(root,s,False,'independent original1h cap; no blocking backup at deadline')

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['supervise','hardstop']);a.add_argument('root',type=P);args=a.parse_args();globals()[args.mode](args.root)
