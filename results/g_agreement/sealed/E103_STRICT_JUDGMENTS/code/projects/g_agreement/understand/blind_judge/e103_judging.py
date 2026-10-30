"""E103 one frozen claim/eight-continuation prompt per call, registered USD5."""
import argparse,hashlib,json,os,re,shutil,subprocess,runpy,time
from functools import lru_cache
from decimal import Decimal
from pathlib import Path
from . import funded_queue as funded
from .run import ROOT,payload
from .dispatch_lock import dispatch_lock
from .e99_channel import validate_wire_privacy
from .operational217 import audit_response
from .parallel_funded import patch_api
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
HERE=ROOT/'results/g_agreement/understand/blind_judge/e103_bank'
SHARED=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue')
funded.CACHE=SHARED
CACHE=SHARED/'E103'
CAP=Decimal('5')


def sources():
    for n,h in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'E103 source pin '+n)


def parser(text):
    require(isinstance(text,str),'text yes/no response')
    value=text.strip().casefold();require(value in ('yes','no'),'frozen yes/no schema')
    return value


def wire(item,p):
    require(set(item)=={'id','prompt'} and re.fullmatch('[a-f0-9]{32}',item['id']) and isinstance(item['prompt'],str),'opaque id and frozen prompt only')
    value=payload([], '', 'E56',p);value.pop('response_format')
    value['messages']=[dict(role='user',content=item['prompt'])]
    return value


@lru_cache(maxsize=1)
def frozen_prompt():
    return runpy.run_path(str(ROOT/'results/g_agreement/understand/e103/judge103.py'))


def privacy_prompt(item,w,original_check):
    require(w['messages']==[dict(role='user',content=item['prompt'])],'unchanged singleton prompt')
    frozen=frozen_prompt();prefix=frozen['QUESTION']+'\n\n'
    require(item['prompt'].startswith(prefix),'frozen E103 question')
    decoded=json.loads(item['prompt'][len(prefix):])
    require(set(decoded)=={'claim','continuations'} and frozen['render'](decoded['claim'],decoded['continuations'])==item['prompt'],'exact frozen render roundtrip')
    # Scan actual string values, not json.dumps escape syntax. A colon followed
    # by an escaped newline (s:\n) is not a Windows path. Real paths still fail.
    for text in [frozen['QUESTION'],decoded['claim'],*decoded['continuations']]:
        original_check('extract',[dict(id=item['id'],readout=text)],w)


def packet():
    receipt=ROOT/'results/g_agreement/understand/e103/I5_JUDGE_PACKET_CPU_RECEIPT.json'
    # Owner receipt and its code were committed before any judging.
    seal_path=ROOT/'results/g_agreement/understand/e103/I5_JUDGE_PACKET_CPU_SEAL.json'
    require(sha(seal_path)==read(HERE/'INPUTS.json')['cpu_packet_seal_sha256'],'owner CPU seal identity')
    owner=read(seal_path)
    # I-5 uses repository-relative member names in this seal.
    for name,digest in owner['files'].items():
        member=(ROOT/name).resolve();require(member.is_relative_to(ROOT.resolve()) and sha(member)==digest,'owner sealed repository member')
    require(str(receipt.relative_to(ROOT)) in owner['files'],'sealed owner receipt')
    r=read(receipt);require(r['experiment']=='E103' and r['registered_judge_cap_usd']==5 and r['calls']==1564 and r['claims']==782 and r['exact8_raw_per_call'] is True,'complete frozen E103 packet')
    require(sha(ROOT/'results/g_agreement/understand/e103/judge103.py')==r['frozen_prompt_source_sha256'],'frozen W-text renderer/parser')
    src=Path(r['private_directory'])/'REQUESTS.PRIVATE.json';require(sha(src)==r['files'][src.name],'exact rendered requests')
    xs=read(src);require(len(xs)==1564 and len({x['id'] for x in xs})==1564,'all1564 unique calls')
    return xs,sha(receipt)


def preflight():
    sources();xs,digest=packet();route,(api,privacy,p,io)=funded.route_api()
    bounds=[];blocked=[]
    for x in xs:
        w=wire(x,p)
        try:privacy_prompt(x,w,privacy.check_wire)
        except ValueError:blocked.append(x['id'])
        bounds.append(api.upper(w))
    # Reservations are sequential: actual settled plus next request upper bound
    # must fit USD5. Sum of every call's output-cap bound is NOT a prepaid charge.
    return dict(bank='E103',status='BLOCKED_EXACT_PROMPT_PRIVACY' if blocked else 'READY',blocked_opaque_ids=blocked,records=len(xs),cap_usd='5',packet_receipt_sha256=digest,source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),cpu_packet_seal_sha256=read(HERE/'INPUTS.json')['cpu_packet_seal_sha256'],max_single_reservation_usd=str(max(bounds)),sum_initial_output_cap_bounds_usd=str(sum(bounds,Decimal(0))),all_prompts_unchanged=True,privacy_static_pass=not blocked,registered_one_call_per_claim_arm=True,paid_calls=0)


def budget(r,a):
    require(r.get('issuer') in ('integrator','W-internals-B') and r.get('verified') is True and r.get('bank')=='E103' and r.get('reservation_included') is True,'posted bank admission')
    cap=Decimal(str(r['allocation_usd']));total=Decimal(str(r['actual_plus_open_caps_usd']))
    require(cap.is_finite() and total.is_finite() and 0<cap<=CAP and cap<=total<=1000,'registered cap/global actual plus open caps')
    require(r['packet_receipt_sha256']==a['packet_receipt_sha256'] and r['source_seal_sha256']==a['source_seal_sha256'],'admission exact packet/source')
    return cap


def run(receipt):
    a=preflight();require(a['privacy_static_pass'],'frozen prompt privacy block; no sends/redaction/drop without owner resolution')
    admission=read(receipt);cap=budget(admission,a)
    require(not (funded.CACHE/'PAUSED_402.json').exists(),'all banks paused HTTP402')
    xs,_=packet();route,(api,privacy,p,io)=funded.route_api();api.CAP=cap
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'credential unavailable')
    CACHE.mkdir(parents=True,exist_ok=True)
    with dispatch_lock(CACHE/'DISPATCH.lock'):
        job=CACHE/'judgments';require(not (job/'JUDGMENT_SEAL.json').exists(),'already terminal; no replay')
        ledger=CACHE/'ledger';ledger.mkdir(exist_ok=True);job.mkdir(exist_ok=True)
        io.CACHE=ledger/'route';io.CACHE.mkdir(exist_ok=True)
        require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'account privacy proof')
        shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
        routes=privacy.check_route(key);saved=(p.payload,p.validate,privacy.check_wire,io.digest)
        original_check=privacy.check_wire
        def privacy_gate(stage,batch,w,unused=None):
            require(len(batch)==1 and w==wire(batch[0],p),'unchanged singleton frozen prompt')
            privacy_prompt(batch[0],w,original_check)
        p.payload=lambda stage,batch,unused=None:wire(batch[0],p)
        p.validate=lambda stage,value,batch,unused=None:parser(value)
        privacy.check_wire=privacy_gate
        patch_api(api,io,'E103');client=api.Client(ledger,key)
        book,done=client.ledger.totals();require(set(book)==done,'unresolved reservation: reconcile through Ledger before resume')
        write(CACHE/'ADMISSION.json',dict(a,integrator=admission))
        write(CACHE/'STATUS.json',dict(bank='E103',status='RUNNING'))
        terminal=[];audits=[]
        try:
            for x in xs:
                require(time.time()<1793336400,'Guiv standing authorization expired Fri30Oct06CET')
                require(not (funded.CACHE/'PAUSED_402.json').exists(),'all banks paused HTTP402')
                stage='E103_yesno';prefix=stage+':'+a['packet_receipt_sha256']+':'
                io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
                result=client.one(stage,[x]);rp=ledger/stage/(result['id']+'.response.json')
                require(rp.exists(),'unsent/budget/unresolved stop; no guessed result')
                response=read(rp);funded.credit_gate(response,rp,'E103',stage,result['id'])
                require(not client.latch.is_set(),'transport failure; stop bank')
                audit=audit_response(response,p)
                require(result['id'] in client.ledger.totals()[1],'actual cost must settle through Ledger')
                content=response['response']['choices'][0]['message'].get('content')
                reason='CHARGED_LENGTH' if audit.get('terminal_unparseable') else None
                if reason:normalized='unparseable'
                else:
                    try:normalized=parser(content)
                    except ValueError:normalized='unparseable';reason='FROZEN_YES_NO_PARSE'
                terminal.append(dict(id=x['id'],response=normalized,raw_response=content,status='UNPARSEABLE' if reason else 'KEPT',reason=reason,attempts=0,request_id=result['id'],response_sha256=sha(rp)))
                audits.append(dict(audit,request_id=result['id'],response_sha256=sha(rp)))
                write(job/'LIVE_PROGRESS.json',dict(bank='E103',records=len(terminal),cost=client.ledger.summary()))
            write(job/'RESPONSES.json',terminal)
            write(job/'ROUTE_AUDIT.json',dict(routes=routes,requests=audits,privacy_proof_sha256=sha(route['privacy_proof']),inventory_sha256=sha(io.CACHE/'last_zdr_route_inventory.json')))
            write(job/'COUNTS.json',dict(records=len(terminal),unparseable=sum(x['status']=='UNPARSEABLE' for x in terminal),cost=client.ledger.summary()))
            write(job/'ADMISSION.json',read(CACHE/'ADMISSION.json'))
            write(job/'JUDGMENT_SEAL.json',dict(bank='E103',route_verified=bool(routes) and len(audits)==1564,redaction_audit_complete=True,redacted_opaque_ids=[],all_prompts_unchanged=True,packet_receipt_sha256=a['packet_receipt_sha256'],source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),files={f.name:sha(f) for f in job.iterdir() if f.is_file() and f.name!='JUDGMENT_SEAL.json'}))
            write(CACHE/'STATUS.json',dict(bank='E103',status='COMPLETE',cost=client.ledger.summary()))
        except Exception as exc:
            write(CACHE/'STATUS.json',dict(bank='E103',status='PAUSED_402' if (funded.CACHE/'PAUSED_402.json').exists() else 'BLOCKED',error_type=type(exc).__name__,cost=client.ledger.summary()));raise
        finally:p.payload,p.validate,privacy.check_wire,io.digest=saved

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['preflight','run']);p.add_argument('--admission');a=p.parse_args()
    if a.action=='preflight':print(json.dumps(preflight(),sort_keys=True))
    else:require(bool(a.admission),'posted admission path');run(a.admission)
