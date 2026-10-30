"""Resume only a verified interrupted capture prefix, under the original setup clock."""
from stage_and_start import *
def main():
 s=state();m=json.loads((HOME/'PREPARATION.json').read_text());assert s['status']=='STAGING' and not (HOME/'ENGINE_ONCE_INTENT.json').exists()
 assert (HOME/'STAGE_TRANSFER_FAILURE.json').exists(),'ACTUAL_ORIGINAL_CONTROLLER_FAILURE_REQUIRED'
 assert time.time()<s['created_epoch']+900-300
 with (HOME/'CAPTURE_PREFIX_CONTINUATION_ONCE_INTENT.json').open('x') as f:json.dump(dict(at=time.time(),original_creation=s['created_epoch'],original_deadline=s['hard_deadline_epoch'],engine_not_started=True),f)
 remote=s['remote_dir'];host,port=s['address'].split(':')
 durable=json.loads((HOME/'DURABLE_GUARD_LABEL.json').read_text());assert durable['original_deadline']==s['hard_deadline_epoch']
 live=subprocess.run(['launchctl','list',durable['label']],capture_output=True,text=True);assert live.returncode==0
 g=dict(l.split('=',1) for l in (GUARDS/s['pod_id']/'mac_guard/state').read_text().splitlines() if '=' in l)
 for kind in ('hardstop','watchdog'):
  p=subprocess.run(['ps','-p',g[kind+'_pid'],'-o','command='],capture_output=True,text=True);assert p.returncode==0 and s['pod_id'] in p.stdout
 program='cd '+shlex.quote(remote)+"\n/weights/venv-kernels/bin/python - <<'PREFIX'\nfrom pathlib import Path\nimport hashlib,json\nassert not Path('outputs').exists() and not Path('run.sh').exists()\np=Path('capture.private.tar.gz');print(json.dumps(dict(size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())))\nPREFIX\n"
 prefix=json.loads(ssh(s,program,30).strip());local=HOME/'capture.private.tar.gz';assert 0<prefix['size']<=local.stat().st_size
 with local.open('rb') as f:assert hashlib.sha256(f.read(prefix['size'])).hexdigest()==prefix['sha256'],'PARTIAL_CAPTURE_PREFIX_MISMATCH'
 if prefix['size']<local.stat().st_size:
  batch='reput '+shlex.quote(str(local))+' '+shlex.quote(remote+'/capture.private.tar.gz')+'\n'
  args=['sftp','-b','-','-i',str(KEY),'-P',port,'-o','BatchMode=yes','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','root@'+host]
  limit=int(s['created_epoch']+900-time.time()-300);assert limit>0
  p=subprocess.run(args,input=batch.encode(),capture_output=True,timeout=limit);assert p.returncode==0,'PREFIX_TRANSFER_FAILED'
 for src,name in [(HOME/'MEASURED_PROFILE.json','MEASURED_PROFILE.json'),(HOME.parent/'MEASURED_AGGREGATE_BINDING.json','MEASURED_AGGREGATE_BINDING.json')]:
  p=subprocess.run(['scp','-i',str(KEY),'-P',port,'-o','BatchMode=yes','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null',str(src),'root@'+host+':'+remote+'/'+name],capture_output=True,timeout=30);assert p.returncode==0
 assigned=dict(experiment='E99',stage99='read',shard=m['shard'],capture_seal_sha256=m['capture_seal_sha256'],measured_profile_sha256=m['measured_profile_sha256'],admission_sha256=m['admission_sha256'],pod_id=s['pod_id'],run_id=s['run_id'],gpu_count=1,cap_seconds=m['cap_seconds'],prior_seconds=m['prior_probe_gpu_seconds'],pod_created_epoch=s['created_epoch'],custody_start_epoch=s['created_epoch'],absolute_deadline_epoch=s['hard_deadline_epoch'],daily_budget_verified=True,projected_daily_USD=json.loads((HOME/'BUDGET.json').read_text())['GPU_upper_with_candidate_usd'])
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
for name,expected in {{'source.tar.gz':{m['source_archive_sha256']!r},'inputs.tar.gz':{m['input_archive_sha256']!r},'capture.private.tar.gz':{m['capture_archive_sha256']!r}}}.items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected
 with tarfile.open(name) as t:
  for item in t.getmembers():
   p=Path(item.name);assert not p.is_absolute() and '..' not in p.parts and not(item.issym() or item.islnk())
  t.extractall('.')
assert hashlib.sha256(Path('MEASURED_PROFILE.json').read_bytes()).hexdigest()=={m['measured_profile_sha256']!r}
assert hashlib.sha256(Path('MEASURED_AGGREGATE_BINDING.json').read_bytes()).hexdigest()=={m['admission_sha256']!r}
assert hashlib.sha256(Path('capture/CAPTURE_SEAL.json').read_bytes()).hexdigest()=={m['capture_seal_sha256']!r}
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
assignment={assigned!r}
assignment['staging_seconds']=time.time()-{s['created_epoch']!r}
Path('assignment.json').write_text(json.dumps(assignment))
Path('RUNTIME_STAGING.json').write_text(json.dumps(dict(at=time.time(),asset_files=len(files),original_setup_deadline={s['created_epoch']+900!r},setup_completed_in_time=time.time()<{s['created_epoch']+900!r})))
assert time.time()<{s['created_epoch']+900!r},'original setup900 exceeded'
REMOTE
'''
 ssh(s,program,min(850,int(s['created_epoch']+900-time.time())))
 # Final read-only identity and immutable deadline before start. No guard rearm.
 assert time.time()<s['created_epoch']+900 and time.time()<s['hard_deadline_epoch']-60
 with (HOME/'ENGINE_ONCE_INTENT.json').open('x') as f:json.dump(dict(at=time.time(),run_id=s['run_id'],source_sha=m['source_sha'],input_sha=m['input_sha']),f)
 cmd=f"/weights/venv-kernels/bin/python -B results/g_agreement/understand/e87/worker87.py --inputs inputs --assets assets.json --assignment assignment.json --out outputs --source-sha {m['source_sha']} --input-sha {m['input_sha']} --stage99 read --capture-root capture --measured-profile MEASURED_PROFILE.json"
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
 ssh(s,'mkdir -p '+shlex.quote(remote+'/releases')+'\n',30);ssh(s,launch,30);s.update(status='WORKER_STARTED_ORIGINAL_DEADLINE',started_epoch=time.time());a.save(s);print('E99 read worker started; original creation-bound deadline unchanged')
if __name__=='__main__':main()
