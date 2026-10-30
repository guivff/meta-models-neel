"""Saved-state continuation under Guiv e34073059; no settled readout is resent.

429 liabilities are BOOKED UPPER BOUNDS, never represented as provider costs.
Original frozen inputs, prompts, codes, source and admission bytes stay unchanged.
"""
import argparse,fcntl,hashlib,json,os,subprocess,time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from . import transport,registered,e123_channel,e118b_channel
from .runner import CACHE
from .accounting_e79b import snapshot
from .accounting import bank_actual
from .banks import validate_schema
from .. import funded_queue,parallel_funded
from ..operational217 import audit_response
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

AUTHORITY='e34073059'
CAPS={'E123':Decimal(3),'E118':Decimal(1)}
PHASES={'E123':'original104_judging','E118':'belief_wrong_consistency_judging'}


def source_gate():
    p=transport.HERE/'RESUME_E340_SOURCE_SEAL.json'
    for n,h in read(p)['files'].items():require(sha(transport.ROOT/n)==h,'published saved-state continuation source')
    return p


def book_bound(root,rid,response_path,cap):
    """Append explicit upper-bound settlement once under the canonical ledger lock."""
    root=Path(root);response_path=Path(response_path);saved=read(response_path)
    require(saved['http_status']==429 and not saved.get('response',{}).get('choices'),'only saved rate refusal has this authority')
    p=root/'ledger.jsonl'
    with p.open('a+') as f:
        fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);rows=[json.loads(x) for x in f if x.strip()]
        reserved={r['id']:r for r in rows if r['event']=='reserve'};settled={r['id']:r for r in rows if r['event']=='settle'}
        require(rid in reserved,'existing physical reservation required, never invent one')
        if rid in settled:
            return settled[rid]  # Never overwrite/rebook an existing known or bound charge.
        upper=Decimal(reserved[rid]['usd'])
        booked=sum((Decimal(settled[k]['usd']) if k in settled else Decimal(v['usd']) for k,v in reserved.items()),Decimal(0))
        require(booked<=Decimal(cap),'booked bounds cannot exceed unchanged lifetime cap')
        event=dict(event='settle',id=rid,usd=str(upper),at=time.time(),authority=AUTHORITY,
            charge_basis='BOOKED_RESERVED_UPPER_BOUND',provider_actual_cost_known=False,
            response_sha256=sha(response_path),original_reserved_upper_usd=str(upper))
        f.write(transport.canonical(event)+'\n');f.flush();os.fsync(f.fileno())
        return event


def rate_loop(send,saved,book,wait):
    for retry in range(6):  # Initial request plus at most FIVE retries.
        if retry:wait(30*(2**(retry-1)))
        result=send(retry);response=saved(result['id'])
        if response['http_status']!=429:return result
        require(not response.get('response',{}).get('choices'),'429 completion ambiguity stops bank')
        book(result['id'])
    return result


def recovered(plans,terminals,completed=None):
    by={t['id']:t for t in terminals};require(len(by)==len(terminals),'unique saved physical logical-attempt terminals')
    results=[]
    for plan in plans:
        found=[]
        for ident in plan['calls']:
            if ident not in by:break
            t=by[ident];found.append(t)
            if t['status']=='KEPT' or t.get('reason') in ('CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED'):break
        if not found or (found[-1]['status']!='KEPT' and found[-1].get('reason') not in ('CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED') and len(found)!=len(plan['calls'])):break
        results.append(found)
    if completed is not None:require(len(results)==completed,'exact saved completed prefix')
    require({t['id'] for xs in results for t in xs}==set(by),'no terminal outside dense recovered prefix')
    return results


def prefix(bank,phase,input_sha,call_id):return 'WIC:'+bank+'_'+phase+':'+input_sha+':'+call_id+':'


def recover(dest,bank,protocol):
    input_sha=sha(dest/'INPUT_SEAL.json');calls=read(dest/'CALLS.json');allowed={c['id']:c for c in calls}
    plans=read(dest/'VALIDATION.json') if bank=='E123' else [dict(calls=[c['id']],unit=dict(id=c['id'],kind='consistency')) for c in calls]
    root=transport.SHARED/bank/'ledger';_,done=__import__('projects.g_agreement.understand.e13.api',fromlist=['Ledger']).Ledger(root/'ledger.jsonl').totals()
    terms=[];raws=[]
    for p in (root/(bank+'_judging')).glob('*.terminal.json'):
        t=read(p)
        if t['input_sha256']!=input_sha:continue
        require(t['id'] in allowed and t['request_id'] in done,'original input/settled terminal identity')
        response=root/(bank+'_judging')/(t['request_id']+'.response.json');request=root/(bank+'_judging')/(t['request_id']+'.request.json')
        require(sha(response)==t['response_sha256'] and read(request)['wire']==transport.frozen_wire(allowed[t['id']],protocol),'original saved response and exact frozen request')
        base=hashlib.sha256((prefix(bank,'judging',input_sha,t['id'])+transport.canonical(read(request)['wire'])).encode()).hexdigest()
        require(t['request_id'] in {base}|{hashlib.sha256(('RATE429:'+base+':'+str(i)).encode()).hexdigest() for i in range(1,5)},'original dispatch salt/physical request identity, never order join')
        terms.append(t);raws.append(dict(path=str(response),sha256=sha(response)))
    old=recovered(plans,terms,169 if bank=='E123' else 1222)
    return plans,old,raws


class ResumeTransport(transport.Transport):
    def __enter__(self):
        _,(api,_,_,_)=funded_queue.route_api();self.unpaced=api.Client.one
        require(not getattr(self.unpaced,'_parallel_patched',False),'new isolated process, original API client')
        result=super().__enter__();self.physical=[];self.bound_events=[]
        original_post=self.api.requests.post;self.original_post=original_post
        def guarded_post(*a,**k):transport.unpaused();return original_post(*a,**k)
        self.api.requests.post=guarded_post
        def one(client,stage,items,taxonomy=None):
            wire=self.api.P.payload(stage,items,taxonomy);canonical=self.io.canonical(wire);digest=self.io.digest;base=digest(canonical)
            def send(retry):
                rid=base if retry==0 else hashlib.sha256(('E340_RATE429:'+base+':'+str(retry)).encode()).hexdigest()
                self.io.digest=lambda value,rid=rid:rid
                if not(client.root/stage/(rid+'.result.json')).exists():
                    parallel_funded.claim_slot(self.bank);transport.unpaused()
                value=self.unpaced(client,stage,items,taxonomy)
                p=client.root/stage/(rid+'.response.json')
                require(p.exists(),'no response/no guessed settlement or reserved resend')
                self.physical.append(dict(path=str(p),sha256=sha(p)))
                return value
            def book(rid):
                p=client.root/stage/(rid+'.response.json');event=book_bound(client.root,rid,p,CAPS[self.bank]);self.bound_events.append(event)
            def wait(seconds):
                end=time.time()+seconds
                while time.time()<end:transport.unpaused();time.sleep(min(1,end-time.time()))
            try:return rate_loop(send,lambda rid:read(client.root/stage/(rid+'.response.json')),book,wait)
            finally:self.io.digest=digest
        self.api.Client.one=one
        return result

    def call(self,call_id,validator=None):
        transport.unpaused();c=self.allowed[call_id];stage=self.bank+'_'+c['phase']
        self.io.digest=lambda value:hashlib.sha256((prefix(self.bank,c['phase'],self.input_sha,call_id)+value).encode()).hexdigest()
        result=self.client.one(stage,[dict(id=call_id)]);p=self.root/'ledger'/stage/(result['id']+'.response.json');saved=read(p)
        if saved['http_status']==402:transport.pause(self.bank,p)
        require(not self.client.latch.is_set(),'bank transport failure latch')
        if saved['http_status']==429:
            t=dict(id=call_id,phase=c['phase'],status='UNPARSEABLE',reason='RATE_LIMIT_EXHAUSTED',result=None)
            audit=dict(http_status=429,terminal_missing=True,no_model_completion=True,budget_charge_basis='BOOKED_RESERVED_UPPER_BOUND',authority=AUTHORITY)
        else:t,audit=transport.decode(c,saved,self.protocol,validator)
        require(result['id'] in self.client.ledger.totals()[1],'known or explicitly booked charge required')
        t.update(request_id=result['id'],response_sha256=sha(p),input_sha256=self.input_sha)
        write(p.with_suffix('.terminal.json'),t)
        return t,dict(audit,request_id=result['id'],response_sha256=sha(p))

    def __exit__(self,*args):
        self.api.requests.post=self.original_post;self.api.Client.one=self.unpaced
        return super().__exit__(*args)


@contextmanager
def scope(bank,dest):
    before=transport.EXPIRY;transport.EXPIRY=1793372400
    try:
        with (e123_channel.worker(dest) if bank=='E123' else e118b_channel.worker()):yield
    finally:transport.EXPIRY=before


def execute(bank):
    source=source_gate();dest=CACHE/bank/PHASES[bank];resume=dest/'resume_e340';a=read(dest/'ADMISSION.json');r=read(resume/'ADMISSION.json');pub=read(resume/'PUBLICATION.json');allocation=Path(pub['allocation_path'])
    require(subprocess.check_output(['git','show',pub['commit']+':'+str(allocation.relative_to(transport.ROOT))],cwd=transport.ROOT)==allocation.read_bytes() and sha(allocation)==pub['allocation_sha256']==sha(resume/'ADMISSION.json'),'published resume source/admission')
    require(r['original_admission_sha256']==sha(dest/'ADMISSION.json') and r['input_sha256']==sha(dest/'INPUT_SEAL.json') and r['resume_source_sha256']==sha(source),'same original source/wires/bank')
    live=read(resume/'LIVE_PROOF.PRIVATE.json');require(sha(resume/'LIVE_PROOF.PRIVATE.json')==r['live_proof_sha256'] and 0<=time.time()-live['at_epoch']<300 and all(live[k] is True for k in ('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'fresh approved route/funding/privacy')
    job=dest/'outputs';require(not(job/'JUDGMENT_SEAL.json').exists(),'never replay complete bank')
    with scope(bank,dest):
        transport.unpaused();proof=snapshot();require(bank in proof['open_banks'],'same original bank remains open');write(resume/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',proof)
        _,(_,_,protocol,_)=funded_queue.route_api();plans,old,raws=recover(dest,bank,protocol)
        require(len(old)==r['recovered_readouts'],'exact saved-state prefix in posted admission')
        units=[];attempts=[];audits=[]
        def accept(plan,ts):
            for i,t in enumerate(ts):attempts.append(dict(t,unit_id=plan['unit']['id'],kind=plan['unit']['kind'],attempt=i))
            t=ts[-1]
            if bank=='E123':units.append(dict(id=plan['unit']['id'],kind=plan['unit']['kind'],status=t['status'],code=e123_channel.registered.normalized_code(plan['unit']['kind'],t),attempts=len(ts)-1,request_id=t['request_id'],response_sha256=t['response_sha256']))
            else:units.append(t)
        for plan,ts in zip(plans,old):accept(plan,ts)
        for b in raws:
            saved=read(b['path']);audits.append(dict(audit_response(saved,protocol),request_id=Path(b['path']).name.split('.')[0],response_sha256=b['sha256'],recovered_saved_terminal=True))
        try:
            with ResumeTransport(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY']) as channel:
                write(job/'RESUME_E340_EXECUTION.json',dict(authority=AUTHORITY,source_sha256=sha(source),resume_admission_sha256=sha(resume/'ADMISSION.json'),original_input_sha256=sha(dest/'INPUT_SEAL.json'),recovered_readouts=len(old),recovered_readouts_not_resent=True,provider_actual_cost_of_booked_bounds_known=False))
                for plan in plans[len(old):]:
                    if bank=='E123':expected,validator=registered.unit_call(plan['unit'],channel.protocol)
                    else:
                        expected=channel.allowed[plan['calls'][0]];schema=expected['rendered']['schema']['schema'];validator=lambda v,s=schema:validate_schema(v,s)
                    ts=[]
                    for ident in plan['calls']:
                        actual=channel.allowed[ident];require(actual['rendered']==expected['rendered'],'unchanged frozen rubric and wire')
                        t,audit=channel.call(ident,validator);ts.append(t);audits.append(audit)
                        if t['status']=='KEPT' or t.get('reason') in ('CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED'):break
                    accept(plan,ts);write(job/'PROGRESS.json',dict(completed=len(units),n=len(plans),cost=channel.summary(),authority=AUTHORITY,at_epoch=time.time()))
                require(len(units)==len(plans),'all original readouts terminal')
                write(job/('JUDGMENTS.json' if bank=='E123' else 'RESPONSES.json'),units)
                if bank=='E123':write(job/'ATTEMPTS.json',attempts)
                write(job/'ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits,rate_refusals_do_not_claim_model_completion=True))
                allraw={x['path']:x for x in raws+channel.physical}
                bookevents=[]
                for line in (channel.root/'ledger/ledger.jsonl').read_text().splitlines():
                    event=json.loads(line)
                    if event.get('authority')==AUTHORITY:
                        bookevents.append(event);p=channel.root/'ledger'/(bank+'_judging')/(event['id']+'.response.json');allraw[str(p)]=dict(path=str(p),sha256=sha(p))
                write(job/'RAW_RESPONSE_BINDINGS.json',list(allraw.values()))
                write(job/'BOOKED_429_BOUNDS.json',dict(authority=AUTHORITY,events=bookevents,total_booked_upper_bound_usd=str(sum((Decimal(e['usd']) for e in bookevents),Decimal(0))),provider_actual_cost_known=False))
                write(job/'COUNTS.json',dict(n=len(units),status_counts=dict(Counter(t['status'] for t in units)),cost=channel.summary(),booked_429_upper_bounds_included=True))
                first=min(Path(x['path']).stat().st_mtime for x in allraw.values());write(job/'STATUS.json',dict(status='COMPLETE',pid=os.getpid(),authority=AUTHORITY))
                write(job/'JUDGMENT_SEAL.json',dict(experiment=bank,status='COMPLETE',phase=PHASES[bank],first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),first_output_source='earliest original retained physical response mtime',input_sha256=sha(dest/'INPUT_SEAL.json'),input_seal_sha256=sha(dest/'INPUT_SEAL.json'),source_seal_sha256=sha(dest/'JUDGING_SOURCE_SEAL.json') if (dest/'JUDGING_SOURCE_SEAL.json').exists() else sha(transport.HERE/'SOURCE_SEAL.json'),resume_source_sha256=sha(source),E118b_source_seal_sha256=sha(e118b_channel.SOURCE) if bank=='E118' else None,route_verified=True,labels_cpu_only=True,redaction_audit_complete=True,redacted_records=0,booked_429_upper_bounds_included=True,provider_actual_cost_of_bounds_known=False,files={p.name:sha(p) for p in job.iterdir() if p.is_file() and p.name!='JUDGMENT_SEAL.json'}))
        except BaseException as exc:
            write(job/'RESUME_E340_STOPPED.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bank',choices=['E123','E118'],required=True);p.add_argument('--phase-directory',type=Path);args=p.parse_args()
    if args.phase_directory is not None:require(args.phase_directory.resolve()==(CACHE/args.bank/PHASES[args.bank]).resolve(),'registered original phase only')
    execute(args.bank)
