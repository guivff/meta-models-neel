"""I2 sole approved E99 phase1 dispatch; complete frozen6680 audit nodes only."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone
import sys,json,os,hashlib,subprocess,time,shutil
R=Path(__file__).resolve().parents[3];PUB=R/'cache/g_agreement/i2/publication';H=R/'cache/g_agreement/i2/e99_phase1_redacted_section221_v1';C=R.parent/'wt-internals-c'
sys.path.insert(0,str(PUB));sys.path.insert(0,str(Path(__file__).parent))
from e99_transport221 import E99Phase1Transport,LEDGER_ROOT
from projects.g_agreement.understand.blind_judge.e99_channel import frozen_wire,validate_wire_privacy
from projects.g_agreement.understand.blind_judge.parallel_funded import claim_slot
from projects.g_agreement.understand.blind_judge import funded_queue as funded,run
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
PAUSE=R.parent/'cache/g_agreement/JUDGING_ACCOUNT_PAUSE_402.json'
def authority():
 a=read(R/'results/g_agreement/i2/SECTION221_ITEM5_DIRECT_AUTHORITY.json');assert a['E99_phase1_cap_usd']==150
 s=read(R/'results/g_agreement/i2/GUIV_STANDING_RESEARCH_AUTHORITY_20261029.json');assert datetime.now(timezone.utc)<datetime.fromisoformat(s['expires_utc'])
 assert not(funded.CACHE/'PAUSED_402.json').exists(),'SHARED402PAUSE'
 if PAUSE.exists():assert read(PAUSE).get('status')=='FUNDING_CONFIRMED_RESUMED','ACCOUNT402PAUSE'
def snapshot():
 dest=H/'global_audits'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ.json');dest.parent.mkdir(exist_ok=True)
 code='from projects.g_agreement.understand.blind_judge.internals_c.accounting import snapshot;import json;from pathlib import Path;Path('+repr(str(dest))+').write_text(json.dumps(snapshot(),indent=2))'
 q=subprocess.run([sys.executable,'-c',code],cwd=C,capture_output=True,timeout=90);assert q.returncode==0,'FRESH_GLOBAL_SNAPSHOT_FAILED'
 return dest,read(dest)
def source():
 authority();a=read(R/'results/g_agreement/i2/E99_SECTION221_PHASE1_REDACTED_CPU_PREFLIGHT.json')
 for n,d in a['private_files'].items():assert sha(H/n)==d
 calls=read(H/'CALLS.PRIVATE.json');hashes=read(H/'WIRE_HASHES.PRIVATE.json');assert len(calls)==6680 and len({x['id'] for x in calls})==6680
 original=read(R/'cache/g_agreement/i2/e99_phase1_section221_v1/CALLS.PRIVATE.json');assert [x['id']for x in calls]==[x['id']for x in original]
 route=read(PUB/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json');api,privacy,protocol,io=run.route_modules(route)
 total=Decimal(0)
 for x in calls:
  w=frozen_wire(x['rendered'],protocol);assert hashlib.sha256(io.canonical(w).encode()).hexdigest()==hashes[x['id']];validate_wire_privacy(w,privacy.check_wire);total+=api.upper(w)
 assert total==Decimal(a['forecast_upper_usd']) and total<=150 and not read(H/'PRIVACY_BLOCKS.PRIVATE.json')
 assert len(read(H/'PATH_REDACTION_AUDIT.json')['affected'])==4
 return calls,route,api,privacy,protocol,io

def live(v):
 calls,route,api,privacy,protocol,io=v;key=os.environ.get('OPENROUTER_API_KEY');assert key
 home=H/'live'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');home.mkdir(parents=True)
 proof=Path(route['privacy_proof']);assert sha(proof)==route['privacy_proof_sha256'];shutil.copy2(proof,home/'OPENROUTER_PRIVACY_PROOF.json');io.CACHE=home;privacy.check_route(key)
 import requests
 q=requests.get('https://openrouter.ai/api/v1/credits',headers={'Authorization':'Bearer '+key},timeout=30);q.raise_for_status();d=q.json()['data'];remaining=Decimal(str(d['total_credits']))-Decimal(str(d['total_usage']));p,b=snapshot();max_request=max(api.upper(frozen_wire(x['rendered'],protocol))for x in calls);physical_holds=Decimal(b['unknown_physical_holds_usd']);assert remaining>=physical_holds+max_request,'CURRENT_REQUEST_EXPOSURE_NOT_FUNDED'
 exposure=Decimal(b['actual_plus_open_caps_usd']);assert exposure+150<=1000
 result=dict(at_epoch=time.time(),global_proof_path=str(p),global_proof_sha256=sha(p),actual_plus_other_open_caps_usd=str(exposure),global_including_E99_phase1_usd=str(exposure+150),remaining_credits_usd=str(remaining),maximum_request_upper_usd=str(max_request),unknown_physical_holds_usd=str(physical_holds),funding_policy='Check current request plus unresolved physical holds;150bank ceiling independently enforced; full6680scope remains fixed',live_route_inventory_sha256=sha(home/'last_zdr_route_inventory.json'),all6680_exact_wires_privacy_checked=True)
 write(home/'LIVE.json',result);return key,home,result

def main():
 assert sys.argv[1:] in (['--preflight'],['--dispatch-once']);os.umask(0o077);v=source();key,home,proof=live(v)
 if sys.argv[1]=='--preflight':print('E99_LIVE_PROOF',str(home/'LIVE.json'));return
 allocation=R/'results/g_agreement/i2/E99_PHASE1_ALLOCATION_SECTION221.json';a=read(allocation);pub=read(H/'ALLOCATION_PUBLICATION.json')
 assert a['allocation_usd']==150 and a['dispatch_source_sha256']==sha(__file__) and a['transport_source_sha256']==sha(Path(__file__).with_name('e99_transport221.py'))
 assert pub['allocation_sha256']==sha(allocation) and pub['shared_commit'];assert sha(Path(a['live_proof_path']))==a['live_proof_sha256']
 calls,route,api,privacy,protocol,io=v
 budget=dict(issuer='integrator',verified=True,E99_allocation_usd=150,phase1_calls=6680,continuation_requires_actual_gate=True,reservation_included=True,global_judging_committed_including_reservation_usd=proof['global_including_E99_phase1_usd'])
 with E99Phase1Transport(route,key,budget) as t:
  assert not(H/'DISPATCH_ONCE_INTENT.json').exists();assert not(t.root/'ledger.jsonl').exists() or not(t.root/'ledger.jsonl').read_text().strip(),'PRIOR_E99_REQUESTS_NO_REPLAY'
  with(H/'DISPATCH_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),allocation_sha256=sha(allocation)),f)
  job=t.root/'phase1_section221';job.mkdir(exist_ok=False);write(job/'START.json',dict(at=time.time(),scope=6680,cap=150,allocation_sha256=sha(allocation),live_proof_sha256=sha(home/'LIVE.json')))
  def before(wire):
   authority();p,b=snapshot();own=t.summary();remaining=max(Decimal(0),Decimal(150)-Decimal(own['committed_usd']));assert Decimal(b['actual_plus_open_caps_usd'])+remaining<=1000
   import requests
   q=requests.get('https://openrouter.ai/api/v1/credits',headers={'Authorization':'Bearer '+key},timeout=30);q.raise_for_status();cr=q.json()['data'];funds=Decimal(str(cr['total_credits']))-Decimal(str(cr['total_usage']))
   assert funds>=Decimal(b['unknown_physical_holds_usd'])+api.upper(wire),'CURRENT_REQUEST_EXPOSURE_NOT_FUNDED_STOP_BEFORE_SEND'
   claim_slot('E99')
  def pause(response):
   x=dict(status='HTTP402_PAUSED_ALL_BANKS',bank='E99',at=time.time(),response_sha256=sha(response));write(PAUSE,x);write(funded.CACHE/'PAUSED_402.json',x)
  t.before_send=before;t.pause_all=pause;term=[]
  try:
   for x in calls:
    r=t.call(x['id'],x['rendered']);term.append(r);write(job/'terminals'/ (x['id']+'.json'),r);write(job/'PROGRESS.json',dict(at=time.time(),done=len(term),total=6680,cost=t.summary()))
   cost=t.summary();assert Decimal(cost['unresolved_reserve_usd'])==0
   write(job/'TERMINAL.json',term);write(job/'COST.json',cost);shutil.copy2(H/'PATH_REDACTION_AUDIT.json',job/'PATH_REDACTION_AUDIT.json')
   actual=Decimal(cost['actual_usd']);gate=actual<=Decimal('68.850925')*Decimal('1.25');write(job/'CONTINUATION_GATE.json',dict(actual_usd=str(actual),logical_call_count=6680,actual_per_logical_call=str(actual/6680),forecast_upper_usd='68.850925',within_1_25_forecast=gate,continuation_not_allocated=True))
   write(job/'RESULT_SEAL.json',dict(experiment='E99',phase='phase1_ALL6680_hallucination_audit',status='COMPLETE_PHASE1_NOT_FULL_DAG',completed_epoch=time.time(),allocation_sha256=sha(allocation),files={str(p.relative_to(job)):sha(p)for p in job.rglob('*')if p.is_file()}))
  except BaseException as e:write(job/'BLOCKED.json',dict(at=time.time(),error_type=type(e).__name__,cost=t.summary(),no_replay=True));raise
 print('E99 phase1 complete')
if __name__=='__main__':main()
