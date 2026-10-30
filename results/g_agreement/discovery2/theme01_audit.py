"""Aggregate-only reproducibility check; invoke with PYTHONDONTWRITEBYTECODE=1."""
import json
import re
from collections import Counter
from evidence_native import load_native, read, RESULTS


def summarize(rows):
    kept = [x for x in rows if x['judge'] and x['judge'].get('category') != 'UNPARSEABLE']
    counts = Counter(x['judge'].get('category') for x in kept)
    correct = wrong = 0
    for x in kept:
        values = set(x['judge'].get('values', [])) if x['judge'].get('category') == 'states_value' else set()
        correct += values == {x['_truth']}
        wrong += bool(values) and len(values) == 1 and x['_truth'] not in values
    return dict(n=len(rows), parseable=len(kept), correct=correct, wrong=wrong,
                signed=(correct-wrong)/len(kept), categories=dict(counts))


def main():
    rows = {b: load_native(b, True) for b in ['E49', 'E56', 'E57', 'E59', 'E62']}
    result = {}
    for bank in ['E56', 'E57']:
        result[bank] = {}
        for feature in sorted({x['feature'] for x in rows[bank] if x['kind'] == 'text'}):
            for reader in ['oracle', 'nla']:
                group = [x for x in rows[bank] if x['feature'] == feature and x['reader'] == reader]
                result[bank][feature+'|'+reader] = summarize(group)
    regex = re.compile(r'\bx\s+(?:is|becomes)(?:\s+now)?\s+(?:a\s+)?(?:string|int(?:eger)?)\b', re.I)
    result['E49_type_wording'] = {
        r: sum(bool(regex.search(x['text'])) for x in rows['E49'] if x['reader']==r and x['feature']=='var_type_at_use')
        for r in ['oracle', 'nla']}
    for bank in ['E59', 'E62']:
        dirname = 'analysis5968_once_2026-10-27' if bank=='E59' else 'analysis402_once_2026-10-27'
        aggregate = read(RESULTS/bank.lower()/dirname/'RESULTS.json')['rates']
        for key, sealed in aggregate.items():
            reader,feature = key.split('|')[:2]
            observed=summarize([x for x in rows[bank] if x['reader']==reader and x['feature']==feature])
            assert abs(observed['signed']-sealed['S'])<1e-12
        result[bank+'_sealed_rate_checks']=len(aggregate)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
