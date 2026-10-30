"""E124 bank3 continuation with cap enforced in the actual ledger namespaces.

Separate correction source; prior source/proofs/responses remain unchanged.
434061b36 permits e340 reserved-bound booking and registered rate retries.
"""
import argparse,hashlib,json,os,time
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from . import transport, resume_e340 as bounds, e124_continuation236 as old
from .accounting import bank_actual
from .accounting_e79b import snapshot
from .banks import validate_schema
from .runner import CACHE
from .. import funded_queue
from ..operational217 import audit_response
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require

CAP=Decimal(3)


def enforce_cap(api,client,unpaced):
    functions=[client.ledger.reserve,client.ledger.settle,client.ledger.summary,unpaced]
    namespaces=[api.__dict__]+[getattr(f,'__func__',f).__globals__ for f in functions]
    for namespace in namespaces:
        require('CAP' in namespace,'actual ledger/client cap namespace exists')
        namespace['CAP']=CAP
    require(all(n['CAP']==CAP for n in namespaces),'registered3 in every actual cap namespace')


class CappedTransport(bounds.ResumeTransport):
    def __enter__(self):
        result=super().__enter__();one=self.api.Client.one
        def capped_one(client,*args,**kwargs):
            enforce_cap(self.api,client,self.unpaced)
            require(Decimal(client.ledger.summary()['committed_usd'])<=CAP,'existing actual+unknown within3')
            return one(client,*args,**kwargs)
        self.api.Client.one=capped_one
        enforce_cap(self.api,self.client,self.unpaced)
        return result
    def summary(self):
        enforce_cap(self.api,self.client,self.unpaced)
        out=super().summary();require(Decimal(out['cap_usd'])==CAP,'summary must report registered3')
        return out


def recover(dest,channel):
    calls=read(dest/'CALLS.json');by={c['id']:c for c in calls};input_sha=sha(dest/'INPUT_SEAL.json')
    book,done=channel.client.ledger.totals();require(set(book)==done,'all saved charges settled or explicitly booked')
    rows=[json.loads(s)for s in (channel.root/'ledger/ledger.jsonl').read_text().splitlines()if s.strip()]
    bounds_by={r['id']:r for r in rows if r.get('event')=='settle'and r.get('authority')=='e34073059'}
    terminals=[];raws=[];audits=[];stage=channel.root/'ledger/E124_judging'
    for p in stage.glob('*.terminal.json'):
        t=read(p)
        if t['input_sha256']!=input_sha:continue
        require(t['id']in by and t['request_id']in done,'same saved settled input/call')
        rid=t['request_id'];rp=stage/(rid+'.response.json');qp=stage/(rid+'.request.json');saved=read(rp);wire=read(qp)['wire']
        require(sha(rp)==t['response_sha256']and wire==transport.frozen_wire(by[t['id']],channel.protocol),'exact original saved wire/response')
        base=hashlib.sha256((bounds.prefix('E124','judging',input_sha,t['id'])+transport.canonical(wire)).encode()).hexdigest()
        allowed={base}|{hashlib.sha256((tag+base+':'+str(i)).encode()).hexdigest()for tag in ('RATE429:','E340_RATE429:')for i in range(1,6)}
        require(rid in allowed,'original salted physical identity; no order join')
        if saved['http_status']==429:
            require(rid in bounds_by and bounds_by[rid]['response_sha256']==sha(rp)and not saved.get('response',{}).get('choices'),'only explicit booked refusal')
            audit=dict(http_status=429,terminal_missing=True,budget_charge_basis='BOOKED_RESERVED_UPPER_BOUND')
        else:
            require(saved.get('response',{}).get('usage',{}).get('cost')is not None and Decimal(str(saved['response']['usage']['cost']))==book[rid],'provider charge exactly reconciled')
            audit=audit_response(saved,channel.protocol)
        terminals.append(t);raws.append(dict(path=str(rp),sha256=sha(rp)));audits.append(dict(audit,request_id=rid,response_sha256=sha(rp),recovered_saved_terminal=True))
    for rid,event in bounds_by.items():
        p=stage/(rid+'.response.json');require(sha(p)==event['response_sha256'],'preserve each booked429raw');raws.append(dict(path=str(p),sha256=sha(p)))
    return old.dense_prefix(calls,terminals),raws,audits


def source_gate():
    p=transport.HERE/'E124_PARALLEL243B_SOURCE_SEAL.json'
    for n,h in read(p)['files'].items():require(sha(transport.ROOT/n)==h,'published corrected E124 source')
    return p


def execute(dest):
    require(dest.resolve()==(CACHE/'E124/model_reference_consistency_judging').resolve(),'only original E124 phase')
    source=source_gate();original=old.original_custody(dest);d=dest/'continuation243b';a=read(d/'ADMISSION.json');pub=read(d/'PUBLICATION.json');p=Path(pub['allocation_path']);job=dest/'outputs'
    require(not(job/'JUDGMENT_SEAL.json').exists()and a['lifetime_cap_usd']=='3'and a['source_sha256']==sha(source),'unfinished original bank3/source only')
    require(a['original_input_sha256']==sha(dest/'INPUT_SEAL.json')and a['original_admission_sha256']==sha(dest/'ADMISSION.json'),'original frozen input/admission untouched')
    import subprocess
    require(sha(p)==pub['allocation_sha256']==sha(d/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'corrected proof published')
    live=read(d/'LIVE_PROOF.PRIVATE.json');require(sha(d/'LIVE_PROOF.PRIVATE.json')==a['live_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in ('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'fresh corrected proof')
    bounds.CAPS['E124']=CAP
    with old.worker():
        transport.unpaused();write(d/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',snapshot())
        try:
            with CappedTransport(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'),original,os.environ['OPENROUTER_API_KEY'])as channel:
                terminals,raws,audits=recover(dest,channel);channel.summary()
                require(len(terminals)==a['recovered_readouts'],'exact accounted saved prefix under bank lock')
                write(job/'CONTINUATION243B_EXECUTION.json',dict(source_sha256=sha(source),recovered_not_resent=len(terminals),original_input_unchanged=True,bank_cap_enforced_usd='3',admission_sha256=sha(d/'ADMISSION.json')))
                for call in channel.calls[len(terminals):]:
                    schema=call['rendered']['schema']['schema'];t,audit=channel.call(call['id'],lambda v,s=schema:validate_schema(v,s));terminals.append(t);audits.append(audit)
                    raw=channel.root/'ledger/E124_judging'/(t['request_id']+'.response.json');require(sha(raw)==t['response_sha256'],'exact new response')
                    raws.append(dict(path=str(raw),sha256=sha(raw)));write(job/'PROGRESS.json',dict(completed=len(terminals),n=len(channel.calls),cost=channel.summary(),at_epoch=time.time(),authority='434061b36/e34073059'))
                require(len(terminals)==len(channel.calls),'all original6424 terminals')
                for r in channel.physical:raws.append(r)
                rawmap={r['path']:r for r in raws};events=[json.loads(s)for s in (channel.root/'ledger/ledger.jsonl').read_text().splitlines()if s.strip()];events=[r for r in events if r.get('event')=='settle'and r.get('authority')=='e34073059']
                write(job/'RESPONSES.json',terminals);write(job/'ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits));write(job/'RAW_RESPONSE_BINDINGS.json',list(rawmap.values()))
                write(job/'BOOKED_429_BOUNDS.json',dict(events=events,total_booked_upper_bound_usd=str(sum((Decimal(r['usd'])for r in events),Decimal(0))),provider_actual_cost_known=False))
                write(job/'COUNTS.json',dict(n=len(terminals),status_counts=dict(Counter(t['status']for t in terminals)),cost=channel.summary(),booked_bounds_not_provider_actual=True))
                write(job/'STATUS.json',dict(status='COMPLETE',bank='E124',source_sha256=sha(source)))
                first=min(Path(r['path']).stat().st_mtime for r in rawmap.values())
                write(job/'JUDGMENT_SEAL.json',dict(experiment='E124',phase='model_reference_consistency_judging',status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_seal_sha256=sha(dest/'INPUT_SEAL.json'),source_seal_sha256=sha(transport.HERE/'SOURCE_SEAL.json'),E124_source_seal_sha256=sha(transport.HERE/'E124_SOURCE_SEAL.json'),continuation_source_sha256=sha(source),route_verified=True,labels_cpu_only=True,redaction_audit_complete=True,redacted_records=0,files={f.name:sha(f)for f in job.iterdir()if f.is_file()and f.name!='JUDGMENT_SEAL.json'}))
        except BaseException as exc:
            write(job/'CONTINUATION243B_STOPPED.json',dict(status='STOPPED',error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase-directory',type=Path,required=True);execute(p.parse_args().phase_directory)
