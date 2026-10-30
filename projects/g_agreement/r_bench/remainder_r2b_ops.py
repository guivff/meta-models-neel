"""Render assigned-volume guard bootstrap; never allocate/resume a pod."""
from pathlib import Path
import json,re,time,subprocess
from projects.g_agreement.r_bench import remainder_r2b_runner as R

def bootstrap(booking,run):
    import base64,shlex
    b=booking;R.validate_booking(b,time.time())
    run=str(run)
    if not re.fullmatch(r'/workspace/remainder/r2b/[A-Za-z0-9_-]{1,80}',run):raise ValueError('Invalid R2-B run path: '+run)
    encoded={name:base64.b64encode((Path(__file__).resolve().parents[3]/'results/g_agreement/r/pod_tools'/name).read_bytes()).decode() for name in ('ws2_watchdog.sh','ws2_hardstop.sh')}
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
[ ! -f "$RUN/hardstop.pid" ] || {{ echo 'Segment already armed; refuse to renew'; exit 2; }}
python3 - "$RUN" <<'R2-B_BOOTSTRAP_DATA'
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
R2-B_BOOTSTRAP_DATA
LEFT=$(({int(b['segment_deadline'])}-$(date +%s)-40))
[ "$LEFT" -gt 300 ] || {{ echo 'Pull reserve reached'; exit 2; }}
# No code/data staging before both shared guards are armed.
nohup bash "$RUN/guards/${{SEG}}/ws2_hardstop.sh" "$POD" "$LEFT" > "$RUN/hardstop.log" 2>&1 < /dev/null &
printf '%s\\n' "$!" > "$RUN/hardstop.pid"
WD_CEIL=45 WD_RESERVE_FILE="$RUN/reservation" nohup bash "$RUN/guards/${{SEG}}/ws2_watchdog.sh" "$POD" "$RUN/job.pid" "$RUN/job.log" > "$RUN/watchdog.log" 2>&1 < /dev/null &
printf '%s\\n' "$!" > "$RUN/watchdog.pid"
for i in $(seq 1 40); do
 if grep -q 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' "$RUN/hardstop.log" && grep -q 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' "$RUN/watchdog.log"; then break; fi
 sleep 1
done
grep -q 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' "$RUN/hardstop.log"
grep -q 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' "$RUN/watchdog.log"
kill -0 "$(cat "$RUN/hardstop.pid")" "$(cat "$RUN/watchdog.pid")"
# Existing volume account key is used solely for own-pod volume verification; never copied or printed.
(set -a; source /workspace/.env; set +a
 python3 - "$POD" "$RUN" <<'R2-B_VOLUME_CHECK'
import json,os,sys,urllib.request
from pathlib import Path
pod,run=sys.argv[1:];booking=json.loads(Path(run,'booking.json').read_text());volume=booking.get('network_volume_id');request=urllib.request.Request('https://rest.runpod.io/v1/pods/'+pod,headers={{'Authorization':'Bearer '+os.environ['RUNPOD_API_KEY'],'User-Agent':'Remainder-R2-B/1.0'}})
with urllib.request.urlopen(request,timeout=30) as response:
 status=response.status;body=json.load(response)
assert status==200 and body.get('id')==pod and body.get('networkVolumeId')==volume and body.get('gpuCount')==1,'Own-pod network-volume mismatch'
assert Path(run).resolve().is_relative_to('/workspace'),'Run escaped workspace'
if True:
 assert os.path.ismount('/workspace') and Path(run).stat().st_dev==Path('/workspace').stat().st_dev,'Not volume mounted'
Path(run,'volume.json').write_text(json.dumps({{'pod':pod,'network_volume_id':volume,'http_status':200,'mounted':True}})+'\\n')
R2-B_VOLUME_CHECK
)
python3 - "$RUN/reservation" <<'R2-B_RESERVATION'
import datetime,time,sys
until=min({int(b['segment_deadline'])},int(time.time())+1800)
open(sys.argv[1],'w').write('job=R2-B\\nuntil='+datetime.datetime.fromtimestamp(until,datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')+'\\n')
R2-B_RESERVATION
echo 'R2-B SHARED GUARDS AND BOOKED STORAGE VERIFIED; integrator must transfer ownership before staging'
'''


def measure_bandwidth(booking,run,host,port,identity,out):
    import shlex
    b=booking;R.validate_booking(b,time.time());run=str(run)
    if not re.fullmatch(r'/workspace/remainder/r2b/[A-Za-z0-9_-]{1,80}',run):raise ValueError('Invalid run path')
    ssh=['ssh','-o','BatchMode=yes','-o','Compression=no','-o','ConnectTimeout=10','-i',str(identity),'-p',str(port),'root@'+host]
    payload="""import hashlib,json,sys,os
from pathlib import Path
pod,run=sys.argv[1:]
ids=[s.split(b'=',1)[1].decode() for s in Path('/proc/1/environ').read_bytes().split(b'\\0') if s.startswith(b'RUNPOD_POD_ID=')]
assert ids==[pod],'POD ID MISMATCH'
# Bootstrap must already have armed this exact segment.
b=json.loads(Path(run,'booking.json').read_text())
for name in ('watchdog','hardstop'):
 assert 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' in Path(run,name+'.log').read_text()
p=Path(run,'bandwidth_sample.bin');data=os.urandom(8*1024*1024);p.write_bytes(data)
print(json.dumps({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}))
"""
    cmd='python3 - '+shlex.quote(b['pod'])+' '+shlex.quote(run)
    left=lambda:max(1,min(120,b['segment_deadline']-R.MIN_PULL-time.time()))
    proof=json.loads(subprocess.run(ssh+[cmd],input=payload,text=True,capture_output=True,check=True,timeout=left()).stdout)
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);sample=out.with_suffix('.sample.bin');start=time.monotonic()
    subprocess.run(['scp','-q','-o','Compression=no','-i',str(identity),'-P',str(port),'root@'+host+':'+run+'/bandwidth_sample.bin',str(sample)],check=True,timeout=left())
    elapsed=time.monotonic()-start
    if sample.stat().st_size!=proof['bytes'] or R.sha(sample)!=proof['sha256']:raise ValueError('Bandwidth sample checksum differs')
    result={**proof,'pod':b['pod'],'measured_epoch':time.time(),'elapsed_seconds':elapsed,'bytes_per_second':proof['bytes']/elapsed}
    out.write_text(json.dumps(result,indent=2)+'\n');subprocess.run(['scp','-q','-i',str(identity),'-P',str(port),str(out),'root@'+host+':'+run+'/bandwidth.json'],check=True,timeout=left())
    return result

