"""Offline R6/R3 payloads and immutable-deadline cold launch chain. Never allocates/stops."""
from __future__ import annotations
import argparse
import hashlib
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
MODULE='projects.g_agreement.r_bench.remainder_r6_deploy'
SCIENCE='projects.g_agreement.r_bench.remainder_r6'
RECOVERY='projects.g_agreement.r_bench.remainder_r6_recovery'
RESERVE=300
CAP=1200
DEFAULT_MANIFEST='cache/g_agreement/r/remainder/r6/recovery/full/selection_recovered.jsonl'
FULL_ID_SHA='62acff9c5546f5e522e3688643ca58e0775d48b65836f530bc4cc482763fbdc0'


def read(path):return json.loads(Path(path).read_text())


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.partial');tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');tmp.replace(path)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def relative(path):
    p=Path(path)
    if p.is_absolute() or '..' in p.parts:raise ValueError('Inputs must use repo-relative paths')
    return str(p)


def prerequisite(experiment,manifest=DEFAULT_MANIFEST,root=ROOT):
    """R3 must not pay for setup until R6's passed recovery and complete state tree exist."""
    if experiment!='r3':return
    mp=root/relative(manifest)
    if not mp.is_file():raise ValueError('R3 blocked: R6 recovered manifest unavailable before cold setup')
    rows=[json.loads(l) for l in mp.read_text().splitlines() if l.strip()]
    keys={(r['case'],r['pair_id'],r['arm']) for r in rows}
    if not rows or len(keys)!=len(rows):raise ValueError('R3 recovery manifest empty/duplicated')
    for row in rows:
        for ref in row['states'].values():
            for key in ('path','index_path'):
                if not (root/relative(ref[key])).is_file():raise ValueError('R3 blocked: recovered state/index absent')
            if ref.get('kind')=='r5_replay':
                p=root/relative(ref['recovery_receipt'])
                if not p.is_file() or sha(p)!=ref.get('recovery_receipt_sha'):raise ValueError('R3 blocked: recovery receipt absent/changed')
                rec=read(p)
                if rec.get('complete_pass') is not True or rec.get('source_identity_sha')!=FULL_ID_SHA:raise ValueError('R3 blocked: R6 recovery not passed for frozen cases')


def source_paths(experiment,manifest=DEFAULT_MANIFEST,root=ROOT):
    if experiment=='r6':
        rows=(root/'results/g_agreement/r/remainder/r6/launch_inputs.txt').read_text().splitlines()
        return sorted({relative(x.strip()) for x in rows if x.strip()})
    prerequisite(experiment,manifest,root)
    paths={relative(manifest)}
    for row in (json.loads(l) for l in (root/manifest).read_text().splitlines() if l.strip()):
        for ref in row['states'].values():
            paths.update(relative(ref[k]) for k in ('path','index_path'))
            if ref.get('kind')=='r5_replay':paths.add(relative(ref['recovery_receipt']))
    return sorted(paths)


def payload(experiment,manifest=DEFAULT_MANIFEST,root=ROOT):
    paths=source_paths(experiment,manifest,root)
    files=[{'path':p,'bytes':(root/p).stat().st_size,'sha256':sha(root/p)} for p in paths]
    return {'experiment':experiment,'manifest':manifest,'input_files':files,'input_bytes':sum(x['bytes'] for x in files),
        'code_roots':['projects/g_agreement','common'],'metadata_files':[f'results/g_agreement/r/remainder/{experiment}/deployment_inputs.json'],'exclude':['.git','.venv','__pycache__','*.pyc','.env','third_party','nla-consistency'],
        'frozen_cap_seconds':CAP,'pull_reserve_seconds':RESERVE,'separate_pod':True,
        'note':'Exact relative files only; fresh isolated repo. R3 requires verified R6 recovery files from the Mac before allocation/setup.'}


def verify_payload(experiment,root=ROOT):
    p=root/f'results/g_agreement/r/remainder/{experiment}/deployment_inputs.json'
    if not p.is_file():raise ValueError('Mac-created deployment_inputs.json required')
    inv=read(p)
    if inv.get('experiment')!=experiment:raise ValueError('Input inventory experiment mismatch')
    for entry in inv['input_files']:
        src=root/relative(entry['path'])
        if not src.is_file() or src.stat().st_size!=entry['bytes'] or sha(src)!=entry['sha256']:raise ValueError('Deployment input missing/changed: '+entry['path'])
    return inv


def validate_guard(experiment,pod,run,now=None,env=None):
    now=time.time() if now is None else now
    env=Path('/proc/1/environ').read_bytes() if env is None else env
    ids=[x.split(b'=',1)[1].decode() for x in env.split(b'\0') if x.startswith(b'RUNPOD_POD_ID=')]
    if ids!=[pod]:raise ValueError('POD ID MISMATCH')
    g=read(run/'guard.json')
    if g.get('pod')!=pod or g.get('experiment')!=experiment:raise ValueError('Guard pod/experiment mismatch')
    start,end=g.get('started_epoch'),g.get('deadline_epoch')
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) for x in (start,end)) or not 0<end-start<=CAP or start>now or end-now<=RESERVE:raise ValueError('Invalid/expired immutable cap or pull reserve reached')
    if not (run/'ARMED').is_file():raise ValueError('Shared guards not ARMED')
    for name in ('watchdog','hardstop'):
        log=(run/f'{name}.log').read_text()
        if 'armed:' not in log or pod not in log:raise ValueError('Shared guard not armed for pod')
        pid=int((run/f'{name}.pid').read_text())
        if pid<=1:raise ValueError('Invalid shared guard PID')
        os.kill(pid,0)
    return g


def science_phases(experiment):
    if experiment=='r6':return ['recovery-preflight','recovery-smoke','recovery-full','generation-preflight','generation-smoke','generation-full','audit']
    return ['generation-preflight','generation-smoke','generation-full','audit']


def phase_command(phase,experiment,pod,run,remaining,manifest=DEFAULT_MANIFEST,python='python',joint_run=False):
    if joint_run and experiment!='r6':raise ValueError('Joint job authorizes R6 only; R3 sampling is parked')
    if isinstance(remaining,bool) or not RESERVE<remaining<=(5400 if joint_run else CAP):raise ValueError('Phase outside immutable remaining budget')
    if phase.startswith('recovery-'):
        value={'recovery-preflight':'preflight','recovery-smoke':'smoke','recovery-full':'recover'}[phase]
        cmd=[python,'-m',RECOVERY,'--phase',value]
        if value!='preflight':
            cmd+=['--pod',pod,'--guard-dir',str(run),'--budget-seconds',str(remaining)]
            if joint_run:cmd+=['--joint-run']
        return cmd
    if phase=='audit':return [python,'-m',MODULE,'audit','--experiment',experiment,'--pod',pod,'--manifest',manifest]
    value={'generation-preflight':'preflight','generation-smoke':'smoke','generation-full':'generate'}[phase]
    cmd=[python,'-m',SCIENCE,'--phase',value,'--manifest',manifest,'--available-cohort','--allow-recaptured-states']
    if experiment=='r3':cmd+=['--profile','r3-sampling']
    if value!='preflight':
        cmd+=['--pod',pod,'--guard-dir',str(run),'--budget-seconds',str(remaining)]
        if joint_run:cmd+=['--joint-run']
    return cmd


def audit(experiment,pod,manifest=DEFAULT_MANIFEST):
    from projects.g_agreement.r_bench import remainder_r6 as R
    rows=R.available_cohort(list(R.read_rows(ROOT/relative(manifest))))
    R.preflight(rows,available=True,allow_recaptured=True)
    profile='r3-sampling' if experiment=='r3' else 'r6';expected={r['gen_id'] for r in R.jobs(rows,profile)}
    generated=list(R.read_rows(R.CACHE/f'remainder/{experiment}/available/generations.jsonl'))
    ids=[r['gen_id'] for r in generated]
    if len(ids)!=len(set(ids)) or set(ids)!=expected:raise ValueError('Incomplete/duplicated generated population')
    if any(r.get('mock') or r.get('pod')!=pod or r.get('code_sha')!=R.sha(R.__file__) for r in generated):raise ValueError('Mock/wrong-pod/code generation row')
    cells=R.assert_coverage(generated,profile)
    out={'complete':True,'profile':profile,'cohort':'available_69_pairs','original_target_met':False,'reports':len(ids),'coverage_cells':cells,'pod':pod}
    write(ROOT/f'results/g_agreement/r/remainder/{experiment}/deployment_audit.json',out);return out


def bundle(experiment,run):
    from projects.g_agreement.r_bench import remainder_deploy as D
    dest=run/'deliverables/operations';dest.mkdir(parents=True,exist_ok=True)
    for name in ('cold_status.json','cold_assets.json','cold_setup.log','venv_freeze.txt','torch_constraint.txt','COLD_SETUP_DONE','COLD_SETUP_FAILED'):
        p=run/name
        if p.is_file():shutil.copy2(p,dest/name)
    return D.bundle(experiment,run)


def descendant_groups(parent_pid,proc_root=Path('/proc')):
    parents={}
    for path in proc_root.iterdir():
        if not path.name.isdigit():continue
        try:
            fields=(path/'stat').read_text().rsplit(')',1)[1].split()
            parents[int(path.name)]=(int(fields[1]),int(fields[2]))
        except (OSError,ValueError,IndexError):continue
    descendants={parent_pid}
    while True:
        new={pid for pid,(ppid,_pgid) in parents.items() if ppid in descendants}
        if new<=descendants:break
        descendants|=new
    return {pgid for pid,(_parent,pgid) in parents.items() if pid in descendants and pgid>1}


def terminate_tree(proc):
    # Cold setup launches bounded children in their own process groups. Stop all
    # descendants, not only the setup parent, before preserving the pull window.
    groups=descendant_groups(proc.pid)|{proc.pid}
    groups.discard(os.getpgrp())
    for group in groups:
        try:os.killpg(group,signal.SIGTERM)
        except ProcessLookupError:pass
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:pass
    for group in groups:
        try:os.killpg(group,signal.SIGKILL)
        except ProcessLookupError:pass
    proc.wait()


def phase_environment(phase,source=None):
    env=dict(os.environ if source is None else source)
    env.pop('RUNPOD_API_KEY',None)
    if phase!='cold-setup':env.pop('HF_TOKEN',None)
    env.update(PYTHONUNBUFFERED='1',HF_HOME=env.get('HF_HOME','/workspace/hf_cache'),
               HF_HUB_OFFLINE='0' if phase=='cold-setup' else '1',TRANSFORMERS_OFFLINE='0' if phase=='cold-setup' else '1')
    return env


def execute(experiment,pod,run,cold=False,manifest=DEFAULT_MANIFEST):
    if ROOT.resolve()!=(run/'repo').resolve():raise ValueError('Execute only inside the isolated booked run repo')
    guard=validate_guard(experiment,pod,run);guard_bytes=(run/'guard.json').read_bytes()
    if any((run/n).exists() for n in ('job_status.json','DONE','FAILED')):raise ValueError('Refuse reused job outcome')
    status={'experiment':experiment,'pod':pod,'state':'RUNNING','started_epoch':time.time(),'deadline_epoch':guard['deadline_epoch'],'reserve_seconds':RESERVE,'phases':[]}
    write(run/'job_status.json',status);rc=1
    try:
        prerequisite(experiment,manifest);verify_payload(experiment)
        phases=(['cold-setup'] if cold else [])+science_phases(experiment)
        python=str(run/'venv/bin/python') if cold else sys.executable
        for phase in phases:
            validate_guard(experiment,pod,run)
            if (run/'guard.json').read_bytes()!=guard_bytes:raise ValueError('Immutable shared guard changed')
            remaining=guard['deadline_epoch']-time.time()
            if phase=='cold-setup':
                command=[sys.executable,'-m','projects.g_agreement.r_bench.remainder_cold_setup','run','--experiment',experiment,'--pod',pod,'--run-dir',str(run),'--setup-only']
            else:command=phase_command(phase,experiment,pod,run,remaining,manifest,python)
            entry={'phase':phase,'started_epoch':time.time(),'command':command};status['phases'].append(entry);write(run/'job_status.json',status)
            bundle(experiment,run)
            env=phase_environment(phase)
            print(f'START {phase}: {remaining-RESERVE:.1f}s before immutable pull reserve',flush=True)
            proc=subprocess.Popen(command,cwd=ROOT,env=env,start_new_session=True)
            try:ret=proc.wait(timeout=max(0,guard['deadline_epoch']-time.time()-RESERVE))
            except subprocess.TimeoutExpired:
                terminate_tree(proc)
                raise RuntimeError(phase+': stopped at immutable300-second pull reserve')
            entry.update(returncode=ret,finished_epoch=time.time());write(run/'job_status.json',status);bundle(experiment,run)
            if ret:raise RuntimeError(f'{phase} failed with exit{ret}')
            if phase=='cold-setup' and not (run/'COLD_SETUP_DONE').is_file():raise RuntimeError('Cold setup returned without completion evidence')
        status['state']='DONE';rc=0
    except Exception as exc:status.update(state='FAILED',error=str(exc))
    finally:
        status['finished_epoch']=time.time();write(run/'job_status.json',status)
        try:
            bundle(experiment,run);(run/status['state']).write_text(json.dumps(status)+'\n');bundle(experiment,run)
        except Exception as exc:
            rc=1;status.update(state='FAILED',bundle_error=str(exc));(run/'DONE').unlink(missing_ok=True)
            write(run/'job_status.json',status);(run/'FAILED').write_text(json.dumps(status)+'\n')
        print(status['state']+': pull and verify available evidence on Mac; no pod stop requested',flush=True)
    return rc


def emit(experiment,pod,run,cold=False,manifest=DEFAULT_MANIFEST):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',pod) or not str(run).startswith(f'/workspace/remainder/{experiment}/') or '..' in run.parts:raise ValueError('Invalid isolated run/pod')
    command=['python3','-m',MODULE,'execute','--experiment',experiment,'--pod',pod,'--run-dir',str(run),'--manifest',relative(manifest)]
    if cold:command+=['--cold-setup']
    return '\n'.join(['#!/usr/bin/env bash','set -euo pipefail',f'RUN={shlex.quote(str(run))}',f'POD={shlex.quote(pod)}',
        'OWN=$(tr "\\0" "\\n" < /proc/1/environ | sed -n "s/^RUNPOD_POD_ID=//p")',
        '[ "$OWN" = "$POD" ] || { echo "POD ID MISMATCH"; exit 2; }',
        'REMAINDER_RUN_DIR="$RUN"; REMAINDER_BOOKED_POD="$POD"',
        'if [ -f /workspace/.env ]; then set -a; source /workspace/.env >/dev/null 2>&1; set +a; fi',
        'RUN="$REMAINDER_RUN_DIR"; POD="$REMAINDER_BOOKED_POD"','cd "$RUN/repo"','echo $$ > "$RUN/job.pid"',
        '[ -s GIT_SHA ] || { echo "GIT_SHA missing"; exit 2; }','export R_GIT_SHA="$(cat GIT_SHA)"',
        'export PYTHONUNBUFFERED=1','export HF_HOME="${HF_HOME:-/workspace/hf_cache}"',
        'export PYTHONPATH="$RUN/repo${PYTHONPATH:+:$PYTHONPATH}"','exec '+shlex.join(command),''])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('payload','emit','execute','audit'))
    p.add_argument('--experiment',choices=('r6','r3'),required=True);p.add_argument('--pod');p.add_argument('--run-dir',type=Path)
    p.add_argument('--manifest',default=DEFAULT_MANIFEST);p.add_argument('--cold-setup',action='store_true');a=p.parse_args(argv)
    if a.action=='payload':
        inv=payload(a.experiment,a.manifest);write(ROOT/f'results/g_agreement/r/remainder/{a.experiment}/deployment_inputs.json',inv)
        print(json.dumps({'experiment':a.experiment,'input_files':len(inv['input_files']),'input_bytes':inv['input_bytes']}));return 0
    if not a.pod:p.error('--pod required')
    if a.action=='audit':print(json.dumps(audit(a.experiment,a.pod,a.manifest)));return 0
    if a.run_dir is None:p.error('--run-dir required')
    if a.action=='emit':print(emit(a.experiment,a.pod,a.run_dir,a.cold_setup,a.manifest),end='');return 0
    return execute(a.experiment,a.pod,a.run_dir,a.cold_setup,a.manifest)

if __name__=='__main__':raise SystemExit(main())
