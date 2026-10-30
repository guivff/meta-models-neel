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
 durable=json.loads((HOME/'DURABLE_GUARD_LABEL.json').read_text());assert durable['label']=='com.mats.i2.e110.filter.amend1.s3.20261029.a1.stop' and durable['original_deadline']==s['hard_deadline_epoch']
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
 for src,name in [(HOME/'source.tar.gz','source.tar.gz'),(HOME/'PUBLIC_FILTER_INPUTS.tar.gz','inputs.tar.gz')]:
  p=subprocess.run(['scp','-i',str(KEY),'-P',port,'-o','BatchMode=yes','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null',str(src),'root@'+host+':'+remote+'/'+name],capture_output=True,timeout=60);assert p.returncode==0,'SCP_SOURCE_INPUT_FAILED'
 assigned=dict(experiment='E110_FILTER_AMEND1',pod_id=s['pod_id'],run_id=s['run_id'],gpu_count=1,cap_seconds=2616,pod_created_epoch=s['created_epoch'],absolute_deadline_epoch=s['hard_deadline_epoch'],shard=m['shard'],candidate_count=750,public_jobs=m['public_jobs'])
 model='/weights/hf_cache/hub/models--Qwen--Qwen3.6-27B/snapshots/'+m['model_revision']
 program=f"""set -e
cd {shlex.quote(remote)}
/weights/venv-kernels/bin/python - <<'REMOTE'
import json,time,hashlib,tarfile,importlib.util,importlib.metadata as md
from pathlib import Path
assert time.time() < {s['created_epoch']+900!r}
for name,expected in {{'torch': '2.8.0+cu128', 'transformers': '5.18.0', 'numpy': '2.5.3', 'peft': '0.21.2', 'safetensors': '0.8.0', 'flash-linear-attention': '0.5.2', 'causal-conv1d': '1.7.0', 'accelerate': '1.15.0', 'huggingface-hub': '1.33.0', 'PyYAML': '6.0.3'}}.items():assert md.version(name)==expected, 'runtime '+name
for n,expected,allow in [('source.tar.gz',{m['source_archive_sha256']!r},['worker.py']),('inputs.tar.gz',{m['input_archive_sha256']!r},['PUBLIC_FILTER_INPUTS.json'])]:
 assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==expected
 with tarfile.open(n) as t:
  assert t.getnames()==allow
  for x in t.getmembers():assert x.isfile() and not x.issym() and not x.islnk()
  t.extractall('.')
assert hashlib.sha256(Path('worker.py').read_bytes()).hexdigest()=={m['source_file_sha256']!r}
spec=importlib.util.spec_from_file_location('exact_e110_worker','worker.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
xs=json.loads(Path('PUBLIC_FILTER_INPUTS.json').read_text());assert len(mod.groups(xs,expected_jobs=2931))>0
assert Path({model!r}).is_dir()
files=[]
for p in sorted(Path({model!r}).rglob('*')):
 if p.is_file():
  assert p.resolve().is_relative_to(Path('/weights'))
  h=hashlib.sha256()
  with p.open('rb') as f:
   for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
  files.append(dict(path=str(p),sha256=h.hexdigest()))
Path('ASSET_BINDING.json').write_text(json.dumps(dict(model={model!r},revision={m['model_revision']!r},files=files)))
Path('assignment.json').write_text(json.dumps({assigned!r}))
Path('RUNTIME_STAGING.json').write_text(json.dumps(dict(at=time.time(),source_import_pass=True,original_setup_deadline={s['created_epoch']+900!r})))
assert time.time() < {s['created_epoch']+900!r}
REMOTE
"""
 ssh(s,program,min(850,int(s['created_epoch']+900-time.time())))
 assert time.time()<s['created_epoch']+900 and time.time()<s['hard_deadline_epoch']-60
 with(HOME/'ENGINE_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),run_id=s['run_id'],source_sha256=m['source_file_sha256']),f)
 input_digest=ssh(s,'cd '+shlex.quote(remote)+"\nsha256sum PUBLIC_FILTER_INPUTS.json\n",30).split()[0]
 cmd=f"/weights/venv-kernels/bin/python -B worker.py --inputs PUBLIC_FILTER_INPUTS.json --inputs-sha256 {input_digest} --assignment assignment.json --model {model} --out outputs"
 cap=max(1,int(s['hard_deadline_epoch']-time.time()-5))
 body=f"""#!/bin/bash
cd {shlex.quote(remote)}
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/weights/hf_cache
set +e
timeout -k 5 {cap} {cmd} >worker.log 2>&1
rc=$?
/weights/venv-kernels/bin/python -c 'import json,time;open("EXIT.json","x").write(json.dumps(dict(code='$rc',finished_epoch=time.time())))'
"""
 launch=f"set -e\ncd {shlex.quote(remote)}\ncat > run.sh <<'SCRIPT'\n{body}\nSCRIPT\nchmod 700 run.sh\nnohup setsid bash run.sh </dev/null >supervisor.log 2>&1 &\necho $! >job.pid\nmkdir -p /workspace/ws2_logs\ncp job.pid /workspace/ws2_logs/job.pid\n"
 ssh(s,launch,30);s.update(status='WORKER_STARTED_ORIGINAL_DEADLINE',started_epoch=time.time());a.save(s);print('E110 filter worker started; original creation-bound1800s unchanged')
if __name__=='__main__':main()
