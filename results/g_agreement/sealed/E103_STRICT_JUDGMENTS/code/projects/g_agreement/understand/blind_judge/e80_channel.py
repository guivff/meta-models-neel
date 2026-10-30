"""E80/E80c: unchanged W-text family renderer on the existing E56 transport."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from decimal import Decimal
from pathlib import Path
import ast
from types import SimpleNamespace
from .run import route_modules, payload
from .privacy79 import redact, strings
from .dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read, sha, verify, write, seal_output
from projects.g_agreement.readerbench.scoring import require

ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'results/g_agreement/understand/blind_judge/e80_channel'
CAP=Decimal('50')


def load_renderers(seal):
    source=Path(seal['wtext_source'])
    for name,digest in seal['renderer_files'].items():
        require(sha(source/name)==digest, 'frozen W-text source changed')
    def module(name):
        spec=importlib.util.spec_from_file_location('_e80_frozen_'+name,source/(name+'.py'))
        obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
    tree=ast.parse((source/'export80.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='judge_messages')
    namespace={'json':json}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source/'export80.py'),'exec'),namespace)
    return SimpleNamespace(judge_messages=namespace['judge_messages']),module('regex80')


def wire_for(packet, sample, protocol, renderer):
    require(packet['headline_scorer']!='regex' and packet['mode'] in ('basic','chain'), 'paid family only')
    calls=renderer.judge_messages(packet,sample)
    require(len(calls)==1, 'exactly one frozen call for one readout')
    call=calls[0]
    wire=payload([], '', 'E56', protocol)
    # Replace all E56 rubric prose and schema; preserve family text byte-for-byte.
    wire['messages']=[{'role':'system','content':call['system']},{'role':'user','content':call['user']}]
    wire['response_format']={'type':'json_schema','json_schema':packet['schema']}
    require(wire['model']=='google/gemini-3.1-flash-lite' and protocol.PROVIDER=='google-vertex/global','exact authorized E56 route')
    return wire


def valid_response(value,packet):
    def validate(v,s):
        require(set(s)<={'type','additionalProperties','required','properties','items','enum','description'},'unsupported frozen schema keyword')
        kind=s['type']
        require(kind in ('object','array','boolean','integer','string'),'supported frozen schema type')
        if kind=='object':
            require(type(v) is dict and set(s['required'])<=set(v),'required schema fields')
            require(s.get('additionalProperties') is False and set(v)<=set(s['properties']),'strict schema fields')
            for k,x in v.items():validate(x,s['properties'][k])
        elif kind=='array':
            require(type(v) is list,'array schema')
            for x in v:validate(x,s['items'])
        else:require(type(v) is {'boolean':bool,'integer':int,'string':str}[kind],'schema scalar type')
        if 'enum' in s:require(v in s['enum'],'schema enum')
    validate(value,packet['schema']['schema'])
    return value


def prepare(spec,seal):
    require(spec['bank'] in ('E80','E80c'), 'E80/E80c only')
    require(sha(spec['custody_receipt'])==spec['custody_receipt_sha256'],'custody receipt pin')
    receipt=read(spec['custody_receipt'])
    require(receipt.get('issuer')=='integrator' and receipt.get('verified') is True and receipt.get('bank')==spec['bank'] and receipt.get('e80b_forecast_precedes_readers_opened') is True,'integrator custody and E80b ordering')
    require(receipt.get('source_seals'), 'sealed reader output custody')
    for source in receipt['source_seals']:verify(source['path'],source['sha256'])
    require(sha(spec['readouts'])==receipt['readouts_sha256']==spec['readouts_sha256'],'readout export pin')
    require(sha(spec['judge_packets'])==seal['judge_packets_sha256'],'original frozen W-text judge packets')
    packets={x['id']:x for x in read(spec['judge_packets'])}
    require(len(packets)==518,'complete frozen item grid')
    items=read(spec['readouts'])
    expected=1036 if spec['bank']=='E80' else 3108
    require(len(items)==expected==receipt['n'] and len({x['id'] for x in items})==len(items),'complete unique bank grid')
    for x in items:
        require(set(x)=={'id','item_id','readout'} and x['item_id'] in packets and isinstance(x['readout'],str),'CPU join fields only')
        require(len(x['id'])==32 and all(c in '0123456789abcdef' for c in x['id']),'opaque record ID')
    counts={k:sum(x['item_id']==k for x in items) for k in packets}
    require(set(counts.values())=={2 if spec['bank']=='E80' else 6},'two readers per item, three E80c ablations; none reused from E80')
    items,audit=redact(items,spec['bank'],addresses=True)
    renderer,regex=load_renderers(seal)
    return items,packets,audit,renderer,regex


def run(spec,preflight=False):
    seal=read(HERE/'ROUTE_SEAL.json')
    for path,digest in seal['files'].items():require(sha(ROOT/path)==digest,'channel source pin')
    items,packets,audit,renderer,regex=prepare(spec,seal)
    route=read(seal['e56_route'])
    require(sha(seal['e56_route'])==seal['e56_route_sha256'],'existing E56 route pin')
    api,privacy,protocol,io=route_modules(route);api.CAP=CAP
    original_check=privacy.check_wire
    wires={x['id']:wire_for(packets[x['item_id']],x['readout'],protocol,renderer) for x in items if packets[x['item_id']]['headline_scorer']!='regex'}
    for wire in wires.values():
        for value in strings(wire['messages']):original_check('extract',[{'id':'opaque','readout':value}],wire)
    worst=sum((api.upper(w) for w in wires.values()),Decimal(0))
    require(worst<=CAP,'whole initial pass must fit shared USD50 ceiling')
    if preflight:
        print(json.dumps(dict(bank=spec['bank'],records=len(items),paid_calls=len(wires),cpu_regex=len(items)-len(wires),first_pass_upper_usd=str(worst),cap_usd='50')));return
    require(sha(spec['budget_receipt'])==spec['budget_receipt_sha256'],'budget receipt pin')
    budget=read(spec['budget_receipt'])
    require(budget.get('issuer')=='integrator' and budget.get('verified') is True and budget.get('shared_E80_E80c_allocation_usd')==50 and budget.get('reservation_included') is True,'shared allocation custody')
    global_total=Decimal(str(budget['global_judging_committed_including_reservation_usd']))
    require(global_total.is_finite() and 50<=global_total<=500,'global USD500 envelope')
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'integrator credential missing')
    ledger_root=Path(seal['ledger_root']);ledger_root.mkdir(parents=True,exist_ok=True)
    with dispatch_lock(ledger_root/'DISPATCH.lock'):
        io.CACHE=ledger_root/'route';io.CACHE.mkdir(exist_ok=True)
        require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'existing privacy proof pin')
        shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json');privacy.check_route(key)
        client=api.Client(ledger_root,key)
        require(Decimal(client.ledger.summary()['committed_usd'])+worst<=CAP,'initial pass plus prior bank/reservations exceeds shared cap')
        out=ledger_root/spec['bank'];out.mkdir(exist_ok=False)
        write(out/'START.json',dict(spec_sha256=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),route_seal_sha256=sha(HERE/'ROUTE_SEAL.json'),first_pass_upper_usd=str(worst)))
        write(out/'REDACTION_AUDIT.json',audit)
        records=[]
        for x in items:
            packet=packets[x['item_id']]
            if x['id'] not in wires:
                records.append(dict(id=x['id'],status='CPU_REGEX',result=regex.score_sample(packet['regex_units'],x['readout'])));continue
            wire=wires[x['id']]
            protocol.payload=lambda *args,wire=wire:wire
            protocol.validate=lambda stage,value,batch,unused=None,packet=packet:valid_response(value,packet)
            def check(stage,batch,sent,unused=None,wire=wire):
                require(sent==wire,'frozen wire changed')
                for value in strings(sent['messages']):original_check('extract',[{'id':'opaque','readout':value}],sent)
            privacy.check_wire=check
            terminal=None
            for attempt in range(3):
                prefix=spec['bank']+':'+x['id']+':'+str(attempt)+':'
                io.digest=lambda value,prefix=prefix:hashlib.sha256((prefix+value).encode()).hexdigest()
                stage=spec['bank']+'_attempt'+str(attempt)
                result=client.one(stage,[{'id':x['id'],'readout':x['readout']}])
                if result['status']=='OK':
                    terminal=dict(id=x['id'],status='KEPT',result=result['value'],attempt=attempt);break
                response=ledger_root/stage/(result['id']+'.response.json')
                require(response.exists() and not client.latch.is_set(),'transport/budget failure; stop')
                r=read(response);b=r['response']
                require(r['http_status']==200 and b.get('provider')==protocol.PROVIDER_NAME and b.get('model') in (protocol.MODEL,protocol.MODEL+'-001') and b.get('usage',{}).get('cost') is not None and b['choices'][0].get('finish_reason')=='stop','transport/route/usage failure; no retry')
                terminal=dict(id=x['id'],status='UNPARSEABLE',result=None,attempt=attempt)
            records.append(terminal)
            write(out/'PROGRESS.json',dict(completed=len(records),cost=client.ledger.summary()))
        write(out/'JUDGMENTS.json',records);write(out/'COST.json',client.ledger.summary())
        seal_output(out,dict(bank=spec['bank'],status='TERMINAL_FROZEN_FAMILY_RESULTS_NO_ANALYSIS',route_seal_sha256=sha(HERE/'ROUTE_SEAL.json')))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True);p.add_argument('--preflight-only',action='store_true')
    a=p.parse_args();run(read(a.spec),a.preflight_only)

if __name__=='__main__':main()
