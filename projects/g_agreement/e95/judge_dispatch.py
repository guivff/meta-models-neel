"""E95 transport binding using E87's existing wire, renderer and classifier.

Credentials are passed by the integrator; importing or preflighting sends nothing.
"""
import hashlib
import json
import re
import shutil
import subprocess
import time
from contextlib import nullcontext, ExitStack
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from projects.g_agreement.readerbench.io import read, sha, write
from projects.g_agreement.readerbench.scoring import require
from projects.g_agreement.understand.blind_judge import e87
from projects.g_agreement.understand.blind_judge.dispatch_lock import dispatch_lock
from projects.g_agreement.understand.blind_judge.privacy79 import check_decoded
from projects.g_agreement.understand.blind_judge.run import route_modules
from projects.g_agreement.understand.blind_judge.operational217 import judge,truncated
from projects.g_agreement.understand.blind_judge.validator221 import e87_classify
from projects.g_agreement.understand.blind_judge import funded_queue
from projects.g_agreement.understand.blind_judge.parallel_funded import patch_api
from .judge_admission import admission, budget_gate
from projects.g_agreement.understand.blind_judge.deadline236 import paid_window

ADAPTER_FILES = (
    'results/g_agreement/understand/e95/deviation2/ROW_INVENTORY.json',
    'results/g_agreement/understand/e95/deviation2/JUDGE_INDEX.json',
    'results/g_agreement/understand/e95/ROW_INVENTORY.json',
    'results/g_agreement/understand/e95/STATEMENT_SCORE_ELIGIBILITY.json',
    'results/g_agreement/understand/e95/oracle_only_inventory/INVENTORY_20261029T1448Z.json',
    'projects/g_agreement/understand/blind_judge/deadline236.py',
    'projects/g_agreement/e95/stage_complete.py',
    'projects/g_agreement/understand/blind_judge/validator221.py',
    'projects/g_agreement/understand/blind_judge/operational217.py',
    'projects/g_agreement/understand/blind_judge/parallel_funded.py',
    'projects/g_agreement/understand/blind_judge/funded_queue.py',
    'projects/g_agreement/e95/judge_dispatch.py',
    'projects/g_agreement/e95/judge_admission.py',
    'projects/g_agreement/e95/judging_stages.py',
    'projects/g_agreement/e95/judging_workers.py',
    'projects/g_agreement/e95/worker_probe.py',
    'projects/g_agreement/e95/packet_intake.py',
    'projects/g_agreement/e95/judge_prepare.py',
    'projects/g_agreement/ops/e98_frozen_regex620.py',
    'results/g_agreement/understand/e76/REGEX_CATALOG.json',
    'projects/g_agreement/understand/blind_judge/internals_c/backend248.py',
    'projects/g_agreement/understand/blind_judge/internals_c/resume_e340.py',
    'projects/g_agreement/understand/blind_judge/internals_c/transport.py',
    'projects/g_agreement/understand/blind_judge/internals_c/booked_bounds248.py',
    'projects/g_agreement/understand/blind_judge/e87.py',
    'projects/g_agreement/understand/blind_judge/run.py',
    'projects/g_agreement/understand/blind_judge/later_runner.py',
    'projects/g_agreement/understand/blind_judge/privacy79.py',
    'projects/g_agreement/understand/blind_judge/judgment_adapter402.py',
    'projects/g_agreement/understand/blind_judge/dispatch_lock.py',
    'projects/g_agreement/readerbench/io.py',
    'projects/g_agreement/readerbench/scoring.py',
    'results/g_agreement/understand/blind_judge/later_banks/RUBRIC202_VALUE.txt',
    'results/g_agreement/understand/blind_judge/e66_e68/E68_RUBRIC.md',
)


def verify_adapter(spec):
    root = Path(__file__).resolve().parents[3]
    require(sha(spec['source_seal']) == spec['source_seal_sha256'], 'E95 adapter source identity')
    source = read(spec['source_seal'])
    require(source.get('experiment') == 'E95' and source.get('kind') == 'judge source binding'
            and set(ADAPTER_FILES) <= set(source['files']),
            'own adapter and existing E87 primitives all bound')
    for name, digest in source['files'].items():
        path = (root/name).resolve()
        require(path.is_relative_to(root) and sha(path) == digest, 'frozen judge source member')
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=root)
        require(hashlib.sha256(blob).hexdigest()==digest,'committed E95 judge dependency')


def calls_and_bound(items, original_ids, api, protocol):
    old = set(original_ids)
    require(old <= {x['id'] for x in items}, 'comparison sample within paid groups')
    original = [dict(x, rubric=x['rubric'].replace(e87.RUBRIC.read_text(),
                e87.ORIGINAL.read_text(), 1)) for x in items if x['id'] in old]
    require(all(x['rubric'].startswith(e87.ORIGINAL.read_text()) for x in original),
            'unchanged original-rubric text')
    primary_wires = [e87.wire([x], protocol) for x in items]
    old_wires = [e87.wire([x], protocol, e87.ORIGINAL.read_text()) for x in original]
    for wire in primary_wires + old_wires:
        p = wire['provider']
        require(wire['model'] == 'google/gemini-3.1-flash-lite'
                and p['only'] == p['order'] == ['google-vertex/global']
                and p['zdr'] is True and p['data_collection'] == 'deny'
                and p['allow_fallbacks'] is False, 'authorized E56 route only')
        require(len(json.loads(wire['messages'][1]['content'])) == 1,
                'one item/layer per paid call')
    bound = sum((api.upper(x) for x in primary_wires + old_wires), Decimal(0))
    return original, bound


def seal_job(out, ledger, metadata, run_prefix):
    raw = out/'RAW_CALLS'
    raw.mkdir(exist_ok=True)
    pattern = re.compile(re.escape(run_prefix)+r'(?:_original)?_attempt[012]')
    for folder in sorted(ledger.iterdir()):
        if folder.is_dir() and pattern.fullmatch(folder.name):
            target = raw/folder.name
            target.mkdir(exist_ok=True)
            for p in folder.glob('*.json'):
                shutil.copy2(p, target/p.name)
    outputs = list(raw.rglob('*.response.json'))
    first = min(outputs, key=lambda p: p.stat().st_mtime_ns) if outputs else None
    evidence = None if first is None else dict(member=str(first.relative_to(out)),
        sha256=sha(first), mtime_ns=first.stat().st_mtime_ns, source='archived response file mtime')
    if (ledger/'ledger.jsonl').exists():
        shutil.copy2(ledger/'ledger.jsonl', out/'LEDGER_AT_END.jsonl')
    write(out/'JUDGMENT_SEAL.json', dict(metadata,
        first_output_utc='unknown' if first is None else datetime.fromtimestamp(
            first.stat().st_mtime, timezone.utc).isoformat(), first_output_evidence=evidence,
        files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
               if p.is_file() and p.name != 'JUDGMENT_SEAL.json'}))



def send_items(state,batch,attempt):
    io=state['io'];client=state['client'];protocol=state['protocol']
    ledger=Path(state['spec']['ledger_root']);stage_prefix=state['stage_prefix']
    require(0 <= attempt <= 2, 'unchanged validation retry count')
    values = []
    for item in batch:
        require(item==state['allowed'][item['id']], 'exact admitted original rendered group')
        if not state.get('original') and item['id'] in state.get('preserved_missing',{}):
            values.append(dict(id=item['id'],status='UNPARSEABLE',code=None,terminal_reason='UNKNOWN_REQUEST_NO_REPLAY',original_request_id=state['preserved_missing'][item['id']]))
            continue
        prefix = stage_prefix+':'+str(attempt)+':'
        io.digest = lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
        stage = stage_prefix+'_attempt'+str(attempt)
        require(time.time()<1793372400,'standing judging authority expired')
        require(not (funded_queue.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 pause')
        response = client.one(stage,[item])
        if response.get('e95_terminal_reason'):
            values.append(dict(id=item['id'],status='UNPARSEABLE',code=None,
                               terminal_reason=response['e95_terminal_reason']))
            continue
        if response['status'] == 'OK':
            values.extend(response['value'])
            continue
        path = ledger/stage/(response['id']+'.response.json')
        require(path.exists(),'transport/budget/unresolved send: stop without resend')
        raw = read(path)
        body = raw['response']
        if raw['http_status']==402:
            funded_queue.CACHE.mkdir(parents=True,exist_ok=True)
            write(funded_queue.CACHE/'PAUSED_402.json',dict(bank='E95',request_id=response['id'],http_status=402,timestamp_utc=datetime.now(timezone.utc).isoformat()))
            raise RuntimeError('HTTP402 all banks paused')
        require(not client.latch.is_set(),'transport/budget/unresolved send: stop without resend')
        if raw['http_status']==200 and body.get('provider')==protocol.PROVIDER_NAME and body.get('model')in(protocol.MODEL,protocol.MODEL+'-001') and body.get('usage',{}).get('cost')is not None and body.get('choices',[{}])[0].get('finish_reason')=='length':
            values.extend(truncated([item]));continue
        require(raw['http_status']==200 and body.get('provider')==protocol.PROVIDER_NAME
                and body.get('model') in (protocol.MODEL,protocol.MODEL+'-001')
                and body.get('usage',{}).get('cost') is not None
                and body['choices'][0].get('finish_reason')=='stop',
                'route/cost/completion failure: stop without resend')
        try:
            json.loads(body['choices'][0]['message']['content'])
        except (ValueError,TypeError):
            values.extend(e87_classify([item],{}))
            continue
        raise RuntimeError('unexpected transport failure; no scientific retry')
    return values

def worker_channel(spec, *, original=False):
    """Fresh-process initialization; uses the same admission/wire/ledger/send."""
    import os
    from .judging_workers import shared_context,patch_api as staged_patch
    verify_adapter(spec)
    items,old_ids=admission(spec)
    require(sha(spec['route'])==spec['route_sha256'],'same existing pinned route')
    route=read(spec['route'])
    for name in ('api','privacy','protocol','io'):
        p=str(Path(route['e10_source'])/(name+'.py'))
        require(sha(p)==route['files'][p],'existing E10 implementation unchanged')
    api,privacy,protocol,io=route_modules(route)
    items,_=e87.redact_groups(items)
    old,_=calls_and_bound(items,old_ids,api,protocol)
    active=e87.ORIGINAL.read_text()if original else e87.RUBRIC.read_text()
    chosen=old if original else items
    budget=read(spec['budget_receipt']);api.CAP=Decimal(str(budget['E95_allocation_usd']))
    stack=ExitStack();stack.enter_context(shared_context(spec))
    stack.enter_context(paid_window(api,pauses=[funded_queue.CACHE/'PAUSED_402.json']))
    ledger=Path(spec['ledger_root']);io.CACHE=ledger/'route_spawn'/str(os.getpid());io.CACHE.mkdir(parents=True,exist_ok=True)
    require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'existing account privacy proof')
    shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
    original_privacy=privacy.check_wire
    protocol.payload=lambda stage,batch,unused=None:e87.wire(batch,protocol,active)
    protocol.validate=lambda stage,response,batch,unused=None:e87_classify(batch,response)
    privacy.check_wire=lambda stage,batch,body,unused=None:check_decoded(original_privacy,batch,body)
    staged_patch(api,io,'E95',interval=spec['request_interval_seconds'])
    client=api.Client(ledger,os.environ['OPENROUTER_API_KEY'])
    return dict(io=io,client=client,protocol=protocol,privacy=privacy,spec=spec,
        allowed={x['id']:x for x in chosen},original=original,
        preserved_missing=spec.get('preserved_missing',{}),contexts=stack,
        stage_prefix='E95_'+spec['packet_seal_sha256'][:16]+('_original'if original else''))


def execute(spec, *, key=None, preflight=True):
    # Admission also checks the frozen sample, rubric, source custody and budget.
    verify_adapter(spec)
    items, original_ids = admission(spec)
    require(sha(spec['route']) == spec['route_sha256'], 'pinned existing E56 route')
    route = read(spec['route'])
    for name in ('api', 'privacy', 'protocol', 'io'):
        p = str(Path(route['e10_source'])/(name+'.py'))
        require(sha(p) == route['files'][p], 'existing E10 implementation unchanged')
    api, privacy, protocol, io = route_modules(route)
    items, audit = e87.redact_groups(items)
    original_rubric = e87.ORIGINAL.read_text()
    original, bound = calls_and_bound(items, original_ids, api, protocol)
    require(abs(bound - Decimal(str(spec['first_pass_worst_case_usd']))) <= Decimal('.00000001'),
            'sealed full initial-pass bound matches exact wires')
    budget = read(spec['budget_receipt'])
    budget_gate(budget, bound)
    if spec.get('parallel_workers'):
        require(spec.get('judging_stage') in (1,2,3) and spec['parallel_workers']==2
                and spec['request_interval_seconds']>=5,'registered staged isolated workers/rate')
    if preflight:
        return dict(bank='E95', primary_calls=len(items), original_calls=len(original),
                    first_pass_upper_usd=str(bound), inference_calls=0)
    require(bool(key), 'integrator credential required')
    protected_parallel=(spec.get('judging_stage')in(1,2,3)
        and spec.get('parallel_workers')==2 and spec.get('request_interval_seconds',0)>=5
        and budget.get('parallel_priority_protected')is True
        and budget.get('parallel_authority')=='b1ba81c12f65194d85659084d66830de2d5190aa')
    require(0<=time.time()-budget['issued_epoch']<=300
            and (budget.get('higher_priority_banks_cleared')is True or protected_parallel),
            'fresh integrator global-budget and registered priority protection for E95')
    require(time.time()<1793372400,'standing judging authority expired')
    require(not (funded_queue.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 pause')
    ledger = Path(spec['ledger_root'])
    require(ledger.name == 'e95_60usd', 'separate E95 ledger namespace')
    out = Path(spec['out'])
    require(not out.exists(), 'never overwrite a prior E95 dispatch')
    ledger.mkdir(parents=True, exist_ok=True)
    from .judging_workers import shared_context
    shared=shared_context(spec) if spec.get('parallel_workers') else nullcontext()
    with dispatch_lock(ledger/'DISPATCH.lock'), shared, paid_window(api,pauses=[funded_queue.CACHE/'PAUSED_402.json']):
        require(not out.exists(), 'prior dispatch appeared while waiting for lock')
        saved = (api.CAP, protocol.payload, protocol.validate, privacy.check_wire, io.digest, io.CACHE)
        original_one=api.Client.one
        if spec.get('parallel_workers'):
            from .judging_workers import patch_api as staged_patch
            staged_patch(api,io,'E95',interval=spec['request_interval_seconds'])
        else:
            patch_api(api,io,'E95')
        api.CAP = Decimal(str(budget['E95_allocation_usd']))
        active_rubric = e87.RUBRIC.read_text()
        stage_prefix = 'E95_'+spec['packet_seal_sha256'][:16]
        run_prefix = stage_prefix
        original_privacy = privacy.check_wire
        client = None
        owns_output = False
        try:
            io.CACHE = ledger/'route'
            io.CACHE.mkdir(exist_ok=True)
            require(sha(route['privacy_proof']) == route['privacy_proof_sha256'], 'existing privacy proof')
            shutil.copyfile(route['privacy_proof'], io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
            route_audit=privacy.check_route(key)
            protocol.payload = lambda stage,batch,unused=None:e87.wire(batch,protocol,active_rubric)
            protocol.validate = lambda stage,response,batch,unused=None:e87_classify(batch,response)
            def check(stage,batch,body,unused=None):
                require(all(set(x)=={'id','rubric','positions'} for x in batch), 'blind wire only')
                check_decoded(original_privacy,batch,body)
            privacy.check_wire = check
            client = api.Client(ledger,key)
            require(Decimal(client.ledger.summary()['committed_usd'])+bound <= api.CAP,
                    'initial pass plus prior actual/unresolved spend fits E95 allocation')
            if 'judging_stage' in spec:
                from .judging_stages import claim,continuation
                if spec.get('continuation'):
                    continuation(spec,items,api,protocol,io)
                else:
                    claim(ledger, spec['judging_stage'], spec['packet_seal_sha256'], out)
            out.mkdir(parents=True)
            owns_output = True
            write(out/'START.json',dict(bank='E95',packet_seal_sha256=spec['packet_seal_sha256'],
                index_sha256=spec['index_sha256'],source_seal_sha256=spec['source_seal_sha256'],
                route_sha256=spec['route_sha256'],first_pass_upper_usd=str(bound)))
            write(out/'PATH_REDACTION_AUDIT.json',audit)
            state=dict(io=io,client=client,protocol=protocol,spec=spec,allowed={x['id']:x for x in items},original=False,preserved_missing=spec.get('preserved_missing',{}))
            def send(batch,attempt):
                state['stage_prefix']=stage_prefix
                return send_items(state,batch,attempt)
            def judged(batch,label):
                live={}
                started=time.time()
                def observer(rows,attempt):
                    for row in rows:live[row['id']]=row
                    write(out/('PROGRESS_'+label+'.json'),dict(at_epoch=time.time(),
                        started_epoch=started,processed_groups=len(live),total_groups=len(batch),
                        kept=sum(x['status']=='KEPT' for x in live.values()),
                        missing_or_pending=sum(x['status']!='KEPT' for x in live.values()),
                        cost=client.ledger.summary()))
                if spec.get('parallel_workers'):
                    from .judging_workers import parallel_judge
                    return parallel_judge(batch,send,judge,spec['parallel_workers'],observer,spec=spec,original=label=='ORIGINAL')
                return judge(batch,send)
            terminal = judged(items,'PRIMARY')
            write(out/'JUDGMENTS.json',terminal)
            active_rubric = original_rubric
            stage_prefix += '_original'
            state.update(original=True,allowed={x['id']:x for x in original})
            old_terminal = judged(original,'ORIGINAL')
            write(out/'ORIGINAL_JUDGMENTS.json',old_terminal)
            from .judging_workers import cost_summary
            accounting=cost_summary(client)
            write(out/'COUNTS.json',dict(n=len(terminal),original_n=len(old_terminal),
                kept=sum(x['status']=='KEPT' for x in terminal),
                unparseable=sum(x['status']=='UNPARSEABLE' for x in terminal),cost=accounting))
            seal_job(out,ledger,dict(experiment='E95',status='TERMINAL_BLIND_GRID_NO_ANALYSIS',
                judging_stage=spec.get('judging_stage'),
                packet_seal_sha256=spec['packet_seal_sha256'],index_sha256=spec['index_sha256'],
                source_seal_sha256=spec['source_seal_sha256'],route_sha256=spec['route_sha256'],stage_inventory_sha256=spec.get('stage_inventory_sha256'),validator='validator221.e87_classify',route_audit=route_audit,
                route_verified=True,redaction_audit_complete=True,cost=accounting),run_prefix)
            if 'judging_stage'in spec:
                from .judging_stages import complete
                complete(ledger,spec['judging_stage'],out)
            return read(out/'COUNTS.json')
        except BaseException as error:
            if owns_output:
                write(out/'BLOCKED.json',dict(error_type=type(error).__name__,resend=False,
                    cost=None if client is None else client.ledger.summary()))
                seal_job(out,ledger,dict(experiment='E95',status='BLOCKED_PARTIAL_NO_ANALYSIS',
                    packet_seal_sha256=spec['packet_seal_sha256']),run_prefix)
            raise
        finally:
            api.Client.one=original_one
            api.CAP,protocol.payload,protocol.validate,privacy.check_wire,io.digest,io.CACHE = saved


def main():
    import argparse,os
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    spec=read(a.spec)
    print(json.dumps(execute(spec,key=os.environ.get('OPENROUTER_API_KEY')if a.run else None,preflight=not a.run),sort_keys=True))

if __name__=='__main__':main()
