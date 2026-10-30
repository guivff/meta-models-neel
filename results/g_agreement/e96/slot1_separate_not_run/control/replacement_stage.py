"""Stage the exact original sampling archive once; no data-dependent changes."""
import json,pathlib,subprocess,time,shlex,urllib.request,os,sys
from replacement_custody import provider,ssh,write,sha
P=pathlib.Path
root=P(sys.argv[1]);state=root/'STATE.json';s=json.loads(state.read_text());log=(root/'STAGING.log').open('a')
def run(args,**kw):return subprocess.run(args,stdout=log,stderr=log,check=True,timeout=max(1,min(900,s['created_epoch']+1800-time.time())),**kw)
def remote(cmd,**kw):
 r=ssh(s,cmd,stdout=log,stderr=log,timeout=max(1,min(900,s['created_epoch']+1800-time.time())),**kw)
 if r.returncode:raise RuntimeError('remote staging command failed')
try:
 while time.time()<s['created_epoch']+600:
  p=provider(s)
  if p and p.get('runtime'):
   s['ssh']=next(x for x in p['runtime']['ports'] if x['privatePort']==22 and x['isIpPublic']);break
  time.sleep(5)
 else:raise RuntimeError('no runtime within original staging allowance')
 # Controller writes its own state concurrently; staging never overwrites it.
 write(root/'SSH.json',s['ssh'])
 for _ in range(60):
  if ssh(s,'true',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15).returncode==0:break
  time.sleep(3)
 else:raise RuntimeError('SSH readiness failed')
 result=ssh(s,'nvidia-smi --query-gpu=name --format=csv,noheader',capture_output=True,text=True,timeout=15)
 if result.returncode or result.stdout.strip()!='NVIDIA H200':raise ValueError('H200 identity required')
 write(root/'GPU_IDENTITY.json',{'pod_id':s['pod_id'],'gpu_type':'H200','nvidia_smi':result.stdout.strip(),'verified_utc':time.time()})
 remote('test ! -e /workspace/e96-sampling && mkdir /workspace/e96-sampling')
 a=s['ssh'];scp=['scp','-q','-i',str(P.home()/'.ssh/id_ed25519_runpod'),'-P',str(a['publicPort'])];dest='root@'+a['ip']+':/workspace/e96-sampling/'
 run(scp+[str(root/n) for n in ['sampling_code.tar.gz','inputs.tar.gz','sampling_stage.py','assets.json','ASSIGNMENT.json']]+[dest])
 remote('cd /workspace/e96-sampling && tar -xzf sampling_code.tar.gz && mkdir inputs && tar -xzf inputs.tar.gz -C inputs && /weights/venv-kernels/bin/python -u sampling_stage.py > stage.log 2>&1 && git clone -q https://github.com/agu18dec/olens_draft.git official-ar && git -C official-ar checkout -q a32590085a6070d75f950155d3c2b3db3eec97ef')
 token=None
 for line in (P.home()/'.config/mats/secrets.env').read_text().splitlines():
  if line.removeprefix('export ').startswith('HF_TOKEN='):token=shlex.split(line.split('=',1)[1])[0]
 if not token:raise RuntimeError('native credential unavailable for pinned whitener')
 req=urllib.request.Request('https://huggingface.co/datasets/agu18dec/local-workspace/resolve/main/ckpts/ar/ptag/whiteners/whitening_iolens_pooled_L44.safetensors',headers={'Authorization':'Bearer '+token},method='HEAD')
 with urllib.request.urlopen(req,timeout=45) as response:url=response.url
 code="import sys,urllib.request,hashlib,pathlib; data=urllib.request.urlopen(sys.stdin.read(),timeout=120).read(); assert hashlib.sha256(data).hexdigest()=='178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a'; pathlib.Path('/workspace/e96-sampling/whitener.pt').write_bytes(data)"
 remote('/weights/venv-kernels/bin/python -c '+shlex.quote(code),input=url,text=True)
 args='--inputs inputs --assignment ASSIGNMENT.json --assets assets.json --official official-ar --whitener whitener.pt --out out --source-seal SOURCE_SEAL.json'
 prefix='cd /workspace/e96-sampling && export PYTHONPATH=/workspace/e96-sampling:/workspace/e96-sampling/official-ar/src OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 && '
 remote(prefix+'/weights/venv-kernels/bin/python -m projects.g_agreement.e96.sample '+args+' --preflight-only >> stage.log 2>&1')
 job="echo $$ > job.pid; exec /weights/venv-kernels/bin/python -u -m projects.g_agreement.e96.sample "+args
 shell="cd /workspace/e96-sampling\nexport PYTHONPATH=/workspace/e96-sampling:/workspace/e96-sampling/official-ar/src OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8\nnohup bash -c "+shlex.quote(job)+" > job.log 2>&1 < /dev/null &\necho $! > detached.pid\n"
 remote('bash -c '+shlex.quote(shell))
 write(root/'WORKER_STARTED.json',{'pod_id':s['pod_id'],'started_epoch':time.time(),'source_archive_sha256':sha(root/'sampling_code.tar.gz'),'original_created_epoch':s['created_epoch'],'worker_deadline_epoch':s['created_epoch']+13920,'replacement_number':1})
except BaseException as e:
 write(root/'STAGING_ERROR.json',{'error_type':type(e).__name__,'error':str(e),'epoch':time.time()});raise
finally:log.close()
