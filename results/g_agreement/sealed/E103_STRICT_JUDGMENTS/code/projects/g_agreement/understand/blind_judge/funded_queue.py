"""Funded E87 grouped/E100 queue; frozen E56 route; account-credit stop latch."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
from collections import Counter,defaultdict
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
from .run import ROOT,route_modules
from . import e87
from .later_runner import channel_payload,classify,judge
from .judgment_adapter402 import render_record,adapt_grid
from .privacy79 import redact,check_decoded
from .rubric202 import original_ids
from .dispatch_lock import dispatch_lock
from .wmech2_channel import response_audit
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

HERE=ROOT/'results/g_agreement/understand/blind_judge/funded_queue'
CACHE=ROOT/'cache/g_agreement/understand/funded_queue'
OLD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-blindspot-internals/cache/g_agreement/understand/blind_judge')
GLOBAL_RECEIPT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i2/results/g_agreement/i2/E81_CAP33_GLOBAL_JUDGING_ADMISSION.json')
class CreditPause(RuntimeError):pass

def credit_gate(response,path,bank,stage,rid):
    if response['http_status']==402:
        write(CACHE/'PAUSED_402.json',dict(bank=bank,stage=stage,request_id=rid,response_sha256=sha(path),reason='HTTP402_ACCOUNT_CREDITS',retry=False))
        raise CreditPause('HTTP402_ACCOUNT_CREDITS')

def source_gate():
    s=read(HERE/'SOURCE_SEAL.json')
    for name,h in s['files'].items():require(sha(ROOT/name)==h,'source pin '+name)

def sealed(p,h):
    # W-mech outputs inventory nested relative paths; standard verifier accepts them.
    return verify(Path(p),h)

def prepare_e87(cfg):
    out=CACHE/'E87';out.mkdir(parents=True,exist_ok=True)
    if (out/'PACKET_SEAL.json').exists():
        sealed(out/'PACKET_SEAL.json',sha(out/'PACKET_SEAL.json'));return
    audit=read(ROOT/'results/g_agreement/understand/e87/INPUT_AUDIT.json')
    require(sha(ROOT/'results/g_agreement/understand/e87/INPUT_AUDIT.json')==cfg['E87_audit_sha256'],'registered roster')
    meta={}
    for bank,s in audit['sources'].items():
        require(sha(s['path'])==s['sha256'],'frozen bank metadata');meta[bank]=read(s['path'])
    packet=[];joins=[];sources=[];counts=Counter()
    for entry,row in zip(cfg['E87'],audit['rows']):
        sp=Path(entry['input']);inp=sealed(sp,entry['input_sha256'])
        op=Path(entry['output']);output=sealed(op,entry['output_sha256'])
        require(output['status']=='COMPLETE' and output['input_seal_sha256']==entry['input_sha256'],'final complete shard')
        items=read(sp.parent/'items.json');records=meta[row['bank']]
        chosen=[x for x in records if x['feature']==row['feature'] and x['split']=='test'][:30]
        require(len(chosen)==len(items)==30 and [x['ids'] for x in chosen]==[x['ids'] for x in items],'first30 frozen bank order')
        by={x['id']:(x,m) for x,m in zip(items,chosen)};groups=defaultdict(list)
        for name in sorted(output['files']):
            if not name.startswith('jobs/') or name.endswith('STAGE_SEAL.json'):continue
            value=read(op.parent/name)
            for x in value if isinstance(value,list) else [value]:
                if 'unit_id' not in x:continue
                require(x['unit_id'] in by and x['arm'] in ('real','placebo'),'sealed source identity')
                groups[x['unit_id'],x['reader'],x['arm'],x['layer']].append(x)
        for (uid,reader,arm,layer),rs in sorted(groups.items()):
            item,m=by[uid];limit=8 if reader=='nla' else 16;n=min(limit,len(item['ids']))
            require(layer==42 if reader=='nla' else layer in e87.ORACLE_LAYERS,'native layer')
            ordered=sorted(rs,key=lambda x:x['position_offset'])
            expected=list(range(1-n,1));require([x['position_offset'] for x in ordered]==expected,'complete ragged chronological positions')
            require(all(x['global_index']==item['global_index'] and x['position']==item['read_index']+x['position_offset'] for x in rs),'registered read indices')
            values={str(y):sorted({x['value'] for x in records if x['feature']==row['feature'] and x['label']==y}) for y in (1,0)}
            require(all(len(v)==1 for v in values.values()),'unique registered row values')
            oid=hashlib.sha256(f'E87_GROUP:{uid}:{reader}:{arm}:{layer}'.encode()).hexdigest()[:32]
            packet.append(dict(id=oid,property=row['feature'],values=dict(A=values['1'][0],B=values['0'][0]),positions=[dict(offset=x['position_offset'],readout=x['text']) for x in ordered]))
            joins.append(dict(id=oid,source_item_id=m['id'],public_item_id=uid,row=row['feature'],reader=reader,arm=arm,layer=layer,true_label=m['label'],target='A' if m['label']==1 else 'B',global_index=item['global_index']))
            counts['nla' if reader=='nla' else 'placebo' if arm=='placebo' else 'oracle']+=1
        require(len(groups)==450,'30 × (7 real +7 placebo +1 NLA)')
        sources.append(entry)
    e87.validate_source(packet)
    require(len(packet)==4500 and dict(counts)==e87.EXPECTED_GROUPS,'complete4500 grouped grid')
    require(sum(len(x['positions']) for x in packet)==67920,'exact67920 readouts')
    write(out/'GROUPED_PACKET.json',packet);write(out/'PRIVATE_JOIN.json',joins);(out/'PRIVATE_JOIN.json').chmod(0o600)
    write(out/'ORIGINAL_IDS.json',original_ids([x['id'] for x in packet],'E87'))
    write(out/'PACKET_SEAL.json',dict(experiment='E87',n=4500,n_readouts=67920,group_counts=dict(counts),authority='47cf57c2',sources=sources,rubric_sha256=sha(e87.RUBRIC),files={n:sha(out/n) for n in ('GROUPED_PACKET.json','PRIVATE_JOIN.json','ORIGINAL_IDS.json')}))

def prepare_e100(cfg):
    out=CACHE/'E100';out.mkdir(parents=True,exist_ok=True)
    if (out/'blind/BLIND_SEAL.json').exists():
        sealed(out/'blind/BLIND_SEAL.json',sha(out/'blind/BLIND_SEAL.json'));return
    s=dict(cfg['E100'],blind=str(out/'blind'),private=str(out/'PRIVATE.json'),judgments=str(out/'judgments'),analysis=str(out/'analysis_once'))
    write(out/'SPEC.json',s)
    subprocess.run([os.sys.executable,str(ROOT/'projects/g_agreement/e100_analysis/adapter.py'),'export','--spec',str(out/'SPEC.json')],cwd=ROOT,check=True)

def load_bank(bank,protocol):
    out=CACHE/bank
    if bank=='E87':
        raw=read(out/'GROUPED_PACKET.json');rubric=e87.RUBRIC.read_text()
        groups=[dict(id=x['id'],rubric=render_record(dict(id=x['id'],property=x['property'],values=x['values'],readout=''),rubric)['rubric'],positions=x['positions']) for x in raw]
        items,audit=e87.redact_groups(groups);old_ids=set(read(out/'ORIGINAL_IDS.json'))
        original=[dict(x,rubric=x['rubric'].replace(rubric,e87.ORIGINAL.read_text(),1)) for x in items if x['id'] in old_ids]
        channels=[('main',items,rubric),('original',original,e87.ORIGINAL.read_text())]
        wire=lambda batch,r:e87.wire(batch,protocol,r)
    else:
        raw=read(out/'blind/JUDGE_PACKET.json');rubric=(out/'blind/RUBRIC.md').read_text()
        rendered=[render_record(x,rubric) for x in raw];require(rendered==read(out/'blind/WIRE_PACKET.json'),'frozen E100 rendering')
        items,audit=redact(rendered,bank,addresses=True);channels=[('main',items,rubric)]
        wire=lambda batch,r:channel_payload(batch,r,'E56',protocol)
    return channels,audit,wire

def upper_plan(bank,protocol,api):
    channels,audit,wire=load_bank(bank,protocol);bound=Decimal(0);n=0
    for _,items,rubric in channels:
        step=1 if bank=='E87' else 4
        for i in range(0,len(items),step):bound+=api.upper(wire(items[i:i+step],rubric));n+=1
    return dict(bank=bank,initial_requests=n,initial_upper_usd=str(bound),redacted_positions_or_records=audit['redacted_records'])

def route_api():
    route=read(ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    for name in ('api','privacy','protocol','io'):
        p=str(Path(route['e10_source'])/(name+'.py'));require(sha(p)==route['files'][p],'external E56 source pin')
    return route,route_modules(route)

def prepare():
    source_gate();CACHE.mkdir(parents=True,exist_ok=True);cfg=read(HERE/'BANK_INPUTS.json')
    prepare_e87(cfg);prepare_e100(cfg)
    _,(api,privacy,p,io)=route_api();plan=[upper_plan(b,p,api) for b in ('E87','E100')]
    receipt=read(GLOBAL_RECEIPT);require(Decimal(receipt['conservative_global_exposure_usd'])<=500,'registered global500')
    require(receipt['retained_envelope_includes_I4_active100_and_Q_E76_E88_full100_and_CORE_future'] is True,'E87/E100 already included in full programme envelope')
    caps=dict(E87=str(Decimal(plan[0]['initial_upper_usd']).to_integral_value(rounding=ROUND_CEILING)),E100='30')
    require(Decimal(plan[1]['initial_upper_usd'])<=30,'E100 firstpass within30')
    v=dict(status='PREPARED_NO_CALLS',banks=plan,caps=caps,global_receipt=str(GLOBAL_RECEIPT),global_receipt_sha256=sha(GLOBAL_RECEIPT),global_exposure_usd=receipt['conservative_global_exposure_usd'],authority='§200 rounded preflight and §208 USD30; user top-up launch',source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),inputs_sha256=sha(HERE/'BANK_INPUTS.json'))
    write(CACHE/'GLOBAL_EVIDENCE.json',receipt)
    write(CACHE/'ADMISSION.json',v);return v

def q_committed(api):
    # Conservatively include all prior Q ledgers, not just the later banks. Duplicate snapshots excluded.
    total=Decimal(0);seen=set()
    for p in OLD.rglob('ledger.jsonl'):
        if 'terminal' in p.parts:continue
        h=sha(p)
        if h in seen:continue
        seen.add(h);book,_=api.Ledger(p).totals();total+=sum(book.values(),Decimal(0))
    p=CACHE/'E87/ledger/ledger.jsonl'
    if p.exists():total+=sum(api.Ledger(p).totals()[0].values(),Decimal(0))
    return total

def execute_bank(bank,admission,key):
    route,(api,privacy,protocol,io)=route_api();api.CAP=Decimal(admission['caps'][bank])
    channels,redaction,wire=load_bank(bank,protocol);base=CACHE/bank;ledger=base/'ledger';ledger.mkdir(exist_ok=True)
    saved=(protocol.payload,protocol.validate,privacy.check_wire,io.digest)
    sealpath=base/('PACKET_SEAL.json' if bank=='E87' else 'blind/BLIND_SEAL.json');packet_sha=sha(sealpath)
    with dispatch_lock(ledger/'DISPATCH.lock'):
        job=base/'judgments';job.mkdir(exist_ok=True)
        if (job/'JUDGMENT_SEAL.json').exists():return
        io.CACHE=ledger/'route';io.CACHE.mkdir(exist_ok=True)
        require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'account privacy proof')
        shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json');routes=privacy.check_route(key)
        client=api.Client(ledger,key);book,done=client.ledger.totals();require(set(book)==done,'unresolved reservation: reconcile before resume')
        write(job/'START.json',dict(bank=bank,packet_seal_sha256=packet_sha,admission_sha256=sha(CACHE/'ADMISSION.json')))
        write(job/'PATH_REDACTION_AUDIT.json',redaction);audits=[]
        for channel,items,rubric in channels:
            classifier=e87.classify if bank=='E87' else classify
            protocol.payload=lambda stage,batch,unused=None:wire(batch,rubric)
            protocol.validate=lambda stage,response,batch,unused=None:classifier(batch,response)
            privacy.check_wire=lambda stage,batch,body,unused=None:check_decoded(saved[2],batch,body)
            for item in items:privacy.check_wire('',[item],wire([item],rubric))
            def send(batch,attempt):
                groups=[[x] for x in batch] if bank=='E87' else [batch];result_rows=[]
                for group in groups:
                    require(not (CACHE/'PAUSED_402.json').exists(),'queue paused402')
                    stage=f'{bank}_{channel}_attempt{attempt}';prefix=stage+':'+packet_sha+':'
                    io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
                    with dispatch_lock(OLD/'FUNDED_QUEUE_GLOBAL.lock'):
                        if bank=='E87':require(q_committed(api)+api.upper(wire(group,rubric))<=100,'Q shared100 actual+unresolved cap')
                        result=client.one(stage,group)
                    rp=ledger/stage/(result['id']+'.response.json')
                    require(rp.exists(),'unresolved/no response: stop, no resend')
                    response=read(rp)
                    credit_gate(response,rp,bank,stage,result['id'])
                    require(not client.latch.is_set(),'transport latch; no resend')
                    audit=response_audit(response,protocol);audit.update(request_id=result['id'],response_sha256=sha(rp))
                    require(result['id'] in client.ledger.totals()[1],'known cost settled')
                    audits.append(audit)
                    if len(audits)==1 or len(audits)%25==0:
                        write(job/'LIVE_PROGRESS.json',dict(bank=bank,channel=channel,verified_requests=len(audits),cost=client.ledger.summary()))
                    if result['status']=='OK':result_rows.extend(result['value'])
                    else:
                        try:json.loads(response['response']['choices'][0]['message']['content'])
                        except (ValueError,TypeError):result_rows.extend(classifier(group,{}));continue
                        raise RuntimeError('unexpected transport failure')
                return result_rows
            terminal=judge(items,send);write(job/(channel+'_TERMINAL.json'),terminal)
            if bank=='E100':flat,_=adapt_grid(terminal,items)
            else:flat=[x['code'] if x['status']=='KEPT' else dict(id=x['id'],category='UNPARSEABLE',values=[],evidence='',first_position=None) for x in terminal]
            write(job/('JUDGMENTS.json' if channel=='main' else 'ORIGINAL_JUDGMENTS.json'),flat)
            write(job/(channel+'_JUDGE_COPY.json'),items)
            write(job/'PROGRESS.json',dict(bank=bank,channel=channel,complete=len(terminal),cost=client.ledger.summary()))
        write(job/'ROUTE_AUDIT.json',dict(routes=routes,requests=audits,privacy_proof_sha256=sha(route['privacy_proof']),inventory_sha256=sha(io.CACHE/'last_zdr_route_inventory.json')))
        write(job/'COUNTS.json',dict(bank=bank,cost=client.ledger.summary()))
        redacted={x['id'][:32] for x in redaction['affected']}
        write(job/'JUDGMENT_SEAL.json',dict(bank=bank,blind_seal_sha256=packet_sha,route_verified=bool(routes) and bool(audits),redaction_audit_complete=True,redacted_opaque_ids=sorted(redacted),source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),files={p.name:sha(p) for p in job.iterdir() if p.is_file() and p.name!='JUDGMENT_SEAL.json'}))
        protocol.payload,protocol.validate,privacy.check_wire,io.digest=saved

def run():
    source_gate();a=read(CACHE/'ADMISSION.json')
    require(a['source_seal_sha256']==sha(HERE/'SOURCE_SEAL.json') and a['inputs_sha256']==sha(HERE/'BANK_INPUTS.json'),'unchanged admission/source')
    require(not (CACHE/'PAUSED_402.json').exists(),'explicit credit pause remains')
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'credential unavailable')
    with dispatch_lock(CACHE/'QUEUE.lock'):
        for bank in ('E87','E100'):
            write(CACHE/'QUEUE_STATUS.json',dict(status='RUNNING',bank=bank))
            try:execute_bank(bank,a,key)
            except Exception as exc:
                write(CACHE/'QUEUE_STATUS.json',dict(status='PAUSED_402' if isinstance(exc,CreditPause) else 'BLOCKED',bank=bank,error_type=type(exc).__name__));raise
        write(CACHE/'QUEUE_STATUS.json',dict(status='COMPLETE',banks=['E87','E100']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);a=p.parse_args()
    if a.action=='prepare':print(json.dumps(prepare(),sort_keys=True))
    else:run()
