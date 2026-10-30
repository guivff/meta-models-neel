"""W-mech2 frozen packets on E56. Integrator-only dispatch; no scientific joins."""
import argparse
import hashlib
import json
import os
import shutil
from decimal import Decimal
from pathlib import Path
from .run import ROOT, route_modules
from .later_runner import channel_payload, classify, judge
from .judgment_adapter402 import render_record, adapt_grid
from .privacy79 import redact, check_decoded
from .dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require, RUBRIC_HASHES

HERE=ROOT/'results/g_agreement/understand/blind_judge/wmech2_channel'
BANKS=('E79','E78','E70','E72','E63')
LEDGER_BASE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-blindspot-internals/cache/g_agreement/understand/blind_judge')

def sources():
    seal=read(HERE/'SOURCE_SEAL.json')
    for name,digest in seal['files'].items():require(sha(ROOT/name)==digest,'channel source changed')

def admission(bank):
    require(bank in BANKS,'supported packet')
    delivery=read(ROOT/'results/g_agreement/r/WMECH2_DELIVERY.json')
    entry=next(x for x in delivery['packets'] if x['experiment']==bank)
    config=ROOT/f'projects/g_agreement/understand/wmech2/{bank}.json'
    require(sha(config)==entry['spec_sha256'],'W-mech2 config binding')
    spec=read(config);packet=Path(entry['packet'])
    bs=verify(packet/('RESULT_SEAL.json' if bank=='E63' else 'BLIND_SEAL.json'),entry['seal_sha256'])
    require(bs['output_seal_sha256']==entry['output_seal_sha256'],'output custody')
    if bank=='E63':
        require(bs['job']=='E63_RP2' and bs['n']==400,'existing frozen R-P2 sample')
        require({'JUDGE_PACKET.json','JUDGE_RUBRIC.md'}<=set(bs['files']),'sealed D5 inputs')
        require(sha(packet/'JUDGE_RUBRIC.md')==RUBRIC_HASHES['D5'],'unchanged D5 rubric')
        rubric=(packet/'JUDGE_RUBRIC.md').read_text();items=read(packet/'JUDGE_PACKET.json')
        require(all(set(x)=={'id','property','values','readout'} and x['values']=={} and x['property']=='What this readout explicitly describes' for x in items),'frozen D5 metadata')
        items=[dict(id=x['id'],readout=x['readout']) for x in items]
        spec={'judgments':str(packet.parent/'judge_rp2')}
    else:
        require({'JUDGE_PACKET.json','WIRE_PACKET.json','RUBRIC.md'}<=set(bs['files']),'sealed public inputs')
        require(sha(packet/'RUBRIC.md')==RUBRIC_HASHES['E56'],'frozen E56 rubric')
        rubric=(packet/'RUBRIC.md').read_text()
        rows=read(packet/'JUDGE_PACKET.json');items=[render_record(x,rubric) for x in rows]
        require(items==read(packet/'WIRE_PACKET.json'),'unchanged W-mech2 wire rendering')
    require(len(items)==entry['records']==len({x['id'] for x in items}),'complete unique grid')
    items,audit=redact(items,bank,addresses=True)
    return entry,spec,items,rubric,audit

def terminal_grid(terminal,items,taxonomy):
    if taxonomy=='E56':return adapt_grid(terminal,items)
    require([x['id'] for x in terminal]==[x['id'] for x in items],'exact D5 terminal grid')
    flat=[];attempts=[]
    for t,item in zip(terminal,items):
        require(type(t['attempts']) is int and 0<=t['attempts']<=2,'bounded validation retries')
        if t['status']=='UNPARSEABLE':
            require(t['attempts']==2 and t['code'] is None,'exhausted D5 retries')
            flat.append(dict(id=t['id'],category='UNPARSEABLE',evidence=''))
        else:
            require(t['status']=='KEPT' and classify([item],dict(records=[t['code']]),'D5')[0]['status']=='KEPT','D5 code validation')
            flat.append(t['code'])
        attempts.append(dict(id=t['id'],status=t['status'],attempts=t['attempts']))
    return flat,attempts

def response_audit(saved,protocol):
    body=saved['response']
    require(saved['http_status']==200 and body.get('provider')==protocol.PROVIDER_NAME and
            body.get('model') in (protocol.MODEL,protocol.MODEL+'-001'),'actual response route')
    cost=Decimal(str(body.get('usage',{}).get('cost')))
    require(cost.is_finite() and cost>=0,'known finite charge')
    require(body['choices'][0].get('finish_reason')=='stop','completed response required')
    return dict(model=body['model'],provider=body['provider'],cost_usd=str(cost))

def budget(receipt,entry):
    require(receipt.get('issuer')=='integrator' and receipt.get('verified') is True and
            receipt.get('bank')==entry['experiment'] and receipt.get('packet_seal_sha256')==entry['seal_sha256'] and
            receipt.get('forecast_and_custody_verified') is True and receipt.get('reservation_included') is True,
            'integrator custody/forecast/allocation receipt')
    cap=Decimal(str(receipt['allocation_usd']));total=Decimal(str(receipt['global_judging_committed_including_reservation_usd']))
    require(cap.is_finite() and total.is_finite() and 0<cap<=total<=500,'allocation within global USD500')
    require(bool(receipt.get('allocation_authority')),'registered allocation authority')
    return cap

def run(bank,receipt_path=None,preflight=False):
    sources();entry,spec,items,rubric,redaction=admission(bank)
    route_path=ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json';route=read(route_path)
    # Verify before executing external source modules.
    for name in ('api','privacy','protocol','io'):
        path=str(Path(route['e10_source'])/(name+'.py'))
        require(sha(path)==route['files'][path],'E56 source pin')
    api,privacy,protocol,io=route_modules(route)
    require(protocol.MODEL=='google/gemini-3.1-flash-lite' and protocol.PROVIDER=='google-vertex/global','E56 route')
    original=(protocol.payload,protocol.validate,privacy.check_wire,io.digest)
    taxonomy='D5' if bank=='E63' else 'E56'
    def wire(batch):return channel_payload(batch,rubric,taxonomy,protocol)
    def check(stage,batch,payload,unused=None):check_decoded(original[2],batch,payload)
    batches=[items[i:i+4] for i in range(0,len(items),4)]
    for batch in batches:check('',batch,wire(batch))
    bound=sum((api.upper(wire(b)) for b in batches),Decimal(0))
    summary=dict(bank=bank,records=len(items),initial_requests=len(batches),initial_upper_usd=str(bound),
                 redacted_records=redaction['redacted_records'],packet_seal_sha256=entry['seal_sha256'])
    if preflight:return summary
    receipt=read(receipt_path);cap=budget(receipt,entry);api.CAP=cap
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'Integrator credential unavailable')
    # Fixed cross-checkout ledger location; no new namespace on retry.
    root=LEDGER_BASE/('wmech2_'+bank)
    out=Path(spec['judgments']);root.mkdir(parents=True,exist_ok=True)
    with dispatch_lock(root/'DISPATCH.lock'):
        require(not (out/'JUDGMENT_SEAL.json').exists(),'already terminal; no second run')
        io.CACHE=root/'route';io.CACHE.mkdir(exist_ok=True)
        require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'account privacy proof pin')
        shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
        routes=privacy.check_route(key) # actual read-only provider inventory; no key serialized
        protocol.payload=lambda stage,batch,unused=None:wire(batch)
        protocol.validate=lambda stage,response,batch,unused=None:classify(batch,response,taxonomy)
        privacy.check_wire=check
        client=api.Client(root,key);book,settled=client.ledger.totals()
        require(set(book)==settled,'unsettled request: reconcile through ledger before resume')
        def identity(batch,attempt):
            prefix=bank+':'+entry['seal_sha256']+':'+str(attempt)+':'
            return hashlib.sha256((prefix+io.canonical(wire(batch))).encode()).hexdigest()
        remaining=sum((api.upper(wire(b)) for b in batches if identity(b,0) not in book),Decimal(0))
        require(Decimal(client.ledger.summary()['committed_usd'])+remaining<=cap,'initial pass exceeds allocation')
        out.mkdir(parents=True,exist_ok=True)
        start=dict(summary,allocation_receipt_sha256=sha(receipt_path),route_seal_sha256=sha(route_path),source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'))
        if (out/'START.json').exists():require(read(out/'START.json')==start,'resume changed frozen inputs/allocation')
        else:write(out/'START.json',start)
        write(out/'JUDGE_COPY.json',items);write(out/'PATH_REDACTION_AUDIT.json',redaction)
        audits=[]
        def send(batch,attempt):
            prefix=bank+':'+entry['seal_sha256']+':'+str(attempt)+':'
            io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
            stage=bank+'_attempt'+str(attempt);result=client.one(stage,batch)
            response=root/stage/(result['id']+'.response.json');request=root/stage/(result['id']+'.request.json')
            require(response.exists() and not client.latch.is_set(),'transport/unresolved/budget stop; no resend')
            require(read(request)['wire']==wire(batch),'actual sent wire matches frozen payload')
            saved=read(response);audit=response_audit(saved,protocol)
            require(result['id'] in client.ledger.totals()[1],'actual cost settled')
            audits.append(dict(audit,request_id=result['id'],request_path=str(request),request_sha256=sha(request),
                               response_path=str(response),response_sha256=sha(response)))
            if result['status']=='OK':return result['value']
            try:json.loads(saved['response']['choices'][0]['message']['content'])
            except (ValueError,TypeError):return classify(batch,{},taxonomy)
            raise RuntimeError('unexpected transport failure; no validation retry')
        try:
            terminal=judge(items,send);flat,attempts=terminal_grid(terminal,items,taxonomy)
            write(out/'TERMINAL.json',terminal)
            write(out/'JUDGMENTS.json',flat);write(out/'ATTEMPTS.json',attempts)
            write(out/'ROUTE_AUDIT.json',dict(routes=routes,requests=audits,
                inventory_sha256=sha(io.CACHE/'last_zdr_route_inventory.json'),privacy_proof_sha256=sha(route['privacy_proof'])))
            shutil.copyfile(io.CACHE/'last_zdr_route_inventory.json',out/'ZDR_INVENTORY.json')
            shutil.copyfile(route['privacy_proof'],out/'PRIVACY_PROOF.json')
            write(out/'COUNTS.json',dict(records=len(flat),unparseable=sum(x['category']=='UNPARSEABLE' for x in flat),cost=client.ledger.summary()))
            if (out/'BLOCKED.json').exists():(out/'BLOCKED.json').unlink()
            write(out/'JUDGMENT_SEAL.json',dict(bank=bank,blind_seal_sha256=entry['seal_sha256'],
                route_verified=bool(routes) and bool(audits),redaction_audit_complete=True,
                redacted_opaque_ids=[x['id'] for x in redaction['affected']],
                route_seal_sha256=sha(route_path),source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),
                unparseable_policy='missing; excluded from scientific denominator',
                files={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='JUDGMENT_SEAL.json'}))
        except Exception as exc:
            write(out/'BLOCKED.json',dict(error_type=type(exc).__name__,cost=client.ledger.summary()));raise
        finally:protocol.payload,protocol.validate,privacy.check_wire,io.digest=original
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bank',choices=BANKS,required=True)
    p.add_argument('--receipt',type=Path);p.add_argument('--preflight-only',action='store_true');a=p.parse_args()
    require(a.preflight_only or a.receipt is not None,'Integrator receipt required')
    print(json.dumps(run(a.bank,a.receipt,a.preflight_only),sort_keys=True))

if __name__=='__main__':main()
