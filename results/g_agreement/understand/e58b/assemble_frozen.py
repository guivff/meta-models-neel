"""Copy and join frozen banks; no generation, fitting, inference or scoring."""
import argparse
import shutil
import subprocess
from pathlib import Path
from common58 import *
from cpu_join58 import validate_labeled_bank as validate_bank, pca_population

E56_COMMIT = 'dad90763c4bb0e0ab62e042eacd70681a61277c7'
E57_COMMIT = 'b55c19426ae2de1d55840f0ee7fec98e920fa644'
E56_SEAL = 'e733bed854700d0129a7b59ed1e1e6ddf82947add11c2f3e77feb36bfb451112'
E57_SEAL = 'cff66637fedd6afd795370e3efbe3e8262d77c98a64e60e8580a9507dd295f7c'
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def assemble(tokenizer_path):
    from tokenizers import Tokenizer
    require(not (CACHE / 'WORKER.RUN_ONCE.json').exists(), 'Cannot assemble after a model invocation')
    require(sha(tokenizer_path) == TOKENIZER_SHA, 'Exact frozen tokenizer bytes required')
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    def encode(text):
        return tokenizer.encode(text, add_special_tokens=False).ids
    wtext = ROOT.parent / 'wt-wtext'
    wmech = ROOT.parent / 'wt-wmech'
    internals = ROOT.parent / 'wt-blindspot-internals'
    oldw1 = ROOT.parent / 'blindspot-worktree/cache/g_agreement/blindspot/w1-bank'
    delivery = CACHE / 'delivery'
    delivery.mkdir(parents=True, exist_ok=False)
    sources = {}

    def copy(name, source, expected=None):
        # APFS aliases path case; the sealed archive must also work on Linux.
        name = name.replace('sources/E56/', 'sources/e56/').replace('sources/E57/', 'sources/e57/')
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Relative staging path required')
        if expected is not None:
            require(sha(source) == expected, 'Frozen source bytes differ')
        dest = delivery / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        sources[name] = sha(dest)
        return sources[name]

    def bank_source(exp, commit, expected):
        directory = wtext / f'results/g_agreement/understand/{exp}/cache/bank_2026-10-27_v1'
        path = directory / 'BANK_SEAL.json'
        original = subprocess.check_output(['git', '-C', str(wtext), 'show',
            commit + f':results/g_agreement/understand/{exp}/BANK_SEAL.json'])
        require(hashlib.sha256(original).hexdigest() == expected == sha(path), 'Requested commit/seal mismatch')
        copy(f'sources/{exp}/BANK_SEAL.json', path, expected)
        record = read(path)
        for name, expected_file in record['files'].items():
            copy(f'sources/{exp}/' + name, directory / name, expected_file)
        return read(directory / 'items.PRIVATE.json'), record

    e56, seal56 = bank_source('e56', E56_COMMIT, E56_SEAL)
    e57, seal57 = bank_source('e57', E57_COMMIT, E57_SEAL)
    annotations = read(delivery / 'sources/e57/ANNOTATIONS.PRIVATE.json')
    e57_definitions = read(delivery / 'sources/e57/DEFINITIONS.json')
    # Full W1 source is exactly the item file already bound by E15.
    e15 = read(HERE.parent / 'e15/plan.json')
    # Private labels/items were deliberately absent from the staged INPUT_SEAL;
    # E15's committed plan separately binds the full private item-file hash.
    require(sha(oldw1 / 'items.DO_NOT_STAGE.jsonl') == e15['W1_full_items_sha256'], 'E15/W1 item lineage mismatch')
    copy('sources/E15/plan.json', HERE.parent / 'e15/plan.json')
    copy('sources/W1/INPUT_SEAL.json', oldw1 / 'INPUT_SEAL.json')
    copy('sources/W1/items.jsonl', oldw1 / 'items.DO_NOT_STAGE.jsonl', e15['W1_full_items_sha256'])
    w1 = jsonl(oldw1 / 'items.DO_NOT_STAGE.jsonl')
    pair15 = HERE.parent / 'e15/CONTINUATION_PAIRS.json'
    pair15_sha = copy('sources/E15/CONTINUATION_PAIRS.json', pair15,
        e15['source_files']['results/g_agreement/understand/e15/CONTINUATION_PAIRS.json'])
    pairs15 = read(pair15)['rows']
    w1values = e15['values']
    # E36 keeps its own full frozen prompts/labels, with the same frozen E15 pairs.
    d36 = wtext / 'results/g_agreement/understand/e36/cache/v2_25_2026-10-25'
    prepared36 = read(d36 / 'PREPARED_SEAL.json')
    for name in ('items.input.jsonl', 'labels.DO_NOT_STAGE.jsonl'):
        copy('sources/E36/' + name, d36 / name, prepared36['files'][name])
    copy('sources/E36/PREPARED_SEAL.json', d36 / 'PREPARED_SEAL.json')
    e36 = jsonl(d36 / 'items.input.jsonl')
    labels36 = {x['id']: x['value'] for x in jsonl(d36 / 'labels.DO_NOT_STAGE.jsonl')}
    defs36 = read(wtext / 'results/g_agreement/understand/e36/ROW_DEFINITIONS.json')
    copy('sources/E36/ROW_DEFINITIONS.json', wtext / 'results/g_agreement/understand/e36/ROW_DEFINITIONS.json')
    # E53's committed item-wise pairs, not its reader scores or captures.
    e49dir = wtext / 'results/g_agreement/understand/e49/cache/frozen_2026-10-26'
    e49seal = read(e49dir / 'BANK_SEAL.json')
    copy('sources/E49/BANK_SEAL.json', e49dir / 'BANK_SEAL.json')
    copy('sources/E49/items.PRIVATE.json', e49dir / 'items.PRIVATE.json', e49seal['files']['items.PRIVATE.json'])
    e49 = read(e49dir / 'items.PRIVATE.json')
    pair53 = internals / 'results/g_agreement/understand/e5354/CONTINUATION_PAIRS.json'
    original53 = subprocess.check_output(['git', '-C', str(internals), 'show',
        'cdafe376bfd7eb7a2cfc96955b8f43d9faab35e5:results/g_agreement/understand/e5354/CONTINUATION_PAIRS.json'])
    require(hashlib.sha256(original53).hexdigest() == sha(pair53), 'Committed E53 pair bytes required')
    pair53_sha = copy('sources/E53/CONTINUATION_PAIRS.json', pair53)
    pairs53 = read(pair53)
    pair56 = wmech / 'results/g_agreement/understand/e56/job/CONTINUATIONS.json'
    original56 = subprocess.check_output(['git', '-C', str(wmech), 'show',
        'c4ac59e1e5c9e789d37648dd47d21ee96bf9e4c2:results/g_agreement/understand/e56/job/CONTINUATIONS.json'])
    require(hashlib.sha256(original56).hexdigest() == sha(pair56), 'Committed E56 pair bytes required')
    pair56_sha = copy('sources/E56/CONTINUATIONS.json', pair56)
    pairs56 = read(pair56)
    pair57_sha = copy('sources/E57/CONTINUATION_FREEZE.json', HERE / 'E57_CONTINUATION_FREEZE.20261027.json')
    pair57 = read(HERE / 'E57_CONTINUATION_FREEZE.20261027.json')
    cats = wtext / 'results/g_agreement/understand/e58a'
    cat_manifest = read(cats / 'CATEGORY_MANIFEST_V3.json')
    category_sha = copy('sources/categories/CATEGORY_MANIFEST_V3.json', cats / 'CATEGORY_MANIFEST_V3.json')
    categories = {}
    for name, expected in cat_manifest['assignment_files'].items():
        copy('sources/categories/' + name, cats / name, expected)
        data = read(cats / name)
        for r in data['rows']:
            key = r['bank'], r['row']
            require(key not in categories or categories[key] == r['category'], 'Conflicting frozen category')
            categories[key] = r['category']
    rows, inventory = [], []

    def add(bank, feature, items, pair_fn, pair_sha, labels=None, values=None):
        selected = [x for x in items if x['feature'] == feature]
        row = {'key': bank + '/' + feature, 'bank': bank, 'feature': feature,
               'category': categories[bank, feature], 'control': feature in CONTROLS, 'dev': [], 'test': []}
        for x in selected:
            require(x['split'] in ('dev', 'test'), 'Unexpected source split')
            require(encode(x['text']) == x['ids'], 'Frozen prompt tokenization mismatch')
            item = {'id': x['id'], 'split': x['split'], 'ids': x['ids']}
            if x['split'] == 'test':
                item['label'] = x['label'] if 'label' in x else int((labels[x['id']] if labels else x['value']) == values[0])
                item['pairs'] = []
                for a, b in pair_fn(x):
                    item['pairs'].append({'A_ids': encode(a), 'B_ids': encode(b), 'A': a, 'B': b,
                                          'source_sha256': pair_sha})
            row[x['split']].append(item)
        # Frozen source pairing supports an exact, no-extra-forward swap control.
        if bank == 'E57':
            paired = {(x['template_index'], x['filler_index'], x['variant']): x['id']
                      for x in selected if x['split'] == 'test'}
            source_lookup = {x['id']: x for x in selected}
            for item in row['test']:
                x = source_lookup[item['id']]
                item['swap_donor_id'] = paired[x['template_index'], x['filler_index'], 1 - x['variant']]
        rows.append(row)
        inventory.append({'row': row['key'], 'status': 'APPLICABLE', 'source_sha256': pair_sha})

    for bank, items, labels, values in [('W1', w1, None, w1values), ('E36', e36, labels36, defs36.get('rows', defs36))]:
        for feature, spec in pairs15.items():
            value_list = values[feature] if bank == 'W1' else values[feature]['values']
            pairs = [(p['A'], p['B']) for p in spec['pairs']]
            for p in spec['pairs']:
                require(encode(p['A']) == p['A_ids'] and encode(p['B']) == p['B_ids'], 'Frozen E15 pair token IDs differ')
            add(bank, feature, items, lambda x, pairs=pairs: pairs, pair15_sha, labels, value_list)
    for feature in sorted({k.split(':')[0] for k in pairs53['by_item']}):
        add('E49', feature, e49, lambda x: pairs53['by_item'][x['id']], pair53_sha)
    for feature, reason in pairs53['not_applicable'].items():
        inventory.append({'row': 'E49/' + feature, 'status': 'NOT_APPLICABLE', 'reason': reason, 'authority_commit': 'cdafe376'})
    for feature, spec in pairs56.items():
        if spec['pairs'] is not None:
            add('E56', feature, e56, lambda x, pairs=spec['pairs']: pairs, pair56_sha)
        else:
            inventory.append({'row': 'E56/' + feature, 'status': 'NOT_APPLICABLE',
                'reason': spec['reason'], 'authority_commit': 'c4ac59e1'})
    e57_static = pair57['static_pairs']
    for feature in sorted(e57_static):
        add('E57', feature, e57, lambda x, p=e57_static[feature]: [p], pair57_sha)
    add('E57', 'page_range_digit', e57,
        lambda x: [[' ' + v for v in annotations[x['id']]['answer_pair']]], pair57_sha)
    for feature in e57_definitions:
        if feature not in e57_static and feature != 'page_range_digit':
            inventory.append({'row': 'E57/' + feature, 'status': 'NOT_APPLICABLE',
                'reason': pair57['not_applicable'].get(feature, 'Outside registered E58b row scope; inherited count twins not duplicated'),
                'authority_commit': 'a52cdb11' if feature in ('loop_direction', 'section_header') else '80033b37'})
    copy('J384.npy', CACHE / 'J384.npy', J_SHA)
    dump(delivery / 'BANK.json', {'experiment': 'E58b', 'complete_registered_scope': True,
        'definition_holds_resolved': True, 'definition_authority_commit': 'a52cdb1101b542fc4887465ac4604a596c2a58c4',
        'source_bank_commits': {'E56': E56_COMMIT, 'E57': E57_COMMIT},
        'pca_population': pca_population(rows), 'rows': rows, 'source_seals': sources,
        'category_seal_sha256': category_sha, 'pair_inventory': inventory})
    validate_bank(read(delivery / 'BANK.json'))
    seal(delivery, 'DELIVERY_SEAL.json', issuer='W-sae', experiment='E58b', verified_complete=True,
         authority='User instruction to bind E15/E56 dad9076/E57 b55c194 plus §173 clarification2',
         source_bank_commits={'E56': E56_COMMIT, 'E57': E57_COMMIT})
    print(json.dumps({'bound_rows': len(rows), 'dev_items': sum(len(r['dev']) for r in rows),
        'test_items': sum(len(r['test']) for r in rows), 'PCA_population': pca_population(rows),
        'model_calls': 0, 'fits': 0, 'scores': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tokenizer', type=Path, required=True)
    assemble(parser.parse_args().tokenizer)
