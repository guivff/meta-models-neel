"""Sole I5 dispatcher for committed W-internals-B E98Bank; no scientific analysis."""
from pathlib import Path
import argparse,datetime,os,sys,time
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.understand.blind_judge.e98_channel import E98Bank,SHARED
from projects.g_agreement.readerbench.io import read,write,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--admission',type=Path,required=True);p.add_argument('--run',type=Path,required=True);a=p.parse_args();r=read(a.admission)
 assert r['bank']=='E98'and r['allocation_usd']==10 and time.time()<r['admission_expires_epoch']
 assert sha(Path(__file__))==r['operator_sha256'];assert not(a.run/'RUN_START.json').exists();assert not(SHARED/'PAUSED_402.json').exists();assert not(SHARED/'E98/judgments/JUDGMENT_SEAL.json').exists()
 src=Path(r['input_seal']);assert sha(src)==r['input_sha256'];bank=E98Bank(src,r['input_sha256']);pre=bank.preflight();assert pre['privacy_static_pass']and pre['source_seal_sha256']==r['source_seal_sha256']
 key=os.environ.get('OPENROUTER_API_KEY');assert key
 write(a.run/'RUN_START.json',dict(bank='E98',operator='I-5 sole dispatcher',pid=os.getpid(),start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),key_serialized=False,primary_records=pre['primary_records'],original_records=pre['old_rubric_records'],input_sha256=r['input_sha256'],source_seal_sha256=r['source_seal_sha256']))
 try:bank.run(r,key)
 except BaseException as exc:
  write(a.run/'RUN_FAILURE.json',dict(error_type=type(exc).__name__,timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()));raise
if __name__=='__main__':main()
