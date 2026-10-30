"""E81 §212: frozen scientific transport, explicit USD33/500 financial admission."""
from pathlib import Path
import sys,json,hashlib,os,time,shutil,fcntl
from decimal import Decimal
H=Path(__file__).resolve().parent;R=H.parents[3];RT=H/'runtime';sys.path.insert(0,str(RT))
from projects.g_agreement.understand.blind_judge import run,later_runner as L,rubric202,channels81_86 as C
from projects.g_agreement.understand.blind_judge.judgment_adapter402 import render_record
from projects.g_agreement.understand.blind_judge.privacy79 import redact,check_decoded
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def preflight(posted):
 for n,d in read(H/'RUNTIME_SOURCE_MANIFEST.json').items():assert sha(RT/n)==d,'RUNTIME_CHANGED'
 a=read(R/'results/g_agreement/i2/E81_JUDGE_ALLOCATION_SECTION212.json');assert sha(__file__)==a['dispatch_source_sha256'],'DISPATCH_SOURCE_CHANGED'
 assert a['authority']=='DIRECT_GUIV_SECTION212' and a['allocation_usd']==33 and a['global_ceiling_usd']==500
 assert sha(R/'results/g_agreement/i2/E81_JUDGE_CAP33_DIRECT_AUTHORITY.json')==a['direct_authority_sha256']
 proof=read(H/'FRESH_GLOBAL_JUDGING_PROOF.json');assert sha(H/'FRESH_GLOBAL_JUDGING_PROOF.json')==a['global_proof_sha256'] and Decimal(proof['conservative_global_exposure_usd'])<=500
 if posted:
  assert 0<=time.time()-__import__('datetime').datetime.fromisoformat(proof['as_of_utc']).timestamp()<120,'FRESH_JUDGING_ADMISSION_REQUIRED'
  p=read(H/'ALLOCATION_PUBLICATION.json');assert p['allocation_sha256']==sha(R/'results/g_agreement/i2/E81_JUDGE_ALLOCATION_SECTION212.json') and p['shared_commit']
 packet=H/'converted_packet';ps=read(packet/'PACKET_SEAL.json');assert sha(packet/'PACKET_SEAL.json')==a['packet_seal_sha256']
 for n,d in ps['files'].items():assert sha(packet/n)==d
 source=read(H/'SOURCE_SEAL.json');assert ps['source_seal_sha256']==sha(H/'SOURCE_SEAL.json') and source['complete'] and source['n']==7376
 assert sha(H/'JUDGE_PACKET.json')==source['files']['JUDGE_PACKET.json']==ps['source_packet_sha256']
 items=read(packet/'PACKET.json');assert items==read(H/'JUDGE_PACKET.json');rubric=(packet/'RUBRIC.txt').read_text();assert rubric.encode()==rubric202.amended();C.check_items('E81',items,rubric)
 wanted=read(packet/'ORIGINAL_IDS.json');assert wanted==rubric202.original_ids([x['id'] for x in items],'E81') and len(wanted)==1844
 items,audit=redact([render_record(x,rubric) for x in items],'E81',addresses=True);original=rubric202.BASE.read_text();old=[dict(x,rubric=x['rubric'].replace(rubric,original,1)) for x in items if x['id'] in set(wanted)]
 route=read(RT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json');route['e10_source']=str(RT/'e10');api,privacy,protocol,io=run.route_modules(route);assert protocol.MODEL=='google/gemini-3.1-flash-lite' and protocol.PROVIDER=='google-vertex/global' and protocol.PROVIDER_NAME=='Google'
 bound=sum((api.upper(L.channel_payload(xs[i:i+4],rr,'E56',protocol)) for xs,rr in [(items,rubric),(old,original)] for i in range(0,len(xs),4)),Decimal(0));assert str(bound)==a['first_pass_worst_upper_usd'] and bound<=33
 return a,items,rubric,old,original,audit,api,privacy,protocol,io,route

def main():
 assert sys.argv[1:] in (['--preflight-only'],['--dispatch-once'])
 posted=sys.argv[1]=='--dispatch-once';v=preflight(posted)
 if not posted:print('CPU full-grid/source/§212 financial preflight PASS; no API or reservation');return
 a,items,rubric,old,original,audit,api,privacy,protocol,io,route=v
 ledger=H/'judging';ledger.mkdir(exist_ok=True);api.CAP=Decimal('33');io.CACHE=ledger/'route';io.CACHE.mkdir(exist_ok=True)
 proof=Path(route['privacy_proof']);assert sha(proof)==route['privacy_proof_sha256'];shutil.copy2(proof,io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
 key=os.environ.get('OPENROUTER_API_KEY');assert key;privacy.check_route(key)
 original_check=privacy.check_wire
 def privacy_check(stage,batch,wire,unused=None):
  assert all(set(x)=={'id','rubric','readout'} for x in batch);check_decoded(original_check,batch,wire)
 privacy.check_wire=privacy_check
 for xs,rr in [(items,rubric),(old,original)]:
  for i in range(0,len(xs),4):privacy_check('',xs[i:i+4],L.channel_payload(xs[i:i+4],rr,'E56',protocol))
 lock=(ledger/'DISPATCH.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with (H/'DISPATCH_ONCE_INTENT.json').open('x') as f:json.dump(dict(at=time.time(),allocation_sha256=sha(R/'results/g_agreement/i2/E81_JUDGE_ALLOCATION_SECTION212.json')),f)
 job=ledger/'E81_judgments';job.mkdir(exist_ok=False);write(job/'START.json',dict(at=time.time(),n=7376,original_n=1844,allocation_sha256=sha(R/'results/g_agreement/i2/E81_JUDGE_ALLOCATION_SECTION212.json'),packet_seal_sha256=a['packet_seal_sha256'],first_pass_upper_usd=a['first_pass_worst_upper_usd'],analysis_allowed=False))
 write(job/'PATH_REDACTION_AUDIT.json',audit);client=api.Client(ledger,key)
 try:
  for label,xs,rr,outname in [('E81',items,rubric,'JUDGMENTS.json'),('E81_original_25pct',old,original,'ORIGINAL_JUDGMENTS.json')]:
   protocol.payload=lambda stage,batch,unused=None,rr=rr:L.channel_payload(batch,rr,'E56',protocol)
   protocol.validate=lambda stage,response,batch,unused=None:L.classify(batch,response,'E56')
   def send(batch,attempt):
    io.digest=lambda value:hashlib.sha256((label+':'+str(attempt)+':'+value).encode()).hexdigest();stage=label+'_attempt'+str(attempt);result=client.one(stage,batch)
    if result['status']=='OK':return result['value']
    p=ledger/stage/(result['id']+'.response.json');assert p.exists() and not client.latch.is_set(),'TRANSPORT_OR_BUDGET_STOP_NO_RESEND';resp=read(p);body=resp['response'];assert resp['http_status']==200 and body.get('provider')==protocol.PROVIDER_NAME and body.get('model') in [protocol.MODEL,protocol.MODEL+'-001'] and body.get('usage',{}).get('cost') is not None and body['choices'][0].get('finish_reason')=='stop','ROUTE_COST_COMPLETION_STOP'
    try:json.loads(body['choices'][0]['message']['content'])
    except(ValueError,TypeError):return L.classify(batch,{},'E56')
    raise RuntimeError('UNEXPECTED_TRANSPORT_FAILURE_NO_RETRY')
   terminal=L.judge(xs,send);assert [x['id'] for x in terminal]==[x['id'] for x in xs];write(job/outname,terminal)
  write(job/'COUNTS.json',dict(n=7376,original_25pct=1844,cost=client.ledger.summary(),analysis_allowed=False));shutil.copy2(ledger/'ledger.jsonl',job/'LEDGER_AT_END.jsonl')
  files={str(p.relative_to(job)):sha(p) for p in job.rglob('*') if p.is_file()};write(job/'RESULT_SEAL.json',dict(status='TERMINAL_BLIND_GRID_NO_ANALYSIS',experiment='E81',files=files,completed_epoch=time.time(),packet_seal_sha256=a['packet_seal_sha256']));print('E81 complete blind grid sealed; private joins unopened')
 except BaseException as e:write(job/'BLOCKED.json',dict(at=time.time(),error_type=type(e).__name__,cost=client.ledger.summary(),retry=False));raise
if __name__=='__main__':main()
