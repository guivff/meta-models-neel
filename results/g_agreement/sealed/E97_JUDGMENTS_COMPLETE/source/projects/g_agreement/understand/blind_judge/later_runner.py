"""Blinded later-bank judging only; no joins or scientific analysis."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import unicodedata
from decimal import Decimal
from pathlib import Path
from .bank_gate import forecast_gate, budget_gate, coordinator_gate
from .run import ROOT, CACHE, route_modules, payload
from projects.g_agreement.readerbench.io import read, sha, verify, write, seal_output
from projects.g_agreement.readerbench.scoring import require, validate_judgments, RUBRIC_HASHES

HERE = ROOT/'results/g_agreement/understand/blind_judge/later_banks'
LEDGER = CACHE/'later_banks_15usd'
SUPPORTED = {'E56', 'E57', 'E62', 'E62P', 'E59', 'E63'}
S6_RUBRIC_SHA = 'c4b6da302776a221b8ca0f4b9a52a0fe67f706270a0a0bc42c08b6a9c529e86f'


def normalize(text):
    quotes = dict.fromkeys('‘’‚‛', "'") | dict.fromkeys('“”„‟«»', '"')
    return re.sub(r'\s+', ' ', ''.join(quotes.get(c, '-' if unicodedata.category(c) == 'Pd' else c)
                                      for c in text)).strip().casefold()


def classify(items, response, taxonomy="E56"):
    """Retain valid batch-mates; duplicated IDs cannot silently overwrite codes."""
    codes = response.get('records', []) if isinstance(response, dict) else []
    if not isinstance(codes, list):
        codes = []
    output = []
    for item in items:
        matches = [x for x in codes if isinstance(x, dict) and x.get('id') == item['id']]
        code = matches[0] if len(matches) == 1 else None
        try:
            require(code is not None, 'missing/duplicate opaque ID')
            c = dict(code);p = dict(item)
            p['readout'] = normalize(p['readout'])
            if isinstance(c.get('evidence'), str):c['evidence'] = normalize(c['evidence'])
            if taxonomy == 'E66':
                from .channels66_68 import validate66
                validate66(code,item)
            elif taxonomy == 'E67':
                from .e67 import validate_code
                validate_code(code,item)
            elif taxonomy == 'S6':
                require(set(c) == {'id','eval_mention','evidence'} and type(c['eval_mention']) is bool, 'S6 schema')
                require(isinstance(c['evidence'], str) and c['evidence'] in p['readout'] and bool(c['evidence']) == c['eval_mention'], 'S6 evidence')
            elif taxonomy == 'E85_202':
                require(set(c)=={'id','eval_mention','genre_vocabulary','evidence'} and
                        type(c['eval_mention']) is bool and type(c['genre_vocabulary']) is bool and
                        type(c['evidence']) is dict and set(c['evidence'])=={'self','genre'},
                        '§202 E85 independent self-evaluation and genre schema')
                for name,flag in (('self','eval_mention'),('genre','genre_vocabulary')):
                    e=c['evidence'][name]
                    require(type(e) is str and bool(e)==c[flag] and normalize(e) in p['readout'],
                            '§202 E85 verbatim evidence')
            elif taxonomy in ('E91','E92'):
                field='polarity' if taxonomy=='E91' else 'source'
                values={'AFFIRMED','NEGATED','NEITHER'} if taxonomy=='E91' else {'user','tool','assistant','no_one'}
                empty='NEITHER' if taxonomy=='E91' else 'no_one'
                require(set(c)=={'id',field,'evidence'} and c[field] in values and
                        type(c['evidence']) is str and bool(c['evidence'])==(c[field]!=empty) and
                        normalize(c['evidence']) in p['readout'],'§201 taxonomy and exact evidence')
            else:
                validate_judgments([p], [c], taxonomy)
            output.append(dict(id=item['id'], status='KEPT', code=code))
        except (ValueError, TypeError, KeyError):
            output.append(dict(id=item['id'], status='INVALID', code=None))
    return output


def channel_payload(items, rubric, taxonomy, protocol):
    wire = payload(items, rubric, 'E56' if taxonomy == 'S6' else taxonomy, protocol)
    if taxonomy == 'E66':
        from .channels66_68 import schema66
        wire['response_format']['json_schema']['schema']['properties']['records']['items']=schema66()
    elif taxonomy == 'E67':
        wire['messages'][1]['content']=json.dumps([{k:x[k] for k in ('id','prompt','readout','rubric')} for x in items],ensure_ascii=False)
        wire['response_format']['json_schema']['schema']['properties']['records']['items']={
            'type':'object','additionalProperties':False,'required':['id','claims','generic'],
            'properties':{'id':{'type':'string'},'generic':{'type':'boolean'},
                'claims':{'type':'array','maxItems':5,'items':{'type':'object','additionalProperties':False,
                    'required':['claim','verdict'],'properties':{'claim':{'type':'string','minLength':1},
                    'verdict':{'type':'string','enum':['SUPPORTED','CONTRADICTED','UNVERIFIABLE']}}}}}}
    elif taxonomy == 'S6':
        wire['response_format']['json_schema']['schema']['properties']['records']['items'] = {
            'type':'object', 'additionalProperties':False, 'required':['id','eval_mention','evidence'],
            'properties':{'id':{'type':'string'},'eval_mention':{'type':'boolean'},'evidence':{'type':'string'}}}
    elif taxonomy == 'E85_202':
        wire['response_format']['json_schema']['schema']['properties']['records']['items']={
            'type':'object','additionalProperties':False,
            'required':['id','eval_mention','genre_vocabulary','evidence'],
            'properties':{'id':{'type':'string'},'eval_mention':{'type':'boolean'},
                          'genre_vocabulary':{'type':'boolean'},'evidence':{'type':'object',
             'additionalProperties':False,'required':['self','genre'],
             'properties':{'self':{'type':'string'},'genre':{'type':'string'}}}}}
    elif taxonomy in ('E91','E92'):
        field='polarity' if taxonomy=='E91' else 'source'
        options=['AFFIRMED','NEGATED','NEITHER'] if taxonomy=='E91' else ['user','tool','assistant','no_one']
        wire['response_format']['json_schema']['schema']['properties']['records']['items']={
            'type':'object','additionalProperties':False,'required':['id',field,'evidence'],
            'properties':{'id':{'type':'string'},field:{'type':'string','enum':options},
                          'evidence':{'type':'string'}}}
    return wire


def admission(spec):
    if spec['bank'] in ('E66','E68','E76') or spec['bank'] in ('E81','E82','E83','E84','E85','E86','E91','E92'):
        if spec['bank'] in ('E91','E92'):
            from .channels91_92 import admission as special_admission
        elif spec['bank'] in ('E81','E82','E83','E84','E85','E86'):
            from .channels81_86 import admission as special_admission
        else:
            from .channels66_68 import admission as special_admission
        return special_admission(spec)
    require(spec['bank'] in SUPPORTED, 'unsupported judging bank')
    # Must run before opening or hashing any readout-containing file.
    gate_fn = coordinator_gate if spec['bank'] == 'E63' else forecast_gate
    gate = gate_fn(spec['bank'], spec['forecast_repo'], spec['forecast_commit'],
                         spec['forecast_path'], spec['forecast_sha256'])
    require(sha(spec['budget_receipt']) == spec['budget_receipt_sha256'], 'allocation hash')
    budget_gate(read(spec['budget_receipt']))
    require(sha(spec['receipt']) == spec['receipt_sha256'], 'custody receipt hash')
    receipt = read(spec['receipt'])
    require(receipt.get('issuer') == 'integrator' and receipt.get('verified') is True and
            receipt.get('bank') == spec['bank'], 'integrator verified bank custody')
    for field in ('bank_seal_sha256', 'capture_seal_sha256', 'forecast_sha256'):
        require(receipt[field] == gate[field], 'forecast/custody mismatch: '+field)
    require(receipt.get('source_seals'), 'verified pull seals required')
    for source in receipt['source_seals']:
        verify(source['path'], source['sha256'])
    require(receipt['packet_seal_sha256'] == spec['packet_seal_sha256'], 'packet custody binding')
    packet = Path(spec['packet'])
    seal = verify(packet/'BLIND_SEAL.json', spec['packet_seal_sha256'])
    require(seal['experiment'] == spec['bank'] and 'JUDGE_PACKET.json' in seal['files'], 'bank packet seal')
    channel = spec.get('channel', 'value')
    require(channel in ({'rp2'} if spec['bank'] == 'E63' else {'value','eval'} if spec['bank'] == 'E62' else {'value'}), 'bank/channel contract')
    taxonomy = 'D5' if channel == 'rp2' else 'S6' if channel == 'eval' else 'E56'
    if channel == 'rp2':
        require(receipt.get('n') == 400 and receipt.get('per_reader_counts') == {'oracle':200,'nla':200}
                and receipt.get('sampling_seed') == 20261027 and receipt.get('sampling_without_replacement') is True, 'frozen E63 R-P2 sample receipt')
    rubric_field = 'eval_rubric_sha256' if channel == 'eval' else 'rubric_sha256'
    packet_file = 'EVAL_PACKET.json' if channel == 'eval' else 'JUDGE_PACKET.json'
    require(packet_file in seal['files'], 'sealed channel packet')
    require(sha(spec['rubric']) == seal[rubric_field] == (S6_RUBRIC_SHA if taxonomy == 'S6' else RUBRIC_HASHES[taxonomy]), 'frozen channel rubric')
    items = read(packet/packet_file)
    require(len(items) == receipt['n'] and len(items) > 0 and len({x['id'] for x in items}) == len(items), 'complete unique packet')
    frozen_rubric = Path(spec['rubric']).read_text()
    if taxonomy == 'E56':
        from .judgment_adapter402 import render_record
        items = [render_record(x, frozen_rubric) for x in items]
        if spec.get('wire_packet'):
            wire = Path(spec['wire_packet'])
            ws = verify(wire.parent/'WIRE_SEAL.json', spec['wire_seal_sha256'])
            require(ws['blind_seal_sha256'] == spec['packet_seal_sha256'] and wire.name in ws['files'], 'rendered wire custody')
            require(read(wire) == items, 'rendered rubric/property/A/B differs from frozen source')
    allowed = {'id','readout'} if taxonomy in ('S6','D5') else {'id','rubric','readout'}
    require(all(set(x) == allowed and
                re.fullmatch('[a-f0-9]{20,64}', x['id']) and
                isinstance(x.get('rubric',''), str) and isinstance(x['readout'], str) for x in items),
            'wire packet requires opaque ID, frozen rubric and text only; no row/arm/reader IDs')
    return items, frozen_rubric


def judge(items, send):
    """Only validation failures are retried, singly, at most twice."""
    results = {}
    for start in range(0, len(items), 4):
        batch = items[start:start+4]
        for record in send(batch, 0):
            results[record['id']] = dict(record, attempts=0)
    for item in items:
        record = results[item['id']]
        if record['status'] == 'KEPT':continue
        for attempt in (1, 2):
            record = dict(send([item], attempt)[0], attempts=attempt)
            results[item['id']] = record
            if record['status'] == 'KEPT':break
        if record['status'] != 'KEPT':record.update(status='UNPARSEABLE', code=None)
    return [results[x['id']] for x in items]


def dispatch(spec, items, rubric, route, key, budget_cap=None):
    from .privacy79 import redact, check_decoded
    items,redaction_audit=redact(items,spec['bank'],addresses=True)
    taxonomy = 'E66' if spec['bank']=='E66' else 'E67' if spec.get('channel') == 'claims' else 'E91' if spec['bank']=='E91' else 'E92' if spec['bank']=='E92' else 'D5' if spec.get('channel') == 'rp2' else 'E85_202' if spec['bank']=='E85' else 'S6' if spec.get('channel') == 'eval' else 'E56'
    job_id = spec['bank'] + ('_eval' if taxonomy in ('S6','E85_202') else '_rp2' if taxonomy == 'D5' else '')
    if taxonomy=='E67':job_id += '_'+spec['packet_id']
    if taxonomy=='E67' and spec.get('wave',1)==2:job_id='E67_wave_2_'+spec['packet_id']
    if spec['bank'] in ('E76','E81','E82','E83','E84','E85','E86','E91','E92'):
        from .cap_ledger import cap_entry
        cap=cap_entry(spec,spec['bank'])
    else:
        cap=Decimal('6') if spec['bank']=='E68' else Decimal('3') if spec['bank']=='E66' else Decimal('5') if taxonomy=='E67' else Decimal('15')
    if budget_cap is not None:
        require(budget_cap.is_finite() and 0<=budget_cap<=cap,'budget may only reduce registered cap')
        cap=budget_cap
    api, privacy, protocol, io = route_modules(route)
    api.CAP = cap
    require(protocol.MODEL == 'google/gemini-3.1-flash-lite' and protocol.PROVIDER == 'google-vertex/global', 'pinned route')
    io.CACHE = LEDGER/'route';io.CACHE.mkdir(parents=True, exist_ok=True)
    require(sha(route['privacy_proof']) == route['privacy_proof_sha256'], 'privacy proof hash')
    shutil.copyfile(route['privacy_proof'], io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
    privacy.check_route(key)
    original_check = privacy.check_wire
    def check(stage, batch, wire, unused=None):
        require(all(set(x) == ({'id','prompt','readout','rubric'} if taxonomy=='E67' else {'id','readout'} if taxonomy in ('S6','E85_202','D5','E66') else {'id','rubric','readout'}) for x in batch), 'private fields')
        check_decoded(original_check,batch,wire)
    privacy.check_wire = check
    protocol.payload = lambda stage, batch, unused=None: channel_payload(batch, rubric, taxonomy, protocol)
    protocol.validate = lambda stage, response, batch, unused=None: classify(batch, response, taxonomy)
    client = api.Client(LEDGER, key)
    original_items=[]; original_rubric=None; original_taxonomy=None
    if spec['bank'] in ('E81','E82','E83','E84','E85','E86','E91','E92'):
        from .rubric202 import BASE,original_ids
        from .channels81_86 import HERE as BANK_HERE
        wanted=set(read(Path(spec['packet'])/'ORIGINAL_IDS.json'))
        require(wanted==set(original_ids([x['id'] for x in items],spec['bank'])),
                '§202 comparison sample')
        if spec['bank'] in ('E91','E92'):
            from .channels91_92 import rubric_path
            original_rubric=rubric_path(spec['bank'],original=True).read_text()
        else:original_rubric=(BANK_HERE/'E85_RUBRIC.txt' if spec['bank']=='E85' else BASE).read_text()
        original_taxonomy='S6' if spec['bank']=='E85' else taxonomy
        original_items=[dict(x,**({'rubric':x['rubric'].replace(rubric,original_rubric,1)}
                    if 'rubric' in x else {})) for x in items if x['id'] in wanted]
        require(len(original_items)==len(wanted) and all(x['rubric'].startswith(original_rubric)
                for x in original_items if 'rubric' in x),'§202 original rubric binding')
    batches = [items[i:i+4] for i in range(0,len(items),4)]
    original_batches=[original_items[i:i+4] for i in range(0,len(original_items),4)]
    for batch in batches:check(spec['bank'], batch, protocol.payload(spec['bank'],batch))
    worst = sum((api.upper(protocol.payload('',b)) for b in batches), Decimal(0))
    if original_batches:
        worst+=sum((api.upper(channel_payload(b,original_rubric,original_taxonomy,protocol))
                    for b in original_batches),Decimal(0))
    require(Decimal(client.ledger.summary()['committed_usd'])+worst <= cap, 'initial bank pass exceeds remaining separate cap; no send')
    if spec['bank'] in ('E76','E81','E82','E83','E84','E85','E86','E91','E92'):
        from .cap_ledger import cap_entry
        cap_entry(spec,spec['bank'],worst)
    job = LEDGER/(job_id+'_judgments')
    job.mkdir(exist_ok=False)
    write(job/'START.json', dict(packet_seal_sha256=spec['packet_seal_sha256'], initial_pass_upper_usd=str(worst)))
    write(job/'PATH_REDACTION_AUDIT.json',redaction_audit)
    write(job/'JUDGE_COPY.json',items)
    active_taxonomy=taxonomy;active_rubric=rubric;active_job=job_id
    def send(batch, attempt):
        prefix = active_job+':'+str(attempt)+':'
        io.digest = lambda value: hashlib.sha256((prefix+value).encode()).hexdigest()
        stage = active_job+'_attempt'+str(attempt)
        protocol.payload=lambda stage,batch,unused=None:channel_payload(batch,active_rubric,active_taxonomy,protocol)
        protocol.validate=lambda stage,response,batch,unused=None:classify(batch,response,active_taxonomy)
        if spec['bank'] in ('E76','E81','E82','E83','E84','E85','E86','E91','E92'):
            from .cap_ledger import global_send
            with global_send(api,protocol.payload(stage,batch)):
                result=client.one(stage,batch)
        else:result = client.one(stage, batch)
        if result['status'] == 'OK':return result['value']
        # Retry malformed JSON only when transport, route, cost and completion are verified.
        response_path = LEDGER/stage/(result['id']+'.response.json')
        require(response_path.exists() and not client.latch.is_set(), 'transport/budget/unresolved request: stop, no resend')
        response = read(response_path);body = response['response']
        require(response['http_status'] == 200 and body.get('provider') == protocol.PROVIDER_NAME and
                body.get('model') in (protocol.MODEL, protocol.MODEL+'-001') and
                body.get('usage',{}).get('cost') is not None and
                body['choices'][0].get('finish_reason') == 'stop', 'transport/route/cost/completion failure: stop')
        try:json.loads(body['choices'][0]['message']['content'])
        except (ValueError, TypeError):return classify(batch, {}, active_taxonomy)
        raise RuntimeError('unexpected client failure; no scientific retry')
    try:
        terminal = judge(items, send)
        write(job/'JUDGMENTS.json', terminal)
        if original_items:
            active_taxonomy=original_taxonomy;active_rubric=original_rubric
            active_job=job_id+'_original_25pct'
            original_terminal=judge(original_items,send)
            write(job/'ORIGINAL_JUDGMENTS.json',original_terminal)
        write(job/'COUNTS.json', dict(n=len(terminal),kept=sum(x['status']=='KEPT' for x in terminal),
            unparseable=sum(x['status']=='UNPARSEABLE' for x in terminal),
            retried=sum(x['attempts']>0 for x in terminal), redacted_records=redaction_audit['redacted_records'],
            original_25pct=len(original_items),cost=client.ledger.summary()))
        shutil.copyfile(LEDGER/'ledger.jsonl', job/'LEDGER_AT_END.jsonl')
        seal_output(job, dict(status='TERMINAL_BLIND_GRID_NO_ANALYSIS', bank=spec['bank'],
            packet_seal_sha256=spec['packet_seal_sha256'], channel=spec.get('channel','value'),wave=spec.get('wave')))
    except Exception as exc:
        write(job/'BLOCKED.json', dict(error_type=type(exc).__name__,cost=client.ledger.summary(),retry=False))
        raise


def main():
    global LEDGER
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--preflight-only',action='store_true');a=p.parse_args()
    manifest = read(HERE/'RUNNER_SOURCE_SEAL.json')
    for name,digest in manifest['files'].items():require(sha(name)==digest,'runner source changed')
    spec = read(a.spec)
    if spec['bank'] in ('E66','E68','E76'):
        LEDGER = CACHE/(spec['bank'].lower()+('_2usd' if spec['bank']=='E76' else '_3usd'))
    elif spec['bank'] in ('E81','E82','E83','E84','E85','E86','E91','E92'):
        LEDGER = CACHE/(spec['bank'].lower()+'_judging')
    items,rubric = admission(spec)
    if a.preflight_only:
        print('Bank/channel packet and admission verified; no API call');return
    route = read(ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    key = os.environ.get('OPENROUTER_API_KEY');require(bool(key),'credential unavailable')
    LEDGER.mkdir(parents=True,exist_ok=True)
    from .dispatch_lock import dispatch_lock
    with dispatch_lock(LEDGER/'DISPATCH.lock'):
        # One operator across banks; ledger reservations additionally use flock and fsync.
        if spec['bank']=='E66':
            from .channels66_68 import reserve_parent
            api,_,_,_=route_modules(route)
            reserve_parent(api,CACHE)
        dispatch(spec,items,rubric,route,key)


if __name__ == '__main__':main()
