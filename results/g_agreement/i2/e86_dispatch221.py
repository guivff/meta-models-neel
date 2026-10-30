"""E86 prospective §221 $4 dispatch: original full flat wires, §217 terminals.
No capture/probe/selection/analysis replay; private joins never loaded here.
"""
from pathlib import Path
import sys,os,json,hashlib,time,fcntl,shutil,subprocess
from decimal import Decimal
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[3];H=R/'cache/g_agreement/i2/e86_judge_cpu_v1';RT=H/'runtime';sys.path.insert(0,str(RT))
from projects.g_agreement.understand.blind_judge import run,later_runner as L,rubric202,channels81_86 as C
from projects.g_agreement.understand.blind_judge.judgment_adapter402 import render_record
from projects.g_agreement.understand.blind_judge.privacy79 import redact,check_decoded
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+'\n')
PAUSE=R.parent/'cache/g_agreement/JUDGING_ACCOUNT_PAUSE_402.json'
def authority():
 a=read(R/'results/g_agreement/i2/SECTION221_ITEM5_DIRECT_AUTHORITY.json');assert a['E86_total_bank_usd']==4
 s=read(R/'results/g_agreement/i2/GUIV_STANDING_RESEARCH_AUTHORITY_20261029.json');assert datetime.now(timezone.utc)<datetime.fromisoformat(s['expires_utc'])
 if PAUSE.exists():assert read(PAUSE).get('status')=='FUNDING_CONFIRMED_RESUMED','HTTP402_ACCOUNT_PAUSED'
def disposition(resp):
 if resp['http_status']==402:return 'PAUSE_402'
 assert resp['http_status']==200,'UNRECOGNISED_PROVIDER_ERROR_STOP'
 b=resp['response'];assert b.get('provider')=='Google' and b.get('model') in ('google/gemini-3.1-flash-lite','google/gemini-3.1-flash-lite-001'),'ROUTE_STOP'
 cost=Decimal(str(b.get('usage',{}).get('cost')));assert cost.is_finite() and cost>=0
 finish=b['choices'][0]['finish_reason'];assert finish in ('stop','length'),'UNKNOWN_FINISH_STOP'
 return 'TERMINAL_UNPARSEABLE' if finish=='length' else 'VALIDATE'
def judge(items,send):
 final={}
 for i in range(0,len(items),4):
  for x in send(items[i:i+4],0):final[x['id']]=dict(x,attempts=0)
 for x in items:
  if final[x['id']]['status'] in ('KEPT','UNPARSEABLE'):continue
  for attempt in (1,2):
   final[x['id']]=dict(send([x],attempt)[0],attempts=attempt)
   if final[x['id']]['status'] in ('KEPT','UNPARSEABLE'):break
  if final[x['id']]['status']=='INVALID':final[x['id']].update(status='UNPARSEABLE',code=None)
 assert set(final)=={x['id']for x in items};return [final[x['id']]for x in items]
def source():
 authority()
 for n,d in read(H/'RUNTIME_SOURCE_MANIFEST.json').items():assert sha(RT/n)==d,'RUNTIME_CHANGED'
 p=read(H/'CPU_PREFLIGHT.json');ss=read(H/'SOURCE_SEAL.json');assert ss['complete'] and ss['n']==800
 assert sha(H/'SOURCE_SEAL.json')==p['source_seal_sha256'] and sha(H/'converted_packet/PACKET_SEAL.json')==p['packet_seal_sha256']
 for n,d in ss['files'].items():assert sha(H/n)==d
 ps=read(H/'converted_packet/PACKET_SEAL.json')
 for n,d in ps['files'].items():assert sha(H/'converted_packet'/n)==d
 items=read(H/'JUDGE_PACKET.json');assert items==read(H/'converted_packet/PACKET.json') and len(items)==800
 rubric=(H/'JUDGE_RUBRIC.txt').read_text();assert rubric.encode()==rubric202.amended();C.check_items('E86',items,rubric)
 ids=read(H/'ORIGINAL_IDS.json');assert ids==rubric202.original_ids([x['id']for x in items],'E86') and len(ids)==200
 records,audit=redact([render_record(x,rubric)for x in items],'E86',addresses=True)
 assert hashlib.sha256(json.dumps(audit,sort_keys=True).encode()).hexdigest()==p['redaction_audit_sha256']
 oldrubric=rubric202.BASE.read_text();old=[dict(x,rubric=x['rubric'].replace(rubric,oldrubric,1))for x in records if x['id']in set(ids)]
 route=read(RT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json');route['e10_source']=str(RT/'e10');api,privacy,protocol,io=run.route_modules(route)
 assert protocol.MODEL=='google/gemini-3.1-flash-lite' and protocol.PROVIDER=='google-vertex/global'
 wires=[L.channel_payload(xs[i:i+4],rr,'E56',protocol)for xs,rr in [(records,rubric),(old,oldrubric)]for i in range(0,len(xs),4)]
 hashes=[hashlib.sha256(io.canonical(w).encode()).hexdigest()for w in wires]
 assert hashlib.sha256(json.dumps(hashes).encode()).hexdigest()==p['wire_hashes_sha256']
 upper=sum((api.upper(w)for w in wires),Decimal(0));assert str(upper)==p['first_pass_upper_usd'] and upper<=4 and len(wires)==250
 for xs,rr in [(records,rubric),(old,oldrubric)]:
  for i in range(0,len(xs),4):check_decoded(privacy.check_wire,xs[i:i+4],L.channel_payload(xs[i:i+4],rr,'E56',protocol))
 return records,rubric,old,oldrubric,audit,route,api,privacy,protocol,io

def global_gate(extra):
 q=subprocess.run([sys.executable,str(H/'fresh_judging_snapshot.py')],cwd=R,capture_output=True,text=True,timeout=90);assert q.returncode==0,'GLOBAL_AUDIT_FAILED '+q.stderr[-500:]
 path=Path(q.stdout.rsplit('LOCAL_AUDIT_PATH ',1)[1].strip());d=read(path);assert Decimal(d['current_request_exposure_usd'])+extra<=1000
 return path,d

def live(v):
 records,rubric,old,oldrubric,audit,route,api,privacy,protocol,io=v
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');home=H/'live_proofs'/stamp;home.mkdir(parents=True,exist_ok=False);io.CACHE=home
 proof=Path(route['privacy_proof']);assert sha(proof)==route['privacy_proof_sha256'];shutil.copy2(proof,home/'OPENROUTER_PRIVACY_PROOF.json')
 key=os.environ.get('OPENROUTER_API_KEY');assert key;privacy.check_route(key)
 import requests
 q=requests.get('https://openrouter.ai/api/v1/credits',headers={'Authorization':'Bearer '+key},timeout=30);q.raise_for_status();c=q.json()['data'];remaining=Decimal(str(c['total_credits']))-Decimal(str(c['total_usage']));assert remaining>=4,'INSUFFICIENT_FUNDED_CREDITS'
 write(home/'LIVE.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),all250_exact_wires_checked=True,route_inventory_sha256=sha(home/'last_zdr_route_inventory.json'),account_proof_sha256=sha(proof),remaining_credits_usd=str(remaining),new_calls=0))
 return key,home

def main():
 assert sys.argv[1:]in (['--source-preflight'],['--live-preflight'],['--dispatch-once'])
 v=source()
 if sys.argv[1]=='--source-preflight':print('E86 original800+200/250wires/upper3.5136009375 under4: CPU PASS; no calls');return
 key,home=live(v)
 if sys.argv[1]=='--live-preflight':print('LIVE_PROOF_PATH',home/'LIVE.json');return
 records,rubric,old,oldrubric,audit,route,api,privacy,protocol,io=v
 ap=R/'results/g_agreement/i2/E86_JUDGE_ALLOCATION_SECTION221.json';a=read(ap);assert a['allocation_usd']==4 and a['dispatch_source_sha256']==sha(__file__) and a['authority_sha256']==sha(R/'results/g_agreement/i2/SECTION221_ITEM5_DIRECT_AUTHORITY.json')
 pub=read(H/'ALLOCATION_PUBLICATION_SECTION221.json');assert pub['allocation_sha256']==sha(ap) and pub['shared_commit']
 proof=read(a['global_proof_path']);assert sha(a['global_proof_path'])==a['global_proof_sha256'] and 0<=time.time()-datetime.fromisoformat(proof['as_of_utc']).timestamp()<120
 assert Decimal(proof['current_request_exposure_usd'])+4<=1000
 ledger=H/'judging';ledger.mkdir(exist_ok=True);lock=(ledger/'DISPATCH.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with (H/'DISPATCH_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),allocation_sha256=sha(ap)),f)
 job=ledger/'E86_judgments';job.mkdir(exist_ok=False);write(job/'START.json',dict(at=time.time(),primary_n=800,original_n=200,allocation_sha256=sha(ap),live_proof_sha256=sha(home/'LIVE.json'),analysis_allowed=False))
 write(job/'PATH_REDACTION_AUDIT.json',audit);api.CAP=Decimal(4);io.CACHE=home;rawcheck=privacy.check_wire;privacy.check_wire=lambda stage,batch,wire,unused=None:check_decoded(rawcheck,batch,wire)
 client=api.Client(ledger,key);truncated=[]
 try:
  for label,xs,rr,out in [('E86',records,rubric,'JUDGMENTS.json'),('E86_original_25pct',old,oldrubric,'ORIGINAL_JUDGMENTS.json')]:
   protocol.payload=lambda stage,batch,unused=None,rr=rr:L.channel_payload(batch,rr,'E56',protocol)
   protocol.validate=lambda stage,response,batch,unused=None:L.classify(batch,response,'E56')
   def send(batch,attempt):
    authority();wire=L.channel_payload(batch,rr,'E56',protocol);global_gate(api.upper(wire));io.digest=lambda value:hashlib.sha256((label+':'+str(attempt)+':'+value).encode()).hexdigest();stage=label+'_attempt'+str(attempt);result=client.one(stage,batch);rp=ledger/stage/(result['id']+'.response.json');assert rp.exists(),'UNSENT_OR_UNRESOLVED_NO_REPLAY'
    disp=disposition(read(rp))
    if disp=='PAUSE_402':
     PAUSE.parent.mkdir(parents=True,exist_ok=True);write(PAUSE,dict(status='HTTP402_PAUSED_ALL_BANKS',bank='E86',at_utc=datetime.now(timezone.utc).isoformat(),response_sha256=sha(rp)));raise RuntimeError('HTTP402_ALL_BANKS_PAUSE')
    if disp=='TERMINAL_UNPARSEABLE':
     truncated.append(dict(ids=[x['id']for x in batch],response_sha256=sha(rp)));return [dict(id=x['id'],status='UNPARSEABLE',code=None,terminal_reason='CHARGED_LENGTH')for x in batch]
    if result['status']=='OK':value=result['value']
    else:
     body=read(rp)['response']
     try:json.loads(body['choices'][0]['message']['content'])
     except(ValueError,TypeError):value=[dict(id=x['id'],status='INVALID',code=None)for x in batch]
     else:raise RuntimeError('UNRECOGNISED_TRANSPORT_ERROR_STOP')
    write(job/'PROGRESS.json',dict(at=time.time(),stage=stage,cost=client.ledger.summary()));return value
   final=judge(xs,send);write(job/out,final)
  write(job/'CHARGED_TRUNCATIONS.json',truncated);write(job/'COUNTS.json',dict(n=800,original_n=200,cost=client.ledger.summary(),analysis_allowed=False));shutil.copy2(ledger/'ledger.jsonl',job/'LEDGER_AT_END.jsonl')
  write(job/'RESULT_SEAL.json',dict(experiment='E86',status='TERMINAL_BLIND_GRID_NO_ANALYSIS',completed_epoch=time.time(),allocation_sha256=sha(ap),packet_seal_sha256=sha(H/'converted_packet/PACKET_SEAL.json'),files={str(p.relative_to(job)):sha(p)for p in job.rglob('*')if p.is_file()}));print('E86 full blind grid sealed; no analysis')
 except BaseException as e:write(job/'BLOCKED.json',dict(at=time.time(),error_type=type(e).__name__,cost=client.ledger.summary(),retry=False));raise
if __name__=='__main__':main()
