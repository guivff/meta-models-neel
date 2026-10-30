"""CPU-only exact original E104 records/native pointers and once bank1 closure."""
from decimal import Decimal
from .runner import CACHE
from .transport import ROOT,HERE,SHARED
from .e140_channel258 import N,PHASE
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

def pointers(joins,rows,phase,n):
 by={r['id']:(i,r)for i,r in enumerate(rows)};require(len(by)==len(rows)==len(joins)==n and len({j['native_key']for j in joins})==n and set(by)=={j['id']for j in joins},'full unique original index/readout IDs')
 refs={}
 for j in joins:
  i,r=by[j['id']];code=r['code'];require(r['kind']=='E140'and(code is None)==(r['status']!='KEPT')and(code is None or code['id']==j['id']),'unaltered literal code/null/opaqueID')
  refs[j['native_key']]=dict(j,judgment_id=j['id'],status=r['status'],code_source=dict(seal=str(phase),sha256=sha(phase)if hasattr(phase,'exists')else'test',member='JUDGMENTS.json',keys=[i,'code']),judgment_row_index=i,request_id=r['request_id'],response_sha256=r['response_sha256'])
 return refs

def close(bank):
 require(bank=='E140','registered original bank1')
 for n,h in read(HERE/'E140_CLOSE258_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'frozen CPU administrative source')
 d=CACHE/bank/PHASE[bank];jp=d/'outputs/JUDGMENT_SEAL.json';s=verify(jp,sha(jp));require(s['experiment']==bank and s['status']=='COMPLETE'and s['source_prompt_on_wire']is False and s['raw_git_export']is False,'complete readout-only phase');verify(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'));refs=pointers(read(d/'SOURCE_POINTERS.PRIVATE.json'),read(jp.parent/'JUDGMENTS.json'),jp,N[bank])
 with dispatch_lock(SHARED/bank/'DISPATCH.lock'):
  actual,unknown=bank_actual(SHARED/bank/'ledger');cost=disposition(1,actual,unknown);p=SHARED/bank/'ALLOCATION_C.json';a=read(p);require(a['bank']==bank and Decimal(a['allocation_usd'])==1,'original lifetime1')
  out=CACHE/bank/'complete258';out.mkdir(exist_ok=True);final=out/'JUDGMENT_SEAL.json'
  if final.exists():verify(final,sha(final));require(read(out/'BANK_COST.json')==cost,'saved once-only close exact')
  else:
   require(a['status']=='OPEN','original open bank');write(out/'READOUT_CODE_BINDINGS.PRIVATE.json',refs);write(out/'BANK_COST.json',cost);write(out/'ORIGINAL_ALLOCATION.PRIVATE.json',a);write(final,dict(experiment=bank,status='COMPLETE_JUDGING_BANK',n=348,route_verified=True,labels_cpu_only=True,analysis_run=False,raw_git_export=False,source_prompt_on_wire=False,source_seals=[dict(seal=str(jp),sha256=sha(jp))],files={n:sha(out/n)for n in['READOUT_CODE_BINDINGS.PRIVATE.json','BANK_COST.json','ORIGINAL_ALLOCATION.PRIVATE.json']}))
  if a['status']=='RELEASED':require(a['completion_seal_sha256']==sha(final),'same release once')
  else:write(p,dict(a,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
  write(SHARED/bank/'BANK_COMPLETE_C.json',dict(bank=bank,status='COMPLETE',seal=str(final),sha256=sha(final),**cost));return final
