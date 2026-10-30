"""Guard-bound cold setup for isolated remainder pods; offline preparation is safe.

Only explicit `run`/`download` on the booked pod installs/downloads. This module
never allocates, contacts the pod API, copies credentials, opens SSH, or stops a pod.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
CAPS={'r2':1200,'r3':1200,'r4':3600,'r5':1800,'r6':1200}
RESERVE=300
MODULE='projects.g_agreement.r_bench.remainder_cold_setup'
PINS=('transformers==5.18.0','peft==0.21.2','accelerate==1.15.0','safetensors==0.8.0',
      'huggingface_hub==1.33.0','tokenizers==0.23.2','numpy==2.5.3','scipy==1.18.1',
      'scikit-learn==1.9.1','pandas==3.0.6','PyYAML==6.0.3')


def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n');temporary.replace(path)


def assets(experiment):
    from projects.g_agreement.core import config as c
    rows=[{'repo':c.TARGET_MODEL_ID,'revision':c.TARGET_MODEL_SHA,
           'patterns':['*.json','*.safetensors','*.model','merges.txt','vocab.json','chat_template.jinja','tokenizer.*']},
          {'repo':c.OLENS_REPO,'revision':c.OLENS_SHA,'patterns':[c.OLENS_SUBFOLDER+'/*']}]
    if experiment!='r5':
        rows.append({'repo':c.NLA_REPO,'revision':c.NLA_SHA,
                     'patterns':[c.NLA_BASE_SUBFOLDER+'/*',c.NLA_ADAPTER_SUBFOLDER+'/*',c.NLA_META_FILE]})
    if experiment=='r4':
        rows.extend([{'repo':c.JLENS_REPO,'revision':c.JLENS_SHA,'patterns':[c.JLENS_FILE]},
                     {'repo':c.SKIPLENS_REPOS['a'],'revision':c.SKIPLENS_SHAS['a'],'patterns':list(c.SKIPLENS_FILES)}])
    return rows


def guard(experiment,pod,run,expected=None):
    own=dict(x.split(b'=',1) for x in Path('/proc/1/environ').read_bytes().split(b'\0') if b'=' in x)
    if own.get(b'RUNPOD_POD_ID',b'').decode()!=pod: raise ValueError('POD ID MISMATCH')
    raw=(run/'guard.json').read_bytes();record=json.loads(raw)
    if expected is not None and raw!=expected: raise ValueError('Immutable guard changed')
    if record.get('pod')!=pod or record.get('experiment')!=experiment: raise ValueError('Guard identity mismatch')
    start,end=record.get('started_epoch'),record.get('deadline_epoch')
    if (any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in (start,end))
            or not 0<end-start<=CAPS[experiment] or start>time.time()): raise ValueError('Invalid original deadline')
    if end-time.time()<=RESERVE: raise RuntimeError('Pull reserve reached')
    if not (run/'ARMED').exists(): raise ValueError('Shared guards not armed')
    for name in ('watchdog','hardstop'):
        text=(run/f'{name}.log').read_text()
        if 'armed:' not in text or pod not in text: raise ValueError(f'{name} not armed for this pod')
        os.kill(int((run/f'{name}.pid').read_text()),0)
    return record,raw


def disk_preflight(experiment,path,usage=None):
    usage=shutil.disk_usage(path) if usage is None else usage
    # Provider's logical 200GB allocation is checked separately in its allocation receipt.
    # Here check the filesystem actually has room for exact assets plus output/runtime reserve.
    minimum=75_000_000_000 if experiment=='r5' else 140_000_000_000
    if usage.total<190_000_000_000: raise ValueError('Expected 200GB-class container filesystem')
    if usage.free<minimum: raise ValueError(f'Insufficient cold disk: need {minimum} free bytes')
    return {'total_bytes':usage.total,'free_bytes':usage.free,'minimum_free_bytes':minimum}


def require_runtime(version=None,torch_version=None,cuda=None):
    version=sys.version_info if version is None else version
    if tuple(version[:2])<(3,12): raise ValueError('Pinned numpy/scipy require Python >=3.12')
    if torch_version is None:
        import torch
        torch_version=torch.__version__;cuda=torch.version.cuda
    if not re.match(r'^2\.8\.\d+(?:\+.*)?$',torch_version) or not cuda:
        raise ValueError('Expected image CUDA torch 2.8; do not silently replace torch')
    return {'python':sys.version,'torch':torch_version,'cuda':cuda,'pins':list(PINS)}


def descendant_groups(parent,proc_root=Path('/proc')):
    rows={}
    for path in proc_root.iterdir():
        if not path.name.isdigit(): continue
        try:
            fields=(path/'stat').read_text().rsplit(')',1)[1].split()
            rows[int(path.name)]=(int(fields[1]),int(fields[2]))
        except (OSError,ValueError,IndexError): continue
    descendants={parent}
    while True:
        new={pid for pid,(ppid,_group) in rows.items() if ppid in descendants}
        if new<=descendants: break
        descendants|=new
    return {group for pid,(_parent,group) in rows.items() if pid in descendants and group>1}


def terminate(proc):
    groups=descendant_groups(proc.pid)|{proc.pid}
    groups.discard(os.getpgrp())
    for group in groups:
        try: os.killpg(group,signal.SIGTERM)
        except ProcessLookupError: pass
    try: proc.wait(timeout=10)
    except subprocess.TimeoutExpired: pass
    for group in groups:
        try: os.killpg(group,signal.SIGKILL)
        except ProcessLookupError: pass
    proc.wait()


def interrupted(signum,_frame):
    raise RuntimeError(f'Cold setup interrupted by signal {signum}')


def bounded(command,experiment,pod,run,frozen,deadline,env=None):
    guard(experiment,pod,run,frozen)
    remaining=deadline-time.time()-RESERVE
    if remaining<=0: raise RuntimeError('Pull reserve reached before phase')
    proc=subprocess.Popen(command,cwd=ROOT,env=env,start_new_session=True)
    previous_bytes=0
    cache=Path((env or os.environ).get('HF_HUB_CACHE',str(Path((env or os.environ).get('HF_HOME','/workspace/hf_cache'))/'hub')))
    try:
        while True:
            guard(experiment,pod,run,frozen)
            left=deadline-time.time()-RESERVE
            if left<=0: raise RuntimeError('Immutable pull-reserve deadline reached')
            try: code=proc.wait(timeout=min(15,left));break
            except subprocess.TimeoutExpired:
                if 'download' in command and cache.exists():
                    size=sum(p.stat().st_size for p in cache.rglob('*') if p.is_file() and not p.is_symlink())
                    if size>previous_bytes:
                        print(f'Pinned download cache grew to {size} bytes',flush=True)
                        previous_bytes=size
        if code: raise RuntimeError(f'Phase failed with exit {code}')
    finally:
        if proc.poll() is None: terminate(proc)


def download(experiment,pod,run):
    # Run as a bounded child of the cold chain; direct invocation still requires live guards.
    record,frozen=guard(experiment,pod,run)
    from huggingface_hub import snapshot_download
    for asset in assets(experiment):
        guard(experiment,pod,run,frozen)
        print('Pinned asset '+asset['repo']+' @ '+asset['revision'],flush=True)
        snapshot_download(repo_id=asset['repo'],revision=asset['revision'],
                          allow_patterns=asset['patterns'],max_workers=4)
    write(run/'cold_assets.json',{'experiment':experiment,'pod':pod,'deadline_epoch':record['deadline_epoch'],
                                 'hf_home':os.environ.get('HF_HOME','/workspace/hf_cache'),
                                 'hf_hub_cache':os.environ.get('HF_HUB_CACHE',str(Path(os.environ.get('HF_HOME','/workspace/hf_cache'))/'hub')),
                                 'assets':assets(experiment),'completed_at':datetime.now(timezone.utc).isoformat()})


def phases(experiment,pod,run,python=sys.executable,setup_only=False):
    vpython=str(run/'venv/bin/python')
    commands=[('venv',[python,'-m','venv','--system-site-packages',str(run/'venv')]),
              ('dependencies',[vpython,'-m','pip','install','--disable-pip-version-check','--no-input',
                               '--constraint',str(run/'torch_constraint.txt'),*PINS]),
              ('assets',[vpython,'-m',MODULE,'download','--experiment',experiment,'--pod',pod,'--run-dir',str(run)])]
    if not setup_only:
        if experiment not in ('r4','r5'): raise ValueError('R2/R3/R6 use --setup-only then their dedicated chain')
        commands.append(('science',[vpython,'-m','projects.g_agreement.r_bench.remainder_deploy','execute',
                                    '--experiment',experiment,'--pod',pod,'--run-dir',str(run)]))
    return commands


def run(experiment,pod,run_dir,setup_only=False):
    if ROOT.resolve()!=(run_dir/'repo').resolve(): raise ValueError('Run from the isolated repo')
    record,frozen=guard(experiment,pod,run_dir)
    if (run_dir/'cold_status.json').exists(): raise ValueError('Refuse implicit cold-setup retry; preserve prior evidence')
    status={'experiment':experiment,'pod':pod,'deadline_epoch':record['deadline_epoch'],
            'started_epoch':time.time(),'state':'RUNNING','phases':[],'setup_only':setup_only}
    write(run_dir/'cold_status.json',status)
    previous_handlers={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
    for sig in previous_handlers: signal.signal(sig,interrupted)
    try:
        status['runtime']=require_runtime();status['disk']=disk_preflight(experiment,run_dir)
        # Image torch remains the installed system CUDA build, never a large resolver replacement.
        (run_dir/'torch_constraint.txt').write_text('torch=='+status['runtime']['torch']+'\n')
        environment=dict(os.environ)
        environment.update(PYTHONUNBUFFERED='1',PIP_DISABLE_PIP_VERSION_CHECK='1',
                           HF_HOME=os.environ.get('HF_HOME','/workspace/hf_cache'),
                           HF_HUB_OFFLINE='0',TRANSFORMERS_OFFLINE='0')
        status['hf_home']=environment['HF_HOME']
        status['hf_hub_cache']=environment.get('HF_HUB_CACHE',str(Path(environment['HF_HOME'])/'hub'))
        for name,command in phases(experiment,pod,run_dir,setup_only=setup_only):
            entry={'phase':name,'started_epoch':time.time()};status['phases'].append(entry)
            write(run_dir/'cold_status.json',status)
            print('COLD START '+name,flush=True)
            phase_env=dict(environment)
            phase_env.pop('RUNPOD_API_KEY',None)  # only the already-armed shared guards need stop authority
            if name!='assets': phase_env.pop('HF_TOKEN',None)
            if name=='science': phase_env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
            bounded(command,experiment,pod,run_dir,frozen,record['deadline_epoch'],phase_env)
            entry['finished_epoch']=time.time();entry['complete']=True
            if name=='dependencies':
                freeze_budget=min(20,record['deadline_epoch']-time.time()-RESERVE)
                if freeze_budget<=0: raise RuntimeError('Pull reserve reached before environment record')
                with (run_dir/'venv_freeze.txt').open('w') as stream:
                    subprocess.run([str(run_dir/'venv/bin/python'),'-m','pip','freeze'],stdout=stream,
                                   stderr=subprocess.DEVNULL,timeout=freeze_budget,check=True)
        status['state']='DONE';code=0
    except Exception as exc:
        status.update(state='FAILED',error_type=type(exc).__name__,error=str(exc));code=1
    for sig,handler in previous_handlers.items(): signal.signal(sig,handler)
    status['finished_epoch']=time.time();write(run_dir/'cold_status.json',status)
    marker='COLD_SETUP_DONE' if code==0 else 'COLD_SETUP_FAILED'
    (run_dir/marker).write_text(json.dumps(status)+'\n')
    destination=run_dir/'deliverables/operations';destination.mkdir(parents=True,exist_ok=True)
    for name in ('cold_status.json','cold_assets.json','venv_freeze.txt','torch_constraint.txt',marker):
        if (run_dir/name).is_file(): shutil.copy2(run_dir/name,destination/name)
    print(marker+'; no pod stop requested',flush=True)
    return code


def emit(experiment,pod,run_dir,setup_only=False):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',pod): raise ValueError('Invalid pod ID')
    if not str(run_dir).startswith(f'/workspace/remainder/{experiment}/') or '..' in run_dir.parts:
        raise ValueError('Invalid isolated run directory')
    command=['python3','-m',MODULE,'run','--experiment',experiment,'--pod',pod,'--run-dir',str(run_dir)]
    if setup_only: command.append('--setup-only')
    return '\n'.join(['#!/usr/bin/env bash','set -euo pipefail',
        f'REMAINDER_RUN_DIR={shlex.quote(str(run_dir))}',f'REMAINDER_BOOKED_POD={shlex.quote(pod)}',
        'OWN=$(tr "\\0" "\\n" < /proc/1/environ | sed -n "s/^RUNPOD_POD_ID=//p")',
        '[ "$OWN" = "$REMAINDER_BOOKED_POD" ] || { echo "POD ID MISMATCH"; exit 2; }',
        '[ -f /workspace/.env ] || { echo "Existing approved environment missing"; exit 2; }',
        'set -a; source /workspace/.env >/dev/null 2>&1; set +a',
        'cd "$REMAINDER_RUN_DIR/repo"','echo $$ > "$REMAINDER_RUN_DIR/job.pid"',
        '[ -s GIT_SHA ] || { echo "GIT_SHA missing"; exit 2; }',
        'export R_GIT_SHA="$(cat GIT_SHA)" PYTHONUNBUFFERED=1',
        'export PYTHONPATH="$REMAINDER_RUN_DIR/repo${PYTHONPATH:+:$PYTHONPATH}"',
        'exec '+shlex.join(command),''])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('plan','emit','run','download'))
    p.add_argument('--experiment',choices=CAPS,required=True)
    p.add_argument('--pod');p.add_argument('--run-dir',type=Path);p.add_argument('--setup-only',action='store_true')
    args=p.parse_args(argv)
    if args.action=='plan':
        print(json.dumps({'experiment':args.experiment,'assets':assets(args.experiment),
                          'pins':list(PINS),'cap_seconds':CAPS[args.experiment],'pull_reserve_seconds':RESERVE},indent=2));return 0
    if not args.pod or not args.run_dir: p.error('Explicit --pod and --run-dir required')
    if args.action=='emit': print(emit(args.experiment,args.pod,args.run_dir,args.setup_only),end='')
    elif args.action=='download': download(args.experiment,args.pod,args.run_dir)
    else: return run(args.experiment,args.pod,args.run_dir,args.setup_only)
    return 0

if __name__=='__main__': raise SystemExit(main())
