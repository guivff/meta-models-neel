"""Prospective saved-state E124 continuation to Guiv's Fri15Z deadline.

No old source edit, settled request resend, reparse, label change or cap reset.
This module does not authorize e340 bound booking for E124: unknown costs stop.
"""
import argparse,hashlib,os,subprocess,time
from contextlib import contextmanager
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from . import transport,e124_channel,e124_phase236
from .phase233 import report_pin
from .accounting_e79b import snapshot
from .accounting import bank_actual
from .runner import CACHE
from .banks import validate_schema
from .. import funded_queue,parallel_funded
from ..operational217 import audit_response
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

DEADLINE=1793372400

def source_gate():
    p=transport.HERE/'E124_CONTINUATION236_SOURCE_SEAL.json'
    for n,h in read(p)['files'].items():require(sha(transport.ROOT/n)==h,'published separate E124 continuation source')
    return p


def dense_prefix(calls,terminals):
    ids=[c['id'] for c in calls];require(len(ids)==len(set(ids)),'unique original calls')
    by={t['id']:t for t in terminals};require(len(by)==len(terminals),'one retained terminal per original logical call')
    out=[]
    for ident in ids:
        if ident not in by:break
        t=by[ident];require(t['status'] in ('KEPT','UNPARSEABLE','REFUSED'),'original known terminal disposition');out.append(t)
    require({t['id'] for t in out}==set(by),'dense original prefix; no order inference or skipped cache')
    return out


def request_identity(input_sha,call,wire,rid):
    prefix='WIC:E124_'+call['phase']+':'+input_sha+':'+call['id']+':'
    base=hashlib.sha256((prefix+transport.canonical(wire)).encode()).hexdigest()
    require(rid in {base}|{hashlib.sha256(('RATE429:'+base+':'+str(i)).encode()).hexdigest() for i in range(1,5)},'original salted physical request identity')


def recover(dest,protocol):
    input_sha=sha(dest/'INPUT_SEAL.json');calls=read(dest/'CALLS.json');allowed={c['id']:c for c in calls};root=transport.SHARED/'E124/ledger'
    _,(api,_,_,_)=funded_queue.route_api();book,done=api.Ledger(root/'ledger.jsonl').totals();require(set(book)==done,'all previous physical charges known; no inferred zero')
    terminals=[];bindings=[];audits=[]
    for p in (root/'E124_judging').glob('*.terminal.json'):
        t=read(p)
        if t['input_sha256']!=input_sha:continue
        require(t['id'] in allowed and t['request_id'] in done,'same original call and settled physical request')
        rp=root/'E124_judging'/(t['request_id']+'.response.json');qp=root/'E124_judging'/(t['request_id']+'.request.json');saved=read(rp);request=read(qp);call=allowed[t['id']]
        require(sha(rp)==t['response_sha256'] and request['wire']==transport.frozen_wire(call,protocol),'byte-exact saved response and frozen wire')
        request_identity(input_sha,call,request['wire'],t['request_id'])
        require(saved.get('response',{}).get('usage',{}).get('cost') is not None,'no bound-booking authorization for E124')
        from decimal import Decimal
        require(Decimal(str(saved['response']['usage']['cost']))==book[t['request_id']],'exact provider charge equals original settlement')
        audit=audit_response(saved,protocol);terminals.append(t);bindings.append(dict(id=t['id'],path=str(rp),sha256=sha(rp)));audits.append(dict(audit,request_id=t['request_id'],response_sha256=sha(rp),recovered_saved_terminal=True))
    return dense_prefix(calls,terminals),bindings,audits


class ContinuationTransport(e124_channel.E124Transport):
    def __enter__(self):
        value=super().__enter__();self.original_post=self.api.requests.post
        def guarded_post(*a,**k):transport.unpaused();return self.original_post(*a,**k)
        self.api.requests.post=guarded_post;return value
    def __exit__(self,*a):
        self.api.requests.post=self.original_post
        return super().__exit__(*a)


@contextmanager
def worker():
    old=transport.EXPIRY;rate=parallel_funded.MAX_429_RETRIES
    transport.EXPIRY=DEADLINE;parallel_funded.MAX_429_RETRIES=0
    try:
        with e124_channel.worker():yield
    finally:transport.EXPIRY=old;parallel_funded.MAX_429_RETRIES=rate


def original_custody(dest):
    profile=read(transport.HERE/'E124_OPERATIONS236_SOURCE_SEAL.json')
    for n,h in profile['files'].items():require(sha(transport.ROOT/n)==h,'original E124 scientific/source profile unchanged')
    admission=read(dest/'ADMISSION.json');report_pin(admission,profile)
    cp=Path(admission['report_census_input_seal']);s=verify(cp,admission['report_census_input_sha256'])
    require(s['status']=='FROZEN_BEFORE_FIRST_CALL' and s['reference_sha256']=='61d87c57337064e297ccb6b183f9b6e6a647ac60c0940e5df18540fb4d6111c0','original model-reference cohort and pre-call census')
    e124_phase236.census_scope(read(cp.parent/'CENSUS.PRIVATE.json'),[x['id'] for x in read(dest/'CALLS.json')])
    return admission


def record_stop(job,exc):
    record=dict(status='STOPPED',bank='E124',error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True)
    write(job/'CONTINUATION236_STOPPED.json',record);write(job/'STATUS.json',record)


def execute(dest):
    source=source_gate();job=dest/'outputs';d=dest/'continuation236';r=read(d/'ADMISSION.json');pub=read(d/'PUBLICATION.json');allocation=Path(pub['allocation_path'])
    require(dest.resolve()==(CACHE/'E124/model_reference_consistency_judging').resolve() and not(job/'JUDGMENT_SEAL.json').exists(),'same unfinished phase only, never a completed bank replay')
    require(r['bank']=='E124' and r['lifetime_cap_usd']=='3' and r['continuation_source_sha256']==sha(source) and r['original_input_sha256']==sha(dest/'INPUT_SEAL.json') and r['original_admission_sha256']==sha(dest/'ADMISSION.json'),'same source/input/admission and lifetime3, no cap reset')
    require(subprocess.check_output(['git','show',pub['commit']+':'+str(allocation.relative_to(transport.ROOT))],cwd=transport.ROOT)==allocation.read_bytes() and sha(allocation)==pub['allocation_sha256']==sha(d/'ADMISSION.json'),'published new continuation admission')
    retired=r['retired_original_pid'];require(type(retired)is int and retired==3420 and subprocess.run(['ps','-p',str(retired),'-o','args='],capture_output=True).returncode!=0,'old own worker retired safely before new worker; no competing process')
    live=read(d/'LIVE_PROOF.PRIVATE.json');require(sha(d/'LIVE_PROOF.PRIVATE.json')==r['live_proof_sha256'] and 0<=time.time()-live['at_epoch']<300 and all(live[k] is True for k in ('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'fresh approved route/privacy/funding proof')
    a=original_custody(dest)
    with worker():
        transport.unpaused();proof=snapshot();require('E124'in proof['open_banks'],'same original bank still OPEN');write(d/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',proof)
        _,(_,_,protocol,_)=funded_queue.route_api()
        require(bank_actual(transport.SHARED/'E124/ledger')[1]==0,'no unresolved physical request')
        try:
            with ContinuationTransport(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY'])as channel:
                terminals,bindings,audits=recover(dest,channel.protocol)
                require(len(terminals)==r['recovered_readouts'],'exact dense recovered prefix under original bank lock')
                write(job/'CONTINUATION236_EXECUTION.json',dict(authority='Guiv236 amendment4 8ba4ecaca',source_sha256=sha(source),original_admission_unchanged=True,original_input_unchanged=True,recovered_not_resent=len(terminals),continuation_admission_sha256=sha(d/'ADMISSION.json')))
                for call in channel.calls[len(terminals):]:
                    schema=call['rendered']['schema']['schema'];t,audit=channel.call(call['id'],lambda v,s=schema:validate_schema(v,s));require(t['id']==call['id'],'exact original terminal ID')
                    raw=channel.root/'ledger'/('E124_'+call['phase'])/(t['request_id']+'.response.json');require(sha(raw)==t['response_sha256'],'exact new saved response')
                    terminals.append(t);audits.append(audit);bindings.append(dict(id=t['id'],phase=call['phase'],path=str(raw),sha256=sha(raw)))
                    write(job/'PROGRESS.json',dict(completed=len(terminals),n=len(channel.calls),cost=channel.summary(),at_epoch=time.time(),authority='236 amendment4'))
                require(len(terminals)==len(channel.calls),'all original calls terminal')
                write(job/'RESPONSES.json',terminals);write(job/'ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits));write(job/'RAW_RESPONSE_BINDINGS.json',bindings)
                write(job/'COUNTS.json',dict(n=len(terminals),status_counts=dict(Counter(t['status'] for t in terminals)),cost=channel.summary()))
                write(job/'STATUS.json',dict(status='COMPLETE',bank='E124',pid=os.getpid(),continuation_source_sha256=sha(source)))
                first=min(Path(x['path']).stat().st_mtime for x in bindings)
                write(job/'JUDGMENT_SEAL.json',dict(experiment='E124',phase='model_reference_consistency_judging',status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),first_output_source='earliest original retained physical response mtime',input_seal_sha256=sha(dest/'INPUT_SEAL.json'),source_seal_sha256=sha(transport.HERE/'SOURCE_SEAL.json'),E124_source_seal_sha256=sha(e124_channel.SOURCE),allocation_sha256=sha(dest/'ADMISSION.json'),continuation_source_sha256=sha(source),route_verified=True,labels_cpu_only=True,redaction_audit_complete=True,redacted_records=0,files={p.name:sha(p)for p in job.iterdir()if p.is_file()and p.name!='JUDGMENT_SEAL.json'}))
        except BaseException as exc:
            record_stop(job,exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase-directory',type=Path,required=True);a=p.parse_args();execute(a.phase_directory)
