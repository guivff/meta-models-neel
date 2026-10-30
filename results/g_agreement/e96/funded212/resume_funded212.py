"""§212 one saved pre-provider credit refusal, after confirmed funding.

No blanket credit402 retry: only the pinned response/request identity gets one
new reservation with identical wire. Frozen scientific files remain unchanged.
"""
import datetime,hashlib,json,shutil
from decimal import Decimal
from pathlib import Path
from . import resume_credit402 as c
from .reconstructor_check import digest,write
from .judge import ROOT
from projects.g_agreement.understand.blind_judge.run import route_modules
REFUSAL='cf3f88bc9f8b0dd8d157a42555c0c9f98053dd73779def7781c755862b3af76f'
RESPONSE_SHA='be362e8b59051d468e4f160de1db935981fbed43896d6449309e0f0d8844c91b'
RETRY=hashlib.sha256(('E96:SECTION212:FUNDED:'+REFUSAL).encode()).hexdigest()
STAGE='E96_current_attempt0_transport0'

def check_response(folder):
 p=folder/(REFUSAL+'.response.json');saved=json.loads(p.read_text());b=saved.get('response') or {};e=b.get('error') or {};m=e.get('metadata') or {}
 if digest(p)!=RESPONSE_SHA or saved.get('http_status')!=402 or e.get('code')!=402 or m.get('limit_source')!='openrouter_credits' or m.get('provider_name') is not None or b.get('id') or b.get('choices') or b.get('provider') or b.get('usage'):raise ValueError('not exact saved no-generation credit refusal; no resend')
 return p

def patch(api,io):
 original=api.Client.one
 def one(self,stage,items,taxonomy=None):
  result=original(self,stage,items,taxonomy)
  if stage!=STAGE or result['id']!=REFUSAL:return result
  folder=self.root/stage;check_response(folder);book,done=self.ledger.totals()
  if REFUSAL not in done or book[REFUSAL]!=0:raise RuntimeError('saved refusal not proven settledzero')
  if RETRY in book and RETRY not in done:raise RuntimeError('uncertain funded retry; never resend')
  wire=api.P.payload(stage,items,taxonomy)
  if json.loads((folder/(REFUSAL+'.request.json')).read_text())['wire']!=wire:raise ValueError('funded retry wire changed')
  self.latch.clear();previous=io.digest
  try:
   io.digest=lambda value:RETRY
   return original(self,stage,items,taxonomy)
  finally:io.digest=previous
 one._funded212=True;api.Client.one=one

def run(packet,allocation,receipt_dir,funding):
 d=json.loads(funding.read_text());age=datetime.datetime.now(datetime.timezone.utc).timestamp()-datetime.datetime.fromisoformat(d['as_of_utc']).timestamp()
 if age<0 or age>600 or Decimal(str(d['credits']['total_credits']))-Decimal(str(d['credits']['total_usage']))<Decimal('.013870625'):raise ValueError('fresh funded read-only proof required')
 route=json.loads((ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json').read_text());api,privacy,protocol,io=route_modules(route);c.bind_cap(api,packet,allocation)
 ledger_root=ROOT/'cache/g_agreement/e96/judging_120';folder=ledger_root/STAGE;p=check_response(folder);ledger=api.Ledger(ledger_root/'ledger.jsonl');book,done=ledger.totals()
 if set(book)-done not in (set(),{REFUSAL}):raise ValueError('other unsettled request; no resume')
 receipt_dir.mkdir(parents=True,exist_ok=False)
 proof={'authority':'direct Guiv §212: pause402, resume after topup; no route/token change','request_id':REFUSAL,'request_sha256':digest(folder/(REFUSAL+'.request.json')),'response_sha256':digest(p),'funding_proof_sha256':digest(funding),'funding_confirmed':True,'private_account_metadata_excluded':True,'reason':'exact saved HTTP402 openrouter_credits, no generation/provider/choices/usage; pre-provider credit refusal, resume authorized after topup','settled_usd':'0','new_request_id':RETRY,'identical_wire_required':True,'one_saved_refusal_only':True,'driver_sha256':digest(__file__),'scientific_change':False}
 write(receipt_dir/'SOURCE_RECEIPT.json',proof);shutil.copy2(__file__,receipt_dir/'EXECUTED_FUNDED212_DRIVER.py')
 if REFUSAL not in done:ledger.settle(REFUSAL,0)
 elif book[REFUSAL]!=0:raise ValueError('charged saved refusal; no resume')
 for name in ['SOURCE_RECEIPT.json','EXECUTED_FUNDED212_DRIVER.py']:shutil.copy2(receipt_dir/name,packet.parent/'judgments'/('FUNDED212_'+name))
 old=c.patch
 def both(api,io):old(api,io);patch(api,io)
 c.patch=both
 try:return c.run(packet,allocation,receipt_dir/'existing_transport')
 finally:c.patch=old
