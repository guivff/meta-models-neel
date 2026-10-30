"""E79 Arm B reader-only channel, original E104 transport, separate USD3."""
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
from .deadline236 import paid_window
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
HERE=ROOT/'results/g_agreement/understand/blind_judge/e79b_bank'
CACHE=funded.CACHE/'E79_ARM_B'
CAP=Decimal('3')
SHARED=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue')
funded.CACHE=SHARED
CACHE=SHARED/'E79_ARM_B'
OWNER=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e79/arm_b')
from .parallel_funded import patch_api
from .operational217 import audit_response,adapt
from projects.g_agreement.understand.wmech2 import core

def source_gate():
    seal=HERE/'SOURCE_SEAL.json'
    for name,h in read(seal)['files'].items():
        require(sha(ROOT/name)==h,'E79_ARM_B judge source pin')
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        require(hashlib.sha256(blob).hexdigest()==h,'uncommitted E79B dependency')
    blob=subprocess.check_output(['git','show','HEAD:'+str(seal.relative_to(ROOT))],cwd=ROOT)
    require(hashlib.sha256(blob).hexdigest()==sha(seal),'uncommitted E79B source seal')

def packet(spec_path):
    cfg=read(spec_path)
    require(Path(spec_path).resolve()==OWNER/'SPEC.json','owner original SPEC only')
    for name,h in read(HERE/'INPUTS.json')['files'].items():require(sha(name)==h,'sealed original delivery binding')
    require(cfg['cap']==dict(bank='E79_ARM_B',lifetime_USD=3,owner='W-internals-B',separate_from_Arm_A=True),'separate reader-only cap')
    blind=Path(cfg['blind']);seal=core.verify(blind/'BLIND_SEAL.json',read(HERE/'INPUTS.json')['blind_seal_sha256'])
    require(seal['private_sha256']==sha(cfg['private']),'original local private join')
    items=read(blind/'WIRE_PACKET.json');source=read(blind/'JUDGE_PACKET.json')
    from .judgment_adapter402 import render_record
    rubric=(blind/'RUBRIC.md').read_text()
    require(items==[render_record(x,rubric)for x in source],'original frozen prompt render roundtrip')
    require(len(items)==len({x['id']for x in items})==672,'all672 reader records')
    require(sha(blind/'RUBRIC.md')=='03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613','original E59 reader rubric')
    return cfg,items,rubric


def prepare(spec_path):
    source_gate();cfg,raw,rubric=packet(spec_path)
    route,(api,privacy,p,io)=funded.route_api()
    items,audit=redact(raw,'E79_ARM_B',addresses=True)
    for i in range(0,len(items),4):check_decoded(privacy.check_wire,items[i:i+4],channel_payload(items[i:i+4],rubric,'E56',p))
    bound=sum((api.upper(channel_payload(items[i:i+4],rubric,'E56',p))for i in range(0,len(items),4)),Decimal(0))
    require(bound<=CAP,'initial all-record output-cap bounds exceed USD3; no silent token/roster change')
    CACHE.mkdir(parents=True,exist_ok=True)
    prepared=dict(bank='E79_ARM_B',records=672,initial_requests=168,initial_upper_usd=str(bound),cap_usd='3',
        blind_seal_sha256=sha(Path(cfg['blind'])/'BLIND_SEAL.json'),source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),
        inputs_sha256=sha(spec_path),input_seal_sha256=cfg['output_sha256'],cap_binding_sha256=sha(OWNER/'CAP_BINDING.json'),
        private_join_sha256=sha(cfg['private']),scope='reader half only; original behaviour frozen; terminal missing remains missing',
        redacted_records=audit['redacted_records'],privacy_static_pass=True,shared_credit_pause=str(SHARED/'PAUSED_402.json'),paid_calls=0)
    if (CACHE/'ADMISSION.json').exists():require(read(CACHE/'ADMISSION.json')==prepared,'immutable prior prepared source')
    else:
        shutil.copyfile(spec_path,CACHE/'INPUTS.json');write(CACHE/'ADMISSION.json',prepared)
    return prepared


def source_safe(codes,originals):
    by={x['id']:x for x in originals};result=[];audit=[]
    for code in codes:
        try:core.score(code,'A',by[code['id']]['readout']);result.append(code)
        except (ValueError,KeyError,TypeError):
            result.append(dict(id=code['id'],category='UNPARSEABLE',values=[],evidence=''))
            audit.append(dict(id=code['id'],reason='JUDGE_COPY_EVIDENCE_NOT_VALID_ON_ORIGINAL_SOURCE'))
    return result,audit


def execute():
    import time
    source_gate();global_admission=read(CACHE/'GLOBAL_ADMISSION.json')
    require(0<=time.time()-global_admission['created_epoch']<=300 and global_admission['allocation_included'] is True and global_admission['unknown_reservations_retained'] is True and global_admission['higher_priority_banks_cleared'] is True,'fresh concrete bank/global admission')
    require(global_admission['bank_admission_sha256']==sha(CACHE/'ADMISSION.json'),'global admission binds prepared bank')
    require((global_admission.get('verified_by_integrator') is True or (global_admission.get('verified_by_operator') is True and global_admission.get('issuer')=='W-internals-B')) and global_admission['bank']=='E79_ARM_B' and Decimal(str(global_admission['cap_usd']))==CAP and CAP<=Decimal(str(global_admission['actual_plus_open_caps_usd']))<=Decimal('1000'),'section212 actual plus open caps admission')
    a=read(CACHE/'ADMISSION.json');require(a['source_seal_sha256']==sha(HERE/'SOURCE_SEAL.json') and a['inputs_sha256']==sha(CACHE/'INPUTS.json'),'unchanged E79_ARM_B admission')
    require(not (funded.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 credit pause')
    cfg,original,rubric=packet(OWNER/'SPEC.json')
    require(sha(Path(cfg['blind'])/'BLIND_SEAL.json')==a['blind_seal_sha256'],'same original blind')
    require(not (ROOT.parent/'cache/g_agreement/JUDGING_ACCOUNT_PAUSE_402.json').exists(),'account HTTP402 pause')
    route,(api,privacy,p,io)=funded.route_api();api.CAP=CAP
    patch_api(api,io,'E79_ARM_B')
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'credential unavailable')
    items,audit=redact(original,'E79_ARM_B',addresses=True)
    saved=(p.payload,p.validate,privacy.check_wire,io.digest);ledger=CACHE/'ledger';ledger.mkdir(exist_ok=True)
    job=CACHE/'judgments';job.mkdir(exist_ok=True)
    with dispatch_lock(ledger/'DISPATCH.lock'), paid_window(api,pauses=[funded.CACHE/'PAUSED_402.json',ROOT.parent/'cache/g_agreement/JUDGING_ACCOUNT_PAUSE_402.json']):
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
            import time
            require(time.time()<1793372400,'standing authority expired')
            require(not (ROOT.parent/'cache/g_agreement/JUDGING_ACCOUNT_PAUSE_402.json').exists(),'account402pause')
            require(not (funded.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 credit pause')
            stage='E79_ARM_B_attempt'+str(attempt);prefix=stage+':'+a['blind_seal_sha256']+':'
            io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
            result=client.one(stage,batch);rp=ledger/stage/(result['id']+'.response.json')
            require(rp.exists(),'transport/unresolved stop; no resend');response=read(rp)
            funded.credit_gate(response,rp,'E79_ARM_B',stage,result['id'])
            require(not client.latch.is_set(),'transport latch')
            v=audit_response(response,p);require(result['id'] in client.ledger.totals()[1],'actual charge settled')
            v.update(request_id=result['id'],response_sha256=sha(rp));audits.append(v)
            write(job/'LIVE_PROGRESS.json',dict(bank='E79_ARM_B',verified_requests=len(audits),cost=client.ledger.summary()))
            if v.get('terminal_unparseable'):return truncated(batch)
            if result['status']=='OK':return result['value']
            try:json.loads(response['response']['choices'][0]['message']['content'])
            except (ValueError,TypeError):return classify(batch,{})
            raise RuntimeError('unexpected transport failure')
        write(CACHE/'STATUS.json',dict(status='RUNNING',bank='E79_ARM_B'))
        try:
            terminal=judge(items,send);flat,attempts=adapt(terminal,items)
            flat,evidence_audit=source_safe(flat,original)
            write(job/'ORIGINAL_EVIDENCE_AUDIT.json',evidence_audit)
            write(job/'ADMISSION.json',a)
            cost=client.ledger.summary();require(Decimal(cost['unresolved_reserve_usd'])==0 and Decimal(cost['actual_usd'])<=CAP,'fully settled separate lifetime cap')
            write(job/'JUDGMENTS.json',flat);write(job/'TERMINAL.json',terminal);write(job/'ATTEMPTS.json',attempts)
            write(job/'JUDGE_COPY.json',items);write(job/'PATH_REDACTION_AUDIT.json',audit)
            write(job/'ROUTE_AUDIT.json',dict(routes=routes,requests=audits,privacy_proof_sha256=sha(route['privacy_proof']),inventory_sha256=sha(io.CACHE/'last_zdr_route_inventory.json')))
            write(job/'COUNTS.json',dict(records=a['records'],unparseable=sum(x['category']=='UNPARSEABLE' for x in flat),cost=client.ledger.summary(),scope=a['scope']))
            write(job/'JUDGMENT_SEAL.json',dict(bank='E79_ARM_B',actual_USD=float(Decimal(cost['actual_usd'])),unknown_charges=0,cap_binding_sha256=a['cap_binding_sha256'],blind_seal_sha256=a['blind_seal_sha256'],input_seal_sha256=a['input_seal_sha256'],global_admission_sha256=sha(CACHE/'GLOBAL_ADMISSION.json'),route_verified=bool(routes) and bool(audits),redaction_audit_complete=True,redacted_opaque_ids=[x['id'] for x in audit['affected']],source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),files={f.name:sha(f) for f in job.iterdir() if f.is_file() and f.name!='JUDGMENT_SEAL.json'}))
            write(CACHE/'STATUS.json',dict(status='COMPLETE',bank='E79_ARM_B',cost=client.ledger.summary()))
        except Exception as exc:
            write(CACHE/'STATUS.json',dict(status='PAUSED_402' if isinstance(exc,funded.CreditPause) else 'BLOCKED',error_type=type(exc).__name__,bank='E79_ARM_B',cost=client.ledger.summary()));raise
        finally:p.payload,p.validate,privacy.check_wire,io.digest=saved

def run():
    import sys
    from .transport217c2_e79b import installed
    with installed(sys.modules[__name__]):execute()
    # The original owner analysis consumes this exact terminal bank. Copy only
    # after the wrapper has finalized its bounded-transport audit and seal.
    seal=CACHE/'judgments/JUDGMENT_SEAL.json';core.verify(seal,sha(seal))
    require(read(seal)['transport217c2_finalized'] is True,'bounded transport finalized')
    target=OWNER/'judge'
    require(not target.exists(),'owner judgments already exist; verify, never overwrite')
    shutil.copytree(seal.parent,target);core.verify(target/'JUDGMENT_SEAL.json',sha(seal))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--spec',default=str(OWNER/'SPEC.json'));args=p.parse_args()
    if args.action=='prepare':print(json.dumps(prepare(args.spec),sort_keys=True))
    else:run()
