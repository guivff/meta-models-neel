"""Registered path/address judge copies; raw inventory remains immutable."""
from pathlib import Path
import json,hashlib,os,sys,datetime
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.understand.blind_judge.privacy79 import redact
from projects.g_agreement.understand.blind_judge.e97_channel import E97Bank
from projects.g_agreement.readerbench.io import sha,read,write

def main():
 src=Path('cache/g_agreement/understand/e97/judge_inventory_v1');dest=Path('cache/g_agreement/understand/e97/judge_copy_v1');assert not dest.exists(),'Never rebuild actual judge copy'
 raw=read(src/'CANDIDATES.PRIVATE.json');copied,audit=redact(raw,'E97',addresses=True)
 assert len(raw)==len(copied)==6668
 for a,b in zip(raw,copied):assert a['id']==b['id']and a['property']==b['property']
 dest.mkdir(parents=True);os.chmod(dest,0o700)
 write(dest/'CANDIDATES.PRIVATE.json',copied);write(dest/'PATH_REDACTION_AUDIT.PRIVATE.json',audit)
 sources=[]
 for reader in ['oracle','nla']:
  p=Path('cache/g_agreement/understand/e97')/(reader+'_native_complete')/'out/OUTPUT_SEAL.json';sources.append(dict(seal=str(p.resolve()),sha256=sha(p)))
 seal=dict(experiment='E97',status='FROZEN_READY',labels_cpu_only=True,native_per_reader_counts=dict(oracle=3360,nla=3360),selected_per_reader_counts=dict(oracle=3308,nla=3360),regex_resolved_retained=52,files={n:sha(dest/n)for n in ['CANDIDATES.PRIVATE.json','PATH_REDACTION_AUDIT.PRIVATE.json']},source_seals=sources,raw_inventory_sha256=sha(src/'CANDIDATES.PRIVATE.json'),judge_copy_only=True,redaction_authorities=['79f63fe08aba5490367bf7579ddef3cfeb9d48a2','25c32f25'])
 write(dest/'INPUT_SEAL.json',seal)
 for p in dest.iterdir():os.chmod(p,0o600)
 bank=E97Bank(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'));pre=bank.preflight();write(dest/'PREFLIGHT.json',pre);os.chmod(dest/'PREFLIGHT.json',0o600)
 receipt=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),bank='E97',input_seal=str((dest/'INPUT_SEAL.json').resolve()),input_sha256=sha(dest/'INPUT_SEAL.json'),raw_candidate_sha256=sha(src/'CANDIDATES.PRIVATE.json'),judge_copy_sha256=sha(dest/'CANDIDATES.PRIVATE.json'),audit_sha256=sha(dest/'PATH_REDACTION_AUDIT.PRIVATE.json'),redacted_records=audit['redacted_records'],affected_opaque_ids=[x['id']for x in audit['affected']],sensitivity_required=audit['sensitivity_required'],preflight=pre,paid_calls=0,reservation_posted=False)
 write(Path('results/g_agreement/understand/e97/I5_JUDGE_COPY_PREFLIGHT_RECEIPT.json'),receipt)
 print(json.dumps(dict(status=pre['status'],redacted=audit['redacted_records'],blocked_ids=len(pre['blocked_opaque_ids']),bound=pre['sum_initial_output_cap_bounds_usd'])))
if __name__=='__main__':main()
