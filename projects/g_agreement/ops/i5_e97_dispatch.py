"""Use the unchanged W-internals-B E97 channel with pre-bound redaction custody."""
from pathlib import Path
import argparse,json,os,sys,time,datetime,hashlib,subprocess
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.understand.blind_judge import e97_channel as channel
from projects.g_agreement.readerbench.io import read,write,sha

def bind_seal_metadata(value,audit,source_hash):
    if value.get('bank')!='E97' or value.get('primary_records')!=6668:raise ValueError('E97 seal only')
    result=dict(value);result['redacted_opaque_ids']=sorted(x['id']for x in audit['affected']);result['judge_copy_audit_sha256']=source_hash
    result['judge_copy_redaction_authority']=['79f63fe08aba5490367bf7579ddef3cfeb9d48a2','25c32f25'];result['affected_exclusion_sensitivity_required']=True
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--admission',type=Path,required=True);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    run=a.run;receipt=read(a.admission);require=lambda x: x or (_ for _ in ()).throw(ValueError('Frozen dispatch binding'))
    own=Path(__file__).resolve();require(sha(own)==receipt['operator_sha256']);require(time.time()<receipt['admission_expires_epoch'])
    src=Path(receipt['input_seal']);require(sha(src)==receipt['input_sha256']);auditpath=src.parent/'PATH_REDACTION_AUDIT.PRIVATE.json';audit=read(auditpath);require(sha(auditpath)==receipt['judge_copy_audit_sha256'])
    require(not(channel.SHARED/'PAUSED_402.json').exists());require(not(run/'RUN_START.json').exists());require(not(channel.SHARED/'E97/judgments/JUDGMENT_SEAL.json').exists())
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key))
    bank=channel.E97Bank(src,receipt['input_sha256']);pre=bank.preflight();require(pre['privacy_static_pass']and pre['source_seal_sha256']==receipt['source_seal_sha256'])
    job=channel.SHARED/'E97/judgments';job.mkdir(parents=True,exist_ok=True);write(job/'PATH_REDACTION_AUDIT.json',audit)
    original=channel.write
    def custody_write(path,value):
        if Path(path)==job/'JUDGMENT_SEAL.json':value=bind_seal_metadata(value,audit,sha(auditpath))
        return original(path,value)
    channel.write=custody_write
    write(run/'RUN_START.json',dict(bank='E97',operator='I-5 sole dispatcher',pid=os.getpid(),start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),input_sha256=receipt['input_sha256'],source_seal_sha256=receipt['source_seal_sha256'],key_serialized=False,redacted_records=audit['redacted_records'],full_unresolved_grid=6668,old_rubric_check=1667))
    try:bank.run(receipt,key)
    except BaseException as exc:
        write(run/'RUN_FAILURE.json',dict(error_type=type(exc).__name__,timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()));raise
    finally:channel.write=original
if __name__=='__main__':main()
