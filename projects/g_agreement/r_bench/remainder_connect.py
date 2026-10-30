"""Connect one allocated remainder pod; secrets stay in SSH stdin and mode0600 remote file.

Credential transfer was explicitly authorized by the user on 2026-10-20. Never
prints or saves the generated credential-bearing script on the Mac.
"""
from __future__ import annotations
import argparse, ipaddress, json, math, os, re, shlex, subprocess, time
from pathlib import Path
from projects.g_agreement.r_bench.remainder_allocate import AllocationApi, ApiError, ROOT
from projects.g_agreement.r_bench.remainder_pod import bootstrap


def own_address(api,pod):
    query='query { pod(input: {podId: '+json.dumps(pod)+'}) { id runtime { ports { ip isIpPublic privatePort publicPort } } } }'
    record=api.request('https://api.runpod.io/graphql','POST',{'query':query}).get('data',{}).get('pod')
    if not record: return None
    if record.get('id')!=pod: raise ValueError('Single-pod API returned another ID')
    for p in (record.get('runtime') or {}).get('ports') or []:
        if p.get('privatePort')==22 and p.get('isIpPublic'):
            host=str(ipaddress.ip_address(p['ip']));port=int(p['publicPort'])
            if not 1<=port<=65535: raise ValueError('Invalid SSH port')
            return host,port
    return None


def credential_check_source():
    """Remote stdlib-only rule-9 check; never prints credentials or response bodies."""
    return '''import json, os, sys, urllib.error, urllib.request
pod = sys.argv[1]
request = urllib.request.Request(
    "https://rest.runpod.io/v1/pods/" + pod,
    headers={"Authorization": "Bearer " + os.environ["RUNPOD_API_KEY"],
             "User-Agent": "Mozilla/5.0 Remainder-GuardCheck/1.0"})
try:
    with urllib.request.urlopen(request, timeout=15) as response:
        status = response.status
        body = json.loads(response.read())
except urllib.error.HTTPError as exc:
    print("REFUSING TO ARM: account credential GET http " + str(exc.code) + " [/workspace/.env]")
    raise SystemExit(2)
except Exception as exc:
    print("REFUSING TO ARM: account credential GET failed " + type(exc).__name__ + " [/workspace/.env]")
    raise SystemExit(2)
if status != 200 or not isinstance(body, dict) or body.get("id") != pod:
    print("REFUSING TO ARM: account credential GET http " + str(status) + ", own-id mismatch [/workspace/.env]")
    raise SystemExit(2)
print("stop credential verified: http 200, own-id matched [/workspace/.env]")
'''


def first_script(exp,pod,seconds,api_key,hf_token,original_deadline):
    if any(not value or '\n' in value or '\r' in value for value in (api_key,hf_token)):
        raise ValueError('Credential missing or multiline')
    if not isinstance(original_deadline,(int,float)) or not math.isfinite(original_deadline) or original_deadline<=0:
        raise ValueError('Valid original absolute deadline required')
    script=bootstrap(exp,pod,pod,seconds,90)
    # Shared rule-9 checks can each take30s and run concurrently; wait long enough for both.
    script=script.replace('for try in $(seq 1 10); do','for try in $(seq 1 40); do',1)
    # Bound both the recorded deadline and the remote sleep to the original
    # allocation epoch; transport latency must never renew the remote cap.
    deadline=math.floor(original_deadline)-40
    script=script.replace(f'GUARD_DEADLINE=$((GUARD_STARTED + {seconds}))',
        f'GUARD_DEADLINE={deadline}\n[ "$GUARD_DEADLINE" -gt "$GUARD_STARTED" ] || {{ echo "Original cap exhausted"; exit 2; }}',1)
    script=script.replace(f'"$RUN/guards/ws2_hardstop.sh" "$POD" {seconds}',
        '"$RUN/guards/ws2_hardstop.sh" "$POD" "$((GUARD_DEADLINE - $(date +%s)))"',1)
    marker='[ ! -e "$RUN" ] || { echo "REFUSE reused run directory"; exit 2; }'
    secret_lines='\n'.join(['export RUNPOD_API_KEY='+shlex.quote(api_key),'export HF_TOKEN='+shlex.quote(hf_token),'export HF_HOME=/workspace/hf_cache'])
    setup='\n'.join(['set +x','umask 077','mkdir -p /workspace',
        "cat > /workspace/.env <<'REMAINDER_PRIVATE_ENV_EOF'",secret_lines,
        'REMAINDER_PRIVATE_ENV_EOF','chmod 0600 /workspace/.env',
        'set -a; source /workspace/.env >/dev/null 2>&1; set +a',
        "python3 - \"$POD\" <<'REMAINDER_STOP_CREDENTIAL_CHECK'",
        credential_check_source(), 'REMAINDER_STOP_CREDENTIAL_CHECK'])
    # bootstrap's explicit /proc/1/environ ID check precedes this only credential write.
    return script.replace(marker,marker+'\n'+setup,1)


def ssh_args(host,port,known_hosts):
    return ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','StrictHostKeyChecking=accept-new',
        '-o','UserKnownHostsFile='+str(known_hosts),'-p',str(port),'-i',str(Path.home()/'.ssh/id_ed25519_runpod'),'root@'+host]


def connect(receipt):
    receipt=receipt.resolve();allowed=ROOT/'results/g_agreement/r/remainder'
    if not receipt.is_relative_to(allowed): raise ValueError('Receipt outside remainder')
    record=json.loads(receipt.read_text());pod=record['pod_id'];exp=record['experiment']
    if record.get('deployment')!='off_volume': raise ValueError('Credential setup is only for a new off-volume pod')
    if not record.get('local_guard_armed'): raise ValueError('Mac watchdog has not armed')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',pod): raise ValueError('Invalid pod ID')
    os.kill(record['local_guard_pid'],0)
    key=os.environ['RUNPOD_API_KEY'];token=os.environ['HF_TOKEN'];api=AllocationApi(key)
    launch=ROOT/'cache/g_agreement/r/remainder'/exp/'launch'/pod;launch.mkdir(parents=True,exist_ok=True)
    boot_end=record['started_epoch']+record.get('boot_timeout_seconds',240)-20
    address=None
    while time.time()<boot_end:
        try: address=own_address(api,pod)
        except ApiError: address=None
        if address: break
        time.sleep(min(5,max(0,boot_end-time.time())))
    if not address: raise RuntimeError('Own SSH endpoint unavailable; independent Mac boot watchdog remains armed')
    host,port=address;args=ssh_args(host,port,launch/'known_hosts')
    remaining=int(record['started_epoch']+record['limit_seconds']-time.time()-40)
    if remaining<=60: raise RuntimeError('Original cap almost exhausted before bootstrap')
    script=first_script(exp,pod,remaining,key,token,record['started_epoch']+record['limit_seconds'])
    result=subprocess.run(args+['bash -s'],input=script,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=min(90,max(1,boot_end-time.time())))
    safe=result.stdout.replace(key,'[REDACTED]').replace(token,'[REDACTED]')
    (launch/'bootstrap.log').write_text(safe)
    if (result.returncode or f'ARMED /workspace/remainder/{exp}/{pod}' not in safe
            or 'stop credential verified: http 200, own-id matched [/workspace/.env]' not in safe):
        raise RuntimeError('Remote guards unconfirmed; see redacted bootstrap.log; Mac watchdog remains armed')
    ack=ROOT/record['armed_ack'];ack.write_text(json.dumps({'pod':pod,'remote_guards_verified':True,'at':time.time()})+'\n')
    connection={'pod':pod,'experiment':exp,'host':host,'port':port,'run_dir':f'/workspace/remainder/{exp}/{pod}',
        'known_hosts':str(launch/'known_hosts'),'original_deadline_epoch':record['started_epoch']+record['limit_seconds'],
        'receipt':str(receipt.relative_to(ROOT)),'credential_setup':'explicitly_authorized_SSH_stdin_mode0600',
        'remote_guards_verified':True,'stop_credential_http':200,'stop_credential_own_id_matched':True,
        'stop_credential_source':'/workspace/.env','connected_at':time.time()}
    (launch/'connection.json').write_text(json.dumps(connection,indent=2)+'\n')
    print(json.dumps(connection));return connection


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args();connect(a.receipt)
if __name__=='__main__':main()
