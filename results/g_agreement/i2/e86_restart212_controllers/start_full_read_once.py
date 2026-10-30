from pathlib import Path
import sys,json,time,hashlib,shlex
sys.path.insert(0,str(Path(__file__).resolve().parent));import stage_and_start as st
H=Path(__file__).resolve().parent
s=st.state();m=json.loads((H/'PREPARATION.json').read_text());v=json.loads((H/'PULL_VERIFIED.json').read_text())
assert v['verified'] and v['status']=='PROFILE_ONLY' and v['profile_source_input_assignment_verified']
p=json.loads((H/'terminal_pull/outputs/MEASURED_PROFILE.json').read_text());assert p['margin']==1.25 and p['phase']=='E86_readers'
assert time.time()+p['forecast_seconds']<s['hard_deadline_epoch']-15,'MEASURED_FULL_READ_NO_FIT_ORIGINAL_CLOCK'
assert m['prior_probe_gpu_seconds']+m['cap_seconds']<=7200
ad=dict(at=time.time(),source_sha=m['source_sha'],input_sha=m['input_sha'],profile_sha256=hashlib.sha256((H/'terminal_pull/outputs/MEASURED_PROFILE.json').read_bytes()).hexdigest(),forecast_with_margin=p['forecast_seconds'],remaining_original_seconds=s['hard_deadline_epoch']-time.time(),original_deadline=s['hard_deadline_epoch'],scientific_items=400,scientific_outputs=800)
with (H/'FULL_READ_ONCE_INTENT.json').open('x')as f:json.dump(ad,f)
remote=s['remote_dir'];program=f"""set -e
cd {shlex.quote(remote)}
/weights/venv-kernels/bin/python - <<'REMOTE'
from pathlib import Path
import json,time,hashlib
assert json.loads(Path('EXIT.json').read_text())['code']==0
assert hashlib.sha256(Path('outputs/OUTPUT_SEAL.json').read_bytes()).hexdigest()=={v['output_seal_sha256']!r}
x=json.loads(Path('assignment.json').read_text());assert x['absolute_deadline_epoch']=={s['hard_deadline_epoch']!r}
x['profile_only']=False
with Path('assignment_full.json').open('x')as f:json.dump(x,f)
with Path('FULL_READ_ONCE_INTENT.json').open('x')as f:json.dump({ad!r},f)
assert time.time()+{p['forecast_seconds']!r}<{s['hard_deadline_epoch']-15!r}
REMOTE
cat > full_read.sh <<'SCRIPT'
#!/bin/bash
cd {shlex.quote(remote)}
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/weights/hf_cache
set +e
timeout -k 5 {int(s['hard_deadline_epoch']-time.time()-10)} /weights/venv-kernels/bin/python -B results/g_agreement/understand/late198/specialized.py --inputs inputs --assets assets.json --assignment assignment_full.json --out full_outputs --stage read --source-sha {m['source_sha']} --input-sha {m['input_sha']} --capture-root capture --selection PUBLIC_SELECTION.json --release READER_RELEASE.json >full_read.log 2>&1
rc=$?
/weights/venv-kernels/bin/python -c 'import json,time;open("EXIT_FULL.json","x").write(json.dumps(dict(code='$rc',finished_epoch=time.time())))'
SCRIPT
nohup setsid bash full_read.sh </dev/null >full_supervisor.log 2>&1 &
echo $! >full_job.pid
cp full_job.pid /workspace/ws2_logs/job.pid
"""
st.ssh(s,program,30)
(H/'FULL_READ_STARTED.json').write_text(json.dumps(ad,indent=2)+'\n');print('E86 full read started once under original restart deadline')
