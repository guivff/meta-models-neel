"""67d3b46d: per-record validation, narrowly normalized evidence, bounded retries."""
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from .run import ROOT, CACHE, route_modules
from projects.g_agreement.readerbench.io import read, write, sha, verify, seal_output
from projects.g_agreement.readerbench.scoring import validate_judgments, require

HERE = ROOT/'results/g_agreement/understand/blind_judge/clarification2'
QUOTES = dict.fromkeys('‘’‚‛', "'") | dict.fromkeys('“”„‟«»', '"')


def normalize(text):
    # No accent folding, punctuation deletion, stemming, fuzzy matching or repair.
    text = ''.join(QUOTES.get(c, '-' if unicodedata.category(c) == 'Pd' else c) for c in text)
    return re.sub(r'\s+', ' ', text).strip().casefold()


def valid(item, code, taxonomy):
    p, c = dict(item), dict(code)
    p['readout'] = normalize(p['readout'])
    if isinstance(c.get('evidence'), str):
        c['evidence'] = normalize(c['evidence'])
    validate_judgments([p], [c], taxonomy)
    return True


def passes(item, code, taxonomy, normalized=True):
    try:
        if normalized:
            valid(item, code, taxonomy)
        else:
            validate_judgments([item], [code], taxonomy)
        return True, None
    except (ValueError, KeyError, TypeError) as exc:
        return False, str(exc)


def first_pass():
    paid = CACHE/'shared_10usd_ledger'
    records = []
    for job, taxonomy in [('D5_E49', 'D5'), ('E54', 'E56')]:
        for path in sorted((paid/job).glob('*.request.json')):
            ident = path.name.removesuffix('.request.json')
            wire = read(path)['wire']
            items = json.loads(wire['messages'][1]['content'])
            response = read(path.with_name(ident+'.response.json'))['response']
            codes = json.loads(response['choices'][0]['message']['content'])['records']
            indexed = {x['id']: x for x in codes}
            require(len(indexed) == len(codes) == len(items) and set(indexed) == {x['id'] for x in items}, 'first-pass ID grid')
            for item in items:
                code = indexed[item['id']]
                old_ok, old_reason = passes(item, code, taxonomy, False)
                ok, reason = passes(item, code, taxonomy)
                require(ok or not old_ok, 'normalization unexpectedly invalidated a formerly valid record')
                records.append(dict(job=job, taxonomy=taxonomy, item=item, code=code, wire=wire,
                                    old_valid=old_ok, valid=ok, reason=reason, attempts=0))
    require(len(records) == 840 and sum(not r['old_valid'] for r in records) == 46, 'original inventory')
    require(len({(r['job'], r['item']['id']) for r in records}) == 840, 'unique opaque IDs')
    return records


def singleton_wire(record):
    wire = copy.deepcopy(record['wire'])
    # Preserve original rubric, prompt template and generation settings. Only batch size changes.
    item = {k: v for k, v in record['item'].items() if k in ('id', 'rubric', 'readout')}
    wire['messages'][1]['content'] = json.dumps([item], ensure_ascii=False)
    return wire


def main():
    plan = read(HERE/'PLAN.json')
    for name, digest in plan['files'].items():
        require(sha(name) == digest, 'clarification2 source changed')
    allocation = Path(plan['allocation_path'])
    require(sha(allocation) == plan['allocation_sha256'], 'allocation hash')
    committed = subprocess.check_output(['git', '-C', plan['integrator_repo'], 'show',
        plan['allocation_commit']+':results/g_agreement/r/JUDGE_ALLOCATION_D5_E54_2026-10-27.json'])
    require(hashlib.sha256(committed).hexdigest() == sha(allocation), 'committed allocation bytes')
    budget = read(allocation)
    require(budget['issuer'] == 'integrator' and budget['status'] == 'ALLOCATED' and
            set(budget['jobs']) == {'D5_E49', 'E54'} and Decimal(budget['cap_usd_total']) == 5 and
            Decimal(budget['inside_daily_ceiling_usd']) == 150, 'allocated budget/scope')
    verify(CACHE/'CUSTODY_2026-10-27/RESULT_SEAL.json', plan['first_pass_custody_sha256'])
    for name, digest in read(CACHE/'CUSTODY_2026-10-27/RAW_RESPONSE_HASHES.json').items():
        require(sha(CACHE/name) == digest, 'first-pass raw evidence changed')
    records = first_pass()
    out = CACHE/'clarification2'
    out.mkdir(exist_ok=False)
    write(out/'REVALIDATED_FIRST_PASS.json', [
        {k: r[k] for k in ('job', 'item', 'code', 'old_valid', 'valid', 'reason')} for r in records])
    pending = [r for r in records if not r['valid']]
    write(out/'RETRY_INVENTORY.json', [{'job': r['job'], 'id': r['item']['id'], 'reason': r['reason']} for r in pending])
    seal_output(out, {'status': 'FIRST_PASS_REVALIDATED_BEFORE_RETRY', 'authority': '67d3b46d'})
    route = read(ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    api, privacy, protocol, io = route_modules(route)
    api.CAP = Decimal('5')
    key = os.environ.get('OPENROUTER_API_KEY')
    require(bool(key), 'credential unavailable')
    io.CACHE.mkdir(exist_ok=True)
    require(sha(route['privacy_proof']) == route['privacy_proof_sha256'], 'privacy proof binding')
    shutil.copyfile(route['privacy_proof'], io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
    privacy.check_route(key)
    original_check = privacy.check_wire
    privacy.check_wire = lambda stage, items, wire, taxonomy=None: original_check('extract',
        [{'id': x['id'], 'readout': json.dumps(x)} for x in items], wire)
    client = api.Client(CACHE/'shared_10usd_ledger', key)
    total_reserve = sum((2*api.upper(singleton_wire(r)) for r in pending), Decimal(0))
    require(Decimal(client.ledger.summary()['committed_usd'])+total_reserve <= 5, 'retry worst case exceeds shared cap')
    summary = Counter()
    for r in records:
        summary[(r['job'], 'kept_before_retry')] += int(r['valid'])
    for r in pending:
        wire = singleton_wire(r)
        item = json.loads(wire['messages'][1]['content'])[0]
        protocol.payload = lambda stage, items, taxonomy=None, w=wire: w
        def validate(stage, result, items, taxonomy=None, tax=r['taxonomy']):
            require(set(result) == {'records'} and len(result['records']) == 1, 'single-record response required')
            valid(items[0], result['records'][0], tax)
            return result['records']
        protocol.validate = validate
        for attempt in (1, 2):
            # Distinct accounting ID per authorized attempt; request bytes remain unchanged.
            prefix = 'clarification2:'+r['job']+':'+r['item']['id']+':'+str(attempt)+':'
            io.digest = lambda value, prefix=prefix: hashlib.sha256((prefix+value).encode()).hexdigest()
            result = client.one('clarification2_'+r['job']+'_attempt'+str(attempt), [item])
            require(result.get('reason') != 'BUDGET_UNSENT', 'budget admission failed')
            r['attempts'] += 1
            if result['status'] == 'OK':
                r['code'] = result['value'][0];r['valid'] = True;r['reason'] = None
                break
            r['reason'] = result.get('reason')
            if client.latch.is_set():
                raise RuntimeError('transport/account/route latch; stop further inference')
        print(json.dumps({'job': r['job'], 'finished_retry_records': sum(x['attempts'] > 0 for x in records),
                          'pending_records': len(pending), 'cost': client.ledger.summary()}), flush=True)
    final = [{k: r[k] for k in ('job', 'item', 'code', 'old_valid', 'valid', 'reason', 'attempts')} for r in records]
    write(out/'FINAL_RECORDS.json', final)
    # Seal all accepted/UNPARSEABLE terminal decisions before opening the private row key.
    terminal = out/'terminal';terminal.mkdir()
    write(terminal/'JUDGMENTS.json', [{'job': r['job'], 'id': r['item']['id'],
        'status': 'KEPT' if r['valid'] else 'UNPARSEABLE', 'code': r['code'] if r['valid'] else None,
        'attempts': r['attempts']} for r in records])
    shutil.copyfile(client.root/'ledger.jsonl', terminal/'LEDGER.jsonl')
    write(terminal/'API_HASHES.json', {str(p.relative_to(CACHE)): sha(p)
        for folder in client.root.glob('clarification2_*') for p in sorted(folder.iterdir()) if p.is_file()})
    seal_output(terminal, {'status': 'TERMINAL_GRID_SEALED_BEFORE_ROW_JOIN', 'authority': '67d3b46d'})
    private = read(ROOT/route['jobs']['D5_E49']['key'])
    row_map = {x['opaque_id']: x['row'] for x in private}
    counts = defaultdict(Counter)
    for r in records:
        if r['job'] == 'D5_E49':
            row = row_map[r['item']['id']]
        else:
            rubric = r['item']['rubric']
            row = 'reasoning_bridge' if 'intermediate animal as cat or dog' in rubric else 'injection_awareness'
            require(row == 'reasoning_bridge' or 'directly from the user or quoted tool output' in rubric, 'frozen E54 target definition')
        c = counts[(r['job'], row)]
        c['total'] += 1;c['kept'] += int(r['valid']);c['kept_before_retry'] += int(r['attempts'] == 0)
        c['retried'] += int(r['attempts'] > 0);c['retry_requests'] += r['attempts'];c['UNPARSEABLE'] += int(not r['valid'])
    report = {'authority': '67d3b46d', 'status': 'VALIDATION_AND_RETRIES_COMPLETE',
        'rows': [dict(job=k[0], row=k[1], **dict(v)) for k,v in sorted(counts.items())],
        'cost': client.ledger.summary(), 'terminal_seal_sha256': sha(terminal/'RESULT_SEAL.json'),
        'category_share_analyses': 0, 'E54_private_key_opened': False}
    write(HERE/'COUNTS.json', report)
    seal_output(HERE, {'status': 'COMPLETE_OPERATIONAL_VALIDATION', 'authority': '67d3b46d'})
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
