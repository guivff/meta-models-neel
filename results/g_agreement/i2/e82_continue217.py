"""§217 saved-state E82 continuation; never resend a charged/reserved request.
Original dispatch/source/allocation/intents stay immutable. Charged length is
terminal missing, while only ordinary validation failures use frozen retries.
"""
import json,time,hashlib,os,fcntl,shutil
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone
import e82_dispatch as D
H=D.H;R=D.R
PAUSE=R.parent/'cache/g_agreement/JUDGING_ACCOUNT_PAUSE_402.json'
class AccountCreditPause(RuntimeError):pass

def response_disposition(response):
 body=response.get('response',{});status=response.get('http_status')
 if status==402:return 'PAUSE_402'
 if status!=200:raise RuntimeError('UNRECOGNISED_PROVIDER_ERROR_'+str(status))
 assert body.get('provider')=='Google' and body.get('model')in ['google/gemini-3.1-flash-lite','google/gemini-3.1-flash-lite-001'],'PROVIDER_MODEL_STOP'
 assert body.get('usage',{}).get('cost')is not None,'UNKNOWN_COST_STOP'
 finish=body['choices'][0].get('finish_reason')
 if finish=='length':return 'TERMINAL_UNPARSEABLE'
 if finish=='stop':return 'VALIDATE'
 raise RuntimeError('UNRECOGNISED_PROVIDER_FINISH_'+str(finish))

def account_gate():
 if PAUSE.exists():
  p=D.read(PAUSE)
  if p.get('status')!='FUNDING_CONFIRMED_RESUMED':raise AccountCreditPause('ACCOUNT_HTTP402_PAUSED_ALL_BANKS')

def live_gate(v):
 p,records,rubric,original,old,allowed,route,api,privacy,protocol,io=v
 io.CACHE=H/'live_route_section217';io.CACHE.mkdir(exist_ok=True);proof=Path(route['privacy_proof']);assert D.sha(proof)==route['privacy_proof_sha256'];shutil.copy2(proof,io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
 key=os.environ.get('OPENROUTER_API_KEY');assert key;privacy.check_route(key)
 import requests
 q=requests.get('https://openrouter.ai/api/v1/credits',headers={'Authorization':'Bearer '+key},timeout=30);q.raise_for_status();credits=q.json()['data'];remaining=Decimal(str(credits['total_credits']))-Decimal(str(credits['total_usage']));assert remaining>0,'CREDITS_NOT_FUNDED'
 for xs,rr in [(records,rubric),(original,old)]:
  for item in xs:D.check_decoded(privacy.check_wire,[item],D.G.wire([item],rr,protocol,D.run.payload))
 D.write(H/'SECTION217_LIVE_PRIVACY_PREFLIGHT.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),all1020wires_checked=True,remaining_credits_usd=str(remaining),route_inventory_sha256=D.sha(io.CACHE/'last_zdr_route_inventory.json'),private_account_proof_sha256=D.sha(proof),no_calls=True))
 return key

def main():
 account_gate();v=D.source_preflight();key=live_gate(v)
 p,records,rubric,original,old,allowed,route,api,privacy,protocol,io=v
 cpath=R/'results/g_agreement/i2/E82_SECTION217_CONTINUATION.json';c=D.read(cpath);assert c['continuation_source_sha256']==D.sha(__file__) and c['original_dispatch_source_sha256']==D.sha(R/'results/g_agreement/i2/e82_dispatch.py')
 assert c['original_allocation_sha256']==D.sha(R/'results/g_agreement/i2/E82_JUDGE_ALLOCATION.json') and c['bank_cap_usd']==18 and c['section217_commit'].startswith('06823691')
 pub=D.read(H/'SECTION217_CONTINUATION_PUBLICATION.json');assert pub['receipt_sha256']==D.sha(cpath) and pub['shared_commit']
 assert (H/'DISPATCH_ONCE_INTENT.json').exists() and (H/'judging/E82_judgments/BLOCKED.json').exists() and not (H/'judging/E82_judgments/RESULT_SEAL.json').exists()
 g=D.read(H/'SECTION217_CONTINUATION_GLOBAL_PROOF.json');assert D.sha(H/'SECTION217_CONTINUATION_GLOBAL_PROOF.json')==c['global_proof_sha256'] and 0<=time.time()-datetime.fromisoformat(g['as_of_utc']).timestamp()<120
 ledger=H/'judging';job=ledger/'E82_judgments';lock=(ledger/'DISPATCH.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with (H/'SECTION217_CONTINUATION_ONCE_INTENT.json').open('x')as f:json.dump(dict(at=time.time(),receipt_sha256=D.sha(cpath)),f)
 api.CAP=Decimal(18);io.CACHE=H/'live_route_section217';original_check=privacy.check_wire;privacy.check_wire=lambda stage,batch,body,unused=None:D.check_decoded(original_check,batch,body)
 client=api.Client(ledger,key);cached=0;new_sends=0;truncations=[];saved=D.read(H/'SECTION217_SAVED_REQUESTS_MANIFEST.json');assert D.sha(H/'SECTION217_SAVED_REQUESTS_MANIFEST.json')==c['saved_requests_manifest_sha256']
 def pause(stage,rid,response):
  PAUSE.parent.mkdir(parents=True,exist_ok=True);D.write(PAUSE,dict(at_utc=datetime.now(timezone.utc).isoformat(),status='HTTP402_PAUSED_ALL_BANKS',bank='E82',stage=stage,request_id=rid,response_sha256=D.sha(response),funding_confirmation_required=True));raise AccountCreditPause('HTTP402_PAUSED_ALL_BANKS')
 try:
  for label,items,rr,name in [('E82',records,rubric,'JUDGMENTS.json'),('E82_original_25pct',original,old,'ORIGINAL_JUDGMENTS.json')]:
   protocol.payload=lambda stage,batch,unused=None,rr=rr:D.G.wire(batch,rr,protocol,D.run.payload)
   protocol.validate=lambda stage,response,batch,unused=None:D.classify(batch,response,allowed)
   def one(item,attempt):
    nonlocal cached,new_sends
    D.authority_gate();account_gate();body=D.G.wire([item],rr,protocol,D.run.payload);stage=label+'_attempt'+str(attempt);rid=hashlib.sha256((label+':'+str(attempt)+':'+io.canonical(body)).encode()).hexdigest();folder=ledger/stage;respath=folder/(rid+'.result.json');response_path=folder/(rid+'.response.json')
    io.digest=lambda value:hashlib.sha256((label+':'+str(attempt)+':'+value).encode()).hexdigest()
    if respath.exists():
     assert D.sha(respath)==saved[str(respath.relative_to(H))] and D.sha(response_path)==saved[str(response_path.relative_to(H))],'SAVED_RESPONSE_CHANGED'
     request_path=folder/(rid+'.request.json');assert D.sha(request_path)==saved[str(request_path.relative_to(H))] and D.read(request_path)['wire']==body,'SAVED_REQUEST_WIRE_CHANGED'
     result=D.read(respath);cached+=1;assert response_path.exists(),'CACHED_RESULT_WITHOUT_RESPONSE'
    else:
     book,done=client.ledger.totals();assert rid not in book,'PRIOR_RESERVED_REQUEST_NO_RESEND'
     D.actual_global_gate(api.upper(body));account_gate();result=client.one(stage,[item]);new_sends+=1
    assert response_path.exists(),'TRANSPORT_BUDGET_STOP_NO_RESEND'
    disposition=response_disposition(D.read(response_path))
    if disposition=='PAUSE_402':pause(stage,rid,response_path)
    if disposition=='TERMINAL_UNPARSEABLE':
     truncations.append(dict(id=item['id'],request_id=rid,stage=stage,response_sha256=D.sha(response_path)))
     return dict(id=item['id'],status='UNPARSEABLE',code=None,terminal_reason='CHARGED_LENGTH',attempts=attempt)
    if result['status']=='OK':return dict(result['value'][0],attempts=attempt)
    body=D.read(response_path)['response']
    try:json.loads(body['choices'][0]['message']['content'])
    except(ValueError,TypeError):return dict(id=item['id'],status='INVALID',code=None,attempts=attempt)
    raise RuntimeError('UNRECOGNISED_TRANSPORT_ERROR_STOP_NO_RETRY')
   final={}
   for item in items:
    final[item['id']]=one(item,0)
    D.write(job/(label+'_SECTION217_PROGRESS.json'),dict(at=time.time(),initial_done=len(final),initial_total=len(items),cached_requests_reused=cached,new_physical_requests=new_sends,charged_truncations=len(truncations),cost=client.ledger.summary()))
   for item in items:
    if final[item['id']]['status']in ('KEPT','UNPARSEABLE'):continue
    for attempt in (1,2):
     final[item['id']]=one(item,attempt)
     if final[item['id']]['status']in ('KEPT','UNPARSEABLE'):break
    if final[item['id']]['status']=='INVALID':final[item['id']].update(status='UNPARSEABLE',code=None)
   D.write(job/name,[final[x['id']]for x in items])
  D.write(job/'CHARGED_TRUNCATIONS_SECTION217.json',truncations);D.write(job/'COUNTS.json',dict(n=816,original_n=204,cost=client.ledger.summary(),cached_requests_reused=cached,new_physical_requests=new_sends,charged_truncations=len(truncations),analysis_allowed=False));shutil.copy2(ledger/'ledger.jsonl',job/'LEDGER_AT_END.jsonl')
  D.write(job/'RESULT_SEAL.json',dict(status='TERMINAL_BLIND_GRID_NO_ANALYSIS',experiment='E82',completed_epoch=time.time(),allocation_sha256=c['original_allocation_sha256'],section217_continuation_receipt_sha256=D.sha(cpath),adapter_preflight_sha256=D.sha(H/'grouped_adapter_v1/PREFLIGHT.json'),files={str(f.relative_to(job)):D.sha(f)for f in job.rglob('*')if f.is_file()}));print('E82 full blind grid sealed; charged length retained missing, no charged request resent')
 except BaseException as e:D.write(job/'SECTION217_BLOCKED.json',dict(at=time.time(),error_type=type(e).__name__,error=str(e),cost=client.ledger.summary(),retry=False));raise
if __name__=='__main__':main()
