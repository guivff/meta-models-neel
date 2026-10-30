"""Exact-wire transport continuation for proven pre-provider inflight402 refusals.

Does not alter frozen judge/packet/rubrics. Ordinary402 and uncertain requests
remain blocked. Official OpenRouter limits docs establish pre-provider rejection.
"""
import datetime,hashlib,json,time,shutil
from pathlib import Path
from . import resume_transport as rt
from .judge import ROOT
from .reconstructor_check import digest,write
from projects.g_agreement.understand.blind_judge.run import route_modules
DOC='https://github.com/OpenRouterTeam/docs/blob/main/api_reference/limits.mdx'
MAX_RETRIES=4

def proven(saved):
 b=saved.get('response') or {};e=b.get('error') or {};m=e.get('metadata') or {};u=b.get('usage') or {}
 return (saved.get('http_status')==402 and e.get('code')==402 and m.get('reason')=='in_flight_budget_exhausted' and m.get('limit_source')=='openrouter_in_flight_budget' and m.get('provider_name') is None and not b.get('id') and not b.get('choices') and not b.get('provider') and all(v in (0,None) for k,v in u.items() if k in ('cost','prompt_tokens','completion_tokens','total_tokens')))

def retry_id(base,k):return hashlib.sha256(f'E96:PREPROVIDER_INFLIGHT402:{base}:{k}'.encode()).hexdigest()

def reconcile(ledger,folder,rid):
 response=folder/(rid+'.response.json');request=folder/(rid+'.request.json');saved=json.loads(response.read_text())
 if not proven(saved):raise ValueError('not proven pre-provider inflight402; never settle/resend')
 book,done=ledger.totals()
 if rid not in book:raise ValueError('reservation missing')
 proof={'request_id':rid,'request_sha256':digest(request),'response_sha256':digest(response),'reason':'HTTP402 exact in_flight_budget_exhausted/openrouter_in_flight_budget, no generation/provider/choices; official docs say rejected before reaching provider','source':DOC,'actual_usd':'0','scientific_change':False}
 p=folder/(rid+'.preprovider402_reconciliation.json')
 if p.exists() and json.loads(p.read_text())!=proof:raise ValueError('reconciliation evidence changed')
 if not p.exists():write(p,proof)
 if rid not in done:ledger.settle(rid,0)
 elif book[rid]!=0:raise ValueError('charged refusal never resent')
 return saved

def patch(api,io):
 original=api.Client.one
 if getattr(original,'_e96_inflight402',False):return
 def one(self,stage,items,taxonomy=None):
  result=original(self,stage,items,taxonomy);base=result['id'];folder=self.root/stage
  for k in range(1,MAX_RETRIES+1):
   rid=result['id'];response=folder/(rid+'.response.json')
   if not response.exists() or not proven(json.loads(response.read_text())):return result
   saved=reconcile(self.ledger,folder,rid);book,done=self.ledger.totals();new=retry_id(base,k)
   if new in book and new not in done:raise RuntimeError('uncertain402 retry reservation; never resend')
   wire=api.P.payload(stage,items,taxonomy)
   if json.loads((folder/(rid+'.request.json')).read_text())['wire']!=wire:raise ValueError('changed retry wire')
   if new not in book:
    delay=int(saved['response']['error']['metadata'].get('headers',{}).get('Retry-After',120))
    if delay<0 or delay>600:raise ValueError('invalid Retry-After; no resend')
    remaining=max(0,delay-(time.time()-response.stat().st_mtime))
    while remaining>0:
     wait=min(30,remaining);time.sleep(wait);remaining-=wait
   self.latch.clear() # exact proven pre-provider rejection only; sequential dispatcher
   previous=io.digest
   try:
    io.digest=lambda value,new=new:new
    result=original(self,stage,items,taxonomy)
   finally:io.digest=previous
  final=folder/(result['id']+'.response.json')
  if final.exists() and proven(json.loads(final.read_text())):reconcile(self.ledger,folder,result['id'])
  return result
 one._e96_inflight402=True;api.Client.one=one

def run(packet,allocation,receipt_dir):
 route=json.loads((ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json').read_text());api,privacy,protocol,io=route_modules(route)
 ledger_root=ROOT/'cache/g_agreement/e96/judging_120';ledger=api.Ledger(ledger_root/'ledger.jsonl');book,done=ledger.totals()
 for rid in set(book)-done:
  paths=list(ledger_root.glob('*/'+rid+'.response.json'))
  if len(paths)!=1:raise ValueError('uncertain request without unique saved response; no resume')
  reconcile(ledger,paths[0].parent,rid)
 receipt_dir.mkdir(parents=True,exist_ok=True)
 driver=receipt_dir/'EXECUTED_CREDIT402_DRIVER.py';shutil.copy2(__file__,driver)
 write(receipt_dir/'SOURCE_RECEIPT.json',{'driver_sha256':digest(__file__),'original_resume_driver_sha256':digest(rt.__file__),'official_source':DOC,'policy':'only proven pre-provider inflight402; max4 new reservations, identical wire, Retry-After honored; unknown/charged/ordinary402 never resent','first_output_utc':'unknown','scientific_change':False})
 for src in [driver,receipt_dir/'SOURCE_RECEIPT.json']:
  dest=packet.parent/'judgments'/('CREDIT402_'+src.name)
  if dest.exists() and digest(dest)!=digest(src):raise ValueError('executed driver evidence changed')
  if not dest.exists():shutil.copy2(src,dest)
 old=rt.patch_client
 def both(api,io,protocol):old(api,io,protocol);patch(api,io)
 rt.patch_client=both
 try:return rt.run(packet,allocation,receipt_dir/'runtime')
 finally:rt.patch_client=old
