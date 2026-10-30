"""Once-only E86 terminal verification and exact source-pointer binding, no inference.
Does not launch the registered analysis watcher or append any cost ledger.
"""
from pathlib import Path
from decimal import Decimal
import json,hashlib,time,shutil
import e86_dispatch221 as D
R,H=D.R,D.H
sha,read,write=D.sha,D.read,D.write

def verify(path):
 s=read(path)
 for n,d in s['files'].items():assert sha(path.parent/n)==(d['sha256']if isinstance(d,dict)else d),n
 return s

def main():
 job=H/'judging/E86_judgments';p=job/'RESULT_SEAL.json';s=verify(p);assert s['experiment']=='E86' and s['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS'
 rows=read(job/'JUDGMENTS.json');old=read(job/'ORIGINAL_JUDGMENTS.json');records,_,original,_,_,_,_,_,_,_=D.source()
 assert len(rows)==800 and len(old)==200 and [x['id']for x in rows]==[x['id']for x in records] and [x['id']for x in old]==[x['id']for x in original]
 assert all(x['status']in ('KEPT','UNPARSEABLE') and (x['code']is not None)==(x['status']=='KEPT')for x in rows+old)
 counts=read(job/'COUNTS.json');cost=counts['cost'];assert Decimal(cost['unresolved_reserve_usd'])==0 and Decimal(cost['actual_usd'])<=4
 science=R/'cache/g_agreement/i2/section212_restarts_v1/e86-a2/full_terminal_pull/full_outputs/OUTPUT_SEAL.json';assert sha(science)=='cfa46523e1fe50337113679fbdada86568a0e6e92348088e28f5a978175fa075';verify(science)
 gate=R/'results/g_agreement/i2/e86_gate_diagnostics_v1/SOURCE_SEAL.json';verify(gate)
 out=H/'analysis_binding_section221';assert not out.exists();out.mkdir()
 write(out/'JUDGED_TEXT.json',[dict(id=x['id'],text=x['readout'])for x in records]);write(out/'TEXT_SEAL.json',dict(experiment='E86',source_packet_sha256=sha(H/'JUDGE_PACKET.json'),redaction_audit_sha256=sha(job/'PATH_REDACTION_AUDIT.json'),files={'JUDGED_TEXT.json':sha(out/'JUDGED_TEXT.json')}))
 sources=[dict(seal=str(q),sha256=sha(q))for q in [science,p,out/'TEXT_SEAL.json',gate]];oi={x['id']:i for i,x in enumerate(old)}
 ref=lambda member,keys,ix:dict(seal_index=ix,member=member,keys=keys)
 ms=[]
 for i,x in enumerate(rows):
  fields=dict(text=ref('JUDGED_TEXT.json',[i,'text'],2),code=ref('JUDGMENTS.json',[i,'code'],1))
  if x['id']in oi:fields['original_code']=ref('ORIGINAL_JUDGMENTS.json',[oi[x['id']],'code'],1)
  ms.append(dict(id=x['id'],fields=fields))
 write(out/'MEASUREMENTS.json',ms);write(out/'DIAGNOSTICS.json',{key:ref('GATE_DIAGNOSTICS.json',[key],3)for key in ['achieved_counts','truth_probes']})
 write(out/'OUTPUT_SEAL.json',dict(experiment='E86',status='COMPLETE',packet_source_sha256=sha(H/'SOURCE_SEAL.json'),private_join_sha256=sha(H/'JOIN_MAP.PRIVATE.json'),route_verified=True,redaction_audit_complete=True,original_subsample_ids=[x['id']for x in old],source_seals=sources,files={n:sha(out/n)for n in ['MEASUREMENTS.json','DIAGNOSTICS.json','JUDGED_TEXT.json','TEXT_SEAL.json']}))
 spec=dict(private_join=str(H/'JOIN_MAP.PRIVATE.json'),packet_source_seal=str(H/'SOURCE_SEAL.json'),release=str(R/'cache/g_agreement/i2/section212_restarts_v1/e86-a2/READER_RELEASE.json'),output_seal=str(out/'OUTPUT_SEAL.json'),output_sha256=sha(out/'OUTPUT_SEAL.json'),analysis=str(R/'cache/g_agreement/i2/e86_analysis_once'))
 write(out/'SPEC.json',spec)
 receipt=R/'results/g_agreement/i2/E86_JUDGE_COMPLETE_SECTION221.json';assert not receipt.exists()
 write(receipt,dict(at_epoch=time.time(),bank='E86',judgment_seal_sha256=sha(p),analysis_binding_seal_sha256=sha(out/'OUTPUT_SEAL.json'),allocation_closed_once=True,actual_usd=cost['actual_usd'],unresolved_usd='0',allocation_usd=4,unused_released_usd=str(Decimal(4)-Decimal(cost['actual_usd'])),primary_kept=sum(x['status']=='KEPT'for x in rows),primary_missing=sum(x['status']=='UNPARSEABLE'for x in rows),original_kept=sum(x['status']=='KEPT'for x in old),original_missing=sum(x['status']=='UNPARSEABLE'for x in old),no_new_cost_ledger_entry=True,no_GPU_booking=True,analysis_not_run=True,sole_author_watcher_owner='W-mech2'))
 print('Complete800+200 verified, cost settled, allocation closed once; exact private SPEC ready for sole owner watcher.')
if __name__=='__main__':main()
