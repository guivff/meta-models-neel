"""Stage only after independent proof that allocator exited and original guards live."""
import json,os,time,subprocess,hashlib,shlex,sys,concurrent.futures
from pathlib import Path
HOME=Path(__file__).resolve().parent
sys.path.insert(0,str(HOME))
import allocate_once as a
GUARDS=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r/offvolume')
KEY=Path.home()/'.ssh/id_ed25519_runpod'
def ssh(s,program,timeout=60):
 host,port=s['address'].split(':');args=['ssh','-i',str(KEY),'-p',port,'-o','BatchMode=yes','-o','ConnectTimeout=15','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','root@'+host,'bash -s']
 p=subprocess.run(args,input=program.encode(),capture_output=True,timeout=timeout)
 with (HOME/'STAGING.private.jsonl').open('a') as f:f.write(json.dumps(dict(at=time.time(),code=p.returncode,stdout=p.stdout.decode(errors='replace'),stderr=p.stderr.decode(errors='replace')))+'\n');os.chmod(f.name,0o600)
 assert p.returncode==0,'SSH_STAGE_FAILED';return p.stdout.decode()
def state():return json.loads(a.STATE.read_text())
def main():
 os.umask(0o077);s=state();m=json.loads((HOME/'PREPARATION.json').read_text());assert s['status']=='ARMED_WAITING_INDEPENDENT_PARENT_EXIT_PROOF'
 durable=json.loads((HOME/'DURABLE_GUARD_LABEL.json').read_text());assert durable['label']=='com.mats.i2.e85.retained.20261029.a1.stop' and durable['original_deadline']==s['hard_deadline_epoch']
 live=subprocess.run(['launchctl','list',durable['label']],capture_output=True,text=True)
 assert live.returncode==0 and durable['label'] in live.stdout and durable['state_dir'] in live.stdout
 assert subprocess.run(['ps','-p',str(s['allocator_pid'])],capture_output=True).returncode!=0,'ALLOCATOR_STILL_LIVE'
 g=dict(l.split('=',1) for l in (GUARDS/s['pod_id']/'mac_guard/state').read_text().splitlines() if '=' in l)
 assert g['pod']==s['pod_id'] and g['keys_staged']=='0'
 abs_guard=json.loads((HOME/'ABSOLUTE_GUARD.private.json').read_text())
 assert abs_guard['stop_at']<=s['hard_deadline_epoch'] and abs_guard['original_creation']==s['created_epoch']
 p=subprocess.run(['ps','-p',str(abs_guard['pid']),'-o','command='],capture_output=True,text=True)
 assert p.returncode==0 and 'absolute_stop.py' in p.stdout and os.getpgid(abs_guard['pid'])!=os.getpgrp()
 for kind in ('hardstop','watchdog'):
  p=subprocess.run(['ps','-p',g[kind+'_pid'],'-o','command='],capture_output=True,text=True);assert p.returncode==0 and s['pod_id'] in p.stdout and 'ws2_'+kind+'.sh' in p.stdout
  assert os.getpgid(int(g[kind+'_pid']))!=os.getpgrp()
 pod=a.api('query { pod(input:{podId:'+json.dumps(s['pod_id'])+'}) { id desiredStatus createdAt costPerHr } }')['pod'];assert pod['id']==s['pod_id'] and pod['desiredStatus']=='RUNNING' and pod['createdAt']==s['provider_creation']['createdAt']
 proof=dict(at=time.time(),allocator_exited=True,both_guards_live=True,original_deadline=s['hard_deadline_epoch'],absolute_provider_stop_at=abs_guard['stop_at'],relative_guard_drift_seconds=int(g['deadline'])-s['hard_deadline_epoch'],new_clocks=False);(HOME/'INDEPENDENT_GUARD_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
 remote='/workspace/'+s['run_id'];s['remote_dir']=remote;s['status']='STAGING';a.save(s)
 ssh(s,'set -e\nmkdir '+shlex.quote(remote)+'\ncommand -v /weights/venv-kernels/bin/python\n')
 host,port=s['address'].split(':')
 for src,name in [(HOME/'source-provenance.tar.gz','source.tar.gz'),(HOME/'inputs.tar.gz','inputs.tar.gz'),(HOME/'capture.public-vectors.tar.gz','capture.public-vectors.tar.gz'),(HOME/'CPU_RELEASE.json','CPU_RELEASE.json')]:
  p=subprocess.run(['scp','-i',str(KEY),'-P',port,'-o','BatchMode=yes','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null',str(src),'root@'+host+':'+remote+'/'+name],capture_output=True,timeout=60);assert p.returncode==0,'SCP_SOURCE_INPUT_FAILED'
 assigned=dict(experiment=m['experiment'],pod_id=s['pod_id'],run_id=s['run_id'],gpu_count=1,cap_seconds=m['cap_seconds'],prior_seconds=m['prior_probe_gpu_seconds'],gpu_type='H200',pod_created_epoch=s['created_epoch'],custody_start_epoch=s['created_epoch'],absolute_deadline_epoch=s['hard_deadline_epoch'],daily_budget_verified=True,projected_daily_USD=json.loads((HOME/'BUDGET.json').read_text())['GPU_upper_with_candidate_usd'])
 assigned['capture_seal_sha256']=m['capture_seal_sha256']
 cache=json.loads(Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i2/results/g_agreement/i2/E73_NATIVE_CACHE_20261027T160646Z.json').read_text())
 versions=cache['runtime_versions'];pins=cache['pins'];target='/weights/hf_cache/hub/models--Qwen--Qwen3.6-27B/snapshots/'+pins['TARGET_MODEL_SHA']
 program=f'''set -e
cd {shlex.quote(remote)}
/weights/venv-kernels/bin/python - <<'REMOTE'
import json,time,hashlib,tarfile,os,importlib.metadata as md
from pathlib import Path
assert time.time() < {s['created_epoch']+900!r}, 'original setup900 exceeded'
assert time.time() < {s['hard_deadline_epoch']-60!r}
for name,expected in {versions!r}.items():assert md.version(name)==expected, 'runtime '+name
for name,expected in {{'source.tar.gz':{m['source_archive_sha256']!r},'inputs.tar.gz':{m['input_archive_sha256']!r},'capture.public-vectors.tar.gz':{m['capture_archive_sha256']!r}}}.items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected
 with tarfile.open(name) as t:
  for item in t.getmembers():
   p=Path(item.name);assert not p.is_absolute() and '..' not in p.parts and not(item.issym() or item.islnk())
  t.extractall('.')
assert hashlib.sha256(Path('capture/STAGE_SEAL.json').read_bytes()).hexdigest()=={m['capture_seal_sha256']!r}
cs=json.loads(Path('capture/STAGE_SEAL.json').read_text())
for name,expected in cs['files'].items():assert hashlib.sha256((Path('capture')/name).read_bytes()).hexdigest()==expected
asset_manifest={{'model': '/weights/hf_cache/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9', 'olens': '/weights/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600', 'nla': '/weights/hf_cache/hub/models--ceselder--qwen3.6-27b-nla-rl/snapshots/5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f', 'revisions': {{'model': '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9', 'olens': 'c95215d5d2f6250f20c305ae55c6e4d7569f92dc', 'nla': '5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f'}}}}
files=[]
for asset_name in ('model','olens','nla'):
 root=Path(asset_manifest[asset_name]);assert root.is_dir(), 'missing registered '+asset_name
 for f in sorted(root.rglob('*')):
  if f.is_file():
   assert f.resolve().is_relative_to(Path('/weights'))
   h=hashlib.sha256()
   with f.open('rb') as stream:
    for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
   files.append(dict(path=str(f),sha256=h.hexdigest()))
asset_manifest['files']=files
Path('assets.json').write_text(json.dumps(asset_manifest))
Path('assignment.json').write_text(json.dumps({assigned!r}))
Path('RUNTIME_STAGING.json').write_text(json.dumps(dict(at=time.time(),asset_files=len(files),original_setup_deadline={s['created_epoch']+900!r},setup_completed_in_time=time.time()<{s['created_epoch']+900!r})))
assert time.time()<{s['created_epoch']+900!r},'original setup900 exceeded'
REMOTE
'''
 ssh(s,program,min(850,int(s['created_epoch']+900-time.time())))
 # Final read-only identity and immutable deadline before start. No guard rearm.
 assert time.time()<s['created_epoch']+900 and time.time()<s['hard_deadline_epoch']-60
 with (HOME/'ENGINE_ONCE_INTENT.json').open('x') as f:json.dump(dict(at=time.time(),run_id=s['run_id'],source_sha=m['source_sha'],input_sha=m['input_sha']),f)
 cmd=f"/weights/venv-kernels/bin/python -B results/g_agreement/understand/late198/retained85.py --inputs inputs --assets assets.json --assignment assignment.json --out outputs --releases releases --capture capture --cpu-release CPU_RELEASE.json --source-sha {m['source_sha']} --input-sha {m['input_sha']} --retained-source-sha {m['retained_source_sha']}"
 cap=max(1,int(s['hard_deadline_epoch']-time.time()-5))
 body=f'''#!/bin/bash
cd {shlex.quote(remote)}
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/weights/hf_cache
set +e
timeout -k 5 {cap} {cmd} >worker.log 2>&1
rc=$?
/weights/venv-kernels/bin/python -c 'import json,time;open("EXIT.json","x").write(json.dumps(dict(code='$rc',finished_epoch=time.time())))'
'''
 launch=f"set -e\ncd {shlex.quote(remote)}\ncat > run.sh <<'SCRIPT'\n{body}\nSCRIPT\nchmod 700 run.sh\nnohup setsid bash run.sh </dev/null >supervisor.log 2>&1 &\necho $! >job.pid\nmkdir -p /workspace/ws2_logs\ncp job.pid /workspace/ws2_logs/job.pid\n"
 ssh(s,'mkdir -p '+shlex.quote(remote+'/releases')+'\n',30);ssh(s,launch,30);s.update(status='WORKER_STARTED_ORIGINAL_DEADLINE',started_epoch=time.time());a.save(s);print(m['experiment']+' specialized worker started; original creation-bound deadline unchanged')
if __name__=='__main__':main()
