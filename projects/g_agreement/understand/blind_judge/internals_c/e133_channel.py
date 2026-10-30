"""Source-bound E133 naming execution, combined lifetime5, both arms separate.

COMPLETE screened native units and fresh published admission are mandatory.
This channel invokes no scientific analysis, screening, reader, GPU or once-guard.
"""
import argparse,json,os,subprocess,time
from collections import Counter
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from . import registered,transport,resume_e340 as bounds
from .accounting_e79b import snapshot
from .e133_judge import naming_call,terminal_code,RUBRIC_SHA
from .e109_privacy import raw_evidence_guard
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

CAP=Decimal(5)


def source_gate():
    p=transport.HERE/'E133_SOURCE_SEAL.json'
    for n,h in read(p)['files'].items():require(sha(transport.ROOT/n)==h,'prospective E133 source pin')
    require(read(p)['report_adapter_pinned']is True,'actual tested owner adapter pinned before calls')
    return p


def unit_call(unit,protocol):
    require(set(unit)=={'id','kind','data'}and unit['kind']=='e133_naming'and unit['id']==unit['data']['id'],'literal blind naming unit')
    return naming_call(unit['data'],protocol)


def check_scope(bank,units,c):
    require(bank=='E133'and c.get('issuer')=='W-internals-C'and c.get('verified')is True and c.get('complete_eligible_native_grid')is True and c.get('labels_cpu_only')is True,'complete E133 original source custody')
    require(c['arm']in ('synthetic','babi')and c['rubric_sha256']==RUBRIC_SHA and 0<len(units)<=1008 and len({u['id']for u in units})==len(units),'same arm/rubric/full unique grid')
    require(len(units)==c['selected_items']*3 and c['native_status']=='COMPLETE'and c['screened_cohort_bound']is True,'all selected44/52/60 cells, no partial-source stitching')
    for unit in units:unit_call(unit,None)


def terminal(terminal):
    return terminal['status']=='KEPT'or terminal.get('reason')in ('CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED')


@contextmanager
def worker():
    source_gate();old=transport.CAPS.get('E133');expiry=transport.EXPIRY
    saved={n:getattr(registered,n)for n in ('HERE','unit_call','check_scope','normalized_code','snapshot')}
    transport.CAPS['E133']=CAP;bounds.CAPS['E133']=CAP;transport.EXPIRY=1793372400
    registered.HERE=transport.HERE/'E133';registered.unit_call=unit_call;registered.check_scope=check_scope;registered.normalized_code=lambda kind,t:terminal_code(t);registered.snapshot=snapshot
    try:yield
    finally:
        for n,v in saved.items():setattr(registered,n,v)
        transport.EXPIRY=expiry
        if old is None:transport.CAPS.pop('E133',None)
        else:transport.CAPS['E133']=old


def run(dest):
    source=source_gate();registered.source_gate(dest/'JUDGING_SOURCE_SEAL.json')
    verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'));a=read(dest/'ADMISSION.json');pub=read(dest/'PUBLICATION.json');p=Path(pub['allocation_path']);live=read(dest/'LIVE_PROOF.PRIVATE.json')
    require(a['bank']=='E133'and Decimal(str(a['allocation_usd']))==CAP and a['E133_source_sha256']==sha(source),'one registered bank5/source-bound admission')
    require(sha(p)==pub['allocation_sha256']==sha(dest/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'actual allocation published before first send')
    require(sha(dest/'LIVE_PROOF.PRIVATE.json')==a['live_route_funding_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in ('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'fresh source-bound live proof')
    job=dest/'outputs';require(not(job/'JUDGMENT_SEAL.json').exists(),'never replay completed bank phase');job.mkdir(exist_ok=True)
    s=read(dest/'INPUT_SEAL.json');unit_root=Path(s['source_seals'][0]['seal']).parent;original=read(unit_root/'ORIGINAL_EVIDENCE.PRIVATE.json');plans=read(dest/'VALIDATION.json')
    with worker():
        transport.unpaused();global_proof=snapshot();require('E133'in global_proof['open_banks'],'same original bank5 counted OPEN');write(dest/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',global_proof)
        try:
            with bounds.ResumeTransport(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY'])as channel:
                for fn in (channel.client.ledger.reserve,channel.client.ledger.settle,channel.client.ledger.summary,channel.unpaced):getattr(fn,'__func__',fn).__globals__['CAP']=CAP
                units=[];attempts=[];audits=[]
                for plan in plans:
                    expected,validator=raw_evidence_guard(lambda u:unit_call(u,channel.protocol),plan['unit'],original)
                    for attempt,cid in enumerate(plan['calls']):
                        require(channel.allowed[cid]['rendered']==expected['rendered'],'exact frozen renderer')
                        t,audit=channel.call(cid,validator);attempts.append(dict(t,unit_id=plan['unit']['id'],attempt=attempt));audits.append(audit)
                        if terminal(t):break
                    units.append(dict(id=plan['unit']['id'],kind='e133_naming',status=t['status'],code=terminal_code(t),attempts=attempt,request_id=t['request_id'],response_sha256=t['response_sha256']))
                    require(Decimal(channel.summary()['cap_usd'])==CAP,'physical cap5 retained');write(job/'PROGRESS.json',dict(completed=len(units),n=len(plans),cost=channel.summary(),at_epoch=time.time()))
                write(job/'JUDGMENTS.json',units);write(job/'ATTEMPTS.json',attempts);write(job/'ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits));write(job/'RAW_RESPONSE_BINDINGS.json',channel.physical)
                events=[json.loads(l)for l in (channel.root/'ledger/ledger.jsonl').read_text().splitlines()if l.strip()];events=[e for e in events if e.get('event')=='settle'and e.get('authority')=='e34073059']
                write(job/'BOOKED_429_BOUNDS.json',dict(events=events,provider_actual_cost_known=False));write(job/'COUNTS.json',dict(n=len(units),status_counts=dict(Counter(u['status']for u in units)),cost=channel.summary()));write(job/'PATH_REDACTION_AUDIT.json',read(unit_root/'PATH_REDACTION_AUDIT.json'))
                first=min(Path(r['path']).stat().st_mtime for r in channel.physical)
                from datetime import datetime,timezone
                write(job/'JUDGMENT_SEAL.json',dict(experiment='E133',phase=s['phase'],status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_sha256=sha(dest/'INPUT_SEAL.json'),source_seal_sha256=sha(dest/'JUDGING_SOURCE_SEAL.json'),E133_source_sha256=sha(source),route_verified=True,labels_cpu_only=True,redaction_audit_complete=True,files={p.name:sha(p)for p in job.iterdir()if p.is_file()}))
        except BaseException as exc:write(job/'STOPPED.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--spec',type=Path);p.add_argument('--phase-directory',type=Path);a=p.parse_args()
    with worker():
        if a.action=='prepare':print(registered.prepare(a.spec))
        else:run(a.phase_directory)
