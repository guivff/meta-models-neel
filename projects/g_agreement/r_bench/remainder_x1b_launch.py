"""X1b-lite queue booking/registration gates and bounded phases. No pod allocation, resume or credential transfer."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import time
from projects.g_agreement.r_bench import remainder_x1b as D

CAP=5400
TOTAL=5400
RESERVE=300



def validate_booking(b,pod,now):
    if b.get('experiment')!='X1b-lite' or b.get('pod')!=pod or b.get('confirmed_by')!='integrator' or not b.get('handoff_line'):
        raise ValueError('Integrator booking for this pod required: '+str(pod))
    if b.get('mode')=='warm_off_volume':
        if b.get('network_volume_id') is not None or b.get('pull_all_before_stop') is not True or b.get('delete_after_queue') is not True:
            raise ValueError('Only an integrator-booked off-volume pod with pull/deletion obligations is allowed')
    elif b.get('mode')!='warm_network_volume' or not b.get('network_volume_id'):
        raise ValueError('X1b-lite requires a booked warm pod with verified storage')
    numbers=[b.get(k) for k in ('assigned_epoch','deadline_epoch','previous_billed_seconds')]
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in numbers):raise ValueError('Invalid booking times')
    start,end,spent=numbers
    if start>now or not 0<end-start<=CAP or spent<0 or spent+end-start>TOTAL:raise ValueError('Assignment/90-minute segment/1.5-hour total exceeded')
    if end-now<=RESERVE:raise ValueError('Pull reserve reached')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',str(b.get('segment_id',''))):raise ValueError('Invalid segment ID')
    return b


def pull_reserve(run,booking):
    proof=D.read(Path(run)/'bandwidth.json')
    rate=proof.get('bytes_per_second',0)
    if proof.get('pod')!=booking['pod'] or proof.get('bytes',0)<8*1024*1024 or not isinstance(rate,(int,float)) or not math.isfinite(rate) or rate<=0:
        raise ValueError('Measured, checksum-verified Mac pull bandwidth required')
    if not re.fullmatch(r'[0-9a-f]{64}',proof.get('sha256','')) or not booking['assigned_epoch']<=proof.get('measured_epoch',0)<=time.time():raise ValueError('Stale/invalid bandwidth proof')
    return max(RESERVE,math.ceil(1.5*350_000_000/rate+60))


def measure_bandwidth(booking,run,host,port,identity,out):
    import shlex
    b=booking;validate_booking(b,b['pod'],time.time());run=str(run)
    if not re.fullmatch(r'/workspace/remainder/x1b/[A-Za-z0-9_-]{1,80}',run):raise ValueError('Invalid run path')
    ssh=['ssh','-o','BatchMode=yes','-o','Compression=no','-o','ConnectTimeout=10','-i',str(identity),'-p',str(port),'root@'+host]
    payload="""import hashlib,json,sys,os
from pathlib import Path
pod,run=sys.argv[1:]
ids=[s.split(b'=',1)[1].decode() for s in Path('/proc/1/environ').read_bytes().split(b'\\0') if s.startswith(b'RUNPOD_POD_ID=')]
assert ids==[pod],'POD ID MISMATCH'
# Bootstrap must already have armed this exact segment.
b=json.loads(Path(run,'booking.json').read_text())
for name in ('watchdog','hardstop'):
 assert 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' in Path(run,name+'.'+b['segment_id']+'.log').read_text()
p=Path(run,'bandwidth_sample.bin');data=os.urandom(8*1024*1024);p.write_bytes(data)
print(json.dumps({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}))
"""
    cmd='python3 - '+shlex.quote(b['pod'])+' '+shlex.quote(run)
    left=lambda:max(1,min(120,b['deadline_epoch']-RESERVE-time.time()))
    proof=json.loads(subprocess.run(ssh+[cmd],input=payload,text=True,capture_output=True,check=True,timeout=left()).stdout)
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);sample=out.with_suffix('.sample.bin');start=time.monotonic()
    subprocess.run(['scp','-q','-o','Compression=no','-i',str(identity),'-P',str(port),'root@'+host+':'+run+'/bandwidth_sample.bin',str(sample)],check=True,timeout=left())
    elapsed=time.monotonic()-start
    if sample.stat().st_size!=proof['bytes'] or D.sha(sample)!=proof['sha256']:raise ValueError('Bandwidth sample checksum differs')
    result={**proof,'pod':b['pod'],'measured_epoch':time.time(),'elapsed_seconds':elapsed,'bytes_per_second':proof['bytes']/elapsed}
    D.save(out,result);subprocess.run(['scp','-q','-i',str(identity),'-P',str(port),str(out),'root@'+host+':'+run+'/bandwidth.json'],check=True,timeout=left())
    return result


def live_check(pod,run):
    run=Path(run)
    if not re.fullmatch(r'/workspace/remainder/x1b/[A-Za-z0-9_-]{1,80}',str(run)):raise ValueError('Private X1b-lite volume run path required')
    raw=(run/'booking.json').read_bytes();b=json.loads(raw);validate_booking(b,pod,time.time())
    def check():
        if (run/'booking.json').read_bytes()!=raw:raise ValueError('Booking changed inside segment')
        validate_booking(b,pod,time.time())
        if b['deadline_epoch']-time.time()<=pull_reserve(run,b):raise ValueError('Measured Mac pull reserve reached')
        ids=[s.split(b'=',1)[1].decode() for s in Path('/proc/1/environ').read_bytes().split(b'\0') if s.startswith(b'RUNPOD_POD_ID=')]
        if ids!=[pod]:raise ValueError('POD ID MISMATCH')
        if not run.resolve().is_relative_to('/workspace'):raise ValueError('Run escaped private workspace')
        receipt=D.read(run/'volume.json')
        validate_storage(b,receipt)
        if b['mode']=='warm_network_volume' and (not os.path.ismount('/workspace') or run.stat().st_dev!=Path('/workspace').stat().st_dev):raise ValueError('Not on mounted network volume')
        for name in ('watchdog','hardstop'):
            log=(run/f'{name}.{b["segment_id"]}.log').read_text()
            if pod not in log or 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' not in log:raise ValueError('Rule-9 guard proof missing')
            pid=int((run/f'{name}.{b["segment_id"]}.pid').read_text())
            if pid<=1:raise ValueError('Invalid guard PID')
            os.kill(pid,0)
    check();return check


def validate_storage(booking,receipt):
    if receipt.get('pod')!=booking['pod'] or receipt.get('http_status')!=200:
        raise ValueError('Own-pod storage API proof missing')
    if receipt.get('mode')!=booking['mode'] or receipt.get('network_volume_id')!=booking.get('network_volume_id'):
        raise ValueError('Own-pod storage differs from booking')
    return receipt


def check_registration(run,plan):
    r=D.read(Path(run)/'registration.json')
    if r.get('experiment')!='X1b-lite' or r.get('confirmed_by')!='integrator' or not r.get('handoff_line') or not isinstance(r.get('section'),int):raise ValueError('Integrator section confirmation missing')
    if r.get('plan_sha256')!=D.digest(plan):raise ValueError('Unregistered item plan')
    brief=D.ROOT/'projects/g_agreement/BRIEF_R.md'
    heading=f"## {r['section']}. X1b-lite"
    if heading not in brief.read_text() or r.get('brief_sha256')!=D.sha(brief):raise ValueError('Committed X1b-lite section missing/changed')
    if not re.fullmatch(r'[0-9a-f]{40}',r.get('prereg_commit','')) or not r.get('pushed_before_compute'):raise ValueError('Pushed preregistration receipt missing')
    return r


def check_layer_release(run,decision):
    r=D.read(Path(run)/'layer_release.json')
    if r.get('decision_sha256')!=D.sha(decision) or not r.get('pushed_before_test') or not re.fullmatch(r'[0-9a-f]{40}',r.get('commit','')):raise ValueError('Pilot layer decision must be pulled, committed and pushed before test scoring')
    if D.read(decision).get('selection_uses_test_outcomes') is not False:raise ValueError('Invalid pool-only decision')


def inventory(run):
    run=Path(run);files={}
    segment=D.read(run/'booking.json')['segment_id'];bundle=run/'pull_bundle'/segment
    if bundle.exists():raise ValueError('Immutable pull bundle already exists; verify/pull it rather than overwrite')
    bundle.mkdir(parents=True)
    # Only the experiment's data and log/receipt files; never secrets or the whole repository.
    paths=list((run/D.DATA_REL).rglob('*'))
    paths += [p for p in run.iterdir() if p.is_file() and (p.suffix in ('.json','.log','.pid','.sh') or p.name=='job.log') and p.name not in ('pull_manifest.json','mac_receipt.json')]
    for p in sorted(set(paths)):
        if p.is_symlink():raise ValueError('Symlink in output inventory')
        if p.is_file():
            rel=p.relative_to(run);dest=bundle/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
            files[str(rel)]={'bytes':dest.stat().st_size,'sha256':D.sha(dest)}
    if not files:raise ValueError('No outputs to pull')
    return {'experiment':'X1b-lite','pod':D.read(run/'booking.json')['pod'],'bundle':str(bundle.relative_to(run)),'files':files,'bytes':sum(x['bytes'] for x in files.values())}


def receipt(local,manifest):
    if sys.platform!='darwin':raise ValueError('Pull receipt must be produced on the Mac')
    m=D.read(manifest)
    for name,entry in m['files'].items():
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe pull path')
        p=Path(local)/rel
        if p.is_symlink() or not p.is_file() or p.stat().st_size!=entry['bytes'] or D.sha(p)!=entry['sha256']:raise ValueError('Mac pull checksum mismatch: '+name)
    return {'experiment':'X1b-lite','pod':m['pod'],'manifest_sha256':D.sha(manifest),'verified_on':'Mac','verified_epoch':time.time(),'files':m['files']}


def verify_pull(run):
    run=Path(run);r=D.read(run/'mac_receipt.json');m=D.read(run/'pull_manifest.json')
    if r.get('verified_on')!='Mac' or r.get('manifest_sha256')!=D.sha(run/'pull_manifest.json') or r.get('files')!=m['files']:raise ValueError('Mac receipt mismatch')
    # Data bytes are immutable after phase completion; logs can grow while guards run.
    for name,entry in m['files'].items():
        if not name.startswith(D.DATA_REL.as_posix()+'/'):continue
        p=run/name
        if p.stat().st_size!=entry['bytes'] or D.sha(p)!=entry['sha256']:raise ValueError('Remote data changed after pull')
    return {'verified':True,'pod':r['pod']}


def warm_handback(pod,run):
    """Verify final pull and reserve a bounded warm handover; never retire guards."""
    import datetime
    run=Path(run);b=D.read(run/'booking.json');now=time.time()
    ids=[x.split(b'=',1)[1].decode() for x in Path('/proc/1/environ').read_bytes().split(b'\0') if x.startswith(b'RUNPOD_POD_ID=')]
    if ids!=[pod] or b.get('pod')!=pod:raise ValueError('Handover pod mismatch: '+str(pod))
    proof=verify_pull(run)
    if proof['pod']!=pod:raise ValueError('Pull pod mismatch: '+str(proof['pod']))
    manifest=D.read(run/'pull_manifest.json')
    actual={str(p.relative_to(run)) for p in (run/D.DATA_REL).rglob('*') if p.is_file()}
    expected={n for n in manifest['files'] if n.startswith(D.DATA_REL.as_posix()+'/')}
    if actual!=expected:raise ValueError('Pull file set differs: '+str(sorted(actual^expected)))
    guards={}
    for name in ('watchdog','hardstop'):
        path=run/f'{name}.{b["segment_id"]}.log'
        log=path.read_text()
        if pod not in log or 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' not in log:raise ValueError('Unarmed guard: '+str(path))
        pid=int((run/f'{name}.{b["segment_id"]}.pid').read_text())
        if pid<=1:raise ValueError('Invalid guard: '+str(pid))
        os.kill(pid,0);guards[name]=pid
    until=min(b['deadline_epoch'],now+1800)
    if until<=now:raise ValueError('Handover deadline elapsed: '+str(b['deadline_epoch']))
    (run/'reservation').write_text('job=X1b-lite-warm-handover\nuntil='+datetime.datetime.fromtimestamp(until,datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')+'\n')
    result={'status':'HANDOVER_READY','custody_transferred':False,'guards':guards,'deadline_epoch':b['deadline_epoch'],'reservation_until_epoch':until,'manifest_sha256':D.sha(run/'pull_manifest.json'),**D.provenance(pod)}
    D.save(run/'warm_handback.json',result)
    return result


def run_phase(pod,run,phase,plan):
    if phase=='reuse':raise ValueError('Fresh H100 capture required; rejected phase: reuse')
    check=live_check(pod,run);check_registration(run,D.read(plan));b=D.read(run/'booking.json');check()
    cmd=[sys.executable,'-m','projects.g_agreement.r_bench.remainder_x1b_collect','--phase',phase,'--pod',pod,'--run-dir',str(run),'--plan',str(plan)]
    env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',XDG_CACHE_HOME=str(run/'runtime_cache'),TORCHINDUCTOR_CACHE_DIR=str(run/'runtime_cache/torch'),TRITON_CACHE_DIR=str(run/'runtime_cache/triton'))
    for k in list(env):
        if any(s in k.upper() for s in ('TOKEN','API_KEY','SECRET','PASSWORD')):env.pop(k)
    began=time.time();child=subprocess.Popen(cmd,start_new_session=True,env=env)
    try:code=child.wait(timeout=max(1,b['deadline_epoch']-pull_reserve(run,b)-time.time()))
    except (subprocess.TimeoutExpired,BaseException):
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        raise
    finally:
        from projects.g_agreement.r_bench.remainder_x1b_collect import write_rows
        write_rows(run/D.DATA_REL/'phase_ledger.jsonl',[{'phase':phase,'started_epoch':began,'ended_epoch':time.time(),'wall_seconds':time.time()-began,'exit_code':child.returncode,**D.provenance(pod)}])
    if code:raise subprocess.CalledProcessError(code,cmd)
    check();return {'phase':phase,'status':'PASS'}


def bootstrap(booking,run):
    import base64,shlex
    b=booking;validate_booking(b,b['pod'],time.time())
    run=str(run)
    if not re.fullmatch(r'/workspace/remainder/x1b/[A-Za-z0-9_-]{1,80}',run):raise ValueError('Invalid X1b-lite run path')
    encoded={name:base64.b64encode((D.ROOT/'results/g_agreement/r/pod_tools'/name).read_bytes()).decode() for name in ('ws2_watchdog.sh','ws2_hardstop.sh','ws2_selfstop.sh')}
    q=shlex.quote
    # Literal Python payload contains public booking metadata and reviewed guard source only.
    payload=json.dumps({'booking':b,'scripts':encoded})
    return f'''#!/usr/bin/env bash
set -euo pipefail
POD={q(b['pod'])}
OWN=$(tr '\\0' '\\n' < /proc/1/environ | sed -n 's/^RUNPOD_POD_ID=//p' | head -1)
[ "$OWN" = "$POD" ] || {{ echo 'POD ID MISMATCH'; exit 2; }}
RUN={q(run)}
SEG={q(b['segment_id'])}
mkdir -p "$RUN/guards"
[ ! -f "$RUN/hardstop.$SEG.pid" ] || {{ echo 'Segment already armed; refuse to renew'; exit 2; }}
python3 - "$RUN" <<'X1b-lite_BOOTSTRAP_DATA'
import base64,json,sys
from pathlib import Path
x=json.loads({payload!r});root=Path(sys.argv[1]);p=root/'booking.json'
# Preserve the prior segment receipt before installing the integrator's new booking.
if p.exists():
 old=json.loads(p.read_text())
 if old['segment_id']==x['booking']['segment_id'] and old!=x['booking']:raise SystemExit('Cannot renew a segment')
 if old['segment_id']!=x['booking']['segment_id']:(root/('booking.'+old['segment_id']+'.json')).write_bytes(p.read_bytes())
p.write_text(json.dumps(x['booking'],indent=2)+'\\n')
for name,data in x['scripts'].items():
 target=root/'guards'/name
 # Separate segment copies: never overwrite a running script.
 target=root/'guards'/x['booking']['segment_id']/name
 target.parent.mkdir(parents=True,exist_ok=True)
 raw=base64.b64decode(data)
 if target.exists() and target.read_bytes()!=raw:raise SystemExit('Cannot replace a live segment guard')
 if not target.exists():target.write_bytes(raw)
X1b-lite_BOOTSTRAP_DATA
LEFT=$(({int(b['deadline_epoch'])}-$(date +%s)-40))
[ "$LEFT" -gt 300 ] || {{ echo 'Pull reserve reached'; exit 2; }}
# No code/data staging before both shared guards are armed.
nohup bash "$RUN/guards/${{SEG}}/ws2_hardstop.sh" "$POD" "$LEFT" > "$RUN/hardstop.$SEG.log" 2>&1 < /dev/null &
printf '%s\\n' "$!" > "$RUN/hardstop.$SEG.pid"
WD_CEIL=90 WD_RESERVE_FILE="$RUN/reservation" nohup bash "$RUN/guards/${{SEG}}/ws2_watchdog.sh" "$POD" "$RUN/job.pid" "$RUN/job.log" > "$RUN/watchdog.$SEG.log" 2>&1 < /dev/null &
printf '%s\\n' "$!" > "$RUN/watchdog.$SEG.pid"
for i in $(seq 1 40); do
 if grep -q 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' "$RUN/hardstop.$SEG.log" && grep -q 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' "$RUN/watchdog.$SEG.log"; then break; fi
 sleep 1
done
grep -q 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' "$RUN/hardstop.$SEG.log"
grep -q 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' "$RUN/watchdog.$SEG.log"
kill -0 "$(cat "$RUN/hardstop.$SEG.pid")" "$(cat "$RUN/watchdog.$SEG.pid")"
# Existing volume account key is used solely for own-pod volume verification; never copied or printed.
(set -a; source /workspace/.env; set +a
 python3 - "$POD" "$RUN" <<'X1b-lite_VOLUME_CHECK'
import json,os,sys,urllib.request
from pathlib import Path
pod,run=sys.argv[1:];booking=json.loads(Path(run,'booking.json').read_text());volume=booking.get('network_volume_id');request=urllib.request.Request('https://rest.runpod.io/v1/pods/'+pod,headers={{'Authorization':'Bearer '+os.environ['RUNPOD_API_KEY'],'User-Agent':'Remainder-X1b-lite/1.0'}})
with urllib.request.urlopen(request,timeout=30) as response:
 status=response.status;body=json.load(response)
assert status==200 and body.get('id')==pod and body.get('networkVolumeId')==volume,'Own-pod network-volume mismatch'
assert Path(run).resolve().is_relative_to('/workspace'),'Run escaped workspace'
if booking['mode']=='warm_network_volume':
 assert os.path.ismount('/workspace') and Path(run).stat().st_dev==Path('/workspace').stat().st_dev,'Not volume mounted'
Path(run,'volume.json').write_text(json.dumps({{'pod':pod,'network_volume_id':volume,'http_status':200,'mode':booking['mode']}})+'\\n')
X1b-lite_VOLUME_CHECK
)
python3 - "$RUN/reservation" <<'X1b-lite_RESERVATION'
import datetime,time,sys
until=min({int(b['deadline_epoch'])},int(time.time())+1800)
open(sys.argv[1],'w').write('job=X1b-lite\\nuntil='+datetime.datetime.fromtimestamp(until,datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')+'\\n')
X1b-lite_RESERVATION
echo 'X1b-lite SHARED GUARDS AND BOOKED STORAGE VERIFIED; integrator must transfer ownership before staging'
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['bootstrap','measure','phase','inventory','receipt','verify-pull','warm-handback']);p.add_argument('--booking',type=Path);p.add_argument('--ssh-host');p.add_argument('--ssh-port',type=int);p.add_argument('--ssh-identity',type=Path);p.add_argument('--phase',choices=['reuse','capture','smoke','readers','nla','pilot','target']);p.add_argument('--pod');p.add_argument('--run-dir',type=Path);p.add_argument('--plan',type=Path,default=D.OUT/'pilot_plan.json');p.add_argument('--manifest',type=Path);p.add_argument('--local',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    if a.action=='bootstrap':
        script=bootstrap(D.read(a.booking),a.run_dir)
        if a.out:a.out.write_text(script)
        else:print(script)
        return
    if a.action=='measure':
        result=measure_bandwidth(D.read(a.booking),a.run_dir,a.ssh_host,a.ssh_port,a.ssh_identity,a.out)
        print(json.dumps(result));return
    if a.action=='phase':result=run_phase(a.pod,a.run_dir,a.phase,a.plan)
    elif a.action=='inventory':result=inventory(a.run_dir)
    elif a.action=='receipt':result=receipt(a.local,a.manifest)
    elif a.action=='warm-handback':result=warm_handback(a.pod,a.run_dir)
    else:result=verify_pull(a.run_dir)
    if a.out:D.save(a.out,result)
    print(json.dumps(result))

if __name__=='__main__':main()
