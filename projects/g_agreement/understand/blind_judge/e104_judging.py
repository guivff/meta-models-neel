"""E104 U/N judging only; USD5 ledger and shared funded-queue HTTP402 latch."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path
from . import funded_queue as funded
from .run import ROOT
from .later_runner import channel_payload,classify
from .operational217 import audit_response as response_audit, judge, adapt as adapt_grid, truncated
from .privacy79 import redact,check_decoded
from .dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
HERE=ROOT/'results/g_agreement/understand/blind_judge/e104_bank'
CACHE=funded.CACHE/'E104'
CAP=Decimal('5')

def source_gate():
    for name,h in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(ROOT/name)==h,'E104 judge source pin')

def prepare(spec_path):
    source_gate()
    from projects.g_agreement.e104_analysis import adapter
    from projects.g_agreement.understand.wmech2 import core
    cfg=read(spec_path)
    require(all(Path(cfg[k]).resolve()==(CACHE/v).resolve() for k,v in [('blind','blind'),('private','PRIVATE.json'),('judgments','judgments')]),'analysis/judge paths agree; private join stays local')
    rows,_=adapter.inputs(cfg)
    require(bool(rows),'no eligible test cells: no judging bank')
    require(len(rows)<=672,'four cells at most, 84 paired test items each')
    CACHE.mkdir(parents=True,exist_ok=True)
    spec_sha=sha(spec_path)
    if (CACHE/'ADMISSION.json').exists():
        a=read(CACHE/'ADMISSION.json');require(a['inputs_sha256']==spec_sha,'unchanged admission spec')
        verify(CACHE/'blind/BLIND_SEAL.json',a['blind_seal_sha256']);return a
    require(not (CACHE/'blind').exists() and not (CACHE/'PRIVATE.json').exists(),'partial export: reconcile, never overwrite')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    core.export(rows,CACHE/'blind',CACHE/'PRIVATE.json',cfg['input_sha256'],commit)
    route,(api,privacy,p,io)=funded.route_api()
    packet,audit=redact(read(CACHE/'blind/WIRE_PACKET.json'),'E104',addresses=True)
    rubric=(CACHE/'blind/RUBRIC.md').read_text()
    bound=sum((api.upper(channel_payload(packet[i:i+4],rubric,'E56',p)) for i in range(0,len(packet),4)),Decimal(0))
    require(bound<=CAP,'complete E104 initial pass fits USD5; no partial selection')
    a=dict(bank='E104',records=len(rows),initial_requests=(len(rows)+3)//4,initial_upper_usd=str(bound),cap_usd='5',blind_seal_sha256=sha(CACHE/'blind/BLIND_SEAL.json'),source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),inputs_sha256=spec_sha,input_seal_sha256=cfg['input_sha256'],scope='E104 eligible U/N test cells only; terminal UNPARSEABLE remains missing',shared_credit_pause=str(funded.CACHE/'PAUSED_402.json'))
    shutil.copyfile(spec_path,CACHE/'INPUTS.json');write(CACHE/'ADMISSION.json',a);return a

def execute():
    source_gate();global_admission=read(CACHE/'GLOBAL_ADMISSION.json')
    require(global_admission['bank_admission_sha256']==sha(CACHE/'ADMISSION.json'),'global admission binds prepared bank')
    require((global_admission.get('verified_by_integrator') is True or (global_admission.get('verified_by_operator') is True and global_admission.get('issuer')=='W-internals-B')) and global_admission['bank']=='E104' and Decimal(str(global_admission['cap_usd']))==CAP and Decimal(str(global_admission['actual_plus_open_caps_usd']))<=Decimal('1000'),'section212 actual plus open caps admission')
    a=read(CACHE/'ADMISSION.json');require(a['source_seal_sha256']==sha(HERE/'SOURCE_SEAL.json') and a['inputs_sha256']==sha(CACHE/'INPUTS.json'),'unchanged E104 admission')
    require(not (funded.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 credit pause')
    verify(CACHE/'blind/BLIND_SEAL.json',a['blind_seal_sha256'])
    route,(api,privacy,p,io)=funded.route_api();api.CAP=CAP
    from .parallel_funded import patch_api
    patch_api(api,io,'E104')
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'credential unavailable')
    items,audit=redact(read(CACHE/'blind/WIRE_PACKET.json'),'E104',addresses=True);rubric=(CACHE/'blind/RUBRIC.md').read_text()
    saved=(p.payload,p.validate,privacy.check_wire,io.digest);ledger=CACHE/'ledger';ledger.mkdir(exist_ok=True)
    job=CACHE/'judgments';job.mkdir(exist_ok=True)
    with dispatch_lock(ledger/'DISPATCH.lock'):
        require(not (job/'JUDGMENT_SEAL.json').exists(),'already terminal')
        io.CACHE=ledger/'route';io.CACHE.mkdir(exist_ok=True)
        require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'account privacy proof')
        shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json');routes=privacy.check_route(key)
        p.payload=lambda stage,batch,unused=None:channel_payload(batch,rubric,'E56',p)
        p.validate=lambda stage,response,batch,unused=None:classify(batch,response)
        privacy.check_wire=lambda stage,batch,wire,unused=None:check_decoded(saved[2],batch,wire)
        client=api.Client(ledger,key);book,done=client.ledger.totals();require(set(book)==done,'reconcile unresolved before resume')
        for x in items:privacy.check_wire('',[x],p.payload('',[x]))
        audits=[]
        def send(batch,attempt):
            require(not (funded.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 credit pause')
            stage='E104_attempt'+str(attempt);prefix=stage+':'+a['blind_seal_sha256']+':'
            io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
            result=client.one(stage,batch);rp=ledger/stage/(result['id']+'.response.json')
            require(rp.exists(),'transport/unresolved stop; no resend');response=read(rp)
            funded.credit_gate(response,rp,'E104',stage,result['id'])
            require(not client.latch.is_set(),'transport latch')
            v=response_audit(response,p);require(result['id'] in client.ledger.totals()[1],'actual charge settled')
            v.update(request_id=result['id'],response_sha256=sha(rp));audits.append(v)
            write(job/'LIVE_PROGRESS.json',dict(bank='E104',verified_requests=len(audits),cost=client.ledger.summary()))
            if v.get('terminal_unparseable'):return truncated(batch)
            if result['status']=='OK':return result['value']
            try:json.loads(response['response']['choices'][0]['message']['content'])
            except (ValueError,TypeError):return classify(batch,{})
            raise RuntimeError('unexpected transport failure')
        write(CACHE/'STATUS.json',dict(status='RUNNING',bank='E104'))
        try:
            terminal=judge(items,send);flat,attempts=adapt_grid(terminal,items)
            write(job/'JUDGMENTS.json',flat);write(job/'TERMINAL.json',terminal);write(job/'ATTEMPTS.json',attempts)
            write(job/'JUDGE_COPY.json',items);write(job/'PATH_REDACTION_AUDIT.json',audit)
            write(job/'ROUTE_AUDIT.json',dict(routes=routes,requests=audits,privacy_proof_sha256=sha(route['privacy_proof']),inventory_sha256=sha(io.CACHE/'last_zdr_route_inventory.json')))
            write(job/'COUNTS.json',dict(records=a['records'],unparseable=sum(x['category']=='UNPARSEABLE' for x in flat),cost=client.ledger.summary(),scope=a['scope']))
            write(job/'JUDGMENT_SEAL.json',dict(bank='E104',blind_seal_sha256=a['blind_seal_sha256'],input_seal_sha256=a['input_seal_sha256'],global_admission_sha256=sha(CACHE/'GLOBAL_ADMISSION.json'),route_verified=bool(routes) and bool(audits),redaction_audit_complete=True,redacted_opaque_ids=[x['id'] for x in audit['affected']],source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),files={f.name:sha(f) for f in job.iterdir() if f.is_file() and f.name!='JUDGMENT_SEAL.json'}))
            write(CACHE/'STATUS.json',dict(status='COMPLETE',bank='E104',cost=client.ledger.summary()))
        except Exception as exc:
            write(CACHE/'STATUS.json',dict(status='PAUSED_402' if isinstance(exc,funded.CreditPause) else 'BLOCKED',error_type=type(exc).__name__,bank='E104',cost=client.ledger.summary()));raise
        finally:p.payload,p.validate,privacy.check_wire,io.digest=saved

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);parser.add_argument('--spec');args=parser.parse_args()
    if args.action=='prepare':
        require(bool(args.spec),'sealed E104 acquisition SPEC required');print(json.dumps(prepare(args.spec),sort_keys=True))
    else:execute()
