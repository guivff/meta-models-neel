"""Read-only sealed D4/E73 loader. Private joins stay in memory; no output writes.

Use python -B to prevent bytecode writes outside discovery2. Never serialize the
returned records: truth, pairing identifiers and source input are private context.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

BASE = Path('/Users/guivff/Documents/ChatGPT/Activation_Readers')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_d4_records():
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(BASE / 'wt-wtext/results/g_agreement/understand/e67'))
    from sources67 import Ledger, load_d4
    pools = load_d4(Ledger())  # verifies the existing once-analysis and stage seals
    result = []
    files = {}
    for (_, reader), rows in pools.items():
        for x in rows:
            src = x['source']
            if src['path'] not in files:
                files[src['path']] = read(src['path'])
            raw = files[src['path']][src['record_index_zero_based']]
            result.append(dict(bank='E61_D4', reader=reader,
                opaque_id=hashlib.sha256(('D4|' + reader + '|' + x['item_id']).encode()).hexdigest()[:16],
                pair_id=hashlib.sha256(('D4|' + x['item_id']).encode()).hexdigest()[:16],
                text=x['readout'], prompt_text=x['prompt_text'], arm=x['arm'],
                position=raw['position'], judge=None))
    assert len(result) == 504
    return result


def load_e73_records():
    root = BASE / 'wt-i2'
    public = root / 'results/g_agreement/i2'
    completion = read(public / 'E73_ONCE_ANALYSIS_COMPLETION.json')
    planpath = public / 'E73_ONCE_ANALYSIS_INPUT_PLAN.json'
    sealpath = public / 'E73_ONCE_ANALYSIS_SEAL.json'
    assert completion['status'] == 'COMPLETE' and completion['analysis_invocations'] == 1
    assert sha(planpath) == completion['plan_sha256']
    assert sha(sealpath) == completion['analysis_seal_sha256']
    plan = read(planpath)
    seal = read(sealpath)
    assert seal['status'] == 'COMPLETE'
    for name, entry in seal['files'].items():
        assert sha(Path(plan['output']) / name) == entry['sha256']

    def bound(path):
        path = Path(path)
        assert sha(path) == plan['input_bindings'][str(path)]
        return read(path)

    result = []
    for bank in plan['banks']:
        spec = bound(bank['builder_spec'])
        wire = bound(bank['judge_wire'])  # authorised redacted copy, never raw unsafe text
        judges = {x['id']: x for x in bound(bank['terminal_path'])}
        joinpath = Path(spec['out']).parent / 'private/JOIN_MAP.json'
        mapping = {x['opaque_id']: x for x in bound(joinpath)}
        itempath = Path(spec['items'])
        assert sha(itempath) == plan['input_bindings'][str(itempath)]
        inputs = {x['id']: x['input_ids'] for x in map(json.loads, itempath.read_text().splitlines())}
        for x in wire:
            m = mapping[x['id']]
            rubric = x['rubric']
            values = re.search(r'\nProperty: (.*?)\nA: (.*?)\nB: (.*?)\n', rubric, re.S)
            assert values
            result.append(dict(bank='E73', cohort=bank['name'], reader=m['reader'],
                opaque_id=x['id'], text=x['readout'], row=m['state'],
                property=values[1], value_descriptions=[values[2], values[3]],
                judge=judges[x['id']], input_ids=inputs[m['source_id']],
                pair_id=hashlib.sha256(('E73|' + m['state'] + '|' + m['source_id']).encode()).hexdigest()[:16],
                _truth=m['label'], truncated=m['truncated']))
    assert len(result) == 2800
    return result


if __name__ == '__main__':
    from collections import Counter
    print('D4 aggregate:', dict(Counter(x['reader'] for x in load_d4_records())))
    print('E73 aggregate:', dict(Counter(x['reader'] for x in load_e73_records())))
