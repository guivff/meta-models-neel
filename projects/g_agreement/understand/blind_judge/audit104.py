"""§223 addition: read-only E104 terminal-missingness audit, no API imports."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from .audit223 import functions, rejection
from projects.g_agreement.readerbench.io import read, sha, write, verify
from projects.g_agreement.readerbench.scoring import require

ROOT = Path(__file__).resolve().parents[4]
CACHE = ROOT / 'cache/g_agreement/understand/funded_queue/E104'
SOURCE = ROOT / 'results/g_agreement/understand/blind_judge/e104_bank/SOURCE_SEAL.json'
SOURCE_SHA = 'cb79daa7228dcf5d6aec0fd15fe6a395927564776acb4dc639398d5bb9ec84bd'


def environment():
    require(sha(SOURCE) == SOURCE_SHA, 'executed E104 source seal')
    for n, h in read(SOURCE)['files'].items():
        require(sha(ROOT / n) == h, 'executed source member ' + n)
    scoring = (ROOT / 'projects/g_agreement/readerbench/scoring.py').read_text()
    env = dict(re=re, unicodedata=unicodedata, __name__='sealed_offline_e104')
    for node in ast.parse(scoring).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('E56', 'D5'):
            env[node.targets[0].id] = ast.literal_eval(node.value)
    functions(scoring, ['require', 'validate_judgments'], env)
    functions((ROOT / 'projects/g_agreement/understand/blind_judge/later_runner.py').read_text(), ['normalize', 'classify'], env)
    return env


def audit():
    env = environment()
    job = CACHE / 'judgments'
    seal = read(job / 'JUDGMENT_SEAL.json')
    require(seal['source_seal_sha256'] == SOURCE_SHA and seal['route_verified'] and seal['redaction_audit_complete'], 'strict route/privacy/source binding')
    for n, h in seal['files'].items():
        require(sha(job / n) == h, 'strict E104 member ' + n)
    blind = verify(CACHE / 'blind/BLIND_SEAL.json', seal['blind_seal_sha256'])
    require(sha(CACHE / 'PRIVATE.json') == blind['private_sha256'], 'LOCAL join binding')
    route = read(job / 'ROUTE_AUDIT.json')
    raw = {x['request_id']: x['response_sha256'] for x in route['requests']}
    rows = read(job / 'TERMINAL.json')
    missing = [x for x in rows if x['status'] == 'UNPARSEABLE']
    require(len(rows) == 336 and len(missing) == 10, 'complete strict missingness inventory')
    copies = {x['id']: x for x in read(job / 'JUDGE_COPY.json')}
    details = []
    for row in missing:
        require(row['attempts'] == 2, 'selected final strict attempt')
        stage = 'E104_attempt2'
        candidates = []
        for rp in (CACHE / 'ledger' / stage).glob('*.response.json'):
            rid = rp.name.removesuffix('.response.json')
            require(raw.get(rid) == sha(rp), 'original sealed route audit/raw response binding')
            qp = rp.with_name(rid + '.request.json')
            wire = read(qp)['wire']
            canonical = json.dumps(wire, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
            require(hashlib.sha256((stage + ':' + seal['blind_seal_sha256'] + ':' + canonical).encode()).hexdigest() == rid, 'original wire identity')
            items = json.loads(wire['messages'][1]['content'])
            for item in items:
                require(copies[item['id']] == item, 'exact original judge copy')
                if item['id'] == row['id']:
                    candidates.append((rp, qp, rid, item))
        require(len(candidates) == 1, 'one final selected response per missing ID')
        rp, qp, rid, item = candidates[0]
        saved = read(rp)
        body = saved['response']
        choice = body['choices'][0]
        require(saved['http_status'] == 200 and choice['finish_reason'] == 'stop' and body['provider'] == 'Google'
                and body['model'] in ('google/gemini-3.1-flash-lite', 'google/gemini-3.1-flash-lite-001'), 'actual completed pinned response')
        value = json.loads(choice['message']['content'])
        reason, facts = rejection('E81', item, value, env)  # same frozen generic E56 schema
        require(env['classify']([item], value, 'E56')[0]['status'] != 'KEPT' and reason != 'VALID_REJECTED_BY_PIPELINE', 'reproduced strict rejection')
        details.append(dict(id=row['id'], attempt=2, request_id=rid, request_sha256=sha(qp), response_sha256=sha(rp),
                            reason=reason, facts=facts, http_status=200, finish_reason='stop'))
    # Reconcile the registered missing-cohort caveat CPU-side without reading
    # targets, candidate values, readout text, or correctness labels.
    ids = {x['id'] for x in missing}
    cohorts = Counter()
    flipped_steered = 0
    for item in read(CACHE / 'PRIVATE.json'):
        if item['opaque_id'] in ids:
            cohorts[(item['row'], item['condition'])] += 1
            if item['row'] == 'language_plan' and item['condition'] == 'steered' and item['flipped'] is True:
                flipped_steered += 1
    return dict(status='COMPLETE_NO_APPLICABLE_VALIDATOR_DEFECT', bank='E104', total_records=336, terminal_missing=10,
                counts=dict(Counter(x['reason'] for x in details)), details=details,
                missing_cohorts=[dict(row=k[0], condition=k[1], count=v) for k, v in sorted(cohorts.items())],
                language_plan_steered_flipped_cohort_missing=flipped_steered,
                strict_judgment_seal_sha256=sha(job / 'JUDGMENT_SEAL.json'), source_seal_sha256=SOURCE_SHA,
                blind_seal_sha256=seal['blind_seal_sha256'], local_private_join_sha256=blind['private_sha256'],
                strict_ledger_sha256=sha(CACHE / 'ledger/ledger.jsonl'), new_calls=0, judgments_changed=False, analysis_reruns=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    args.out.mkdir(parents=True, exist_ok=False)
    write(args.out / 'E104_AUDIT.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'details'}, indent=2))
