"""One-shot allowlisted E106 staging; no automatic worker retry or clock reset."""
import json,pathlib,subprocess,time,shlex,os,sys
from custody import owned,ssh,write,sha
P=pathlib.Path

def stage(root):
 s=json.loads((root/'STATE.json').read_text());pre=json.loads((root/'PREFLIGHT.json').read_text())
 for n,h in pre['files'].items():
  if sha(root/n)!=h:raise ValueError('staging payload changed '+n)
 with (root/'STAGE_CLAIM.json').open('x') as f:json.dump({'pod_id':s['pod_id'],'created_epoch':s['created_epoch'],'started_epoch':time.time()},f)
 log=(root/'STAGING.log').open('a');stage_end=min(s['created_epoch']+900,s['deadline_epoch']-300)
 def budget():
  left=stage_end-time.time()
  if left<=0:raise TimeoutError('original staging allowance exhausted before load')
  return min(120,left)
 def remote(cmd,**kw):
  x=ssh(s,cmd,stdout=log,stderr=log,timeout=budget(),**kw)
  if x.returncode:raise RuntimeError('remote staging command failed')
 try:
  while time.time()<stage_end:
   p=owned(s)
   if p and p.get('runtime'):
    s['ssh']=next(x for x in p['runtime']['ports'] if x['privatePort']==22 and x['isIpPublic']);break
   time.sleep(5)
  else:raise RuntimeError('no runtime before staging reserve')
  for _ in range(60):
   if ssh(s,'true',stdout=log,stderr=log,timeout=budget()).returncode==0:break
   time.sleep(3)
  else:raise RuntimeError('SSH unavailable')
  identity=ssh(s,'nvidia-smi --query-gpu=name --format=csv,noheader',capture_output=True,text=True,timeout=budget())
  if identity.returncode or identity.stdout.strip()!='NVIDIA H200':raise ValueError('admitted H200 identity required')
  write(root/'GPU_IDENTITY.json',{'pod_id':s['pod_id'],'gpu_type':'H200','nvidia_smi':identity.stdout.strip(),'epoch':time.time()})
  remote('test ! -e /workspace/e106-run && mkdir /workspace/e106-run')
  a=s['ssh'];scp=['scp','-q','-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-i',str(P.home()/'.ssh/id_ed25519_runpod'),'-P',str(a['publicPort'])];dest='root@'+a['ip']+':/workspace/e106-run/'
  subprocess.run(scp+[str(root/n) for n in ['source.tar.gz','inputs.tar.gz','ASSETS.json','ORACLE_MANIFEST.json','NLA_MANIFEST.json','ADMISSION.json']]+[dest],stdout=log,stderr=log,timeout=budget(),check=True)
  check="import pathlib,hashlib;assert hashlib.sha256(pathlib.Path('/workspace/e106-run/source.tar.gz').read_bytes()).hexdigest()=="+repr(pre['files']['source.tar.gz'])+";assert hashlib.sha256(pathlib.Path('/workspace/e106-run/inputs.tar.gz').read_bytes()).hexdigest()=="+repr(pre['files']['inputs.tar.gz'])
  remote('/weights/venv-kernels/bin/python -c '+shlex.quote(check))
  remote('cd /workspace/e106-run && tar -xzf source.tar.gz && tar -xzf inputs.tar.gz')
  prefix='cd /workspace/e106-run && export PYTHONPATH=/workspace/e106-run:/workspace/e106-run/external/mats-nla-workspace/src OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_CACHE_PATH=/workspace/e106-run/cuda_cache && '
  remote(prefix+'/weights/venv-kernels/bin/python -c '+shlex.quote('import torch,peft,transformers;from projects.g_agreement.e106 import worker,runtime;from mats.readers.nla import load_nla;print("CPU_IMPORT_PASS",torch.__version__,peft.__version__,transformers.__version__)')+' > stage.log 2>&1')
  admission=json.loads((root/'ADMISSION.json').read_text());write(root/'ADMISSION_PRE_STAGE.json',admission);admission['measured_e106_staging_seconds']=[time.time()-s['created_epoch']];write(root/'ADMISSION.json',admission)
  subprocess.run(scp+[str(root/'ADMISSION.json'),dest],stdout=log,stderr=log,timeout=budget(),check=True)
  args='--phase '+s['phase']+' --inputs cache/g_agreement/e106/inputs_v1 --assets ASSETS.json --admission ADMISSION.json --out out'
  marker='import sys,json,pathlib;pathlib.Path("WORKER_EXIT.json").write_text(json.dumps({"exit_code":int(sys.argv[1])}))'
  job='/weights/venv-kernels/bin/python -u -m projects.g_agreement.e106.worker '+args+'; rc=$?; /weights/venv-kernels/bin/python -c '+shlex.quote(marker)+' "$rc"; exit "$rc"'
  script=root/'RUN.sh';script.write_text('#!/bin/bash\ncd /workspace/e106-run\nexport PYTHONPATH=/workspace/e106-run:/workspace/e106-run/external/mats-nla-workspace/src OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_CACHE_PATH=/workspace/e106-run/cuda_cache\necho $$ > job.pid\n'+job+'\n')
  subprocess.run(scp+[str(script),dest],stdout=log,stderr=log,timeout=budget(),check=True)
  write(root/'WORKER_COMMAND_CLAIM.json',{'pod_id':s['pod_id'],'submitted_epoch':time.time(),'script_sha256':sha(script),'worker_attempts':1})
  remote('bash -c '+shlex.quote('cd /workspace/e106-run\nnohup bash RUN.sh > job.log 2>&1 < /dev/null &\necho $! > detached.pid\n'))
  write(root/'WORKER_STARTED.json',{'pod_id':s['pod_id'],'phase':s['phase'],'started_epoch':time.time(),'original_created_epoch':s['created_epoch'],'original_deadline_epoch':s['deadline_epoch'],'measured_staging_seconds':admission['measured_e106_staging_seconds'][0]})
 except BaseException as e:write(root/'STAGE_ERROR.json',{'error_type':type(e).__name__,'error':str(e),'epoch':time.time(),'preload':True});raise
 finally:log.close()
if __name__=='__main__':stage(P(sys.argv[1]))
