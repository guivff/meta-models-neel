"""User-authorized X1 pinned staging; no allocation, guard retirement, or science."""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from projects.g_agreement.r_bench import remainder_x1 as D
from projects.g_agreement.r_bench import remainder_x1_launch as G
from projects.g_agreement.r_bench import remainder_cold_setup as C

STAGING_CAP=1200


def estimate(missing_bytes,rate,observed_seconds):
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (missing_bytes,rate,observed_seconds)):
        raise ValueError('Finite measured staging inputs required')
    if missing_bytes<0 or rate<=0 or observed_seconds<30:
        raise ValueError('Need nonnegative missing bytes and observed throughput over at least30 seconds')
    seconds=math.ceil(1.5*missing_bytes/rate+180)
    return {'missing_bytes':missing_bytes,'observed_bytes_per_second':rate,'observed_seconds':observed_seconds,
            'transfer_safety_factor':1.5,'runtime_allowance_seconds':180,'estimated_seconds':seconds,
            'within_20_minutes':seconds<=STAGING_CAP}


def validate_estimate(record,pod,now):
    expected=estimate(record['missing_bytes'],record['observed_bytes_per_second'],record['observed_seconds'])
    if any(record.get(k)!=v for k,v in expected.items()):raise ValueError('Staging estimate calculation differs')
    if record.get('pod')!=pod or not record.get('measurement_source') or not 0<=now-record.get('measured_epoch',0)<=3600:
        raise ValueError('Fresh own-pod measured staging estimate required')
    if not expected['within_20_minutes']:raise ValueError('Estimated staging exceeds20 minutes: report before starting')
    return expected


def requirements():
    # Exact previously pinned R4 asset list is also the X1 target+four-reader set.
    return C.assets('r4')


def download(run,pod):
    check=G.live_check(pod,run);check();G.check_registration(run,D.read(D.OUT/'pilot_plan.json'))
    stamp=D.read(run/'staging_status.json')
    if stamp.get('pod')!=pod or time.time()>=stamp['deadline_epoch']:raise ValueError('Staging expired')
    from huggingface_hub import snapshot_download
    for asset in requirements():
        check()
        if time.time()>=stamp['deadline_epoch']:raise ValueError('Staging expired')
        print('Pinned asset '+asset['repo']+' @ '+asset['revision'],flush=True)
        snapshot_download(repo_id=asset['repo'],revision=asset['revision'],allow_patterns=asset['patterns'],max_workers=4)


def run(pod,run):
    run=Path(run);check=G.live_check(pod,run);check();G.check_registration(run,D.read(D.OUT/'pilot_plan.json'))
    proposal=D.read(run/'staging_estimate.json');validate_estimate(proposal,pod,time.time())
    if (run/'staging_status.json').exists():raise ValueError('Staging already attempted; no implicit retry/reset')
    b=D.read(run/'booking.json');start=time.time();deadline=min(start+STAGING_CAP,b['deadline_epoch']-G.pull_reserve(run,b))
    if deadline-start<proposal['estimated_seconds']:raise ValueError('Estimated staging does not fit segment before pull reserve')
    runtime=C.require_runtime()
    if shutil.disk_usage(run).free<proposal['missing_bytes']+5_000_000_000:raise ValueError('Insufficient disk for missing assets plus5GB reserve')
    status={'pod':pod,'started_epoch':start,'deadline_epoch':deadline,'estimated_seconds':proposal['estimated_seconds'],
            'status':'RUNNING','runtime':runtime,'phases':[],**D.provenance(pod)}
    D.save(run/'staging_status.json',status)
    (run/'torch_constraint.txt').write_text('torch=='+runtime['torch']+'\n')
    python=str(run/'venv/bin/python')
    commands=[('venv',[sys.executable,'-m','venv','--system-site-packages',str(run/'venv')]),
              ('dependencies',[python,'-m','pip','install','--disable-pip-version-check','--no-input','--constraint',str(run/'torch_constraint.txt'),*C.PINS]),
              ('assets',[python,'-m','projects.g_agreement.r_bench.remainder_x1_stage','download','--pod',pod,'--run-dir',str(run)])]
    env=os.environ.copy()
    for key in list(env):
        if any(s in key.upper() for s in ('TOKEN','API_KEY','SECRET','PASSWORD')):env.pop(key)
    env.update(HF_HOME='/workspace/hf_cache',HF_HUB_CACHE='/workspace/hf_cache/hub',HF_HUB_OFFLINE='0',TRANSFORMERS_OFFLINE='0',PYTHONUNBUFFERED='1')
    try:
        for name,cmd in commands:
            check();left=deadline-time.time()
            if left<=0:raise TimeoutError('Staging cap reached')
            entry={'phase':name,'started_epoch':time.time()};status['phases'].append(entry);D.save(run/'staging_status.json',status)
            proc=subprocess.Popen(cmd,start_new_session=True,env=env)
            try:
                while proc.poll() is None:
                    check();left=deadline-time.time()
                    if left<=0:raise TimeoutError('Staging cap reached')
                    try:proc.wait(timeout=min(15,left))
                    except subprocess.TimeoutExpired:print(json.dumps({'staging_phase':name,'elapsed_seconds':time.time()-start}),flush=True)
                if proc.returncode:raise subprocess.CalledProcessError(proc.returncode,cmd)
            finally:
                if proc.poll() is None:C.terminate(proc)
            entry['ended_epoch']=time.time();entry['exit_code']=proc.returncode
        status['status']='PASS';status['python']=python
    except BaseException as exc:
        status['status']='FAILED';status['error_type']=type(exc).__name__
        raise
    finally:
        status['ended_epoch']=time.time();D.save(run/'staging_status.json',status)
    return status


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['run','download']);p.add_argument('--pod',required=True);p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
    if a.action=='run':print(json.dumps(run(a.pod,a.run_dir)))
    else:download(a.run_dir,a.pod)

if __name__=='__main__':main()
