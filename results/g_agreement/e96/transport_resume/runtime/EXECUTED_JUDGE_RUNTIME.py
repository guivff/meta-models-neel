"""E96 integrator-only E56-route judging; no label join or rule evaluation.

Preflight makes zero API calls. Actual dispatch requires a current sealed USD120
allocation within the global USD500 envelope. The existing E10 transport reserves
before each send and caches exact requests. Only schema failures get two retries;
proven uncharged429 rejections have the existing capped5/10/20/40s policy.
"""
import argparse,contextlib,datetime,hashlib,json,os,shutil,time
from decimal import Decimal
from pathlib import Path
from .reconstructor_check import digest,write
from .prepare_smoke_inputs import verify
from projects.g_agreement.understand.blind_judge.run import route_modules
from projects.g_agreement.understand.blind_judge.later_runner import channel_payload,classify,judge
from projects.g_agreement.understand.blind_judge.judgment_adapter402 import render_record,adapt_grid
from projects.g_agreement.understand.blind_judge.privacy79 import redact,check_decoded
from projects.g_agreement.understand.blind_judge.dispatch_lock import dispatch_lock
from projects.g_agreement.understand.blind_judge.rubric202 import amended,BASE
from projects.g_agreement.understand.blind_judge.wmech2_channel import response_audit
from projects.g_agreement.understand.blind_judge.e76_recovery import rejected_uncharged
from projects.g_agreement.readerbench.scoring import RUBRIC_HASHES

ROOT=Path(__file__).resolve().parents[3]
CAP=Decimal('120')


def allocation(path,packet_sha):
    d=json.loads(path.read_text())
    if d.get('issuer')!='I-4' or d.get('bank')!='E96' or d.get('packet_seal_sha256')!=packet_sha or not d.get('verified'):raise ValueError('integrator allocation binding')
    cap=Decimal(str(d['allocation_usd']));total=Decimal(str(d['global_judging_committed_including_e96_usd']))
    if not cap.is_finite() or not total.is_finite() or not 0<cap<=CAP or not cap<=total<=500:raise ValueError('registered120/500USD envelope')
    if not d.get('global_evidence') or not d.get('allocation_authority'):raise ValueError('budget provenance required')
    return cap


def run(packet,budget_receipt=None,preflight_only=False):
    verify(packet,'PACKET_SEAL.json');seal=json.loads((packet/'PACKET_SEAL.json').read_text());packet_sha=digest(packet/'PACKET_SEAL.json')
    for name,h in seal['code_files'].items():
        if digest(ROOT/name)!=h:raise ValueError('frozen judging implementation changed')
    if digest(BASE)!=RUBRIC_HASHES['E56']:raise ValueError('original172 rubric changed')
    if seal['experiment']!='E96' or seal['status']!='REGEX_SCORED_UNRESOLVED_PACKET_FROZEN_NO_API_CALLS':raise ValueError('E96 packet custody')
    original=json.loads((packet/'JUDGE_PACKET.json').read_text());old=set(json.loads((packet/'OLD_RUBRIC_IDS.json').read_text()))
    if len(original)!=seal['judge_unresolved'] or len(old)!=seal['old_rubric_unresolved'] or not old<={x['id'] for x in original}:raise ValueError('frozen unresolved grid')
    current=amended().decode();base=BASE.read_text();items=[render_record(x,current) for x in original]
    items,redaction=redact(items,'E96',addresses=True)
    old_items=[dict(x,rubric=x['rubric'].replace(current,base,1)) for x in items if x['id'] in old]
    route_path=ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json';route=json.loads(route_path.read_text())
    for name in ('api','privacy','protocol','io'):
        p=str(Path(route['e10_source'])/(name+'.py'))
        if digest(p)!=route['files'][p]:raise ValueError('E56 external source pin')
    api,privacy,protocol,io=route_modules(route)
    if protocol.MODEL!='google/gemini-3.1-flash-lite' or protocol.PROVIDER!='google-vertex/global':raise ValueError('registered route')
    saved=(protocol.payload,protocol.validate,privacy.check_wire,io.digest)
    def wire(batch,rubric):return channel_payload(batch,rubric,'E56',protocol)
    for group,rubric in [(items,current),(old_items,base)]:
        for start in range(0,len(group),4):check_decoded(saved[2],group[start:start+4],wire(group[start:start+4],rubric))
    bound=sum((api.upper(wire(group[i:i+4],rubric)) for group,rubric in [(items,current),(old_items,base)] for i in range(0,len(group),4)),Decimal(0))
    summary={'bank':'E96','packet_seal_sha256':packet_sha,'unresolved_records':len(items),'original_rubric_records':len(old_items),'first_pass_upper_usd':str(bound),'redacted_records':redaction['redacted_records'],'source_kind':'preflight; no API calls'}
    if bound>CAP:raise ValueError('initial pass exceeds120USD; no send')
    if preflight_only:return summary
    if budget_receipt is None:raise ValueError('current global allocation receipt required')
    cap=allocation(budget_receipt,packet_sha)
    if bound>cap:raise ValueError('whole initial pass exceeds allocation; no send')
    api.CAP=cap
    key=os.environ.get('OPENROUTER_API_KEY')
    if not key:raise ValueError('credential unavailable')
    ledger=ROOT/'cache/g_agreement/e96/judging_120';ledger.mkdir(parents=True,exist_ok=True)
    out=packet.parent/'judgments';out.mkdir(exist_ok=True)
    if (out/'JUDGMENT_SEAL.json').exists():raise ValueError('judgments already sealed')
    with dispatch_lock(ledger/'DISPATCH.lock'):
        io.CACHE=ledger/'route';io.CACHE.mkdir(exist_ok=True)
        if digest(route['privacy_proof'])!=route['privacy_proof_sha256']:raise ValueError('privacy proof pin')
        shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
        routes=privacy.check_route(key)
        privacy.check_wire=lambda stage,batch,w,unused=None:check_decoded(saved[2],batch,w)
        client=api.Client(ledger,key)
        book,done=client.ledger.totals()
        if set(book)!=done:raise ValueError('unsettled prior request; reconcile before resume')
        audits=[];first=None
        start_doc=dict(summary,allocation_receipt_sha256=digest(budget_receipt),route_seal_sha256=digest(route_path))
        if (out/'START.json').exists():
            if json.loads((out/'START.json').read_text())!=start_doc:raise ValueError('resume changed packet or allocation')
        else:write(out/'START.json',start_doc)
        write(out/'JUDGE_COPY.json',items);write(out/'PATH_REDACTION_AUDIT.json',redaction)
        try:
            for pass_name,group,rubric in [('current',items,current),('original',old_items,base)]:
                protocol.payload=lambda stage,batch,unused=None:wire(batch,rubric)
                protocol.validate=lambda stage,response,batch,unused=None:classify(batch,response,'E56')
                def identity(batch,attempt,retry=0):
                    prefix=f'E96:{packet_sha}:{pass_name}:{attempt}:{retry}:'
                    return hashlib.sha256((prefix+io.canonical(wire(batch,rubric))).encode()).hexdigest()
                known=set(client.ledger.totals()[0])
                remaining=sum((api.upper(wire(group[i:i+4],rubric)) for i in range(0,len(group),4) if identity(group[i:i+4],0) not in known),Decimal(0))
                if Decimal(client.ledger.summary()['committed_usd'])+remaining>cap:raise ValueError('remaining first pass exceeds allocation')
                def send(batch,attempt):
                    nonlocal first
                    for retry in range(5):
                        rid=identity(batch,attempt,retry);io.digest=lambda value,rid=rid:rid
                        stage=f'E96_{pass_name}_attempt{attempt}_transport{retry}'
                        result=client.one(stage,batch);rid=result['id'];response=ledger/stage/(rid+'.response.json');request=ledger/stage/(rid+'.request.json')
                        if not response.exists() or client.latch.is_set():raise RuntimeError('transport/budget/unresolved stop; no resend')
                        saved_response=json.loads(response.read_text())
                        if saved_response['http_status']==429:
                            rejected_uncharged(saved_response);book,done=client.ledger.totals()
                            if rid not in done:client.ledger.settle(rid,0)
                            write(ledger/stage/(rid+'.reconciliation.json'),{'request_id':rid,'reason':'proven uncharged429: no generation/id/choices; zero or absent usage','actual_usd':'0','request_sha256':digest(request),'response_sha256':digest(response)})
                            if retry==4:raise RuntimeError('bounded transport429 retries exhausted')
                            time.sleep((5,10,20,40)[retry]);continue
                        audit=response_audit(saved_response,protocol)
                        if json.loads(request.read_text())['wire']!=wire(batch,rubric):raise ValueError('sent wire differs from frozen payload')
                        if first is None:
                            first=datetime.datetime.fromtimestamp(response.stat().st_mtime,datetime.timezone.utc).isoformat();write(out/'FIRST_OUTPUT.json',{'first_output_utc':first,'source':'first actual judgment response mtime','response_sha256':digest(response)})
                        audits.append(dict(audit,request_id=rid,request_sha256=digest(request),response_sha256=digest(response),pass_name=pass_name))
                        if result['status']=='OK':return result['value']
                        try:json.loads(saved_response['response']['choices'][0]['message']['content'])
                        except (ValueError,TypeError):return classify(batch,{},'E56')
                        raise RuntimeError('unexpected transport failure; no scientific retry')
                terminal=judge(group,send);flat,attempts=adapt_grid(terminal,group)
                write(out/(pass_name+'_TERMINAL.json'),terminal);write(out/(pass_name+'_JUDGMENTS.json'),flat);write(out/(pass_name+'_ATTEMPTS.json'),attempts)
            write(out/'COST.json',client.ledger.summary());write(out/'ROUTE_AUDIT.json',{'routes':routes,'requests':audits,'privacy_proof_sha256':digest(route['privacy_proof'])})
            shutil.copyfile(ledger/'ledger.jsonl',out/'LEDGER_AT_END.jsonl')
            if (out/'BLOCKED.json').exists():(out/'BLOCKED.json').unlink()
            write(out/'JUDGMENT_SEAL.json',{'code_files':seal['code_files'],'bank':'E96','status':'TERMINAL_BLIND_GRID_NO_LABEL_JOIN','first_output_utc':first or 'unknown','first_output_source':'FIRST_OUTPUT.json; judgment response mtime','packet_seal_sha256':packet_sha,'route_verified':bool(routes),'redacted_opaque_ids':[r['id'] for r in redaction['affected']],'files':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='JUDGMENT_SEAL.json'}})
        except BaseException as exc:
            write(out/'BLOCKED.json',{'error_type':type(exc).__name__,'cost':client.ledger.summary(),'first_output_utc':first or 'unknown'});raise
        finally:protocol.payload,protocol.validate,privacy.check_wire,io.digest=saved
    return dict(summary,cost=client.ledger.summary())


def main():
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--budget-receipt',type=Path);p.add_argument('--preflight-only',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.packet,a.budget_receipt,a.preflight_only),indent=2))
if __name__=='__main__':main()
