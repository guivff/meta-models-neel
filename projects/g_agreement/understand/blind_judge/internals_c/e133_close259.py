"""Administrative E133 lifetime close: sealed synthetic + final unjudgeable bAbI.
No model, response parsing, semantic reclassification, analysis, or archive rebuild.
"""
from decimal import Decimal
from datetime import datetime,timezone
from .transport import ROOT,HERE,SHARED
from .runner import CACHE
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

def validate_contract(phase,binding,rows,babi,actual,unknown,reported):
 require(phase['experiment']=='E133'and phase['status']=='COMPLETE'and phase['route_verified']is True and phase['phase']=='synthetic_naming_judging','original complete synthetic phase')
 require(binding['experiment']=='E133'and binding['arm']=='synthetic'and binding['status']=='COMPLETE_SOURCE_CODE_BINDING','original complete literal code binding')
 require(len(rows)==540 and len({r['id']for r in rows})==540 and all(r['status']in('KEPT','UNPARSEABLE')for r in rows),'full540 terminal synthetic judgments, no replay')
 require(babi['experiment']=='E133b'and babi['status']=='NOT_EVALUABLE_MEASUREMENT'and babi['screen_only']is True and babi['qualifying_pairs']==0 and babi['final_attempt_closed']is True and babi['further_runs_authorized']is False and babi['main_capture_readers_probes_patching']is False and babi['negative_result_claim']is False and babi['model_task_failure_claim']is False,'actual final screen-only measurement disposition, not pending source or scientific negative')
 require(Decimal(str(actual))==Decimal(str(reported)),'no cost beyond original published synthetic phase')
 return disposition(5,actual,unknown)

def close():
 source=HERE/'E133_CLOSE259_SOURCE_SEAL.json'
 for n,h in read(source)['files'].items():require(sha(ROOT/n)==h,'published tested administrative closure source')
 d=CACHE/'E133/synthetic_naming_judging/outputs';jp=d/'JUDGMENT_SEAL.json';bp=CACHE/'E133/synthetic_published_binding245/BINDING_SEAL.json';np=ROOT/'results/g_agreement/understand/e133b/FINAL_DISPOSITION.json';rp=ROOT/'results/g_agreement/understand/e133/C_SYNTHETIC_JUDGING_COMPLETE245/RECEIPT.json'
 authority=read(source)['original_sources']
 for p in(jp,bp,np,rp):require(sha(p)==authority[str(p)],'exact previously published original disposition/phase/binding/receipt')
 phase=verify(jp,sha(jp));binding=verify(bp,sha(bp));require(binding['judgment_sha256']==sha(jp),'original binding points to same immutable phase');rows=read(d/'JUDGMENTS.json');babi=read(np);receipt=read(rp)
 reported=receipt['total_booked_usd']
 with dispatch_lock(SHARED/'E133/DISPATCH.lock'):
  actual,unknown=bank_actual(SHARED/'E133/ledger');cost=validate_contract(phase,binding,rows,babi,actual,unknown,reported);ap=SHARED/'E133/ALLOCATION_C.json';allocation=read(ap);require(allocation['bank']=='E133'and allocation['operator']=='W-internals-C'and Decimal(allocation['allocation_usd'])==5 and allocation['reservation_included']is True,'same original combined lifetime5')
  out=CACHE/'E133/complete259';out.mkdir(exist_ok=True);final=out/'BANK_DISPOSITION_SEAL.json'
  if final.exists():verify(final,sha(final));require(read(out/'BANK_COST.json')==cost,'saved original close unchanged')
  else:
   require(allocation['status']=='OPEN','only close actual original open bank')
   write(out/'ORIGINAL_ALLOCATION.PRIVATE.json',allocation);write(out/'BANK_COST.json',cost)
   write(out/'PHASE_DISPOSITIONS.json',dict(synthetic=dict(status='COMPLETE',n=540,phase_seal=str(jp),phase_sha256=sha(jp),binding_seal=str(bp),binding_sha256=sha(bp)),babi=dict(status='NOT_EVALUABLE_MEASUREMENT',source=str(np),sha256=sha(np),screen_only=True,no_main_readouts=True,paid_judging='NOT_RUN_NO_ELIGIBLE_READOUTS',scientific_negative=False)))
   write(final,dict(experiment='E133',status='COMPLETE_REGISTERED_BANK_DISPOSITIONS',final_bank=True,completed_utc=datetime.now(timezone.utc).isoformat(),source_manifest_sha256=sha(source),route_verified=True,labels_cpu_only=True,scientific_analysis_run=False,prior_phase_seals_unchanged=True,source_seals=[dict(seal=str(jp),sha256=sha(jp)),dict(seal=str(bp),sha256=sha(bp))],files={n:sha(out/n)for n in('ORIGINAL_ALLOCATION.PRIVATE.json','BANK_COST.json','PHASE_DISPOSITIONS.json')}))
  if allocation['status']=='RELEASED':require(allocation['completion_seal_sha256']==sha(final),'same once-only release')
  else:
   require(allocation['status']=='OPEN','known allocation status');write(ap,dict(allocation,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
  write(SHARED/'E133/BANK_COMPLETE_C.json',dict(bank='E133',status='COMPLETE',registered_dispositions_complete=True,synthetic_judgments=540,babi_status='NOT_EVALUABLE_MEASUREMENT',babi_judging='NOT_RUN_NO_ELIGIBLE_READOUTS',seal=str(final),sha256=sha(final),**cost));return final

if __name__=='__main__':print(close())
