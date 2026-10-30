"""Sole saved-state E97 continuation under §217 clarification 2.

Original launch/admission/error remain immutable in their durable root. Reuses
canonical bank, exact input, original cache/ledger and fixed USD15 allocation.
"""
import argparse,os,sys,time,datetime
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.understand.blind_judge import e97_channel as channel
from projects.g_agreement.understand.blind_judge import transport217c2 as transport
from projects.g_agreement.ops.i5_e97_dispatch import bind_seal_metadata
from projects.g_agreement.readerbench.io import read,write,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--admission',type=Path,required=True);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
 r=read(a.admission)
 def require(v):
  if not v:raise ValueError('E97 saved-state resume binding')
 require(sha(__file__)==r['operator_sha256'] and time.time()<r['admission_expires_epoch'])
 require(r['authority']==transport.AUTHORITY and sha(transport.HERE/'SOURCE_SEAL.json')==r['transport_source_seal_sha256'])
 transport.source_gate()
 require(not(a.run/'RUN_START.json').exists() and not(channel.SHARED/'PAUSED_402.json').exists())
 require(not(channel.SHARED/'E97/judgments/JUDGMENT_SEAL.json').exists())
 require(sha(r['original_failed_response'])=='8b8a7a95e98fe7ebe12bd8d97be7e676d411ad0a4184c68099ef9b919b2d5a36')
 try:os.kill(23211,0)
 except ProcessLookupError:pass
 else:raise ValueError('Original E97 process still exists; no duplicate')
 src=Path(r['input_seal']);require(sha(src)==r['input_sha256'])
 auditpath=src.parent/'PATH_REDACTION_AUDIT.PRIVATE.json';audit=read(auditpath);require(sha(auditpath)==r['judge_copy_audit_sha256'])
 bank=channel.E97Bank(src,r['input_sha256']);pre=bank.preflight()
 require(pre['privacy_static_pass'] and pre['source_seal_sha256']==r['source_seal_sha256'])
 key=os.environ.get('OPENROUTER_API_KEY');require(bool(key))
 original=channel.write;job=channel.SHARED/'E97/judgments'
 def custody_write(path,value):
  if Path(path)==job/'JUDGMENT_SEAL.json':value=bind_seal_metadata(value,audit,sha(auditpath))
  return original(path,value)
 a.run.mkdir(parents=True,exist_ok=True)
 with (a.run/'RUN_START.json').open('x') as f:
  import json
  json.dump(dict(operator='I5 sole saved-state continuation',pid=os.getpid(),at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),authority=transport.AUTHORITY,input_sha256=r['input_sha256'],no_new_bank_allocation=True,key_serialized=False),f)
 channel.write=custody_write
 try:
  with transport.installed(channel):bank.run(r,key)
 except BaseException as exc:
  write(a.run/'RUN_FAILURE.json',dict(error_type=type(exc).__name__,at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()));raise
 finally:channel.write=original
if __name__=='__main__':main()
