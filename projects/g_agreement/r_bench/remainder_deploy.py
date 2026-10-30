"""Offline payload inventory and guarded R4/R5 job runner; never allocates/stops pods.

Run emit on the Mac, install its stdout as the booked run's job.sh, then detach it.
A successful job performs coverage audit; statistical analysis stays on the Mac.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
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

ROOT = Path(__file__).resolve().parents[3]
RESERVE = 300
CAPS = {'r4': 3600, 'r5': 1800}
MODULE = 'projects.g_agreement.r_bench.remainder_deploy'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+'.partial')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')
    tmp.replace(path)


def source_paths(experiment, root=ROOT):
    """Exactly the raw state/index inputs; whole arrays retain their frozen hashes."""
    common = ['projects/g_agreement/dataset/items_r.json',
              'projects/g_agreement/manifest/frozen_config_r.json']
    if experiment == 'r4':
        common += ['results/g_agreement/r/r5_selection.json', 'results/g_agreement/r/r5x_selection.json']
        manifest = read(root/'results/g_agreement/r/remainder/r4/preflight.json')
        for ds, fact in manifest['facts'].items():
            common += [fact['state_path'], f'cache/g_agreement/r/states/{ds}/index.json']
    else:
        manifest = read(root/'results/g_agreement/r/remainder/r5/manifest.json')
        common += ['results/g_agreement/r/remainder/r5/manifest.json']
        for fact in manifest['facts']:
            base = f"cache/g_agreement/r/states/{fact['dataset']}"
            common += [base+'/index.json'] + [f'{base}/chat_L{layer}.npy' for layer in manifest['layers']]
    for name in common:
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Input paths must remain inside the isolated repo')
    return sorted(set(common))


def payload(experiment, root=ROOT):
    paths = source_paths(experiment, root)
    entries = [{'path': p, 'bytes': (root/p).stat().st_size} for p in paths]
    return {'experiment': experiment, 'input_files': entries, 'input_bytes': sum(e['bytes'] for e in entries),
            'code_roots': ['projects/g_agreement', 'common'],
            'exclude': ['.git', '.venv', '__pycache__', '*.pyc', '.env', 'third_party', 'nla-consistency'],
            'shared_cache': '/workspace/mats-minis/cache', 'hf_home': '/workspace/hf_cache',
            'note': 'Sync code roots plus these exact files. Ignore inherited live outputs/certificates; use a fresh isolated run. Shared volume needs no state copy if the same hashes pass preflight.'}


def asset_inventory(experiment, hf_home=None):
    """Read cache metadata only. A cold/dangling snapshot fails before model loading."""
    from projects.g_agreement.core import config as c
    home=Path(hf_home or os.environ.get('HF_HOME','/workspace/hf_cache'))
    hub=Path(os.environ.get('HF_HUB_CACHE',str(home/'hub')))
    specifications=[('target',c.TARGET_MODEL_ID,c.TARGET_MODEL_SHA,'',True),
                    ('oracle',c.OLENS_REPO,c.OLENS_SHA,c.OLENS_SUBFOLDER,False)]
    if experiment=='r4':
        specifications += [('nla_base',c.NLA_REPO,c.NLA_SHA,c.NLA_BASE_SUBFOLDER,True),
                           ('nla_adapter',c.NLA_REPO,c.NLA_SHA,c.NLA_ADAPTER_SUBFOLDER,False),
                           ('skip_a',c.SKIPLENS_REPOS['a'],c.SKIPLENS_SHAS['a'],'',False)]
    assets=[]; missing=[]
    for name,repo,revision,subfolder,base in specifications:
        directory=hub/('models--'+repo.replace('/','--'))/'snapshots'/revision/subfolder
        required=['config.json','tokenizer_config.json','tokenizer.json'] if base else ['adapter_config.json','adapter_model.safetensors']
        if name in ('nla_base','skip_a'): required.append('nla_meta.yaml')
        if base:
            index=directory/'model.safetensors.index.json'
            if index.is_file():
                required += ['model.safetensors.index.json']+sorted(set(read(index)['weight_map'].values()))
            else: required.append('model.safetensors')
        absent=[str(directory/f) for f in required if not (directory/f).is_file()]
        missing += absent
        assets.append({'name':name,'repo':repo,'revision':revision,'directory':str(directory),'required':required,'missing':absent})
    if experiment=='r4':
        lens=hub/('models--'+c.JLENS_REPO.replace('/','--'))/'snapshots'/c.JLENS_SHA/c.JLENS_FILE
        absent=[] if lens.is_file() else [str(lens)]
        assets.append({'name':'jlens','repo':c.JLENS_REPO,'revision':c.JLENS_SHA,'path':str(lens),'missing':absent})
        missing += absent
    return {'experiment':experiment,'hf_home':str(home),'hf_hub_cache':str(hub),'assets':assets,'missing':missing}


def check_environment(experiment):
    inventory=asset_inventory(experiment)
    versions={name:importlib.metadata.version(name) for name in
              ('torch','transformers','peft','accelerate','huggingface_hub','safetensors','numpy','pandas','scipy','scikit-learn','PyYAML')}
    import torch
    from transformers import Qwen3_5ForCausalLM  # import verifies the installed architecture support
    inventory.update(versions=versions,cuda_available=torch.cuda.is_available(),cuda_version=torch.version.cuda)
    write(ROOT/f'results/g_agreement/r/remainder/{experiment}/deployment_environment.json',inventory)
    if inventory['missing']: raise ValueError('Pinned model assets absent: '+str(inventory['missing']))
    if not inventory['cuda_available']: raise ValueError('CUDA GPU unavailable')
    return inventory


def validate_identity(experiment, pod, run, env_bytes=None):
    own = Path('/proc/1/environ').read_bytes() if env_bytes is None else env_bytes
    fields = dict(x.split(b'=',1) for x in own.split(b'\0') if b'=' in x)
    if fields.get(b'RUNPOD_POD_ID', b'').decode() != pod:
        raise ValueError('POD ID MISMATCH')
    record = read(run/'guard.json')
    if record.get('pod') != pod or record.get('experiment') != experiment:
        raise ValueError('Guard identity mismatch')
    start, end = record.get('started_epoch'), record.get('deadline_epoch')
    if (any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in (start,end))
            or not 0 < end-start <= CAPS[experiment] or start > time.time()):
        raise ValueError('Invalid immutable guard interval')
    return record


def phase_commands(experiment, pod, run, deadline, python=sys.executable):
    prefix = [python, '-m', f'projects.g_agreement.r_bench.remainder_{experiment}']
    if experiment == 'r4':
        utc = datetime.fromtimestamp(deadline, timezone.utc).isoformat()
        live = ['--pod',pod,'--guard-dir',str(run),'--deadline-utc',utc]
        phases = [('preflight',prefix+['--phase','preflight','--pod',pod]),
                  ('live-smoke',prefix+['--phase','live-smoke']+live),
                  ('run',prefix+['--phase','run']+live)]
    else:
        live = ['--pod',pod,'--deadline-epoch',str(deadline),'--batch','32']
        phases = [('preflight',prefix+['--phase','preflight','--pod',pod]),
                  ('live-smoke',prefix+['--phase','smoke','--live']+live),
                  ('run',prefix+['--phase','run']+live)]
    phases.insert(0,('environment',[python,'-m',MODULE,'environment','--experiment',experiment]))
    phases.append(('audit',[python,'-m',MODULE,'audit','--experiment',experiment]))
    return phases


def audit(experiment):
    if experiment == 'r4':
        from projects.g_agreement.r_bench import remainder_r4 as m
        evidence = m.load_completed_evidence()
        rows = m.read_rows(m.CACHE/'run/rows.jsonl')
        result = m.validate_completed_population(rows,evidence)
        m.assert_states(m.CACHE/'run',evidence['run_complete']['fact_items'])
    else:
        from projects.g_agreement.r_bench import remainder_r5 as m
        manifest = read(m.RESULTS/'manifest.json')
        rows = m.load_rows(m.CACHE/'scores.jsonl')
        if any(r.get('mock') for r in rows):
            raise ValueError('Mock outcomes cannot pass live audit')
        result = {'actual_rows':m.assert_coverage(rows,manifest),'complete':True}
    write(ROOT/f'results/g_agreement/r/remainder/{experiment}/deployment_audit.json',result)
    return result


def copy_changed(source, destination):
    src, dst=Path(source),Path(destination)
    if not dst.exists() or (src.stat().st_size,src.stat().st_mtime_ns)!=(dst.stat().st_size,dst.stat().st_mtime_ns):
        shutil.copy2(src,dst)
    return str(dst)


def bundle(experiment, run, root=ROOT):
    """Copies owned evidence, never symlinks or credentials; safe after a failed phase."""
    dest = run/'deliverables'
    for relative in [f'cache/g_agreement/r/remainder/{experiment}',
                     f'results/g_agreement/r/remainder/{experiment}']:
        src = root/relative
        if src.exists():
            if src.is_symlink() or any(p.is_symlink() for p in src.rglob('*')):
                raise ValueError('Refuse symlink in experiment outputs')
            shutil.copytree(src,dest/relative,dirs_exist_ok=True,copy_function=copy_changed)
    ops = dest/'operations'
    ops.mkdir(parents=True,exist_ok=True)
    for name in ('guard.json','ARMED','job.sh','job.pid','job.log','watchdog.log','hardstop.log',
                 'watchdog.pid','hardstop.pid','job_status.json','DONE','FAILED'):
        p=run/name
        if p.is_file(): shutil.copy2(p,ops/name)
    guards = run/'guards'
    if guards.exists(): shutil.copytree(guards,ops/'guards',dirs_exist_ok=True)
    files = {}
    for p in sorted(dest.rglob('*')):
        if p.is_symlink(): raise ValueError('Refuse symlink in bundle')
        if p.is_file():
            h=hashlib.sha256()
            with p.open('rb') as f:
                for b in iter(lambda:f.read(1<<20),b''): h.update(b)
            files[str(p.relative_to(dest))]=h.hexdigest()
    write(run/'pull_manifest.json',{'files':files,'complete_job':(run/'DONE').exists()})
    return files


def emit(experiment,pod,run,python='python'):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',pod): raise ValueError('Invalid explicit pod ID')
    if not str(run).startswith(f'/workspace/remainder/{experiment}/') or '..' in run.parts:
        raise ValueError('Run must be the isolated experiment directory')
    # Only source the pod's existing volume environment, after its own-ID check. No credentials are transferred.
    cmd=[python,'-m',MODULE,'execute','--experiment',experiment,'--pod',pod,'--run-dir',str(run)]
    return '\n'.join(['#!/usr/bin/env bash','set -euo pipefail',
        f'RUN={shlex.quote(str(run))}',f'POD={shlex.quote(pod)}',
        'OWN=$(tr "\\0" "\\n" < /proc/1/environ | sed -n "s/^RUNPOD_POD_ID=//p")',
        '[ "$OWN" = "$POD" ] || { echo "POD ID MISMATCH"; exit 2; }',
        'REMAINDER_RUN_DIR="$RUN"; REMAINDER_BOOKED_POD="$POD"',
        'if [ -f /workspace/.env ]; then set -a; source /workspace/.env >/dev/null 2>&1; set +a; fi',
        'RUN="$REMAINDER_RUN_DIR"; POD="$REMAINDER_BOOKED_POD"',
        'cd "$RUN/repo"','echo $$ > "$RUN/job.pid"',
        '[ -s GIT_SHA ] || { echo "GIT_SHA missing"; exit 2; }',
        'export R_GIT_SHA="$(cat GIT_SHA)"',
        'export PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1',
        'export HF_HOME="${HF_HOME:-/workspace/hf_cache}"',
        'export PYTHONPATH="$RUN/repo${PYTHONPATH:+:$PYTHONPATH}"',
        'exec '+shlex.join(cmd),''])


def execute(experiment,pod,run):
    if ROOT.resolve() != (run/'repo').resolve(): raise ValueError('Runner must execute from its isolated repo')
    record=validate_identity(experiment,pod,run)
    if not (run/'ARMED').exists(): raise ValueError('Shared guards not ARMED')
    for name in ('watchdog','hardstop'):
        log=(run/f'{name}.log').read_text()
        if 'armed:' not in log or pod not in log: raise ValueError(f'{name} not armed for booked pod')
        os.kill(int((run/f'{name}.pid').read_text()),0)
    frozen=(run/'guard.json').read_bytes()
    if any((run/name).exists() for name in ('DONE','FAILED','job_status.json')):
        raise ValueError('Refuse an existing job outcome; preserve failed run evidence')
    status={'experiment':experiment,'pod':pod,'deadline_epoch':record['deadline_epoch'],
            'started_epoch':time.time(),'state':'RUNNING','phases':[]}
    write(run/'job_status.json',status)
    code=1
    try:
        for phase,command in phase_commands(experiment,pod,run,record['deadline_epoch']):
            if (run/'guard.json').read_bytes()!=frozen: raise ValueError('Immutable guard changed')
            remaining=record['deadline_epoch']-time.time()-RESERVE
            if remaining<=0: raise RuntimeError('Pull reserve reached')
            entry={'phase':phase,'command':command,'started_epoch':time.time()}
            status['phases'].append(entry); write(run/'job_status.json',status)
            print(f'START {phase}; {remaining:.0f}s before pull reserve',flush=True)
            proc=subprocess.Popen(command,cwd=ROOT,start_new_session=True)
            try:
                rc=proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGTERM)
                try: proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL); proc.wait()
                raise RuntimeError(f'{phase}: immutable pull-reserve deadline reached')
            entry.update(returncode=rc,finished_epoch=time.time())
            write(run/'job_status.json',status)
            bundle(experiment,run)
            if rc: raise RuntimeError(f'{phase} failed with exit {rc}')
        status['state']='DONE'; code=0
    except Exception as exc:
        status['state']='FAILED'; status['error']=str(exc)
    finally:
        status['finished_epoch']=time.time(); write(run/'job_status.json',status)
        try:
            bundle(experiment,run)
            (run/status['state']).write_text(json.dumps(status)+'\n')
            bundle(experiment,run)
        except Exception as exc:
            code=1; status['state']='FAILED'; status['bundle_error']=str(exc)
            (run/'DONE').unlink(missing_ok=True)
            write(run/'job_status.json',status)
            (run/'FAILED').write_text(json.dumps(status)+'\n')
        print(status['state']+': inspect job_status and pull all available evidence; no stop requested',flush=True)
    return code


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['inputs','emit','execute','audit','bundle','assets','environment'])
    p.add_argument('--experiment',required=True,choices=CAPS)
    p.add_argument('--pod'); p.add_argument('--run-dir',type=Path); p.add_argument('--python',default='python')
    a=p.parse_args(argv)
    if a.action=='inputs': print(json.dumps(payload(a.experiment),indent=2))
    elif a.action=='assets': print(json.dumps(asset_inventory(a.experiment),indent=2))
    elif a.action=='environment': print(json.dumps(check_environment(a.experiment),indent=2))
    elif a.action=='audit': print(json.dumps(audit(a.experiment)))
    else:
        if not a.run_dir: p.error('--run-dir required')
        if a.action=='bundle': bundle(a.experiment,a.run_dir)
        else:
            if not a.pod: p.error('--pod required')
            if a.action=='emit': print(emit(a.experiment,a.pod,a.run_dir,a.python),end='')
            else: return execute(a.experiment,a.pod,a.run_dir)
    return 0

if __name__=='__main__': raise SystemExit(main())
