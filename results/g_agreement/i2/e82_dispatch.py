"""E82 full grouped blind judging, explicit human cap18 and pinned destination.
All source/rubric/wires are prospective, allocation must be shared before send.
Only malformed-code validation is retried, singly, at most twice. No truth joins.
"""
from pathlib import Path
import sys,json,hashlib,os,time,shutil,fcntl,subprocess
from decimal import Decimal
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[3];H=R/'cache/g_agreement/i2/e82_judge_cpu_v1';RT=H/'runtime';sys.path.insert(0,str(RT));sys.path.insert(0,str(H))
from projects.g_agreement.understand.blind_judge import run,later_runner as L,rubric202
from projects.g_agreement.understand.blind_judge.privacy79 import check_decoded
from projects.g_agreement.readerbench.scoring import validate_judgments
import e82_grouped_judge as G
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def authority_gate():
 a=read(R/'results/g_agreement/i2/E82_JUDGE_CAP18_DIRECT_AUTHORITY.json');assert a['answer']=='Approve $18 total cap' and a['total_judging_cap_usd']==18
 s=read(R/'results/g_agreement/i2/GUIV_STANDING_RESEARCH_AUTHORITY_20261029.json');assert datetime.now(timezone.utc)<datetime.fromisoformat(s['expires_utc']),'DESTINATION_AUTHORITY_EXPIRED'
 return a,s

def source_preflight():
 authority_gate()
 for name,d in read(H/'RUNTIME_SOURCE_MANIFEST.json').items():assert sha(RT/name)==d,'RUNTIME_CHANGED'
 p=read(H/'grouped_adapter_v1/PREFLIGHT.json');assert sha(H/'e82_grouped_judge.py')==p['renderer_code_sha256']
 for n,d in p['files'].items():assert sha(H/'grouped_adapter_v1'/n)==d,'GROUPED_SOURCE_CHANGED'
 assert p['primary_records']==816 and p['original_rubric_records']==204 and p['native_outputs']==13580 and p['all_positions_retained']
 records=read(H/'grouped_adapter_v1/GROUPED_PACKET.json');ids=read(H/'grouped_adapter_v1/ORIGINAL_IDS.json');assert ids==rubric202.original_ids([x['id']for x in records],'E82')
 rubric=rubric202.amended().decode();old=rubric202.BASE.read_text();assert hashlib.sha256(rubric.encode()).hexdigest()==p['rubric_sha256']
 original=[dict(x,rubric=x['rubric'].replace(rubric,old,1))for x in records if x['id']in set(ids)]
 # Missing-truth B is visibly empty; no private target map is opened by dispatch.
 allowed={x['id']:['A']if x['rubric'].endswith('\nB: \n')else ['A','B']for x in records}
 assert sum(len(v)==1 for v in allowed.values())==20
 route=read(RT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json');route['e10_source']=str(RT/'e10')
 api,privacy,protocol,io=run.route_modules(route);assert protocol.MODEL=='google/gemini-3.1-flash-lite' and protocol.PROVIDER=='google-vertex/global' and protocol.PROVIDER_NAME=='Google'
 wires=[G.wire([x],rr,protocol,run.payload)for xs,rr in [(records,rubric),(original,old)]for x in xs]
 assert [hashlib.sha256(io.canonical(w).encode()).hexdigest()for w in wires]==read(H/'grouped_adapter_v1/WIRE_HASHES.json')
 upper=sum((api.upper(w)for w in wires),Decimal(0));assert str(upper)==p['first_pass_upper_usd'] and upper<=18
 return p,records,rubric,original,old,allowed,route,api,privacy,protocol,io

def live_gate(v):
 p,records,rubric,original,old,allowed,route,api,privacy,protocol,io=v
 io.CACHE=H/'live_route';io.CACHE.mkdir(exist_ok=True);proof=Path(route['privacy_proof']);assert sha(proof)==route['privacy_proof_sha256'];shutil.copy2(proof,io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
 key=os.environ.get('OPENROUTER_API_KEY');assert key;privacy.check_route(key)
 # A read-only funding query, never prints or stores the credential.
 import requests
 q=requests.get('https://openrouter.ai/api/v1/credits',headers={'Authorization':'Bearer '+key},timeout=30);q.raise_for_status();credits=q.json()['data'];remaining=Decimal(str(credits['total_credits']))-Decimal(str(credits['total_usage']));assert remaining>0,'CREDITS_NOT_FUNDED'
 write(H/'LIVE_CREDITS_CHECK.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),remaining_usd=str(remaining),funded=True))
 for xs,rr in [(records,rubric),(original,old)]:
  for x in xs:check_decoded(privacy.check_wire,[x],G.wire([x],rr,protocol,run.payload))
 write(H/'LIVE_PRIVACY_PREFLIGHT.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),all1020wires_checked=True,route_inventory_sha256=sha(io.CACHE/'last_zdr_route_inventory.json'),private_account_proof_sha256=sha(proof),model=protocol.MODEL,provider=protocol.PROVIDER,zdr=True,data_collection='deny',fallbacks=False,standing_authority_sha256=sha(R/'results/g_agreement/i2/GUIV_STANDING_RESEARCH_AUTHORITY_20261029.json'),new_calls=0,new_reservations=0))
 return key

def actual_global_gate(extra):
 q=subprocess.run([sys.executable,str(H/'fresh_judging_snapshot.py')],cwd=R,capture_output=True,text=True,timeout=90)
 assert q.returncode==0,'GLOBAL_ACTUAL_AUDIT_FAILED_NO_SEND: '+q.stderr[-1000:]
 path=Path(q.stdout.rsplit('LOCAL_AUDIT_PATH ',1)[1].strip());s=read(path);assert Decimal(s['current_request_exposure_usd'])+extra<=1000,'GLOBAL_JUDGING_CAP_NO_SEND'
 return path,s

def classify(batch,response,allowed):
 result=[];codes=response.get('records',[])if isinstance(response,dict)else []
 if not isinstance(codes,list):codes=[]
 for x in batch:
  matches=[c for c in codes if isinstance(c,dict)and c.get('id')==x['id']]
  try:
   assert len(matches)==1;c=matches[0];normal=dict(x,positions=[dict(p,readout=L.normalize(p['readout']))for p in x['positions']]);nc=dict(c,evidence=L.normalize(c['evidence']))
   G.validate_code(normal,nc,allowed[x['id']],validate_judgments)
   result.append(dict(id=x['id'],status='KEPT',code=c))
  except (AssertionError,ValueError,TypeError,KeyError):result.append(dict(id=x['id'],status='INVALID',code=None))
 return result

def main():
 assert sys.argv[1:]in (['--source-preflight'],['--live-preflight'],['--dispatch-once'])
 v=source_preflight()
 if sys.argv[1]=='--source-preflight':print('E82 full1020exactwires/source/rubric/cap PASS; no calls/reservations');return
 key=live_gate(v)
 if sys.argv[1]=='--live-preflight':print('E82 liveprivacy/all1020wires/ZDR/credits PASS; no calls/reservations');return
 p,records,rubric,original,old,allowed,route,api,privacy,protocol,io=v
 allocation=R/'results/g_agreement/i2/E82_JUDGE_ALLOCATION.json';a=read(allocation)
 assert a['bank']=='E82' and a['allocation_usd']==18 and a['dispatch_source_sha256']==sha(__file__) and a['direct_authority_sha256']==sha(R/'results/g_agreement/i2/E82_JUDGE_CAP18_DIRECT_AUTHORITY.json') and a['standing_authority_sha256']==sha(R/'results/g_agreement/i2/GUIV_STANDING_RESEARCH_AUTHORITY_20261029.json')
 assert a['adapter_preflight_sha256']==sha(H/'grouped_adapter_v1/PREFLIGHT.json')
 publication=read(H/'ALLOCATION_PUBLICATION.json');assert publication['allocation_sha256']==sha(allocation) and publication['shared_commit']
 proof=read(H/'FRESH_GLOBAL_JUDGING_PROOF.json');assert sha(H/'FRESH_GLOBAL_JUDGING_PROOF.json')==a['global_proof_sha256'] and 0<=time.time()-datetime.fromisoformat(proof['as_of_utc']).timestamp()<120 and Decimal(proof['current_request_exposure_usd'])+18<=1000
 ledger=H/'judging';ledger.mkdir(exist_ok=True);lock=(ledger/'DISPATCH.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with (H/'DISPATCH_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),allocation_sha256=sha(allocation)),f)
 api.CAP=Decimal(18);io.CACHE=H/'live_route';original_check=privacy.check_wire
 privacy.check_wire=lambda stage,batch,body,unused=None:check_decoded(original_check,batch,body)
 client=api.Client(ledger,key);job=ledger/'E82_judgments';job.mkdir(exist_ok=False);write(job/'START.json',dict(at=time.time(),primary_n=816,original_n=204,allocation_sha256=sha(allocation),analysis_allowed=False))
 try:
  for label,items,rr,name in [('E82',records,rubric,'JUDGMENTS.json'),('E82_original_25pct',original,old,'ORIGINAL_JUDGMENTS.json')]:
   protocol.payload=lambda stage,batch,unused=None,rr=rr:G.wire(batch,rr,protocol,run.payload)
   protocol.validate=lambda stage,response,batch,unused=None:classify(batch,response,allowed)
   def send(item,attempt):
    authority_gate();path,s=actual_global_gate(api.upper(G.wire([item],rr,protocol,run.payload)))
    io.digest=lambda value:hashlib.sha256((label+':'+str(attempt)+':'+value).encode()).hexdigest();stage=label+'_attempt'+str(attempt);result=client.one(stage,[item])
    if result['status']=='OK':return result['value'][0]
    response_path=ledger/stage/(result['id']+'.response.json');assert response_path.exists()and not client.latch.is_set(),'TRANSPORT_BUDGET_CREDITS_STOP_NO_RESEND';resp=read(response_path);body=resp['response'];assert resp['http_status']==200 and body.get('provider')==protocol.PROVIDER_NAME and body.get('model')in [protocol.MODEL,protocol.MODEL+'-001']and body.get('usage',{}).get('cost')is not None and body['choices'][0].get('finish_reason')=='stop','ROUTE_COST_COMPLETION_STOP'
    try:json.loads(body['choices'][0]['message']['content'])
    except (ValueError,TypeError):return dict(id=item['id'],status='INVALID',code=None)
    raise RuntimeError('UNEXPECTED_TRANSPORT_FAILURE_NO_RETRY')
   terminal={}
   for item in items:
    terminal[item['id']]=dict(send(item,0),attempts=0)
    write(job/(label+'_PROGRESS.json'),dict(at=time.time(),initial_done=len(terminal),initial_total=len(items),cost=client.ledger.summary()))
   for item in items:
    if terminal[item['id']]['status']=='KEPT':continue
    for attempt in (1,2):
     terminal[item['id']]=dict(send(item,attempt),attempts=attempt)
     if terminal[item['id']]['status']=='KEPT':break
    if terminal[item['id']]['status']!='KEPT':terminal[item['id']].update(status='UNPARSEABLE',code=None)
   final=[terminal[x['id']]for x in items];assert len(final)==len(items);write(job/name,final)
  write(job/'COUNTS.json',dict(n=816,original_n=204,cost=client.ledger.summary(),analysis_allowed=False));shutil.copy2(ledger/'ledger.jsonl',job/'LEDGER_AT_END.jsonl')
  write(job/'RESULT_SEAL.json',dict(status='TERMINAL_BLIND_GRID_NO_ANALYSIS',experiment='E82',completed_epoch=time.time(),allocation_sha256=sha(allocation),adapter_preflight_sha256=sha(H/'grouped_adapter_v1/PREFLIGHT.json'),files={str(f.relative_to(job)):sha(f)for f in job.rglob('*')if f.is_file()}));print('E82 full blind judgments sealed; private targets unopened')
 except BaseException as e:write(job/'BLOCKED.json',dict(at=time.time(),error_type=type(e).__name__,error=str(e),cost=client.ledger.summary(),retry=False));raise
if __name__=='__main__':main()
