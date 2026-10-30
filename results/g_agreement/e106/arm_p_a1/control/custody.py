"""Laptop-only E102 gate custody: no idle stop, no training/retry launcher.

Uses only stdlib. The separately frozen worker generates all GPU evidence. This
module verifies bytes/ordering after pull; it never trains, judges or scores S.
"""
import argparse,datetime,hashlib,json,math,pathlib,shlex,shutil,subprocess,tarfile,tempfile,time
P=pathlib.Path
REMOTE='/workspace/e106-run'
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
 a=s['ssh'];return subprocess.run(['ssh','-o','StrictHostKeyChecking=accept-new','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2','-i',str(P.home()/'.ssh/id_ed25519_runpod'),'-p',str(a['publicPort']),'root@'+a['ip'],cmd],**kw)
def unpack(archive,dest):
 with tarfile.open(archive) as t:
  for m in t.getmembers():
   if m.name.startswith('/') or '..' in P(m.name).parts or not(m.isfile() or m.isdir()):raise ValueError('unsafe archive')
  t.extractall(dest,filter='data')
def backup(root,s,full=False):
 folder=root/'backups';folder.mkdir(exist_ok=True);archive=folder/(str(time.time_ns())+('.full' if full else '')+'.tar.gz')
 code="import pathlib,tarfile,sys;r=pathlib.Path('/workspace/e106-run');t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',format=tarfile.PAX_FORMAT);files="
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
  if not p.resolve().is_relative_to(out.resolve()) or sha(p)!=h:raise ValueError('E106 output hash')
 firsts=[p for p in out.iterdir() if p.is_file() and (p.name=='PARITY_RAW.json' or p.name.startswith(('oracle_0','nla_0')) and p.stem.rsplit('_',1)[-1].isdigit())]
 first=min(firsts,key=lambda p:p.stat().st_mtime_ns) if firsts else None
 result={'status':'NOT_RUN','phase':expected['phase'],'first_output_utc':datetime.datetime.fromtimestamp(first.stat().st_mtime,datetime.timezone.utc).isoformat() if first else 'unknown','first_output_source':str(first.relative_to(root))+' PAXmtime' if first else 'no generatedreadoutfound','gpu_type':gpu_type,'verified_files':len(seal['files']),'scientific_analysis':False}
 if (out/'FAILURE.json').exists():result['failure']=json.loads((out/'FAILURE.json').read_text());return result
 report=json.loads((out/'REPORT.json').read_text())
 if expected['phase']=='arm_p':
  rows=[]
  for reader in ['oracle','nla']:
   for p in sorted(out.glob(reader+'_*.json')):
    if p.stem.rsplit('_',1)[-1].isdigit():rows+=json.loads(p.read_text())
  keys=[(x['reader'],x['item_key']) for x in rows];want={(reader,key) for reader in ['oracle','nla'] for key in expected['item_keys']}
  if len(keys)!=1344 or len(set(keys))!=1344 or set(keys)!=want or report['status']!='COMPLETE' or report['outputs']!=1344:raise ValueError('exact1344Pgrid')
  result.update(status='COMPLETE',outputs=1344);return result
 checks=json.loads((out/'PARITY.json').read_text());raw=json.loads((out/'PARITY_RAW.json').read_text());parameters=json.loads((out/'PARAMETERS.json').read_text());parity=expected['parity'];derived=[]
 for i in parity['compare_indices']:
  actual=raw[i]['raw'].encode();want=parity['records'][i]['raw'].encode();derived.append(actual==want)
 if len(derived)!=3 or not all(derived) or len(checks)!=3 or not all(x['byte_equal'] for x in checks):raise ValueError('threebyteexactgreedyrequired')
 losses=[json.loads((out/f'STEP_{i:02d}.json').read_text()) for i in range(1,11)]
 if [x['step'] for x in losses]!=list(range(1,11)) or any(not math.isfinite(x['loss']) for x in losses):raise ValueError('tenfinitesteps')
 if (out/'PARITY.json').stat().st_mtime_ns>min((out/f'STEP_{i:02d}.json').stat().st_mtime_ns for i in range(1,11)):raise ValueError('optimizerbeforeparity')
 if report['status']!='PASS' or report['steps']!=10 or report['frozen_before_sha256']!=report['frozen_after_sha256'] or report['adapter_tensors_changed']<=0:raise ValueError('frozenbaseupdateproof')
 if parameters['new_adapter_rank']!=16 or not parameters['base_and_original_adapter_frozen'] or parameters['merge_used'] or gpu_type not in parameters['gpu']:raise ValueError('rank16frozenoriginalhardware')
 result.update(status='PASS',steps=10,greedy_reproductions=3,base_frozen=True,adapter_tensors_changed=report['adapter_tensors_changed']);return result

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
   if time.time()>=s['deadline_epoch']-240:
    archive=backup(root,s,True);write(root/'GATE_VERIFIED.json',{'status':'NOT_RUN','phase':expected['phase'],'first_output_utc':'unknown','archive_path':str(archive),'archive_sha256':sha(archive),'reason':'originalphasebudgetreserve'});close(root,s,True,'verified diagnostics atphasebudgetreserve');return
  except Exception as e:
   with (root/'EVENTS.log').open('a') as f:f.write(datetime.datetime.now(datetime.timezone.utc).isoformat()+' '+type(e).__name__+' '+str(e)+'\n')
   if time.time()>=s['deadline_epoch']-240:close(root,s,False,'retrieval failure at original gate reserve');return
  time.sleep(10)

def hardstop(root):
 s=json.loads((root/'STATE.json').read_text())
 while time.time()<s['deadline_epoch']-180:
  if json.loads((root/'STATE.json').read_text()).get('status') in ('TERMINATED','CLOSED_EXITED'):return
  time.sleep(min(10,max(0,s['deadline_epoch']-180-time.time())))
 close(root,s,False,'independent originalphase cap; no blocking backup at deadline')

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['supervise','hardstop']);a.add_argument('root',type=P);args=a.parse_args();globals()[args.mode](args.root)
