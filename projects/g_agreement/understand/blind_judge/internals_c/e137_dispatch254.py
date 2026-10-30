"""Prospective dispatch supplement; shared audit function unchanged, no prior calls."""
import argparse,os,time,subprocess
from pathlib import Path
from decimal import Decimal
from contextlib import contextmanager
from collections import Counter
from . import transport
from .e137_channel253 import N,PHASE,render,worker as original_worker
from .accounting253 import snapshot
from .backend248 import BackendTransport
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
OPS='projects/g_agreement/understand/blind_judge/operational217.py'
OPS_SHA='e257e51ea9ac0ab6ccec4147c20e010551568e108006f05c3618722288d0109f'
def source_gate(bank):
    require(bank=='E137','registered samebank');p=transport.HERE/'E137_DISPATCH254_SOURCE.json';s=read(p)
    for n,h in s['files'].items():require(sha(transport.ROOT/n)==h,'frozen prospective dispatch source')
    from .e137_channel253 import source_gate as old_gate
    old_gate(bank)
    for n,h in read(transport.HERE/'SOURCE_SEAL.json')['files'].items():
        require(sha(transport.ROOT/n)==(OPS_SHA if n==OPS else h),'original source with exact current OPS exception only')
    return p
@contextmanager
def worker(bank):
    with original_worker(bank):
        old=transport.source_gate;transport.source_gate=lambda:source_gate(bank)
        try:yield
        finally:transport.source_gate=old

def terminal_record(t):
    if t['status']!='KEPT':return None
    rows=t['result']['records'];require(len(rows)==1,'original singleton code');return rows[0]

def run(d):
    bank=read(d/'INPUT_SEAL.json')['experiment'];require(bank in N,'registered new phase');source=source_gate(bank);home=d/'dispatch254';a=read(home/'ADMISSION.json');pub=read(home/'PUBLICATION.json');p=Path(pub['allocation_path']);live=read(home/'LIVE_PROOF.PRIVATE.json')
    require(a['bank']==bank and a['allocation_usd']=='2'and a['bank_source_sha256']==sha(source)and a['input_sha256']==sha(d/'INPUT_SEAL.json'),'same registered source/cap2')
    require(sha(p)==pub['allocation_sha256']==sha(home/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'exact admission published before calls')
    require(sha(home/'LIVE_PROOF.PRIVATE.json')==a['live_route_funding_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in['route_verified','account_privacy_verified','funded_remaining_bank_cap']),'fresh authenticated proof')
    verify(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'));plans=read(d/'VALIDATION.json');allowed={x['id']:x for x in read(d/'CALLS.json')};require(len(plans)==N[bank]and len(allowed)==3*N[bank],'full first/retry inventory')
    for plan in plans:
        expected,_=render(bank,plan['unit']);require(all(allowed[cid]['rendered']==expected['rendered']for cid in plan['calls']),'roundtripped actual frozen wires')
    with worker(bank):g=snapshot();require(bank in g['open_banks'],'actual registered OPEN allocation');write(d/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',g)
    fd=os.open(d/'DISPATCH_ONCE254.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);write(d/'DISPATCH_ONCE254.json',dict(pid=os.getpid(),source_sha256=sha(source)));job=d/'outputs';job.mkdir(exist_ok=True)
    with worker(bank):
        try:
            with BackendTransport(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY'],zero_limit=2)as channel:
                rows=[];attempts=[];audits=[]
                for plan in plans:
                    expected,validator=render(bank,plan['unit'],channel.protocol)
                    for attempt,cid in enumerate(plan['calls']):
                        require(channel.allowed[cid]['rendered']==expected['rendered'],'literal rubric/payload');t,audit=channel.call(cid,validator);attempts.append(dict(t,unit_id=plan['unit']['id'],attempt=attempt));audits.append(audit)
                        if t['status']=='KEPT'or t.get('reason')in('CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED','UNCHARGED_BACKEND_RETRIES_EXHAUSTED'):break
                    code=terminal_record(t);status=t['status']
                    if bank=='E136R':status='KEPT'if code and code['code']in('YES','NO')else'UNPARSEABLE'
                    row=dict(id=plan['unit']['id'],kind=bank,status=status,code=code,request_id=t['request_id'],response_sha256=t['response_sha256'],attempts=attempt)
                    if bank=='E136R':row['judgment']=code['code']if code else'UNPARSEABLE'
                    rows.append(row);write(job/'PROGRESS.json',dict(at_epoch=time.time(),completed=len(rows),n=N[bank],cost=channel.summary()))
                for name,value in [('JUDGMENTS.json',rows),('ATTEMPTS.json',attempts),('ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits)),('RAW_RESPONSE_BINDINGS.json',channel.physical),('COUNTS.json',dict(n=N[bank],status_counts=dict(Counter(r['status']for r in rows)),cost=channel.summary())),('PATH_REDACTION_AUDIT.json',read(d/'PATH_REDACTION_AUDIT.json'))]:write(job/name,value)
                from datetime import datetime,timezone
                first=min(Path(x['path']).stat().st_mtime for x in channel.physical);write(job/'JUDGMENT_SEAL.json',dict(experiment=bank,phase=PHASE[bank],status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_sha256=sha(d/'INPUT_SEAL.json'),source_sha256=sha(source),route_verified=True,labels_cpu_only=True,raw_git_export=False,source_prompt_on_wire=False,files={p.name:sha(p)for p in job.iterdir()if p.is_file()}))
        except BaseException as exc:write(job/'STOPPED254.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise



if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase-directory',required=True,type=Path);a=p.parse_args();run(a.phase_directory)
