"""E107b forecast judging; original398 target plans, same combined lifetime2.
No original E107 judgment, analysis or guard is rerun. Schema retries stay zero.
"""
import argparse,os,time,subprocess
from collections import Counter
from pathlib import Path
from . import registered,transport
from .e107b_generation243 import ForecastTransport,worker as generation_worker
from .runner import CACHE,seal_phase,preflight
from ..rubric202 import amended
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def source_gate():
    p=transport.HERE/'E107B_JUDGING245_SOURCE_SEAL.json'
    for n,h in read(p)['files'].items():require(sha(transport.ROOT/n)==h,'frozen E107b judging source')
    return p


def units_from(plans,generated,expected=398):
    by={x['id']:x for x in generated};require(len(by)==len(generated),'unique forecast IDs')
    require(set(by)=={p['forecast_id']for p in plans}and len(plans)==expected,'whole registered generation/target grid')
    units=[]
    for p in plans:
        g=by[p['forecast_id']]
        require(g['status']=='GENERATED'and g['phase']=='generation'and g['finish_reason']in('stop','length')and type(g['text'])is str and not g.get('refusal'),'literal complete forecast or explicit missing disposition needed')
        units.append(dict(id=p['judgment_id'],kind='value',data=dict(id=p['judgment_id'],property=p['property'],values=p['values'],readout=g['text']),rubric=amended().decode()))
    require(len({u['id']for u in units})==expected,'unique original target judgment IDs')
    return units


def prepare():
    source=source_gate();base=CACHE/'E107b';gen=base/'generation/outputs/GENERATION_SEAL.json';g=verify(gen,sha(gen));require(g['experiment']=='E107b'and g['status']=='COMPLETE'and g['bank_complete']is False,'full generation, bank not closed')
    original=base/'forecast_source/SOURCE_SEAL.json';verify(original,'95bb773c2e0c0af00a2daa0d45ce03371923809fa1b82398a22ba3a700ca16ee');plans=read(original.parent/'JUDGE_PLAN.PRIVATE.json');units=units_from(plans,read(gen.parent/'RESPONSES.json'))
    _,audit=redact([u['data']for u in units],'E107b',addresses=True)
    require(audit['redacted_records']==0,'owner redaction0 contract; stop for prospective companion if affected')
    _,(_,_,protocol,_)=registered.funded.route_api();calls=[];validation=[]
    for u in units:
        call,_=registered.unit_call(u,protocol);calls.append(call);validation.append(dict(unit=u,calls=[call['id']]))
    dest=base/'forecast_judging';require(not(dest/'INPUT_SEAL.json').exists(),'prepare once, frozen judging phase')
    dest=seal_phase('E107b','forecast_judging',calls,dict(generation_sha256=sha(gen),forecast_source_sha256=sha(original),judging_source_sha256=sha(source),n=398,max_schema_retries=0),[dict(seal=str(gen),sha256=sha(gen)),dict(seal=str(original),sha256=sha(original))])
    for n,v in [('UNITS.PRIVATE.json',units),('VALIDATION.json',validation),('TARGET_PLAN.PRIVATE.json',plans),('PATH_REDACTION_AUDIT.json',audit)]:write(dest/n,v)
    s=read(dest/'INPUT_SEAL.json');s['files'].update({n:sha(dest/n)for n in ['UNITS.PRIVATE.json','VALIDATION.json','TARGET_PLAN.PRIVATE.json','PATH_REDACTION_AUDIT.json']});write(dest/'INPUT_SEAL.json',s)
    with generation_worker():preflight(dest)
    return dest


def run(dest):
    source=source_gate();a=read(dest/'ADMISSION.json');pub=read(dest/'PUBLICATION.json');p=Path(pub['allocation_path']);live=read(dest/'LIVE_PROOF.PRIVATE.json')
    require(a['bank']=='E107b'and a['allocation_usd']=='2'and a['E107b_judging_source_sha256']==sha(source),'same combined2 bank/source')
    require(sha(p)==pub['allocation_sha256']==sha(dest/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'published source-bound phase beforecalls')
    require(sha(dest/'LIVE_PROOF.PRIVATE.json')==a['live_route_funding_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in ('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'fresh authenticated proof')
    verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'));job=dest/'outputs';job.mkdir(exist_ok=True)
    fd=os.open(dest/'JUDGING_ONCE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);write(dest/'JUDGING_ONCE.json',dict(pid=os.getpid(),source_sha256=sha(source),no_resend=True))
    with generation_worker():
        transport.unpaused()
        try:
            with ForecastTransport(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY'])as channel:
                units=[];attempts=[];audits=[]
                for plan in read(dest/'VALIDATION.json'):
                    expected,validator=registered.unit_call(plan['unit'],channel.protocol);cid=plan['calls'][0];require(channel.allowed[cid]['rendered']==expected['rendered'],'exact original primary rubric and frozen forecast')
                    t,audit=channel.call(cid,validator);attempts.append(t);audits.append(audit);units.append(dict(id=plan['unit']['id'],kind='value',status=t['status'],code=registered.normalized_code('value',t),attempts=0,request_id=t['request_id'],response_sha256=t['response_sha256']))
                    write(job/'PROGRESS.json',dict(completed=len(units),n=398,cost=channel.summary(),at_epoch=time.time()))
                require(len(units)==398,'all398 terminal including missing')
                for n,v in [('JUDGMENTS.json',units),('ATTEMPTS.json',attempts),('RAW_RESPONSE_BINDINGS.json',channel.physical),('ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits)),('COUNTS.json',dict(n=398,status_counts=dict(Counter(u['status']for u in units)),cost=channel.summary(),budget_release=False)),('PATH_REDACTION_AUDIT.json',read(dest/'PATH_REDACTION_AUDIT.json'))]:write(job/n,v)
                from datetime import datetime,timezone
                first=min(Path(r['path']).stat().st_mtime for r in channel.physical)
                write(job/'JUDGMENT_SEAL.json',dict(experiment='E107b',phase='forecast_judging',status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_sha256=sha(dest/'INPUT_SEAL.json'),source_sha256=sha(source),route_verified=True,labels_cpu_only=True,redacted_records=0,files={p.name:sha(p)for p in job.iterdir()if p.is_file()}))
        except BaseException as exc:write(job/'STOPPED.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--phase-directory',type=Path);a=p.parse_args()
    if a.action=='prepare':print(prepare())
    else:run(a.phase_directory)
