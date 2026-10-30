"""Prospective isolated E137462 judging; unchanged E133 rubric/native custody."""
import argparse,os,time,subprocess,json
from pathlib import Path
from decimal import Decimal
from contextlib import contextmanager
from collections import Counter
from . import transport,resume_e340 as bounds,registered
from .runner import CACHE,seal_phase,preflight
from .backend248 import BackendTransport
from .accounting253 import snapshot
from .banks import opaque
from .e133_judge import naming_call
from .e138_judge253 import assert_value_allowlist
from .e137_intake253 import intake
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
N={'E137':462};PHASE={'E137':'naming_judging253'}
def render(bank,unit,p=None):
    require(bank=='E137' and set(unit)=={'id','property','values','readout'},'registered blind E133 allowlist');ordered=dict(id=unit['id'],property=unit['property'],values={k:unit['values'][k]for k in sorted(unit['values'])},readout=unit['readout']);return naming_call(ordered,p)
def source_gate(bank):
    require(bank=='E137','registered exactbank');p=transport.HERE/'E137_SOURCE253.json';s=read(p)
    for n,h in s['files'].items():require(sha(transport.ROOT/n)==h,'frozen prospective source')
    for n,h in s['owner_frozen_files'].items():require(sha(n)==h,'genuine tested committed owner source copies')
    return p
@contextmanager
def worker(bank):
    source_gate(bank);old=transport.CAPS.get(bank);expiry=transport.EXPIRY;transport.CAPS[bank]=Decimal(2);bounds.CAPS[bank]=Decimal(2);transport.EXPIRY=1793372400
    try:yield
    finally:
        transport.EXPIRY=expiry
        if old is None:transport.CAPS.pop(bank,None)
        else:transport.CAPS[bank]=old

def prepare():
    bank='E137';source=source_gate(bank);unitseal=intake();us=verify(unitseal,sha(unitseal));units=read(unitseal.parent/'UNITS.json');plans=[];calls=[];_,(_,_,protocol,_)=registered.funded.route_api()
    for u in units:
        original,_=render(bank,u,protocol);assert_value_allowlist(original,json.loads(original['rendered']['user'])[0],'E137');ids=[]
        for attempt in range(3):
            c=dict(original,id=opaque(bank,'judging',u['id'],str(attempt)));calls.append(c);ids.append(c['id'])
        plans.append(dict(unit=u,calls=ids))
    _,audit=redact([dict(id=u['id'],readout=u['readout'])for u in units],bank,addresses=True);require(audit['redacted_records']==0,'any privacy copies require source companion')
    d=CACHE/bank/PHASE[bank];require(not(d/'INPUT_SEAL.json').exists(),'prepareonce')
    d=seal_phase(bank,PHASE[bank],calls,dict(n=462,max_schema_retries=2,bank_source_sha256=sha(source),raw_git_export=False,source_prompt_on_wire=False),[dict(seal=str(unitseal),sha256=sha(unitseal))]+us['source_seals'])
    for name,value in [('VALIDATION.json',plans),('SOURCE_POINTERS.PRIVATE.json',read(unitseal.parent/'SOURCE_POINTERS.PRIVATE.json')),('PATH_REDACTION_AUDIT.json',audit)]:write(d/name,value)
    s=read(d/'INPUT_SEAL.json');s['files'].update({n:sha(d/n)for n in['VALIDATION.json','SOURCE_POINTERS.PRIVATE.json','PATH_REDACTION_AUDIT.json']});write(d/'INPUT_SEAL.json',s)
    with worker(bank):preflight(d)
    return d

def run(d):
    bank=read(d/'INPUT_SEAL.json')['experiment'];require(bank in N,'registered new phase');source=source_gate(bank);a=read(d/'ADMISSION.json');pub=read(d/'PUBLICATION.json');p=Path(pub['allocation_path']);live=read(d/'LIVE_PROOF.PRIVATE.json')
    require(a['bank']==bank and a['allocation_usd']=='2'and a['bank_source_sha256']==sha(source)and a['input_sha256']==sha(d/'INPUT_SEAL.json'),'same registered source/cap2')
    require(sha(p)==pub['allocation_sha256']==sha(d/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'exact admission published before calls')
    require(sha(d/'LIVE_PROOF.PRIVATE.json')==a['live_route_funding_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in['route_verified','account_privacy_verified','funded_remaining_bank_cap']),'fresh authenticated proof')
    verify(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'));plans=read(d/'VALIDATION.json');allowed={x['id']:x for x in read(d/'CALLS.json')};require(len(plans)==N[bank]and len(allowed)==3*N[bank],'full first/retry inventory')
    for plan in plans:
        expected,_=render(bank,plan['unit']);require(all(allowed[cid]['rendered']==expected['rendered']for cid in plan['calls']),'roundtripped actual frozen wires')
    with worker(bank):g=snapshot();require(bank in g['open_banks'],'actual registered OPEN allocation');write(d/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',g)
    fd=os.open(d/'JUDGING_ONCE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);write(d/'JUDGING_ONCE.json',dict(pid=os.getpid(),source_sha256=sha(source)));job=d/'outputs';job.mkdir(exist_ok=True)
    with worker(bank):
        try:
            with BackendTransport(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY'],zero_limit=2)as channel:
                rows=[];attempts=[];audits=[]
                for plan in plans:
                    expected,validator=render(bank,plan['unit'],channel.protocol)
                    for attempt,cid in enumerate(plan['calls']):
                        require(channel.allowed[cid]['rendered']==expected['rendered'],'literal rubric/payload');t,audit=channel.call(cid,validator);attempts.append(dict(t,unit_id=plan['unit']['id'],attempt=attempt));audits.append(audit)
                        if t['status']=='KEPT'or t.get('reason')in('CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED','UNCHARGED_BACKEND_RETRIES_EXHAUSTED'):break
                    code=t['result']if t['status']=='KEPT'else None;status=t['status']
                    if bank=='E136R':status='KEPT'if code and code['code']in('YES','NO')else'UNPARSEABLE'
                    row=dict(id=plan['unit']['id'],kind=bank,status=status,code=code,request_id=t['request_id'],response_sha256=t['response_sha256'],attempts=attempt)
                    if bank=='E136R':row['judgment']=code['code']if code else'UNPARSEABLE'
                    rows.append(row);write(job/'PROGRESS.json',dict(at_epoch=time.time(),completed=len(rows),n=N[bank],cost=channel.summary()))
                for name,value in [('JUDGMENTS.json',rows),('ATTEMPTS.json',attempts),('ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits)),('RAW_RESPONSE_BINDINGS.json',channel.physical),('COUNTS.json',dict(n=N[bank],status_counts=dict(Counter(r['status']for r in rows)),cost=channel.summary())),('PATH_REDACTION_AUDIT.json',read(d/'PATH_REDACTION_AUDIT.json'))]:write(job/name,value)
                from datetime import datetime,timezone
                first=min(Path(x['path']).stat().st_mtime for x in channel.physical);write(job/'JUDGMENT_SEAL.json',dict(experiment=bank,phase=PHASE[bank],status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_sha256=sha(d/'INPUT_SEAL.json'),source_sha256=sha(source),route_verified=True,labels_cpu_only=True,raw_git_export=False,source_prompt_on_wire=False,files={p.name:sha(p)for p in job.iterdir()if p.is_file()}))
        except BaseException as exc:write(job/'STOPPED253.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--phase-directory',type=Path);a=p.parse_args();print(prepare())if a.action=='prepare'else run(a.phase_directory)
