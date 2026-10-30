"""Mac-only X4 guard adapter. Normal completion never stops or deletes a pod."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
import re
from projects.g_agreement.r_bench import x4_cue_ops as O


def tool_env(state, envfile=None):
    state = Path(state).resolve()
    connection = O.read_json(state / 'connection.json')
    env = dict(os.environ, WS2_MAC_GUARD_DIR=str(state / 'mac_guard'),
               WS2_SSH_KEY=connection['ssh_key'], WD_RESERVE_FILE=str(state / 'reservation.flag'))
    if envfile is None:
        envfile = O.read_json(state / 'guard_receipt.json')['mac_env_file']
    env['RUNPOD_SECRETS'] = str(Path(envfile).resolve())
    return env


def guard_state(state):
    values = {}
    for line in (Path(state) / 'mac_guard/state').read_text().splitlines():
        key, value = line.split('=', 1)
        values[key] = value
    return values


def verify_live_guards(state, a):
    """Mac PID checks belong here, before each dispatch, not on the Linux pod."""
    state = Path(state)
    info = guard_state(state)
    if info.get('pod') != a['pod_id'] or int(info['deadline']) > a['hard_deadline'] or int(info['deadline']) <= time.time():
        raise ValueError('Mac guard pod/deadline mismatch: ' + str(info.get('pod')))
    pids, logs = [], {}
    for role in ('hardstop', 'watchdog'):
        pid = int(info[role + '_pid'])
        os.kill(pid, 0)
        command = subprocess.check_output(['ps', '-o', 'args=', '-p', str(pid)], text=True)
        if 'ws2_' + role + '.sh' not in command or a['pod_id'] not in command:
            raise ValueError('wrong Mac guard process: ' + role + ':' + str(pid))
        caf = int(info[role + '_caffeinate_pid'])
        os.kill(caf, 0)
        cafcmd = subprocess.check_output(['ps', '-o', 'args=', '-p', str(caf)], text=True)
        if 'caffeinate' not in cafcmd:
            raise ValueError('wrong caffeinate process: ' + str(caf))
        candidates = sorted((state / 'mac_guard').glob(role + '*.log'), key=lambda p: p.stat().st_mtime)
        log = candidates[-1]
        if not any('armed: credential' in line and 'check http 200' in line for line in log.read_text().splitlines()):
            raise ValueError('Mac guard lacks own-id 200 arming receipt: ' + role)
        pids.append(pid); logs[role] = str(log)
    if len(set(pids)) != len(pids):
        raise ValueError('duplicate Mac guard PID: ' + str(pids))
    return pids, logs


def mac_tool(state, args, envfile=None):
    subprocess.run(['bash', str(Path(state) / 'tools/ws2_macguard.sh'), *args],
                   env=tool_env(state, envfile), check=True, start_new_session=True)


def arm(state, envfile, ssh_key):
    state = Path(state).resolve()
    a, archive, code, guards = O.verified_bundle(state)
    O.remaining(a, science=True)
    if (state / 'connection.json').exists():
        raise ValueError('already attempted; reconcile durable state, never reset')
    status = O.checked_status(a['pod_id'], envfile)
    private = O.private_env(envfile)
    connection = O.endpoint(a['pod_id'], private['RUNPOD_API_KEY'])
    O.write_new(state / 'connection.json', dict(connection, ssh_key=str(Path(ssh_key).resolve())))
    tools = state / 'tools'; tools.mkdir()
    for name, content in guards.items():
        (tools / name).write_text(content)
    address = connection['ip'] + ':' + str(connection['port'])
    # Shared tooling makes the native-ID check its first SSH command, and arms
    # both guards under caffeinate before any source/credential staging.
    mac_tool(state, ['arm', a['pod_id'], address, str(O.remaining(a) - 60), '45',
                     '/workspace/ws2_logs/job.pid'], envfile)
    pids, logs = verify_live_guards(state, a)
    status = O.checked_status(a['pod_id'], envfile)
    receipt = dict(status, credential_source='mac_account_env', guard_location='mac',
                   mac_env_file=str(Path(envfile).resolve()), guard_pids=pids, guard_logs=logs,
                   status_id_matched=True, assignment_sha256=O.digest(O.canonical(a)),
                   hard_deadline=a['hard_deadline'], armed_at=time.time(), guards_verified_at=time.time())
    O.validate_guard_receipt(a, receipt)
    O.write_new(state / 'guard_receipt.json', receipt)
    payload = {'assignment': a, 'receipt': receipt, 'code': code,
               'hf_token': private.get('HF_TOKEN')}
    program = '''import json,sys,pathlib,shlex,os
p=json.load(sys.stdin); a=p['assignment']
ids=[v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\\0') if v.startswith(b'RUNPOD_POD_ID=')]
assert ids==[a['pod_id']], 'native ID changed'
r=pathlib.Path('/workspace/x4_ops'); r.mkdir(parents=True,exist_ok=False)
(r/'x4_cue_ops.py').write_text(p['code'])
for name,value in [('assignment.json',a),('guard_receipt.json',p['receipt'])]: (r/name).write_text(json.dumps(value))
e='HF_HOME=/workspace/hf_cache\\n'
if p['hf_token']: e+='HF_TOKEN='+shlex.quote(p['hf_token'])+'\\n'
f=r/'model.env'; f.write_text(e); f.chmod(0o600)
'''
    O.remote(state, 'python3 -c ' + shlex.quote(program), O.canonical(payload))
    O.remote(state, 'cat > ' + O.REMOTE_OPS + '/source.tar', archive)
    O.remote(state, 'echo ' + shlex.quote(O.digest(archive) + '  ' + O.REMOTE_OPS + '/source.tar') +
             ' | sha256sum --check --status && mkdir ' + O.REMOTE_REPO + ' && tar -xf ' + O.REMOTE_OPS + '/source.tar -C ' + O.REMOTE_REPO)
    O.remote(state, "printf '%s\\n' " + shlex.quote(a['source_commit']) + ' > ' + O.REMOTE_REPO + '/GIT_SHA')
    cache = '/workspace/x4_data/cache' if a['off_volume'] else '/workspace/mats-minis/cache'
    O.remote(state, 'mkdir -p ' + cache + ' && ln -s ' + cache + ' ' + O.REMOTE_REPO + '/cache && ls -la ' + O.REMOTE_REPO + '/cache')
    return receipt


def launch(state, stage):
    from projects.g_agreement.r_bench import x4_cue_run as R
    state = Path(state).resolve()
    a = O.read_json(state / 'assignment.json')
    guard = O.read_json(state / 'guard_receipt.json')
    O.checked_status(a['pod_id'], guard['mac_env_file'])
    verify_live_guards(state, a)
    outputs = [str(path) for path in R.output_paths(O.REMOTE_REPO + '/' + O.DATA_REL).values() if path.suffix == '.jsonl']
    outputs.append('/workspace/ws2_logs/x4-' + stage + '.log')
    mac_tool(state, ['rearm', a['pod_id'], '/workspace/ws2_logs/job.pid', *outputs])
    pids, logs = verify_live_guards(state, a)
    guard.update(guard_pids=pids, guard_logs=logs, guards_verified_at=time.time())
    (state / 'guard_receipt.json').write_text(json.dumps(guard, sort_keys=True))
    phases = O.stage_phases(stage)
    selection = None if stage == 'select' else O.read_json(state / 'selection_freeze.json')
    for phase in phases:
        receipt = O.phase_receipt(a, guard, phase, selection)
        O.remote(state, 'test ! -e ' + O.REMOTE_OPS + '/' + phase + '.json && cat > ' + O.REMOTE_OPS + '/' + phase + '.json', O.canonical(receipt))
    script = O.chain_text(stage)
    script_path = state / (stage + '.sh')
    script_path.write_text(script)
    connection = O.read_json(state / 'connection.json')
    # Shared job command checks live Mac PIDs and nests timeout within the guards.
    subprocess.run(['bash', str(state / 'tools/ws2_offvolume.sh'), 'job', a['pod_id'],
                    connection['ip'] + ':' + str(connection['port']), str(O.remaining(a, science=True)),
                    'x4-' + stage, str(script_path)], env=tool_env(state), check=True)
    O.write_new(state / (stage + '_launch.json'), {'at': time.time(), 'hard_deadline': a['hard_deadline'],
                'chain_sha256': O.digest(script.encode()), 'guard_pids': pids, 'guard_location': 'mac'})


def finish(state, envfile, stage, disposition, queue_evidence, receiver_job=None):
    """Verify the pull, then return warm to the integrator; no provider mutations."""
    state = Path(state)
    a = O.read_json(state / 'assignment.json')
    receipt = O.read_json(state / (stage + '_pull.json'))
    O.same_assignment(a, receipt)
    if not receipt.get('verified') or not queue_evidence.strip() or disposition != 'handover':
        raise ValueError('verified pull and dated warm handover evidence required')
    if (state / 'evaluate_launch.json').exists() and stage == 'select':
        raise ValueError('selection-only pull is stale after evaluation launch')
    O.verify_closure_snapshot(state, a, receipt, stage, envfile)
    status, body = O.provider(a['pod_id'], O.private_env(envfile)['RUNPOD_API_KEY'])
    if status != 200 or body.get('id') != a['pod_id'] or body.get('desiredStatus') != 'RUNNING':
        raise ValueError('warm handover needs own-ID RUNNING status')
    pids, _ = verify_live_guards(state, a)
    if not re.fullmatch(r'[A-Za-z0-9._:/-]{1,80}', receiver_job or ''):
        raise ValueError('name the queued receiver job for the warm reservation')
    until = min(time.time() + 1800, a['hard_deadline'] - 60)
    if until <= time.time():
        raise ValueError('no warm reservation time remains within X4 cap')
    (state / 'reservation.flag').write_text('job=' + receiver_job + '\nuntil=' + time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(until)) + '\n')
    result = {'pod_id': a['pod_id'], 'action': 'warm-handover-ready', 'at': time.time(),
              'queue_evidence': queue_evidence, 'pull_manifest_sha256': receipt['manifest_sha256'],
              'guard_pids': pids, 'hard_deadline': a['hard_deadline'], 'receiver_job': receiver_job, 'reservation_until': until,
              'receiver_must_arm_before_retiring_x4_guards': True}
    O.write_new(state / 'handover_ready.json', result)
    return result
