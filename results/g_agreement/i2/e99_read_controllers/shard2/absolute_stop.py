"""Extra provider-side absolute stop; never extends or replaces existing guards."""
import json,time,subprocess,os
from pathlib import Path
HOME=Path(__file__).resolve().parent
API='/Users/guivff/repl/tools/runpod_api.sh'
def main():
 os.umask(0o077);s=json.loads((HOME/'ALLOCATION.private.json').read_text());end=s['hard_deadline_epoch']-10
 p=HOME/'ABSOLUTE_GUARD.private.json'
 with p.open('x') as f:json.dump(dict(pid=os.getpid(),started=time.time(),stop_at=end,original_creation=s['created_epoch'],original_deadline=s['hard_deadline_epoch']),f)
 while time.time()<end:time.sleep(min(5,end-time.time()))
 for attempt in range(5):
  q='mutation { podStop(input:{podId:'+json.dumps(s['pod_id'])+'}) { id desiredStatus } }'
  try:
   r=subprocess.run(['bash',API,q],capture_output=True,timeout=30)
   (HOME/f'ABSOLUTE_STOP_{attempt}.private.json').write_bytes(r.stdout)
   x=json.loads(r.stdout)
   if r.returncode==0 and not x.get('errors') and x['data']['podStop']['id']==s['pod_id']:return
  except Exception:pass
  time.sleep(3)
 raise RuntimeError('ABSOLUTE_STOP_FAILED')
if __name__=='__main__':main()
