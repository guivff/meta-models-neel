"""Durable R2 cold-pod chain and an explicit Mac-side transfer measurement.

No allocation or stop API. `emit`, `inputs` and tests are offline. Only the
operator-invoked `measure` command uses SSH/SCP against an explicit booked pod.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
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
MODULE='projects.g_agreement.r_bench.remainder_r2_deploy'
CAP,RESERVE,PROBE_BYTES=1200,300,16*1024*1024


def read(p):return json.loads(Path(p).read_text())


def write(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.partial')
    tmp.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n');tmp.replace(p)


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def check_path(pod,run):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',pod):raise ValueError('Invalid pod ID')
    if not re.fullmatch(r'/workspace/remainder/r2/[A-Za-z0-9_-]{1,80}',str(run)):raise ValueError('Run must be fresh isolated R2 directory')


def guard(pod,run,env_bytes=None,now=None,check_processes=True):
    check_path(pod,run);now=time.time() if now is None else now
    raw=Path('/proc/1/environ').read_bytes() if env_bytes is None else env_bytes
    own=[p.split(b'=',1)[1].decode() for p in raw.split(b'\0') if p.startswith(b'RUNPOD_POD_ID=')]
    if own!=[pod]:raise ValueError('POD ID MISMATCH')
    p=run/'guard.json';g=read(p);values=[g.get('started_epoch'),g.get('deadline_epoch')]
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in values):raise ValueError('Invalid guard epochs')
    start,end=values
    if g.get('experiment')!='r2' or g.get('pod')!=pod or start>now or not 0<end-start<=CAP:raise ValueError('Invalid R2 guard identity/cap')
    if end-now<=RESERVE:raise ValueError('R2 pull reserve reached')
    if not (run/'ARMED').is_file():raise ValueError('Shared guards not armed')
    if check_processes:
        for name in ('watchdog','hardstop'):
            log=(run/f'{name}.log').read_text()
            if 'armed:' not in log or pod not in log:raise ValueError('Shared guard did not arm for booked pod')
            pid=int((run/f'{name}.pid').read_text())
            if pid<=1:raise ValueError('Invalid shared guard PID')
            os.kill(pid,0)
    return {**g,'guard_sha256':sha(p)}


def inputs(root=ROOT):
    obj=read(root/'results/g_agreement/r/remainder/r2/deployment_inputs.json')
    paths=set()
    for entry in obj['input_files']:
        p=Path(entry['path'])
        if p.is_absolute() or '..' in p.parts or p.name=='.env' or p.as_posix() in paths:raise ValueError('Nonportable/duplicate input path')
        if not re.fullmatch(r'[0-9a-f]{64}',entry['sha256']):raise ValueError('Input checksum absent')
        if entry['bytes']<=0:raise ValueError('Empty source input')
        paths.add(p.as_posix())
    if len(paths)!=obj['input_file_count'] or sum(e['bytes'] for e in obj['input_files'])!=obj['input_bytes']:raise ValueError('Input totals disagree')
    return obj


def prepare_probe(pod,run,joint_run=False):
    if joint_run:
        from projects.g_agreement.r_bench.remainder_joint import guard as joint_guard
        g=joint_guard(pod,run)
    else:g=guard(pod,run)
    p=run/'bandwidth_probe.bin';mp=run/'bandwidth_probe.json'
    if p.exists() or mp.exists():raise ValueError('Transfer probe already exists; do not renew measurement implicitly')
    # Random bytes prevent compression from inflating network throughput estimates.
    with p.open('xb') as f:
        os.chmod(p,0o600)
        for _ in range(PROBE_BYTES//(1<<20)):f.write(os.urandom(1<<20))
        f.flush();os.fsync(f.fileno())
    record={'pod':pod,'run_dir':str(run),'guard_sha256':g['guard_sha256'],'deadline_epoch':g['deadline_epoch'],
            'bytes':p.stat().st_size,'sha256':sha(p),'created_epoch':time.time(),'path':str(p)}
    write(mp,record);return record


def validate_measurement(rec,pod,run,g,now=None):
    now=time.time() if now is None else now
    if rec.get('pod')!=pod or rec.get('run_dir')!=str(run) or rec.get('guard_sha256')!=g['guard_sha256'] or rec.get('deadline_epoch')!=g['deadline_epoch']:raise ValueError('Transfer measurement belongs to another booked run')
    samples=rec.get('samples',[])
    if rec.get('measured_on')!='Mac' or len(samples)!=2:raise ValueError('Two actual Mac transfers required')
    if not re.fullmatch(r'[0-9a-f]{64}',rec.get('probe_sha256','')):raise ValueError('Probe checksum missing')
    rates=[]
    for sample in samples:
        seconds=sample.get('seconds');n=sample.get('bytes')
        if n!=PROBE_BYTES or not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<=0:raise ValueError('Invalid transfer size/timing')
        if sample.get('sha256')!=rec['probe_sha256']:raise ValueError('Transferred probe checksum differs')
        rates.append(n/seconds)
    rate=rec.get('bytes_per_second')
    if not isinstance(rate,(int,float)) or not math.isfinite(rate) or not math.isclose(rate,min(rates),rel_tol=1e-12):raise ValueError('Transfer rate must be slower measured sample')
    if not g['started_epoch']<=rec.get('measured_epoch',0)<=now:raise ValueError('Transfer measurement outside current booked interval')
    return rate


def measure(pod,run,host,port,identity,out,joint_run=False):
    """Parent invokes this on the Mac after first SSH/guards/code sync; no API use."""
    if joint_run:
        from projects.g_agreement.r_bench.remainder_joint import check_path as joint_path
        joint_path(pod,run)
    else:check_path(pod,run)
    if not re.fullmatch(r'[A-Za-z0-9.-]+',host) or not 1<=port<=65535:raise ValueError('Invalid explicit SSH endpoint')
    if sys.platform!='darwin':raise ValueError('Transfer measurement must run on the Mac')
    out=Path(out)
    if out.exists():raise ValueError('Refuse reused local measurement directory')
    out.mkdir(parents=True)
    common=['-o','BatchMode=yes','-o','Compression=no','-i',str(identity)]
    ssh=['ssh',*common,'-p',str(port),'root@'+host]
    cmd=['python3','-m',MODULE,'prepare-probe','--pod',pod,'--run-dir',str(run)]
    if joint_run:cmd+=['--joint-run']
    remote='cd '+shlex.quote(str(run/'repo'))+' && exec '+shlex.join(cmd)
    started=time.monotonic()
    probe=json.loads(subprocess.run([*ssh,remote],check=True,capture_output=True,text=True,timeout=45).stdout)
    if probe.get('pod')!=pod or probe.get('run_dir')!=str(run) or probe.get('bytes')!=PROBE_BYTES:raise ValueError('Wrong remote transfer probe')
    samples=[]
    for i in range(2):
        remaining=probe['deadline_epoch']-time.time()-RESERVE
        if remaining<=0:raise RuntimeError('Immutable pull reserve reached during Mac throughput measurement')
        path=out/f'probe_{i}.bin';t0=time.monotonic()
        subprocess.run(['scp',*common,'-P',str(port),f'root@{host}:{run}/bandwidth_probe.bin',str(path)],check=True,timeout=min(120,remaining))
        elapsed=time.monotonic()-t0
        if path.stat().st_size!=PROBE_BYTES or sha(path)!=probe['sha256']:raise ValueError('Mac transfer size/checksum mismatch')
        samples.append({'bytes':path.stat().st_size,'seconds':elapsed,'sha256':sha(path)})
    rec={'pod':pod,'run_dir':str(run),'guard_sha256':probe['guard_sha256'],'deadline_epoch':probe['deadline_epoch'],
         'probe_sha256':probe['sha256'],'measured_on':'Mac','samples':samples,'bytes_per_second':min(s['bytes']/s['seconds'] for s in samples),
         'measured_epoch':time.time(),'measurement_wall_seconds':time.monotonic()-started,'ssh_host':host,'ssh_port':port}
    receipt=out/'pull_bandwidth.json';write(receipt,rec)
    remaining=probe['deadline_epoch']-time.time()-RESERVE
    if remaining<=0:raise RuntimeError('Immutable pull reserve reached before measurement receipt upload')
    subprocess.run(['scp',*common,'-P',str(port),str(receipt),f'root@{host}:{run}/pull_bandwidth.json'],check=True,timeout=min(30,remaining))
    return rec


def phase_commands(pod,run,deadline,rate):
    py=str(run/'venv/bin/python');base=[py,'-m','projects.g_agreement.r_bench.remainder_r2_capture']
    live=['--pod',pod,'--guard-dir',str(run),'--deadline-epoch',str(deadline),'--batch','32']
    return [('cold-setup',[sys.executable,'-m','projects.g_agreement.r_bench.remainder_cold_setup','run','--experiment','r2','--pod',pod,'--run-dir',str(run),'--setup-only']),
            ('preflight',base+['--phase','preflight','--pod',pod]),
            ('live-smoke',base+['--phase','live-smoke',*live,'--measured-pull-bytes-per-second',str(rate)]),
            ('capture',base+['--phase','capture',*live])]


def publish_file(source,dest):
    """Owned immutable output chunks may hardlink; never duplicate tens of GiB."""
    source,dest=Path(source),Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    if source.is_symlink():raise ValueError('Symlink output refused')
    if dest.exists():
        if dest.is_symlink():raise ValueError('Symlink destination refused')
        if os.path.samefile(source,dest):return
        dest.unlink()
    try:os.link(source,dest)
    except OSError:shutil.copy2(source,dest)


def bundle(run,root=ROOT):
    dst=run/'deliverables'
    for rel in ('cache/g_agreement/r/remainder/r2','results/g_agreement/r/remainder/r2'):
        source=root/rel
        if source.is_symlink():raise ValueError('Symlink experiment output root refused')
        if source.exists():
            for p in source.rglob('*'):
                if p.is_symlink():raise ValueError('Symlink experiment output refused')
                if p.is_file():publish_file(p,dst/rel/p.relative_to(source))
    ops=dst/'operations';ops.mkdir(parents=True,exist_ok=True)
    # Operational logs are snapshots because their writers may still be alive.
    for name in ('guard.json','ARMED','job.sh','job.pid','job.log','job_status.json','watchdog.log','hardstop.log',
                 'watchdog.pid','hardstop.pid','cold_status.json','COLD_SETUP_DONE','full_disk_projection.json','pull_bandwidth.json','bandwidth_probe.json','DONE','FAILED'):
        p=run/name
        if p.is_file():shutil.copy2(p,ops/name)
    if (run/'guards').exists():shutil.copytree(run/'guards',ops/'guards',dirs_exist_ok=True)
    return {'files':sum(p.is_file() for p in dst.rglob('*')),'path':str(dst)}


def disk_projection(output_bytes,free_bytes,asset_bytes,input_bytes,same_filesystem=True):
    values=(output_bytes,free_bytes,asset_bytes,input_bytes)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in values) or output_bytes<=0:
        raise ValueError('Invalid full-capture disk projection')
    copies=1 if same_filesystem else 2
    headroom=max(5*1024**3,.10*output_bytes)
    required_free=output_bytes*copies+headroom
    # The authorised cold fallback is 200 GB even if overlayfs reports host space.
    allocated=200_000_000_000
    projected_owned=asset_bytes+input_bytes+output_bytes*copies+10_000_000_000+headroom
    ready=free_bytes>=required_free and projected_owned<=allocated
    return {'ready':ready,'free_bytes':free_bytes,'required_free_bytes':required_free,'projected_output_bytes':output_bytes,
            'publication_copies':copies,'headroom_bytes':headroom,'model_asset_bytes':asset_bytes,'source_input_bytes':input_bytes,
            'runtime_allowance_bytes':10_000_000_000,'allocated_disk_bytes':allocated,'projected_owned_bytes':projected_owned}


def full_disk_gate(run,root=ROOT,strict=True):
    output=root/'cache/g_agreement/r/remainder/r2';cert=read(output/'live_smoke.json')
    if cert.get('kind')!='live' or cert.get('coverage',{}).get('arm_cells')!=72:raise ValueError('Live smoke required for disk projection')
    cold=read(run/'cold_status.json');hub=Path(cold['hf_hub_cache'])
    if not hub.is_dir():raise ValueError('Recorded model cache is absent')
    # Blob files count once; snapshot symlinks must not double-count the same model.
    assets=sum(p.stat().st_size for p in hub.rglob('*') if p.is_file() and not p.is_symlink())
    inventory=inputs(root);usage=shutil.disk_usage(output)
    result=disk_projection(cert['projected_tap_bytes'],usage.free,assets,inventory['input_bytes'],output.stat().st_dev==run.stat().st_dev)
    write(run/'full_disk_projection.json',result)
    if strict and not result['ready']:raise RuntimeError('DISK BLOCKED: full capture plus output publication/headroom exceeds available space or authorised 200GB allocation')
    return result


def emit(pod,run):
    check_path(pod,run)
    return '\n'.join(['#!/usr/bin/env bash','set -euo pipefail',f'RUN={shlex.quote(str(run))}',f'POD={shlex.quote(pod)}',
        'OWN=$(tr "\\0" "\\n" < /proc/1/environ | sed -n "s/^RUNPOD_POD_ID=//p")',
        '[ "$OWN" = "$POD" ] || { echo "POD ID MISMATCH"; exit 2; }',
        'REMAINDER_BOOKED_RUN="$RUN"; REMAINDER_BOOKED_POD="$POD"',
        'if [ -f /workspace/.env ]; then set -a; source /workspace/.env >/dev/null 2>&1; set +a; fi',
        'RUN="$REMAINDER_BOOKED_RUN"; POD="$REMAINDER_BOOKED_POD"',
        'cd "$RUN/repo"','echo $$ > "$RUN/job.pid"','[ -s GIT_SHA ] || { echo "GIT_SHA missing"; exit 2; }',
        'export R_GIT_SHA="$(cat GIT_SHA)"','export PYTHONUNBUFFERED=1',
        'export HF_HOME="${HF_HOME:-/workspace/hf_cache}"','export PYTHONPATH="$RUN/repo${PYTHONPATH:+:$PYTHONPATH}"',
        'exec python3 -m '+MODULE+' execute --pod "$POD" --run-dir "$RUN"',''])


def execute(pod,run):
    if ROOT.resolve()!=(run/'repo').resolve():raise ValueError('Execute only in isolated booked repo')
    g=guard(pod,run);frozen=(run/'guard.json').read_bytes()
    if any((run/name).exists() for name in ('job_status.json','DONE','FAILED')):raise ValueError('Prior R2 run outcome exists')
    rate=validate_measurement(read(run/'pull_bandwidth.json'),pod,run,g)
    status={'pod':pod,'experiment':'r2','deadline_epoch':g['deadline_epoch'],'code_sha':sha(__file__),
            'started_epoch':time.time(),'state':'RUNNING','phases':[],'measured_pull_bytes_per_second':rate}
    write(run/'job_status.json',status);code=1
    try:
        for phase,command in phase_commands(pod,run,g['deadline_epoch'],rate):
            guard(pod,run)
            if (run/'guard.json').read_bytes()!=frozen:raise ValueError('Original guard changed')
            remaining=g['deadline_epoch']-time.time()-RESERVE-15
            if remaining<=0:raise RuntimeError('Pull reserve reached')
            if phase=='capture':status['full_disk_projection']=full_disk_gate(run)
            env=dict(os.environ)
            if phase!='cold-setup':
                if not (run/'COLD_SETUP_DONE').is_file():raise RuntimeError('Cold setup completion marker missing')
                env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
                for key in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN','RUNPOD_API_KEY','OPENROUTER_API_KEY'):env.pop(key,None)
            entry={'phase':phase,'started_epoch':time.time(),'command':command};status['phases'].append(entry);write(run/'job_status.json',status)
            print('START '+phase+f'; {remaining:.0f}s before immutable pull reserve',flush=True)
            proc=subprocess.Popen(command,cwd=ROOT,env=env,start_new_session=True)
            try:rc=proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                raise RuntimeError(phase+': immutable deadline reached')
            entry.update(returncode=rc,finished_epoch=time.time())
            if phase=='live-smoke' and (ROOT/'cache/g_agreement/r/remainder/r2/live_smoke.json').is_file():
                status['full_disk_projection']=full_disk_gate(run,strict=False)
            write(run/'job_status.json',status);bundle(run)
            if rc:raise RuntimeError(phase+f' failed with exit {rc}')
        result=read(ROOT/'cache/g_agreement/r/remainder/r2/capture_complete.json')
        if result.get('pod')!=pod or result.get('coverage',{}).get('status')!='PASS' or result['coverage'].get('arm_cells')!=72:raise ValueError('Full capture certificate absent/incomplete')
        status['state']='DONE';code=0
    except Exception as exc:status['state']='FAILED';status['error']=str(exc)
    finally:
        status['finished_epoch']=time.time();write(run/'job_status.json',status)
        (run/status['state']).write_text(json.dumps(status)+'\n')
        try:status['bundle']=bundle(run)
        except Exception as exc:
            code=1;status['state']='FAILED';status['bundle_error']=str(exc);(run/'DONE').unlink(missing_ok=True)
            (run/'FAILED').write_text(json.dumps(status)+'\n')
        write(run/'job_status.json',status)
        ops=run/'deliverables/operations'
        if ops.exists():shutil.copy2(run/'job_status.json',ops/'job_status.json')
        print(status['state']+': pull all available evidence to the Mac; this chain never stops a pod',flush=True)
    return code


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('inputs','emit','prepare-probe','measure','execute','bundle'))
    p.add_argument('--pod');p.add_argument('--run-dir',type=Path);p.add_argument('--ssh-host');p.add_argument('--ssh-port',type=int)
    p.add_argument('--ssh-identity',type=Path);p.add_argument('--out-dir',type=Path);p.add_argument('--joint-run',action='store_true');a=p.parse_args(argv)
    if a.action=='inputs':result=inputs()
    else:
        if not a.pod or not a.run_dir:p.error('explicit --pod and --run-dir required')
        if a.action=='emit':print(emit(a.pod,a.run_dir),end='');return 0
        if a.action=='execute':return execute(a.pod,a.run_dir)
        if a.action=='prepare-probe':result=prepare_probe(a.pod,a.run_dir,a.joint_run)
        elif a.action=='bundle':result=bundle(a.run_dir)
        else:
            if not all((a.ssh_host,a.ssh_port,a.ssh_identity,a.out_dir)):p.error('measure requires explicit own-pod SSH endpoint/identity and local output directory')
            result=measure(a.pod,a.run_dir,a.ssh_host,a.ssh_port,a.ssh_identity,a.out_dir,a.joint_run)
    print(json.dumps(result,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
