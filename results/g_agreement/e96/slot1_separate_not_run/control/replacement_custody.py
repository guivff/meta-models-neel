"""One authorized slot-1 replacement; laptop-only custody, no scientific retry.

Standalone stdlib implementation copied byte-for-byte to a non-Documents service
root. No idle-GPU stop exists. Every minute retains a new immutable PAX snapshot;
completion triggers full verification before stop. Independent hardstop shares
original creation time and never renews it. Snapshot contents are never scored.
"""
import argparse,datetime,hashlib,json,os,pathlib,shlex,shutil,subprocess,tarfile,tempfile,time
P=pathlib.Path
REMOTE='/workspace/e96-sampling'
API=P.home()/'repl/tools/runpod_api.sh'
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def write(p,d):
 p=P(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(p)
def query(q):
 d=json.loads(subprocess.check_output(['bash',str(API),q],text=True,timeout=45))
 if d.get('errors'):raise RuntimeError('provider API error')
 return d['data']
def provider(s):
 p=query('query { pod(input:{podId:"'+s['pod_id']+'"}) { id name desiredStatus createdAt costPerHr gpuCount runtime { ports { ip isIpPublic privatePort publicPort } } } }')['pod']
 if p is not None and (p['id']!=s['pod_id'] or p['name']!=s['pod_name'] or p['createdAt']!=s['created_utc']):raise ValueError('owned replacement identity')
 return p
def ssh(s,command,**kw):
 a=s['ssh'];return subprocess.run(['ssh','-o','StrictHostKeyChecking=accept-new','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2','-i',str(P.home()/'.ssh/id_ed25519_runpod'),'-p',str(a['publicPort']),'root@'+a['ip'],command],**kw)
def extract(archive,dest):
 with tarfile.open(archive) as t:
  for m in t.getmembers():
   if m.name.startswith('/') or '..' in P(m.name).parts or not (m.isfile() or m.isdir()):raise ValueError('unsafe PAX archive member')
  t.extractall(dest,filter='data')
def snapshot(root,s,full=False):
 """A fresh snapshot never overwrites a prior snapshot or reads semantic results."""
 folder=root/'backups';folder.mkdir(exist_ok=True)
 path=folder/(str(time.time_ns())+('.full' if full else '.incremental')+'.tar.gz')
 code="import pathlib,tarfile,sys; r=pathlib.Path('/workspace/e96-sampling'); t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',format=tarfile.PAX_FORMAT); files="
 if full:code+="[p for p in r.rglob('*') if p.is_file() and (p.is_relative_to(r/'out') or p.relative_to(r).as_posix() in ['job.log','stage.log','assets.json','ASSIGNMENT.json','SOURCE_SEAL.json','sampling_code.tar.gz'])]"
 else:code+="[p for p in (r/'out').rglob('*') if p.is_file() and (p.name.startswith(('generate.','reconstruct.')) or p.name in ['FIRST_OUTPUT.json','RUN.json','OUTPUT_SEAL.json'])]"
 code+="; [(t.add(p,arcname=str(p.relative_to(r)),recursive=False)) for p in sorted(files)]; t.close()"
 with path.with_suffix('.part').open('wb') as f:r=ssh(s,'python3 -c '+shlex.quote(code),stdout=f,stderr=subprocess.PIPE,timeout=180)
 if r.returncode:raise RuntimeError('snapshot transport failed; no stop authorized')
 path.with_suffix('.part').replace(path)
 check=P(tempfile.mkdtemp(prefix='verify-',dir=root))
 try:
  extract(path,check);files={str(p.relative_to(check)):sha(p) for p in check.rglob('*') if p.is_file()}
  prior=json.loads((root/'IMMUTABLE_FILES.json').read_text()) if (root/'IMMUTABLE_FILES.json').exists() else {}
  immutable={n:h for n,h in files.items() if P(n).name.startswith(('generate.','reconstruct.')) or P(n).name=='FIRST_OUTPUT.json'}
  if any(immutable.get(n)!=h for n,h in prior.items()):raise ValueError('retained immutable output missing or changed')
  write(root/'IMMUTABLE_FILES.json',immutable)
  write(path.with_suffix('.receipt.json'),{'archive_sha256':sha(path),'files':files,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'full' if full else 'incremental','unscored':True})
 finally:shutil.rmtree(check)
 return path

def verify_complete(archive,expected,source_sha,seal_sha,pod):
 work=P(tempfile.mkdtemp(prefix='complete-',dir=archive.parent.parent))
 try:
  extract(archive,work);out=work/'out';run=json.loads((out/'RUN.json').read_text());seal=json.loads((out/'OUTPUT_SEAL.json').read_text())
  if run['status']!='COMPLETE' or seal['status']!='COMPLETE' or run['slot']!=1 or run['pod_id']!=pod:raise ValueError('replacement completion/ownership')
  if sha(work/'sampling_code.tar.gz')!=source_sha or sha(work/'SOURCE_SEAL.json')!=seal_sha:raise ValueError('executed source differs from original preflight')
  for n,h in seal['files'].items():
   p=out/n
   if not p.resolve().is_relative_to(out.resolve()) or sha(p)!=h:raise ValueError('output hash mismatch')
  want={tuple(x) for x in expected}
  for phase in ('generate','reconstruct'):
   rows=[x for p in out.glob('*/*/'+phase+'.*.json') for x in json.loads(p.read_text())];keys={(x['row_key'],x['reader'],x['id'],x['sample_index']) for x in rows}
   if len(rows)!=17920 or len(keys)!=len(rows) or keys!=want:raise ValueError('exact original slot1 grid')
  first=min(out.glob('*/*/generate.*.json'),key=lambda p:p.stat().st_mtime_ns)
  first_utc=datetime.datetime.fromtimestamp(first.stat().st_mtime,datetime.timezone.utc).isoformat()
  if first_utc!=seal['first_output_utc'] or first_utc!=run['first_output_utc']:raise ValueError('first output PAX mtime')
  return {'status':'PASS','pod_id':pod,'slot':1,'attempt':'replacement-once','samples':17920,'gpu_type':'H200','first_output_utc':first_utc,'first_output_source':'first generation file PAX mtime','archive_sha256':sha(archive),'output_seal_sha256':sha(out/'OUTPUT_SEAL.json'),'verified_files':len(seal['files'])}
 finally:shutil.rmtree(work)

def decision(now,s,complete,failed):
 if complete:return 'VERIFY_COLLECT_STOP'
 if failed:return 'BACKUP_STOP_FALLBACK'
 if now>=s['created_epoch']+14040:return 'BACKUP_STOP_FALLBACK'
 return 'CONTINUE_BACKUP'  # GPU utilization is deliberately irrelevant.

def stop(root,s,verified,reason):
 # Snapshot first. At the hard deadline budget wins even if the network is down.
 p=provider(s)
 if p is not None and p['desiredStatus']!='EXITED':query('mutation { podStop(input:{podId:"'+s['pod_id']+'"}) { id desiredStatus } }')
 limit=time.time()+90
 while p is not None and p['desiredStatus']!='EXITED':
  if time.time()>limit:raise RuntimeError('stop not confirmed')
  time.sleep(3);p=provider(s)
 exit_time=time.time();s.update(status='CLOSED_EXITED',first_exit_observed_epoch=exit_time,verified_complete=verified,close_reason=reason,gpu_hours_upper=(exit_time-s['created_epoch'])/3600,gpu_usd_rate_based_upper=(exit_time-s['created_epoch'])/3600*s['rate'])
 write(root/'STATE.json',s)
 # Termination only after complete verified pull. Failed partials stay unopened.
 if (verified or s.get('preemption_archive_custody_verified')) and p is not None:
  query('mutation { podTerminate(input:{podId:"'+s['pod_id']+'"}) }')
  if provider(s) is not None:raise RuntimeError('termination not confirmed')
  s['status']='TERMINATED';write(root/'STATE.json',s)

CORE={'E101','E81','E90','E86','E82','E99','E103','E80c','E87'}
def preempt(root,s):
 request=root/'CORE_PREEMPT_REQUEST.json'
 if not request.exists():return False
 d=json.loads(request.read_text())
 if d.get('pod_id')!=s['pod_id'] or d.get('core_experiment') not in CORE or not d.get('requested_by') or not d.get('reason'):raise ValueError('preemption must bind ownedpod and CORE authority')
 archive=snapshot(root,s,full=True)
 with tarfile.open(archive) as saved:
  times=[m.mtime for m in saved.getmembers() if m.isfile() and P(m.name).name.startswith('generate.')]
 first=datetime.datetime.fromtimestamp(min(times),datetime.timezone.utc).isoformat() if times else 'unknown'
 receipt={'status':'PREEMPTED_NOT_RUN','authority':'§211amendment1,7a354530','request':d,'archive_path':str(archive),'archive_sha256':sha(archive),'disposition':'Entire original slot1 replacement incomplete: ALL slot1 rows NOT RUN; no partial rows stitched or scored','first_output_utc':first,'first_output_note':'earliest generation PAX mtime, or unknown if no generation; partial contents unopened; final analysis uses retained35200 only'}
 write(root/'PREEMPTION_RECEIPT.json',receipt)
 s['preemption_archive_custody_verified']=True
 stop(root,s,False,'COREpreemption: slot1 NOT RUN, no stitching')
 return True

def supervise(root):
 s=json.loads((root/'STATE.json').read_text())
 if s.get('status') in ('TERMINATED','CLOSED_EXITED'):return
 expected=json.loads((root/'EXPECTED.json').read_text());last=0
 while True:
  p=provider(s)
  if p is None or p['desiredStatus']=='EXITED':raise RuntimeError('unexpected stopped/absent replacement; use registered fallback, never retry')
  if not s.get('ssh') and p.get('runtime'):
   s['ssh']=next(x for x in p['runtime']['ports'] if x['privatePort']==22 and x['isIpPublic']);write(root/'STATE.json',s)
  if not s.get('ssh'):time.sleep(5);continue
  try:
   if preempt(root,s):return
   r=ssh(s,'test -f '+REMOTE+'/out/OUTPUT_SEAL.json && echo COMPLETE; test -f '+REMOTE+'/out/FAILURE.json && echo FAILED; true',capture_output=True,text=True,timeout=20)
   if r.returncode:raise RuntimeError('SSH health failure')
   complete='COMPLETE' in r.stdout;failed='FAILED' in r.stdout or (root/'STAGING_ERROR.json').exists();action=decision(time.time(),s,complete,failed)
   if action=='VERIFY_COLLECT_STOP':
    archive=snapshot(root,s,full=True);receipt=verify_complete(archive,expected,s['archive_sha256'],s['source_seal_sha256'],s['pod_id']);receipt['archive_path']=str(archive);write(root/'PULL_VERIFIED.json',receipt)
    stop(root,s,True,'complete exact-grid verified local archive');return
   if action=='BACKUP_STOP_FALLBACK':
    archive=snapshot(root,s,full=True)
    with tarfile.open(archive) as saved:times=[m.mtime for m in saved.getmembers() if m.isfile() and P(m.name).name.startswith('generate.')]
    first=datetime.datetime.fromtimestamp(min(times),datetime.timezone.utc).isoformat() if times else 'unknown'
    write(root/'FALLBACK_CUSTODY_RECEIPT.json',{'status':'NOT_RUN_INCOMPLETE_REPLACEMENT','archive_path':str(archive),'archive_sha256':sha(archive),'pod_id':s['pod_id'],'first_output_utc':first,'first_output_source':'first generation PAX mtime if any; partial contents remain unopened','disposition':'all incomplete slot1 rows NOT RUN, no stitching; retained primary unaffected','reason':'worker/stagingfailure or original retrieval reserve'})
    stop(root,s,False,'full failure diagnostics archived; incomplete slot1 NOTRUN');return
   if time.time()-last>=60:
    archive=snapshot(root,s);s.update(last_backup_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),last_backup_archive=str(archive),backup_files=len(json.loads((root/'IMMUTABLE_FILES.json').read_text())));write(root/'STATE.json',s);last=time.time()
  except Exception as e:
   with (root/'EVENTS.log').open('a') as f:f.write(datetime.datetime.now(datetime.timezone.utc).isoformat()+' '+type(e).__name__+' '+str(e)+'\n')
   if time.time()>=s['created_epoch']+14040:stop(root,s,False,'retrieval failure at original budget reserve; fallback');return
  time.sleep(10)

def hardstop(root):
 s=json.loads((root/'STATE.json').read_text())
 while time.time()<s['created_epoch']+14160:
  if (root/'STATE.json').exists() and json.loads((root/'STATE.json').read_text()).get('status') in ('TERMINATED','CLOSED_EXITED'):return
  time.sleep(min(10,max(0,s['created_epoch']+14160-time.time())))
 # Independent guard never blocks on a network backup at the hard deadline.
 # Primary backups run every minute; budget reserve is240s.
 # No budget-clock renewal and no sampling retry.
 stop(root,s,False,'independent original4h hardstop; registered fallback')

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['supervise','hardstop']);a.add_argument('root',type=P);v=a.parse_args()
 try:globals()[v.mode](v.root)
 except BaseException as exc:
  write(v.root/(v.mode+'_ERROR.json'),{'error_type':type(exc).__name__,'error':str(exc),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});raise
