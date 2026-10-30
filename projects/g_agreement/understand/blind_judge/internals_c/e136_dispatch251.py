"""Prospective E136 dispatch-only field-order correction; original phase/cap frozen."""
import argparse,json,os,time,subprocess
from collections import Counter
from pathlib import Path
from . import e136_channel250 as original,transport
from .e136_channel250 import worker,validate_plan
from .backend248 import BackendTransport
from .accounting250 import snapshot
from .accounting import bank_actual
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def cue_call(unit,protocol=None):
    # Exactly the original prepared order, independent of JSON serialization on disk.
    ordered={k:unit[k]for k in ('id','readout','source_text','question')}
    require(set(unit)==set(ordered),'no private/new fields')
    return original.cue_call(ordered,protocol)


def source_gate():
    p=transport.HERE/'E136_DISPATCH251_SOURCE_SEAL.json'
    for n,h in read(p)['files'].items():require(sha(transport.ROOT/n)==h,'prospective tested dispatch source')
    return p


def run(d):
 new_source=source_gate();source=original.source_gate();supp=d/'dispatch251';a=read(d/'ADMISSION.json');pub=read(d/'PUBLICATION.json');p=Path(pub['allocation_path']);live=read(supp/'LIVE_PROOF.PRIVATE.json')
 require(a['bank']=='E136'and a['allocation_usd']=='1'and a['E136_source_sha256']==sha(source)and a['input_sha256']==sha(d/'INPUT_SEAL.json'),'same original bank1/frozen question source')
 require(sha(p)==pub['allocation_sha256']==sha(d/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'published exact admission before calls')
 refresh=read(supp/'ADMISSION.json');posted=read(supp/'PUBLICATION.json');rp=Path(posted['allocation_path'])
 require(refresh['original_admission_sha256']==sha(d/'ADMISSION.json')and refresh['source_sha256']==sha(new_source)and sha(supp/'ADMISSION.json')==posted['allocation_sha256']==sha(rp)and subprocess.check_output(['git','show',posted['commit']+':'+str(rp.relative_to(transport.ROOT))],cwd=transport.ROOT)==rp.read_bytes(),'published prospective dispatch-only refresh')
 require(sha(supp/'LIVE_PROOF.PRIVATE.json')==refresh['live_route_funding_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in['route_verified','account_privacy_verified','funded_remaining_bank_cap']),'fresh source-bound dispatch proof')
 actual,unknown=bank_actual(transport.SHARED/'E136/ledger');require(actual==unknown==0 and not list((transport.SHARED/'E136/ledger/E136_judging').glob('*.request.json')),'original failed before any physical request; no restart of paid state')
 allowed={c['id']:c for c in read(d/'CALLS.json')}
 for plan in read(d/'VALIDATION.json'):
  expected,_=cue_call(plan['unit']);require(all(allowed[cid]['rendered']==expected['rendered']for cid in plan['calls']),'every unchanged original wire byte verified')
 verify(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'));validate_plan(read(d/'VALIDATION.json'),read(d/'CALLS.json'));job=d/'outputs';job.mkdir(exist_ok=True)
 with worker():
  g=snapshot();require('E136'in g['open_banks'],'actual original OPEN allocation present');write(supp/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',g)
 fd=os.open(supp/'DISPATCH_ONCE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);write(supp/'DISPATCH_ONCE.json',dict(pid=os.getpid(),source_sha256=sha(new_source)))
 with worker():
  transport.unpaused()
  try:
   with BackendTransport(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY'],zero_limit=2)as channel:
    rows=[];attempts=[];audits=[]
    for plan in read(d/'VALIDATION.json'):
     expected,validator=cue_call(plan['unit'],channel.protocol)
     for attempt,cid in enumerate(plan['calls']):
      require(channel.allowed[cid]['rendered']==expected['rendered'],'literal frozen direct question wire');t,audit=channel.call(cid,validator);attempts.append(dict(t,unit_id=plan['unit']['id'],attempt=attempt));audits.append(audit)
      if t['status']=='KEPT'or t.get('reason')in('CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED','UNCHARGED_BACKEND_RETRIES_EXHAUSTED'):break
     code=t['result']if t['status']=='KEPT'else None;status='KEPT'if code and code['code']in('YES','NO')else'UNPARSEABLE'
     rows.append(dict(id=plan['unit']['id'],kind='cue136',status=status,code=code,judgment=code['code']if code else'UNPARSEABLE',request_id=t['request_id'],response_sha256=t['response_sha256'],attempts=attempt));write(job/'PROGRESS.json',dict(at_epoch=time.time(),completed=len(rows),n=400,cost=channel.summary()))
    for name,value in [('JUDGMENTS.json',rows),('ATTEMPTS.json',attempts),('ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits)),('RAW_RESPONSE_BINDINGS.json',channel.physical),('COUNTS.json',dict(n=400,status_counts=dict(Counter(r['status']for r in rows)),cost=channel.summary())),('PATH_REDACTION_AUDIT.json',read(d/'PATH_REDACTION_AUDIT.json'))]:write(job/name,value)
    from datetime import datetime,timezone
    first=min(Path(x['path']).stat().st_mtime for x in channel.physical);write(job/'JUDGMENT_SEAL.json',dict(experiment='E136',phase='cue_judging250',status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_sha256=sha(d/'INPUT_SEAL.json'),source_sha256=sha(new_source),route_verified=True,labels_cpu_only=True,raw_git_export=False,files={p.name:sha(p)for p in job.iterdir()if p.is_file()}))
  except BaseException as exc:write(job/'DISPATCH251_STOPPED.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase-directory',type=Path,required=True);run(p.parse_args().phase_directory)
