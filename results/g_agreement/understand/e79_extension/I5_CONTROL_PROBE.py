from pathlib import Path
import datetime,json,subprocess,os
base=Path('/Users/guivff/repl/activation-readers-i5/control_preflight')
proof=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),background_persistent_write=False,provider_authenticated=False)
try:
    (base/'write-test').write_text('durable background artifact')
    proof['background_persistent_write']=True
    run=subprocess.run(['/Users/guivff/repl/tools/runpod_api.sh','query { myself { id } }'],capture_output=True,text=True,timeout=30)
    data=json.loads(run.stdout)
    proof['provider_authenticated']=isinstance(data.get('data',{}).get('myself'),dict)and bool(data['data']['myself'].get('id'))
except Exception as error:
    proof['error_type']=type(error).__name__
finally:
    p=base/'proof.json';p.write_text(json.dumps(proof,indent=2)+'\n');p.chmod(0o600)
