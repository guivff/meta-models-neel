"""E135 local-only full-bank closure and original-code pointer handoff."""
from decimal import Decimal
from .runner import CACHE
from .transport import ROOT,HERE,SHARED
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

def pointers(joins,rows,phase,n=336):
 by={r['id']:(i,r)for i,r in enumerate(rows)};require(len(joins)==len(rows)==len(by)==n and len({j['readout_id']for j in joins})==n and {j['id']for j in joins}==set(by),'full unique original readoutIDs')
 result={}
 for j in joins:
  i,r=by[j['id']];require(r['kind']=='original104'and(r['code']is None)==(r['status']!='KEPT'),'original code/null preserved')
  if r['code']is not None:require(r['code']['id']==j['id'],'literal codeID sibling')
  result[j['readout_id']]=dict(j,judgment_id=j['id'],status=r['status'],code_source=dict(seal=str(phase),sha256=sha(phase)if hasattr(phase,'exists')else'test',member='JUDGMENTS.json',keys=[i,'code']))
 return result

def close():
 for n,h in read(HERE/'E135_CLOSE245_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published admin source')
 d=CACHE/'E135/original104_judging_checked245';jp=d/'outputs/JUDGMENT_SEAL.json';s=verify(jp,sha(jp));require(s['status']=='COMPLETE'and s['experiment']=='E135'and s['raw_git_export']is False,'full correct private phase');verify(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'));binding=pointers(read(d/'SOURCE_POINTERS.PRIVATE.json'),read(jp.parent/'JUDGMENTS.json'),jp)
 with dispatch_lock(SHARED/'E135/DISPATCH.lock'):
  actual,unknown=bank_actual(SHARED/'E135/ledger');cost=disposition(1,actual,unknown);p=SHARED/'E135/ALLOCATION_C.json';a=read(p);require(a['bank']=='E135'and Decimal(a['allocation_usd'])==1,'original reducedcap1')
  out=CACHE/'E135/complete245';out.mkdir(exist_ok=True);final=out/'JUDGMENT_SEAL.json'
  if final.exists():verify(final,sha(final));require(read(out/'BANK_COST.json')==cost,'no latercost/reclose')
  else:
   require(a['status']=='OPEN','original open1');write(out/'READOUT_CODE_BINDINGS.PRIVATE.json',binding);write(out/'BANK_COST.json',cost);write(out/'ORIGINAL_ALLOCATION.PRIVATE.json',a);write(final,dict(experiment='E135',status='COMPLETE_JUDGING_BANK',n=336,route_verified=True,labels_cpu_only=True,raw_git_export=False,files={n:sha(out/n)for n in['READOUT_CODE_BINDINGS.PRIVATE.json','BANK_COST.json','ORIGINAL_ALLOCATION.PRIVATE.json']}))
  if a['status']=='RELEASED':require(a['completion_seal_sha256']==sha(final),'same once release')
  else:write(p,dict(a,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
  write(SHARED/'E135/BANK_COMPLETE_C.json',dict(bank='E135',status='COMPLETE',seal=str(final),sha256=sha(final),**cost));return final
