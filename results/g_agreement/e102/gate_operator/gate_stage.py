"""One-shot E102 gate staging; no production trainer, capture or eval commands.

Copied with gate_custody.py to a non-Documents service directory. Only the sealed
worker/input archive, pinned model manifest and gate admission reach the pod.
"""
import datetime,json,pathlib,shlex,subprocess,sys,time
from gate_custody import owned,ssh,sha,write
P=pathlib.Path
BASE='/weights/hf_cache/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
ADAPTER='/weights/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600'

def stage(root):
    state=json.loads((root/'STATE.json').read_text());manifest=json.loads((root/'STAGING_PLAN.json').read_text())
    if manifest['experiment']!='E102_GATE' or manifest['training_admitted'] is not False:raise ValueError('gate-only manifest')
    for n,h in manifest['files'].items():
        if sha(root/n)!=h:raise ValueError('exact gate payload changed')
    if (root/'STAGE_CLAIM.json').exists():raise ValueError('gate staging never automatically repeated')
    write(root/'STAGE_CLAIM.json',{'created_epoch':state['created_epoch'],'started_epoch':time.time(),'pod_id':state['pod_id']})
    deadline=state['created_epoch']+600
    log=(root/'STAGING.log').open('a')
    def budget():
        left=deadline-time.time()
        if left<=0:raise TimeoutError('original staging allowance exhausted')
        return max(1,min(120,left))
    def remote(cmd,**kw):
        result=ssh(state,cmd,stdout=log,stderr=log,timeout=budget(),**kw)
        if result.returncode:raise RuntimeError('gate staging remote command failed')
    try:
        while time.time()<deadline:
            p=owned(state)
            if p and p.get('runtime'):
                state['ssh']=next(x for x in p['runtime']['ports'] if x['privatePort']==22 and x['isIpPublic']);break
            time.sleep(5)
        else:raise RuntimeError('gate runtime unavailable')
        for _ in range(60):
            if ssh(state,'true',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=budget()).returncode==0:break
            time.sleep(3)
        else:raise RuntimeError('SSH unavailable')
        identity=ssh(state,'nvidia-smi --query-gpu=name --format=csv,noheader',capture_output=True,text=True,timeout=budget())
        names=identity.stdout.strip().splitlines()
        if identity.returncode or len(names)!=1 or state['gpu_type'] not in names[0]:raise ValueError('admitted single GPU type mismatch')
        write(root/'GPU_IDENTITY.json',{'pod_id':state['pod_id'],'gpu_type':state['gpu_type'],'nvidia_smi':names[0],'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        remote('test ! -e /workspace/e102-gate && mkdir /workspace/e102-gate')
        a=state['ssh'];scp=['scp','-q','-i',str(P.home()/'.ssh/id_ed25519_runpod'),'-P',str(a['publicPort'])]
        result=subprocess.run(scp+[str(root/n) for n in ['gate-source-inputs.tar.gz','ADMISSION.json','ASSETS.json','SOURCE_SEAL.json']]+['root@'+a['ip']+':/workspace/e102-gate/'],stdout=log,stderr=log,timeout=budget())
        if result.returncode:raise RuntimeError('allowlisted staging transfer failed')
        remote('cd /workspace/e102-gate && tar -xzf gate-source-inputs.tar.gz')
        # Check every archived byte before imports/model work; never stage a checkout.
        check="import json,hashlib,pathlib; r=pathlib.Path('/workspace/e102-gate'); s=json.loads((r/'SOURCE_SEAL.json').read_text()); assert all(hashlib.sha256((r/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in s['files'])"
        prefix='cd /workspace/e102-gate && export PYTHONPATH=/workspace/e102-gate:/workspace/e102-gate/external/mats-nla-workspace/src OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_CACHE_PATH=/workspace/e102-gate/cuda_cache && '
        remote(prefix+'/weights/venv-kernels/bin/python -c '+shlex.quote(check)+' > stage.log 2>&1')
        imports='import torch,peft,transformers; from mats.readers.olens import OracleLens; from mats.readers.nla import Sampling; assert torch.cuda.is_available() and torch.cuda.device_count()==1; print(torch.__version__,transformers.__version__,torch.cuda.get_device_name(0))'
        remote(prefix+'/weights/venv-kernels/bin/python -c '+shlex.quote(imports)+' >> stage.log 2>&1')
        args='--inputs cache/g_agreement/e102/gate_inputs --out out --model '+BASE+' --adapter '+ADAPTER+' --admission ADMISSION.json --asset-manifest ASSETS.json'
        # A terminal marker also exists for import/load failures before out/ exists.
        marker="import sys,json,pathlib; pathlib.Path('WORKER_EXIT.json').write_text(json.dumps({'exit_code':int(sys.argv[1]),'production_training':False}))"
        job='/weights/venv-kernels/bin/python -u -m projects.g_agreement.e102.gate '+args+'; status=$?; /weights/venv-kernels/bin/python -c '+shlex.quote(marker)+' "$status"; exit "$status"'
        script=root/'RUN_GATE.sh';script.write_text('#!/bin/bash\nset -u\ncd /workspace/e102-gate\nexport PYTHONPATH=/workspace/e102-gate:/workspace/e102-gate/external/mats-nla-workspace/src OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_CACHE_PATH=/workspace/e102-gate/cuda_cache\necho $$ > job.pid\n'+job+'\n')
        result=subprocess.run(scp+[str(script),'root@'+a['ip']+':/workspace/e102-gate/RUN_GATE.sh'],stdout=log,stderr=log,timeout=budget())
        if result.returncode:raise RuntimeError('gate command staging failed')
        write(root/'WORKER_COMMAND_CLAIM.json',{'pod_id':state['pod_id'],'submitted_epoch':time.time(),'script_sha256':sha(script),'automatic_retry':False})
        remote('cd /workspace/e102-gate && nohup bash RUN_GATE.sh > job.log 2>&1 < /dev/null &')
        write(root/'WORKER_STARTED.json',{'pod_id':state['pod_id'],'started_epoch':time.time(),'original_created_epoch':state['created_epoch'],'source_archive_sha256':sha(root/'gate-source-inputs.tar.gz'),'gate_only':True})
    except BaseException as exc:
        write(root/'STAGE_ERROR.json',{'type':type(exc).__name__,'error':str(exc),'epoch':time.time(),'gate_only':True})
        if state.get('ssh'):
            try:remote("cd /workspace/e102-gate && printf '%s' '{\"stage_failed\":true}' > STAGE_ERROR.json")
            except Exception:pass
        raise
    finally:log.close()

if __name__=='__main__':stage(P(sys.argv[1]))
