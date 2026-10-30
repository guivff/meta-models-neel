"""R-D Mac launcher: frozen source, own-pod guards, bounded job, verified pull.

No deployment, resume, or termination operation exists. `release` stops only
with an exact own-pod integrator HANDOFF clearance after a verified pull;
otherwise it returns the pod warm under the existing immutable deadline.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import importlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import time
import uuid
from projects.g_agreement.r_bench import rd_pretext as P
from projects.g_agreement.r_bench import rd_pretext_items as B
from projects.g_agreement.r_bench import x4b_cue_ops as X

REMOTE_REPO = '/workspace/rd_pretext_repo'
REMOTE_OPS = '/workspace/rd_pretext_ops'
DATA_REL = 'cache/g_agreement/r/rd_pretext'
BANK_REL = 'projects/g_agreement/dataset/items_r_rd_pretext.json'
HANDOFF_REL = 'results/g_agreement/r/HANDOFF.md'
GUARD_REL = 'results/g_agreement/r/pod_tools'
GUARDS = ('ws2_macguard.sh', 'ws2_hardstop.sh', 'ws2_watchdog.sh', 'ws2_offvolume.sh', 'ws2_verify_pull.py')
OPS_OUTPUTS = ('assignment.rd.json', 'receipt.rd.json', 'exit.rd.json', 'run_log.rd.txt')
OPS_RESULTS = 'results/g_agreement/r/rd_pretext_ops'
DEPENDENCIES = ('transformers', 'peft', 'accelerate', 'huggingface_hub', 'safetensors', 'tokenizers', 'numpy', 'scipy', 'scikit-learn', 'PyYAML', 'pandas')
RUN_ID = 'rd-ops-' + uuid.uuid4().hex
_STOP_AUTHORITY = object()


def digest(raw): return hashlib.sha256(raw).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
def read(path): return json.loads(Path(path).read_text())
def sha(path): return digest(Path(path).read_bytes())
def git(*args): return subprocess.check_output(['git', *args])
def assignment_sha(a): return digest(canonical(a))
def source_files(): return tuple(importlib.import_module('projects.g_agreement.r_bench.rd_pretext_run').source_files())
def paths(base, smoke=False):
    runner = importlib.import_module('projects.g_agreement.r_bench.rd_pretext_run')
    return runner.paths(Path(base)/'smoke' if smoke else Path(base))


def write_new(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    row = dict(obj, run_id=RUN_ID, run_kind='test' if 'pytest' in __import__('sys').modules else 'real', code_sha256=sha(__file__))
    with path.open('x') as f:
        json.dump(row, f, sort_keys=True, indent=2, allow_nan=False); f.write('\n')
    return row


def validate_assignment(a, now=None, science=True):
    now = time.time() if now is None else now
    if type(a.get('brief_section')) is not int or a['brief_section'] != P.BRIEF_SECTION:
        raise ValueError('integrator-assigned section required')
    if not re.fullmatch(r'[A-Za-z0-9-]{6,80}', a.get('pod_id', '')):
        raise ValueError('explicit own pod ID required')
    if a.get('fresh_pod') is not True or a.get('off_volume') is not True:
        raise ValueError('fresh off-volume integrator assignment required')
    if not any(g in a.get('gpu', '') for g in ('H100', 'H200')):
        raise ValueError('registered H100/H200 required; other GPU needs a dated protocol amendment')
    for key in ('integrator_clearance', 'prior_guard_evidence'):
        if not isinstance(a.get(key), str) or not a[key].strip(): raise ValueError(key + ' required')
    pids = a.get('prior_guard_pids')
    if not isinstance(pids, list) or len(set(pids)) != len(pids) or any(type(p) is not int or p <= 1 for p in pids):
        raise ValueError('explicit prior guard PID list required')
    start, end = a.get('assigned_at'), a.get('hard_deadline')
    if not all(type(v) in (int, float) and math.isfinite(v) for v in (start, end)):
        raise ValueError('finite allocation timestamps required')
    if end != start + P.MAX_SECONDS or not start <= now < end - (P.PULL_RESERVE_SECONDS if science else 0):
        raise ValueError('immutable assigned_at+9000 deadline/science cutoff violated')
    for key, length in [('source_commit', 40), ('bank_file_sha256', 64), ('bank_sha256', 64)]:
        if not re.fullmatch('[a-f0-9]{' + str(length) + '}', a.get(key, '')): raise ValueError('invalid frozen ' + key)
    return a


def remaining(a, now=None):
    now = time.time() if now is None else now
    validate_assignment(a, now)
    return int(a['hard_deadline'] - P.PULL_RESERVE_SECONDS - now)


def archive_paths(tracked):
    """Full tracked Python/shell code closure, manifests, and one frozen bank."""
    chosen = []
    for name in tracked:
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts: raise ValueError('unsafe tracked archive path')
        if any(v in {'.env', '.git', '.venv', 'cache', 'secrets', '.aws'} or v.startswith('.env.') for v in p.parts): continue
        if p.suffix.lower() in ('.key', '.pem', '.p12', '.pfx'): continue
        if p.suffix in ('.py', '.sh') or '/manifest/' in name and p.suffix == '.json' or name in (BANK_REL, 'requirements.txt', 'pyproject.toml'):
            chosen.append(name)
    if BANK_REL not in chosen or 'requirements.txt' not in chosen:
        raise ValueError('frozen bank/requirements absent from committed source')
    return sorted(chosen)


def verify_pushed(commit):
    """The immutable source may precede a later published guard/HANDOFF receipt."""
    if not re.fullmatch('[a-f0-9]{40}', commit): raise ValueError('full commit required')
    branch = 'refs/heads/codex/r-d'
    value = git('ls-remote', 'origin', branch).decode().split()
    if len(value) != 2 or value[1] != branch or not re.fullmatch('[a-f0-9]{40}', value[0]):
        raise ValueError('published codex/r-d head required')
    published = value[0]
    try:
        git('cat-file', '-e', published + '^{commit}')
    except subprocess.CalledProcessError:
        # Fetch only this exact branch; never merge, rebase, or change the checkout.
        git('fetch', '--no-tags', 'origin', branch)
        if git('rev-parse', 'FETCH_HEAD').decode().strip() != published:
            raise ValueError('published branch changed during source verification')
    try:
        git('merge-base', '--is-ancestor', commit, published)
    except subprocess.CalledProcessError:
        raise ValueError('frozen source is not an ancestor of published codex/r-d') from None
    if git('ls-remote', 'origin', branch).decode().split() != value:
        raise ValueError('published branch changed during source verification')
    return published


def dependency_pins(raw):
    found = {}
    for line in raw.decode().splitlines():
        if re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+', line):
            name = line.split('==')[0].casefold()
            if name in found: raise ValueError('duplicate frozen dependency pin')
            found[name] = line
    missing = [name for name in DEPENDENCIES if name.casefold() not in found]
    if missing: raise ValueError('missing frozen dependency pins: ' + repr(missing))
    return [found[name.casefold()] for name in DEPENDENCIES]


def prepare(a, state):
    validate_assignment(a)
    if git('status', '--porcelain').strip() or git('rev-parse', 'HEAD').decode().strip() != a['source_commit']:
        raise ValueError('clean committed source HEAD required')
    verify_pushed(a['source_commit'])
    bank = git('show', a['source_commit'] + ':' + BANK_REL); frozen = B.validate(json.loads(bank))
    if digest(bank) != a['bank_file_sha256'] or frozen['bank_sha256'] != a['bank_sha256']:
        raise ValueError('frozen full bank mismatch')
    tracked = git('ls-tree', '-r', '--name-only', a['source_commit']).decode().splitlines()
    deployed = archive_paths(tracked); declared = source_files()
    if not declared or not set(declared).issubset(deployed): raise ValueError('SOURCE_FILES missing from archive')
    modes = {line.split('\t')[1]: line.split()[0] for line in git('ls-tree', '-r', a['source_commit']).decode().splitlines()}
    if any(modes[p] not in ('100644', '100755') for p in deployed): raise ValueError('archive may not contain symlink code/data')
    hashes = {p: digest(git('show', a['source_commit'] + ':' + p)) for p in declared}
    for p, expected in hashes.items():
        if sha(p) != expected: raise ValueError('imported source differs from frozen commit: ' + p)
    a = dict(a, source_hashes=hashes)
    requirements = git('show', a['source_commit'] + ':requirements.txt'); pins = dependency_pins(requirements)
    archive = gzip.compress(git('archive', '--format=tar', a['source_commit'], '--', *deployed), mtime=0)
    state = Path(state).resolve(); state.mkdir(parents=True, exist_ok=False)
    (state/'assignment.json').write_bytes(canonical(a)); (state/'source.tar.gz').write_bytes(archive)
    (state/'requirements.txt').write_bytes(requirements)
    tools = state/'tools'; tools.mkdir()
    for name in GUARDS: (tools/name).write_bytes(git('show', a['source_commit'] + ':' + GUARD_REL + '/' + name))
    write_new(state/'bundle.json', dict(assignment_sha256=assignment_sha(a), archive_sha256=digest(archive),
        requirements_sha256=digest(requirements), dependency_pins=pins, deployed_paths=deployed,
        tool_sha256={name: sha(tools/name) for name in GUARDS}))
    return dict(state=str(state), archive_bytes=len(archive), source_files=len(deployed), hard_deadline=a['hard_deadline'])


def verified_bundle(state):
    state = Path(state); a = read(state/'assignment.json'); bundle = read(state/'bundle.json')
    if bundle['assignment_sha256'] != assignment_sha(a) or bundle['archive_sha256'] != sha(state/'source.tar.gz'):
        raise ValueError('prepared bundle changed')
    if bundle['requirements_sha256'] != sha(state/'requirements.txt') or bundle['dependency_pins'] != dependency_pins((state/'requirements.txt').read_bytes()):
        raise ValueError('frozen requirements changed')
    if bundle['tool_sha256'] != {name: sha(state/'tools'/name) for name in GUARDS}:
        raise ValueError('frozen guard tools changed')
    for p, expected in a['source_hashes'].items():
        if sha(p) != expected: raise ValueError('local execution source changed: ' + p)
    return a


def tool_env(state, envfile=None):
    state = Path(state).resolve(); c = read(state/'connection.json')
    if envfile is None: envfile = read(state/'guard_receipt.json')['mac_env_file']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('WD_', 'WS2_'))}
    env.update(WS2_MAC_GUARD_DIR=str(state/'mac_guard'), WS2_MAC_CACHE=str(state/'pulls'),
        WS2_SSH_KEY=c['ssh_key'], RUNPOD_SECRETS=str(Path(envfile).resolve()), WS2_HANDOFF=str(Path(HANDOFF_REL).resolve()))
    return env


def shared_tool(state, tool, args, envfile=None, *, _stop_authority=None):
    allowed = {'ws2_macguard.sh': {'arm', 'rearm', 'hold'}, 'ws2_offvolume.sh': {'job', 'pull', 'release'}}
    stopping = tool == 'ws2_macguard.sh' and args and args[0] == 'stop' and _stop_authority is _STOP_AUTHORITY
    if tool not in allowed or not args or args[0] not in allowed[tool] and not stopping:
        raise ValueError('unregistered/lifecycle operation forbidden')
    verified_bundle(state)
    subprocess.run(['bash', str(Path(state)/'tools'/tool), *args], env=tool_env(state, envfile), check=True, start_new_session=True)


def status(state, envfile=None, *, running=True):
    a = verified_bundle(state)
    if envfile is None: envfile = read(Path(state)/'guard_receipt.json')['mac_env_file']
    code, body = X.provider(a['pod_id'], X.private_env(envfile)['RUNPOD_API_KEY'])
    if code != 200 or body.get('id') != a['pod_id'] or running and body.get('desiredStatus') != 'RUNNING':
        raise ValueError('assigned pod requires own-ID HTTP200 RUNNING status')
    return dict(status_http=code, status_id=a['pod_id'], status_id_matched=True, desired_status=body.get('desiredStatus'))


def remote(state, command, data=None):
    state = Path(state).resolve(); conn = read(state/'connection.json')
    args = ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=20','-o','StrictHostKeyChecking=accept-new',
        '-o','UserKnownHostsFile='+str(state/'known_hosts'),'-p',str(conn['port']),'-i',conn['ssh_key'],
        'root@'+conn['ip'],command]
    try:
        result = subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=60)
    except (subprocess.TimeoutExpired,OSError):
        raise RuntimeError('remote operation timed out or failed; details redacted') from None
    if result.returncode: raise RuntimeError('remote operation failed; inspect sanitized remote logs')
    return result.stdout


def own_id_check(state, pod):
    code = "import pathlib;print([v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\\0') if v.startswith(b'RUNPOD_POD_ID=')])"
    if remote(state, 'python3 -c ' + shlex.quote(code)).decode().strip() != repr([pod]):
        raise ValueError('native SSH pod ID mismatch')


def guard_state(state):
    return dict(line.split('=', 1) for line in (Path(state)/'mac_guard/state').read_text().splitlines() if '=' in line)


def verify_guards(state, a):
    state = Path(state); info = guard_state(state)
    if info.get('pod') != a['pod_id'] or not time.time() < int(info['deadline']) <= a['hard_deadline']:
        raise ValueError('wrong pod/deadline in Mac guard state')
    if info.get('keys_staged') != '0': raise ValueError('account credential staged on pod')
    conn = read(state/'connection.json')
    if info.get('addr') != conn['ip'] + ':' + str(conn['port']): raise ValueError('guard SSH endpoint changed')
    pids, logs, armed = [], {}, []
    for role in ('hardstop', 'watchdog'):
        pid = int(info[role + '_pid']); os.kill(pid, 0)
        cmd = subprocess.check_output(['ps', '-o', 'args=', '-p', str(pid)], text=True)
        if 'ws2_' + role + '.sh' not in cmd or a['pod_id'] not in cmd: raise ValueError('wrong live guard PID')
        caf = int(info[role + '_caffeinate_pid']); os.kill(caf, 0)
        if 'caffeinate' not in subprocess.check_output(['ps', '-o', 'args=', '-p', str(caf)], text=True):
            raise ValueError('guard lacks live caffeinate')
        files = sorted((state/'mac_guard').glob(role + '*.log'), key=lambda p: p.stat().st_mtime)
        lines = [line for line in files[-1].read_text().splitlines() if 'armed: credential' in line and 'check http 200' in line] if files else []
        if not lines: raise ValueError('missing armed own-pod 200 receipt')
        pids.append(pid); logs[role] = str(files[-1]); armed.extend(lines)
    if len(set(pids)) != 2: raise ValueError('duplicate guard PIDs')
    return dict(guard_pids=pids, guard_logs=logs, armed_lines=armed, guards_live=True, guards_verified_at=time.time())


def output_paths():
    output = [str(p) for smoke in (False, True) for p in paths(REMOTE_REPO+'/'+DATA_REL, smoke).values()]
    if any('.rd.' not in PurePosixPath(p).name and not p.endswith('.rd') for p in output):
        raise ValueError('runner outputs must use registered rd pull suffix')
    return output + [REMOTE_REPO+'/'+OPS_RESULTS+'/'+name for name in OPS_OUTPUTS]


def arm(state, envfile, ssh_key):
    state = Path(state).resolve(); a = verified_bundle(state); remaining(a)
    if (state/'connection.json').exists(): raise ValueError('arm already attempted; reconcile without resetting')
    status(state, envfile)
    endpoint = X.endpoint(a['pod_id'], X.private_env(envfile)['RUNPOD_API_KEY'])
    (state/'connection.json').write_bytes(canonical(dict(endpoint, ssh_key=str(Path(ssh_key).resolve()))))
    own_id_check(state, a['pod_id'])
    # Arm directly on the forthcoming job PID and module-derived outputs.
    shared_tool(state, 'ws2_macguard.sh', ['arm', a['pod_id'], endpoint['ip']+':'+str(endpoint['port']),
        str(int(a['hard_deadline']-time.time())-60), '90', '/workspace/ws2_logs/job.pid', *output_paths()], envfile)
    # arm's watchdog initial stat command lacks paths; rearm fixes its watched-output list before posting the receipt.
    shared_tool(state, 'ws2_macguard.sh', ['rearm', a['pod_id'], '/workspace/ws2_logs/job.pid', *output_paths()], envfile)
    guards = verify_guards(state, a); check = status(state, envfile)
    line = 'R-D §42 armed: pod=' + a['pod_id'] + ' hardstop_pid=' + str(guards['guard_pids'][0]) + ' watchdog_pid=' + str(guards['guard_pids'][1]) + ' allocation_deadline=' + str(a['hard_deadline'])
    receipt = dict(check, **guards, credential_source='mac_account_env', guard_location='mac',
        mac_env_file=str(Path(envfile).resolve()), hard_deadline=a['hard_deadline'], assignment_sha256=assignment_sha(a),
        handoff_lines=[line, *guards['armed_lines']])
    return write_new(state/'guard_receipt.json', receipt)


def check_handoff(state, a, latest):
    receipt = read(Path(state)/'guard_receipt.json'); text = Path(HANDOFF_REL).read_text()
    if receipt['assignment_sha256'] != assignment_sha(a) or receipt['guard_pids'] != latest['guard_pids']:
        raise ValueError('posted guard receipt no longer matches live guards')
    if not all(line in text for line in receipt['handoff_lines']): raise ValueError('post exact armed lines in HANDOFF before work')
    if a['prior_guard_evidence'] not in text: raise ValueError('prior-owner guard evidence missing from HANDOFF')
    for pid in a['prior_guard_pids']:
        try: os.kill(pid, 0)
        except ProcessLookupError: continue
        raise ValueError('prior-owner guard PID still live: ' + str(pid))


def quiescent(state):
    code = """import pathlib,json
p=pathlib.Path('/workspace/ws2_logs/job.pid');alive=[]
if p.exists():
 pid=int(p.read_text().strip())
 for f in pathlib.Path('/proc').glob('[0-9]*/stat'):
  try:
   fields=f.read_text().split(') ',1)[1].split()
   if (int(f.parent.name)==pid or int(fields[2])==pid) and fields[0] not in ('Z','X'): alive.append(int(f.parent.name))
  except (FileNotFoundError,ProcessLookupError): pass
print(json.dumps({'quiescent':not alive}))
"""
    if not json.loads(remote(state, 'python3 -c ' + shlex.quote(code)))['quiescent']:
        raise ValueError('job/process group still active')


def chain_text(state):
    state = Path(state); a = verified_bundle(state)
    pins = dependency_pins((state/'requirements.txt').read_bytes())
    # These exact bytes were extracted from committed requirements, not the working checkout.
    exit_code = "import json,pathlib,sys,time; p=json.load(open('"+REMOTE_OPS+"/receipt.json')); p.update(exit_code=int(sys.argv[1]),finished_at=time.time()); pathlib.Path('"+REMOTE_REPO+'/'+OPS_RESULTS+"/exit.rd.json').write_text(json.dumps(p,sort_keys=True))"
    trap = 'rc=$?; trap - EXIT; python3 -c '+shlex.quote(exit_code)+' "$rc"; cp /workspace/ws2_logs/rd-pretext.log '+REMOTE_REPO+'/'+OPS_RESULTS+'/run_log.rd.txt; exit "$rc"'
    return '\n'.join(['#!/usr/bin/env bash', 'set -euo pipefail', 'cd '+REMOTE_REPO,
        'trap '+shlex.quote(trap)+' EXIT', 'set -a', 'source '+REMOTE_OPS+'/model.env', 'set +a',
        'unset RUNPOD_API_KEY', 'export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_DISABLE_XET=1 OMP_NUM_THREADS=4',
        'python3 -m venv --system-site-packages /workspace/rd_pretext_venv',
        '/workspace/rd_pretext_venv/bin/python -m pip install --disable-pip-version-check '+shlex.join(pins),
        '/workspace/rd_pretext_venv/bin/python -m pip freeze > /workspace/ws2_logs/venv_freeze.txt',
        shlex.join(['/workspace/rd_pretext_venv/bin/python','-m','projects.g_agreement.r_bench.rd_pretext_run','run',
                    '--bank',BANK_REL,'--out',DATA_REL,'--receipt',REMOTE_OPS+'/receipt.json']), ''])


def stage_bundle(state, a, receipt, hf_token=False):
    """All called after guards, own ID, HANDOFF, and quiescence checks."""
    state = Path(state); envfile = read(state/'guard_receipt.json')['mac_env_file']
    private = X.private_env(envfile)
    payload = dict(pod_id=a['pod_id'], hf_token=private.get('HF_TOKEN') if hf_token else None)
    code = """import json,sys,pathlib,shlex
p=json.load(sys.stdin)
ids=[v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\\0') if v.startswith(b'RUNPOD_POD_ID=')]
assert ids==[p['pod_id']]
r=pathlib.Path('/workspace/rd_pretext_ops');r.mkdir(exist_ok=False)
e='HF_HOME=/workspace/hf_cache\\n'
if p['hf_token']:e+='HF_TOKEN='+shlex.quote(p['hf_token'])+'\\n'
f=r/'model.env';f.write_text(e);f.chmod(0o600)
"""
    remote(state, 'python3 -c '+shlex.quote(code), canonical(payload))
    remote(state, 'cat > '+REMOTE_OPS+'/source.tar.gz', (state/'source.tar.gz').read_bytes())
    command = 'printf %s '+shlex.quote(sha(state/'source.tar.gz')+'  '+REMOTE_OPS+'/source.tar.gz\n')
    remote(state, command+' | sha256sum --check --status && mkdir '+REMOTE_REPO+' && tar -xzf '+REMOTE_OPS+'/source.tar.gz -C '+REMOTE_REPO)
    code = """import json,sys,pathlib
p=json.load(sys.stdin);r=pathlib.Path('/workspace/rd_pretext_repo');(r/'GIT_SHA').write_text(p['assignment']['source_commit']+'\\n')
(r/'cache').mkdir();out=r/'results/g_agreement/r/rd_pretext_ops';out.mkdir(parents=True,exist_ok=True)
assignment=dict(p['assignment'],**{k:p['receipt'][k] for k in ('run_id','run_kind','code_sha256')})
(out/'assignment.rd.json').write_text(json.dumps(assignment,sort_keys=True))
(out/'receipt.rd.json').write_text(json.dumps(p['receipt'],sort_keys=True))
pathlib.Path('/workspace/rd_pretext_ops/receipt.json').write_text(json.dumps(p['receipt'],sort_keys=True))
"""
    remote(state, 'python3 -c '+shlex.quote(code), canonical(dict(assignment=a, receipt=receipt)))


def launch(state, hf_token=False):
    state = Path(state).resolve(); a = verified_bundle(state); remaining(a)
    if (state/'launch_attempt.json').exists(): raise ValueError('run already attempted; do not repeat failed stage')
    check = status(state); own_id_check(state, a['pod_id']); quiescent(state)
    latest = verify_guards(state, a); check_handoff(state, a, latest)
    verify_pushed(a['source_commit'])
    receipt = dict(a, **check, **latest, phase='run', guard_location='mac', credential_source='mac_account_env',
                   science_cutoff=a['hard_deadline']-P.PULL_RESERVE_SECONDS, assignment_sha256=assignment_sha(a),
                   run_id='rd-'+uuid.uuid4().hex, run_kind='real', code_sha256=a['source_hashes']['projects/g_agreement/r_bench/rd_pretext_run.py'])
    write_new(state/'launch_attempt.json', dict(attempted_at=time.time(), assignment_sha256=assignment_sha(a)))
    stage_bundle(state, a, receipt, hf_token)
    # Recheck after transfer. The receipt carries the same live PIDs; never replace them behind HANDOFF.
    latest = verify_guards(state, a); check_handoff(state, a, latest); quiescent(state)
    script = state/'run.sh'; script.write_text(chain_text(state))
    cap = min(remaining(a), int(guard_state(state)['deadline'])-int(time.time())-60)
    if cap <= 0: raise ValueError('no science time remains after staging')
    conn = read(state/'connection.json')
    shared_tool(state, 'ws2_offvolume.sh', ['job',a['pod_id'],conn['ip']+':'+str(conn['port']),str(cap),
        'rd-pretext',str(script),'rd_pretext_repo','rd'])
    result = dict(receipt, launched_at=time.time(), timeout_seconds=cap, output_paths=output_paths())
    return write_new(state/'launch.json', result)


def validate_manifest(raw):
    allowed = {str(PurePosixPath(p).relative_to(REMOTE_REPO)) for p in output_paths()}; found = {}
    for line in raw.decode().splitlines():
        if not line.strip(): continue
        hash_, sep, name = line.partition('  ')
        if not sep or not re.fullmatch('[a-f0-9]{64}', hash_) or name not in allowed or name in found:
            raise ValueError('unregistered/invalid/duplicate pull path: '+name)
        found[name] = hash_
    if not found: raise ValueError('empty pull manifest')
    return found


def verify_local_pull(dest, found):
    dest = Path(dest)
    for name, expected in found.items():
        if name.startswith('cache/g_agreement/r/'): local = dest/'cache'/name.removeprefix('cache/g_agreement/r/')
        else: local = dest/'results'/name.removeprefix('results/g_agreement/')
        if local.is_symlink() or sha(local) != expected: raise ValueError('local pull hash mismatch: '+name)


def pull(state):
    state = Path(state).resolve(); a = verified_bundle(state); status(state); own_id_check(state,a['pod_id']); quiescent(state)
    conn = read(state/'connection.json')
    shared_tool(state,'ws2_offvolume.sh',['pull',a['pod_id'],conn['ip']+':'+str(conn['port']),'rd_pretext_repo','rd'])
    dest = state/'pulls/offvolume'/a['pod_id']; marker = read(dest/'PULL_VERIFIED.json')
    if marker.get('pod') != a['pod_id'] or marker.get('suffix') != 'rd' or marker.get('files',0) <= 0:
        raise ValueError('shared pull receipt does not match own outputs')
    command = 'cd '+REMOTE_REPO+" && find cache/g_agreement/r results/g_agreement -type f \\( -name '*.rd.*' -o -name '*.rd' \\) -exec sha256sum {} + 2>/dev/null | sort -k2"
    after = remote(state,command); found = validate_manifest(after)
    if digest(after) != marker['manifest_sha256'] or digest((dest/'pod_manifest.txt').read_bytes()) != marker['manifest_sha256'] or marker['files'] != len(found):
        raise ValueError('outputs changed during verified pull')
    verify_local_pull(dest,found); quiescent(state)
    receipt = dict(marker,assignment_sha256=assignment_sha(a),verified=True,quiescent=True,dest=str(dest),at=time.time())
    write_new(state/('pull-'+str(time.time_ns())+'.json'),receipt); (state/'latest_pull.json').write_bytes(canonical(receipt))
    return receipt


def release(state, receiver='integrator'):
    state = Path(state); a = verified_bundle(state); status(state); quiescent(state)
    if not re.fullmatch(r'[A-Za-z0-9._:/-]{1,80}',receiver): raise ValueError('named receiver required')
    receipt = pull(state); clearance = a.get('integrator_completion_clearance')
    if clearance:
        if a['pod_id'] not in clearance or clearance not in Path(HANDOFF_REL).read_text().splitlines() or not re.search(r'\bstop\b',clearance,re.I):
            raise ValueError('exact own-pod stop clearance missing from HANDOFF')
        shared_tool(state,'ws2_macguard.sh',['stop',a['pod_id'],'--confirm',clearance],_stop_authority=_STOP_AUTHORITY)
        stopped = status(state,running=False)
        if stopped['desired_status'] != 'EXITED': raise ValueError('stop not confirmed EXITED')
        result = dict(pod_id=a['pod_id'],action='verified-pull-then-stop',clearance=clearance,**stopped)
    else:
        verify_guards(state,a)
        mins = min(30,int((a['hard_deadline']-60-time.time())//60))
        if mins <= 0: raise ValueError('no warm hold remains before immutable hard deadline')
        conn = read(state/'connection.json')
        shared_tool(state,'ws2_offvolume.sh',['release',a['pod_id'],conn['ip']+':'+str(conn['port']),'rd_pretext_repo','rd',receiver,str(mins)])
        result = dict(pod_id=a['pod_id'],action='warm-return',receiver=receiver,**verify_guards(state,a))
    result.update(hard_deadline=a['hard_deadline'],pull_manifest_sha256=receipt['manifest_sha256'])
    return write_new(state/'completion.json',result)


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='cmd',required=True)
    for name in ('prepare','arm','launch','pull','release'):
        q = sub.add_parser(name); q.add_argument('--state',type=Path,required=True)
        if name == 'prepare': q.add_argument('--assignment',type=Path,required=True)
        if name == 'arm': q.add_argument('--env-file',type=Path,required=True); q.add_argument('--ssh-key',type=Path,required=True)
        if name == 'launch': q.add_argument('--hf-token',action='store_true')
        if name == 'release': q.add_argument('--receiver',default='integrator')
    args = parser.parse_args()
    if args.cmd == 'prepare': result = prepare(read(args.assignment),args.state)
    elif args.cmd == 'arm': result = arm(args.state,args.env_file,args.ssh_key)
    elif args.cmd == 'launch': result = launch(args.state,args.hf_token)
    elif args.cmd == 'pull': result = pull(args.state)
    else: result = release(args.state,args.receiver)
    print(json.dumps(result,sort_keys=True))


if __name__ == '__main__': main()
