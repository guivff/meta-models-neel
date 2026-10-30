"""§200 E87: one blinded call per item/layer with every position's native readout."""
import argparse
import hashlib
import json
import os
import re
import shutil
from decimal import Decimal
from pathlib import Path

from projects.g_agreement.readerbench.io import read,sha,verify,write,seal_output
from projects.g_agreement.readerbench.scoring import require,validate_judgments
from .run import ROOT,CACHE,route_modules,payload
from .dispatch_lock import dispatch_lock
from .judgment_adapter402 import render_record
from .privacy79 import redact,check_decoded
from .later_runner import normalize,judge

HERE=ROOT/'results/g_agreement/understand/e87'
RUBRIC=ROOT/'results/g_agreement/understand/blind_judge/later_banks/RUBRIC202_VALUE.txt'
ORIGINAL=ROOT/'results/g_agreement/understand/blind_judge/e66_e68/E68_RUBRIC.md'
LEDGER=CACHE/'e87_4usd'
ROWS={'container_after_move','holder_after_handovers','branch_taken','var_type_at_use',
      'user_expertise','unit_system','nesting_depth','indent_level','topic_twin','loop_direction'}
ORACLE_LAYERS=(20,28,36,44,52,56,60)
EXPECTED_GROUPS={'oracle':2100,'nla':300,'placebo':2100}
EXPECTED_READOUTS=67920


def validate_grid(seal,n):
    require(seal.get('authority')=='47cf57c2' and
            seal.get('oracle_layers')==list(ORACLE_LAYERS) and
            seal.get('group_counts')==EXPECTED_GROUPS and
            seal.get('n_readouts')==EXPECTED_READOUTS and
            n==sum(EXPECTED_GROUPS.values()),
            'E87 seven-layer amended grid and matched placebo forecast')


def validate_source(items):
    require(type(items) is list and len(items)>0 and len({x['id'] for x in items})==len(items),
            'complete unique grouped IDs')
    for x in items:
        require(set(x)=={'id','property','values','positions'} and
                re.fullmatch('[a-f0-9]{20,64}',x['id']) and
                type(x['positions']) is list and 1 <= len(x['positions']) <= 16,
                'opaque group and registered position count')
        expected=list(range(1-len(x['positions']),1))
        require([p.get('offset') for p in x['positions']]==expected and
                all(type(p) is dict and set(p)=={'offset','readout'} and
                    type(p['readout']) is str for p in x['positions']),
                'all positions in chronological order, ending at read token')
        render_record(dict(id=x['id'],property=x['property'],values=x['values'],readout=''),
                      RUBRIC.read_text())


def convert(spec,out):
    require(sha(spec['source_seal'])==spec['source_seal_sha256'],'verified source seal hash')
    s=read(spec['source_seal']);source=Path(spec['source_packet'])
    require(s.get('experiment')=='E87' and s.get('complete') is True and
            source.name=='GROUPED_PACKET.json' and source.parent.resolve()==Path(spec['source_seal']).parent.resolve() and
            sha(source)==s['files'][source.name] and s['rubric_sha256']==sha(RUBRIC) and
            Path(spec['rubric']).read_bytes()==RUBRIC.read_bytes(),
            'frozen complete packet and §172 rubric')
    items=read(source);validate_source(items);require(s['n']==len(items),'group count seal')
    require(sum(len(x['positions']) for x in items)==s['n_readouts'],'all achieved positions sealed')
    validate_grid(s,len(items))
    for key in ('row_inventory_verified','first_30_frozen_order_verified','placebo_matched_verified',
                'placebo_random_only_verified'):
        require(s.get(key) is True,'registered grid custody: '+key)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    write(out/'GROUPED_PACKET.json',items)
    (out/'RUBRIC.txt').write_bytes(RUBRIC.read_bytes())
    from .rubric202 import original_ids
    write(out/'ORIGINAL_IDS.json',original_ids([x['id'] for x in items],'E87'))
    write(out/'PACKET_SEAL.json',dict(experiment='E87',n=len(items),
        authority='47cf57c2',oracle_layers=list(ORACLE_LAYERS),
        group_counts=EXPECTED_GROUPS,n_readouts=EXPECTED_READOUTS,
        source_seal_sha256=spec['source_seal_sha256'],source_packet_sha256=sha(source),
        rubric_sha256=sha(RUBRIC),files={p.name:sha(p) for p in (out/'GROUPED_PACKET.json',out/'RUBRIC.txt',out/'ORIGINAL_IDS.json')}))


def budget_gate(b,spec):
    from .cap_ledger import cap_entry
    cap=cap_entry(spec,'E87')
    require(b.get('issuer')=='integrator' and b.get('verified') is True and b.get('bank')=='E87' and
            b.get('allocation_id') and b.get('reservation_included') is True and
            b.get('date_zurich') in ('2026-10-28','2026-10-29') and
            Decimal(str(b['reserved_judging_usd']))==cap and
            cap<=Decimal(str(b['daily_committed_including_reservation_usd']))<=300,
            'sealed E87 ceiling in daily limit')


def admission(spec):
    require(spec['bank']=='E87' and spec.get('channel')=='grouped_positions','E87 channel only')
    require(sha(spec['budget_receipt'])==spec['budget_receipt_sha256'],'budget receipt binding')
    budget_gate(read(spec['budget_receipt']),spec)
    require(sha(spec['receipt'])==spec['receipt_sha256'],'custody receipt binding')
    r=read(spec['receipt'])
    require(r.get('issuer')=='integrator' and r.get('verified') is True and r.get('bank')=='E87' and
            r.get('authority')=='47cf57c2' and r.get('forecast_gate_verified') is True and
            r.get('amended_seven_layer_forecast_verified') is True and
            r.get('e87_hold_resolved') is True and
            r.get('source_seals') and r.get('private_map_sealed') is True,
            'registered verified pull/forecast and private item/layer key')
    require(sha(spec['amended_forecast_file'])==spec['amended_forecast_sha256']==
            r.get('amended_forecast_sha256'),'seven-layer forecast receipt binding')
    amended=read(spec['amended_forecast_file'])
    require(amended.get('layers')==list(ORACLE_LAYERS) and
            amended.get('exact_readouts')=={'nla':2400,'oracle_real':32760,
                                             'oracle_placebo':32760,'total':EXPECTED_READOUTS} and
            amended.get('status')=='READY', 'amended forecast must clear launch hold')
    for entry in r['source_seals']:require(sha(entry['path'])==entry['sha256'],'source custody')
    packet=Path(spec['packet']);s=verify(packet/'PACKET_SEAL.json',spec['packet_seal_sha256'])
    require(s['experiment']=='E87' and r['packet_seal_sha256']==spec['packet_seal_sha256'] and
            s['source_seal_sha256'] in {entry['sha256'] for entry in r['source_seals']} and
            s['n']==r['n'] and s['rubric_sha256']==sha(RUBRIC) and
            (packet/'RUBRIC.txt').read_bytes()==RUBRIC.read_bytes(),
            'verified grouped conversion/rubric')
    validate_grid(s,s['n']);validate_grid(r,r['n'])
    source_path=next(Path(x['path']) for x in r['source_seals'] if x['sha256']==s['source_seal_sha256'])
    original=read(source_path);p=source_path.parent/'GROUPED_PACKET.json'
    require(sha(p)==original['files']['GROUPED_PACKET.json']==s['source_packet_sha256'] and
            read(p)==read(packet/'GROUPED_PACKET.json'),'source packet still byte-bound')
    items=read(packet/'GROUPED_PACKET.json');validate_source(items)
    from .rubric202 import original_ids
    require(read(packet/'ORIGINAL_IDS.json')==original_ids([x['id'] for x in items],'E87'),
            '§202 sealed comparison sample')
    require(len(items)==r['n'],'complete item × layer and placebo grid')
    return [dict(id=x['id'],rubric=render_record(dict(id=x['id'],property=x['property'],
               values=x['values'],readout=''),RUBRIC.read_text())['rubric'],positions=x['positions'])
            for x in items]


def redact_groups(groups):
    flat=[dict(id=group['id']+f'{p["offset"]:+03}',readout=p['readout'])
          for group in groups for p in group['positions']]
    copied,audit=redact(flat,'E87',addresses=True)
    ix=iter(copied)
    result=[dict(g,positions=[dict(p,readout=next(ix)['readout']) for p in g['positions']])
            for g in groups]
    require(next(ix,None) is None,'complete redaction')
    return result,audit


def validate_code(item,code):
    require(set(code)=={'id','category','values','evidence','first_position'} and
            code['id']==item['id'],'group code identity/schema')
    positions=item['positions'];by={p['offset']:p['readout'] for p in positions}
    pos=code['first_position'];category=code['category'];evidence=code['evidence']
    require(category in ('states_value','names_property_without_value','exhibits','silent') and
            type(evidence) is str,'§172 category and evidence')
    if category=='silent':
        require(pos is None and evidence=='' and code['values']==[],'silent no mention')
    else:
        require(type(pos) is int and pos in by and bool(normalize(evidence)) and
                normalize(evidence) in normalize(by[pos]),'quote at asserted first position')
    # Native §172 schema still validates the value set and code category.
    flat=dict(id=item['id'],readout='\n'.join(p['readout'] for p in positions))
    normalized=dict(id=flat['id'],readout=normalize(flat['readout']))
    clean={k:code[k] for k in ('id','category','values','evidence')}
    clean['evidence']=normalize(clean['evidence'])
    validate_judgments([normalized],[clean],'E56')


def classify(items,response):
    codes=response.get('records',[]) if isinstance(response,dict) else []
    if type(codes) is not list:codes=[]
    out=[]
    for item in items:
        found=[c for c in codes if type(c) is dict and c.get('id')==item['id']]
        try:
            require(len(found)==1,'one result per ID');validate_code(item,found[0])
            out.append(dict(id=item['id'],status='KEPT',code=found[0]))
        except (ValueError,TypeError,KeyError):out.append(dict(id=item['id'],status='INVALID',code=None))
    return out


def wire(items,protocol,rubric=None):
    require(all(set(x)=={'id','rubric','positions'} for x in items),
            'wire accepts rendered blind groups only')
    w=payload([],RUBRIC.read_text() if rubric is None else rubric,'E56',protocol)
    w['messages'][1]['content']=json.dumps(items,ensure_ascii=False)
    schema=w['response_format']['json_schema']['schema']['properties']['records']['items']
    schema['properties']['first_position']={'type':['integer','null'],'minimum':-15,'maximum':0}
    schema['required'].append('first_position')
    return w


def dispatch(spec,items,route,key):
    from .cap_ledger import cap_entry,global_send
    items,audit=redact_groups(items)
    api,privacy,protocol,io=route_modules(route);api.CAP=cap_entry(spec,'E87')
    require(protocol.MODEL=='google/gemini-3.1-flash-lite' and protocol.PROVIDER=='google-vertex/global',
            'pinned E10 route')
    io.CACHE=LEDGER/'route';io.CACHE.mkdir(parents=True,exist_ok=True)
    require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'privacy proof')
    shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
    privacy.check_route(key)
    original=privacy.check_wire
    def check(stage,batch,body,unused=None):
        require(all(set(x)=={'id','rubric','positions'} for x in batch),'only blind grouped records')
        check_decoded(original,batch,body)
    privacy.check_wire=check
    active_rubric=RUBRIC.read_text()
    protocol.payload=lambda stage,batch,unused=None:wire(batch,protocol,active_rubric)
    protocol.validate=lambda stage,response,batch,unused=None:classify(batch,response)
    client=api.Client(LEDGER,key)
    # A batch is one item/layer; 8/16 readouts are never split into separate calls.
    original_ids=set(read(Path(spec['packet'])/'ORIGINAL_IDS.json'))
    original_items=[dict(i,rubric=i['rubric'].replace(RUBRIC.read_text(),ORIGINAL.read_text(),1))
                    for i in items if i['id'] in original_ids]
    require(len(original_items)==len(original_ids) and all(i['rubric'].startswith(ORIGINAL.read_text())
               for i in original_items),'original-rubric exact sample')
    worst=sum((api.upper(wire([i],protocol)) for i in items),Decimal(0))
    worst+=sum((api.upper(wire([i],protocol,ORIGINAL.read_text())) for i in original_items),Decimal(0))
    require(Decimal(client.ledger.summary()['committed_usd'])+worst<=api.CAP,
            'complete initial sweep exceeds sealed E87 ceiling; no send')
    cap_entry(spec,'E87',worst)
    job=LEDGER/'E87_grouped_judgments';job.mkdir(exist_ok=False)
    write(job/'START.json',dict(n=len(items),source_packet_seal_sha256=spec['packet_seal_sha256'],
                                initial_upper_usd=str(worst)))
    write(job/'JUDGE_COPY.json',items);write(job/'PATH_REDACTION_AUDIT.json',audit)
    stage_prefix='E87'
    def send(batch,attempt):
        require(1<=len(batch)<=4,'grouping only in local iteration')
        output=[]
        for item in batch:
            singleton=[item]
            ident=stage_prefix+':'+str(attempt)+':'
            io.digest=lambda v:hashlib.sha256((ident+v).encode()).hexdigest()
            stage=stage_prefix+'_attempt'+str(attempt)
            with global_send(api,wire(singleton,protocol,active_rubric)):
                result=client.one(stage,singleton)
            if result['status']=='OK':
                output.extend(result['value']);continue
            response_path=LEDGER/stage/(result['id']+'.response.json')
            require(response_path.exists() and not client.latch.is_set(),
                    'transport/budget/unresolved request: stop, no resend')
            response=read(response_path);body=response['response']
            require(response['http_status']==200 and body.get('provider')==protocol.PROVIDER_NAME and
                    body.get('model') in (protocol.MODEL,protocol.MODEL+'-001') and
                    body.get('usage',{}).get('cost') is not None and
                    body['choices'][0].get('finish_reason')=='stop',
                    'route/cost/completion failure: stop, no resend')
            try:json.loads(body['choices'][0]['message']['content'])
            except (ValueError,TypeError):output.extend(classify(singleton,{}));continue
            raise RuntimeError('unexpected client failure; no scientific retry')
        return output
    try:
        terminal=judge(items,send)
        write(job/'JUDGMENTS.json',terminal)
        active_rubric=ORIGINAL.read_text();stage_prefix='E87_original'
        original_terminal=judge(original_items,send)
        write(job/'ORIGINAL_JUDGMENTS.json',original_terminal)
        write(job/'COUNTS.json',dict(n=len(items),kept=sum(x['status']=='KEPT' for x in terminal),
            unparseable=sum(x['status']=='UNPARSEABLE' for x in terminal),
            retried=sum(x['attempts']>0 for x in terminal),original_n=len(original_terminal),
            original_kept=sum(x['status']=='KEPT' for x in original_terminal),cost=client.ledger.summary()))
        shutil.copyfile(LEDGER/'ledger.jsonl',job/'LEDGER_AT_END.jsonl')
        seal_output(job,dict(status='TERMINAL_BLIND_GRID_NO_ANALYSIS',bank='E87',
                             packet_seal_sha256=spec['packet_seal_sha256']))
    except Exception as exc:
        write(job/'BLOCKED.json',dict(error_type=type(exc).__name__,cost=client.ledger.summary(),retry=False))
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',required=True,type=Path);p.add_argument('--preflight-only',action='store_true')
    args=p.parse_args()
    source=read(HERE/'SOURCE_SEAL.json')
    for name,digest in source['files'].items():require(sha(name)==digest,'E87 source changed')
    spec=read(args.spec);items=admission(spec)
    if args.preflight_only:
        print('E87 full grouped packet and budget verified; no judging calls');return
    route=read(ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'integrator credential unavailable')
    LEDGER.mkdir(parents=True,exist_ok=True)
    with dispatch_lock(LEDGER/'DISPATCH.lock'):
        dispatch(spec,items,route,key)


if __name__=='__main__':main()
