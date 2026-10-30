"""§110 fresh horizon items; CPU-only construction and independent token audit.

No W1 bank is read. Only its authored template grammars and asked phrasings are
reused. Full texts are constructed before choosing capture positions; no target
generation, activation capture, reader score or model weights are involved.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import random
import re

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot.items import FEATURES, load_pinned_tokenizer
from projects.g_agreement.blindspot.w1_templates import PARENS, PROSE, EXPRESSIONS
from .e15_pairs import frozen_pairs

SEED = 20261025
ROWS = ('prose_paren', 'python_string', 'list_depth')
CELLS = ('short_early', 'short_late', 'long_early', 'long_late')
WORDS = ('saffron', 'cobalt', 'russet', 'verdant', 'pewter', 'maroon', 'ivory', 'ochre',
         'umber', 'scarlet', 'mauve', 'crimson', 'azure', 'violet', 'sepia', 'indigo')
NOUNS = ('pavilion', 'observatory', 'courthouse', 'aqueduct', 'greenhouse', 'boathouse',
         'foundry', 'conservatory', 'kitchen', 'chapel', 'pantry', 'shelter', 'mill', 'dock')
REPLACEMENTS = {
    'caretaker': ('steward', 'custodian', 'porter'), 'box': ('basket', 'trunk', 'chest'),
    'visitors': ('travellers', 'delegates', 'inspectors'), 'guide': ('host', 'ranger', 'curator'),
    'workshop': ('foundry', 'pavilion', 'studio'), 'ledger': ('register', 'journal', 'notebook'),
    'residents': ('families', 'neighbours', 'volunteers'), 'trees': ('elms', 'cedars', 'willows'),
    'technicians': ('surveyors', 'engineers', 'students'), 'water': ('stream', 'basin', 'pond'),
    'librarian': ('archivist', 'historian', 'curator'), 'notebook': ('diary', 'journal', 'folio'),
    'gardener': ('groundskeeper', 'carpenter', 'steward'), 'birds': ('finches', 'robins', 'sparrows'),
    'excursion': ('outing', 'expedition', 'visit'), 'museum': ('gallery', 'exhibition', 'library'),
    'passengers': ('commuters', 'travellers', 'guests'), 'photographs': ('portraits', 'drawings', 'postcards'),
    'cafe': ('bakery', 'tavern', 'canteen'), 'orchard': ('garden', 'farm', 'market'),
    'mechanic': ('craftsman', 'watchmaker', 'engineer'), 'apprentice': ('student', 'trainee', 'assistant'),
    'teacher': ('lecturer', 'researcher', 'instructor'), 'archive': ('library', 'collection', 'gallery'),
}
STAGE_KEYS = ('id', 'pair_id', 'lexical_id', 'feature', 'cell', 'split', 'cluster',
              'ids', 'read_index', 'next16_ids', 'next16_text', 'random_donor_id', 'opposite_donor_id')


def encode(tok, text):
    return tok.encode(text, add_special_tokens=False)


def decode(tok, ids):
    return tok.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)


def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()


def fill(feature, family, variant):
    """Fresh lexical draw shared across a row's horizon cells, never across splits."""
    rng = random.Random(int(digest(f'{SEED}:{feature}:{family}:{variant}'), 16))
    word = rng.choice(WORDS) + ' ' + rng.choice(NOUNS)
    paragraph = PROSE[family].format(word=word)
    for term, choices in REPLACEMENTS.items():
        paragraph = re.sub(r'\b' + term + r'\b', rng.choice(choices), paragraph)
    # A fresh suffix, long enough to supply the full window even after a closer.
    tail = (' while the ' + rng.choice(WORDS) + ' ' + rng.choice(NOUNS) +
            ' remained quiet and the assistant carefully compared the revised measurements with '
            'the notes from yesterday before putting the spare materials on the shelf beside '
            'the window and checking the final record once more')
    return word, paragraph + tail, tail


def body_of_length(tok, text, target):
    words = text.split()
    options = [' '.join(words[:n]) for n in range(1, len(words) + 1)]
    candidates = [(len(encode(tok, ' ' + s)), s) for s in options]
    exact = [(n, s) for n, s in candidates if target <= n <= target + 1]
    if not exact:
        raise ValueError('no whole-word body at requested span length')
    return exact[0][1]


def token_at(tok, text, char_start, char_end):
    result = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    indices = [i for i, (a, b) in enumerate(result['offset_mapping'])
               if a < char_end and b > char_start]
    if len(indices) != 1:
        raise ValueError('structural marker must occupy one exact token')
    return indices[0]


def record(tok, text, read, meta):
    full = encode(tok, text)
    nxt = full[read + 1:read + 17]
    if len(nxt) != 16 or encode(tok, decode(tok, nxt)) != nxt:
        raise ValueError('real next16 must round-trip to exact reconstructor tokens')
    prefix = decode(tok, full[:read + 1])
    if encode(tok, prefix) != full[:read + 1]:
        raise ValueError('capture prefix retokenization mismatch')
    return {**meta, 'text': text, 'full_ids': full, 'ids': full[:read + 1],
            'read_index': read, 'prefix': prefix, 'next16_ids': nxt,
            'next16_text': decode(tok, nxt)}


def span_pair(tok, feature, family, variant, span):
    word, material, suffix = fill(feature, family, variant)
    target = (20 + (family + variant) % 10) if span == 'short' else (60 + (family + 2 * variant) % 19)
    body = body_of_length(tok, material, target)
    prefix = (PARENS[family][0].format(word=word).rstrip() if feature == 'prose_paren'
              else EXPRESSIONS[family].format(expr='').rstrip())
    markers = (('(', ')'), (',', ',')) if feature == 'prose_paren' else (('"', '"'), ('note', 'note'))
    result = []
    for side, (opener, closer) in enumerate(markers):
        text = prefix + ' ' + opener + ' ' + body + ' ' + closer + suffix
        opchar = len(prefix) + 1
        clchar = len(prefix + ' ' + opener + ' ' + body + ' ')
        oi = token_at(tok, text, opchar, opchar + len(opener))
        ci = token_at(tok, text, clchar, clchar + len(closer))
        result.append((text, oi, ci, (opchar, opchar + len(opener)), (clchar, clchar + len(closer))))
    return result


def build(tok):
    items = []
    for feature in ROWS:
        for family in range(12):
            split = 'dev' if family < 4 else 'test'
            for variant in range(8):
                lexical = digest(f'E17:{feature}:{family}:{variant}')[:20]
                common = {'feature': feature, 'split': split, 'cluster': f'{feature}:t{family:02d}',
                          'family': family, 'variant': variant, 'lexical_id': lexical}
                if feature != 'list_depth':
                    for span in ('short', 'long'):
                        twins = span_pair(tok, feature, family, variant, span)
                        for point in ('early', 'late'):
                            cell = span + '_' + point
                            pair_id = digest(f'{lexical}:{cell}')[:24]
                            oi, ci = twins[0][1:3]
                            choices = list(range(5, 9)) if point == 'early' else list(range(3, 9))
                            rotation = (family + variant) % len(choices)
                            choices = choices[rotation:] + choices[:rotation]
                            for distance in choices:
                                read = oi + distance if point == 'early' else ci - distance
                                try:
                                    pair = [record(tok, text, read, {**common, 'cell': cell, 'pair_id': pair_id,
                                            'id': digest(f'{pair_id}:{side}')[:24], 'value': FEATURES[feature].values[side],
                                            'label': 1 - side, 'opener_index': op, 'closer_index': cl,
                                            'opener_chars': list(oc), 'closer_chars': list(cc),
                                            'span_tokens': cl - op - 1, 'since_opener': read - op,
                                            'to_closer': cl - read})
                                            for side, (text, op, cl, oc, cc) in enumerate(twins)]
                                    break
                                except ValueError as exc:
                                    if distance == choices[-1]:
                                        raise exc
                            items.extend(pair)
                else:
                    word, material, tail = fill(feature, family, variant)
                    body = body_of_length(tok, material, 36 + (family + variant) % 7)
                    mark = ('-', '*', '+')[family % 3]
                    header = f'  {mark} {word} planning record\n    {mark} review the collected materials\n'
                    for point in ('mid_item', 'line_end'):
                        pair_id = digest(f'{lexical}:{point}')[:24]
                        for side, spaces in enumerate((2, 6)):
                            indent = ' ' * spaces
                            line = indent + mark + ' ' + body
                            text = header + line + '\n' + indent + mark + tail + '.\n'
                            endchar = len(header + line)
                            offsets = tok(text, add_special_tokens=False, return_offsets_mapping=True)['offset_mapping']
                            endidx = max(i for i, (_, b) in enumerate(offsets) if b <= endchar)
                            startchar = len(header + indent + mark)
                            startidx = token_at(tok, text, startchar + 1, startchar + 2)
                            read = endidx if point == 'line_end' else startidx + 10
                            items.append(record(tok, text, read, {**common, 'cell': point, 'pair_id': pair_id,
                                'id': digest(f'{pair_id}:{side}')[:24], 'value': FEATURES[feature].values[side],
                                'label': 1 - side, 'depth': 1 if side == 0 else 3,
                                'root_indent': 2, 'current_indent': spaces, 'line_end_chars': endchar,
                                'line_end_index': endidx, 'to_line_end': endidx - read}))
    groups = defaultdict(list)
    pairs = defaultdict(list)
    for x in items:
        groups[x['feature'], x['cell'], x['split'], x['cluster'], len(x['ids']) // 16].append(x['id'])
        pairs[x['pair_id']].append(x)
    for pair in pairs.values():
        for x, twin in (pair, pair[::-1]):
            x['opposite_donor_id'] = twin['id']
            pool = sorted(groups[x['feature'], x['cell'], x['split'], x['cluster'], len(x['ids']) // 16])
            x['random_donor_id'] = pool[int(digest(f'E17-random:{SEED}:{x["id"]}'), 16) % len(pool)]
    return items


def relative_list_depth(prefix):
    """Parse the list stack, including a reset to root when the next sibling begins."""
    stack = []
    for line in prefix.splitlines():
        m = re.match(r'^( *)([-*+]) ', line)
        if not m:
            raise ValueError('non-list line in frozen list grammar')
        indent = len(m[1])
        while stack and indent < stack[-1]:
            stack.pop()
        if not stack or indent > stack[-1]:
            stack.append(indent)
    return len(stack)


def verify(tok, items, *, complete=True):
    """Recompute every index/label from bytes; do not trust authoring metadata."""
    byid = {x['id']: x for x in items}
    if len(byid) != len(items):
        raise ValueError('duplicate item ID')
    pairs = defaultdict(list)
    counts = Counter()
    window_counts = defaultdict(Counter)
    ranges = defaultdict(lambda: defaultdict(list))
    for x in items:
        ids = encode(tok, x['text'])
        r = x['read_index']
        assert ids == x['full_ids'] and x['ids'] == ids[:r + 1]
        assert r == len(x['ids']) - 1
        assert x['prefix'] == decode(tok, x['ids']) and encode(tok, x['prefix']) == x['ids']
        assert x['next16_ids'] == ids[r + 1:r + 17] and len(x['next16_ids']) == 16
        assert x['next16_text'] == decode(tok, x['next16_ids'])
        assert encode(tok, x['next16_text']) == x['next16_ids']
        assert x['split'] == ('dev' if x['family'] < 4 else 'test')
        assert x['cluster'] == f'{x["feature"]}:t{x["family"]:02d}'
        assert x['value'] == FEATURES[x['feature']].values[1 - x['label']]
        if x['feature'] != 'list_depth':
            oi = token_at(tok, x['text'], *x['opener_chars'])
            ci = token_at(tok, x['text'], *x['closer_chars'])
            assert (oi, ci) == (x['opener_index'], x['closer_index']) and oi < r < ci
            assert ci - oi - 1 == x['span_tokens']
            assert r - oi == x['since_opener'] and ci - r == x['to_closer']
            lo, hi = (20, 30) if x['cell'].startswith('short') else (60, 80)
            assert lo <= x['span_tokens'] <= hi
            if x['cell'].endswith('early'):
                assert 5 <= r - oi <= 8
            else:
                assert 3 <= ci - r <= 8
            if x['cell'] == 'long_early':
                assert ci - r > 40
            oc = x['text'][slice(*x['opener_chars'])]
            cc = x['text'][slice(*x['closer_chars'])]
            if x['feature'] == 'prose_paren':
                assert (oc, cc) == (('(', ')') if x['label'] else (',', ','))
                state = x['prefix'].count('(') - x['prefix'].count(')')
                assert state == x['label']
            else:
                assert (oc, cc) == (('"', '"') if x['label'] else ('note', 'note'))
                assert x['prefix'].count('"') % 2 == x['label']
            for k in ('span_tokens', 'since_opener', 'to_closer'):
                ranges[x['feature'], x['cell']][k].append(x[k])
        else:
            depth = relative_list_depth(x['prefix'])
            assert depth == x['depth'] == (1 if x['label'] else 3)
            offsets = tok(x['text'], add_special_tokens=False, return_offsets_mapping=True)['offset_mapping']
            last = max(i for i, (_, b) in enumerate(offsets) if b <= x['line_end_chars'])
            assert last == x['line_end_index'] and last - r == x['to_line_end']
            assert x['text'][x['line_end_chars']] == '\n'
            if x['cell'] == 'line_end':
                assert last == r and x['prefix'][-1] != '\n'
                assert re.match(r'^\n' + ' ' * x['current_indent'] + r'[-*+] ', x['next16_text'])
            else:
                assert last - r >= 10 and '\n' not in decode(tok, ids[r + 1:last + 1])
            ranges[x['feature'], x['cell']]['to_line_end'].append(last - r)
        counts[x['feature'], x['cell'], x['split']] += 1
        pairs[x['pair_id']].append(x)
        donor = byid[x['random_donor_id']]
        assert all(donor[k] == x[k] for k in ('feature', 'cell', 'split', 'cluster'))
        assert len(donor['ids']) // 16 == len(x['ids']) // 16
        opposite = byid[x['opposite_donor_id']]
        assert opposite['pair_id'] == x['pair_id'] and opposite['label'] != x['label']
    for pair in pairs.values():
        assert len(pair) == 2
        a, b = sorted(pair, key=lambda x: -x['label'])
        assert a['label'] == 1 and b['label'] == 0
        assert a['read_index'] == b['read_index'] and len(a['full_ids']) == len(b['full_ids'])
        assert all(a[k] == b[k] for k in ('feature', 'cell', 'split', 'cluster', 'lexical_id'))
        if a['feature'] != 'list_depth':
            changed = [i for i, (u, v) in enumerate(zip(a['full_ids'], b['full_ids'])) if u != v]
            assert changed == [a['opener_index'], a['closer_index']]
            assert a['opener_index'] == b['opener_index'] and a['closer_index'] == b['closer_index']
        else:
            # The only different bytes are the two current/next-line indentation spans.
            assert a['text'].replace('\n  ', '\n').lstrip(' ') == b['text'].replace('\n      ', '\n  ').replace('\n  ', '\n').lstrip(' ')
            assert a['line_end_index'] == b['line_end_index']
        window_counts[a['feature'], a['cell']]['identical_twin_next16' if a['next16_ids'] == b['next16_ids'] else 'different_twin_next16'] += 1
    if complete:
        assert len(items) == 1920 and len(pairs) == 960
        expected = {(f, c, s): (64 if s == 'dev' else 128) for f in ROWS
                    for c in (CELLS if f != 'list_depth' else ('mid_item', 'line_end')) for s in ('dev', 'test')}
        assert dict(counts) == expected
        assert not {x['cluster'] for x in items if x['split'] == 'dev'} & {x['cluster'] for x in items if x['split'] == 'test'}
    return {'status': 'PASS', 'items': len(items), 'pairs': len(pairs), 'no_W1_bank_read': True,
            'seed': SEED, 'n_by_cell_split': {'/'.join(k): v for k, v in counts.items()},
            'ranges': {'/'.join(k): {n: [min(v), max(v)] for n, v in r.items()} for k, r in ranges.items()},
            'next16_twin_audit': {'/'.join(k): dict(v) for k, v in window_counts.items()},
            'checks': ['all full texts retokenized', 'all prefix/read indices recomputed', 'all labels independently parsed',
                       'span length and both distances', 'neutral marker-only twin differences',
                       'relative list-stack depth and equal indices', 'exact real next16 and AR retokenization',
                       '96 pairs/cell, 32 dev/64 test, disjoint template families', 'frozen donors within split/cell']}


def freeze(tok, tokenizer, frozen, stage):
    frozen, stage = Path(frozen), Path(stage)
    if (frozen / 'freeze').exists() or stage.exists():
        raise ValueError('freeze exists; no overwrite or resample')
    items = build(tok)
    audit = verify(tok, items)
    folder = frozen / 'freeze'
    folder.mkdir(parents=True, exist_ok=False)
    stage.mkdir(parents=True, exist_ok=False)
    payload = ''.join(json.dumps(x, sort_keys=True) + '\n' for x in items).encode()
    (folder / 'items.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    P.dump(folder / 'CPU_VALIDATION.json', audit)
    pairdata = frozen_pairs(tok)
    pairdata['rows'] = {f: pairdata['rows'][f] for f in ROWS}
    # The objects are byte-for-byte E15 candidates; E17 performs no new pair selection.
    pairdata['experiment_use'] = 'E17: both frozen E15-valid pairs averaged, all per-pair scores retained; no new validity gate.'
    P.dump(stage / 'pairs.json', pairdata)
    P.dump(stage / 'phrasings.json', {f: {'values': FEATURES[f].values, 'olens': FEATURES[f].pairs('olens')} for f in ROWS})
    P.jsonl(stage / 'items.input.jsonl', [{k: x[k] for k in STAGE_KEYS} for x in items])
    labels = stage.parent / (stage.name + '.labels.DO_NOT_STAGE.jsonl')
    P.jsonl(labels, [{k: x[k] for k in ('id', 'feature', 'cell', 'split', 'cluster', 'lexical_id', 'pair_id', 'label', 'value')} for x in items])
    files = ['projects/g_agreement/understand/e17_items.py', 'projects/g_agreement/understand/e15_pairs.py',
             'projects/g_agreement/blindspot/w1_templates.py', 'projects/g_agreement/blindspot/items.py',
             'projects/g_agreement/blindspot/protocol.py', 'results/g_agreement/understand/e17/REGISTERED_SECTION.md']
    manifest = {'experiment': 'E17', 'section': 110, 'registration_commit': '409690eef4efe65ac222c80b0c446f91ba448ce2', 'seed': SEED,
        'items': 1920, 'pairs': 960, 'cells': 10, 'pairs_per_cell': {'dev': 32, 'test': 64},
        'split': 'families 0..3 dev, 4..11 test; eight fresh lexical instances/family, whole family held out',
        'paired_cells': 'same lexical_id across horizon cells; bootstrap lexical_id preserves twins and cells',
        'tokenizer_sha256': P.sha(Path(tokenizer) / 'tokenizer.json'),
        'full_bank_gzip_sha256': P.sha(folder / 'items.jsonl.gz'), 'full_bank_uncompressed_sha256': hashlib.sha256(payload).hexdigest(),
        'labels_sha256': P.sha(labels), 'authoring_sources': {p: P.sha(P.ROOT / p) for p in files},
        'capture': 'raw prefix through read_index inclusive, block44; full suffix never enters target capture',
        'window': 'exact real next16 from authored full_ids, beginning strictly after read token; no generation',
        'donors': 'random hash independent of value within feature/cell/split/family/16token lengthbin, self allowed; opposite is exact twin',
        'span_length': 'interior token count = closer_index - opener_index - 1; markers each one token',
        'distance': 'early read-opener in[5,8]; late closer-read in[3,8]; long-early closer-read>40',
        'list': 'common ancestors at2/4spaces; current and next sibling at2(top) or6(third); no padding; E15 2vs4space candidates remain inherited proxy',
        'python_neutral_control': 'quotes replaced by bare word note; outside-string twin may not form executable Python; state is lexical, not syntax validity',
        'continuation_pairs': 'both E15 valid pairs for each of3rows frozen unchanged; no new dev selection',
        'science_cap_seconds': 3600, 'setup_seconds': 2400, 'source_probe': 'dev-only fixed W1 logistic probe at44',
        'no_model_calls': True}
    P.dump(stage / 'manifest.json', manifest)
    P.seal(stage, ['items.input.jsonl', 'pairs.json', 'phrasings.json', 'manifest.json'], 'E17_ITEMS_FROZEN_BEFORE_ANY_CAPTURE')
    for name in ('manifest.json', 'INPUT_SEAL.json', 'pairs.json', 'phrasings.json'):
        (folder / name).write_bytes((stage / name).read_bytes())
    return audit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('freeze', 'verify'))
    p.add_argument('--tokenizer', type=Path, required=True)
    p.add_argument('--frozen', type=Path, required=True)
    p.add_argument('--stage', type=Path)
    a = p.parse_args()
    tok = load_pinned_tokenizer(a.tokenizer)
    if a.command == 'freeze':
        result = freeze(tok, a.tokenizer, a.frozen, a.stage)
    else:
        items = [json.loads(s) for s in gzip.decompress((a.frozen / 'freeze/items.jsonl.gz').read_bytes()).decode().splitlines()]
        result = verify(tok, items)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
