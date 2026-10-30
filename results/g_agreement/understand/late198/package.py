"""Bind a frozen public bank, forecast, exact-archive preflight, then emit READY."""
import argparse
import math
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
import numpy as np
from contract import *
from worker import initial_work

def source_archive(destination):
    digest_value=sha(HERE/'SOURCE_SEAL.json')
    verify(HERE,'SOURCE_SEAL.json',digest_value)
    names=set(read(HERE/'DEPENDENCIES.json'))
    names.update(str((HERE/name).relative_to(ROOT)) for name in read(HERE/'SOURCE_SEAL.json')['files'])
    names.add(str((HERE/'SOURCE_SEAL.json').relative_to(ROOT)))
    with tarfile.open(destination,'w:gz') as archive:
        for name in sorted(names):archive.add(ROOT/name,arcname=name,recursive=False)
    return digest_value

def forecast(plan,items,scores,downstream,limits):
    work=initial_work(plan['experiment'],items,scores,downstream)
    seeds=limits['seed_seconds_per_batch']
    require(set(work)<=set(seeds) and all(math.isfinite(seeds[k]) and seeds[k]>=0 for k in work),'forecast seed coverage')
    wait=limits['cpu_wait_allowance_seconds']
    require(math.isfinite(wait) and wait>=0,'CPU wait allowance')
    seconds=sum(n*seeds[p] for p,n in work.items())+wait+60
    cap=math.ceil(1.25*seconds)
    return dict(status='PLANNING_FORECAST_FROM_SAVED_TIMINGS',jobs=work,forecast_seconds=seconds,
                recommended_cap_seconds=cap,margin=1.25,seed_seconds_per_batch=seeds,
                cpu_wait_allowance_seconds=wait,retrieval_reserve_seconds=60,
                synthetic_warmups='discarded and excluded from batch estimator; charged to absolute stage clock',
                fits_request=cap<=limits['cap_seconds'],new_GPU_measurement=False)

def exact_preflight(source,inputs,source_sha,input_sha,limits,items_count):
    with tempfile.TemporaryDirectory(prefix='late198-exact-') as tmp:
        root=Path(tmp)
        for archive_name,dest in ((source,'source'),(inputs,'data')):
            (root/dest).mkdir()
            with tarfile.open(archive_name) as archive:archive.extractall(root/dest,filter='data')
        start=time.time()
        assignment=dict(experiment=limits['experiment'],pod_id='CPU_STUB',gpu_count=1,
            cap_seconds=limits['cap_seconds'],prior_seconds=0,pod_created_epoch=start,custody_start_epoch=start,
            absolute_deadline_epoch=start+limits['cap_seconds'],daily_budget_verified=True,projected_daily_USD=260)
        write(root/'assignment.json',assignment);write(root/'assets.json',{})
        command=[sys.executable,str(root/'source'/HERE.relative_to(ROOT)/'worker.py'),
            '--inputs',str(root/'data/inputs'),'--assets',str(root/'assets.json'),'--assignment',str(root/'assignment.json'),
            '--out',str(root/'out'),'--releases',str(root/'releases'),'--source-sha',source_sha,'--input-sha',input_sha,'--dry-run']
        result=subprocess.run(command,capture_output=True,text=True)
        require(result.returncode==0,result.stderr)
        proof=read(root/'out/DRY_RUN.json');require(proof['status']=='COMPLETE','all stages must fit CPU dry run')
        require(read(root/'out/OUTPUT_SEAL.json')['synthetic'] is True,'stub outputs labelled synthetic')
        # Exercise fail-closed exact-input guards with model loading stubbed.
        negative=[]
        assignment['cap_seconds']+=1;assignment['absolute_deadline_epoch']+=1
        write(root/'assignment.json',assignment,replace=True)
        command[command.index('--out')+1]=str(root/'overcap')
        r=subprocess.run(command,capture_output=True,text=True)
        require(r.returncode!=0 and 'request cap' in r.stderr,'overcap rejected');negative.append('overcap')
        assignment['cap_seconds']-=1;assignment['absolute_deadline_epoch']-=1
        write(root/'assignment.json',assignment,replace=True)
        write(root/'data/inputs/PRIVATE_TARGETS.json',{'synthetic':True})
        r=subprocess.run(command,capture_output=True,text=True)
        require(r.returncode!=0 and 'extra private files' in r.stderr,'extra file rejected');negative.append('extra_private_file')
        (root/'data/inputs/PRIVATE_TARGETS.json').unlink();(root/'data/inputs/items.json').unlink()
        r=subprocess.run(command,capture_output=True,text=True)
        require(r.returncode!=0,'missing sealed input rejected');negative.append('missing_input')
        return dict(status='PASS',experiment=limits['experiment'],items=items_count,GPU_calls=0,
                    source_archive_sha256=sha(source),input_archive_sha256=sha(inputs),
                    all_stages_executed=True,negative_cases=negative)

def build(bank,bank_sha,stage_request,destination,synthetic=False):
    bank=Path(bank);destination=Path(destination)
    verify(bank,'BANK_SEAL.json',bank_sha)
    plan=read(bank/'PLAN.json');items=read(bank/'items.json')
    scores=read(bank/'SCORE_ITEMS.json');downstream=read(bank/'DOWNSTREAM.json')
    exp=validate_plan(plan,items,scores,downstream)
    # PLAN.bank_seal is the upstream owner's freeze, not this bank wrapper (no circular seal).
    limits=read(stage_request);require(limits['experiment']==exp,'stage experiment')
    require(limits['cap_seconds']<=limits['cumulative_cap_seconds'],'stage cumulative cap')
    if exp=='E83' and not synthetic:
        from collections import Counter
        counts=Counter(x['feature'] for x in items)
        require(len(counts)==8 and set(counts.values())=={84} and len(items)==672,'frozen eight rows x84')
    f=forecast(plan,items,scores,downstream,limits)
    require(f['fits_request'],'forecast exceeds request; commit HOLD_CAP, do not silently enlarge cap')
    destination.mkdir(parents=True,exist_ok=False);inp=destination/'inputs';inp.mkdir()
    for name in ('PLAN.json','items.json','SCORE_ITEMS.json','DOWNSTREAM.json'):
        shutil.copyfile(bank/name,inp/name)
    if exp=='E83':shutil.copyfile(bank/'acts44.npy',inp/'acts44.npy')
    limits=dict(limits,status='READY');write(inp/'STAGE_REQUEST.json',limits)
    input_sha=seal(inp,'INPUT_SEAL.json',experiment=exp,bank_wrapper_sha256=bank_sha,synthetic=synthetic)
    source=destination/'source.tar.gz';input_archive=destination/'inputs.tar.gz'
    source_sha=source_archive(source)
    with tarfile.open(input_archive,'w:gz') as archive:archive.add(inp,arcname='inputs')
    proof=exact_preflight(source,input_archive,source_sha,input_sha,limits,len(items))
    write(destination/'EXACT_PREFLIGHT.json',proof);write(destination/'FORECAST.json',f)
    request=dict(experiment=exp,status='SYNTHETIC_TEST_ONLY' if synthetic else 'READY',launch_allowed=not synthetic,
        priority_after=['E79','E80'],source_archive=str(source.resolve()),source_archive_sha256=sha(source),
        source_seal_sha256=source_sha,input_archive=str(input_archive.resolve()),input_archive_sha256=sha(input_archive),
        input_seal_sha256=input_sha,cap_seconds=limits['cap_seconds'],cumulative_cap_seconds=limits['cumulative_cap_seconds'],
        forecast=f,exact_preflight=proof,labels_on_pod=False,integrator_owns_launch=True,
        argv=['python',str(Path('/workspace')/HERE.relative_to(ROOT)/'worker.py'),
              '--inputs',f'/workspace/{exp.lower()}/inputs','--assets','/workspace/e56/assets.json',
              '--assignment',f'/workspace/{exp.lower()}/assignment.json','--out',f'/workspace/{exp.lower()}/out',
              '--releases',f'/workspace/{exp.lower()}/releases','--source-sha',source_sha,'--input-sha',input_sha])
    write(destination/'REQUEST.json',request)
    return request

def main():
    p=argparse.ArgumentParser()
    for name in ('bank','stage-request','destination'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--bank-sha',required=True)
    a=p.parse_args();build(a.bank,a.bank_sha,a.stage_request,a.destination)

if __name__=='__main__':main()
